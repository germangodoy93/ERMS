import { useAuthStore } from "@/stores/auth";
import type { Me } from "@/types/api";

/** Mirrors backend app/modules/roles/catalog.py (Perm). */
export const PERMS = {
  USERS_READ: "users:read",
  USERS_MANAGE: "users:manage",
  ROLES_MANAGE: "roles:manage",
  AUDIT_READ: "audit:read",
} as const;

export type PermissionCode = (typeof PERMS)[keyof typeof PERMS];

export const ADMIN_ROLE_CODE = "ADMIN";

export function can(user: Me | null, permission: PermissionCode): boolean {
  return user?.permissions.includes(permission) ?? false;
}

export function useCan(permission: PermissionCode): boolean {
  return useAuthStore((state) => can(state.user, permission));
}
