import type { ReactNode } from "react";
import type { RouteObject } from "react-router";

import { AppLayout } from "@/layouts/AppLayout";
import { RequireAuth, RequirePermission } from "@/modules/auth/components/RouteGuards";
import { ChangePasswordPage } from "@/modules/auth/pages/ChangePasswordPage";
import { ForgotPasswordPage } from "@/modules/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/modules/auth/pages/LoginPage";
import { ResetPasswordPage } from "@/modules/auth/pages/ResetPasswordPage";
import { PERMS, type PermissionCode } from "@/modules/auth/permissions";

import { NotFoundPage } from "./NotFoundPage";
import {
  AssemblyBuilderPage,
  AssemblyPage,
  AuditPage,
  CatalogPage,
  CustomerDetailPage,
  CustomersPage,
  DashboardPage,
  DevicesPage,
  InventoryPage,
  NewWorkOrderPage,
  OrganizationPage,
  ReportsPage,
  RolesPage,
  SystemStatusPage,
  UsersPage,
  WorkOrderDetailPage,
  WorkOrdersPage,
} from "./pages";

function guarded(path: string, permission: PermissionCode, element: ReactNode): RouteObject {
  return {
    path,
    element: <RequirePermission permission={permission}>{element}</RequirePermission>,
  };
}

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
          {
            index: true,
            element: (
              <RequirePermission permission={PERMS.WORK_ORDERS_READ}>
                <DashboardPage />
              </RequirePermission>
            ),
          },
          { path: "sistema", element: <SystemStatusPage /> },
          guarded("ordenes", PERMS.WORK_ORDERS_READ, <WorkOrdersPage />),
          guarded("ordenes/nueva", PERMS.WORK_ORDERS_CREATE, <NewWorkOrderPage />),
          guarded("ordenes/:orderId", PERMS.WORK_ORDERS_READ, <WorkOrderDetailPage />),
          guarded("clientes", PERMS.CUSTOMERS_READ, <CustomersPage />),
          guarded("clientes/:customerId", PERMS.CUSTOMERS_READ, <CustomerDetailPage />),
          guarded("dispositivos", PERMS.CUSTOMERS_READ, <DevicesPage />),
          guarded("inventario", PERMS.INVENTORY_READ, <InventoryPage />),
          guarded("reportes", PERMS.REPORTS_READ, <ReportsPage />),
          guarded("ensamble", PERMS.ASSEMBLY_MANAGE, <AssemblyPage />),
          guarded("ensamble/nueva", PERMS.ASSEMBLY_MANAGE, <AssemblyBuilderPage />),
          guarded("ensamble/:buildId", PERMS.ASSEMBLY_MANAGE, <AssemblyBuilderPage />),
          guarded("taller", PERMS.ORGANIZATION_MANAGE, <OrganizationPage />),
          guarded("catalogo", PERMS.CATALOG_MANAGE, <CatalogPage />),
          guarded("usuarios", PERMS.USERS_READ, <UsersPage />),
          guarded("roles", PERMS.USERS_READ, <RolesPage />),
          guarded("auditoria", PERMS.AUDIT_READ, <AuditPage />),
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
