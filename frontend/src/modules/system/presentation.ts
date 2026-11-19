/** Presentation mapping for system health: labels and visual tones (no business rules). */
import type { ComponentStatus, OverallStatus } from "@/types/api";

export type Tone = "success" | "danger" | "neutral";

const COMPONENT_LABELS: Record<string, string> = {
  database: "Base de datos (PostgreSQL)",
  redis: "Redis (tareas en segundo plano)",
};

export function componentLabel(name: string): string {
  return COMPONENT_LABELS[name] ?? name;
}

export const COMPONENT_STATUS_PRESENTATION: Record<ComponentStatus, { label: string; tone: Tone }> =
  {
    ok: { label: "Operativo", tone: "success" },
    error: { label: "Con fallas", tone: "danger" },
    not_configured: { label: "No configurado", tone: "neutral" },
  };

export const OVERALL_STATUS_PRESENTATION: Record<
  OverallStatus,
  { title: string; description: string; tone: Tone }
> = {
  ok: {
    title: "Sistema operativo",
    description: "Todos los componentes críticos responden correctamente.",
    tone: "success",
  },
  unavailable: {
    title: "Servicio no disponible",
    description: "Al menos un componente crítico presenta fallas.",
    tone: "danger",
  },
};

const ENVIRONMENT_LABELS: Record<string, string> = {
  development: "Desarrollo",
  test: "Pruebas",
  production: "Producción",
};

export function environmentLabel(environment: string): string {
  return ENVIRONMENT_LABELS[environment] ?? environment;
}

const dateTimeFormatter = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "medium",
  timeStyle: "medium",
  timeZone: "America/Bogota",
});

/** Formats a UTC ISO timestamp in Colombian local time. */
export function formatBogotaDateTime(isoUtc: string): string {
  return dateTimeFormatter.format(new Date(isoUtc));
}

export function formatLatency(latencyMs: number | null | undefined): string | null {
  if (latencyMs === null || latencyMs === undefined) return null;
  return `${latencyMs.toLocaleString("es-CO", { maximumFractionDigits: 1 })} ms`;
}
