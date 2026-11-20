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

## 4. Pruebas del Sprint 1

Resultado local del 2026-11-19: **71 pruebas de backend** (93 % de cobertura; servicios entre
87 % y 100 %) y **45 de frontend**, todas en verde.

| Prueba | Archivo | Verifica |
|---|---|---|
| Criptografía | `backend/tests/unit/test_security.py` | Argon2id; JWT expirado, con otra clave, de otro tipo o sin firma (`alg=none`) rechazado; política de contraseñas; `JWT_SECRET` corto rechazado |
| Esquema | `backend/tests/integration/test_database.py` | Migraciones en ambos sentidos; catálogo de permisos sembrado; **modelos ORM = migraciones** (autogenerate vacío) |
| Login y sesión | `backend/tests/integration/test_auth_api.py` | Cookie segura; mismo error para correo inexistente o clave errada; bloqueo tras 5 fallos; usuario inactivo; rotación; gracia de 30 s y luego detección de robo; expiración absoluta; logout invalida el access token |
| Contraseñas | `backend/tests/integration/test_auth_api.py` | Contraseña temporal bloquea la app hasta cambiarla; política aplicada; recuperación por correo de un solo uso que cierra sesiones |
| Usuarios | `backend/tests/integration/test_users_api.py` | Alta con correo normalizado; duplicados (409); supervisor sin escalada a Administrador; técnico/recepción sin acceso; último administrador protegido; desactivar cierra sesiones; filtros, paginación y comodines LIKE; **aislamiento entre organizaciones** |
| Roles y auditoría | `backend/tests/integration/test_roles_audit_api.py` | Cambios de permisos efectivos sin nuevo token; rol Administrador inmutable; filtros de auditoría por acción, entidad, actor y fechas |
| Bootstrap | `backend/tests/integration/test_cli.py` | Crea organización, sede, roles y administrador; no se ejecuta dos veces; aplica la política de contraseñas |
| Cliente HTTP | `frontend/src/services/http.test.ts` | Bearer automático; un solo refresh para peticiones concurrentes; reintento tras refresh; sesión limpia si el refresh falla; sin refresh tras login fallido |
| Rutas | `frontend/src/modules/auth/components/RouteGuards.test.tsx` | Carga, redirección a login con `next`, cambio de contraseña obligatorio, acceso restringido |
| Login | `frontend/src/modules/auth/pages/LoginPage.test.tsx` | Validaciones; redirección a `next`; **bloqueo de open redirect**; mensaje del servidor |
| Usuarios (UI) | `frontend/src/modules/users/pages/UsersPage.test.tsx` | Estados; supervisor sin acciones sobre administradores y con el rol Administrador deshabilitado; solo lectura sin acciones |
| Humo de autenticación | `scripts/smoke-auth.sh` (CI, Docker Compose) | Bootstrap → login por el proxy web → correo de recuperación entregado a Mailpit |

## 5. Pruebas del Sprint 2

Resultado local del 2026-11-19: **129 pruebas de backend** (94 % de cobertura; servicios entre
85 % y 100 %) y **79 de frontend**, todas en verde. Además se recorrió el flujo completo por el
proxy web contra PostgreSQL: política → cliente → equipo → anonimización.

| Prueba | Archivo | Verifica |
|---|---|---|
| Identificadores colombianos | `backend/tests/unit/test_identifiers.py` | Dígito de verificación del NIT contra NIT públicos; CC, CE, pasaporte; teléfonos (celular, fijo 60X, +57, extranjeros); IMEI con Luhn; serial; búsqueda sin tildes |
| Plantilla de la política | `backend/tests/unit/test_identifiers.py` | Datos del responsable, plazos de 10 y 15 días hábiles, SIC; textos de autorización con la versión |
| Esquema | `backend/tests/integration/test_database.py` | Migración 0003 en ambos sentidos; modelos = migraciones (incluye índice GIN trigram) |
| Datos del taller y política | `backend/tests/integration/test_customers_api.py` | NIT y teléfono normalizados; no se publica con datos faltantes; versiones; solo el administrador |
| Clientes | `backend/tests/integration/test_customers_api.py` | Sin política no hay registro; autorización obligatoria; validaciones; documento opcional pero único; búsqueda por nombre sin tildes, documento, teléfono y comodines; edición; revocar/otorgar con historial de solo inserción; **anonimización sin datos personales en la auditoría**; permisos por rol; aislamiento entre talleres |
| Equipos y catálogo | `backend/tests/integration/test_devices_api.py` | Catálogo precargado; permisos de catálogo; filtros de modelos; IMEI y serial normalizados; IMEI inválido o repetido; serial único por modelo; cliente sin autorización bloqueado; búsqueda; notas borradas al anonimizar; aislamiento entre talleres |
| Producción | `backend/tests/unit/test_health.py` | Swagger, ReDoc y OpenAPI responden 404 en producción |
| Bootstrap | `backend/tests/integration/test_cli.py` | Precarga los fabricantes |
| Contrato | `frontend/src/types/api.contract.test.ts` | 24 esquemas y 4 enums nuevos iguales al OpenAPI |
| Presentación | `frontend/src/modules/customers/presentation.test.ts` | Formato de teléfono y documento; estado del cliente; IMEI (igual al backend) |
| Clientes (UI) | `frontend/src/modules/customers/pages/CustomersPage.test.tsx` | Listado; registro bloqueado sin política; autorización obligatoria y consentimientos enviados; técnico sin botón de registro |

## 6. Pruebas del Sprint 3

Resultado local del 2026-11-20: **142 pruebas de backend** y **99 de frontend**, todas en
verde; módulos nuevos entre 90 % y 100 % de cobertura. Además se recorrió el flujo completo por
el proxy web: condiciones → cliente con autorización de fotos → equipo → orden → acta PDF →
foto → estados → entrega.

| Prueba | Archivo | Verifica |
|---|---|---|
| Esquema | `backend/tests/integration/test_database.py` | Migración 0004 en ambos sentidos; modelos = migraciones |
| Condiciones | `backend/tests/integration/test_work_orders_api.py` | Sin condiciones no hay recepción; plantilla; solo el administrador publica |
| Recepción | `test_work_orders_api.py` | Numeración consecutiva por taller; dinero con dos decimales; accesorios y "Otro"; anticipo exige medio; equipo de otro cliente; una sola orden abierta por equipo; técnico no crea; cliente sin autorización |
| Estados | `test_work_orders_api.py` | Flujo completo con roles; motivos obligatorios; transiciones inválidas; entrega a tercero con documento; orden cerrada inmodificable |
| Asignación | `test_work_orders_api.py` | Solo técnicos activos; el técnico no mueve órdenes de otro; al tomar una orden sin asignar se la asigna |
| Acta | `test_work_orders_api.py` | PDF descargable; texto con marcado se escapa |
| Fotos | `test_work_orders_api.py` | Exigen autorización; **GPS eliminado**; redimensionadas; no imágenes y GIF rechazados; nombre de archivo saneado; límites de cantidad y tamaño; borrar |
| Formatos del PDF | `backend/tests/unit/test_identifiers.py` | Pesos colombianos y teléfonos |
| Contrato | `frontend/src/types/api.contract.test.ts` | 14 esquemas y 5 enums nuevos |
| Presentación | `frontend/src/modules/workorders/presentation.test.ts` | Pesos, lectura de montos escritos a mano, motivos iguales al backend |
| Detalle (UI) | `frontend/src/modules/workorders/pages/WorkOrderDetailPage.test.tsx` | Solo las acciones permitidas por la API; motivo obligatorio al devolver de control de calidad; aviso de modo demostración |

**Windows:** si la terminal abre la carpeta como `c:\...` (minúscula), Vitest carga dos copias de
sí mismo y las pruebas de interfaz fallan con `Invalid Chai property: toBeInTheDocument`.
Ejecute las pruebas desde una terminal en `C:\...` (ver ERMS-DEVOPS).
