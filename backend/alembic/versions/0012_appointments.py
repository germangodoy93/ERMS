"""Agenda of remote and on-site appointments (PM-04, sprint R1): service catalog, service
hours, appointments and the `appointments:manage` permission.

Revision ID: 0012_appointments
Revises: 0011_notices
Create Date: 2026-11-26
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0012_appointments"
down_revision: str | None = "0011_notices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {
    "appointments:manage": "Agendar, mover y cancelar citas remotas y en sitio",
}
GRANTS = {
    "ADMIN": set(NEW_PERMISSIONS),
    "SUPERVISOR": set(NEW_PERMISSIONS),
    "RECEPTIONIST": set(NEW_PERMISSIONS),
}
VISIT_DESCRIPTION = (
    "El técnico va al sitio, hace el diagnóstico y sigue el proceso normal de la orden "
    "(cotización, autorización, reparación y entrega)."
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.add_column("organizations", sa.Column("field_service_hours", JSONB(), nullable=True))
    op.create_table(
        "field_services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("modality", sa.String(10), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=True),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("price_includes_tax", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "modality IN ('REMOTE', 'ON_SITE')", name="ck_field_services_modality_valid"
        ),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 15 AND 480", name="ck_field_services_duration_valid"
        ),
        sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_field_services_price_positive"),
        sa.CheckConstraint("tax_rate IN (0, 19)", name="ck_field_services_tax_rate_valid"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_field_services_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_field_services"),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_field_services_organization_id_name"
        ),
    )
    op.create_index("ix_field_services_organization_id", "field_services", ["organization_id"])
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(20), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("modality", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("technician_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("locality", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "overlap_reason",
            sa.Text(),
            nullable=True,
            comment="Por qué se agendó aunque el técnico tenía otra cita",
        ),
        sa.Column("remote_consent_channel", sa.String(10), nullable=True),
        sa.Column("remote_consent_text", sa.Text(), nullable=True),
        sa.Column("remote_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "modality IN ('REMOTE', 'ON_SITE')", name="ck_appointments_modality_valid"
        ),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'CANCELLED')", name="ck_appointments_status_valid"
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_appointments_ends_after_start"),
        sa.CheckConstraint(
            "modality <> 'ON_SITE' OR (address IS NOT NULL AND locality IS NOT NULL)",
            name="ck_appointments_on_site_has_address",
        ),
        sa.CheckConstraint(
            "modality <> 'REMOTE' OR remote_consent_at IS NOT NULL",
            name="ck_appointments_remote_has_consent",
        ),
        sa.CheckConstraint(
            "status <> 'CANCELLED' OR cancel_reason IS NOT NULL",
            name="ck_appointments_cancel_has_reason",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_appointments_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_appointments_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["field_services.id"],
            name="fk_appointments_service_id_field_services",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["technician_id"],
            ["users.id"],
            name="fk_appointments_technician_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_appointments_created_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
        sa.UniqueConstraint(
            "organization_id", "number", name="uq_appointments_organization_id_number"
        ),
    )
    op.create_index("ix_appointments_customer_id", "appointments", ["customer_id"])
    op.create_index(
        "ix_appointments_organization_id_starts_at",
        "appointments",
        ["organization_id", "starts_at"],
    )
    op.create_index(
        "ix_appointments_technician_id_starts_at", "appointments", ["technician_id", "starts_at"]
    )

    conn = op.get_bind()
    # Every existing workshop starts with the technical visit (price set by the workshop).
    conn.execute(
        sa.text(
            "INSERT INTO field_services (id, organization_id, name, modality, duration_minutes, "
            "description) SELECT gen_random_uuid(), id, 'Visita técnica', 'ON_SITE', 60, :d "
            "FROM organizations"
        ),
        {"d": VISIT_DESCRIPTION},
    )
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions,
        [{"id": uuid.uuid4(), "code": c, "description": d} for c, d in NEW_PERMISSIONS.items()],
    )
    for role_code, codes in GRANTS.items():
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes) "
                "WHERE r.code = :role AND r.is_system"
            ),
            {"codes": sorted(codes), "role": role_code},
        )


def downgrade() -> None:
    op.drop_table("appointments")
    op.drop_table("field_services")
    op.drop_column("organizations", "field_service_hours")
    codes = sorted(NEW_PERMISSIONS)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(codes=codes)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(codes=codes))
