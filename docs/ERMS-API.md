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
| Paginación | `?page=1&size=20&sort=-created_at&q=` → `{items, total, page, size}` |
| Autenticación (Sprint 1) | `Authorization: Bearer <access_token>`; refresh token en cookie `httpOnly` |

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
| `validation_error` | 422 | Entrada inválida |
| `not_found` | 404 | Recurso o ruta inexistente |
| `conflict` | 409 | Violación de regla de negocio o unicidad |
| `permission_denied` | 403 | RBAC |
| `internal_error` | 500 | Error inesperado; no expone detalles internos |

## Endpoints implementados

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
      "detail": "PostgreSQL disponible, migración 0001_initial (head)"
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
