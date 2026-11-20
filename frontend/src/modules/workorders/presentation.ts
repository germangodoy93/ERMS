import type {
  AccessoryCode,
  AccessoryItem,
  PaymentMethod,
  Priority,
  UnlockMethod,
  WorkOrderStatus,
} from "@/types/api";

/** Mirrors backend app/modules/workorders/catalog.py labels. */
export const STATUS_LABELS: Record<WorkOrderStatus, string> = {
  RECIBIDO: "Recibido",
  INSPECCION: "Inspección",
  DIAGNOSTICO: "Diagnóstico",
  COTIZACION: "Cotización",
  PENDIENTE_AUTORIZACION: "Pendiente de autorización",
  APROBADO: "Aprobado",
  COTIZACION_RECHAZADA: "Cotización rechazada",
  EN_REPARACION: "En reparación",
  CONTROL_CALIDAD: "Control de calidad",
  LISTO_ENTREGA: "Listo para entrega",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
  NO_REPARABLE: "No reparable",
};

/** Verb shown on the action button that moves the order to each state. */
export const TRANSITION_ACTIONS: Record<WorkOrderStatus, string> = {
  RECIBIDO: "Recibir",
  INSPECCION: "Iniciar inspección",
  DIAGNOSTICO: "Iniciar diagnóstico",
  COTIZACION: "Pasar a cotización",
  PENDIENTE_AUTORIZACION: "Enviar al cliente para autorización",
  APROBADO: "Cliente aprobó",
  COTIZACION_RECHAZADA: "Cliente rechazó",
  EN_REPARACION: "Iniciar reparación",
  CONTROL_CALIDAD: "Enviar a control de calidad",
  LISTO_ENTREGA: "Marcar listo para entrega",
  ENTREGADO: "Entregar equipo",
  CANCELADO: "Cancelar orden",
  NO_REPARABLE: "Marcar no reparable",
};

/** Mirrors backend catalog.reason_required. */
export function reasonRequired(from: WorkOrderStatus, to: WorkOrderStatus): boolean {
  return (
    to === "CANCELADO" ||
    to === "NO_REPARABLE" ||
    to === "COTIZACION_RECHAZADA" ||
    (from === "CONTROL_CALIDAD" && to === "EN_REPARACION")
  );
}

export const NEGATIVE_TRANSITIONS: ReadonlySet<WorkOrderStatus> = new Set([
  "CANCELADO",
  "NO_REPARABLE",
  "COTIZACION_RECHAZADA",
]);

export type StatusTone = "neutral" | "info" | "warning" | "success" | "danger";

export function statusTone(status: WorkOrderStatus): StatusTone {
  switch (status) {
    case "LISTO_ENTREGA":
    case "ENTREGADO":
      return "success";
    case "PENDIENTE_AUTORIZACION":
      return "warning";
    case "CANCELADO":
    case "NO_REPARABLE":
    case "COTIZACION_RECHAZADA":
      return "danger";
    case "RECIBIDO":
      return "neutral";
    default:
      return "info";
  }
}

export const PRIORITY_LABELS: Record<Priority, string> = {
  NORMAL: "Normal",
  HIGH: "Alta",
  URGENT: "Urgente",
};

export const UNLOCK_LABELS: Record<UnlockMethod, string> = {
  NOT_REQUIRED: "No requiere desbloqueo",
  CUSTOMER_IN_PERSON: "El cliente dará el código en persona al técnico",
  CUSTOMER_UNLOCKS: "El cliente desbloqueará el equipo cuando se requiera",
};

export const ACCESSORY_LABELS: Record<AccessoryCode, string> = {
  CHARGER: "Cargador",
  CABLE: "Cable",
  CASE: "Funda o estuche",
  BATTERY: "Batería",
  SIM: "Tarjeta SIM",
  SD_CARD: "Memoria SD",
  CONTROLLER: "Control",
  BOX: "Caja",
  OTHER: "Otro",
};

export const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  CASH: "Efectivo",
  TRANSFER: "Transferencia",
  CARD: "Tarjeta",
  NEQUI: "Nequi",
  DAVIPLATA: "Daviplata",
};

export function accessoriesText(items: AccessoryItem[]): string {
  if (items.length === 0) return "Ninguno";
  return items
    .map((a) => (a.detail ? `${ACCESSORY_LABELS[a.code]}: ${a.detail}` : ACCESSORY_LABELS[a.code]))
    .join(", ");
}

// Intl uses non-breaking spaces; plain spaces keep the text predictable in tests and PDFs.
const NON_BREAKING_SPACES = new RegExp(`[${String.fromCharCode(0xa0, 0x202f)}]`, "g");

const pesos = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});
const pesosWithCents = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  minimumFractionDigits: 2,
});

/** "50000.00" → "$ 50.000"; cents only when present: "$ 1.250.000,50". */
export function formatMoney(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = Number(value);
  const formatter = Number.isInteger(amount) ? pesos : pesosWithCents;
  return formatter.format(amount).replace(NON_BREAKING_SPACES, " ");
}

/** Accepts "50.000", "50000" or "50000,5" typed by the user; returns "50000.50" or null. */
export function parseMoney(input: string): string | null {
  const clean = input.replace(/[\s$]/g, "");
  if (!clean) return "0.00";
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$/.test(clean)) return null;
  const [integer = "0", decimals = ""] = clean.replace(/\./g, "").split(",");
  return `${Number(integer)}.${decimals.padEnd(2, "0")}`;
}

/** Bogotá calendar date (YYYY-MM-DD) of "now", for date inputs. */
export function todayInBogota(): string {
  const now = new Date(Date.now() - 5 * 60 * 60 * 1000);
  return now.toISOString().slice(0, 10);
}
