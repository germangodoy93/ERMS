import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { COMPONENT_STATUSES, OVERALL_STATUSES } from "./api";

interface SchemaObject {
  enum?: string[];
  properties?: Record<string, unknown>;
  required?: string[];
}

const openapi = JSON.parse(
  // Vitest runs from frontend/; the schema is exported by backend/scripts/export_openapi.py.
  readFileSync(resolve(process.cwd(), "../docs/api/openapi.json"), "utf-8"),
) as { components: { schemas: Record<string, SchemaObject> }; paths: Record<string, unknown> };

const schemas = openapi.components.schemas;

function schema(name: string): SchemaObject {
  const found = schemas[name];
  if (!found) throw new Error(`Schema ${name} missing from docs/api/openapi.json`);
  return found;
}

/** The TypeScript interface must declare exactly these fields (see src/types/api.ts). */
const FIELDS: Record<string, { all: string[]; required: string[] }> = {
  ReadinessResponse: {
    all: ["checked_at", "components", "environment", "status", "version"],
    required: ["checked_at", "components", "environment", "status", "version"],
  },
  ComponentHealth: {
    all: ["critical", "detail", "latency_ms", "name", "status"],
    required: ["critical", "name", "status"],
  },
  TokenResponse: {
    all: ["access_token", "expires_at", "must_change_password", "token_type"],
    required: ["access_token", "expires_at", "must_change_password"],
  },
  MeResponse: {
    all: [
      "email",
      "full_name",
      "id",
      "must_change_password",
      "organization",
      "permissions",
      "roles",
    ],
    required: [
      "email",
      "full_name",
      "id",
      "must_change_password",
      "organization",
      "permissions",
      "roles",
    ],
  },
  UserRead: {
    all: [
      "created_at",
      "email",
      "full_name",
      "id",
      "is_active",
      "last_login_at",
      "locked_until",
      "must_change_password",
      "phone",
      "roles",
      "updated_at",
    ],
    required: [
      "created_at",
      "email",
      "full_name",
      "id",
      "is_active",
      "last_login_at",
      "locked_until",
      "must_change_password",
      "phone",
      "roles",
      "updated_at",
    ],
  },
  UserCreate: {
    all: ["email", "full_name", "phone", "role_ids", "temporary_password"],
    required: ["email", "full_name", "role_ids", "temporary_password"],
  },
  UserUpdate: { all: ["email", "full_name", "is_active", "phone"], required: [] },
  RoleRead: {
    all: ["code", "id", "is_system", "name", "permissions"],
    required: ["code", "id", "is_system", "name", "permissions"],
  },
  AuditLogRead: {
    all: [
      "action",
      "actor",
      "changes",
      "created_at",
      "entity_id",
      "entity_type",
      "id",
      "ip_address",
    ],
    required: [
      "action",
      "actor",
      "changes",
      "created_at",
      "entity_id",
      "entity_type",
      "id",
      "ip_address",
    ],
  },
};

describe("API contract (docs/api/openapi.json)", () => {
  it("exposes the endpoints used by the frontend", () => {
    expect(Object.keys(openapi.paths)).toEqual(
      expect.arrayContaining([
        "/api/v1/health/ready",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/auth/password/forgot",
        "/api/v1/auth/password/reset",
        "/api/v1/auth/password/change",
        "/api/v1/users",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{user_id}/roles",
        "/api/v1/users/{user_id}/temporary-password",
        "/api/v1/roles",
        "/api/v1/roles/{role_id}/permissions",
        "/api/v1/permissions",
        "/api/v1/audit-logs",
      ]),
    );
  });

  it("keeps status enums in sync", () => {
    expect(schema("ComponentStatus").enum).toEqual([...COMPONENT_STATUSES]);
    expect(schema("OverallStatus").enum).toEqual([...OVERALL_STATUSES]);
  });

  it.each(Object.entries(FIELDS))("keeps %s fields in sync", (name, fields) => {
    const s = schema(name);
    expect(Object.keys(s.properties ?? {}).sort()).toEqual([...fields.all].sort());
    expect((s.required ?? []).slice().sort()).toEqual([...fields.required].sort());
  });
});
