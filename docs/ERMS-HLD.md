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
  puede contener el usuario del correo. Bloqueo de 15 min tras 5 intentos fallidos.
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
  existen en su interfaz.

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

## 6. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Docker no instalado en el equipo de desarrollo | Bloquea el cierre del Sprint 0 | Instalar Docker Desktop + WSL2. CI ejecuta el smoke test con Compose. |
| Festividades de diciembre (Sprints 2 y 3) | Menor capacidad | Priorizar el backlog y aceptar alcance reducido del Sprint 3. |
| Restricciones de Apple y consolas | Diagnóstico automatizado limitado | Checklists manuales marcados como tales; nunca simular pruebas. |
| Plan gratuito de Railway con límites de recursos | Rendimiento | Medir en el Sprint 6; el diseño no depende de Railway. |
| Datos personales de clientes | Legal (Habeas Data) | Consentimiento registrado, cifrado en tránsito, mínimos privilegios. |
