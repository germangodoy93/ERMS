import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";

import { PERMS } from "../permissions";
import { RequireAuth, RequirePermission } from "./RouteGuards";

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: "/login", element: <p>login page</p> },
      {
        element: <RequireAuth />,
        children: [
          { path: "/cambiar-contrasena", element: <p>change password page</p> },
          { path: "/privado", element: <p>private page</p> },
          {
            path: "/auditoria",
            element: (
              <RequirePermission permission={PERMS.ROLES_MANAGE}>
                <p>roles admin</p>
              </RequirePermission>
            ),
          },
        ],
      },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe("route guards", () => {
  it("shows a loader while the session is being restored", () => {
    useAuthStore.setState({ status: "unknown", user: null, accessToken: null });
    renderAt("/privado");
    expect(screen.getByText("Cargando ERMS…")).toBeInTheDocument();
  });

  it("redirects anonymous users to login keeping the destination", () => {
    useAuthStore.setState({ status: "anonymous", user: null, accessToken: null });
    const router = renderAt("/privado?x=1");
    expect(screen.getByText("login page")).toBeInTheDocument();
    expect(router.state.location.search).toBe(`?next=${encodeURIComponent("/privado?x=1")}`);
  });

  it("forces the temporary password change before anything else", () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "t",
      user: makeMe({ must_change_password: true }),
    });
    renderAt("/privado");
    expect(screen.getByText("change password page")).toBeInTheDocument();
  });

  it("renders private pages for authenticated users", () => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: makeMe() });
    renderAt("/privado");
    expect(screen.getByText("private page")).toBeInTheDocument();
  });

  it("blocks pages the role is not allowed to see", () => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: makeMe() });
    renderAt("/auditoria");
    expect(screen.getByText("Acceso restringido")).toBeInTheDocument();
    expect(screen.queryByText("roles admin")).not.toBeInTheDocument();
  });
});
