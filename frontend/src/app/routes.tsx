import type { RouteObject } from "react-router";

import { AppLayout } from "@/layouts/AppLayout";
import { AuditPage } from "@/modules/audit/pages/AuditPage";
import { RequireAuth, RequirePermission } from "@/modules/auth/components/RouteGuards";
import { ChangePasswordPage } from "@/modules/auth/pages/ChangePasswordPage";
import { ForgotPasswordPage } from "@/modules/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/modules/auth/pages/LoginPage";
import { ResetPasswordPage } from "@/modules/auth/pages/ResetPasswordPage";
import { PERMS } from "@/modules/auth/permissions";
import { CustomerDetailPage } from "@/modules/customers/pages/CustomerDetailPage";
import { CustomersPage } from "@/modules/customers/pages/CustomersPage";
import { CatalogPage } from "@/modules/devices/pages/CatalogPage";
import { DevicesPage } from "@/modules/devices/pages/DevicesPage";
import { InventoryPage } from "@/modules/inventory/pages/InventoryPage";
import { OrganizationPage } from "@/modules/organization/pages/OrganizationPage";
import { RolesPage } from "@/modules/roles/pages/RolesPage";
import { NewWorkOrderPage } from "@/modules/workorders/pages/NewWorkOrderPage";
import { WorkOrderDetailPage } from "@/modules/workorders/pages/WorkOrderDetailPage";
import { WorkOrdersPage } from "@/modules/workorders/pages/WorkOrdersPage";
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
            path: "ordenes",
            element: (
              <RequirePermission permission={PERMS.WORK_ORDERS_READ}>
                <WorkOrdersPage />
              </RequirePermission>
            ),
          },
          {
            path: "ordenes/nueva",
            element: (
              <RequirePermission permission={PERMS.WORK_ORDERS_CREATE}>
                <NewWorkOrderPage />
              </RequirePermission>
            ),
          },
          {
            path: "ordenes/:orderId",
            element: (
              <RequirePermission permission={PERMS.WORK_ORDERS_READ}>
                <WorkOrderDetailPage />
              </RequirePermission>
            ),
          },
          {
            path: "inventario",
            element: (
              <RequirePermission permission={PERMS.INVENTORY_READ}>
                <InventoryPage />
              </RequirePermission>
            ),
          },
          {
            path: "clientes",
            element: (
              <RequirePermission permission={PERMS.CUSTOMERS_READ}>
                <CustomersPage />
              </RequirePermission>
            ),
          },
          {
            path: "clientes/:customerId",
            element: (
              <RequirePermission permission={PERMS.CUSTOMERS_READ}>
                <CustomerDetailPage />
              </RequirePermission>
            ),
          },
          {
            path: "dispositivos",
            element: (
              <RequirePermission permission={PERMS.CUSTOMERS_READ}>
                <DevicesPage />
              </RequirePermission>
            ),
          },
          {
            path: "taller",
            element: (
              <RequirePermission permission={PERMS.ORGANIZATION_MANAGE}>
                <OrganizationPage />
              </RequirePermission>
            ),
          },
          {
            path: "catalogo",
            element: (
              <RequirePermission permission={PERMS.CATALOG_MANAGE}>
                <CatalogPage />
              </RequirePermission>
            ),
          },
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
