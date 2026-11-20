import { expect, type APIRequestContext } from "@playwright/test";

/**
 * Master data the browser flow needs (workshop data, published policy and terms, a phone
 * model, a part in stock). It goes through the public API so the UI test focuses on the
 * order lifecycle. Everything is fictitious and idempotent for a disposable environment.
 */
export interface Seed {
  token: string;
  partName: string;
  modelName: string;
  customerName: string;
}

export async function apiLogin(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  const res = await request.post("/api/v1/auth/login", { data: { email, password } });
  expect(res.status(), await res.text()).toBe(200);
  return ((await res.json()) as { access_token: string }).access_token;
}

async function call<T>(
  request: APIRequestContext,
  token: string,
  method: "get" | "post" | "patch" | "put",
  path: string,
  data?: unknown,
): Promise<T> {
  const res = await request[method](`/api/v1${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
  expect(res.ok(), `${method.toUpperCase()} ${path}: ${res.status()} ${await res.text()}`).toBe(
    true,
  );
  return (await res.json()) as T;
}

export async function seed(request: APIRequestContext, token: string, run: string): Promise<Seed> {
  await call(request, token, "patch", "/organization", {
    legal_name: "Taller Ficticio E2E SAS",
    tax_id: "890903938",
    address: "Calle Ficticia 1",
    city: "Bogotá",
    phone: "6010000000",
    email: "taller-e2e@example.com",
  });
  const policy = await call<{ policy: unknown }>(request, token, "get", "/privacy-policy");
  if (!policy.policy) {
    const draft = await call<{ content: string }>(request, token, "get", "/privacy-policy/draft");
    await call(request, token, "post", "/privacy-policy", { content: draft.content });
  }
  const terms = await call<{ terms: unknown; template: string }>(
    request,
    token,
    "get",
    "/reception-terms",
  );
  if (!terms.terms)
    await call(request, token, "post", "/reception-terms", { content: terms.template });

  const manufacturers = await call<{ id: string; name: string }[]>(
    request,
    token,
    "get",
    "/catalog/manufacturers",
  );
  const samsung = manufacturers.find((m) => m.name === "Samsung");
  expect(samsung).toBeDefined();
  const modelName = `Galaxy Navegador ${run}`;
  await call(request, token, "post", "/catalog/models", {
    manufacturer_id: samsung!.id,
    category_code: "PHONE",
    name: modelName,
  });

  const partName = `Pantalla Navegador ${run}`;
  const part = await call<{ id: string }>(request, token, "post", "/inventory/parts", {
    sku: `nav-${run}`,
    name: partName,
    sale_price: "200000",
    tax_rate: 19,
    price_includes_tax: true,
    min_stock: 1,
  });
  const supplier = await call<{ id: string }>(request, token, "post", "/inventory/suppliers", {
    name: `Proveedor Navegador ${run}`,
  });
  await call(request, token, "post", "/inventory/entries", {
    supplier_id: supplier.id,
    invoice_number: `FV-NAV-${run}`,
    received_on: new Date().toISOString().slice(0, 10),
    lines: [{ part_id: part.id, quantity: 3, unit_cost: "120000" }],
  });
  return { token, partName, modelName, customerName: `Cliente Navegador ${run}` };
}
