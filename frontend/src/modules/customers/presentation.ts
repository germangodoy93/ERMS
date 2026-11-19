import type {
  ConsentChannel,
  ConsentPurpose,
  ConsentStatus,
  CustomerKind,
  CustomerListItem,
  IdType,
} from "@/types/api";

export const ID_TYPE_LABELS: Record<IdType, string> = {
  CC: "Cédula de ciudadanía",
  CE: "Cédula de extranjería",
  NIT: "NIT",
  PAS: "Pasaporte",
  TI: "Tarjeta de identidad",
  PPT: "Permiso por protección temporal",
};

export const KIND_LABELS: Record<CustomerKind, string> = {
  PERSON: "Persona",
  COMPANY: "Empresa",
};

export const PURPOSE_LABELS: Record<ConsentPurpose, string> = {
  DATA_PROCESSING: "Tratamiento de datos personales",
  PHOTOS: "Fotografías del equipo",
  DIAGNOSTIC_AGENT: "Agente de diagnóstico",
};

export const CHANNEL_LABELS: Record<ConsentChannel, string> = {
  SCREEN: "Aceptado en pantalla",
  PAPER: "Firmado en papel",
  VERBAL: "Verbal",
};

export function formatDocument(customer: Pick<CustomerListItem, "id_type" | "id_number">): string {
  return customer.id_type && customer.id_number ? `${customer.id_type} ${customer.id_number}` : "—";
}

export type CustomerState = "served" | "inactive" | "no_consent" | "anonymized";

export function customerState(
  customer: Pick<CustomerListItem, "is_active" | "anonymized_at"> & { can_be_served?: boolean },
): CustomerState {
  if (customer.anonymized_at) return "anonymized";
  if (!customer.is_active) return "inactive";
  if (customer.can_be_served === false) return "no_consent";
  return "served";
}

export const STATE_BADGES: Record<
  CustomerState,
  { tone: "success" | "danger" | "neutral"; label: string }
> = {
  served: { tone: "success", label: "Activo" },
  inactive: { tone: "neutral", label: "Inactivo" },
  no_consent: { tone: "danger", label: "Sin autorización" },
  anonymized: { tone: "neutral", label: "Anonimizado" },
};

/** Current state of every purpose, including the ones never asked. */
export function consentRows(
  consents: ConsentStatus[],
): { purpose: ConsentPurpose; status: ConsentStatus | null }[] {
  const byPurpose = new Map(consents.map((c) => [c.purpose, c]));
  return (Object.keys(PURPOSE_LABELS) as ConsentPurpose[]).map((purpose) => ({
    purpose,
    status: byPurpose.get(purpose) ?? null,
  }));
}
