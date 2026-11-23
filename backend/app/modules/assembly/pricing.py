"""Sale prices of assembly parts from the supplier cost.

The workshop buys at the supplier's list price (VAT included) and sells at cost + margin,
rounded UP to the next $1.000. A part whose price was fixed by hand (`price_locked`) keeps it.
"""

import re
import uuid
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inventory.models import Part

STEP = Decimal("1000")


def sale_price(cost: Decimal, margin_percent: Decimal) -> Decimal:
    raw = cost * (Decimal("1") + margin_percent / Decimal("100"))
    return (raw / STEP).to_integral_value(rounding=ROUND_CEILING) * STEP


def apply_price(part: Part, margin_percent: Decimal) -> None:
    """Recomputes the sale price of an assembly part unless it was fixed by hand."""
    if part.assembly_category is not None and not part.price_locked:
        part.sale_price = sale_price(part.unit_cost, margin_percent)


def reprice_all(session: Session, organization_id: uuid.UUID, margin_percent: Decimal) -> int:
    """After a margin change: new sale price for every assembly part not fixed by hand."""
    parts = session.scalars(
        select(Part).where(
            Part.organization_id == organization_id,
            Part.assembly_category.is_not(None),
            Part.price_locked.is_(False),
        )
    )
    count = 0
    for part in parts:
        part.sale_price = sale_price(part.unit_cost, margin_percent)
        count += 1
    session.flush()
    return count


def parse_pesos(text: str) -> Decimal | None:
    """Amounts as written in supplier lists: "$ 1,999,000", "1.999.000", "451605" (thousand
    separators of either kind) or with cents, "1999000,50" / "1999000.50"."""
    text = text.strip()
    cents = Decimal("0")
    match = re.search(r"[.,](\d{2})$", text)
    if match:
        cents = Decimal(match.group(1)) / 100
        text = text[: match.start()]
    digits = "".join(ch for ch in text if ch.isdigit())
    return Decimal(digits) + cents if digits else None
