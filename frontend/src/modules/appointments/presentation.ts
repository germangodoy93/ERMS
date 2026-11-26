import type { AppointmentRead, ConsentChannelCode, HoursDay, Modality } from "@/types/api";

export const MODALITY_LABELS: Record<Modality, string> = {
  REMOTE: "Remota",
  ON_SITE: "En sitio",
};

export const CONSENT_CHANNEL_LABELS: Record<ConsentChannelCode, string> = {
  SCREEN: "En pantalla",
  PAPER: "Firmada en papel",
  VERBAL: "Verbal (por teléfono)",
};

export const WEEKDAY_LABELS = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
] as const;

// Dates travel as "YYYY-MM-DD" (Bogotá calendar). Bogotá has no daylight saving: UTC-5.
const BOGOTA_OFFSET_MS = 5 * 60 * 60 * 1000;

function parseDay(date: string): Date {
  const [y = 0, m = 1, d = 1] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export function addDays(date: string, days: number): string {
  const day = parseDay(date);
  day.setUTCDate(day.getUTCDate() + days);
  return day.toISOString().slice(0, 10);
}

/** 0 = Monday … 6 = Sunday, like the backend. */
export function weekdayOf(date: string): number {
  return (parseDay(date).getUTCDay() + 6) % 7;
}

export function weekStart(date: string): string {
  return addDays(date, -weekdayOf(date));
}

/** Bogotá calendar date of a UTC timestamp. */
export function bogotaDate(iso: string): string {
  return new Date(new Date(iso).getTime() - BOGOTA_OFFSET_MS).toISOString().slice(0, 10);
}

/** Bogotá wall-clock time ("HH:MM") of a UTC timestamp. */
export function bogotaTime(iso: string): string {
  return new Date(new Date(iso).getTime() - BOGOTA_OFFSET_MS).toISOString().slice(11, 16);
}

/** "2026-11-30" + "09:30" → "2026-11-30T09:30:00-05:00". */
export function toBogotaIso(date: string, time: string): string {
  return `${date}T${time}:00-05:00`;
}

const dayTitle = new Intl.DateTimeFormat("es-CO", {
  weekday: "long",
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

export function formatDayTitle(date: string): string {
  const text = dayTitle.format(parseDay(date));
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** "08:00:00" → "8:00". */
export function shortTime(value: string): string {
  const [h = "0", m = "00"] = value.split(":");
  return `${Number(h)}:${m}`;
}

export function hoursLabel(day: HoursDay | undefined): string {
  if (!day?.opens || !day.closes) return "Sin servicio";
  return `${shortTime(day.opens)} a ${shortTime(day.closes)}`;
}

export function timeRange(appointment: AppointmentRead): string {
  const start = shortTime(bogotaTime(appointment.starts_at));
  return `${start} – ${shortTime(bogotaTime(appointment.ends_at))}`;
}

/** Appointments of each day of the range, in time order. */
export function groupByDay(
  appointments: AppointmentRead[],
  days: string[],
): Map<string, AppointmentRead[]> {
  const groups = new Map(days.map((d) => [d, [] as AppointmentRead[]]));
  const sorted = [...appointments].sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  for (const appointment of sorted) {
    groups.get(bogotaDate(appointment.starts_at))?.push(appointment);
  }
  return groups;
}

export function durationLabel(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${m} min` : `${h} h`;
}
