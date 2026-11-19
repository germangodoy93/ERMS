/**
 * API contract types mirroring the backend OpenAPI schema (docs/api/openapi.json).
 *
 * Written by hand because openapi-typescript does not yet support TypeScript 6
 * (ADR-008). `src/types/api.contract.test.ts` fails if these drift from the schema.
 */

// --- Health -------------------------------------------------------------------

export const COMPONENT_STATUSES = ["ok", "error", "not_configured"] as const;
export type ComponentStatus = (typeof COMPONENT_STATUSES)[number];

export const OVERALL_STATUSES = ["ok", "unavailable"] as const;
export type OverallStatus = (typeof OVERALL_STATUSES)[number];

export interface ComponentHealth {
  name: string;
  status: ComponentStatus;
  critical: boolean;
  latency_ms?: number | null;
  detail?: string | null;
}

export interface LivenessResponse {
  status?: OverallStatus;
  version: string;
}

export interface ReadinessResponse {
  status: OverallStatus;
  version: string;
  environment: string;
  /** ISO-8601 timestamp in UTC. */
  checked_at: string;
  components: ComponentHealth[];
}

// --- Shared -------------------------------------------------------------------

/** RFC 9457 Problem Details, returned by every API error. */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  instance: string;
  errors?: { field: string; message: string; type: string }[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// --- Auth ---------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  token_type?: string;
  expires_at: string;
  must_change_password: boolean;
}

export interface RoleRef {
  id: string;
  code: string;
  name: string;
}

export interface OrganizationRef {
  id: string;
  name: string;
}

export interface Me {
  id: string;
  email: string;
  full_name: string;
  organization: OrganizationRef;
  roles: RoleRef[];
  permissions: string[];
  must_change_password: boolean;
}

// --- Users, roles, audit ---------------------------------------------------------

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  must_change_password: boolean;
  roles: RoleRef[];
  last_login_at: string | null;
  locked_until: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  full_name: string;
  phone?: string | null;
  temporary_password: string;
  role_ids: string[];
}

export interface UserUpdate {
  email?: string | null;
  full_name?: string | null;
  phone?: string | null;
  is_active?: boolean | null;
}

export interface Role {
  id: string;
  code: string;
  name: string;
  is_system: boolean;
  permissions: string[];
}

export interface Permission {
  code: string;
  description: string;
}

export interface AuditActor {
  id: string;
  email: string;
  full_name: string;
}

export interface AuditLog {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  changes: Record<string, unknown> | null;
  actor: AuditActor | null;
  ip_address: string | null;
  created_at: string;
}
