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

## Sprint 5 – Taller y comercial (P1)

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S5-01 | Como supervisor, quiero administrar el inventario | Repuestos con costo, precio, IVA y stock mínimo; proveedores; entradas simples con factura; ajustes por conteo con motivo; libro de movimientos; alerta de stock bajo | ✅ |
| S5-02 | Como técnico o recepcionista, quiero cotizar | Versiones; mano de obra y repuestos (del inventario o por pedir); IVA 19 % opcional por ítem con precio con o sin IVA; descuentos > 10 % solo con autorización; PDF; vigencia 15 días | ✅ |
| S5-03 | Como recepcionista, quiero registrar la respuesta del cliente | Enviar, aprobar o rechazar (con motivo) desde la cotización, que mueve la orden; vencida no se aprueba | ✅ |
| S5-04 | Como técnico, quiero registrar la reparación | Trabajos con tiempo; repuestos descontados del inventario sin existencias negativas; devolución | ✅ |
| S5-05 | Como técnico, quiero hacer el control de calidad | Lista de la categoría; sin control aprobado no se marca listo para entrega | ✅ |
| S5-06 | Como recepcionista, quiero cobrar | Saldo según cotización aprobada (incluye diagnóstico) o diagnóstico; pagos con comprobante RC; el anticipo es el primer pago | ✅ |
| S5-07 | Como supervisor, quiero autorizar entregas con saldo | Solo con permiso y motivo registrado en el historial | ✅ |

## Sprint 6 – Cierre del MVP

| ID | Historia | Criterios de aceptación | Estado |
|---|---|---|---|
| S6-01 | Como recepcionista, quiero que cada reparación entregada tenga garantía | Días por defecto del taller (90), ajustables en la entrega; solo si se reparó; vigencia visible en la orden | ✅ |
| S6-02 | Como recepcionista, quiero atender reclamos de garantía | Orden nueva enlazada a la original, sin cobro de diagnóstico, cotización en $0 permitida; el supervisor acepta o rechaza con resolución | ✅ |
| S6-03 | Como dueño, quiero ver el estado del taller al entrar | Órdenes abiertas por estado, recibidas hoy y en la semana, vencidas, esperando al cliente, listas para entrega con saldo, ingresos del mes por medio, tiempo promedio, carga por técnico, stock bajo, garantías por vencer y reclamos abiertos. El técnico solo ve sus órdenes y sin dinero | ✅ |
| S6-04 | Como dueño, quiero reportes por fechas | Ingresos, órdenes, inventario y técnicos; en pantalla, Excel (CSV) y PDF | ✅ |
| S6-05 | Como equipo, quiero una prueba de punta a punta en el navegador | Playwright recorre recepción → diagnóstico → cotización → reparación → calidad → pago → entrega → reclamo de garantía, en CI | ✅ |
| S6-06 | Como usuario, quiero que la aplicación cargue rápido | Pantallas cargadas bajo demanda y librerías en archivos separados que el navegador conserva entre despliegues | ✅ |
| S6-07 | Como dueño, quiero proteger el inicio de sesión | Límite de 20 intentos fallidos por IP cada 15 min (429), además del bloqueo por cuenta | ✅ |
| S6-08 | Como dueño, quiero respaldos de la base de datos | Backups nativos de Railway (plan Pro) programados y simulacro de restauración documentado | ✅ (configuración manual) |

## Requerimientos detectados

Las historias se detallan en la planificación de cada sprint, a partir de los módulos 2 – 11
del documento de requerimientos y del modelo de [ERMS-ERD.md](ERMS-ERD.md). Se agregan
estos requerimientos detectados en el análisis:

| ID | Requerimiento | Sprint |
|---|---|---|
| R-01 | Consentimiento de tratamiento de datos (Ley 1581 de 2012) | 2 ✅ |
| R-02 | Estado `COTIZACION_RECHAZADA` y devolución sin reparar | 3 ✅ |
| R-03 | Numeración de documentos sin colisiones (`document_sequences`) | 3 ✅ |
| R-04 | Consentimiento antes de ejecutar el agente en el equipo del cliente | 4 ✅ |
| R-05 | Token de agente de un solo uso, limitado a una sesión | 4 ✅ |
| R-06 | IVA por ítem de cotización (19 % o 0 %) | 5 ✅ |
| R-07 | Existencias por sede (`stock_levels`) | 5 ✅ |
| R-08 | Compras a proveedores: entrada simple en el Sprint 5; órdenes de compra después del MVP | 5 ✅ (simple) |
| R-09 | Backups programados de PostgreSQL | 6 ✅ (Railway) |

## Después del MVP

Prioridad acordada (2026-11-20). Antes de planear la facturación DIAN, confirmar en el RUT si el
taller está obligado (responsabilidades 52, 48 o 47; ver la investigación del 2026-11-20).

| Puesto | Sprint | Contenido |
|---|---|---|
| 1 | Bases operativas | Almacenamiento definitivo de fotos y proveedor de correo (hoy las fotos están en modo demostración y la recuperación de contraseña no envía correos en producción) |
| 2 | Avisos al cliente por WhatsApp | Fase A sin costo: botón que abre WhatsApp con el mensaje listo (enlace `wa.me`), enviado por el asesor. Fase B: envío automático con la API oficial de WhatsApp Cloud (plantillas de utilidad, cerca de USD 0,0008 por mensaje en Colombia; requiere número dedicado y verificación del negocio en Meta) |
| 3 | Atención remota, en sitio y recogida | PM-04 |
| 4 | Agente v2 – mantenimiento | PM-01 |
| 5 | Ensamble de equipos | PM-03 |
| 6 | Facturación electrónica DIAN | Mediante proveedor autorizado (costo mensual o por factura) |
| 7 | IA por fotos | PM-02 (requiere el puesto 1) |
| 8 | Android | Diagnóstico por ADB |
| 9 | Crecimiento | Órdenes de compra (R-08), varias sedes con RLS, Celery y Redis |

| ID | Historia | Criterios de aceptación propuestos |
|---|---|---|
| PM-01 | **Agente v2 – mantenimiento.** Como técnico, quiero analizar virus y limpiar el sistema desde el agente | Modo separado del diagnóstico (que sigue siendo solo lectura). Autorización nueva y separada del cliente ("Mantenimiento del equipo"). Cada acción la ordena el técnico desde ERMS **y** se confirma en el equipo mostrando exactamente qué se hará. Antivirus: estado, firmas, amenazas y análisis rápido con Microsoft Defender; eliminar o poner en cuarentena solo con confirmación. Limpieza: vista previa con tamaño (temporales de Windows, papelera, caché de Windows Update, miniaturas); **nunca** documentos, fotos, descargas ni datos de navegación. Todo queda registrado en la orden. |
| PM-02 | Revisión del equipo con IA a partir de fotos | Proveedor de IA y almacenamiento definitivos; resultados `AI_SUGGESTION`, nunca comprobados |
| PM-03 | **Ensamble de equipos (PC de escritorio).** Como asesor del taller, quiero armar un PC a la medida con validación de compatibilidad | Solo lo usa el asesor (sin página pública). Componentes: procesador, board, RAM, almacenamiento, tarjeta gráfica, fuente, chasis y refrigeración, con especificaciones técnicas en el inventario. **Reglas de compatibilidad:** socket procesador–board, tipo y velocidad de RAM soportados por la board y el procesador, ranuras de RAM y M.2, potencia de la fuente con margen frente al consumo, tamaño de la tarjeta gráfica y de la board frente al chasis. **Cuellos de botella:** aviso cuando el procesador y la tarjeta gráfica están muy desbalanceados para el uso (oficina, diseño, gaming) o la RAM es insuficiente. Precios registrados a mano (cambian); se permiten componentes por pedir al proveedor. Cotización con IVA opcional; si el cliente compra, se registra como orden de ensamble que descuenta inventario, registra el trabajo, las pruebas finales (agente de diagnóstico) y crea la garantía. Especificaciones: evaluar cargarlas desde una base abierta (BuildCores OpenDB o pc-builder-parts, CC BY 4.0) revisando su licencia; precios en línea quedan fuera hasta encontrar una fuente oficial. |
| PM-04 | **Atención remota, en sitio y recogida.** Como taller, quiero atender sin que el cliente venga al local, con un cobro que proteja a ambas partes | **Modalidades de la orden:** en taller (actual), remota, en sitio y recogida/envío. Remota y en sitio siguen *Agendada → En curso → Finalizada* (con cotización, pago y garantía) y se pueden convertir en una orden de taller enlazada. **Remota:** Asistencia rápida de Windows (Quick Assist); autorización de acceso remoto del cliente; registro de técnico, inicio, fin y trabajo; el código de la sesión no se guarda; se puede usar el agente de diagnóstico. **En sitio:** dirección y localidad del servicio, recargo de desplazamiento por zona, llegada y salida marcadas por el técnico (sin rastreo de ubicación), repuestos descontados del inventario, cierre con nombre y documento de quien recibe, acta PDF, aviso "técnico en camino". **Recogida o envío:** (a) el taller recoge y devuelve con cargo por zona (misma tabla de recargos); (b) el cliente envía por transportadora a su cargo: transportadora y número de guía, estado del empaque y fotos al abrirlo como evidencia, acta de recepción al llegar; la devolución la paga el cliente (o contra entrega). **Cobro inteligente:** catálogo de servicios con precio fijo; revisión corta de 20 min con valor fijo (valor configurable) en la que se da el precio cerrado; anticipo del 50 % para clientes nuevos y saldo al confirmar que funciona; si no se soluciona, solo se cobra la revisión y se devuelve el resto del anticipo; contador de tiempo y aprobación del cliente por WhatsApp antes de exceder el estimado; con 3 servicios pagados a tiempo, el cliente puede pagar al final; resumen por WhatsApp al terminar; garantía de servicio de 15 días; pagos por Nequi, Daviplata, transferencia o Bre-B confirmados por el asesor (pasarela con comisión, opcional después). **Agenda:** lunes a viernes 8:00–18:00 y sábado 8:00–12:00 (configurable), festivos de Colombia calculados (Ley Emiliani), aviso de cruce de citas por técnico. |
