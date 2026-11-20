# ERMS – Product Backlog

Prioridad: **P1** imprescindible para el MVP · **P2** importante · **P3** deseable.

## Sprint 0 – Fundaciones

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S0-01 | Como equipo, quiero un repositorio con estructura y convenciones definidas | Estructura según LLD; `.gitignore`, `.editorconfig`, pre-commit | ✅ |
| S0-02 | Como equipo, quiero la API base | FastAPI con config por entorno, logging JSON, errores RFC 9457, Swagger en `/api/v1/docs` | ✅ |
| S0-03 | Como equipo, quiero migraciones de base de datos | Alembic configurado; migración `0001_initial`; prueba upgrade/downgrade | ✅ probado en CI contra PostgreSQL 17 |
| S0-04 | Como operador, quiero endpoints de salud | `/health/live` = 200; `/health/ready` = 200 solo si la BD responde y está en `head`, si no 503 | ✅ |
| S0-05 | Como usuario, quiero una primera pantalla | Layout con sidebar responsive; página "Estado del sistema" consumiendo `/health/ready` | ✅ |
| S0-06 | Como equipo, quiero el entorno en Docker | `docker compose up` levanta db, redis, backend y frontend con healthchecks; `scripts/smoke-test.sh` pasa | ✅ verificado en CI (GitHub Actions) |
| S0-07 | Como equipo, quiero CI | Lint, tipos, pruebas, contrato OpenAPI, smoke test con Compose y build de imágenes | ✅ en verde (run 44569035697) |
| S0-08 | Como equipo, quiero documentación reproducible | README + 8 documentos | ✅ |

## Sprint 1 – Identidad y acceso (P1)

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S1-01 | Como usuario, quiero iniciar sesión con correo y contraseña | Hash Argon2id; access token de 15 min; refresh token en cookie `httpOnly`; bloqueo de 15 min tras 5 intentos fallidos; mismo mensaje para correo inexistente o clave errada | ✅ |
| S1-02 | Como usuario, quiero que mi sesión se renueve y poder cerrarla | Sesión máx. 12 h y 2 h de inactividad; rotación de refresh token; reutilización revoca la sesión (gracia de 30 s para pestañas simultáneas); logout invalida también el access token | ✅ |
| S1-03 | Como usuario, quiero recuperar mi contraseña | Token de un solo uso, 30 min, por correo (Mailpit en desarrollo); respuesta idéntica exista o no el correo; cierra todas las sesiones | ✅ |
| S1-04 | Como administrador o supervisor, quiero gestionar usuarios | Crear con contraseña temporal (cambio obligatorio), editar, activar/desactivar, asignar roles; nadie se desactiva a sí mismo; siempre queda un administrador activo; el supervisor no puede asignar ni gestionar el rol Administrador | ✅ |
| S1-05 | Como administrador, quiero gestionar roles y permisos | 4 roles de sistema; matriz de permisos editable salvo el rol Administrador; cambios efectivos de inmediato; 403 sin permiso | ✅ |
| S1-06 | Como supervisor, quiero auditoría de acciones | Login (exitoso y fallido), logout, cambios de usuarios, roles y contraseñas en `audit_logs` con actor, IP y diff; consulta con filtros | ✅ |
| S1-07 | Como administrador, quiero registrar la organización y su sede | `python -m app.cli bootstrap` crea organización, sede Bogotá, roles y primer administrador; la contraseña se lee de variable o consola, nunca de argumentos | ✅ |
| S1-08 | Como usuario, quiero pantallas de login y gestión de usuarios | Login, recuperación, restablecimiento y cambio de contraseña; usuarios, roles y auditoría; React Hook Form + Zod; rutas protegidas; menú según permisos | ✅ |

## Sprint 2 – Clientes y equipos (P1)

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S2-01 | Como administrador, quiero registrar los datos del taller y publicar la política de datos | Razón social, NIT (con dígito de verificación), dirección, ciudad, teléfono y correo; plantilla con los mínimos de la Ley 1581 y el Decreto 1377; versiones inmutables; sin política no se registran clientes | ✅ |
| S2-02 | Como recepcionista, quiero registrar clientes con su autorización | Persona o empresa; documento opcional y único; al menos teléfono o correo; autorización de tratamiento obligatoria y opcionales para fotos y agente; medio (pantalla, papel, verbal) y versión de la política | ✅ |
| S2-03 | Como recepcionista, quiero buscar clientes | Por nombre sin tildes, documento o teléfono; filtros y paginación | ✅ |
| S2-04 | Como recepcionista, quiero gestionar las autorizaciones | Otorgar y revocar con historial de solo inserción; sin autorización vigente no se registran equipos | ✅ |
| S2-05 | Como administrador, quiero atender el derecho de supresión | Anonimizar (irreversible) borra los datos personales y conserva el historial técnico; la auditoría no guarda datos personales | ✅ |
| S2-06 | Como recepcionista o técnico, quiero registrar los equipos del cliente | Categoría → fabricante → modelo (creable en el formulario); IMEI con Luhn y único; serial único por modelo; búsqueda por IMEI, serial o modelo | ✅ |
| S2-07 | Como supervisor, quiero administrar el catálogo | Fabricantes precargados, renombrar y desactivar; corregir y desactivar modelos | ✅ |
| S2-08 | Pendientes del Sprint 1 | Nombre del taller en el encabezado; Swagger y OpenAPI ocultos en producción | ✅ |

## Sprint 3 – Recepción (P1)

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S3-01 | Como administrador, quiero publicar las condiciones del acta | Plantilla editable (no es asesoría legal); versiones inmutables; sin condiciones no se reciben equipos | ✅ |
| S3-02 | Como recepcionista, quiero recibir un equipo | Buscar o crear cliente y equipo en el mismo flujo; falla, estado físico, accesorios (lista + Otro), desbloqueo sin contraseñas, prioridad, fecha estimada, valor del diagnóstico y anticipo con medio de pago; número consecutivo sin colisiones | ✅ |
| S3-03 | Como recepcionista, quiero imprimir el acta de recepción | PDF con datos del taller, cliente, equipo, recepción, valores, condiciones y firmas; se descarga al crear la orden | ✅ |
| S3-04 | Como técnico o recepcionista, quiero mover la orden por sus estados | Máquina de estados con permisos por estado, motivos obligatorios, propiedad del técnico, historial de solo inserción | ✅ |
| S3-05 | Como supervisor o recepcionista, quiero asignar técnicos | Solo usuarios activos con permiso técnico | ✅ |
| S3-06 | Como recepcionista, quiero registrar la entrega | Quién retira (titular o tercero con documento); la orden queda cerrada | ✅ |
| S3-07 | Como técnico, quiero fotografiar el equipo | Solo con autorización de fotos; sin metadatos GPS; **modo demostración** hasta elegir proveedor | ✅ (demo) |
| S3-08 | Como usuario, quiero ver y buscar las órdenes | Vistas: abiertas, mías, sin asignar, esperando al cliente, listas, todas; búsqueda por número, cliente, IMEI, serial o modelo | ✅ |

**Aplazado:** Celery + Redis (sin trabajo en segundo plano que lo justifique todavía; ADR-022) y
el proveedor de almacenamiento definitivo para las fotos (ADR-023).

## Sprint 4 – Diagnóstico (P1)

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S4-01 | Como técnico, quiero registrar un diagnóstico manual o visual | Lista de chequeo por categoría; resultado y observación por prueba; "No probado" explícito; conclusión y recomendación; reabrir mientras la orden esté en diagnóstico | ✅ |
| S4-02 | Como recepcionista, quiero que no se cotice sin diagnóstico | La orden no pasa a COTIZACIÓN sin diagnóstico cerrado | ✅ |
| S4-03 | Como técnico, quiero diagnosticar un computador con el agente | Código de un solo uso; autorización del cliente; agente portable para Windows, solo lectura; SMART con permisos de administrador; resultados automáticos evaluados por el servidor | ✅ |
| S4-04 | Como cliente, quiero un informe del diagnóstico | PDF con resultados (automáticos marcados), conclusión y recomendación | ✅ |
| S4-05 | Como equipo, quiero distribuir el agente | Construcción en GitHub Actions (Windows) y publicación en GitHub Releases con SHA256 | ✅ |

**Fuera de este sprint:** revisión del equipo con IA a partir de fotos (requiere un servicio
de pago y almacenamiento definitivo; sus resultados serán `AI_SUGGESTION`, nunca comprobados).

## Sprints 5 – 6

Las historias se detallan en la planificación de cada sprint, a partir de los módulos 2 – 11
del documento de requerimientos y del modelo de [ERMS-ERD.md](ERMS-ERD.md). Se agregan
estos requerimientos detectados en el análisis:

| ID | Requerimiento | Sprint |
|---|---|---|
| R-01 | Consentimiento de tratamiento de datos (Ley 1581 de 2012) | 2 ✅ |
| R-02 | Estado `COTIZACION_RECHAZADA` y devolución sin reparar | 3 |
| R-03 | Numeración de documentos sin colisiones (`document_sequences`) | 3 ✅ |
| R-04 | Consentimiento antes de ejecutar el agente en el equipo del cliente | 4 ✅ |
| R-05 | Token de agente de un solo uso, limitado a una sesión | 4 ✅ |
| R-06 | IVA por ítem de cotización (19 % o 0 %) | 5 |
| R-07 | Existencias por sede (`stock_levels`) | 5 |
| R-08 | Compras a proveedores (`purchase_orders`) | 5 |
| R-09 | Backups programados de PostgreSQL | 6 |
