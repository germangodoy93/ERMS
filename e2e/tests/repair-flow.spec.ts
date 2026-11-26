import { expect, test, type Locator, type Page } from "@playwright/test";

import { apiLogin, seed } from "./api";
import { EMAIL, login } from "./auth";

const RUN = Date.now().toString(36);

async function selectOption(scope: Page | Locator, label: string, option: string | RegExp) {
  await scope.getByLabel(label, { exact: true }).click();
  const page = "page" in scope ? scope.page() : scope;
  await page.getByRole("option", { name: option }).first().click();
}

/**
 * Clicks a button that saves something. Panels refetch and remount after every change; on a
 * slow CI machine a click during that swap is lost, so wait for the network to be idle first
 * and again after the action.
 */
async function save(page: Page, button: Locator) {
  await page.waitForLoadState("networkidle");
  await expect(button).toBeEnabled();
  await button.click();
  await page.waitForLoadState("networkidle");
}

/** Clicks a status action in "Gestión" and confirms it. */
async function transition(page: Page, action: string, status: string) {
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: action, exact: true }).click();
  await save(page, page.getByRole("dialog").getByRole("button", { name: "Confirmar" }));
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(statusBadge(page)).toHaveText(status);
}

/** The status badge next to the order number. */
function statusBadge(page: Page): Locator {
  return page.getByRole("heading", { level: 1 }).locator("xpath=following-sibling::*[1]");
}

test("reception → diagnostic → quote → repair → QC → payment → delivery → warranty", async ({
  page,
  request,
}) => {
  const password = await login(page, request);
  const data = await seed(request, await apiLogin(request, EMAIL, password), RUN);

  // --- Reception: new customer and device from the wizard. -------------------------------
  await page.goto("/ordenes/nueva");
  await page.getByRole("button", { name: "Nuevo cliente" }).click();
  let dialog = page.getByRole("dialog");
  await dialog.getByLabel("Nombre o razón social").fill(data.customerName);
  await dialog.getByLabel("Teléfono").fill("3001234567");
  await dialog.getByRole("checkbox", { name: /Tratamiento de datos personales/ }).check();
  await dialog.getByRole("button", { name: "Registrar cliente" }).click();
  await expect(dialog).toBeHidden();

  await page.getByRole("button", { name: /Registrar.*equipo/ }).click();
  dialog = page.getByRole("dialog");
  await selectOption(dialog, "Categoría", /Celular|Teléfono/);
  await selectOption(dialog, "Fabricante", "Samsung");
  await selectOption(dialog, "Modelo", data.modelName);
  await dialog
    .getByRole("button", { name: /Registrar|Guardar/ })
    .last()
    .click();
  await expect(dialog).toBeHidden();

  await page.getByLabel("Falla reportada por el cliente").fill("La pantalla no muestra imagen.");
  await page.getByLabel("Estado físico (verificado con el cliente)").fill("Vidrio partido.");
  await page.getByLabel("Valor del diagnóstico").fill("40000");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Crear orden y descargar acta" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
  await page.waitForURL(/\/ordenes\/[0-9a-f-]{36}$/);
  const orderUrl = page.url();
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toHaveText(/^ER-\d{4}-\d{6}$/);
  const orderNumber = await heading.innerText();

  // --- Diagnostic. -------------------------------------------------------------------------
  await transition(page, "Iniciar inspección", "Inspección");
  await transition(page, "Iniciar diagnóstico", "Diagnóstico");
  const screen = page.getByRole("radiogroup", { name: "Pantalla" });
  if (await screen.count()) await screen.getByRole("radio", { name: "Falla" }).click();
  await page.getByRole("button", { name: 'Marcar pendientes como "No probado"' }).click();
  await save(page, page.getByRole("button", { name: "Guardar resultados" }));
  await page.getByLabel("Conclusión del técnico").fill("Pantalla dañada por golpe.");
  await page.getByLabel("Reparación recomendada (opcional)").fill("Cambiar la pantalla.");
  await save(page, page.getByRole("button", { name: "Cerrar diagnóstico" }));
  await expect(page.getByText(/Cerrado el/)).toBeVisible();
  await transition(page, "Pasar a cotización", "Cotización");

  // --- Quote with a part from inventory, sent and approved. --------------------------------
  await save(page, page.getByRole("button", { name: "Crear cotización" }));
  await page.getByRole("button", { name: "Repuesto", exact: true }).click();
  await selectOption(page, "Del inventario (opcional)", new RegExp(data.partName));
  await save(page, page.getByRole("button", { name: "Guardar", exact: true }));
  await save(page, page.getByRole("button", { name: "Enviar al cliente" }));
  await expect(statusBadge(page)).toHaveText("Pendiente de autorización");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Cliente aprobó" }).click();
  await save(page, page.getByRole("dialog").getByRole("button", { name: "Confirmar" }));
  await expect(statusBadge(page)).toHaveText("Aprobado");

  // --- Repair: task, part consumed, quality check. ---------------------------------------
  await transition(page, "Iniciar reparación", "En reparación");
  await page.getByLabel("Nuevo trabajo").fill("Cambio de pantalla completo.");
  await page.getByLabel("Minutos de trabajo").fill("45");
  await save(page, page.getByRole("button", { name: "Registrar trabajo" }));
  await selectOption(page, "Usar repuesto del inventario", new RegExp(data.partName));
  await save(page, page.getByRole("button", { name: "Descontar" }));
  await expect(page.getByText("Repuesto descontado del inventario.")).toBeVisible();
  await transition(page, "Enviar a control de calidad", "Control de calidad");
  for (const group of await page.getByRole("radiogroup", { name: /^Calidad:/ }).all()) {
    await group.getByRole("radio", { name: "Bien" }).click();
  }
  await save(page, page.getByRole("button", { name: "Registrar control de calidad" }));
  await transition(page, "Marcar listo para entrega", "Listo para entrega");

  // --- WhatsApp notice: suggested, prepared and turned into a wa.me link. ----------------
  await expect(page.getByText("Aviso pendiente:")).toBeVisible();
  await page.getByRole("button", { name: /Avisar por WhatsApp/ }).click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Mensaje")).toHaveValue(new RegExp(orderNumber));
  await save(page, dialog.getByRole("button", { name: /Preparar mensaje/ }));
  await expect(dialog.getByRole("link", { name: /Abrir WhatsApp aquí/ })).toHaveAttribute(
    "href",
    /^https:\/\/wa\.me\/573001234567\?text=/,
  );
  await expect(dialog.getByAltText(/Código QR/)).toBeVisible();
  await dialog.getByRole("button", { name: "Listo" }).click();
  await expect(page.getByText("Aviso pendiente:")).toBeHidden();

  // --- Payment of the balance and delivery with a 30-day warranty. -----------------------
  // The panels refetch after the status change and the payment form remounts with the new
  // balance: wait until everything settled before paying (cash is the default method).
  await page.waitForLoadState("networkidle");
  await expect(page.getByLabel("Valor del pago")).not.toHaveValue(/^0?$/);
  await save(page, page.getByRole("button", { name: "Registrar pago" }));
  await expect(page.getByText(/^Pago registrado: RC-/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Comprobante" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Entregar equipo", exact: true }).click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/Saldo pendiente/)).toHaveCount(0);
  await dialog.getByLabel("Días de garantía (opcional)").fill("30");
  await save(page, dialog.getByRole("button", { name: "Registrar entrega" }));
  await expect(dialog).toBeHidden();
  await expect(statusBadge(page)).toHaveText("Entregado");

  // --- Warranty claim opens a new order without diagnostic fee. --------------------------
  const warrantyCard = page
    .getByText("Garantía", { exact: true })
    .locator("xpath=ancestor::*[@data-slot='card'][1]");
  try {
    await expect(page.getByText(/^30 días: del/)).toBeVisible();
  } catch {
    // Diagnose an intermittent CI failure: stale screen or warranty not created?
    const before = await warrantyCard.innerText().catch(() => "(sin tarjeta)");
    await page.reload();
    const after = await warrantyCard.innerText().catch(() => "(sin tarjeta)");
    throw new Error(`Garantía no visible. Antes: «${before}». Tras recargar: «${after}».`);
  }
  await expect(page.getByText("Vigente")).toBeVisible();
  await page.getByRole("button", { name: "Abrir reclamo de garantía" }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByLabel("Falla que reporta el cliente").fill("La pantalla volvió a fallar.");
  await dialog.getByLabel("Estado físico al recibirlo").fill("Sin golpes nuevos.");
  await save(page, dialog.getByRole("button", { name: "Abrir reclamo" }));
  await page.waitForURL(
    (url) => url.href !== orderUrl && /\/ordenes\/[0-9a-f-]{36}$/.test(url.href),
  );
  await expect(page.getByText(`Esta orden atiende un reclamo de garantía de`)).toBeVisible();
  await expect(page.getByRole("link", { name: orderNumber })).toBeVisible();

  // --- Dashboard reflects the workshop. ---------------------------------------------------
  await page.goto("/");
  await expect(page.getByText("Ingresos del mes")).toBeVisible();
});
