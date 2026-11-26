# ERMS – Roadmap (90 días)

Scrum con un Sprint 0 de 1 semana y 6 sprints de 2 semanas, unos 91 días.

| Sprint | Fechas | Objetivo | Entregables principales |
|---|---|---|---|
| **0** | 19 – 25 nov 2026 | Fundaciones | Arquitectura, repositorio, Docker, FastAPI, React, Alembic, CI, salud, documentación |
| **1** | 26 nov – 9 dic | Identidad y acceso | Login, logout, refresh, recuperación de contraseña, usuarios, roles, permisos, auditoría, sedes |
| **2** | 10 – 23 dic | Clientes y equipos | Clientes, consentimientos (Habeas Data), fabricantes, categorías, modelos, dispositivos |
| **3** | 24 dic – 6 ene 2027 | Recepción | ✅ Órdenes de servicio, máquina de estados, acta de recepción en PDF, fotografías en modo demostración. Celery y el almacenamiento definitivo quedan para cuando se necesiten. |
| **4** | 7 – 20 ene | Diagnóstico | ✅ Diagnóstico manual y visual con listas por categoría, agente portable de Windows (solo lectura), informe PDF. La IA por fotos queda para después del MVP. |
| **5** | 21 ene – 3 feb | Taller | ✅ Inventario con entradas simples, cotizaciones versionadas con IVA opcional por ítem, reparación con consumo de repuestos, control de calidad, pagos y comprobantes |
| **6** | 4 – 17 feb | Cierre del MVP | ✅ Garantías y reclamos, dashboard por rol, reportes en pantalla, CSV y PDF, prueba de punta a punta con Playwright, carga bajo demanda, límite de intentos por IP, backups de Railway |

**Riesgo de calendario:** los Sprints 2 y 3 coinciden con las festividades de diciembre y
enero. El Sprint 3 tiene alcance mínimo comprometido (órdenes y acta PDF); fotografías y
Celery pueden pasar al Sprint 4 si la capacidad es baja.

## Después del MVP

- ✅ Almacenamiento definitivo de fotos: bucket privado de Railway (ADR-053).
- Proveedor de correo por API HTTPS (último puesto del backlog).
- Celery y Redis cuando haya trabajo largo (correos masivos, reportes pesados).
- Agente v2 – mantenimiento: antivirus (Microsoft Defender) y limpieza del sistema con
  autorización y confirmación explícitas (PM-01 en el backlog).
- Atención remota (Quick Assist), en sitio y recogida/envío, con agenda y cobro por etapas
  (PM-04), después de los avisos por WhatsApp.
- Ensamble de equipos de escritorio (PM-03): ✅ E1 configurador, compatibilidad, cuellos de
  botella, orden de ensamble y lista de chequeo (2026-11-23). ✅ E2 visor 3D, iluminación RGB, modo Setup y 3D en la lista de chequeo (2026-11-23).
- Asistente virtual de IA en el chat de la landing (PM-05): orienta al cliente, da rangos de
  costo del catálogo y crea la solicitud para el técnico.
- Campañas publicitarias con registro de gastos, atribución de clientes y sugerencias de IA
  (PM-06).
- Adaptador Android (ADB) y adaptador Linux.
- Capa de IA con proveedor real, base de conocimiento y patrones de fallas.
- Facturación electrónica DIAN mediante proveedor autorizado.
- ✅ Avisos al cliente por WhatsApp, fase A (enlace y QR, ADR-054). Pendiente: fase B con la API
  oficial (envío automático) y avisos por correo.
- Múltiples sedes en operación y RLS de PostgreSQL.
