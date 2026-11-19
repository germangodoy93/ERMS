# ERMS – Low Level Design (LLD) y convenciones

## 1. Estructura del repositorio

```
ERMS/
├── backend/                  API FastAPI (uv, Python 3.13)
│   ├── app/
│   │   ├── core/             config, logging, database, exceptions (+ security en Sprint 1)
│   │   ├── shared/           Base ORM, mixins, registro de modelos
│   │   ├── modules/          un paquete por dominio (ver HLD §3)
│   │   └── main.py           application factory
│   ├── alembic/              migraciones
│   ├── scripts/              start.sh, export_openapi.py
│   └── tests/{unit,integration}
├── frontend/                 SPA React (npm)
│   └── src/
│       ├── app/              App, rutas, páginas globales
│       ├── components/       componentes compartidos; ui/ = shadcn
│       ├── layouts/          AppLayout, navegación
│       ├── modules/<dominio>/ api.ts, hooks/, pages/, components/, presentation.ts
│       ├── services/         cliente HTTP
│       ├── hooks/ stores/    hooks globales, stores Zustand (desde el Sprint 1)
│       └── types/            contratos de API
├── diagnostic-agent/         Sprint 4: paquete Python `erms_agent` (src layout)
├── infrastructure/           init de PostgreSQL; backups y despliegue
├── docs/                     documentación y docs/api/openapi.json
├── scripts/                  smoke-test.sh, dev-db-setup.sql
└── docker-compose.yml        entorno local
```

Cambios respecto a la estructura sugerida en el documento de requerimientos:

| Cambio | Motivo |
|---|---|
| `modules/catalog` en lugar de `manufacturers` | Fabricantes, categorías y modelos forman un solo dominio. |
| Módulos `organizations`, `audit`, `storage`, `ai`, `health` | Transversales explícitos; `ai` será un puerto con interfaz y sin implementación falsa. |
| `diagnostic-agent/src/erms_agent/` | Un directorio con guion no se puede importar en Python. |
| `docs/api/openapi.json` versionado | Fuente única del contrato; CI verifica que esté actualizado. |

## 2. Convenciones de código

### General

- Código, tablas, columnas y endpoints en **inglés**; textos de interfaz y mensajes de error
  al usuario en **español (es-CO)**.
- Los códigos de estado de orden conservan el vocabulario del negocio: `RECIBIDO`,
  `EN_REPARACION`, …
- Sin TODO sin justificar, sin funciones vacías y sin datos simulados presentados como reales.

### Python (backend y agente)

- Formato y lint: `ruff format` y `ruff check` (reglas en `pyproject.toml`).
- Tipos: `mypy --strict`.
- Nombres: `snake_case` para funciones y variables, `PascalCase` para clases y `UPPER_CASE`
  para constantes.
- Dinero: `Decimal` en Python, `NUMERIC(14,2)` en PostgreSQL y `string` en JSON.
- Fechas: `datetime` con zona horaria, almacenadas en UTC.

### Base de datos

- Tablas en plural `snake_case`; PK `id UUID`.
- Todas las tablas llevan `created_at` y `updated_at` (`timestamptz`).
- Las tablas de negocio llevan `organization_id` con FK e índice.
- Nombres de restricciones deterministas (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`), definidos en
  `app/shared/models.py`.
- Una migración por cambio lógico, revisada a mano; nunca se edita una migración publicada.
- Las migraciones deben pasar `upgrade` → `downgrade` → `upgrade` (prueba de integración).

### API REST

- Prefijo `/api/v1`; recursos en plural con `kebab-case` (`/work-orders`).
- Transiciones de estado como acciones explícitas: `POST /work-orders/{id}/transitions`.
- Paginación: `?page=1&size=20&sort=-created_at&q=` → `{items, total, page, size}`.
- Errores: RFC 9457 (ver `app/core/exceptions.py`).

### TypeScript (frontend)

- ESLint + Prettier (con orden de clases Tailwind) y `strict` + `noUncheckedIndexedAccess`.
- Componentes en `PascalCase.tsx`; hooks en `useXxx.ts`; alias `@/` → `src/`.
- Sin lógica de negocio en componentes: las llamadas HTTP van en `modules/*/api.ts`, el
  estado de servidor en hooks de TanStack Query y los textos y tonos en `presentation.ts`.

### Git

- Rama `main` protegida; ramas cortas `feat/…`, `fix/…`, `docs/…`, `chore/…`.
- Commits con [Conventional Commits](https://www.conventionalcommits.org/):
  `feat(work-orders): …`.
- Pull request con CI en verde antes de fusionar.
- Ganchos locales con `pre-commit` (`.pre-commit-config.yaml`); bloquean archivos `.env`.

## 3. Definición de terminado (DoD)

Una historia está terminada cuando:

1. El código cumple estas convenciones y pasa lint y tipos.
2. Tiene pruebas unitarias y de integración cuando hay base de datos, y todas pasan en CI.
3. Las migraciones se probaron en ambos sentidos.
4. Los endpoints están documentados en OpenAPI y `docs/api/openapi.json` está actualizado.
5. `ERMS-API.md` y los documentos afectados están actualizados.
6. Se cumplen los criterios de aceptación del backlog.
