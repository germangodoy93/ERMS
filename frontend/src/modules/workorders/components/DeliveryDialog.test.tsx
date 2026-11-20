import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { getBilling } from "@/modules/workshop/api";
import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { Billing, WorkOrder } from "@/types/api";

import { deliverWorkOrder } from "../api";
import { DeliveryDialog } from "./OrderActionDialogs";

vi.mock("@/modules/workshop/api", () => ({ getBilling: vi.fn() }));
vi.mock("../api", () => ({ deliverWorkOrder: vi.fn(), changeStatus: vi.fn() }));

const ORDER = {
  id: "o1",
  number: "ER-2026-000003",
  customer: { full_name: "Cliente Ficticio" },
  device: { manufacturer: "Samsung", model: "Galaxy" },
} as WorkOrder;

function billing(balance: string): Billing {
  return {
    diagnostic_fee: "50000.00",
    accepted_quote_total: null,
    amount_due: "50000.00",
    paid: "0.00",
    balance,
    payments: [],
    can_register: Number(balance) > 0,
  };
}

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <DeliveryDialog order={ORDER} onClose={() => undefined} />
    </QueryClientProvider>,
  );
}

describe("DeliveryDialog", () => {
  it("blocks delivery with balance for reception", async () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "t",
      user: makeMe({ permissions: ["work_orders:deliver", "work_orders:read"] }),
    });
    vi.mocked(getBilling).mockResolvedValue(billing("50000.00"));
    renderDialog();
    expect(await screen.findByText(/Saldo pendiente de \$ 50\.000/)).toBeInTheDocument();
    expect(screen.getByText(/pida autorización a un supervisor/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar entrega" })).toBeDisabled();
  });

  it("lets a supervisor deliver with a reason", async () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "t",
      user: makeMe({
        permissions: [
          "work_orders:deliver",
          "work_orders:deliver_with_balance",
          "work_orders:read",
        ],
      }),
    });
    vi.mocked(getBilling).mockResolvedValue(billing("50000.00"));
    vi.mocked(deliverWorkOrder).mockResolvedValue({ ...ORDER, status: "ENTREGADO" } as WorkOrder);
    renderDialog();
    const submit = await screen.findByRole("button", { name: "Registrar entrega" });
    expect(submit).toBeDisabled();
    fireEvent.change(await screen.findByLabelText("Motivo de la entrega con saldo"), {
      target: { value: "Se condona el diagnóstico" },
    });
    fireEvent.click(submit);
    await waitFor(() =>
      expect(deliverWorkOrder).toHaveBeenCalledWith("o1", {
        picked_up_by_customer: true,
        name: null,
        document: null,
        notes: null,
        balance_reason: "Se condona el diagnóstico",
        warranty_days: null,
      }),
    );
  });

  it("delivers without questions when nothing is owed", async () => {
    vi.mocked(getBilling).mockResolvedValue(billing("0.00"));
    renderDialog();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Registrar entrega" })).toBeEnabled(),
    );
    expect(screen.queryByText(/Saldo pendiente/)).toBeNull();
  });
});
