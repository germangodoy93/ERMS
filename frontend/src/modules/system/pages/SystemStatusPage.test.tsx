import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import type { ReadinessResponse } from "@/types/api";

import { fetchReadiness } from "../api";
import { SystemStatusPage } from "./SystemStatusPage";

vi.mock("../api", () => ({ fetchReadiness: vi.fn() }));
const fetchReadinessMock = vi.mocked(fetchReadiness);

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SystemStatusPage />
    </QueryClientProvider>,
  );
}

const readyResponse: ReadinessResponse = {
  status: "ok",
  version: "0.1.0",
  environment: "development",
  checked_at: "2026-11-19T17:30:00Z",
  components: [
    {
      name: "database",
      status: "ok",
      critical: true,
      latency_ms: 2.5,
      detail: "PostgreSQL disponible, migración 0001_initial (head)",
    },
    { name: "redis", status: "not_configured", critical: false, detail: null },
  ],
};

describe("SystemStatusPage", () => {
  afterEach(() => fetchReadinessMock.mockReset());

  it("shows each component when the API is ready", async () => {
    fetchReadinessMock.mockResolvedValue(readyResponse);
    renderPage();

    expect(await screen.findByText("Sistema operativo")).toBeInTheDocument();
    expect(screen.getByText("Base de datos (PostgreSQL)")).toBeInTheDocument();
    expect(screen.getByText("Operativo")).toBeInTheDocument();
    expect(screen.getByText("No configurado")).toBeInTheDocument();
    expect(screen.getByText("Desarrollo")).toBeInTheDocument();
  });

  it("shows the unavailable state reported by the API", async () => {
    fetchReadinessMock.mockResolvedValue({
      ...readyResponse,
      status: "unavailable",
      components: [{ name: "database", status: "error", critical: true, detail: "Sin conexión" }],
    });
    renderPage();

    expect(await screen.findByText("Servicio no disponible")).toBeInTheDocument();
    expect(screen.getByText("Con fallas")).toBeInTheDocument();
  });

  it("shows a connection error when the API cannot be reached", async () => {
    fetchReadinessMock.mockRejectedValue(new Error("Network Error"));
    renderPage();

    expect(await screen.findByText("No hay conexión con la API")).toBeInTheDocument();
  });
});
