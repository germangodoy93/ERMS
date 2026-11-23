import { lazy } from "react";

// Application pages are loaded on demand: the login screen does not download the whole app.
export const AssemblyBuilderPage = lazy(() =>
  import("@/modules/assembly/pages/AssemblyBuilderPage").then((m) => ({
    default: m.AssemblyBuilderPage,
  })),
);
export const AssemblyPage = lazy(() =>
  import("@/modules/assembly/pages/AssemblyPage").then((m) => ({ default: m.AssemblyPage })),
);
export const AuditPage = lazy(() =>
  import("@/modules/audit/pages/AuditPage").then((m) => ({ default: m.AuditPage })),
);
export const CustomerDetailPage = lazy(() =>
  import("@/modules/customers/pages/CustomerDetailPage").then((m) => ({
    default: m.CustomerDetailPage,
  })),
);
export const CustomersPage = lazy(() =>
  import("@/modules/customers/pages/CustomersPage").then((m) => ({ default: m.CustomersPage })),
);
export const CatalogPage = lazy(() =>
  import("@/modules/devices/pages/CatalogPage").then((m) => ({ default: m.CatalogPage })),
);
export const DevicesPage = lazy(() =>
  import("@/modules/devices/pages/DevicesPage").then((m) => ({ default: m.DevicesPage })),
);
export const InventoryPage = lazy(() =>
  import("@/modules/inventory/pages/InventoryPage").then((m) => ({ default: m.InventoryPage })),
);
export const OrganizationPage = lazy(() =>
  import("@/modules/organization/pages/OrganizationPage").then((m) => ({
    default: m.OrganizationPage,
  })),
);
export const DashboardPage = lazy(() =>
  import("@/modules/reports/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
export const ReportsPage = lazy(() =>
  import("@/modules/reports/pages/ReportsPage").then((m) => ({ default: m.ReportsPage })),
);
export const RolesPage = lazy(() =>
  import("@/modules/roles/pages/RolesPage").then((m) => ({ default: m.RolesPage })),
);
export const SystemStatusPage = lazy(() =>
  import("@/modules/system/pages/SystemStatusPage").then((m) => ({
    default: m.SystemStatusPage,
  })),
);
export const UsersPage = lazy(() =>
  import("@/modules/users/pages/UsersPage").then((m) => ({ default: m.UsersPage })),
);
export const NewWorkOrderPage = lazy(() =>
  import("@/modules/workorders/pages/NewWorkOrderPage").then((m) => ({
    default: m.NewWorkOrderPage,
  })),
);
export const WorkOrderDetailPage = lazy(() =>
  import("@/modules/workorders/pages/WorkOrderDetailPage").then((m) => ({
    default: m.WorkOrderDetailPage,
  })),
);
export const WorkOrdersPage = lazy(() =>
  import("@/modules/workorders/pages/WorkOrdersPage").then((m) => ({ default: m.WorkOrdersPage })),
);
