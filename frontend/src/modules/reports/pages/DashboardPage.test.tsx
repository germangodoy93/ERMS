import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { Dashboard } from "@/types/api";

import { getDashboard } from "../api";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api", () => ({ getDashboard: vi.fn() }));

const BASE: Dashboard = {
  scope: "WORKSHOP",
  open_by_status: [
    { status: "DIAGNOSTICO", count: 2 },
    { status: "LISTO_ENTREGA", count: 1 },
  ],
  received_today: 3,
  received_week: 9,
  overdue: 1,
  awaiting_customer: 2,
  expired_quotes: 1,
  ready_for_delivery: 1,
  ready_balance: "120000.00",
  income_month: [
    { method: "CASH", amount: "100000.00" },
    { method: "NEQUI", amount: "50000.00" },
  ],
  income_month_total: "150000.00",
  avg_turnaround_days: 2.5,
  technician_load: [{ technician: { id: "t1", full_name: "Técnica Ficticia" }, open_orders: 4 }],
  low_stock: 2,
  warranties_expiring: 1,
  open_claims: 0,
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: makeMe() });
  });

  it("shows workshop indicators with money", async () => {
    vi.mocked(getDashboard).mockResolvedValue(BASE);
    renderPage();
    expect(await screen.findByText("$ 150.000")).toBeInTheDocument();
    expect(screen.getByText("Saldo por cobrar $ 120.000")).toBeInTheDocument();
    expect(screen.getByText("1 cotizaciones vencidas")).toBeInTheDocument();
    expect(screen.getByText("Técnica Ficticia")).toBeInTheDocument();
    expect(screen.getByText("2,5 días")).toBeInTheDocument();
  });

  it("technicians only see their own orders, without money", async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      ...BASE,
      scope: "MINE",
      ready_balance: null,
      income_month: null,
      income_month_total: null,
      technician_load: null,
      low_stock: null,
      warranties_expiring: null,
      open_claims: null,
    });
    renderPage();
    expect(await screen.findByText("Tus órdenes asignadas.")).toBeInTheDocument();
    expect(screen.queryByText("Ingresos del mes")).toBeNull();
    expect(screen.queryByText("Carga por técnico")).toBeNull();
  });
});
