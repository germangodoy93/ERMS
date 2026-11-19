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

// --- Organization and privacy policy (Sprint 2) -----------------------------------

export interface Organization {
  id: string;
  name: string;
  slug: string;
  legal_name: string | null;
  tax_id: string | null;
  address: string | null;
  city: string | null;
  phone: string | null;
  email: string | null;
}

export interface OrganizationUpdate {
  name?: string | null;
  legal_name?: string | null;
  tax_id?: string | null;
  address?: string | null;
  city?: string | null;
  phone?: string | null;
  email?: string | null;
}

export const CONSENT_PURPOSES = ["DATA_PROCESSING", "PHOTOS", "DIAGNOSTIC_AGENT"] as const;
export type ConsentPurpose = (typeof CONSENT_PURPOSES)[number];

export const CONSENT_CHANNELS = ["SCREEN", "PAPER", "VERBAL"] as const;
export type ConsentChannel = (typeof CONSENT_CHANNELS)[number];

export interface PrivacyPolicy {
  id: string;
  version: number;
  content: string;
  published_at: string;
}

export interface PrivacyPolicyVersion {
  id: string;
  version: number;
  published_at: string;
}

export interface CurrentPrivacyPolicy {
  policy: PrivacyPolicy | null;
  authorizations: Partial<Record<ConsentPurpose, string>>;
}

export interface PrivacyPolicyDraft {
  content: string;
  missing_fields: string[];
}

// --- Customers ------------------------------------------------------------------

export const ID_TYPES = ["CC", "CE", "NIT", "PAS", "TI", "PPT"] as const;
export type IdType = (typeof ID_TYPES)[number];

export const CUSTOMER_KINDS = ["PERSON", "COMPANY"] as const;
export type CustomerKind = (typeof CUSTOMER_KINDS)[number];

export interface ConsentStatus {
  purpose: ConsentPurpose;
  granted: boolean;
  channel: ConsentChannel;
  policy_version: number;
  recorded_at: string;
}

export interface ConsentRecord extends ConsentStatus {
  id: string;
  recorded_by: string | null;
}

export interface CustomerListItem {
  id: string;
  kind: CustomerKind;
  full_name: string;
  id_type: IdType | null;
  id_number: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  anonymized_at: string | null;
  created_at: string;
}

export interface Customer extends CustomerListItem {
  address: string | null;
  notes: string | null;
  updated_at: string;
  consents: ConsentStatus[];
  can_be_served: boolean;
}

export interface ConsentGrant {
  purpose: ConsentPurpose;
  channel: ConsentChannel;
}

export interface CustomerCreate {
  kind?: CustomerKind;
  full_name: string;
  id_type?: IdType | null;
  id_number?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  notes?: string | null;
  consents: ConsentGrant[];
}

export interface CustomerUpdate {
  kind?: CustomerKind | null;
  full_name?: string | null;
  id_type?: IdType | null;
  id_number?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  notes?: string | null;
  is_active?: boolean | null;
}

export interface ConsentChange {
  purpose: ConsentPurpose;
  granted: boolean;
  channel: ConsentChannel;
}

// --- Device catalog and devices ----------------------------------------------------

export interface DeviceCategory {
  code: string;
  name: string;
}

export interface Manufacturer {
  id: string;
  name: string;
  is_active: boolean;
}

export interface DeviceModel {
  id: string;
  name: string;
  release_year: number | null;
  is_active: boolean;
  manufacturer: Manufacturer;
  category: DeviceCategory;
}

export interface DeviceModelCreate {
  manufacturer_id: string;
  category_code: string;
  name: string;
  release_year?: number | null;
}

export interface DeviceModelUpdate {
  category_code?: string | null;
  name?: string | null;
  release_year?: number | null;
  is_active?: boolean | null;
}

export interface ManufacturerUpdate {
  name?: string | null;
  is_active?: boolean | null;
}

export interface Device {
  id: string;
  customer_id: string;
  model: DeviceModel;
  serial_number: string | null;
  imei: string | null;
  operating_system: string | null;
  storage: string | null;
  color: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeviceSearchItem extends Device {
  customer_name: string;
}

export interface DeviceCreate {
  model_id: string;
  serial_number?: string | null;
  imei?: string | null;
  operating_system?: string | null;
  storage?: string | null;
  color?: string | null;
  notes?: string | null;
}

export interface DeviceUpdate {
  model_id?: string | null;
  serial_number?: string | null;
  imei?: string | null;
  operating_system?: string | null;
  storage?: string | null;
  color?: string | null;
  notes?: string | null;
  is_active?: boolean | null;
}
