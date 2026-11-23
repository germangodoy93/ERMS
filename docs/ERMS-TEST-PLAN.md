# ERMS – Plan de pruebas

## 1. Niveles

| Nivel | Herramienta | Alcance | Dónde se ejecuta |
|---|---|---|---|
| Unitarias backend | pytest | Servicios, validaciones, manejadores de error, checks con dobles de prueba | Local y CI |
| Integración backend | pytest + PostgreSQL real | Migraciones (upgrade/downgrade), repositorios, transacciones | Local (con `ERMS_TEST_DATABASE_URL`) y CI |
| Unitarias frontend | Vitest + Testing Library | Presentación, páginas con API simulada | Local y CI |
| Contrato | Vitest + `docs/api/openapi.json`; CI verifica que el JSON coincide con el código | Tipos del frontend frente a esquemas del backend | Local y CI |
| Humo E2E | `scripts/smoke-test.sh` | Web → proxy → API → PostgreSQL | CI con Docker Compose y local |
| E2E de UI | Playwright 1.65.0 (`e2e/`) | Recepción → diagnóstico → cotización → reparación → calidad → pago → entrega → reclamo de garantía | CI (job `docker`) |

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

## 7. Pruebas del Sprint 4

Resultado local del 2026-11-20: **155 pruebas de backend**, **10 del agente** y **109 de
frontend**, todas en verde; módulo de diagnóstico entre 93 % y 100 % de cobertura. Además se
ejecutó el **agente real en Windows 11** (código fuente y `.exe` empaquetado) contra el entorno
local: se vinculó con el código, leyó las 8 secciones sin permisos de administrador y registró 9
resultados (por ejemplo, desgaste de batería 33,6 % → ADVERTENCIA; SMART → NO SOPORTADO sin
administrador).

| Prueba | Archivo | Verifica |
|---|---|---|
| Evaluación | `backend/tests/unit/test_diagnostic_evaluation.py` | Umbrales de batería, discos, espacio, SMART y estabilidad; secciones faltantes nunca quedan OK; catálogo por categoría |
| Diagnóstico manual | `backend/tests/integration/test_diagnostics_api.py` | Solo en DIAGNÓSTICO; cotización bloqueada sin diagnóstico; cierre exige todas las pruebas y conclusión; pruebas ajenas o del agente rechazadas; reabrir; PDF |
| Permisos | `test_diagnostics_api.py` | Recepción no registra; otro técnico no modifica |
| Agente | `test_diagnostics_api.py` | Código de un solo uso, sin guion y en minúsculas; token de un solo reporte; código anterior invalidado; vencimiento; autorización del cliente; el cierre invalida el token; aislamiento entre talleres |
| Recolección | `diagnostic-agent/tests/test_collect.py` | Respuestas de un objeto o de una lista; enums de disco como texto o número; truncado; SMART vacío; informe de batería; fallas aisladas por sección; **consultas sin comandos de escritura**; HTTPS obligatorio |
| Contrato | `frontend/src/types/api.contract.test.ts` | Esquemas y enums de diagnóstico |
| Panel (UI) | `frontend/src/modules/diagnostics/components/DiagnosticPanel.test.tsx` | Resultados del agente solo lectura; cierre bloqueado con pendientes; "No probado" masivo; guardar y cerrar; código del agente |

## 8. Pruebas del Sprint 5

Resultado local del 2026-11-20: **172 pruebas de backend** (módulos nuevos entre 85 % y 100 %)
y **131 de frontend**, todas en verde. Recorrido completo por el proxy web: repuesto y entrada →
orden con anticipo → diagnóstico → cotización (pantalla $238.000 IVA incluido + mano de obra
$60.000 con 15 %: total $289.000) → aprobación → consumo de repuesto → control de calidad →
pago con comprobante → entrega. La migración 0006 convirtió en pago el anticipo de una orden
existente.

| Prueba | Archivo | Verifica |
|---|---|---|
| Dinero e IVA | `backend/tests/unit/test_money.py` | Precio sin IVA, con IVA incluido, sin IVA, descuento y redondeo; base + IVA = total |
| Inventario | `backend/tests/integration/test_commerce_api.py` | SKU normalizado y único; permisos; entradas con costo; ajuste con motivo; libro de movimientos; stock bajo; proveedores |
| Cotizaciones | `test_commerce_api.py` | Totales con IVA opcional; límite de descuento y autorización; un borrador a la vez; técnico no envía; estados solo por cotización; versiones y reemplazo; rechazo con motivo; vencida no se aprueba; PDF |
| Reparación y calidad | `test_commerce_api.py` | Solo en reparación; consumo y existencia insuficiente; devolución; control incompleto, fallido y aprobado; LISTO_ENTREGA exige control aprobado |
| Pagos y entrega | `test_commerce_api.py` | Anticipo como primer pago con RC; saldo con cotización aprobada; pago mayor al saldo; entrega bloqueada con saldo; supervisor con motivo; comprobante PDF; aislamiento entre talleres |
| Contrato | `frontend/src/types/api.contract.test.ts` | 16 esquemas y 20 rutas nuevas |
| Cotización (UI) | `frontend/src/modules/workshop/quotePayload.test.ts` | Conversión de valores escritos ("50.000", "1,5"), validaciones, saldo |
| Entrega (UI) | `frontend/src/modules/workorders/components/DeliveryDialog.test.tsx` | Recepción bloqueada con saldo; supervisor con motivo; sin saldo sin preguntas |

## 9. Pruebas del Sprint 6

Resultado local del 2026-11-20: **179 pruebas de backend** (95 % de cobertura), **145 de
frontend** y **1 E2E en navegador** (unos 20 s), todas en verde. El E2E se ejecutó contra una
organización nueva con contraseña temporal, igual que en CI. Recorrido por el proxy web:
entrega con garantía de 60 días → reclamo (orden nueva, diagnóstico $0) → cotización en $0 →
reclamo aceptado → dashboard → cuatro reportes en JSON, CSV (con BOM) y PDF → rango invertido
422 → 21 intentos fallidos de inicio de sesión: 429 con `Retry-After`.

La prueba E2E encontró tres errores de interfaz que las pruebas unitarias no veían, ya
corregidos y cubiertos por pruebas nuevas:

1. Al cambiar el estado de la orden, los paneles (diagnóstico, cotización, reparación, pagos,
   garantía) no se actualizaban hasta recargar la página.
2. Al guardar resultados del diagnóstico se borraba la conclusión ya escrita.
3. El valor sugerido del pago seguía siendo el saldo de cuando se abrió la página (solo el
   diagnóstico) aunque luego se aprobara la cotización.

| Prueba | Archivo | Verifica |
|---|---|---|
| Garantías | `backend/tests/integration/test_warranties_reports_api.py` | Garantía al entregar con días del taller o de la entrega; sin garantía si no se reparó; reclamo vigente; orden nueva sin diagnóstico; cotización $0; decisión; permisos |
| Dashboard | `test_warranties_reports_api.py` | Alcance del taller con dinero; técnico solo sus órdenes y sin dinero |
| Reportes | `test_warranties_reports_api.py` | Cuatro reportes; columnas de dinero; CSV con BOM y `;`; PDF; rango invertido y mayor a un año; permisos |
| CSV seguro | `test_warranties_reports_api.py` | Fórmulas neutralizadas, números intactos |
| Límite por IP | `test_warranties_reports_api.py` | 20 fallos → 429 con `Retry-After` |
| Contrato | `frontend/src/types/api.contract.test.ts` | Esquemas y 5 rutas nuevas |
| Dashboard, reportes y garantía (UI) | `frontend/src/modules/reports/**/*.test.tsx` | Indicadores por alcance; moneda en reportes; abrir reclamo |
| Regresiones (UI) | `workorders/hooks.test.tsx`, `DiagnosticPanel.test.tsx`, `BillingPanel.test.tsx` | Los tres errores anteriores |
| E2E | `e2e/tests/repair-flow.spec.ts` | Flujo completo en Chromium, incluida la descarga del acta y el cambio de contraseña temporal |

## 10. Pruebas del Sprint E1 (ensamble)

Resultado local del 2026-11-23: **195 pruebas de backend** (94 %; módulo de ensamble entre 90 %
y 100 %) y **164 de frontend**, todas en verde. Con el catálogo real del simulador (185 piezas)
importado por el proxy web, los seis presets del simulador dan el mismo resultado que en él: los
cinco válidos quedan listos y "Con errores para practicar" reporta sus seis incompatibilidades.
La orden de ensamble del preset "Gamer 1440p" nace en cotización con 9 ítems y $9.869.000.

| Prueba | Archivo | Verifica |
|---|---|---|
| Reglas | `backend/tests/unit/test_assembly_rules.py` | Preset gamer compatible y su precio; preset con errores; fuente; anclaje del disipador; largo de gráfica; velocidad de RAM; radiador y espacio para ventiladores; Strimer 16 pines; cuellos de botella por uso y umbral; candidatos; orden de pasos; validación de especificaciones |
| API | `backend/tests/integration/test_assembly_api.py` | Importación idempotente y validada; edición del repuesto sin perder especificaciones; evaluación y candidatos; permisos (solo técnico y administrador); orden completa: cotización, aprobación, descuento sin existencias (422) y con existencias, pasos en orden, control de calidad, pago, entrega y garantía |
| Migración | `backend/tests/integration/test_database.py` | 0008 coincide con los modelos y se revierte |
| UI | `frontend/src/modules/assembly/**/*.test.ts(x)` | Selección como el simulador; textos de especificaciones; archivo de catálogo; configurador con motivos, faltantes y guardado; lista de chequeo |
| Contrato | `frontend/src/types/api.contract.test.ts` | 12 esquemas nuevos, 6 actualizados, 9 rutas y los enums de categoría y uso |
| Precios (0009) | `backend/tests/unit/test_assembly_pricing.py`, `test_assembly_api.py`, `test_commerce_api.py` | Costo + margen redondeado hacia arriba; lectura de montos del proveedor; precio fijado a mano que sobrevive a costos y margen nuevos; recálculo por entrada de inventario y por margen; plantilla y actualización desde CSV (Windows-1252, filas inválidas y códigos desconocidos); costo oculto para el técnico. La migración 0009 convirtió en costo las 185 piezas importadas con 0008 (verificado en local) |

**Windows:** si la terminal abre la carpeta como `c:\...` (minúscula), Vitest carga dos copias de
sí mismo y las pruebas de interfaz fallan con `Invalid Chai property: toBeInTheDocument`.
Ejecute las pruebas desde una terminal en `C:\...` (ver ERMS-DEVOPS).
