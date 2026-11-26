import { expect, type APIRequestContext, type Page } from "@playwright/test";

// Credentials of a disposable admin (CI bootstraps one; locally use the E2E user).
export const EMAIL = process.env.E2E_EMAIL ?? "e2e-admin@example.com";
const PASSWORD = process.env.E2E_PASSWORD ?? "Definitiva-E2E-Sprint2";
// When the admin still has a temporary password, the first flow changes it to this one.
const NEW_PASSWORD = process.env.E2E_NEW_PASSWORD ?? "Definitiva-Navegador-2026";

/** The password that works now: the initial one, or the new one after another spec changed it. */
async function currentPassword(request: APIRequestContext): Promise<string> {
  for (const password of [PASSWORD, NEW_PASSWORD]) {
    const res = await request.post("/api/v1/auth/login", { data: { email: EMAIL, password } });
    if (res.ok()) return password;
  }
  throw new Error("Ninguna de las contraseñas E2E funciona.");
}

/** Signs in through the UI (changing a temporary password) and returns the password in use. */
export async function login(page: Page, request: APIRequestContext): Promise<string> {
  const password = await currentPassword(request);
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill(EMAIL);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Ingresar" }).click();
  // The app may land on "/" first and then redirect to the password change.
  const current = page.getByLabel("Contraseña actual");
  await expect(current.or(page.getByRole("link", { name: "Inicio" }))).toBeVisible();
  if (await current.isVisible()) {
    await page.getByLabel("Contraseña actual").fill(password);
    await page.getByLabel("Nueva contraseña", { exact: true }).fill(NEW_PASSWORD);
    await page.getByLabel("Confirmar nueva contraseña").fill(NEW_PASSWORD);
    await page.getByRole("button", { name: "Cambiar contraseña" }).click();
    await page.waitForURL((url) => !url.pathname.startsWith("/cambiar-contrasena"));
    return NEW_PASSWORD;
  }
  return password;
}
