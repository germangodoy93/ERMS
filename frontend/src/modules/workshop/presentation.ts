import type { MovementKind, PartKind, QuoteStatus } from "@/types/api";

export const QUOTE_STATUS_LABELS: Record<QuoteStatus, string> = {
  DRAFT: "Borrador",
  SENT: "Enviada",
  ACCEPTED: "Aprobada",
  REJECTED: "Rechazada",
  SUPERSEDED: "Reemplazada",
  EXPIRED: "Vencida",
};

export const QUOTE_STATUS_TONE: Record<QuoteStatus, string> = {
  DRAFT: "border-border bg-muted text-muted-foreground",
  SENT: "border-warning/50 bg-warning/15 text-foreground",
  ACCEPTED: "border-success/40 bg-success/10 text-success",
  REJECTED: "border-destructive/40 bg-destructive/10 text-destructive",
  SUPERSEDED: "border-border bg-muted text-muted-foreground",
  EXPIRED: "border-destructive/40 bg-destructive/10 text-destructive",
};

export const PART_KIND_LABELS: Record<PartKind, string> = {
  PART: "Repuesto",
  COMPONENT: "Componente",
  ACCESSORY: "Accesorio",
  CONSUMABLE: "Consumible",
};

export const MOVEMENT_LABELS: Record<MovementKind, string> = {
  IN: "Entrada",
  OUT: "Salida",
  ADJUSTMENT: "Ajuste",
  RETURN: "Devolución",
};

/** Positive balance: the customer owes; negative: money in favour of the customer. */
export function balanceLabel(balance: string): string {
  const value = Number(balance);
  if (value > 0) return "Saldo pendiente";
  if (value < 0) return "Saldo a favor del cliente";
  return "Pagado";
}
