"""Assembly pricing: supplier cost + workshop margin, prices fixed by hand.

Parts imported with 0008 stored the supplier price as the sale price and a zero cost. This
migration moves that value to the cost and recomputes the sale price with the default 15 %
margin, rounded up to the next $1.000.

Revision ID: 0009_assembly_pricing
Revises: 0008_assembly
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_assembly_pricing"
down_revision: str | None = "0008_assembly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "parts",
        sa.Column(
            "price_locked",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Precio de venta fijado a mano: no se recalcula con el costo y el margen",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "assembly_margin_percent", sa.Numeric(5, 2), server_default="15", nullable=False
        ),
    )
    op.execute(
        "UPDATE parts SET unit_cost = sale_price, "
        "sale_price = CEIL(sale_price * 1.15 / 1000) * 1000 "
        "WHERE assembly_category IS NOT NULL AND unit_cost = 0"
    )


def downgrade() -> None:
    op.drop_column("organizations", "assembly_margin_percent")
    op.drop_column("parts", "price_locked")
