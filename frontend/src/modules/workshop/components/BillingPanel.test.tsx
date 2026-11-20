import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";

import type { Billing, WorkOrder } from "@/types/api";

import { getBilling } from "../api";
import { workshopKeys } from "../hooks";
import { BillingPanel } from "./BillingPanel";

vi.mock("../api", () => ({
  getBilling: vi.fn(),
  registerPayment: vi.fn(),
  downloadReceipt: vi.fn(),
}));

const ORDER = { id: "o1", number: "ER-2026-000010", status: "DIAGNOSTICO" } as WorkOrder;

const DIAGNOSTIC_ONLY: Billing = {
  diagnostic_fee: "40000.00",
  accepted_quote_total: null,
  amount_due: "40000.00",
  paid: "0.00",
  balance: "40000.00",
  payments: [],
  can_register: true,
};

describe("BillingPanel", () => {
  it("suggests the current balance, also after the quote is approved", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.mocked(getBilling).mockResolvedValue(DIAGNOSTIC_ONLY);
    render(
      <QueryClientProvider client={client}>
        <BillingPanel order={ORDER} />
      </QueryClientProvider>,
    );
    expect(await screen.findByLabelText("Valor del pago")).toHaveValue("40000");

    act(() => {
      client.setQueryData(workshopKeys.billing("o1"), {
        ...DIAGNOSTIC_ONLY,
        accepted_quote_total: "200000.00",
        amount_due: "200000.00",
        balance: "200000.00",
      });
    });
    await waitFor(() => expect(screen.getByLabelText("Valor del pago")).toHaveValue("200000"));
  });
});
