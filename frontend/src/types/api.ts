/**
 * API contract types mirroring the backend OpenAPI schema (docs/api/openapi.json).
 *
 * Written by hand because openapi-typescript does not yet support TypeScript 6
 * (see docs/ERMS-DEVOPS.md). `src/types/api.contract.test.ts` fails if these
 * definitions drift from the published schema.
 */

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
