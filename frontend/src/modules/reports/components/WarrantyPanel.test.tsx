import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type { WarrantyOverview, WorkOrder } from "@/types/api";

import { getWarranty, openClaim } from "../api";
import { WarrantyPanel } from "./WarrantyPanel";

vi.mock("../api", () => ({ getWarranty: vi.fn(), openClaim: vi.fn(), decideClaim: vi.fn() }));

const ORDER = { id: "o1", number: "ER-2026-000010", status: "ENTREGADO" } as WorkOrder;

const ACTIVE: WarrantyOverview = {
  warranty: {
    id: "w1",
    work_order_id: "o1",
    work_order_number: "ER-2026-000010",
    days: 90,
    starts_on: "2026-11-20",
    ends_on: "2027-02-18",
    active: true,
  },
  claims: [],
  is_claim_order: false,
  can_claim: true,
  can_decide: false,
};

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <WarrantyPanel order={ORDER} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WarrantyPanel", () => {
  it("shows the active warranty and opens a claim", async () => {
    vi.mocked(getWarranty).mockResolvedValue(ACTIVE);
    vi.mocked(openClaim).mockResolvedValue({ id: "o2", number: "ER-2026-000011" } as WorkOrder);
    renderPanel();
    expect(await screen.findByText("90 días: del 2026-11-20 al 2027-02-18")).toBeInTheDocument();
    expect(screen.getByText("Vigente")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Abrir reclamo de garantía" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Falla que reporta el cliente"), {
      target: { value: "La pantalla volvió a fallar." },
    });
    fireEvent.change(within(dialog).getByLabelText("Estado físico al recibirlo"), {
      target: { value: "Sin golpes." },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Abrir reclamo" }));
    await waitFor(() =>
      expect(openClaim).toHaveBeenCalledWith("o1", {
        reported_issue: "La pantalla volvió a fallar.",
        physical_condition: "Sin golpes.",
        unlock_method: "NOT_REQUIRED",
      }),
    );
  });

  it("explains when there is no warranty", async () => {
    vi.mocked(getWarranty).mockResolvedValue({ ...ACTIVE, warranty: null, can_claim: false });
    renderPanel();
    expect(
      await screen.findByText("Esta orden no tiene garantía (no se reparó)."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Abrir reclamo de garantía" })).toBeNull();
  });
});
