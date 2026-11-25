# ERMS – High Level Design (HLD)

> ERMS – Electronic Repair Management System. Plataforma de gestión para un centro de
> diagnóstico y reparación de computadores, celulares, tablets y consolas en Bogotá, Colombia.

| Campo | Valor |
|---|---|
| Versión | 0.1 (Sprint 0) |
| Estado | Aprobado para el Sprint 0 |
| Fecha | 2026-11-19 |

## 1. Contexto y alcance

- Operación inicial: **un taller en Bogotá**. El modelo de datos soporta varias sedes (`branches`)
  y varias organizaciones (`organizations`) desde el día 1.
- Usuarios: Administrador, Supervisor, Técnico y Recepcionista (RBAC).
- Ciclo completo: recepción → inspección → diagnóstico → cotización → autorización →
  reparación → control de calidad → entrega → garantía.
- Fuera de alcance del MVP: facturación electrónica DIAN (solo se deja el puerto de
  integración), notificaciones por WhatsApp/SMS, app móvil nativa y microservicios.

## 2. Vista de componentes

```
                    ┌────────────── Railway (producción) ──────────────┐
 Navegador ──HTTPS──►  web: Caddy                                      │
                    │   /        → SPA React (estáticos)               │
                    │   /api/*   → backend (red privada)               │
                    └──────────────┬───────────────────────────────────┘
                                   │
       ┌───────────────────────────┼─────────────────────────┬────────────────────┐
       ▼                           ▼                         ▼                    ▼
  PostgreSQL 17             Redis (broker y           Celery worker/beat    Almacenamiento S3
  (datos + auditoría)       resultados)               (PDF, correo,         (fotos, PDFs)
                                                       backups) Sprint 3+   Sprint 3+

  Agente de diagnóstico (ejecutable portable, Sprint 4)
    └─► HTTPS → /api/v1/diagnostics/agent/*  con token de un solo uso
        limitado a UNA sesión de diagnóstico (permisos mínimos)
```

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Web | React 19, Vite 8, TypeScript 6, Tailwind 4, shadcn/ui, TanStack Query, React Router 8 | Interfaz para técnicos y recepción |
| API | Python 3.13, FastAPI, SQLAlchemy 2.1, Pydantic 2, Alembic | Reglas de negocio, seguridad, contratos REST |
| Base de datos | PostgreSQL 17 | Fuente de verdad, integridad referencial |
| Tareas asíncronas | Celery + Redis | Generación de PDF, correos, backups |
| Archivos | S3-compatible (proveedor por definir en el Sprint 3) | Fotografías y documentos |
| Agente | Python, empaquetado como ejecutable | Recolección de datos de hardware con consentimiento |

## 3. Arquitectura del backend: monolito modular

Cada dominio vive en `backend/app/modules/<dominio>/` con capas fijas:

| Archivo | Capa | Regla |
|---|---|---|
| `router.py` | HTTP | Solo traduce HTTP ↔ servicio. Sin lógica de negocio. |
| `schemas.py` | DTO | Modelos Pydantic de entrada y salida. |
| `service.py` | Negocio | Reglas, transacciones y autorización fina. |
| `repository.py` | Datos | Consultas SQLAlchemy, **siempre filtradas por `organization_id`**. |
| `models.py` | ORM | Tablas del módulo. |
| `dependencies.py` | DI | Construcción de servicios para `Depends`. |

Reglas entre módulos:

1. Un módulo consume a otro **solo a través de su `service`**.
2. Nada fuera de `core/` construye respuestas de error HTTP: los módulos lanzan `AppError`.
3. Los modelos se registran en `app/shared/registry.py` para que Alembic los vea.

Transversales en `app/core/`: configuración, logging JSON, base de datos, errores
RFC 9457 y, desde el Sprint 1, seguridad (JWT y RBAC) y auditoría.

## 4. Seguridad (resumen)

- Argon2id (`pwdlib`) para contraseñas; JWT con PyJWT. Política: mínimo 12 caracteres y no
  puede contener el usuario del correo. Bloqueo de 15 min tras 5 intentos fallidos por cuenta y, desde el Sprint 6, máximo 20 intentos
  fallidos por IP cada 15 min (429 con `Retry-After`).
- Access token de 15 minutos guardado solo en memoria del cliente. El refresh token va en
  cookie `httpOnly`, `Secure`, `SameSite=Strict`, limitada a `/api/v1/auth`, con rotación y
  revocación en BD. La sesión dura máx. 12 h y se cierra tras 2 h sin actividad.
- Detección de robo: reutilizar un refresh token ya rotado revoca toda la sesión. Hay una
  gracia de 30 s para que dos pestañas que renuevan a la vez no se cierren mutuamente.
- El access token se invalida al cerrar sesión: cada petición verifica que la sesión siga activa.
- RBAC con permisos granulares (`users:read`, …) asignados a roles. Los permisos se consultan
  en cada petición y **no viajan en el JWT**, así que retirar un permiso aplica de inmediato.
- Protección de privilegios: solo `roles:manage` (Administrador) asigna el rol Administrador o
  gestiona a un administrador. Siempre queda al menos un administrador activo.
- Contraseña temporal al crear usuarios, con cambio obligatorio en el primer ingreso (el
  backend responde 403 `password_change_required` a todo lo demás).
- Aislamiento por organización en la capa de repositorio; RLS de PostgreSQL como refuerzo
  en una fase posterior.
- Auditoría de solo inserción (`audit_logs`) con actor, acción, entidad, diff e IP.
- **Habeas Data (Ley 1581 de 2012):** el cliente solo se registra con su autorización de
  tratamiento, ligada a la versión publicada de la política (`privacy_policies`,
  `customer_consents`). Las autorizaciones de fotos y del agente son separadas. La supresión
  se atiende anonimizando, y la auditoría nunca guarda los valores de los datos personales.
- El agente nunca ejecuta formateos, borrados ni cambios de firmware: esas operaciones no
  existen en su código. Solo lee información técnica del hardware, con código de un solo uso
  y token limitado a un reporte de una orden; no lee archivos, cuentas ni programas.

## 5. Decisiones de arquitectura (ADR)

| ADR | Decisión | Alternativa descartada | Motivo |
|---|---|---|---|
| 001 | SQLAlchemy **síncrono** + psycopg 3 | async + asyncpg | Celery es síncrono, así que API y workers comparten modelos y sesión. El volumen de un taller no justifica la complejidad de async. |
| 002 | PyJWT + pwdlib (Argon2id) | python-jose + passlib | Ambas alternativas están sin mantenimiento; passlib falla con bcrypt ≥ 4.1. |
| 003 | Errores RFC 9457 (`application/problem+json`) | Formato propio | Estándar con un solo contrato de error para el frontend. |
| 004 | Monolito modular | Microservicios | Requisito del MVP; un solo despliegue y transacciones locales. |
| 005 | Railway con un Dockerfile por servicio | Docker Compose en producción | Railway no ejecuta Compose; PostgreSQL y Redis gestionados. Compose se usa solo en local y CI. |
| 006 | Caddy sirve la SPA y hace proxy de `/api` | SPA y API en dominios distintos | Mismo origen: sin CORS en producción y cookies `SameSite=Strict` funcionales. |
| 007 | TanStack Query para estado de servidor; Zustand para estado de UI y sesión | Solo Zustand | Caché, reintentos e invalidación sin reimplementarlos. Gratuito (MIT). |
| 008 | Tipos de API escritos a mano con prueba de contrato | `openapi-typescript` | La herramienta exige TypeScript 5. La prueba `api.contract.test.ts` detecta desviaciones. Se revisará cuando soporte TS 6. |
| 009 | TypeScript 6.0 | TypeScript 7.0 | `typescript-eslint` exige `<6.1`. |
| 010 | IVA por ítem de cotización (19 % o 0 %/exento) | Tarifa global | El negocio cobra IVA en unos casos y en otros no. |
| 011 | Correo: Mailpit en desarrollo; SMTP genérico en producción (plan gratuito) | Proveedor de pago | Restricción de costo cero. |
| 012 | Almacenamiento de objetos: abstracción S3 con proveedor a decidir en el Sprint 3 | MinIO fijo | MinIO cambió su licencia y distribución en 2025; se evaluarán alternativas gratuitas. |
| 013 | Correo de usuario único en todo el sistema | Único por organización | Login sin elegir organización; preparado para multiempresa. |
| 014 | Catálogo de permisos en código e insertado por migraciones | Sincronizar al arrancar la API | Mismo catálogo en todos los entornos, sin escrituras concurrentes al arrancar varias instancias. |
| 015 | Contraseña temporal + cambio obligatorio al crear usuarios | Invitación por correo | Funciona sin SMTP en producción. La invitación por correo puede agregarse cuando haya proveedor. |
| 016 | Período de gracia de 30 s en la rotación del refresh token | Revocación estricta | Evita cerrar la sesión cuando dos pestañas renuevan a la vez, sin perder la detección de robo. |
| 017 | Política de datos versionada en la base, con plantilla; sin política publicada no se registran clientes | Texto fijo en el código | Cada autorización queda ligada al texto exacto que aceptó el cliente. El taller no tenía política: la plantilla cubre los mínimos legales y se advierte que no es asesoría legal. |
| 018 | La auditoría de clientes registra los nombres de los campos, no sus valores | Diff completo como en usuarios | Al anonimizar no queda ningún dato personal en `audit_logs`, que es de solo inserción. |
| 019 | Supresión mediante anonimización | Borrado físico | Se conserva el historial técnico y comercial que exigen las normas contables, sin datos personales. |
| 020 | Categorías de equipo globales y fijas; fabricantes y modelos por taller | Todo por taller | Las categorías anclan checklists y pruebas de diagnóstico (Sprint 4) que deben ser iguales en todos los entornos. |
| 021 | Swagger y OpenAPI deshabilitados en producción | Publicarlos | Reducen la superficie expuesta; el contrato está en `docs/api/openapi.json`. |
| 022 | Acta en PDF generada en la petición con reportlab (BSD); Celery y Redis aplazados | Celery desde el Sprint 3 | Un acta se genera en milisegundos; un Redis más en Railway consume créditos sin necesidad. Se incorporará cuando haya trabajo largo (correos masivos, reportes, respaldos). |
| 023 | Fotos detrás de una interfaz `Storage`; implementación local en **modo demostración** | Elegir proveedor ya | Decisión del negocio: probar el flujo sin costo. En Railway el disco es efímero; la interfaz y la API lo indican (`demo: true`). Cambiar de proveedor solo toca `app/core/storage.py`. |
| 024 | Numeración con `INSERT … ON CONFLICT DO UPDATE … RETURNING` | `SELECT … FOR UPDATE` | Una sola sentencia atómica, también para el primer número del año. |
| 025 | Las órdenes no guardan contraseñas de desbloqueo; se registra el método | Campo cifrado | Regla del proyecto: no recolectar contraseñas. El cliente desbloquea o se la da en persona al técnico. |
| 026 | Las fotos se re-codifican (JPEG, máx. 2048 px, sin EXIF) | Guardar el original | Elimina la ubicación GPS y otros metadatos personales, valida que sea una imagen real y controla el tamaño. |
| 027 | Consulta de IMEI reportados: botón que copia el IMEI y abre la consulta pública oficial (imeicolombia.com.co) | Automatizar el formulario o pagar GSMA Device Check | La consulta oficial no tiene API y exige verificación humana; automatizarla sería no oficial y frágil. GSMA tiene costo. |
| 028 | Agente: Python solo con biblioteca estándar, consultas CIM por PowerShell y `powercfg`, empaquetado con PyInstaller | pywin32/WMI o un agente en .NET | Sin dependencias externas, auditable y probado en Windows real. Las consultas son fijas y de solo lectura; una prueba lo verifica. |
| 029 | Ejecutable sin firma digital, publicado en GitHub Releases con SHA256 | Certificado de firma (~USD 200/año) | Decisión de costo. Windows SmartScreen advierte; la pantalla de ERMS explica cómo continuar. |
| 030 | Catálogo de pruebas en código; umbrales evaluados en el servidor | Tablas editables; evaluar en el agente | Igual en todos los entornos y versionado con el código. Cambiar un umbral no exige publicar un nuevo agente. |
| 031 | Agente sin permisos de administrador por defecto; SMART solo si se ejecuta elevado | Exigir administrador | Mínimo privilegio. Lo no leído queda `NOT_SUPPORTED`. |
| 032 | IVA opcional por ítem; el precio puede incluirlo o no; el servidor calcula y redondea (`ROUND_HALF_UP`) | Precios siempre sin IVA | Decisión del negocio: unos ítems llevan IVA y otros no, y los precios se manejan de ambas formas. |
| 033 | Los estados ligados a la cotización solo cambian desde la cotización | Botones de estado libres | La orden y la cotización no pueden contradecirse. |
| 034 | Entradas de inventario simples (sin órdenes de compra) | Flujo de compras completo | Decisión del negocio para el MVP. |
| 035 | Saldo = cotización aprobada (incluye el diagnóstico) o diagnóstico − pagos; entrega con saldo solo con permiso y motivo | Bloqueo total | Decisión del negocio; queda trazado en el historial y la auditoría. |
| 036 | Comprobante de pago interno con numeración `RC-<año>-<consecutivo>` | Factura electrónica | La facturación DIAN está fuera del MVP; el comprobante lo aclara. |
| 037 | Garantía automática al entregar un equipo reparado; el reclamo abre una orden nueva enlazada (`warranty_of_id`) | Reabrir la orden original | La orden original queda cerrada e intacta; el reclamo tiene su propio diagnóstico, historial y documentos. |
| 038 | Reportes con un solo modelo tabular que alimenta JSON, CSV y PDF; CSV con BOM, `;` y neutralización de fórmulas | Librería de Excel (xlsx) | Sin dependencias nuevas; Excel en español lo abre directamente; evita inyección de fórmulas (CSV injection). |
| 039 | Límite de intentos fallidos por IP en memoria del proceso | Redis | Hay una sola instancia del backend; Redis costaría más sin beneficio. Si se escala a varias instancias, se mueve a Redis. |
| 040 | Pantallas cargadas bajo demanda (`React.lazy`) y librerías en fragmentos separados | Un solo archivo | El código propio inicial pasa de 525 kB a 32 kB; las librerías cambian poco y quedan en la caché del navegador. |
| 041 | Backups con la función nativa de Railway (plan Pro) | `pg_dump` programado propio | Sin código ni almacenamiento adicional; el simulacro de restauración se hace en un entorno duplicado. |
| 042 | E2E con Playwright contra el stack de Docker Compose en CI; los datos maestros se crean por la API y el flujo de la orden por la interfaz | Todo por la interfaz | Prueba lo que el usuario hace sin volver la prueba lenta y frágil. |
| 043 | El catálogo de ensamble es el inventario: `parts.assembly_category` + `specs` JSONB validadas por categoría (Pydantic) | Tablas por categoría; datos dentro del código como el simulador | Un solo lugar para precio y existencia; las reglas leen campos explícitos, no adivinan por el nombre del producto. |
| 044 | Las reglas de compatibilidad corren en el servidor (`assembly/rules.py`, funciones puras) | Solo en el navegador | Una sola fuente de verdad para la pantalla, la orden y las pruebas. |
| 045 | La venta de un PC armado es una orden `kind = ASSEMBLY` que entra directo a cotización | Flujo de venta aparte | Reutiliza cotización, pagos, control de calidad, entrega, garantía y reportes sin duplicarlos. |
| 046 | El catálogo con precios se carga por archivo desde la aplicación y vive en `data/private/` (excluido de Git) | Sembrarlo en una migración | El repositorio es público; los precios son información comercial del taller. |
| 047 | Piezas de ensamble: la lista del proveedor es el **costo** y el precio de venta es costo + margen del taller (15 %), redondeado hacia arriba a $1.000, salvo precio fijado a mano | Guardar el precio del proveedor como venta | El taller compra a esa lista; venderla tal cual sería sin ganancia. |
| 048 | Actualización de costos con CSV desde Excel (plantilla descargable), no con el PDF del proveedor ni con xlsx | Leer el PDF; librería de Excel | El PDF mezcla columnas y tiene errores de digitación; CSV no agrega dependencias y Excel lo abre y guarda. |
| 049 | El costo solo lo ve quien tiene `inventory:manage` | Visible para todos | Decisión del dueño: el técnico ve solo el precio de venta. |
| 050 | Visor 3D con three.js 0.187 (npm, MIT) en un fragmento propio que solo se descarga al abrir el 3D | Copiar el simulador con three r128 desde un CDN | Versión mantenida, sin dependencias externas en tiempo de ejecución y sin costo de carga para el resto de la aplicación. Se adaptaron el manejo de color (`colorSpace`), las intensidades de luz (unidades físicas) y las sombras (`PCFShadowMap`). |
| 051 | El setup se vende en la misma orden que el PC y sus piezas son repuestos del inventario | Pedido aparte | Una sola cotización, un solo pago y una sola garantía. |
| 052 | La revisión del setup se calcula en el navegador (`setup.ts`) | En el servidor | Depende de la distribución 3D y nunca bloquea la venta; las reglas del PC siguen en el servidor. |
| 053 | Fotos en un **bucket privado de Railway** (S3) con `S3Storage` (boto3); cierra ADR-012 y ADR-023 | Volumen de Railway; Cloudflare R2 | Decisión del dueño (2026-11-25): todo en Railway. US$ 0,015/GB-mes, sin costo de operaciones ni de descarga, sobrevive a los despliegues. El bucket no es público: las fotos solo se sirven por la API, que valida permisos. Si falla la subida se deshace la fila (503); si falla el borrado se conserva para reintentar (la foto es del cliente). Sin variables `S3_*` se mantiene el modo demostración. |

## 6. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Docker no instalado en el equipo de desarrollo | Bloquea el cierre del Sprint 0 | Instalar Docker Desktop + WSL2. CI ejecuta el smoke test con Compose. |
| Festividades de diciembre (Sprints 2 y 3) | Menor capacidad | Priorizar el backlog y aceptar alcance reducido del Sprint 3. |
| Restricciones de Apple y consolas | Diagnóstico automatizado limitado | Checklists manuales marcados como tales; nunca simular pruebas. |
| Recursos de Railway | Rendimiento | Plan Pro. Pantallas bajo demanda y librerías en caché; el diseño no depende de Railway. |
| Datos personales de clientes | Legal (Habeas Data) | Consentimiento registrado, cifrado en tránsito, mínimos privilegios. |
