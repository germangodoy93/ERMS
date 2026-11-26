import { expect, test, type APIRequestContext } from "@playwright/test";

import { apiLogin, seed } from "./api";
import { EMAIL, login } from "./auth";

const RUN = Date.now().toString(36);

/** A Monday-to-Friday, non-holiday date about two weeks ahead (Bogotá calendar). */
async function workday(request: APIRequestContext, token: string): Promise<string> {
  const start = new Date(Date.now() - 5 * 3600 * 1000);
  start.setUTCDate(start.getUTCDate() + 14);
  const from = start.toISOString().slice(0, 10);
  const end = new Date(start);
  end.setUTCDate(end.getUTCDate() + 10);
  const res = await request.get("/api/v1/appointments/holidays", {
    headers: { Authorization: `Bearer ${token}` },
    params: { from, to: end.toISOString().slice(0, 10) },
  });
  const holidays = new Set(((await res.json()) as { date: string }[]).map((h) => h.date));
  const day = new Date(start);
  while ([0, 6].includes(day.getUTCDay()) || holidays.has(day.toISOString().slice(0, 10))) {
    day.setUTCDate(day.getUTCDate() + 1);
  }
  return day.toISOString().slice(0, 10);
}

test("agenda: schedule an on-site visit, see it in the week and cancel it", async ({
  page,
  request,
}) => {
  const password = await login(page, request);
  const token = await apiLogin(request, EMAIL, password);
  await seed(request, token, `ag${RUN}`);
  const customerName = `Cliente Agenda ${RUN}`;
  const customer = await request.post("/api/v1/customers", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      kind: "PERSON",
      full_name: customerName,
      phone: "3001234567",
      consents: [{ purpose: "DATA_PROCESSING", channel: "SCREEN" }],
    },
  });
  expect(customer.status(), await customer.text()).toBe(201);
  const day = await workday(request, token);

  await page.getByRole("link", { name: "Agenda" }).click();
  await page.getByRole("button", { name: "Nueva cita" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Cliente", { exact: true }).fill(customerName);
  await dialog.getByRole("button", { name: new RegExp(customerName) }).click();
  await expect(dialog.getByText(/precio según el diagnóstico/)).toBeVisible();
  await dialog.getByLabel("Fecha").fill(day);
  await dialog.getByLabel("Hora").fill("10:00");
  await dialog.getByLabel("Qué necesita el cliente").fill("El computador no enciende.");
  await dialog.getByLabel("Dirección de la visita").fill("Calle Ficticia 1 # 2-3");
  await dialog.getByLabel("Localidad", { exact: true }).click();
  await page.getByRole("option", { name: "Suba" }).click();
  await dialog.getByRole("button", { name: "Agendar cita" }).click();
  await expect(dialog).toBeHidden();

  // The agenda jumps to the week of the new appointment.
  const item = page.getByRole("button", { name: new RegExp(customerName) });
  await expect(item).toBeVisible();
  await expect(item).toContainText("10:00 – 11:00");
  await item.click();
  await expect(dialog.getByRole("heading", { name: /^Cita CT-\d{4}-\d{6}/ })).toBeVisible();
  await expect(dialog.getByText("Calle Ficticia 1 # 2-3 · Suba")).toBeVisible();
  await dialog.getByRole("button", { name: "Cancelar cita" }).click();
  await dialog.getByLabel("Motivo de la cancelación").fill("El cliente traerá el equipo.");
  await dialog.getByRole("button", { name: "Confirmar cancelación" }).click();
  await expect(dialog).toBeHidden();
  await expect(item).toBeHidden();
});
