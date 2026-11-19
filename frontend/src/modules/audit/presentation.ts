/** Spanish labels for audit actions recorded by the backend. */
export const AUDIT_ACTION_LABELS: Record<string, string> = {
  "auth.login": "Inicio de sesión",
  "auth.login_failed": "Inicio de sesión fallido",
  "auth.logout": "Cierre de sesión",
  "auth.refresh_reuse_detected": "Reutilización de sesión detectada",
  "auth.password_reset_requested": "Solicitud de restablecimiento",
  "auth.password_reset": "Contraseña restablecida",
  "auth.password_changed": "Contraseña cambiada",
  "user.created": "Usuario creado",
  "user.updated": "Usuario actualizado",
  "user.roles_changed": "Roles modificados",
  "user.temporary_password_set": "Contraseña temporal asignada",
  "role.permissions_changed": "Permisos de rol modificados",
  "organization.bootstrapped": "Organización creada",
  "organization.updated": "Datos del taller actualizados",
  "privacy_policy.published": "Política de datos publicada",
  "customer.created": "Cliente registrado",
  "customer.updated": "Cliente actualizado",
  "customer.consent_granted": "Autorización otorgada",
  "customer.consent_revoked": "Autorización revocada",
  "customer.anonymized": "Cliente anonimizado",
  "catalog.manufacturer_created": "Fabricante creado",
  "catalog.manufacturer_updated": "Fabricante actualizado",
  "catalog.model_created": "Modelo creado",
  "catalog.model_updated": "Modelo actualizado",
  "device.created": "Equipo registrado",
  "device.updated": "Equipo actualizado",
};

export function auditActionLabel(action: string): string {
  return AUDIT_ACTION_LABELS[action] ?? action;
}

/** Bogotá is UTC-5 all year (no daylight saving): convert a local date to a UTC bound. */
export function bogotaDayBoundToUtc(date: string, bound: "start" | "end"): string | undefined {
  if (!date) return undefined;
  const time = bound === "start" ? "00:00:00.000" : "23:59:59.999";
  return new Date(`${date}T${time}-05:00`).toISOString();
}
