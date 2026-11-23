from decimal import Decimal

import pytest

from app.modules.assembly.pricing import parse_pesos, sale_price


@pytest.mark.parametrize(
    ("cost", "margin", "expected"),
    [
        ("1999000", "15", "2299000"),  # 2.298.850 rounds UP to the next $1.000
        ("451605", "15", "520000"),  # 519.345,75
        ("200000", "15", "230000"),  # exact: no rounding
        ("100000", "0", "100000"),
        ("0", "15", "0"),
    ],
)
def test_sale_price_is_cost_plus_margin_rounded_up(cost: str, margin: str, expected: str) -> None:
    assert sale_price(Decimal(cost), Decimal(margin)) == Decimal(expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$ 1,999,000", "1999000"),
        ("1.999.000", "1999000"),
        ("451605", "451605"),
        (" $ 451,605 ", "451605"),
        ("1999000,50", "1999000.50"),
        ("1.999.000,50", "1999000.50"),
        ("gratis", None),
        ("", None),
    ],
)
def test_parse_pesos(text: str, expected: str | None) -> None:
    assert parse_pesos(text) == (Decimal(expected) if expected else None)
