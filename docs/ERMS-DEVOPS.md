# ERMS – DevOps

## 1. Versiones fijadas

Las versiones exactas están en `backend/uv.lock` y `frontend/package-lock.json`, y las
dependencias directas del frontend se instalan con `--save-exact`. Estas son las versiones
verificadas el 2026-11-19:

| Componente | Versión | Nota |
|---|---|---|
| Python | 3.13 | Requerimiento |
| uv | 0.13.9 | Gestor de dependencias Python |
| FastAPI / Starlette | 0.165.0 / 1.10.0 | |
| SQLAlchemy | 2.1.9 | |
| Pydantic / pydantic-settings | 2.14.4 / 2.16.3 | |
| Alembic | 1.20.1 | |
| psycopg | 3.3.9 | Driver síncrono (ADR-001) |
| redis-py | 8.1.0 | |
| Node.js | 24 (LTS) | Mínimo 22.12 por Vite 8 |
| React / React DOM | 19.3.1 | |
| Vite | 8.3.8 | |
| TypeScript | **6.0.3** | No 7.0: `typescript-eslint` 8.73 exige `<6.1` (ADR-009) |
| Tailwind CSS | 4.3.5 | |
| shadcn CLI / radix-ui | 4.23.0 / 1.8.1 | |
| React Router | 8.5.2 | |
| TanStack Query | 5.108.1 | |
| Vitest | 5.1.1 | |
| PostgreSQL (imagen) | 17-alpine | Igual a la versión local instalada |
| Redis (imagen) | 8-alpine | |
| Caddy (imagen) | 2.10-alpine | Servidor web de producción |

### Decisiones de compatibilidad

- **openapi-typescript** (7.13) exige `typescript@^5`. No se fuerza el peer: los tipos se
  escriben a mano y `src/types/api.contract.test.ts` los compara con `docs/api/openapi.json`
  (ADR-008).
- **httpx en TestClient:** Starlette 1.10 avisa que `httpx` está deprecado en `TestClient` y
  recomienda `httpx2`. Ese paquete aún no se ha evaluado, así que se mantiene `httpx` y se
  filtra solo esa advertencia en `pyproject.toml`. Todas las demás advertencias son errores.
- **shadcn CLI:** necesita el alias `@/*` también en el `tsconfig.json` raíz. Sin él crea
  archivos en una carpeta `@/` e instala un paquete npm ajeno llamado `cn`.

## 2. Entornos

| Entorno | Cómo se ejecuta | Base de datos |
|---|---|---|
| Local con Docker | `docker compose up --build` | Contenedor `postgres:17-alpine` (puerto host 5433) |
| Local sin Docker | `uv run uvicorn` + `npm run dev` | PostgreSQL 17 instalado (puerto 5432) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | Servicio PostgreSQL efímero |
| Producción | Railway (Sprint 6) | PostgreSQL gestionado por Railway |

## 3. Variables de entorno (backend)

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | Sí | `postgres://` o `postgresql://`; se fuerza el driver psycopg |
| `ENVIRONMENT` | No | `development` · `test` · `production` |
| `REDIS_URL` | No (hasta el Sprint 3) | Broker de Celery |
| `CORS_ORIGINS` | No | Lista separada por comas; vacía = sin CORS (mismo origen) |
| `LOG_LEVEL` / `LOG_JSON` | No | `INFO` / `true` |
| `RUN_MIGRATIONS` | No | `true` aplica `alembic upgrade head` al arrancar (Compose) |
| `PORT` | No | Puerto HTTP; Railway lo inyecta |
| `ERMS_TEST_DATABASE_URL` | Solo pruebas | Base **desechable** para las pruebas de integración |

Frontend: `VITE_API_PROXY_TARGET` (proxy de desarrollo) y `VITE_API_BASE_URL` (opcional).
Servidor web de producción: `API_UPSTREAM` y `PORT`.

## 4. CI (GitHub Actions)

| Job | Pasos |
|---|---|
| `backend` | ruff, mypy, pytest (unitarias + integración contra PostgreSQL), verificación de que `docs/api/openapi.json` está actualizado |
| `frontend` | eslint, prettier, tsc, vitest, build |
| `docker` | `docker compose up --wait` + `scripts/smoke-test.sh`; build de las imágenes `prod` |

## 5. Despliegue en Railway (plan para el Sprint 6)

| Servicio Railway | Origen | Configuración |
|---|---|---|
| `backend` | `backend/Dockerfile` (target `prod`) | Pre-deploy: `alembic upgrade head`; healthcheck `/api/v1/health/ready`; `DATABASE_URL=${{Postgres.DATABASE_URL}}` |
| `web` | `frontend/Dockerfile` (target `prod`) | `API_UPSTREAM=http://backend.railway.internal:8000`; dominio público con HTTPS de Railway |
| `Postgres` | Plantilla de Railway | Backups programados (R-09) |
| `Redis` | Plantilla de Railway | Desde el Sprint 3 |

La API no necesita dominio público: solo `web` se expone, y `/api` viaja por la red privada.

## 6. Secretos

- Nunca en el repositorio: `.env` está en `.gitignore` y bloqueado por pre-commit.
- Local: archivos `.env` a partir de `.env.example`.
- CI: contraseñas efímeras solo para el contenedor de pruebas.
- Producción: variables de Railway.
