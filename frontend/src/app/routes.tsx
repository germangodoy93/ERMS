import type { RouteObject } from "react-router";

import { AppLayout } from "@/layouts/AppLayout";
import { AuditPage } from "@/modules/audit/pages/AuditPage";
import { RequireAuth, RequirePermission } from "@/modules/auth/components/RouteGuards";
import { ChangePasswordPage } from "@/modules/auth/pages/ChangePasswordPage";
import { ForgotPasswordPage } from "@/modules/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/modules/auth/pages/LoginPage";
import { ResetPasswordPage } from "@/modules/auth/pages/ResetPasswordPage";
import { PERMS } from "@/modules/auth/permissions";
import { RolesPage } from "@/modules/roles/pages/RolesPage";
import { SystemStatusPage } from "@/modules/system/pages/SystemStatusPage";
import { UsersPage } from "@/modules/users/pages/UsersPage";

import { NotFoundPage } from "./NotFoundPage";

export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  { path: "/recuperar-contrasena", element: <ForgotPasswordPage /> },
  { path: "/restablecer-contrasena", element: <ResetPasswordPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: "/cambiar-contrasena", element: <ChangePasswordPage /> },
      {
        path: "/",
        element: <AppLayout />,
        children: [
          { index: true, element: <SystemStatusPage /> },
          {
            path: "usuarios",
            element: (
              <RequirePermission permission={PERMS.USERS_READ}>
                <UsersPage />
              </RequirePermission>
            ),
          },
          {
            path: "roles",
            element: (
              <RequirePermission permission={PERMS.USERS_READ}>
                <RolesPage />
              </RequirePermission>
            ),
          },
          {
            path: "auditoria",
            element: (
              <RequirePermission permission={PERMS.AUDIT_READ}>
                <AuditPage />
              </RequirePermission>
            ),
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
