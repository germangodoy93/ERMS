# ERMS – Roadmap (90 días)

Scrum con un Sprint 0 de 1 semana y 6 sprints de 2 semanas, unos 91 días.

| Sprint | Fechas | Objetivo | Entregables principales |
|---|---|---|---|
| **0** | 19 – 25 nov 2026 | Fundaciones | Arquitectura, repositorio, Docker, FastAPI, React, Alembic, CI, salud, documentación |
| **1** | 26 nov – 9 dic | Identidad y acceso | Login, logout, refresh, recuperación de contraseña, usuarios, roles, permisos, auditoría, sedes |
| **2** | 10 – 23 dic | Clientes y equipos | Clientes, consentimientos (Habeas Data), fabricantes, categorías, modelos, dispositivos |
| **3** | 24 dic – 6 ene 2027 | Recepción | Órdenes de servicio, máquina de estados, fotografías (almacenamiento S3), acta de recepción en PDF, Celery |
| **4** | 7 – 20 ene | Diagnóstico | Diagnóstico manual, checklists, motor de plugins, agente Windows inicial |
| **5** | 21 ene – 3 feb | Taller | Reparaciones, control de calidad, inventario, cotizaciones con IVA por ítem, pagos |
| **6** | 4 – 17 feb | Cierre del MVP | Garantías, reportes PDF, dashboard, pruebas integrales, despliegue en Railway |

**Riesgo de calendario:** los Sprints 2 y 3 coinciden con las festividades de diciembre y
enero. El Sprint 3 tiene alcance mínimo comprometido (órdenes y acta PDF); fotografías y
Celery pueden pasar al Sprint 4 si la capacidad es baja.

## Después del MVP

- Adaptador Android (ADB) y adaptador Linux.
- Capa de IA con proveedor real, base de conocimiento y patrones de fallas.
- Facturación electrónica DIAN mediante proveedor autorizado.
- Notificaciones al cliente (WhatsApp/SMS/correo).
- Múltiples sedes en operación y RLS de PostgreSQL.
