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

- Argon2id (`pwdlib`) para contraseñas; JWT con PyJWT.
- Access token de 15 minutos en memoria del cliente; refresh token en cookie `httpOnly`,
  `Secure`, `SameSite=Strict`, con rotación y revocación en base de datos.
- RBAC con permisos granulares (`work_orders:create`, …) asignados a roles.
- Aislamiento por organización en la capa de repositorio; RLS de PostgreSQL como refuerzo
  en una fase posterior.
- Auditoría de solo inserción (`audit_logs`) con actor, acción, entidad, diff e IP.
- **Habeas Data (Ley 1581 de 2012):** el consentimiento del cliente queda registrado
  (`customer_consents`) antes de tratar datos personales o ejecutar el agente en su equipo.
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

## 6. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Docker no instalado en el equipo de desarrollo | Bloquea el cierre del Sprint 0 | Instalar Docker Desktop + WSL2. CI ejecuta el smoke test con Compose. |
| Festividades de diciembre (Sprints 2 y 3) | Menor capacidad | Priorizar el backlog y aceptar alcance reducido del Sprint 3. |
| Restricciones de Apple y consolas | Diagnóstico automatizado limitado | Checklists manuales marcados como tales; nunca simular pruebas. |
| Plan gratuito de Railway con límites de recursos | Rendimiento | Medir en el Sprint 6; el diseño no depende de Railway. |
| Datos personales de clientes | Legal (Habeas Data) | Consentimiento registrado, cifrado en tránsito, mínimos privilegios. |
