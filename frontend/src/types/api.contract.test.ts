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

describe("API contract (docs/api/openapi.json)", () => {
  it("exposes the health endpoints used by the frontend", () => {
    expect(Object.keys(openapi.paths)).toEqual(
      expect.arrayContaining(["/api/v1/health/live", "/api/v1/health/ready"]),
    );
  });

  it("keeps status enums in sync", () => {
    expect(schema("ComponentStatus").enum).toEqual([...COMPONENT_STATUSES]);
    expect(schema("OverallStatus").enum).toEqual([...OVERALL_STATUSES]);
  });

  it("keeps ReadinessResponse fields in sync", () => {
    const readiness = schema("ReadinessResponse");
    expect(Object.keys(readiness.properties ?? {}).sort()).toEqual(
      ["checked_at", "components", "environment", "status", "version"].sort(),
    );
    expect(readiness.required?.sort()).toEqual(
      ["checked_at", "components", "environment", "status", "version"].sort(),
    );
  });

  it("keeps ComponentHealth fields in sync", () => {
    const component = schema("ComponentHealth");
    expect(Object.keys(component.properties ?? {}).sort()).toEqual(
      ["critical", "detail", "latency_ms", "name", "status"].sort(),
    );
    expect(component.required?.sort()).toEqual(["critical", "name", "status"]);
  });
});
