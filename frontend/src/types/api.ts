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

// --- Work orders (Sprint 3) ----------------------------------------------------------

export const WORK_ORDER_STATUSES = [
  "RECIBIDO",
  "INSPECCION",
  "DIAGNOSTICO",
  "COTIZACION",
  "PENDIENTE_AUTORIZACION",
  "APROBADO",
  "COTIZACION_RECHAZADA",
  "EN_REPARACION",
  "CONTROL_CALIDAD",
  "LISTO_ENTREGA",
  "ENTREGADO",
  "CANCELADO",
  "NO_REPARABLE",
] as const;
export type WorkOrderStatus = (typeof WORK_ORDER_STATUSES)[number];

export const PRIORITIES = ["NORMAL", "HIGH", "URGENT"] as const;
export type Priority = (typeof PRIORITIES)[number];

export const UNLOCK_METHODS = ["NOT_REQUIRED", "CUSTOMER_IN_PERSON", "CUSTOMER_UNLOCKS"] as const;
export type UnlockMethod = (typeof UNLOCK_METHODS)[number];

export const ACCESSORIES = [
  "CHARGER",
  "CABLE",
  "CASE",
  "BATTERY",
  "SIM",
  "SD_CARD",
  "CONTROLLER",
  "BOX",
  "OTHER",
] as const;
export type AccessoryCode = (typeof ACCESSORIES)[number];

export const PAYMENT_METHODS = ["CASH", "TRANSFER", "CARD", "NEQUI", "DAVIPLATA"] as const;
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

export interface AccessoryItem {
  code: AccessoryCode;
  detail?: string | null;
}

export interface PersonRef {
  id: string;
  full_name: string;
}

export interface WorkOrderCustomer {
  id: string;
  full_name: string;
  phone: string | null;
  id_type: string | null;
  id_number: string | null;
}

export interface WorkOrderDevice {
  id: string;
  category: string;
  manufacturer: string;
  model: string;
  imei: string | null;
  serial_number: string | null;
}

export interface WorkOrderListItem {
  id: string;
  number: string;
  status: WorkOrderStatus;
  priority: Priority;
  received_at: string;
  estimated_delivery_date: string | null;
  customer: WorkOrderCustomer;
  device: WorkOrderDevice;
  assigned_technician: PersonRef | null;
}

export interface StatusHistoryItem {
  from_status: WorkOrderStatus | null;
  to_status: WorkOrderStatus;
  reason: string | null;
  changed_by: PersonRef | null;
  changed_at: string;
}

export interface WorkOrder extends WorkOrderListItem {
  branch: string;
  reported_issue: string;
  physical_condition: string;
  accessories: AccessoryItem[];
  unlock_method: UnlockMethod;
  /** Decimal string with two places, e.g. "50000.00". */
  diagnostic_fee: string;
  advance_amount: string;
  advance_method: PaymentMethod | null;
  notes: string | null;
  terms_version: number;
  received_by: PersonRef | null;
  delivered_at: string | null;
  delivered_to_name: string | null;
  delivered_to_document: string | null;
  history: StatusHistoryItem[];
  allowed_transitions: WorkOrderStatus[];
  customer_allows_photos: boolean;
  updated_at: string;
}

export interface WorkOrderCreate {
  customer_id: string;
  device_id: string;
  reported_issue: string;
  physical_condition: string;
  accessories?: AccessoryItem[];
  unlock_method: UnlockMethod;
  priority?: Priority;
  estimated_delivery_date?: string | null;
  diagnostic_fee?: string;
  advance_amount?: string;
  advance_method?: PaymentMethod | null;
  notes?: string | null;
  assigned_technician_id?: string | null;
}

export interface WorkOrderUpdate {
  reported_issue?: string | null;
  physical_condition?: string | null;
  priority?: Priority | null;
  estimated_delivery_date?: string | null;
  notes?: string | null;
}

export interface DeliveryRequest {
  picked_up_by_customer: boolean;
  name?: string | null;
  document?: string | null;
  notes?: string | null;
}

export interface ReceptionTerms {
  id: string;
  version: number;
  content: string;
  published_at: string;
}

export interface CurrentReceptionTerms {
  terms: ReceptionTerms | null;
  template: string;
}

export interface Photo {
  id: string;
  file_name: string;
  size_bytes: number;
  created_at: string;
}

export interface PhotoList {
  demo: boolean;
  max_photos: number;
  items: Photo[];
}

// --- Diagnostics (Sprint 4) -----------------------------------------------------------

export const DIAGNOSTIC_RESULTS = ["OK", "WARNING", "FAIL", "NOT_TESTED", "NOT_SUPPORTED"] as const;
export type DiagnosticResultCode = (typeof DIAGNOSTIC_RESULTS)[number];

export const DIAGNOSTIC_SOURCES = ["MANUAL", "AGENT", "AI_SUGGESTION"] as const;
export type DiagnosticSource = (typeof DIAGNOSTIC_SOURCES)[number];

export interface DiagnosticTestResult {
  test_code: string;
  name: string;
  component: string;
  automated: boolean;
  result: DiagnosticResultCode | null;
  observation: string | null;
  evidence: Record<string, unknown> | null;
  source: DiagnosticSource | null;
  recorded_by: PersonRef | null;
  recorded_at: string | null;
}

export interface Diagnostic {
  session_id: string | null;
  state: "NOT_STARTED" | "OPEN" | "CLOSED";
  editable: boolean;
  agent_available: boolean;
  agent_unavailable_reason: string | null;
  agent_download_url: string;
  conclusion: string | null;
  recommendation: string | null;
  closed_at: string | null;
  closed_by: PersonRef | null;
  agent_version: string | null;
  agent_elevated: boolean | null;
  agent_reported_at: string | null;
  results: DiagnosticTestResult[];
}

export interface DiagnosticResultInput {
  test_code: string;
  result: DiagnosticResultCode;
  observation?: string | null;
}

export interface AgentPairing {
  code: string;
  expires_at: string;
  download_url: string;
}
