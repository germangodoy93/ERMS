import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import type { Report } from "@/types/api";

import { getReport } from "../api";
import { ReportsPage } from "./ReportsPage";

vi.mock("../api", () => ({ getReport: vi.fn(), downloadReport: vi.fn() }));

const INCOME: Report = {
  kind: "income",
  title: "Ingresos",
  date_from: "2026-11-01",
  date_to: "2026-11-20",
  columns: ["Fecha", "Comprobante", "Orden", "Cliente", "Medio", "Valor"],
  rows: [["2026-11-20 09:38", "RC-2026-000001", "ER-2026-000001", "Cliente", "Nequi", "20000.00"]],
  summary: [["Total", "$ 20.000"]],
  money_columns: [5],
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ReportsPage />
    </QueryClientProvider>,
  );
}

describe("ReportsPage", () => {
  it("formats peso columns and switches report kind", async () => {
    vi.mocked(getReport).mockResolvedValue(INCOME);
    renderPage();
    expect(await screen.findAllByText("$ 20.000")).toHaveLength(2); // table cell + summary
    expect(screen.queryByText("20000.00")).toBeNull();

    fireEvent.click(screen.getByRole("tab", { name: "Inventario" }));
    await waitFor(() =>
      expect(getReport).toHaveBeenLastCalledWith(
        "inventory",
        expect.any(String),
        expect.any(String),
      ),
    );
  });
});
