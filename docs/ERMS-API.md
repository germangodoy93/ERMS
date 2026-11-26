# ERMS – Contratos de API

- **Base:** `/api/v1`
- **Swagger UI:** `/api/v1/docs` · **ReDoc:** `/api/v1/redoc` · **OpenAPI:** `/api/v1/openapi.json`
  (solo fuera de producción; en producción responden 404)
- **Copia versionada:** [`docs/api/openapi.json`](api/openapi.json). CI falla si no coincide con
  el código.

Este documento solo describe endpoints **implementados**. Los planificados aparecen en
`ERMS-BACKLOG.md` y se documentan aquí cuando se construyen.

## Convenciones

| Aspecto | Contrato |
|---|---|
| Formato | JSON UTF-8 |
| Fechas | ISO-8601 en UTC (`2026-11-19T17:30:00Z`) |
| Dinero | string decimal en COP (`"150000.00"`) |
| Paginación | `?page=1&size=20` (máx. 100) → `{items, total, page, size}` |
| Autenticación | `Authorization: Bearer <access_token>` (15 min). Refresh token en cookie `erms_refresh` (`HttpOnly`, `SameSite=Strict`, `Secure` en producción, `Path=/api/v1/auth`). |
| Correos | Se guardan en minúsculas y son únicos en todo el sistema |

### Errores (RFC 9457)

Todas las respuestas de error usan `Content-Type: application/problem+json`:

```json
{
  "type": "https://erms.local/problems/validation_error",
  "title": "Datos de entrada inválidos",
  "status": 422,
  "detail": "Uno o más campos no cumplen las validaciones.",
  "code": "validation_error",
  "instance": "/api/v1/customers",
  "errors": [{ "field": "body.email", "message": "...", "type": "value_error" }]
}
```

| `code` | HTTP | Uso |
|---|---|---|
| `validation_error` | 422 | Entrada inválida (formato) |
| `business_rule_violation` | 422 | Regla de negocio, p. ej. política de contraseñas (`errors[].type = "password_policy"`) o último administrador |
| `not_authenticated` | 401 | Falta el token, expiró o la sesión fue cerrada. Incluye `WWW-Authenticate: Bearer`. |
| `invalid_credentials` | 401 | Correo o contraseña incorrectos, cuenta inactiva o bloqueada (mensaje idéntico en todos los casos) |
| `password_change_required` | 403 | El usuario tiene contraseña temporal; solo puede usar `/auth/me`, `/auth/password/change` y `/auth/logout` |
| `permission_denied` | 403 | RBAC |
| `not_found` | 404 | Recurso inexistente o de otra organización |
| `rate_limited` | 429 | Demasiados intentos fallidos de inicio de sesión desde la misma IP (20 en 15 min). Incluye `Retry-After` en segundos. |
| `conflict` | 409 | Unicidad (correo, documento del cliente, IMEI, serial, fabricante o modelo ya registrado) |
| `internal_error` | 500 | Error inesperado; no expone detalles internos |

## Endpoints implementados

### Autenticación (`/auth`)

| Método y ruta | Acceso | Respuesta | Notas |
|---|---|---|---|
| `POST /auth/login` | público | 200 `TokenResponse` + cookie | `{email, password}`. 5 fallos → bloqueo de 15 min. |
| `POST /auth/refresh` | cookie | 200 `TokenResponse` + cookie nueva | Rota el refresh token. Reutilizar uno rotado hace más de 30 s revoca toda la sesión. |
| `POST /auth/logout` | cookie | 204 | Idempotente; invalida también los access tokens de la sesión. |
| `POST /auth/password/forgot` | público | 202 | Misma respuesta exista o no el correo. Enlace válido 30 min, un solo uso. |
| `POST /auth/password/reset` | token del correo | 204 | `{token, new_password}`; cierra todas las sesiones del usuario. |
| `POST /auth/password/change` | autenticado* | 204 | `{current_password, new_password}`; cierra las demás sesiones. |
| `GET /auth/me` | autenticado* | 200 `MeResponse` | Roles, permisos efectivos y organización. |

\* Permitido aunque el usuario tenga contraseña temporal.

```json
// TokenResponse
{ "access_token": "eyJ…", "token_type": "bearer", "expires_at": "2026-11-19T17:45:00Z", "must_change_password": false }
// MeResponse
{ "id": "…", "email": "persona@example.com", "full_name": "…", "organization": { "id": "…", "name": "…" },
  "roles": [{ "id": "…", "code": "SUPERVISOR", "name": "Supervisor" }],
  "permissions": ["audit:read", "users:manage", "users:read"], "must_change_password": false }
```

Sesión: dura como máximo 12 h desde el login y se cierra tras 2 h sin renovar el token.

### Usuarios (`/users`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /users?q=&is_active=&role=&page=&size=` | `users:read` | 200 `Page[UserRead]` |
| `POST /users` | `users:manage` | 201 `UserRead`: `{email, full_name, phone?, temporary_password, role_ids[]}` |
| `GET /users/{id}` | `users:read` | 200 `UserRead` |
| `PATCH /users/{id}` | `users:manage` | 200 `UserRead`: cambia solo los campos enviados (`email`, `full_name`, `phone`, `is_active`) |
| `PUT /users/{id}/roles` | `users:manage` | 200 `UserRead`: `{role_ids[]}` reemplaza los roles |
| `POST /users/{id}/temporary-password` | `users:manage` | 200 `UserRead`: obliga a cambiarla y cierra las sesiones del usuario |

Reglas:

- Asignar o quitar el rol Administrador, o gestionar a un usuario administrador, requiere `roles:manage` (403).
- No puede desactivarse a sí mismo ni dejar la organización sin administradores activos (422).
- Desactivar un usuario cierra sus sesiones.

### Roles y permisos

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /roles` | `users:read` | 200 `RoleRead[]` (`id`, `code`, `name`, `is_system`, `permissions[]`) |
| `GET /permissions` | `users:read` | 200 `[{code, description}]` |
| `PUT /roles/{id}/permissions` | `roles:manage` | 200 `RoleRead`: `{permissions[]}`. El rol Administrador no se modifica (422). |

Los cambios de permisos aplican de inmediato: los permisos no viajan en el JWT.

### Auditoría

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /audit-logs?action=&entity_type=&entity_id=&actor_user_id=&date_from=&date_to=&page=&size=` | `audit:read` | 200 `Page[AuditLogRead]`, del más reciente al más antiguo |

Acciones registradas: `auth.login`, `auth.login_failed`, `auth.logout`,
`auth.refresh_reuse_detected`, `auth.password_reset_requested`, `auth.password_reset`,
`auth.password_changed`, `user.created`, `user.updated`, `user.roles_changed`,
`user.temporary_password_set`, `role.permissions_changed`, `organization.bootstrapped`,
`organization.updated`, `privacy_policy.published`, `customer.created`, `customer.updated`,
`customer.consent_granted`, `customer.consent_revoked`, `customer.anonymized`,
`catalog.manufacturer_created`, `catalog.manufacturer_updated`, `catalog.model_created`,
`catalog.model_updated`, `device.created`, `device.updated`, `reception_terms.published`,
`work_order.created`, `work_order.updated`, `work_order.assigned`,
`work_order.status_changed`, `work_order.photo_added`, `work_order.photo_deleted`,
`diagnostic.results_saved`, `diagnostic.closed`, `diagnostic.reopened`,
`diagnostic.agent_pairing_created`, `diagnostic.agent_paired`, `diagnostic.agent_reported`,
`inventory.part_saved`, `inventory.supplier_saved`, `inventory.stock_received`,
`inventory.adjusted`, `quote.created`, `quote.saved`, `quote.discarded`, `quote.sent`,
`quote.accepted`, `quote.rejected`, `repair.task_added`, `repair.part_consumed`,
`repair.part_returned`, `repair.quality_checked`, `payment.registered`,
`work_order.delivered_with_balance`.
Las contraseñas y los tokens nunca se registran. De los clientes solo se registran los
**nombres de los campos** que cambiaron, nunca sus valores (ADR-018).

### Datos del taller y política de datos

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /organization` | autenticado | 200 `OrganizationRead` (`name`, `legal_name`, `tax_id`, `address`, `city`, `phone`, `email`) |
| `PATCH /organization` | `organization:manage` | 200 `OrganizationRead`. NIT con dígito de verificación validado o calculado; teléfono en E.164. |
| `GET /privacy-policy` | autenticado | 200 `{policy, authorizations}`: política vigente (o `null`) y textos de autorización que se muestran en recepción |
| `GET /privacy-policy/draft` | `organization:manage` | 200 `{content, missing_fields[]}`: plantilla con los datos del taller |
| `POST /privacy-policy` | `organization:manage` | 201 `PrivacyPolicyRead`: `{content}` publica la versión siguiente. 422 si faltan datos del taller o quedan marcadores `[...]`. |
| `GET /privacy-policy/versions` | `customers:read` | 200 `[{id, version, published_at}]` |
| `GET /privacy-policy/versions/{n}` | `customers:read` | 200 `PrivacyPolicyRead` |

Las versiones publicadas no se editan: un cambio publica una versión nueva.

### Clientes (`/customers`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /customers?q=&is_active=&page=&size=` | `customers:read` | 200 `Page[CustomerListItem]`. `q` busca por nombre (sin tildes), documento (prefijo) o teléfono. |
| `POST /customers` | `customers:manage` | 201 `CustomerRead` |
| `GET /customers/{id}` | `customers:read` | 200 `CustomerRead` (incluye `consents[]` vigentes y `can_be_served`) |
| `PATCH /customers/{id}` | `customers:manage` | 200 `CustomerRead`: cambia solo los campos enviados, incluido `is_active` |
| `GET /customers/{id}/consents` | `customers:read` | 200 historial de autorizaciones, del más reciente al más antiguo |
| `POST /customers/{id}/consents` | `customers:manage` | 200 `CustomerRead`: `{purpose, granted, channel}` |
| `POST /customers/{id}/anonymize` | `customers:anonymize` | 200 `CustomerRead`: `{channel}`. Irreversible. |

```json
// POST /customers
{ "kind": "PERSON", "full_name": "…", "id_type": "CC", "id_number": "1.000.000.001",
  "phone": "300 000 0001", "email": null, "address": null, "notes": null,
  "consents": [{ "purpose": "DATA_PROCESSING", "channel": "SCREEN" }] }
```

Reglas:

- Sin política publicada no se registran clientes (422).
- `consents` debe incluir `DATA_PROCESSING`; `PHOTOS` y `DIAGNOSTIC_AGENT` son opcionales.
  `channel`: `SCREEN` (en pantalla), `PAPER` (firmado) o `VERBAL`.
- El documento es opcional; si se envía, tipo y número van juntos y no se repiten en el taller
  (409). Tipos: `CC`, `CE`, `NIT`, `PAS`, `TI`, `PPT`. El NIT se guarda como `900123456-7`.
- Se exige al menos un teléfono o un correo. Teléfonos colombianos: 10 dígitos (celular 3XX o
  fijo 60X); se guardan como `+57…`. Los extranjeros deben empezar con `+`.
- Las autorizaciones son de solo inserción: revocar agrega un registro.
- Anonimizar borra nombre, documento, contacto, dirección y notas (también las notas de sus
  equipos), revoca las autorizaciones y desactiva al cliente. El historial técnico se conserva.

### Catálogo de equipos (`/catalog`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /catalog/categories` | autenticado | 200 `[{code, name}]`: `LAPTOP`, `DESKTOP`, `PHONE`, `TABLET`, `CONSOLE`, `OTHER` |
| `GET /catalog/manufacturers?include_inactive=` | autenticado | 200 `ManufacturerRead[]` |
| `POST /catalog/manufacturers` | `catalog:manage` | 201: `{name}` (único sin distinguir mayúsculas) |
| `PATCH /catalog/manufacturers/{id}` | `catalog:manage` | 200: `{name?, is_active?}` |
| `GET /catalog/models?manufacturer_id=&category=&q=&include_inactive=` | autenticado | 200 `DeviceModelRead[]` (máx. 200) |
| `POST /catalog/models` | `devices:manage` | 201: `{manufacturer_id, category_code, name, release_year?}` |
| `PATCH /catalog/models/{id}` | `catalog:manage` | 200: `{name?, category_code?, release_year?, is_active?}` |

### Equipos

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /customers/{id}/devices` | `customers:read` | 200 `DeviceRead[]` |
| `POST /customers/{id}/devices` | `devices:manage` | 201 `DeviceRead`: `{model_id, imei?, serial_number?, operating_system?, storage?, color?, notes?}` |
| `GET /devices?q=&page=&size=` | `customers:read` | 200 `Page[DeviceSearchItem]`: busca por IMEI, serial o modelo (mínimo 3 caracteres) |
| `GET /devices/{id}` | `customers:read` | 200 `DeviceRead` |
| `PATCH /devices/{id}` | `devices:manage` | 200 `DeviceRead`. El propietario no cambia. |

Reglas: solo se registran equipos de clientes activos, no anonimizados y con autorización
de datos vigente (422). El IMEI tiene 15 dígitos con dígito de control Luhn y es único en el
taller; el serial es único por modelo (409 con el nombre del propietario actual).

### Condiciones del acta (`/reception-terms`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /reception-terms` | autenticado | 200 `{terms: ReceptionTermsRead \| null, template}` |
| `POST /reception-terms` | `organization:manage` | 201 `ReceptionTermsRead`: `{content}` publica la versión siguiente |

### Órdenes de servicio (`/work-orders`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /work-orders?q=&status=&status=&technician_id=&unassigned=&open=&page=&size=` | `work_orders:read` | 200 `Page[WorkOrderListItem]`, de la más reciente a la más antigua. `q`: número, cliente (sin tildes), IMEI, serial o modelo. |
| `POST /work-orders` | `work_orders:create` | 201 `WorkOrderRead` |
| `GET /work-orders/technicians` | `work_orders:assign` | 200 `[{id, full_name}]`: usuarios activos con `work_orders:progress` |
| `GET /work-orders/{id}` | `work_orders:read` | 200 `WorkOrderRead` (incluye `history[]` y `allowed_transitions[]` para el usuario actual) |
| `PATCH /work-orders/{id}` | `work_orders:create` | 200: corrige falla, estado físico, prioridad, fecha estimada y notas (no los valores) |
| `PUT /work-orders/{id}/assignment` | `work_orders:assign` | 200: `{technician_id \| null}` |
| `POST /work-orders/{id}/status` | `progress` o `deliver` según el estado | 200: `{status, reason?}` |
| `POST /work-orders/{id}/delivery` | `work_orders:deliver` | 200: `{picked_up_by_customer, name?, document?, notes?}` |
| `GET /work-orders/{id}/reception-act.pdf` | `work_orders:read` | 200 `application/pdf` (descarga) |
| `GET /work-orders/{id}/photos` | `work_orders:read` | 200 `{demo, max_photos, items[]}` |
| `POST /work-orders/{id}/photos` | `work_orders:create` o `progress` | 201: `multipart/form-data` con `file` (JPG, PNG o WEBP; máx. 10 MB). 503 si el bucket no responde (no se guarda nada) |
| `GET /work-orders/{id}/photos/{photo_id}` | `work_orders:read` | 200 `image/jpeg` |
| `DELETE /work-orders/{id}/photos/{photo_id}` | `work_orders:create` o `progress` | 204. 503 si el bucket no responde (la foto se conserva) |

```json
// POST /work-orders
{ "customer_id": "…", "device_id": "…", "reported_issue": "No enciende.",
  "physical_condition": "Pantalla rayada.", "unlock_method": "CUSTOMER_IN_PERSON",
  "accessories": [{ "code": "CHARGER" }, { "code": "OTHER", "detail": "Lápiz óptico" }],
  "priority": "NORMAL", "estimated_delivery_date": "2026-11-27",
  "diagnostic_fee": "50000", "advance_amount": "20000", "advance_method": "NEQUI",
  "assigned_technician_id": null, "notes": null }
```

Reglas:

- Requiere condiciones publicadas, cliente con autorización de datos vigente y un equipo activo
  del mismo cliente sin otra orden abierta (409).
- Número `ER-<año>-<6 dígitos>`, consecutivo por taller y año (hora de Bogotá).
- `unlock_method`: `NOT_REQUIRED`, `CUSTOMER_IN_PERSON` o `CUSTOMER_UNLOCKS`. **Nunca se envían
  ni guardan contraseñas o patrones.**
- Accesorios: `CHARGER`, `CABLE`, `CASE`, `BATTERY`, `SIM`, `SD_CARD`, `CONTROLLER`, `BOX`,
  `OTHER` (exige `detail`). Medios de pago: `CASH`, `TRANSFER`, `CARD`, `NEQUI`, `DAVIPLATA`.
- Dinero como texto decimal con dos posiciones en las respuestas (`"50000.00"`).
- Transiciones y permisos: ver la tabla en [ERMS-ERD.md](ERMS-ERD.md). Transición inválida o sin
  motivo requerido: 422; sin permiso u orden de otro técnico: 403. `ENTREGADO` solo por
  `/delivery`. Una orden entregada no se modifica.
- Fotos: exigen la autorización `PHOTOS` vigente del cliente; se re-codifican a JPEG de máx.
  2048 px **sin metadatos EXIF (incluido el GPS)**; máx. 20 por orden. Con `demo: true` se
  guardan en el disco del servidor y pueden perderse al redesplegar.

### Diagnóstico

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /work-orders/{id}/diagnostic` | `work_orders:read` | 200 `DiagnosticRead`: estado, pruebas de la categoría con su resultado, disponibilidad del agente |
| `PUT /work-orders/{id}/diagnostic/results` | `work_orders:progress` | 200: `{results: [{test_code, result, observation?}]}` (solo pruebas manuales) |
| `POST /work-orders/{id}/diagnostic/close` | `work_orders:progress` | 200: `{conclusion, recommendation?}` |
| `POST /work-orders/{id}/diagnostic/reopen` | `work_orders:progress` | 200 |
| `POST /work-orders/{id}/diagnostic/agent-pairing` | `work_orders:progress` | 201 `{code, expires_at, download_url}` |
| `GET /work-orders/{id}/diagnostic-report.pdf` | `work_orders:read` | 200 `application/pdf` |
| `POST /diagnostics/agent/pair` | código de emparejamiento | 200 `{token, expires_at, work_order_number, device}` |
| `POST /diagnostics/agent/report` | `Bearer <token del agente>` | 200 `{results}` |

Reglas:

- Resultados: `OK`, `WARNING`, `FAIL`, `NOT_TESTED`, `NOT_SUPPORTED`. Se registran con la orden en
  `DIAGNOSTICO` (el técnico, sobre sus órdenes). Para cerrar, **todas** las pruebas manuales de
  la categoría deben tener resultado (`NOT_TESTED` es válido, por ejemplo si el equipo no
  enciende) y se exige la conclusión. **No se pasa a `COTIZACION` sin diagnóstico cerrado.**
- Las pruebas `AGENT_*` solo las llena el agente; a mano devuelven 422.
- Agente: solo para `LAPTOP`/`DESKTOP`, con la orden en `DIAGNOSTICO` y la autorización
  `DIAGNOSTIC_AGENT` vigente del cliente. Código `XXXX-XXXX` (alfabeto sin 0/O/1/I) de un solo
  uso, válido 30 min; se canjea por un token válido 15 min para **un** reporte. Un código nuevo
  o el cierre del diagnóstico invalidan los anteriores. Código o token inválido: 401.
- El reporte del agente (`AgentReport`) trae solo lo que Windows permitió leer; el backend
  evalúa con estos umbrales y lo que falta queda `NOT_SUPPORTED`:

| Prueba | Advertencia | Falla |
|---|---|---|
| `AGENT_BATTERY` (desgaste = 1 − capacidad actual / diseño) | ≥ 20 % | ≥ 40 % |
| `AGENT_DISK_HEALTH` (estado que reporta Windows) | Warning | Unhealthy |
| `AGENT_DISK_SPACE` | < 10 % libre en algún volumen | — |
| `AGENT_DISK_SMART` (solo como administrador) | errores de lectura/escritura, desgaste ≥ 80 %, temperatura ≥ 60 °C | — |
| `AGENT_STABILITY` (30 días) | ≥ 1 apagado inesperado o ≥ 1 pantallazo azul | ≥ 5 pantallazos azules |

### Inventario (`/inventory`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /inventory/parts?q=&low_stock=&include_inactive=` | `inventory:read` | 200 `PartRead[]` con `stock` y `low_stock` |
| `POST /inventory/parts` · `PUT /inventory/parts/{id}` | `inventory:manage` | `PartWrite`; SKU en mayúsculas y único |
| `GET /inventory/parts/{id}/movements` | `inventory:read` | 200 movimientos (más reciente primero) |
| `POST /inventory/parts/{id}/adjustments` | `inventory:manage` | `{counted_quantity, reason}` (conteo físico) |
| `POST /inventory/entries` | `inventory:manage` | 201: `{supplier_id?, invoice_number?, received_on, lines: [{part_id, quantity, unit_cost}]}`; actualiza el costo del repuesto |
| `GET/POST /inventory/suppliers` · `PUT /inventory/suppliers/{id}` | `inventory:read` / `inventory:manage` | Proveedores |

La existencia nunca es negativa: si no alcanza, 422 "Existencia insuficiente".

### Cotizaciones (`/work-orders/{id}/quotes`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET …/quotes` | `work_orders:read` | 200 `{diagnostic_fee, quotes[], can_edit, can_send, can_respond, max_discount_percent}` |
| `POST …/quotes` | `quotes:manage` | 201 borrador (copia la versión anterior) |
| `PUT …/quotes/{q}` | `quotes:manage` | 200: `{items: [{kind, part_id?, description?, quantity, unit_price, discount_percent, apply_tax, price_includes_tax}], notes?}` |
| `DELETE …/quotes/{q}` | `quotes:manage` | 204 (solo borrador) |
| `POST …/quotes/{q}/send` | `work_orders:deliver` | 200: la orden pasa a PENDIENTE_AUTORIZACION; vigencia 15 días |
| `POST …/quotes/{q}/response` | `work_orders:deliver` | 200: `{accepted, channel, reason?}` → APROBADO o COTIZACION_RECHAZADA |
| `GET …/quotes/{q}/pdf` | `work_orders:read` | PDF |

Reglas: IVA opcional por ítem (19 %); el precio puede incluirlo o no y el servidor calcula
base + IVA = total con redondeo `ROUND_HALF_UP`. Descuento > 10 % por ítem exige
`quotes:discount` y queda registrado quién lo autorizó. Una cotización vencida no se acepta.
Los estados PENDIENTE_AUTORIZACION, APROBADO y COTIZACION_RECHAZADA **solo** cambian por la
cotización (`/status` responde 422). Si se aprueba, el diagnóstico queda incluido en el total.

### Reparación y control de calidad (`/work-orders/{id}/repair`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET …/repair` | `work_orders:read` | 200 `{tasks[], quality_checks[], qc_tests[], can_repair, can_check}` |
| `POST …/repair/tasks` | `repairs:manage` | 201: `{description, labor_minutes?}` (orden EN_REPARACION) |
| `POST …/repair/tasks/{t}/parts` | `repairs:manage` | `{part_id, quantity}` → salida de inventario |
| `POST …/repair/tasks/{t}/parts/{p}/return` | `repairs:manage` | devolución al inventario |
| `POST …/repair/quality-checks` | `repairs:manage` | 201: `{results: [todas las pruebas manuales de la categoría], notes?}`; aprobado si ninguna es FAIL |

`CONTROL_CALIDAD → LISTO_ENTREGA` exige que el último control esté aprobado.

### Pagos (`/work-orders/{id}`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET …/billing` | `work_orders:read` | 200 `{diagnostic_fee, accepted_quote_total, amount_due, paid, balance, payments[], can_register}` |
| `POST …/payments` | `payments:manage` | 201: `{amount, method, reference?, notes?}`; no puede superar el saldo |
| `GET …/payments/{p}/receipt.pdf` | `work_orders:read` | Comprobante (no es factura electrónica) |

Valor del servicio = total de la cotización aprobada (incluye el diagnóstico) o, sin cotización
aprobada, el valor del diagnóstico. El anticipo de la recepción es el primer pago. Entregar con
saldo > 0 exige `work_orders:deliver_with_balance` y `balance_reason` en `/delivery`.

### Garantías (`/work-orders/{id}/warranty`)

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET …/warranty` | `work_orders:read` | 200 `{warranty, claims[], is_claim_order, can_claim, can_decide}`. En una orden de reclamo, `warranty` es la de la orden original. |
| `POST …/warranty/claims` | `warranties:manage` | 201 `WorkOrderRead`: `{reported_issue, physical_condition, unlock_method, accessories?}`. Abre una orden nueva para el mismo equipo, sin valor de diagnóstico y con `warranty_of_id`. Solo con garantía vigente y sin otro reclamo abierto. |
| `POST …/warranty/claims/{c}/decision` | `warranties:manage` | 200: `{accepted, resolution}` |

La garantía se crea al entregar un equipo reparado (cotización aprobada o trabajos
registrados), con los días de `DeliveryRequest.warranty_days` o, si no se indican, los de
`organizations.warranty_days`. Las órdenes de reclamo no generan una garantía nueva y su
cotización puede ser de $0.

### Dashboard y reportes

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /dashboard` | `work_orders:read` | 200 `Dashboard`. Con `reports:read`, alcance `WORKSHOP` (todo el taller, con dinero); sin él, `MINE` (solo las órdenes asignadas y los campos de dinero en `null`). |
| `GET /reports/{kind}?from=&to=&format=` | `reports:read` | `kind`: `income`, `orders`, `inventory`, `technicians`. `format`: `json` (200 `Report`), `csv` o `pdf`. Rango máximo 366 días; `from > to` responde 422. |

`Report` = `{kind, title, date_from, date_to, columns[], rows[][], summary[[etiqueta, valor]], money_columns[]}`.
El CSV usa UTF-8 con BOM y `;` para que Excel en español lo abra directamente; las columnas de
`money_columns` van como número sin formato. Las celdas de texto que empiezan por `=`, `+`, `-`,
`@`, tabulador o retorno de carro se anteponen con `'` para evitar inyección de fórmulas.

### Ensamble de PC (`/assembly`, Sprint E1)

Solo técnicos y administradores (`assembly:manage`).

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /assembly/catalog` | `assembly:manage` | 200 `CatalogPart[]`: repuestos activos con `assembly_category`, precio, existencia y `specs` |
| `POST /assembly/catalog/import` | `assembly:manage` + `inventory:manage` | 200 `{created, updated, errors[]}`: crea o actualiza por SKU con `cost` (precio del proveedor, IVA incluido); no toca existencias |
| `GET /assembly/catalog/costs.csv` | `assembly:manage` + `inventory:manage` | Plantilla para Excel (UTF-8 con BOM, `;`): Código, Nombre, Categoría, Costo, Precio de venta, Precio fijado a mano |
| `POST /assembly/catalog/costs` | `assembly:manage` + `inventory:manage` | Multipart `file` (CSV ≤ 2 MB, `;` o `,`, UTF-8 o Windows-1252) con columnas Código y Costo → 200 `{updated, unchanged, unknown[], errors[]}` |
| `POST /assembly/evaluate` | `assembly:manage` | 200 `EvaluationOut`: `{errors[], warnings[], missing[], ready, watts, recommended_psu_w, price, gaming_index, work_index, ram_gb, candidates}`. Con `candidates_for`, `candidates` da el motivo por el que no encaja cada pieza de esa categoría |
| `GET/POST /assembly/builds` · `GET/PUT/DELETE /assembly/builds/{id}` | `assembly:manage` | Configuraciones; solo los borradores se editan o borran |
| `POST /assembly/builds/{id}/order` | `assembly:manage` | 201 `WorkOrderRead`: `{customer_id}`. Exige configuración completa y compatible. Crea el equipo "PC armada a la medida", la orden `kind = ASSEMBLY` en COTIZACION (sin inspección ni diagnóstico) y la cotización en borrador con las piezas y la mano de obra |
| `GET /work-orders/{id}/assembly` | `work_orders:read` | 200 lista de chequeo `{steps[{code, title, done, blocked_reason}], parts_consumed, can_work}` |
| `POST /work-orders/{id}/assembly/consume` | `repairs:manage` (en reparación) | Descuenta todas las piezas de una vez (todas o ninguna) |
| `POST /work-orders/{id}/assembly/steps/{code}` | `repairs:manage` (en reparación) | Marca el paso; 422 "Aún no: …" si falta un paso previo |

`Selection` = `{cpu, board, ram, ram_units, gpu, psu, case, cooler, storage[≤4], rgb[≤8], monitor[≤3], keyboard, mouse,
pad, headset, mic[≤2], speaker, camera, stream[≤3], chair, desk, light[≤2], desk_shape (STRAIGHT, L), pc_position (AUTO,
DESK, FLOOR)}`. `EvaluationOut.setup_price` suma el setup aparte del PC; la cotización de la orden incluye ambos. Las
especificaciones aceptan `style` (detalles visuales del 3D, sin efecto en las reglas).
Las especificaciones por categoría están en `app/modules/assembly/catalog.py` (`SPEC_MODELS`);
`PUT /inventory/parts/{id}` acepta `assembly_category`, `specs` y `price_locked` y, si no se envían, los conserva.

**Precios de ensamble:** precio de venta = costo × (1 + `organizations.assembly_margin_percent` / 100), redondeado hacia
arriba al siguiente múltiplo de $1.000, salvo `price_locked`. Se recalcula al importar, al actualizar costos, al registrar
una entrada de inventario y al cambiar el margen. `PartRead.unit_cost` (y el costo de los movimientos) es `null` para
quien no tiene `inventory:manage`.

### Avisos al cliente por WhatsApp (`/notices`, sprint 3 posterior al MVP)

ERMS arma el mensaje y el enlace `https://wa.me/<celular>?text=<mensaje>`; el asesor lo envía desde WhatsApp Business
(ADR-054). Solo celulares: un teléfono fijo (`+5760…`) o vacío no permite avisar.

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /work-orders/{id}/notices` | `work_orders:read` | 200 `{phone, can_whatsapp, blocked_reason, can_prepare, suggested, pending, drafts[{kind, label, body}], history[]}` |
| `POST /work-orders/{id}/notices` | `work_orders:read` + `customers:notify` | 201 `{notice, url}`: `{kind, body}` (≤ 1500, editable). 422 si el cliente no tiene celular |
| `GET /notices/pending` | `work_orders:read` + `customers:notify` | 200 órdenes por avisar: cotización enviada, equipo listo, no reparado o cancelado, y recordatorio cada 7 días si el equipo sigue sin retirar |
| `GET /notices/templates` | `organization:manage` | 200 `{templates[{kind, label, body, default_body, is_default}], placeholders[], reminder_days}` |
| `PUT /notices/templates/{kind}` | `organization:manage` | `{body}`; 422 si usa un campo que no existe o con formato (`{total:>5}`) |
| `DELETE /notices/templates/{kind}` | `organization:manage` | Restaura el texto original |

Campos: `{cliente}`, `{orden}`, `{equipo}`, `{taller}`, `{telefono_taller}`, `{direccion_taller}`, `{falla}`, `{total}`,
`{saldo}`, `{diagnostico}`, `{fecha_estimada}`, `{motivo}`, `{dias_listo}`, `{garantia_dias}`, `{garantia_hasta}`.

### Agenda remota y en sitio (`/appointments`, PM-04 sprint R1)

Citas fuera del taller (ADR-055). Fechas con zona horaria; se validan en hora de Bogotá: dentro del
horario de servicio del día, el mismo día, nunca en festivo ni en el pasado.

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /appointments/options` | `work_orders:read` | 200 `{hours[], services[] (activos), technicians[], localities[], remote_access_text, can_manage}` |
| `GET /appointments/holidays?from&to` | `work_orders:read` | 200 `[{date, name}]` festivos de Colombia (máximo 62 días) |
| `GET /appointments?from&to&technician_id&include_cancelled` | `work_orders:read` | 200 citas del rango; el técnico sin `appointments:manage` ni `work_orders:assign` solo ve las suyas |
| `POST /appointments` | `work_orders:read` + `appointments:manage` | 201 cita. 422 fuera de horario, festivo, pasado, sin dirección (en sitio) o sin autorización (remota). 409 `appointment_overlap` si el técnico ya tiene otra cita (con `errors[]` de las citas); se agenda enviando `overlap_reason` |
| `GET /appointments/{id}` | `work_orders:read` | 200; 403 si es de otro técnico |
| `PATCH /appointments/{id}` | `work_orders:read` + `appointments:manage` | Mover, cambiar duración, técnico o datos; mismas reglas y 409 |
| `POST /appointments/{id}/cancel` | `work_orders:read` + `appointments:manage` | `{reason}`; la hora queda libre |
| `GET/PUT /appointments/hours` | lectura `work_orders:read`; cambio `organization:manage` | `{days[7]{weekday, opens, closes}}`; vacío = sin servicio |
| `GET /appointments/services` · `POST` · `PUT /{id}` | lectura `work_orders:read`; cambios `organization:manage` | Catálogo `{name, modality, duration_minutes, price?, tax_rate (0/19), price_includes_tax, description, is_active}`; 409 nombre repetido |

### Salud

### `GET /api/v1/health/live`

Indica si el proceso está en ejecución. No consulta dependencias.

**200**

```json
{ "status": "ok", "version": "0.1.0" }
```

### `GET /api/v1/health/ready`

Verifica las dependencias. La base de datos debe responder y estar migrada a la revisión
`head` de Alembic. Redis no es crítico hasta que se introduzca Celery.

| HTTP | Significado |
|---|---|
| 200 | Todos los componentes críticos están operativos |
| 503 | Algún componente crítico falló; el cuerpo indica cuál |

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "checked_at": "2026-11-19T17:30:00Z",
  "components": [
    {
      "name": "database",
      "status": "ok",
      "critical": true,
      "latency_ms": 2.1,
      "detail": "PostgreSQL disponible, migración 0002_identity_access (head)"
    },
    {
      "name": "redis",
      "status": "ok",
      "critical": false,
      "latency_ms": 0.8,
      "detail": "Redis disponible"
    }
  ]
}
```

`components[].status`: `ok` | `error` | `not_configured`.
