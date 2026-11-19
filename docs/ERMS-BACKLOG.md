# ERMS – Product Backlog

Prioridad: **P1** imprescindible para el MVP · **P2** importante · **P3** deseable.

## Sprint 0 – Fundaciones

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S0-01 | Como equipo, quiero un repositorio con estructura y convenciones definidas | Estructura según LLD; `.gitignore`, `.editorconfig`, pre-commit | ✅ |
| S0-02 | Como equipo, quiero la API base | FastAPI con config por entorno, logging JSON, errores RFC 9457, Swagger en `/api/v1/docs` | ✅ |
| S0-03 | Como equipo, quiero migraciones de base de datos | Alembic configurado; migración `0001_initial`; prueba upgrade/downgrade | ✅ código · ⏳ prueba contra PostgreSQL real |
| S0-04 | Como operador, quiero endpoints de salud | `/health/live` = 200; `/health/ready` = 200 solo si la BD responde y está en `head`, si no 503 | ✅ |
| S0-05 | Como usuario, quiero una primera pantalla | Layout con sidebar responsive; página "Estado del sistema" consumiendo `/health/ready` | ✅ |
| S0-06 | Como equipo, quiero el entorno en Docker | `docker compose up` levanta db, redis, backend y frontend con healthchecks; `scripts/smoke-test.sh` pasa | ⏳ requiere Docker |
| S0-07 | Como equipo, quiero CI | Lint, tipos, pruebas, contrato OpenAPI, smoke test con Compose y build de imágenes | ✅ definido · ⏳ primer run requiere remoto en GitHub |
| S0-08 | Como equipo, quiero documentación reproducible | README + 8 documentos | ✅ |

## Sprint 1 – Identidad y acceso (P1)

| ID | Historia | Criterios de aceptación |
|---|---|---|
| S1-01 | Como usuario, quiero iniciar sesión con correo y contraseña | Hash Argon2id; access token de 15 min; refresh token en cookie `httpOnly`; bloqueo temporal tras 5 intentos fallidos |
| S1-02 | Como usuario, quiero que mi sesión se renueve y poder cerrarla | Rotación de refresh token; reutilización detectada revoca la familia de tokens; logout revoca |
| S1-03 | Como usuario, quiero recuperar mi contraseña | Token de un solo uso con vigencia de 30 min enviado por correo (Mailpit en desarrollo); respuesta idéntica exista o no el correo |
| S1-04 | Como administrador, quiero gestionar usuarios | CRUD, activar/desactivar; un usuario no puede desactivarse a sí mismo |
| S1-05 | Como administrador, quiero gestionar roles y permisos | 4 roles semilla (Administrador, Supervisor, Técnico, Recepcionista); permisos granulares; endpoints protegidos con 403 |
| S1-06 | Como supervisor, quiero auditoría de acciones | Login, logout y cambios de usuarios y roles quedan en `audit_logs` con actor, IP y diff |
| S1-07 | Como administrador, quiero registrar la organización y su sede | Comando de arranque crea la organización y la sede Bogotá y el primer administrador (sin contraseñas en el repositorio) |
| S1-08 | Como usuario, quiero pantallas de login y gestión de usuarios | React Hook Form + Zod; rutas protegidas; menú según permisos |

## Sprints 2 – 6

Las historias se detallan en la planificación de cada sprint, a partir de los módulos 2 – 11
del documento de requerimientos y del modelo de [ERMS-ERD.md](ERMS-ERD.md). Se agregan
estos requerimientos detectados en el análisis:

| ID | Requerimiento | Sprint |
|---|---|---|
| R-01 | Consentimiento de tratamiento de datos (Ley 1581 de 2012) | 2 |
| R-02 | Estado `COTIZACION_RECHAZADA` y devolución sin reparar | 3 |
| R-03 | Numeración de documentos sin colisiones (`document_sequences`) | 3 |
| R-04 | Consentimiento antes de ejecutar el agente en el equipo del cliente | 4 |
| R-05 | Token de agente de un solo uso, limitado a una sesión | 4 |
| R-06 | IVA por ítem de cotización (19 % o 0 %) | 5 |
| R-07 | Existencias por sede (`stock_levels`) | 5 |
| R-08 | Compras a proveedores (`purchase_orders`) | 5 |
| R-09 | Backups programados de PostgreSQL | 6 |
