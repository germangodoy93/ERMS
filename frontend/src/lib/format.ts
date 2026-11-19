const dateTimeFormatter = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "America/Bogota",
});

/** Formats a UTC ISO timestamp in Colombian local time; "—" when empty. */
export function formatDateTime(isoUtc: string | null | undefined): string {
  return isoUtc ? dateTimeFormatter.format(new Date(isoUtc)) : "—";
}
