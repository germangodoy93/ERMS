# ERMS – Plan de pruebas

## 1. Niveles

| Nivel | Herramienta | Alcance | Dónde se ejecuta |
|---|---|---|---|
| Unitarias backend | pytest | Servicios, validaciones, manejadores de error, checks con dobles de prueba | Local y CI |
| Integración backend | pytest + PostgreSQL real | Migraciones (upgrade/downgrade), repositorios, transacciones | Local (con `ERMS_TEST_DATABASE_URL`) y CI |
| Unitarias frontend | Vitest + Testing Library | Presentación, páginas con API simulada | Local y CI |
| Contrato | Vitest + `docs/api/openapi.json`; CI verifica que el JSON coincide con el código | Tipos del frontend frente a esquemas del backend | Local y CI |
| Humo E2E | `scripts/smoke-test.sh` | Web → proxy → API → PostgreSQL | CI con Docker Compose y local |
| E2E de UI | Playwright (a evaluar en el Sprint 6) | Flujos críticos: recepción → entrega | CI |

## 2. Reglas

- Cobertura mínima del 80 % en `service.py` de cada módulo.
- Toda migración se prueba en ambos sentidos.
- Las pruebas de integración usan una base de datos **desechable**: se borra y se recrea.
- Las advertencias se tratan como errores (`filterwarnings = error`); las excepciones
  están documentadas.
- Las pruebas no usan datos que parezcan reales: nombres, documentos e IMEI son
  evidentemente ficticios.

## 3. Pruebas del Sprint 0

| Prueba | Archivo | Verifica |
|---|---|---|
| Normalización de `DATABASE_URL` y CORS | `backend/tests/unit/test_config.py` | Railway entrega `postgres://`; se fuerza psycopg |
| Formato de log JSON | `backend/tests/unit/test_logging.py` | Campos y contexto |
| Lógica de readiness | `backend/tests/unit/test_health.py` | Crítico vs no crítico; 200/503 |
| Errores RFC 9457 | `backend/tests/unit/test_health.py` | 404 y 500 sin filtrar detalles |
| Swagger y OpenAPI | `backend/tests/unit/test_health.py` | `/api/v1/docs` y `openapi.json` = 200 |
| Servidores inalcanzables | `backend/tests/unit/test_health.py` | BD y Redis caídos se reportan como `error` |
| Migraciones | `backend/tests/integration/test_database.py` | upgrade → downgrade → upgrade; readiness detecta migración pendiente |
| Presentación | `frontend/src/modules/system/presentation.test.ts` | Etiquetas, hora de Bogotá |
| Página de estado | `frontend/src/modules/system/pages/SystemStatusPage.test.tsx` | Estados OK, no disponible y sin conexión |
| Contrato | `frontend/src/types/api.contract.test.ts` | Enums y campos iguales al OpenAPI |
| Humo E2E | `scripts/smoke-test.sh` | 6 verificaciones de punta a punta |
