import { useAuthStore } from "@/stores/auth";
import type { Me } from "@/types/api";

/** Mirrors backend app/modules/roles/catalog.py (Perm). */
export const PERMS = {
  USERS_READ: "users:read",
  USERS_MANAGE: "users:manage",
  ROLES_MANAGE: "roles:manage",
  AUDIT_READ: "audit:read",
  ORGANIZATION_MANAGE: "organization:manage",
  CUSTOMERS_READ: "customers:read",
  CUSTOMERS_MANAGE: "customers:manage",
  CUSTOMERS_ANONYMIZE: "customers:anonymize",
  DEVICES_MANAGE: "devices:manage",
  CATALOG_MANAGE: "catalog:manage",
  WORK_ORDERS_READ: "work_orders:read",
  WORK_ORDERS_CREATE: "work_orders:create",
  WORK_ORDERS_ASSIGN: "work_orders:assign",
  WORK_ORDERS_PROGRESS: "work_orders:progress",
  WORK_ORDERS_DELIVER: "work_orders:deliver",
  WORK_ORDERS_DELIVER_WITH_BALANCE: "work_orders:deliver_with_balance",
  INVENTORY_READ: "inventory:read",
  INVENTORY_MANAGE: "inventory:manage",
  QUOTES_MANAGE: "quotes:manage",
  QUOTES_DISCOUNT: "quotes:discount",
  REPAIRS_MANAGE: "repairs:manage",
  PAYMENTS_MANAGE: "payments:manage",
  REPORTS_READ: "reports:read",
  WARRANTIES_MANAGE: "warranties:manage",
} as const;

export type PermissionCode = (typeof PERMS)[keyof typeof PERMS];

export const ADMIN_ROLE_CODE = "ADMIN";

export function can(user: Me | null, permission: PermissionCode): boolean {
  return user?.permissions.includes(permission) ?? false;
}

export function useCan(permission: PermissionCode): boolean {
  return useAuthStore((state) => can(state.user, permission));
}
