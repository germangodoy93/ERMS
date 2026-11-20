"""Permission catalog and system roles.

Permissions are defined in code and inserted by Alembic data migrations, so every
environment (local, CI, Railway) has exactly the same catalog. When a sprint adds
permissions, it adds them here AND in a new migration that grants them to system roles.
"""

from enum import StrEnum


class RoleCode(StrEnum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    TECHNICIAN = "TECHNICIAN"
    RECEPTIONIST = "RECEPTIONIST"


class Perm(StrEnum):
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    ROLES_MANAGE = "roles:manage"
    AUDIT_READ = "audit:read"
    ORGANIZATION_MANAGE = "organization:manage"
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_MANAGE = "customers:manage"
    CUSTOMERS_ANONYMIZE = "customers:anonymize"
    DEVICES_MANAGE = "devices:manage"
    CATALOG_MANAGE = "catalog:manage"
    WORK_ORDERS_READ = "work_orders:read"
    WORK_ORDERS_CREATE = "work_orders:create"
    WORK_ORDERS_ASSIGN = "work_orders:assign"
    WORK_ORDERS_PROGRESS = "work_orders:progress"
    WORK_ORDERS_DELIVER = "work_orders:deliver"


PERMISSION_DESCRIPTIONS: dict[Perm, str] = {
    Perm.USERS_READ: "Consultar usuarios y roles",
    Perm.USERS_MANAGE: "Crear y editar usuarios y asignar roles (excepto Administrador)",
    Perm.ROLES_MANAGE: "Editar permisos de roles y asignar el rol Administrador",
    Perm.AUDIT_READ: "Consultar la auditoría",
    Perm.ORGANIZATION_MANAGE: "Editar los datos del taller y publicar la política de datos",
    Perm.CUSTOMERS_READ: "Consultar clientes, sus equipos y consentimientos",
    Perm.CUSTOMERS_MANAGE: "Crear y editar clientes y registrar consentimientos",
    Perm.CUSTOMERS_ANONYMIZE: "Anonimizar clientes (derecho de supresión)",
    Perm.DEVICES_MANAGE: "Registrar y editar equipos de clientes",
    Perm.CATALOG_MANAGE: "Administrar fabricantes y modelos",
    Perm.WORK_ORDERS_READ: "Consultar órdenes de servicio",
    Perm.WORK_ORDERS_CREATE: "Recibir equipos y crear órdenes de servicio",
    Perm.WORK_ORDERS_ASSIGN: "Asignar técnicos a las órdenes",
    Perm.WORK_ORDERS_PROGRESS: "Avanzar las etapas técnicas de las órdenes",
    Perm.WORK_ORDERS_DELIVER: "Registrar decisiones del cliente, cancelar y entregar equipos",
}

SYSTEM_ROLES: dict[RoleCode, tuple[str, frozenset[Perm]]] = {
    RoleCode.ADMIN: ("Administrador", frozenset(Perm)),
    RoleCode.SUPERVISOR: (
        "Supervisor",
        frozenset(
            {
                Perm.USERS_READ,
                Perm.USERS_MANAGE,
                Perm.AUDIT_READ,
                Perm.CUSTOMERS_READ,
                Perm.CUSTOMERS_MANAGE,
                Perm.DEVICES_MANAGE,
                Perm.CATALOG_MANAGE,
                Perm.WORK_ORDERS_READ,
                Perm.WORK_ORDERS_CREATE,
                Perm.WORK_ORDERS_ASSIGN,
                Perm.WORK_ORDERS_PROGRESS,
                Perm.WORK_ORDERS_DELIVER,
            }
        ),
    ),
    RoleCode.TECHNICIAN: (
        "Técnico",
        frozenset(
            {
                Perm.CUSTOMERS_READ,
                Perm.DEVICES_MANAGE,
                Perm.WORK_ORDERS_READ,
                Perm.WORK_ORDERS_PROGRESS,
            }
        ),
    ),
    RoleCode.RECEPTIONIST: (
        "Recepcionista",
        frozenset(
            {
                Perm.CUSTOMERS_READ,
                Perm.CUSTOMERS_MANAGE,
                Perm.DEVICES_MANAGE,
                Perm.WORK_ORDERS_READ,
                Perm.WORK_ORDERS_CREATE,
                Perm.WORK_ORDERS_ASSIGN,
                Perm.WORK_ORDERS_DELIVER,
            }
        ),
    ),
}
