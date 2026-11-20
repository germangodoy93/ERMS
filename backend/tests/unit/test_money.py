from decimal import Decimal

import pytest

from app.shared.money import line_amounts, money

D = Decimal


def test_price_without_vat_adds_19_percent() -> None:
    amounts = line_amounts(D(1), D(100000), D(0), D(19), price_includes_tax=False)
    assert (amounts.base, amounts.tax, amounts.total) == (
        D("100000.00"),
        D("19000.00"),
        D("119000.00"),
    )


def test_price_with_vat_included_is_split() -> None:
    amounts = line_amounts(D(1), D(119000), D(0), D(19), price_includes_tax=True)
    assert (amounts.base, amounts.tax, amounts.total) == (
        D("100000.00"),
        D("19000.00"),
        D("119000.00"),
    )


def test_no_vat() -> None:
    amounts = line_amounts(D(2), D(45000), D(0), D(0), price_includes_tax=False)
    assert (amounts.base, amounts.tax, amounts.total) == (D("90000.00"), D("0.00"), D("90000.00"))


def test_discount_before_vat_and_rounding() -> None:
    amounts = line_amounts(D(3), D("33333.33"), D("10"), D(19), price_includes_tax=False)
    assert amounts.gross == D("99999.99")
    assert amounts.discount == D("10000.00")
    assert amounts.base == D("89999.99")
    assert amounts.tax == D("17100.00")
    assert amounts.total == amounts.base + amounts.tax


@pytest.mark.parametrize("price", ["1", "999.99", "1234567.89", "50000"])
def test_included_vat_always_adds_up(price: str) -> None:
    amounts = line_amounts(D(1), D(price), D(0), D(19), price_includes_tax=True)
    assert amounts.base + amounts.tax == amounts.total == money(price)


def test_money_rounds_half_up() -> None:
    assert money("0.005") == D("0.01")
    assert money("2.675") == D("2.68")
