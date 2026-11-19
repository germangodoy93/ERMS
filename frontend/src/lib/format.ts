const dateTimeFormatter = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "America/Bogota",
});

/** Formats a UTC ISO timestamp in Colombian local time; "—" when empty. */
export function formatDateTime(isoUtc: string | null | undefined): string {
  return isoUtc ? dateTimeFormatter.format(new Date(isoUtc)) : "—";
}

/** Colombian numbers (+57) are shown as "300 123 4567"; others keep their E.164 form. */
export function formatPhone(e164: string | null | undefined): string {
  if (!e164) return "—";
  const match = /^\+57(\d{3})(\d{3})(\d{4})$/.exec(e164);
  return match ? `${match[1]} ${match[2]} ${match[3]}` : e164;
}
