import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AxiosError, type AxiosResponse } from "axios";
import { createMemoryRouter, RouterProvider } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";

import { signIn } from "../session";
import { LoginPage } from "./LoginPage";

vi.mock("../session", () => ({ signIn: vi.fn() }));
const signInMock = vi.mocked(signIn);

function renderLogin(path = "/login") {
  const router = createMemoryRouter(
    [
      { path: "/login", element: <LoginPage /> },
      { path: "/", element: <p>home</p> },
      { path: "/usuarios", element: <p>users</p> },
      { path: "/cambiar-contrasena", element: <p>change password</p> },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
}

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
}

describe("LoginPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ status: "anonymous", user: null, accessToken: null });
    signInMock.mockReset();
  });

  it("validates fields before calling the API", async () => {
    renderLogin();
    fill("no-es-correo", "");
    expect(await screen.findByText("Ingrese un correo electrónico válido.")).toBeInTheDocument();
    expect(screen.getByText("Ingrese su contraseña.")).toBeInTheDocument();
    expect(signInMock).not.toHaveBeenCalled();
  });

  it("goes to the requested page after logging in", async () => {
    signInMock.mockResolvedValue(makeMe());
    renderLogin(`/login?next=${encodeURIComponent("/usuarios")}`);
    fill("supervisor@example.com", "una-clave");
    expect(await screen.findByText("users")).toBeInTheDocument();
    expect(signInMock).toHaveBeenCalledWith("supervisor@example.com", "una-clave");
  });

  it("ignores external redirect targets", async () => {
    signInMock.mockResolvedValue(makeMe());
    renderLogin(`/login?next=${encodeURIComponent("//malicioso.example.com")}`);
    fill("supervisor@example.com", "una-clave");
    expect(await screen.findByText("home")).toBeInTheDocument();
  });

  it("sends users with a temporary password to change it", async () => {
    signInMock.mockResolvedValue(makeMe({ must_change_password: true }));
    renderLogin();
    fill("supervisor@example.com", "una-clave");
    expect(await screen.findByText("change password")).toBeInTheDocument();
  });

  it("shows the message returned by the API", async () => {
    const detail = "Correo o contraseña incorrectos.";
    signInMock.mockRejectedValue(
      new AxiosError("401", "401", undefined, null, {
        status: 401,
        data: { code: "invalid_credentials", detail },
      } as AxiosResponse),
    );
    renderLogin();
    fill("supervisor@example.com", "mala");
    await waitFor(() => expect(screen.getByText(detail)).toBeInTheDocument());
  });
});
