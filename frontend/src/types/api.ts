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
  warranty_days: number;
  assembly_bottleneck_gap: number;
  assembly_min_ram_gb: number;
  assembly_margin_percent: string;
}

export interface OrganizationUpdate {
  warranty_days?: number | null;
  assembly_bottleneck_gap?: number | null;
  assembly_min_ram_gb?: number | null;
  assembly_margin_percent?: string | null;
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
  /** SERVICE = reparación; ASSEMBLY = PC armada a la medida. */
  kind: "SERVICE" | "ASSEMBLY";
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
  balance_reason?: string | null;
  warranty_days?: number | null;
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

// --- Inventory (Sprint 5) ---------------------------------------------------------------

export const PART_KINDS = ["PART", "COMPONENT", "ACCESSORY", "CONSUMABLE"] as const;
export type PartKind = (typeof PART_KINDS)[number];

export interface PartItem {
  id: string;
  sku: string;
  name: string;
  kind: PartKind;
  /** Null unless the user manages the inventory. */
  unit_cost: string | null;
  sale_price: string;
  tax_rate: number;
  price_includes_tax: boolean;
  min_stock: number;
  notes: string | null;
  is_active: boolean;
  stock: number;
  low_stock: boolean;
  assembly_category: AssemblyCategory | null;
  specs: Record<string, unknown> | null;
  /** Assembly parts: sale price fixed by hand (otherwise cost + margin). */
  price_locked: boolean;
}

export interface PartWrite {
  sku: string;
  name: string;
  kind: PartKind;
  unit_cost: string;
  sale_price: string;
  tax_rate: 0 | 19;
  price_includes_tax: boolean;
  min_stock: number;
  notes?: string | null;
  is_active: boolean;
  /** Omitted = unchanged. */
  assembly_category?: AssemblyCategory | null;
  specs?: Record<string, unknown> | null;
  price_locked?: boolean | null;
}

export interface Supplier {
  id: string;
  name: string;
  tax_id: string | null;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
}

export interface SupplierWrite {
  name: string;
  tax_id?: string | null;
  contact_name?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active?: boolean;
}

export interface StockEntryCreate {
  supplier_id?: string | null;
  invoice_number?: string | null;
  received_on: string;
  notes?: string | null;
  lines: { part_id: string; quantity: number; unit_cost: string }[];
}

export interface StockEntry {
  id: string;
  supplier: string | null;
  invoice_number: string | null;
  received_on: string;
  lines: number;
  total_cost: string;
}

export const MOVEMENT_KINDS = ["IN", "OUT", "ADJUSTMENT", "RETURN"] as const;
export type MovementKind = (typeof MOVEMENT_KINDS)[number];

export interface Movement {
  id: string;
  kind: MovementKind;
  quantity: number;
  stock_after: number;
  unit_cost: string | null;
  reference_type: string | null;
  reference_id: string | null;
  reference_label: string | null;
  reason: string | null;
  created_by: PersonRef | null;
  created_at: string;
}

// --- Quotations ---------------------------------------------------------------------------

export const QUOTE_STATUSES = [
  "DRAFT",
  "SENT",
  "ACCEPTED",
  "REJECTED",
  "SUPERSEDED",
  "EXPIRED",
] as const;
export type QuoteStatus = (typeof QUOTE_STATUSES)[number];

export interface QuoteItemInput {
  kind: "LABOR" | "PART";
  part_id?: string | null;
  description?: string | null;
  quantity: string;
  unit_price: string;
  discount_percent?: string;
  apply_tax?: boolean;
  price_includes_tax?: boolean;
}

export interface QuoteItem {
  id: string;
  position: number;
  kind: "LABOR" | "PART";
  part_id: string | null;
  sku: string | null;
  in_stock: number | null;
  description: string;
  quantity: string;
  unit_price: string;
  discount_percent: string;
  tax_rate: number;
  price_includes_tax: boolean;
  discount_amount: string;
  base_amount: string;
  tax_amount: string;
  total_amount: string;
}

export interface Quote {
  id: string;
  version: number;
  status: QuoteStatus;
  valid_until: string | null;
  notes: string | null;
  subtotal: string;
  discount_total: string;
  tax_total: string;
  total: string;
  discount_authorized_by: PersonRef | null;
  created_by: PersonRef | null;
  created_at: string;
  sent_at: string | null;
  responded_at: string | null;
  response_channel: ConsentChannel | null;
  items: QuoteItem[];
}

export interface QuoteOverview {
  diagnostic_fee: string;
  quotes: Quote[];
  can_edit: boolean;
  can_send: boolean;
  can_respond: boolean;
  max_discount_percent: number;
}

// --- Repairs and quality control ----------------------------------------------------------

export interface RepairPartUsed {
  id: string;
  part_id: string;
  sku: string;
  name: string;
  quantity: number;
  unit_cost: string;
  returned: boolean;
}

export interface RepairTask {
  id: string;
  description: string;
  labor_minutes: number | null;
  technician: PersonRef | null;
  created_at: string;
  parts: RepairPartUsed[];
}

export interface QualityCheck {
  id: string;
  passed: boolean;
  results: {
    test_code: string;
    name: string;
    result: DiagnosticResultCode;
    observation: string | null;
  }[];
  notes: string | null;
  checked_by: PersonRef | null;
  checked_at: string;
}

export interface RepairOverview {
  tasks: RepairTask[];
  quality_checks: QualityCheck[];
  qc_tests: { test_code: string; name: string }[];
  can_repair: boolean;
  can_check: boolean;
}

// --- Payments -------------------------------------------------------------------------------

export interface PaymentItem {
  id: string;
  receipt_number: string | null;
  kind: "ADVANCE" | "PAYMENT";
  amount: string;
  method: PaymentMethod;
  reference: string | null;
  notes: string | null;
  received_by: PersonRef | null;
  paid_at: string;
}

export interface Billing {
  diagnostic_fee: string;
  accepted_quote_total: string | null;
  amount_due: string;
  paid: string;
  balance: string;
  payments: PaymentItem[];
  can_register: boolean;
}

// --- Warranties, dashboard and reports (Sprint 6) -------------------------------------

export interface Warranty {
  id: string;
  work_order_id: string;
  work_order_number: string;
  days: number;
  starts_on: string;
  ends_on: string;
  active: boolean;
}

export interface WarrantyClaim {
  id: string;
  claim_order_id: string;
  claim_order_number: string;
  reported_issue: string;
  status: "OPEN" | "ACCEPTED" | "REJECTED";
  resolution: string | null;
  decided_by: PersonRef | null;
  decided_at: string | null;
  created_at: string;
}

export interface WarrantyOverview {
  warranty: Warranty | null;
  claims: WarrantyClaim[];
  is_claim_order: boolean;
  can_claim: boolean;
  can_decide: boolean;
}

export interface ClaimCreate {
  reported_issue: string;
  physical_condition: string;
  accessories?: AccessoryItem[];
  unlock_method: UnlockMethod;
}

export interface Dashboard {
  scope: "WORKSHOP" | "MINE";
  open_by_status: { status: WorkOrderStatus; count: number }[];
  received_today: number;
  received_week: number;
  overdue: number;
  awaiting_customer: number;
  expired_quotes: number;
  ready_for_delivery: number;
  ready_balance: string | null;
  income_month: { method: PaymentMethod; amount: string }[] | null;
  income_month_total: string | null;
  avg_turnaround_days: number | null;
  technician_load: { technician: PersonRef | null; open_orders: number }[] | null;
  low_stock: number | null;
  warranties_expiring: number | null;
  open_claims: number | null;
}

export const REPORT_KINDS = ["income", "orders", "inventory", "technicians"] as const;
export type ReportKind = (typeof REPORT_KINDS)[number];

export interface Report {
  kind: ReportKind;
  title: string;
  date_from: string;
  date_to: string;
  columns: string[];
  rows: string[][];
  summary: [string, string][];
  /** Column indexes holding peso amounts (plain numbers, for Excel). */
  money_columns: number[];
}

// --- PC assembly (Sprint E1) ---------------------------------------------------------

/** PC parts (the configurator tabs). */
export const PC_CATEGORIES = [
  "CPU",
  "BOARD",
  "RAM",
  "GPU",
  "STORAGE",
  "PSU",
  "CASE",
  "COOLER",
  "RGB",
] as const;
/** Setup sold with the PC in the same order. */
export const SETUP_CATEGORIES = [
  "MONITOR",
  "KEYBOARD",
  "MOUSE",
  "PAD",
  "HEADSET",
  "MIC",
  "SPEAKER",
  "CAMERA",
  "STREAM",
  "CHAIR",
  "DESK",
  "LIGHT",
] as const;
export const ASSEMBLY_CATEGORIES = [...PC_CATEGORIES, ...SETUP_CATEGORIES] as const;
export type AssemblyCategory = (typeof ASSEMBLY_CATEGORIES)[number];
export type DeskShape = "STRAIGHT" | "L";
export type PcPosition = "AUTO" | "DESK" | "FLOOR";

export const USE_PROFILES = ["OFFICE", "DESIGN", "GAMING"] as const;
export type UseProfile = (typeof USE_PROFILES)[number];

export interface CatalogPart {
  id: string;
  sku: string;
  name: string;
  category: AssemblyCategory;
  sale_price: string;
  stock: number;
  specs: Record<string, unknown>;
}

export interface Selection {
  cpu?: string | null;
  board?: string | null;
  ram?: string | null;
  ram_units: number;
  gpu?: string | null;
  psu?: string | null;
  case?: string | null;
  cooler?: string | null;
  storage: string[];
  rgb: string[];
  monitor?: string[];
  keyboard?: string | null;
  mouse?: string | null;
  pad?: string | null;
  headset?: string | null;
  mic?: string[];
  speaker?: string | null;
  camera?: string | null;
  stream?: string[];
  chair?: string | null;
  desk?: string | null;
  light?: string[];
  desk_shape?: DeskShape;
  pc_position?: PcPosition;
}

export interface EvaluateRequest {
  selection: Selection;
  profile: UseProfile;
  candidates_for?: AssemblyCategory | null;
}

export interface AssemblyIssue {
  message: string;
  categories: AssemblyCategory[];
}

export interface Evaluation {
  errors: AssemblyIssue[];
  warnings: AssemblyIssue[];
  missing: AssemblyCategory[];
  ready: boolean;
  watts: number;
  recommended_psu_w: number;
  price: string;
  /** Monitors, peripherals and furniture of the setup. */
  setup_price: string;
  gaming_index: number;
  work_index: number;
  ram_gb: number;
  /** Part id → why it does not fit the current selection. */
  candidates: Record<string, string>;
}

export interface BuildSummary {
  id: string;
  name: string;
  profile: UseProfile;
  status: "DRAFT" | "ORDERED";
  price: string;
  work_order_id: string | null;
  work_order_number: string | null;
  updated_at: string;
}

export interface BuildRead extends BuildSummary {
  selection: Selection;
  labor_price: string;
  notes: string | null;
  created_by: PersonRef | null;
  evaluation: Evaluation;
  editable: boolean;
}

export interface BuildWrite {
  name: string;
  profile: UseProfile;
  selection: Selection;
  labor_price: string;
  notes?: string | null;
}

export interface AssemblyStep {
  code: string;
  title: string;
  done: boolean;
  blocked_reason: string | null;
}

export interface AssemblyChecklist {
  build_id: string;
  build_name: string;
  steps: AssemblyStep[];
  parts_consumed: boolean;
  can_work: boolean;
}

export interface CatalogImportItem {
  sku: string;
  name: string;
  category: AssemblyCategory;
  /** Supplier price, VAT included. */
  cost: string;
  specs: Record<string, unknown>;
}

export interface CatalogImportResult {
  created: number;
  updated: number;
  errors: string[];
}

export interface CostUpdateResult {
  updated: number;
  unchanged: number;
  unknown: string[];
  errors: string[];
}

// --- Customer notices by WhatsApp (post-MVP sprint 3) -----------------------------------

export type NoticeKind =
  "RECEIVED" | "QUOTE_READY" | "READY" | "NOT_REPAIRED" | "REMINDER" | "DELIVERED" | "FREE";

export interface NoticeDraft {
  kind: NoticeKind;
  label: string;
  body: string;
}

export interface NoticeRead {
  id: string;
  kind: NoticeKind;
  label: string;
  phone: string;
  body: string;
  prepared_by: PersonRef | null;
  prepared_at: string;
}

export interface NoticePanel {
  phone: string | null;
  can_whatsapp: boolean;
  blocked_reason: string | null;
  can_prepare: boolean;
  suggested: NoticeKind;
  pending: boolean;
  drafts: NoticeDraft[];
  history: NoticeRead[];
}

export interface PreparedNotice {
  notice: NoticeRead;
  url: string;
}

export interface PendingNotice {
  work_order_id: string;
  number: string;
  customer_name: string;
  status: WorkOrderStatus;
  kind: NoticeKind;
  label: string;
  since: string;
  can_whatsapp: boolean;
}

export interface NoticeTemplate {
  kind: NoticeKind;
  label: string;
  body: string;
  default_body: string;
  is_default: boolean;
}

export interface NoticeTemplates {
  templates: NoticeTemplate[];
  placeholders: { name: string; description: string }[];
  reminder_days: number;
}
