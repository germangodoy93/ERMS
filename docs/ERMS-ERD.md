# ERMS – Modelo entidad-relación

Estado de cada entidad: **✅ migrada** · **📐 diseñada** (se migra en el sprint indicado).

Todas las tablas tienen `id UUID PK`, `created_at timestamptz` y `updated_at timestamptz`. Las
tablas de negocio tienen además `organization_id UUID NOT NULL FK → organizations` con índice.

## 1. Diagrama (núcleo)

```mermaid
erDiagram
    organizations ||--o{ branches : tiene
    organizations ||--o{ users : emplea
    users }o--o{ roles : user_roles
    roles }o--o{ permissions : role_permissions
    organizations ||--o{ customers : atiende
    customers ||--o{ customer_consents : otorga
    customers ||--o{ devices : posee
    manufacturers ||--o{ device_models : fabrica
    device_categories ||--o{ device_models : clasifica
    device_models ||--o{ devices : instancia
    devices ||--o{ work_orders : ingresa
    branches ||--o{ work_orders : recibe
    users ||--o{ work_orders : "técnico asignado"
    work_orders ||--o{ work_order_status_history : registra
    work_orders ||--o{ diagnostic_sessions : diagnostica
    diagnostic_sessions ||--o{ diagnostic_results : produce
    diagnostic_tests ||--o{ diagnostic_results : define
    work_orders ||--o{ quotations : cotiza
    quotations ||--o{ quotation_items : contiene
    work_orders ||--o{ repair_tasks : ejecuta
    repair_tasks ||--o{ repair_task_parts : consume
    parts ||--o{ repair_task_parts : usado
    parts ||--o{ stock_levels : existencia
    branches ||--o{ stock_levels : almacena
    parts ||--o{ inventory_movements : mueve
    work_orders ||--o{ payments : paga
    work_orders ||--o| warranties : garantiza
    warranties ||--o{ warranty_claims : reclama
```

## 2. Entidades

### Identidad y organización

| Tabla | Sprint | Columnas clave | Restricciones |
|---|---|---|---|
| `organizations` | ✅ 0 · 2 | name, slug, tax_id (NIT), timezone, is_active; desde el Sprint 2: legal_name, address, city, phone, email (responsable del tratamiento) | `uq(slug)` |
| `branches` | ✅ 1 | name, city, address, phone, is_active | `uq(organization_id, name)` |
| `users` | ✅ 1 | email, full_name, phone, password_hash, must_change_password, is_active, failed_login_count, locked_until, last_login_at, password_changed_at | `uq(email)` **global**; `ck(email = lower(email))` |
| `roles` | ✅ 1 | code (ADMIN, SUPERVISOR, TECHNICIAN, RECEPTIONIST), name, is_system | `uq(organization_id, code)` |
| `permissions` | ✅ 1 | code (`users:read`…), description | `uq(code)`; catálogo global insertado por migraciones |
| `user_roles`, `role_permissions` | ✅ 1 | tablas puente | PK compuesta; índice por la segunda columna |
| `refresh_tokens` | ✅ 1 | user_id, family_id (sesión), token_hash (SHA-256), expires_at (inactividad), session_expires_at (absoluta), revoked_at, replaced_by_id, ip, user_agent | `uq(token_hash)`; índices por user_id y family_id |
| `password_reset_tokens` | ✅ 1 | user_id, token_hash (SHA-256), expires_at, used_at | `uq(token_hash)` |
| `audit_logs` | ✅ 1 | organization_id, actor_user_id, action, entity_type, entity_id, changes JSONB, ip, user_agent, created_at | solo inserción; índices (entity_type, entity_id), (organization_id, created_at), action, actor |

### Clientes y dispositivos

| Tabla | Sprint | Columnas clave | Restricciones |
|---|---|---|---|
| `privacy_policies` | ✅ 2 | version, content, published_at, published_by_id | `uq(organization_id, version)`; versiones inmutables |
| `customers` | ✅ 2 | kind (PERSON/COMPANY), full_name, search_name (sin tildes), id_type (CC, CE, NIT, PAS, TI, PPT), id_number, phone (E.164), email, address, notes, is_active, anonymized_at, created_by_id | `uq(organization_id, id_type, id_number)` (documento opcional); `ck` tipo y número juntos; índice GIN trigram (`pg_trgm`) por `search_name` |
| `customer_consents` | ✅ 2 | customer_id, purpose (DATA_PROCESSING, PHOTOS, DIAGNOSTIC_AGENT), granted, channel (SCREEN, PAPER, VERBAL), policy_id, recorded_by_id, recorded_at | Ley 1581 de 2012; **solo inserción**: el estado vigente es el último registro por finalidad. La evidencia en archivo podrá adjuntarse con `attachments` cuando se defina el almacenamiento. |
| `device_categories` | ✅ 2 | code (PK), name, sort_order | **Catálogo global** fijo: LAPTOP, DESKTOP, PHONE, TABLET, CONSOLE, OTHER |
| `manufacturers` | ✅ 2 | name, is_active | `uq(organization_id, name)`; 13 precargados por taller |
| `device_models` | ✅ 2 | manufacturer_id, category_code, name, release_year, is_active | `uq(manufacturer_id, name)` |
| `devices` | ✅ 2 | customer_id, model_id, serial_number, imei, operating_system, storage, color, notes, is_active | IMEI validado con Luhn; `uq(organization_id, imei)`; `uq(organization_id, model_id, serial_number)` |

### Órdenes de servicio

| Tabla | Sprint | Columnas clave | Restricciones |
|---|---|---|---|
| `document_sequences` | ✅ 3 | organization_id, doc_type (WORK_ORDER, …), year, last_value | PK (organization_id, doc_type, year); se incrementa con `INSERT … ON CONFLICT DO UPDATE … RETURNING` (atómico) |
| `reception_terms` | ✅ 3 | version, content, published_at, published_by_id | `uq(organization_id, version)`; versiones inmutables |
| `work_orders` | ✅ 3 | number (`ER-2026-000001`), branch_id, customer_id, device_id, assigned_technician_id, status, priority, received_at, received_by_id, reported_issue, physical_condition, accessories JSONB `[{code, detail}]`, unlock_method, estimated_delivery_date, diagnostic_fee, advance_amount, advance_method, notes, terms_id, delivered_at, delivered_to_name, delivered_to_document | `uq(organization_id, number)`; índices (organization_id, status), (organization_id, received_at); dinero `NUMERIC(14,2) ≥ 0`; anticipo > 0 exige medio de pago. **No guarda contraseñas de desbloqueo.** |
| `work_order_status_history` | ✅ 3 | work_order_id, from_status, to_status, changed_by_id, reason, changed_at | solo inserción |
| `attachments` | ✅ 3 | organization_id, entity_type, entity_id, kind (PHOTO), storage_key, file_name, content_type, size_bytes, sha256, uploaded_by_id | índice (entity_type, entity_id); `uq(storage_key)` |

**Estados de la orden:** `RECIBIDO`, `INSPECCION`, `DIAGNOSTICO`, `COTIZACION`,
`PENDIENTE_AUTORIZACION`, `APROBADO`, `COTIZACION_RECHAZADA` *(agregado)*, `EN_REPARACION`,
`CONTROL_CALIDAD`, `LISTO_ENTREGA`, `ENTREGADO`, `CANCELADO`, `NO_REPARABLE`.

Los estados `NO_REPARABLE`, `COTIZACION_RECHAZADA` y `CANCELADO` pasan a `LISTO_ENTREGA` y luego
a `ENTREGADO`, porque el equipo siempre se devuelve.

**Transiciones (Sprint 3)** — definidas en `backend/app/modules/workorders/catalog.py`:

| Desde | Hacia | Permiso |
|---|---|---|
| RECIBIDO | INSPECCION · CANCELADO* | progress · deliver |
| INSPECCION | DIAGNOSTICO · NO_REPARABLE* · CANCELADO* | progress · progress · deliver |
| DIAGNOSTICO | COTIZACION · NO_REPARABLE* · CANCELADO* | progress · progress · deliver |
| COTIZACION | PENDIENTE_AUTORIZACION · CANCELADO* | deliver |
| PENDIENTE_AUTORIZACION | APROBADO · COTIZACION_RECHAZADA* · CANCELADO* | deliver |
| APROBADO | EN_REPARACION · CANCELADO* | progress · deliver |
| EN_REPARACION | CONTROL_CALIDAD · NO_REPARABLE* | progress |
| CONTROL_CALIDAD | LISTO_ENTREGA · EN_REPARACION* | progress (o deliver para LISTO_ENTREGA) |
| COTIZACION_RECHAZADA, NO_REPARABLE, CANCELADO | LISTO_ENTREGA | progress o deliver |
| LISTO_ENTREGA | ENTREGADO (por `/delivery`) | deliver |

\* Exige motivo. Un técnico sin `work_orders:assign` solo mueve órdenes asignadas a él o sin
asignar (al moverla se le asigna).

### Diagnóstico

| Tabla | Sprint | Columnas clave | Restricciones |
|---|---|---|---|
| Catálogo de pruebas | ✅ 4 | En código (`backend/app/modules/diagnostics/catalog.py`): código, nombre, componente, categorías, automática o manual | Igual en todos los entornos (ADR-030) |
| `diagnostic_sessions` | ✅ 4 | work_order_id, started_by_id, closed_at, closed_by_id, conclusion, recommendation, agent_version, agent_elevated, agent_reported_at | `uq(work_order_id)` |
| `diagnostic_results` | ✅ 4 | session_id, test_code, result (OK, WARNING, FAIL, NOT_TESTED, NOT_SUPPORTED), observation, evidence JSONB, source (MANUAL, AGENT, AI_SUGGESTION), recorded_by_id, recorded_at | `uq(session_id, test_code)` |
| `agent_pairings` | ✅ 4 | session_id, code_hash, expires_at, paired_at, token_hash, token_expires_at, reported_at | `uq(code_hash)`, `uq(token_hash)`; SHA-256 |

`source = AI_SUGGESTION` nunca se presenta como resultado comprobado (Módulo 12).

### Reparación, inventario y comercial

| Tabla | Sprint | Columnas clave | Restricciones |
|---|---|---|---|
| `repair_tasks` | 📐 5 | work_order_id, technician_id, description, procedure, labor_minutes, status | — |
| `qc_checklists`, `qc_results` | 📐 5 | ítems requeridos por categoría; resultado por ítem | no se finaliza sin QC completo |
| `parts` | 📐 5 | sku, name, kind (PART, COMPONENT, ACCESSORY, CONSUMABLE), unit_cost, sale_price, min_stock | `uq(organization_id, sku)` |
| `suppliers` | 📐 5 | name, nit, contact, phone, email | — |
| `stock_levels` | 📐 5 | part_id, branch_id, quantity | `ck(quantity >= 0)`, `uq(part_id, branch_id)` |
| `inventory_movements` | 📐 5 | part_id, branch_id, type (IN, OUT, ADJUSTMENT, RETURN), quantity, unit_cost, reference_type, reference_id, created_by | solo inserción |
| `purchase_orders`, `purchase_order_items` | 📐 5 | supplier_id, status, items | — |
| `repair_task_parts` | 📐 5 | repair_task_id, part_id, quantity, movement_id | FK al movimiento que descontó el stock |
| `quotations` | 📐 5 | work_order_id, number, version, status (DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED), subtotal, discount_total, tax_total, total, discount_authorized_by | montos `NUMERIC(14,2)` |
| `quotation_items` | 📐 5 | quotation_id, kind (LABOR, PART), part_id, description, quantity, unit_price, discount, **tax_rate** (0 o 0.19) | IVA por ítem (ADR-010) |
| `payments` | 📐 5 | work_order_id, amount, method (CASH, TRANSFER, CARD, NEQUI, DAVIPLATA), reference, received_by, paid_at | `ck(amount > 0)` |
| `warranties` | 📐 6 | work_order_id, starts_at, ends_at, conditions | — |
| `warranty_claims` | 📐 6 | warranty_id, reported_issue, diagnosis, resolution, new_work_order_id | — |

**Transacción de consumo de repuestos (Sprint 5):** en una sola transacción se ejecuta
`SELECT … FOR UPDATE` sobre `stock_levels`, se valida la cantidad, se inserta el registro en
`inventory_movements` (OUT) y se inserta el registro en `repair_task_parts`. Si falta stock se
hace rollback completo.
