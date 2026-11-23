import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type { AssemblyChecklist, WorkOrder } from "@/types/api";

import { completeStep, consumeParts, getChecklist } from "../api";
import { AssemblyChecklistPanel } from "./AssemblyChecklistPanel";

vi.mock("../api", () => ({
  getChecklist: vi.fn(),
  consumeParts: vi.fn(),
  completeStep: vi.fn(),
}));

const ORDER = { id: "o1", kind: "ASSEMBLY", status: "EN_REPARACION" } as WorkOrder;

const CPU = {
  code: "cpu",
  title: "Colocar la CPU en el socket",
  done: false,
  blocked_reason: null,
};
const PASTE = {
  code: "paste",
  title: "Aplicar pasta térmica sobre la CPU",
  done: false,
  blocked_reason: "Aún no: primero la CPU debe estar en su socket.",
};

const CHECKLIST: AssemblyChecklist = {
  build_id: "b1",
  build_name: "Gamer de Ana",
  parts_consumed: false,
  can_work: true,
  steps: [CPU, PASTE],
};

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AssemblyChecklistPanel order={ORDER} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AssemblyChecklistPanel", () => {
  it("consumes the parts and then completes steps in order", async () => {
    vi.mocked(getChecklist).mockResolvedValue(CHECKLIST);
    vi.mocked(consumeParts).mockResolvedValue({ ...CHECKLIST, parts_consumed: true });
    vi.mocked(completeStep).mockResolvedValue({
      ...CHECKLIST,
      parts_consumed: true,
      steps: [
        { ...CPU, done: true },
        { ...PASTE, blocked_reason: null },
      ],
    });
    renderPanel();
    expect(
      await screen.findByText("Aún no: primero la CPU debe estar en su socket."),
    ).toBeInTheDocument();
    expect(screen.getByText(/0 de 2 pasos/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Descontar piezas/ }));
    expect(await screen.findByText("Piezas descontadas del inventario.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Colocar la CPU en el socket/ }));
    await waitFor(() => expect(completeStep).toHaveBeenCalledWith("o1", "cpu"));
    expect(await screen.findByText(/1 de 2 pasos/)).toBeInTheDocument();
    expect(screen.queryByText(/Aún no:/)).toBeNull();
  });

  it("is read-only outside the repair stage", async () => {
    vi.mocked(getChecklist).mockResolvedValue({ ...CHECKLIST, can_work: false });
    renderPanel();
    expect(await screen.findByRole("button", { name: /Descontar piezas/ })).toBeDisabled();
    expect(screen.getByText("Los pasos se marcan con la orden en reparación.")).toBeInTheDocument();
  });
});
