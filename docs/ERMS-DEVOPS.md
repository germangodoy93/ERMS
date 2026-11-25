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
| PyJWT / pwdlib (argon2) | 2.15.1 / 0.4.2 | Sprint 1 (ADR-002) |
| email-validator | 2.4.0 | Valida `EmailStr`; rechaza dominios reservados como `.test` y `.local` |
| zustand / react-hook-form / zod | 5.1.0 / 7.92.0 / 4.6.7 | Sprint 1 |
| @hookform/resolvers / sonner | 7.0.7 / 2.0.8 | Sprint 1 |
| Mailpit (imagen) | v1.33.1 | Correo de desarrollo; no se usa la v1.34.0 por ser de hace 2 días |
| reportlab | 5.1.0 | Sprint 3, acta en PDF. Licencia BSD. Sin tipos: `mypy` lo ignora (`pyproject.toml`) |
| Pillow | 13.0.0 | Dependencia de reportlab; también valida y limpia las fotos (licencia MIT-CMU) |
| PyInstaller | 6.22.3 | Sprint 4, solo para construir el agente (licencia GPL con excepción que permite distribuir el ejecutable) |
| three / @types/three | **0.187.0** (fijadas) | Sprint E2, visor 3D del ensamble. Licencia MIT. Va en su propio fragmento de carga diferida |
| Playwright (`@playwright/test`) | **1.65.0** (fijada) | Sprint 6, E2E en `e2e/`. No se usa la 1.65.1 por ser muy reciente. Licencia Apache 2.0 |
| python-multipart | **0.0.33** (fijada) | Subida de fotos en FastAPI. No se usa la 0.0.34 por ser de hace 4 días |

### Decisiones de compatibilidad

- **openapi-typescript** (7.13) exige `typescript@^5`. No se fuerza el peer: los tipos se
  escriben a mano y `src/types/api.contract.test.ts` los compara con `docs/api/openapi.json`
  (ADR-008).
- **httpx en TestClient:** Starlette 1.10 avisa que `httpx` está deprecado en `TestClient` y
  recomienda `httpx2`. Ese paquete aún no se ha evaluado, así que se mantiene `httpx` y se
  filtra solo esa advertencia en `pyproject.toml`. Todas las demás advertencias son errores.
- **shadcn CLI:** necesita el alias `@/*` también en el `tsconfig.json` raíz. Aun así, la
  versión 4.23 **instala un paquete npm ajeno llamado `cn`** y lo importa en los componentes.
  Después de cada `npx shadcn add …` hay que ejecutar `npm uninstall cn` y reemplazar
  `from "cn"` por `from "@/lib/utils"` en `src/components/ui/`.
- **Radix en pruebas:** jsdom no trae `ResizeObserver`; `src/test/setup.ts` define un stub.
- **Vitest en Windows:** si el directorio actual usa la unidad en minúscula (`c:\Users\...`,
  como lo abre a veces VS Code), Vitest carga dos instancias de `vitest` y fallan los
  matchers de jest-dom (`Invalid Chai property`). Solución: abrir la terminal en `C:\...` o
  ejecutar `cmd /c "cd /d C:\ruta\frontend && npm test"`. En CI (Linux) no ocurre.
- **PostgreSQL:** la migración 0003 ejecuta `CREATE EXTENSION IF NOT EXISTS pg_trgm`. El
  usuario de Railway, Docker y CI puede crearla; en un servidor propio requiere un rol con ese
  privilegio.

## 2. Entornos

| Entorno | Cómo se ejecuta | Base de datos |
|---|---|---|
| Local con Docker | `docker compose up --build` | Contenedor `postgres:17-alpine` (puerto host 5433) |
| Local sin Docker | `uv run uvicorn` + `npm run dev` | PostgreSQL 17 instalado (puerto 5432) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | Servicio PostgreSQL efímero |
| Producción | Railway, desplegado desde el 2026-11-19 (Sprint 1) | PostgreSQL gestionado por Railway |

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
| `JWT_SECRET` | **Sí** | Clave de firma de los access tokens, mínimo 32 caracteres (`openssl rand -hex 32`). Cambiarla cierra todas las sesiones. |
| `ACCESS_TOKEN_TTL_MINUTES` · `SESSION_MAX_HOURS` · `SESSION_IDLE_MINUTES` | No | 15 · 12 · 120 |
| `LOGIN_MAX_ATTEMPTS` · `LOGIN_LOCKOUT_MINUTES` | No | 5 · 15 (por cuenta) |
| `LOGIN_IP_MAX_FAILURES` · `LOGIN_IP_WINDOW_MINUTES` | No | 20 · 15 (por IP, en memoria del proceso) |
| `PASSWORD_MIN_LENGTH` · `PASSWORD_RESET_TTL_MINUTES` | No | 12 · 30 |
| `REFRESH_COOKIE_SECURE` | No | Por defecto `true` solo en producción |
| `FRONTEND_URL` | Sí en producción | Base de los enlaces enviados por correo (p. ej. el dominio de `web` en Railway) |
| `SMTP_HOST` · `SMTP_PORT` · `SMTP_USERNAME` · `SMTP_PASSWORD` · `SMTP_STARTTLS` · `SMTP_FROM` | Para recuperar contraseñas | Sin `SMTP_HOST` no se envían correos: se registra el intento sin el enlace. |
| `S3_BUCKET` · `S3_ENDPOINT` · `S3_ACCESS_KEY_ID` · `S3_SECRET_ACCESS_KEY` | Para guardar fotos | Bucket de Railway (ADR-053). Van juntas: si falta una, la API no arranca. En Railway se referencian desde el bucket: `${{Bucket.BUCKET}}`, `${{Bucket.ENDPOINT}}`, `${{Bucket.ACCESS_KEY_ID}}`, `${{Bucket.SECRET_ACCESS_KEY}}`. |
| `S3_REGION` · `S3_ADDRESSING_STYLE` | No | `auto` · `virtual` (usar `path` solo si la pestaña *Credentials* del bucket lo indica) |
| `ATTACHMENTS_DIR` | No | Sin `S3_*`: carpeta local de fotos (por defecto `var/attachments`). En Railway es efímera: **modo demostración**. |
| `ATTACHMENT_MAX_BYTES` · `ATTACHMENT_MAX_PER_ORDER` | No | 10 MB · 20 |
| `AGENT_DOWNLOAD_URL` | No | Descarga del agente (por defecto, el último release de GitHub) |
| `AGENT_PAIRING_MINUTES` · `AGENT_TOKEN_MINUTES` | No | 30 · 15 |
| `ERMS_ADMIN_PASSWORD` | Solo `bootstrap` | Contraseña temporal del primer administrador |
| `ERMS_TEST_DATABASE_URL` | Solo pruebas | Base **desechable** para las pruebas de integración |

Frontend: `VITE_API_PROXY_TARGET` (proxy de desarrollo) y `VITE_API_BASE_URL` (opcional).
Servidor web de producción: `API_UPSTREAM` y `PORT`.

## 4. CI (GitHub Actions)

`agent-release.yml` construye el agente en Windows cuando cambia `diagnostic-agent/` y lo
publica en el release `agent-v<versión>` con su SHA256. La descarga estable es
`https://github.com/germangodoy93/ERMS/releases/latest/download/erms-agente.exe`. Para publicar
una versión nueva, se cambia `VERSION` en `diagnostic-agent/erms_agent/__init__.py`.

Construcción local (Windows):

```powershell
cd diagnostic-agent; python -m uv sync
python -m uv run pyinstaller --onefile --console --name erms-agente --distpath build/dist --workpath build/work --specpath build erms_agent/__main__.py
.\build\dist\erms-agente.exe --server http://localhost:5173   # contra el entorno local
```

| Job | Pasos |
|---|---|
| `backend` | ruff, mypy, pytest (unitarias + integración contra PostgreSQL), verificación de que `docs/api/openapi.json` está actualizado |
| `agent` | ruff, mypy, pytest del agente (Linux; las consultas se prueban con salidas de ejemplo) |
| `frontend` | eslint, prettier, tsc, vitest, build |
| `docker` | `docker compose up --wait` + `scripts/smoke-test.sh` + `scripts/smoke-auth.sh` (bootstrap → login por el proxy web → correo de recuperación en Mailpit) + E2E con Playwright (Chromium) sobre el mismo stack; build de las imágenes `prod`. Si el E2E falla, el reporte y la traza quedan como artefacto `playwright-report` (7 días). |

### Prueba E2E en local

Con el backend y Vite corriendo (`http://localhost:5173`):

```powershell
cd e2e; npm ci; npx playwright install chromium
$env:E2E_EMAIL = "admin@example.com"; $env:E2E_PASSWORD = "<contraseña>"
npx playwright test          # agrega --headed para ver el navegador
```

Crea datos ficticios (repuesto, modelo, cliente, órdenes) en la organización del usuario: úsela
solo en entornos desechables, **nunca contra producción**. Si el usuario tiene contraseña
temporal, la prueba la cambia por `E2E_NEW_PASSWORD`.

### Pruebas de integración en Windows sin Docker

El PostgreSQL 17 instalado trae `initdb` y `pg_ctl`, así que se puede crear un clúster
**desechable** en otro puerto sin tocar el servidor principal ni conocer su contraseña:

```powershell
$pg = "C:\Program Files\PostgreSQL\17\bin"; $data = "$env:TEMP\erms-pg"
& "$pg\initdb.exe" -D $data -U erms --auth=trust -E UTF8 --locale=C
& "$pg\pg_ctl.exe" -D $data -o "-p 54329 -c listen_addresses=127.0.0.1" -l "$data.log" start
& "$pg\createdb.exe" -h 127.0.0.1 -p 54329 -U erms erms_test
cd backend; $env:ERMS_TEST_DATABASE_URL = "postgresql://erms@127.0.0.1:54329/erms_test"; uv run pytest
& "$pg\pg_ctl.exe" -D $data stop   # al terminar
```

## 5. Despliegue en Railway

El repositorio es un monorepo: **cada servicio debe apuntar a su carpeta** mediante *Root
Directory*. Sin eso, Railway construye la raíz con Railpack y falla con
`railpack process exited with an error`. Railway usa el Dockerfile automáticamente cuando lo
encuentra en el Root Directory y construye la última etapa (`prod`).

La configuración se hace en el panel, sin `railway.json`, porque Railway deprecó "Config as
Code" (vigente solo hasta el 2026-12-01).

### Catálogo de ensamble (datos privados)

El catálogo con precios **no está en el repositorio** (es público). El archivo se genera a partir
del simulador del taller y se guarda en `data/private/catalogo-ensamble.json` (carpeta excluida
de Git). Para cargarlo, en producción o en local: *Ensamble de PC → Importar catálogo* con un
usuario administrador. La importación crea o actualiza por código (SKU) con el **costo** del proveedor y nunca
cambia existencias. El precio de venta es costo + margen (15 % por defecto, en *Datos del
taller*). Para una lista nueva del proveedor: *Plantilla de costos* → cambiar la columna Costo
en Excel → guardar como CSV → *Actualizar costos*.

### Servicio `Postgres`

*New → Database → PostgreSQL*.

**Backups (R-09, plan Pro):** en el servicio `Postgres`, pestaña *Backups*, activar los
programas diario y semanal (Railway conserva cada copia según el programa). Antes de una
migración riesgosa, crear un backup manual desde la misma pestaña.

Simulacro de restauración (una vez al mes y antes de salir en vivo):

1. En el proyecto, duplicar el entorno `production` como `restore-drill` (*Environments → New →
   Duplicate*), para no tocar los datos reales.
2. En `restore-drill`, servicio `Postgres` → *Backups*, restaurar el backup más reciente.
3. Abrir la web de `restore-drill`, iniciar sesión y revisar que estén las últimas órdenes y
   pagos. Anotar la fecha y el resultado.
4. Eliminar el entorno `restore-drill`.

Restaurar en `production` reemplaza los datos actuales: solo ante una pérdida real.

### Servicio `backend` (nombre exacto: `backend`, se usa en la red privada)

| Ajuste (Settings) | Valor |
|---|---|
| Source → Root Directory | `/backend` |
| Build → Watch Paths | `/backend/**` |
| Deploy → Pre-deploy Command | `alembic upgrade head` |
| Deploy → Healthcheck Path | `/api/v1/health/ready` |
| Networking | **Sin dominio público** |

| Variable | Valor |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referencia, no se copia) |
| `ENVIRONMENT` | `production` |
| `PORT` | `8000` (puerto fijo para la red privada) |
| `FORWARDED_ALLOW_IPS` | `*` (la API solo es accesible por la red privada) |
| `JWT_SECRET` | Valor aleatorio propio de 64 caracteres hex (*Generate* en Railway o `openssl rand -hex 32`) |
| `FRONTEND_URL` | `https://<dominio-del-servicio-web>` |
| `SMTP_*` | Cuando se defina el proveedor gratuito; sin ellas no se envían correos de recuperación |

Primer administrador, una sola vez. Se ejecuta desde la pestaña **Console** del servicio
`backend` en Railway (o con `railway ssh`). Esa consola no hereda el `PATH` de la imagen, así
que hay que usar el Python del entorno virtual por su ruta completa:

```bash
bind 'set enable-bracketed-paste off'   # escribirlo a mano: evita que se pegue "^[[200~"
/opt/venv/bin/python -m app.cli bootstrap \
  --org-name "<Razón social>" --org-slug <slug> --admin-email <correo> --admin-name "<Nombre>"
# Pide la contraseña temporal por consola (no queda en el historial)
```

### Servicio `web`

| Ajuste (Settings) | Valor |
|---|---|
| Source → Root Directory | `/frontend` |
| Build → Watch Paths | `/frontend/**` |
| Deploy → Healthcheck Path | `/` |
| Networking | *Generate Domain* con puerto destino `8080` |

| Variable | Valor |
|---|---|
| `API_UPSTREAM` | `http://backend.railway.internal:8000` |
| `PORT` | `8080` |

### Notas

- **Un repositorio, dos servicios.** Ambos se conectan al mismo repo y cada uno usa su
  *Root Directory*. Un solo servicio no puede ejecutar la web y la API.
- **Variables sugeridas:** Railway propone las variables que encuentra en `.env.example`
  (`POSTGRES_*`, `LOG_JSON`…). Son para Docker local; no se usan. Conviene cargar las de las
  tablas con el *Raw Editor*.
- `RAILWAY_ENVIRONMENT` la crea Railway; la app lee **`ENVIRONMENT`**, que debe definirse.
- **Renombrar un servicio no cambia su dirección privada.** Se edita en *Settings →
  Networking → Private Networking* para que sea `backend.railway.internal`.
- Diagnóstico rápido desde el dominio de `web`: un **503 sin contenido** en `/api/*` indica que
  falta `API_UPSTREAM`, porque Caddy no tiene a dónde reenviar. Si `/api/v1/health/ready`
  dice "no tiene migraciones", falta el *Pre-deploy Command*.
- La API no tiene dominio público: el navegador solo habla con `web`, y `/api` viaja por la
  red privada (mismo origen, sin CORS).
- Los Dockerfiles no usan cache mounts de BuildKit: Railway solo los acepta con un `id`
  prefijado por el ID del servicio.
- La red privada de Railway solo existe en tiempo de ejecución, no durante el build.
- Los entornos creados después del 16-oct-2025 resuelven IPv4 en la red privada, por eso el
  backend escucha en `0.0.0.0`. En un entorno anterior (solo IPv6) habría que escuchar en `::`.

## 6. Secretos

- Nunca en el repositorio: `.env` está en `.gitignore` y bloqueado por pre-commit.
- Local: archivos `.env` a partir de `.env.example`.
- CI: contraseñas efímeras solo para el contenedor de pruebas.
- Producción: variables de Railway.
