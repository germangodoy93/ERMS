"""Money arithmetic in Colombian pesos: Decimal, two places, ROUND_HALF_UP.

A line's price may be entered with or without IVA (ADR-010 and Sprint 5 decision): both are
supported and always produce base + tax = total exactly.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal(100)
VAT_RATES = (Decimal("0"), Decimal("19"))  # percent; 0 = without IVA (exento/excluido/no aplica)


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class LineAmounts:
    gross: Decimal  # quantity * unit price, as entered
    discount: Decimal
    base: Decimal  # without IVA
    tax: Decimal
    total: Decimal


def line_amounts(
    quantity: Decimal,
    unit_price: Decimal,
    discount_percent: Decimal,
    tax_rate: Decimal,
    *,
    price_includes_tax: bool,
) -> LineAmounts:
    gross = money(quantity * unit_price)
    discount = money(gross * discount_percent / HUNDRED)
    net = gross - discount
    rate = tax_rate / HUNDRED
    if price_includes_tax:
        total = net
        base = money(total / (1 + rate))
        tax = total - base
    else:
        base = net
        tax = money(base * rate)
        total = base + tax
    return LineAmounts(gross=gross, discount=discount, base=base, tax=tax, total=total)
