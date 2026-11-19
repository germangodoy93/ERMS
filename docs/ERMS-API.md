# ERMS – Contratos de API

- **Base:** `/api/v1`
- **Swagger UI:** `/api/v1/docs` · **ReDoc:** `/api/v1/redoc` · **OpenAPI:** `/api/v1/openapi.json`
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
| `conflict` | 409 | Unicidad (p. ej. correo ya registrado) |
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
`user.temporary_password_set`, `role.permissions_changed`, `organization.bootstrapped`.
Las contraseñas y los tokens nunca se registran.

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
