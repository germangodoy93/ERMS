# ERMS – Electronic Repair Management System

Plataforma para gestionar un centro de diagnóstico, mantenimiento y reparación de
computadores, celulares, tablets y consolas: desde la recepción del equipo hasta su entrega y
garantía.

**Estado:** Sprint 0 (fundaciones). Ver [roadmap](docs/ERMS-ROADMAP.md).

| Capa | Tecnología |
|---|---|
| Web | React 19 · Vite 8 · TypeScript 6 · Tailwind 4 · shadcn/ui · TanStack Query |
| API | Python 3.13 · FastAPI · SQLAlchemy 2.1 · Pydantic 2 · Alembic |
| Datos | PostgreSQL 17 · Redis 8 |
| Infraestructura | Docker Compose (local y CI) · GitHub Actions · Railway (producción) |

## Opción A: con Docker (recomendada)

Requisitos: Docker Desktop con WSL2 (Windows) o Docker Engine con Compose v2.

```bash
cp .env.example .env          # y define POSTGRES_PASSWORD
docker compose up --build
```

| Servicio | URL |
|---|---|
| Web | http://localhost:5173 |
| API (Swagger) | http://localhost:8000/api/v1/docs |
| PostgreSQL | `localhost:5433` (usuario y base `erms`) |

Las migraciones se aplican automáticamente al arrancar el backend. Para verificar la
comunicación de punta a punta (Git Bash o Linux):

```bash
bash scripts/smoke-test.sh     # debe terminar en "All checks passed"
```

Pruebas dentro de los contenedores:

```bash
docker compose exec backend pytest
docker compose exec frontend npm test
```

## Opción B: sin Docker

Requisitos: Python 3.13, [uv](https://docs.astral.sh/uv/) (`pip install uv`), Node.js ≥ 22.12 y
PostgreSQL 17.

### 1. Base de datos (solo una vez)

Crea un usuario y las bases `erms` y `erms_test` con tu usuario `postgres`. Reemplaza
`CHANGE_ME` por una contraseña propia:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost -v pwd="'CHANGE_ME'" -f scripts/dev-db-setup.sql
```

### 2. Backend

```powershell
cd backend
copy .env.example .env         # y reemplaza CHANGE_ME por la contraseña anterior
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend (otra terminal)

```powershell
cd frontend
npm ci
npm run dev                    # http://localhost:5173 (proxy /api → :8000)
```

## Calidad

| Comando | Qué hace |
|---|---|
| `cd backend; uv run pytest` | Pruebas unitarias. Las de integración se ejecutan si `ERMS_TEST_DATABASE_URL` está definida. |
| `cd backend; uv run ruff check .; uv run mypy app tests` | Lint y tipos |
| `cd frontend; npm test` | Vitest |
| `cd frontend; npm run lint; npm run typecheck` | ESLint y TypeScript |
| `pre-commit install` | Activa los ganchos locales (requiere `pip install pre-commit`) |

Cuando cambien los esquemas de la API, regenera el contrato:

```powershell
cd backend; uv run python -m scripts.export_openapi ../docs/api/openapi.json
```

## Documentación

| Documento | Contenido |
|---|---|
| [ERMS-HLD](docs/ERMS-HLD.md) | Arquitectura, decisiones (ADR) y riesgos |
| [ERMS-LLD](docs/ERMS-LLD.md) | Estructura, convenciones y definición de terminado |
| [ERMS-ERD](docs/ERMS-ERD.md) | Modelo de datos |
| [ERMS-API](docs/ERMS-API.md) | Contratos de API |
| [ERMS-BACKLOG](docs/ERMS-BACKLOG.md) | Historias y criterios de aceptación |
| [ERMS-ROADMAP](docs/ERMS-ROADMAP.md) | Plan de 90 días |
| [ERMS-DEVOPS](docs/ERMS-DEVOPS.md) | Versiones, entornos, CI y despliegue |
| [ERMS-TEST-PLAN](docs/ERMS-TEST-PLAN.md) | Estrategia de pruebas |
