import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { CatalogPart, Evaluation } from "@/types/api";

import { evaluateBuild, getCatalog, saveBuild } from "../api";
import { EMPTY_SELECTION } from "../presentation";
import { AssemblyBuilderPage } from "./AssemblyBuilderPage";

vi.mock("../api", () => ({
  getCatalog: vi.fn(),
  evaluateBuild: vi.fn(),
  saveBuild: vi.fn(),
  getBuild: vi.fn(),
  orderBuild: vi.fn(),
}));

const CATALOG: CatalogPart[] = [
  {
    id: "c1",
    sku: "ENS-CPU-C20",
    name: "AMD Ryzen 7 9800X3D",
    category: "CPU",
    sale_price: "1999000.00",
    stock: 2,
    specs: { socket: "AM5", cores: 8, tdp_w: 162, integrated_graphics: true },
  },
  {
    id: "c2",
    sku: "ENS-CPU-C4",
    name: "Intel Core Ultra 7 265KF",
    category: "CPU",
    sale_price: "1490000.00",
    stock: 0,
    specs: { socket: "LGA1851", cores: 20, tdp_w: 250, integrated_graphics: false },
  },
];

const EVALUATION: Evaluation = {
  errors: [
    {
      message: "Socket incompatible: la CPU es LGA1851 y la placa AM5.",
      categories: ["CPU", "BOARD"],
    },
  ],
  warnings: [{ message: "Poco margen en la fuente.", categories: ["PSU"] }],
  missing: ["RAM"],
  ready: false,
  watts: 300,
  recommended_psu_w: 400,
  price: "1999000.00",
  setup_price: "0.00",
  gaming_index: 30,
  work_index: 50,
  ram_gb: 0,
  candidates: { c2: "Socket incompatible: la CPU es LGA1851 y la placa AM5." },
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/ensamble/nueva"]}>
        <Routes>
          <Route path="/ensamble/nueva" element={<AssemblyBuilderPage />} />
          <Route path="/ensamble/:buildId" element={<p>Guardada</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AssemblyBuilderPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "t",
      user: makeMe({ permissions: ["assembly:manage"] }),
    });
    vi.mocked(getCatalog).mockResolvedValue(CATALOG);
    vi.mocked(evaluateBuild).mockResolvedValue(EVALUATION);
  });

  it("shows prices, stock, incompatibility reasons and the compatibility list", async () => {
    renderPage();
    const intel = await screen.findByRole("button", { name: /Intel Core Ultra 7 265KF/ });
    expect(within(intel).getByText(/No compatible: Socket incompatible/)).toBeInTheDocument();
    expect(within(intel).getByText(/por pedir/)).toBeInTheDocument();
    const amd = screen.getByRole("button", { name: /AMD Ryzen 7 9800X3D/ });
    expect(within(amd).getByText(/2 en bodega/)).toBeInTheDocument();
    expect(screen.getByText("1 incompatibilidad")).toBeInTheDocument();
    expect(screen.getByText("Poco margen en la fuente.")).toBeInTheDocument();
    expect(screen.getByText("Falta").parentElement).toHaveTextContent("FaltaMemoria");
    expect(screen.getByRole("button", { name: /Crear orden/ })).toBeDisabled();
  });

  it("selects a part, evaluates it and saves the build", async () => {
    vi.mocked(saveBuild).mockResolvedValue({ id: "b1" } as never);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /AMD Ryzen 7 9800X3D/ }));
    await waitFor(() =>
      expect(evaluateBuild).toHaveBeenLastCalledWith({
        selection: { ...EMPTY_SELECTION, cpu: "c1" },
        profile: "GAMING",
        candidates_for: "CPU",
      }),
    );
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Gamer de Ana" } });
    fireEvent.change(screen.getByLabelText("Mano de obra del ensamble"), {
      target: { value: "150.000" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Guardar/ }));
    await waitFor(() =>
      expect(saveBuild).toHaveBeenCalledWith(
        {
          name: "Gamer de Ana",
          profile: "GAMING",
          selection: { ...EMPTY_SELECTION, cpu: "c1" },
          labor_price: "150000.00",
          notes: null,
        },
        undefined,
      ),
    );
    expect(await screen.findByText("Guardada", {}, { timeout: 5000 })).toBeInTheDocument();
  });
});
