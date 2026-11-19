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
`catalog.model_updated`, `device.created`, `device.updated`.
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
