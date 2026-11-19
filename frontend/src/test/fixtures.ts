import type { Me, Role, User } from "@/types/api";

/** Test-only data: obviously fictitious values. */
export const ROLES: Role[] = [
  { id: "r-admin", code: "ADMIN", name: "Administrador", is_system: true, permissions: [] },
  { id: "r-sup", code: "SUPERVISOR", name: "Supervisor", is_system: true, permissions: [] },
  { id: "r-tech", code: "TECHNICIAN", name: "Técnico", is_system: true, permissions: [] },
];

export function makeMe(overrides: Partial<Me> = {}): Me {
  return {
    id: "me-1",
    email: "supervisor@example.com",
    full_name: "Supervisora de Prueba",
    organization: { id: "org-1", name: "Organización de prueba" },
    roles: [{ id: "r-sup", code: "SUPERVISOR", name: "Supervisor" }],
    permissions: ["audit:read", "users:manage", "users:read"],
    must_change_password: false,
    ...overrides,
  };
}

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "u-1",
    email: "tecnico@example.com",
    full_name: "Técnico de Prueba",
    phone: null,
    is_active: true,
    must_change_password: false,
    roles: [{ id: "r-tech", code: "TECHNICIAN", name: "Técnico" }],
    last_login_at: null,
    locked_until: null,
    created_at: "2026-11-19T15:00:00Z",
    updated_at: "2026-11-19T15:00:00Z",
    ...overrides,
  };
}
