"""Customers, Habeas Data consents, privacy policy and device catalog.

Revision ID: 0003_customers_devices
Revises: 0002_identity_access
Create Date: 2026-11-19
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_customers_devices"
down_revision: str | None = "0002_identity_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copies of the catalogs at this revision (migrations never import app code).
NEW_PERMISSIONS = {
    "organization:manage": "Editar los datos del taller y publicar la política de datos",
    "customers:read": "Consultar clientes, sus equipos y consentimientos",
    "customers:manage": "Crear y editar clientes y registrar consentimientos",
    "customers:anonymize": "Anonimizar clientes (derecho de supresión)",
    "devices:manage": "Registrar y editar equipos de clientes",
    "catalog:manage": "Administrar fabricantes y modelos",
}
GRANTS = {
    "ADMIN": set(NEW_PERMISSIONS),
    "SUPERVISOR": {"customers:read", "customers:manage", "devices:manage", "catalog:manage"},
    "RECEPTIONIST": {"customers:read", "customers:manage", "devices:manage"},
    "TECHNICIAN": {"customers:read", "devices:manage"},
}
CATEGORIES = [
    ("LAPTOP", "Computador portátil", 1),
    ("DESKTOP", "Computador de escritorio", 2),
    ("PHONE", "Celular", 3),
    ("TABLET", "Tablet", 4),
    ("CONSOLE", "Consola de videojuegos", 5),
    ("OTHER", "Otro", 6),
]
MANUFACTURERS = (
    "Acer",
    "Apple",
    "Asus",
    "Dell",
    "HP",
    "Huawei",
    "Lenovo",
    "Microsoft",
    "Motorola",
    "Nintendo",
    "Samsung",
    "Sony",
    "Xiaomi",
)


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _org_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id"],
        ["organizations.id"],
        name=f"fk_{table}_organization_id_organizations",
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    for name, length in (("legal_name", 200), ("address", 255), ("city", 80)):
        op.add_column("organizations", sa.Column(name, sa.String(length=length), nullable=True))
    op.add_column("organizations", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("organizations", sa.Column("email", sa.String(length=254), nullable=True))

    op.create_table(
        "privacy_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by_id", sa.Uuid(), nullable=True),
        _org_fk("privacy_policies"),
        sa.ForeignKeyConstraint(
            ["published_by_id"],
            ["users.id"],
            name="fk_privacy_policies_published_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_privacy_policies"),
        sa.UniqueConstraint(
            "organization_id", "version", name="uq_privacy_policies_organization_id_version"
        ),
    )
    op.create_index("ix_privacy_policies_organization_id", "privacy_policies", ["organization_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("search_name", sa.String(length=200), nullable=False),
        sa.Column("id_type", sa.String(length=5), nullable=True),
        sa.Column("id_number", sa.String(length=32), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "(id_type IS NULL) = (id_number IS NULL)", name="ck_customers_id_type_with_number"
        ),
        sa.CheckConstraint("kind IN ('PERSON', 'COMPANY')", name="ck_customers_kind_valid"),
        sa.CheckConstraint("email = lower(email)", name="ck_customers_email_lowercase"),
        _org_fk("customers"),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_customers_created_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.UniqueConstraint(
            "organization_id",
            "id_type",
            "id_number",
            name="uq_customers_organization_id_id_type_id_number",
        ),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])
    op.create_index("ix_customers_organization_id_phone", "customers", ["organization_id", "phone"])
    op.create_index(
        "ix_customers_search_name_trgm",
        "customers",
        ["search_name"],
        postgresql_using="gin",
        postgresql_ops={"search_name": "gin_trgm_ops"},
    )

    op.create_table(
        "customer_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("channel", sa.String(length=10), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "purpose IN ('DATA_PROCESSING', 'PHOTOS', 'DIAGNOSTIC_AGENT')",
            name="ck_customer_consents_purpose_valid",
        ),
        sa.CheckConstraint(
            "channel IN ('SCREEN', 'PAPER', 'VERBAL')", name="ck_customer_consents_channel_valid"
        ),
        _org_fk("customer_consents"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_customer_consents_customer_id_customers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["privacy_policies.id"],
            name="fk_customer_consents_policy_id_privacy_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_id"],
            ["users.id"],
            name="fk_customer_consents_recorded_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customer_consents"),
    )
    op.create_index(
        "ix_customer_consents_customer_purpose",
        "customer_consents",
        ["customer_id", "purpose", "recorded_at"],
    )

    categories = op.create_table(
        "device_categories",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("code", name="pk_device_categories"),
    )
    op.bulk_insert(
        categories,
        [{"code": code, "name": name, "sort_order": order} for code, name, order in CATEGORIES],
    )

    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *_timestamps(),
        _org_fk("manufacturers"),
        sa.PrimaryKeyConstraint("id", name="pk_manufacturers"),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_manufacturers_organization_id_name"
        ),
    )
    op.create_index("ix_manufacturers_organization_id", "manufacturers", ["organization_id"])

    op.create_table(
        "device_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("manufacturer_id", sa.Uuid(), nullable=False),
        sa.Column("category_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("release_year", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *_timestamps(),
        _org_fk("device_models"),
        sa.ForeignKeyConstraint(
            ["manufacturer_id"],
            ["manufacturers.id"],
            name="fk_device_models_manufacturer_id_manufacturers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_code"],
            ["device_categories.code"],
            name="fk_device_models_category_code_device_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_device_models"),
        sa.UniqueConstraint(
            "manufacturer_id", "name", name="uq_device_models_manufacturer_id_name"
        ),
    )
    op.create_index("ix_device_models_organization_id", "device_models", ["organization_id"])

    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("serial_number", sa.String(length=64), nullable=True),
        sa.Column("imei", sa.String(length=15), nullable=True),
        sa.Column("operating_system", sa.String(length=60), nullable=True),
        sa.Column("storage", sa.String(length=40), nullable=True),
        sa.Column("color", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *_timestamps(),
        _org_fk("devices"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_devices_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["device_models.id"],
            name="fk_devices_model_id_device_models",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_devices"),
        sa.UniqueConstraint("organization_id", "imei", name="uq_devices_organization_id_imei"),
        sa.UniqueConstraint(
            "organization_id",
            "model_id",
            "serial_number",
            name="uq_devices_organization_id_model_id_serial_number",
        ),
    )
    op.create_index("ix_devices_customer_id", "devices", ["customer_id"])
    op.create_index("ix_devices_model_id", "devices", ["model_id"])
    op.create_index(
        "ix_devices_organization_id_serial_number", "devices", ["organization_id", "serial_number"]
    )

    _seed_permissions_and_catalog()


def _seed_permissions_and_catalog() -> None:
    conn = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions,
        [
            {"id": uuid.uuid4(), "code": code, "description": description}
            for code, description in NEW_PERMISSIONS.items()
        ],
    )
    # Existing organizations: grant the new permissions to their system roles...
    for role_code, codes in GRANTS.items():
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes) "
                "WHERE r.code = :role AND r.is_system"
            ),
            {"codes": sorted(codes), "role": role_code},
        )
    # ...and pre-load the default manufacturers.
    organization_ids = conn.scalars(sa.text("SELECT id FROM organizations")).all()
    manufacturers = sa.table(
        "manufacturers",
        sa.column("id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("name", sa.String()),
    )
    rows = [
        {"id": uuid.uuid4(), "organization_id": org_id, "name": name}
        for org_id in organization_ids
        for name in MANUFACTURERS
    ]
    if rows:
        op.bulk_insert(manufacturers, rows)


def downgrade() -> None:
    op.drop_table("devices")
    op.drop_table("device_models")
    op.drop_table("manufacturers")
    op.drop_table("device_categories")
    op.drop_table("customer_consents")
    op.drop_table("customers")
    op.drop_table("privacy_policies")
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(codes=sorted(NEW_PERMISSIONS))
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(
            codes=sorted(NEW_PERMISSIONS)
        )
    )
    for name in ("email", "phone", "city", "address", "legal_name"):
        op.drop_column("organizations", name)
    # pg_trgm is left installed: other objects may depend on it.
