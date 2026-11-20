import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { WorkOrder } from "@/types/api";

import { changeStatus, getWorkOrder, listPhotos } from "../api";
import { WorkOrderDetailPage } from "./WorkOrderDetailPage";

vi.mock("../api", () => ({
  getWorkOrder: vi.fn(),
  changeStatus: vi.fn(),
  listPhotos: vi.fn(),
  listTechnicians: vi.fn().mockResolvedValue([]),
  deliverWorkOrder: vi.fn(),
  assignTechnician: vi.fn(),
  downloadReceptionAct: vi.fn(),
  uploadPhoto: vi.fn(),
  deletePhoto: vi.fn(),
  getPhotoContent: vi.fn(),
}));

const TECHNICIAN = makeMe({
  roles: [{ id: "r-tech", code: "TECHNICIAN", name: "Técnico" }],
  permissions: ["customers:read", "devices:manage", "work_orders:progress", "work_orders:read"],
});

function order(overrides: Partial<WorkOrder> = {}): WorkOrder {
  return {
    id: "o1",
    number: "ER-2026-000001",
    status: "CONTROL_CALIDAD",
    priority: "NORMAL",
    received_at: "2026-11-20T15:00:00Z",
    estimated_delivery_date: null,
    customer: {
      id: "c1",
      full_name: "Cliente Ficticio Uno",
      phone: "+573000000001",
      id_type: "CC",
      id_number: "1000000001",
    },
    device: {
      id: "d1",
      category: "Celular",
      manufacturer: "Samsung",
      model: "Galaxy Ficticio",
      imei: "490154203237518",
      serial_number: null,
    },
    assigned_technician: { id: "me-1", full_name: "Técnico de Prueba" },
    branch: "Sede Bogotá",
    reported_issue: "No enciende.",
    physical_condition: "Pantalla rayada.",
    accessories: [{ code: "CHARGER", detail: null }],
    unlock_method: "NOT_REQUIRED",
    diagnostic_fee: "50000.00",
    advance_amount: "20000.00",
    advance_method: "NEQUI",
    notes: null,
    terms_version: 1,
    received_by: { id: "u2", full_name: "Recepción de Prueba" },
    delivered_at: null,
    delivered_to_name: null,
    delivered_to_document: null,
    history: [
      {
        from_status: null,
        to_status: "RECIBIDO",
        reason: null,
        changed_by: { id: "u2", full_name: "Recepción de Prueba" },
        changed_at: "2026-11-20T15:00:00Z",
      },
    ],
    allowed_transitions: ["LISTO_ENTREGA", "EN_REPARACION"],
    customer_allows_photos: false,
    updated_at: "2026-11-20T15:00:00Z",
    ...overrides,
  };
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/ordenes/o1"]}>
        <Routes>
          <Route path="/ordenes/:orderId" element={<WorkOrderDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WorkOrderDetailPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: TECHNICIAN });
    vi.mocked(getWorkOrder).mockResolvedValue(order());
    vi.mocked(listPhotos).mockResolvedValue({ demo: true, max_photos: 20, items: [] });
  });

  it("shows order data and only the transitions the API allows", async () => {
    renderPage();
    expect(await screen.findByText("ER-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("$ 50.000")).toBeInTheDocument();
    expect(screen.getByText("$ 20.000 (Nequi)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar listo para entrega" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar reparación" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Entregar equipo/ })).toBeNull();
    expect(await screen.findByText("Modo demostración")).toBeInTheDocument();
    expect(screen.getByText(/no ha autorizado fotografías/)).toBeInTheDocument();
  });

  it("asks for a reason when quality control sends the device back", async () => {
    vi.mocked(changeStatus).mockResolvedValue(order({ status: "EN_REPARACION" }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Iniciar reparación" }));
    const dialog = await screen.findByRole("dialog");
    const confirm = within(dialog).getByRole("button", { name: "Confirmar" });
    expect(within(dialog).getByText("Motivo (obligatorio)")).toBeInTheDocument();
    expect(confirm).toBeDisabled();

    fireEvent.change(within(dialog).getByRole("textbox"), {
      target: { value: "El micrófono no funciona." },
    });
    fireEvent.click(confirm);
    await waitFor(() =>
      expect(changeStatus).toHaveBeenCalledWith("o1", "EN_REPARACION", "El micrófono no funciona."),
    );
  });
});
