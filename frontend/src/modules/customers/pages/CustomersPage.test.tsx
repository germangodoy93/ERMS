import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { getCurrentPolicy } from "@/modules/organization/api";
import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { CurrentPrivacyPolicy, Customer, CustomerListItem } from "@/types/api";

import { createCustomer, listCustomers } from "../api";
import { CustomersPage } from "./CustomersPage";

vi.mock("../api", () => ({
  listCustomers: vi.fn(),
  createCustomer: vi.fn(),
  getCustomer: vi.fn(),
  updateCustomer: vi.fn(),
  listConsents: vi.fn(),
  changeConsent: vi.fn(),
  anonymizeCustomer: vi.fn(),
}));
vi.mock("@/modules/organization/api", () => ({ getCurrentPolicy: vi.fn() }));

const RECEPTION = makeMe({
  roles: [{ id: "r-rec", code: "RECEPTIONIST", name: "Recepcionista" }],
  permissions: ["customers:manage", "customers:read", "devices:manage"],
});

const POLICY: CurrentPrivacyPolicy = {
  policy: { id: "p1", version: 2, content: "Texto", published_at: "2026-11-19T15:00:00Z" },
  authorizations: {
    DATA_PROCESSING: "Autorizo el tratamiento de mis datos (versión 2).",
    PHOTOS: "Autorizo fotografías del equipo.",
    DIAGNOSTIC_AGENT: "Autorizo el agente de diagnóstico.",
  },
};

function customer(overrides: Partial<CustomerListItem> = {}): CustomerListItem {
  return {
    id: "c1",
    kind: "PERSON",
    full_name: "Cliente Ficticio Uno",
    id_type: "CC",
    id_number: "1000000001",
    phone: "+573000000001",
    email: null,
    is_active: true,
    anonymized_at: null,
    created_at: "2026-11-19T15:00:00Z",
    ...overrides,
  };
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <CustomersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function openNewCustomer() {
  fireEvent.click(await screen.findByRole("button", { name: /Nuevo cliente/ }));
  return screen.findByRole("dialog");
}

describe("CustomersPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: RECEPTION });
    vi.mocked(listCustomers).mockResolvedValue({
      items: [
        customer(),
        customer({
          id: "c2",
          full_name: "Cliente Anonimizado",
          id_type: null,
          id_number: null,
          phone: null,
          anonymized_at: "2026-11-19T16:00:00Z",
          is_active: false,
        }),
      ],
      total: 2,
      page: 1,
      size: 20,
    });
    vi.mocked(getCurrentPolicy).mockResolvedValue(POLICY);
  });

  it("lists customers with formatted phone and state", async () => {
    renderPage();
    expect(await screen.findByText("Cliente Ficticio Uno")).toBeInTheDocument();
    expect(screen.getByText("300 000 0001")).toBeInTheDocument();
    expect(screen.getByText("Anonimizado")).toBeInTheDocument();
  });

  it("blocks registration while there is no published policy", async () => {
    vi.mocked(getCurrentPolicy).mockResolvedValue({ policy: null, authorizations: {} });
    renderPage();
    const dialog = await openNewCustomer();
    expect(
      await within(dialog).findByText("Falta la política de tratamiento de datos"),
    ).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Registrar cliente" })).toBeNull();
  });

  it("requires the data processing authorization and sends the granted consents", async () => {
    vi.mocked(createCustomer).mockResolvedValue({
      ...customer(),
      address: null,
      notes: null,
      updated_at: "2026-11-19T15:00:00Z",
      consents: [],
      can_be_served: true,
    } satisfies Customer);
    renderPage();
    const dialog = await openNewCustomer();
    expect(
      await within(dialog).findByText("Autorizo el tratamiento de mis datos (versión 2)."),
    ).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText("Nombre o razón social"), {
      target: { value: "Cliente Ficticio Nuevo" },
    });
    fireEvent.change(within(dialog).getByLabelText("Teléfono"), {
      target: { value: "300 000 0009" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Registrar cliente" }));
    expect(
      await within(dialog).findByText(
        "Sin la autorización de tratamiento de datos no se puede registrar al cliente.",
      ),
    ).toBeInTheDocument();
    expect(createCustomer).not.toHaveBeenCalled();

    const [dataProcessing, photos] = within(dialog).getAllByRole("checkbox");
    fireEvent.click(dataProcessing!);
    fireEvent.click(photos!);
    fireEvent.click(within(dialog).getByRole("button", { name: "Registrar cliente" }));

    await waitFor(() => expect(createCustomer).toHaveBeenCalledTimes(1));
    expect(vi.mocked(createCustomer).mock.calls[0]?.[0]).toEqual({
      kind: "PERSON",
      full_name: "Cliente Ficticio Nuevo",
      id_type: null, // a type without number means "no document"
      id_number: null,
      phone: "300 000 0009",
      email: null,
      address: null,
      notes: null,
      consents: [
        { purpose: "DATA_PROCESSING", channel: "SCREEN" },
        { purpose: "PHOTOS", channel: "SCREEN" },
      ],
    });
  });

  it("technicians can search but not register customers", async () => {
    useAuthStore.setState({
      user: makeMe({ permissions: ["customers:read", "devices:manage"] }),
    });
    renderPage();
    await screen.findByText("Cliente Ficticio Uno");
    expect(screen.queryByRole("button", { name: /Nuevo cliente/ })).toBeNull();
  });
});
