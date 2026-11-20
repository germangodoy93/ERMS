import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  ACCESSORIES,
  COMPONENT_STATUSES,
  CONSENT_CHANNELS,
  CONSENT_PURPOSES,
  CUSTOMER_KINDS,
  ID_TYPES,
  OVERALL_STATUSES,
  PAYMENT_METHODS,
  PRIORITIES,
  UNLOCK_METHODS,
  WORK_ORDER_STATUSES,
} from "./api";

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
  OrganizationRead: {
    all: ["address", "city", "email", "id", "legal_name", "name", "phone", "slug", "tax_id"],
    required: ["address", "city", "email", "id", "legal_name", "name", "phone", "slug", "tax_id"],
  },
  OrganizationUpdate: {
    all: ["address", "city", "email", "legal_name", "name", "phone", "tax_id"],
    required: [],
  },
  PrivacyPolicyRead: {
    all: ["content", "id", "published_at", "version"],
    required: ["content", "id", "published_at", "version"],
  },
  PrivacyPolicyVersion: {
    all: ["id", "published_at", "version"],
    required: ["id", "published_at", "version"],
  },
  CurrentPrivacyPolicy: {
    all: ["authorizations", "policy"],
    required: ["authorizations", "policy"],
  },
  PrivacyPolicyDraft: {
    all: ["content", "missing_fields"],
    required: ["content", "missing_fields"],
  },
  ConsentStatus: {
    all: ["channel", "granted", "policy_version", "purpose", "recorded_at"],
    required: ["channel", "granted", "policy_version", "purpose", "recorded_at"],
  },
  ConsentRecordRead: {
    all: ["channel", "granted", "id", "policy_version", "purpose", "recorded_at", "recorded_by"],
    required: [
      "channel",
      "granted",
      "id",
      "policy_version",
      "purpose",
      "recorded_at",
      "recorded_by",
    ],
  },
  ConsentGrant: { all: ["channel", "purpose"], required: ["channel", "purpose"] },
  ConsentChange: {
    all: ["channel", "granted", "purpose"],
    required: ["channel", "granted", "purpose"],
  },
  CustomerListItem: {
    all: [
      "anonymized_at",
      "created_at",
      "email",
      "full_name",
      "id",
      "id_number",
      "id_type",
      "is_active",
      "kind",
      "phone",
    ],
    required: [
      "anonymized_at",
      "created_at",
      "email",
      "full_name",
      "id",
      "id_number",
      "id_type",
      "is_active",
      "kind",
      "phone",
    ],
  },
  CustomerRead: {
    all: [
      "address",
      "anonymized_at",
      "can_be_served",
      "consents",
      "created_at",
      "email",
      "full_name",
      "id",
      "id_number",
      "id_type",
      "is_active",
      "kind",
      "notes",
      "phone",
      "updated_at",
    ],
    required: [
      "address",
      "anonymized_at",
      "can_be_served",
      "consents",
      "created_at",
      "email",
      "full_name",
      "id",
      "id_number",
      "id_type",
      "is_active",
      "kind",
      "notes",
      "phone",
      "updated_at",
    ],
  },
  CustomerCreate: {
    all: [
      "address",
      "consents",
      "email",
      "full_name",
      "id_number",
      "id_type",
      "kind",
      "notes",
      "phone",
    ],
    required: ["consents", "full_name"],
  },
  CustomerUpdate: {
    all: [
      "address",
      "email",
      "full_name",
      "id_number",
      "id_type",
      "is_active",
      "kind",
      "notes",
      "phone",
    ],
    required: [],
  },
  CategoryRead: { all: ["code", "name"], required: ["code", "name"] },
  ManufacturerRead: { all: ["id", "is_active", "name"], required: ["id", "is_active", "name"] },
  ManufacturerUpdate: { all: ["is_active", "name"], required: [] },
  DeviceModelRead: {
    all: ["category", "id", "is_active", "manufacturer", "name", "release_year"],
    required: ["category", "id", "is_active", "manufacturer", "name", "release_year"],
  },
  DeviceModelCreate: {
    all: ["category_code", "manufacturer_id", "name", "release_year"],
    required: ["category_code", "manufacturer_id", "name"],
  },
  DeviceModelUpdate: { all: ["category_code", "is_active", "name", "release_year"], required: [] },
  DeviceRead: {
    all: [
      "color",
      "created_at",
      "customer_id",
      "id",
      "imei",
      "is_active",
      "model",
      "notes",
      "operating_system",
      "serial_number",
      "storage",
      "updated_at",
    ],
    required: [
      "color",
      "created_at",
      "customer_id",
      "id",
      "imei",
      "is_active",
      "model",
      "notes",
      "operating_system",
      "serial_number",
      "storage",
      "updated_at",
    ],
  },
  DeviceSearchItem: {
    all: [
      "color",
      "created_at",
      "customer_id",
      "customer_name",
      "id",
      "imei",
      "is_active",
      "model",
      "notes",
      "operating_system",
      "serial_number",
      "storage",
      "updated_at",
    ],
    required: [
      "color",
      "created_at",
      "customer_id",
      "customer_name",
      "id",
      "imei",
      "is_active",
      "model",
      "notes",
      "operating_system",
      "serial_number",
      "storage",
      "updated_at",
    ],
  },
  DeviceCreate: {
    all: ["color", "imei", "model_id", "notes", "operating_system", "serial_number", "storage"],
    required: ["model_id"],
  },
  DeviceUpdate: {
    all: [
      "color",
      "imei",
      "is_active",
      "model_id",
      "notes",
      "operating_system",
      "serial_number",
      "storage",
    ],
    required: [],
  },
  WorkOrderListItem: {
    all: [
      "assigned_technician",
      "customer",
      "device",
      "estimated_delivery_date",
      "id",
      "number",
      "priority",
      "received_at",
      "status",
    ],
    required: [
      "assigned_technician",
      "customer",
      "device",
      "estimated_delivery_date",
      "id",
      "number",
      "priority",
      "received_at",
      "status",
    ],
  },
  WorkOrderRead: {
    all: [
      "accessories",
      "advance_amount",
      "advance_method",
      "allowed_transitions",
      "assigned_technician",
      "branch",
      "customer",
      "customer_allows_photos",
      "delivered_at",
      "delivered_to_document",
      "delivered_to_name",
      "device",
      "diagnostic_fee",
      "estimated_delivery_date",
      "history",
      "id",
      "notes",
      "number",
      "physical_condition",
      "priority",
      "received_at",
      "received_by",
      "reported_issue",
      "status",
      "terms_version",
      "unlock_method",
      "updated_at",
    ],
    required: [
      "accessories",
      "advance_amount",
      "advance_method",
      "allowed_transitions",
      "assigned_technician",
      "branch",
      "customer",
      "customer_allows_photos",
      "delivered_at",
      "delivered_to_document",
      "delivered_to_name",
      "device",
      "diagnostic_fee",
      "estimated_delivery_date",
      "history",
      "id",
      "notes",
      "number",
      "physical_condition",
      "priority",
      "received_at",
      "received_by",
      "reported_issue",
      "status",
      "terms_version",
      "unlock_method",
      "updated_at",
    ],
  },
  WorkOrderCreate: {
    all: [
      "accessories",
      "advance_amount",
      "advance_method",
      "assigned_technician_id",
      "customer_id",
      "device_id",
      "diagnostic_fee",
      "estimated_delivery_date",
      "notes",
      "physical_condition",
      "priority",
      "reported_issue",
      "unlock_method",
    ],
    required: ["customer_id", "device_id", "physical_condition", "reported_issue", "unlock_method"],
  },
  WorkOrderUpdate: {
    all: ["estimated_delivery_date", "notes", "physical_condition", "priority", "reported_issue"],
    required: [],
  },
  StatusHistoryItem: {
    all: ["changed_at", "changed_by", "from_status", "reason", "to_status"],
    required: ["changed_at", "changed_by", "from_status", "reason", "to_status"],
  },
  AccessoryItem: { all: ["code", "detail"], required: ["code"] },
  PersonRef: { all: ["full_name", "id"], required: ["full_name", "id"] },
  CustomerSummary: {
    all: ["full_name", "id", "id_number", "id_type", "phone"],
    required: ["full_name", "id", "id_number", "id_type", "phone"],
  },
  DeviceSummary: {
    all: ["category", "id", "imei", "manufacturer", "model", "serial_number"],
    required: ["category", "id", "imei", "manufacturer", "model", "serial_number"],
  },
  DeliveryRequest: {
    all: ["document", "name", "notes", "picked_up_by_customer"],
    required: ["picked_up_by_customer"],
  },
  CurrentReceptionTerms: { all: ["template", "terms"], required: ["template", "terms"] },
  ReceptionTermsRead: {
    all: ["content", "id", "published_at", "version"],
    required: ["content", "id", "published_at", "version"],
  },
  PhotoRead: {
    all: ["created_at", "file_name", "id", "size_bytes"],
    required: ["created_at", "file_name", "id", "size_bytes"],
  },
  PhotoList: { all: ["demo", "items", "max_photos"], required: ["demo", "items", "max_photos"] },
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
        "/api/v1/organization",
        "/api/v1/privacy-policy",
        "/api/v1/privacy-policy/draft",
        "/api/v1/privacy-policy/versions/{version}",
        "/api/v1/customers",
        "/api/v1/customers/{customer_id}",
        "/api/v1/customers/{customer_id}/consents",
        "/api/v1/customers/{customer_id}/anonymize",
        "/api/v1/customers/{customer_id}/devices",
        "/api/v1/devices",
        "/api/v1/devices/{device_id}",
        "/api/v1/catalog/categories",
        "/api/v1/catalog/manufacturers",
        "/api/v1/catalog/manufacturers/{manufacturer_id}",
        "/api/v1/catalog/models",
        "/api/v1/catalog/models/{model_id}",
        "/api/v1/reception-terms",
        "/api/v1/work-orders",
        "/api/v1/work-orders/technicians",
        "/api/v1/work-orders/{order_id}",
        "/api/v1/work-orders/{order_id}/assignment",
        "/api/v1/work-orders/{order_id}/status",
        "/api/v1/work-orders/{order_id}/delivery",
        "/api/v1/work-orders/{order_id}/reception-act.pdf",
        "/api/v1/work-orders/{order_id}/photos",
        "/api/v1/work-orders/{order_id}/photos/{attachment_id}",
      ]),
    );
  });

  it("keeps status enums in sync", () => {
    expect(schema("ComponentStatus").enum).toEqual([...COMPONENT_STATUSES]);
    expect(schema("OverallStatus").enum).toEqual([...OVERALL_STATUSES]);
    expect(schema("ConsentPurpose").enum).toEqual([...CONSENT_PURPOSES]);
    expect(schema("ConsentChannel").enum).toEqual([...CONSENT_CHANNELS]);
    expect(schema("IdType").enum).toEqual([...ID_TYPES]);
    expect(schema("CustomerKind").enum).toEqual([...CUSTOMER_KINDS]);
    expect(schema("Status").enum).toEqual([...WORK_ORDER_STATUSES]);
    expect(schema("Priority").enum).toEqual([...PRIORITIES]);
    expect(schema("UnlockMethod").enum).toEqual([...UNLOCK_METHODS]);
    expect(schema("Accessory").enum).toEqual([...ACCESSORIES]);
    expect(schema("PaymentMethod").enum).toEqual([...PAYMENT_METHODS]);
  });

  it.each(Object.entries(FIELDS))("keeps %s fields in sync", (name, fields) => {
    const s = schema(name);
    expect(Object.keys(s.properties ?? {}).sort()).toEqual([...fields.all].sort());
    expect((s.required ?? []).slice().sort()).toEqual([...fields.required].sort());
  });
});
