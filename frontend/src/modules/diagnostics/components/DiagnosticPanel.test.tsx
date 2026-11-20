import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { Diagnostic, DiagnosticTestResult, WorkOrder } from "@/types/api";

import { closeDiagnostic, createAgentPairing, getDiagnostic, saveResults } from "../api";
import { remaining } from "../presentation";
import { DiagnosticPanel } from "./DiagnosticPanel";

vi.mock("../api", () => ({
  getDiagnostic: vi.fn(),
  saveResults: vi.fn(),
  closeDiagnostic: vi.fn(),
  reopenDiagnostic: vi.fn(),
  createAgentPairing: vi.fn(),
  downloadDiagnosticReport: vi.fn(),
}));

function test(code: string, name: string, extra: Partial<DiagnosticTestResult> = {}) {
  return {
    test_code: code,
    name,
    component: "General",
    automated: false,
    result: null,
    observation: null,
    evidence: null,
    source: null,
    recorded_by: null,
    recorded_at: null,
    ...extra,
  } satisfies DiagnosticTestResult;
}

function diagnostic(overrides: Partial<Diagnostic> = {}): Diagnostic {
  return {
    session_id: null,
    state: "NOT_STARTED",
    editable: true,
    agent_available: true,
    agent_unavailable_reason: null,
    agent_download_url: "https://example.com/erms-agente.exe",
    conclusion: null,
    recommendation: null,
    closed_at: null,
    closed_by: null,
    agent_version: null,
    agent_elevated: null,
    agent_reported_at: null,
    results: [
      test("POWER_ON", "Encendido"),
      test("KEYBOARD", "Teclado"),
      test("AGENT_BATTERY", "Desgaste de batería", {
        automated: true,
        result: "WARNING",
        source: "AGENT",
        observation: "Desgaste 33.6 %",
      }),
    ],
    ...overrides,
  };
}

const ORDER = { id: "o1", number: "ER-2026-000002", status: "DIAGNOSTICO" } as WorkOrder;

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <DiagnosticPanel order={ORDER} />
    </QueryClientProvider>,
  );
}

describe("DiagnosticPanel", () => {
  beforeEach(() => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "t",
      user: makeMe({ permissions: ["work_orders:progress", "work_orders:read"] }),
    });
    vi.mocked(getDiagnostic).mockResolvedValue(diagnostic());
  });

  it("shows agent results as automatic and read-only", async () => {
    renderPanel();
    expect(await screen.findByText("Desgaste 33.6 %")).toBeInTheDocument();
    expect(screen.getByText(/Agente de diagnóstico \(automático\)/)).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup", { name: "Desgaste de batería" })).toBeNull();
    expect(screen.getByRole("radiogroup", { name: "Encendido" })).toBeInTheDocument();
  });

  it("cannot close until every manual test has a result, then saves and closes", async () => {
    vi.mocked(saveResults).mockResolvedValue(diagnostic({ state: "OPEN" }));
    vi.mocked(closeDiagnostic).mockResolvedValue(diagnostic({ state: "CLOSED", editable: false }));
    renderPanel();
    const power = await screen.findByRole("radiogroup", { name: "Encendido" });
    fireEvent.change(screen.getByLabelText("Conclusión del técnico"), {
      target: { value: "No enciende: falla de placa." },
    });
    const closeButton = screen.getByRole("button", { name: /Cerrar diagnóstico/ });
    expect(closeButton).toBeDisabled();

    fireEvent.click(within(power).getByRole("radio", { name: "Falla" }));
    fireEvent.click(screen.getByRole("button", { name: /Marcar pendientes como/ }));
    expect(
      within(screen.getByRole("radiogroup", { name: "Teclado" })).getByRole("radio", {
        name: "No probado",
      }),
    ).toHaveAttribute("aria-checked", "true");
    expect(closeButton).toBeEnabled();

    fireEvent.click(closeButton);
    await waitFor(() => expect(closeDiagnostic).toHaveBeenCalled());
    expect(saveResults).toHaveBeenCalledWith("o1", [
      { test_code: "POWER_ON", result: "FAIL", observation: null },
      { test_code: "KEYBOARD", result: "NOT_TESTED", observation: null },
    ]);
    expect(closeDiagnostic).toHaveBeenCalledWith("o1", "No enciende: falla de placa.", null);
  });

  it("keeps the typed conclusion when results are saved", async () => {
    const saved = diagnostic({
      state: "OPEN",
      results: [
        test("POWER_ON", "Encendido", { result: "FAIL", recorded_at: "2026-11-20T15:00:00Z" }),
        test("KEYBOARD", "Teclado"),
      ],
    });
    vi.mocked(saveResults).mockResolvedValue(saved);
    renderPanel();
    const power = await screen.findByRole("radiogroup", { name: "Encendido" });
    fireEvent.change(screen.getByLabelText("Conclusión del técnico"), {
      target: { value: "Falla de placa." },
    });
    fireEvent.click(within(power).getByRole("radio", { name: "Falla" }));
    vi.mocked(getDiagnostic).mockResolvedValue(saved);
    fireEvent.click(screen.getByRole("button", { name: /Guardar resultados/ }));
    await waitFor(() => expect(saveResults).toHaveBeenCalled());
    // The editor remounts with the saved results; the conclusion survives.
    await waitFor(() =>
      expect(
        within(screen.getByRole("radiogroup", { name: "Encendido" })).getByRole("radio", {
          name: "Falla",
        }),
      ).toHaveAttribute("aria-checked", "true"),
    );
    expect(screen.getByLabelText("Conclusión del técnico")).toHaveValue("Falla de placa.");
  });

  it("generates a one-time code for the agent", async () => {
    vi.mocked(createAgentPairing).mockResolvedValue({
      code: "ABCD-2345",
      expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
      download_url: "https://example.com/erms-agente.exe",
    });
    renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: /Diagnóstico con agente/ }));
    expect(await screen.findByText("ABCD-2345")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Descargar agente/ })).toHaveAttribute(
      "href",
      "https://example.com/erms-agente.exe",
    );
  });

  it("formats the remaining time of the code", () => {
    const now = Date.parse("2026-11-20T10:00:00Z");
    expect(remaining("2026-11-20T10:28:41Z", now)).toBe("28:41");
    expect(remaining("2026-11-20T09:00:00Z", now)).toBe("vencido");
  });
});
