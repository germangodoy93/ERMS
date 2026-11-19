import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe, makeUser, ROLES } from "@/test/fixtures";

import { listRoles, listUsers } from "../api";
import { UsersPage } from "./UsersPage";

vi.mock("../api", () => ({
  listUsers: vi.fn(),
  listRoles: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  setUserRoles: vi.fn(),
  setTemporaryPassword: vi.fn(),
}));

const ADMIN_USER = makeUser({
  id: "u-admin",
  full_name: "Administradora de Prueba",
  email: "admin@example.com",
  roles: [{ id: "r-admin", code: "ADMIN", name: "Administrador" }],
});
const TECH_USER = makeUser({ must_change_password: true });

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("UsersPage", () => {
  beforeEach(() => {
    vi.mocked(listRoles).mockResolvedValue(ROLES);
    vi.mocked(listUsers).mockResolvedValue({
      items: [ADMIN_USER, TECH_USER],
      total: 2,
      page: 1,
      size: 20,
    });
  });

  it("lists users with their status", async () => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: makeMe() });
    renderPage();
    expect(await screen.findByText("Técnico de Prueba")).toBeInTheDocument();
    expect(screen.getByText("Clave temporal")).toBeInTheDocument();
    expect(screen.getByText("1–2 de 2")).toBeInTheDocument();
  });

  it("supervisor cannot act on administrators nor assign the admin role", async () => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: makeMe() });
    renderPage();
    await screen.findByText("Técnico de Prueba");

    expect(
      screen.queryByRole("button", { name: "Acciones para Administradora de Prueba" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Acciones para Técnico de Prueba" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Nuevo usuario/ }));
    const dialog = await screen.findByRole("dialog");
    const adminCheckbox = within(dialog)
      .getByText("Administrador")
      .closest("label")
      ?.querySelector("button");
    expect(adminCheckbox).toBeDisabled();
  });

  it("read-only users do not see management actions", async () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "t",
      user: makeMe({ permissions: ["users:read"] }),
    });
    renderPage();
    await screen.findByText("Técnico de Prueba");
    expect(screen.queryByRole("button", { name: /Nuevo usuario/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Acciones para/ })).not.toBeInTheDocument();
  });
});
