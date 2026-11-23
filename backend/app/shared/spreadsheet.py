"""Helpers for spreadsheets (CSV) opened in Excel."""

from decimal import Decimal

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> str:
    """Prevents CSV formula injection: text that starts like a formula is quoted. Numbers
    (including negative ones) are left as they are."""
    text = "" if value is None else str(value)
    if text.startswith(FORMULA_PREFIXES):
        try:
            Decimal(text)
        except ArithmeticError:
            return "'" + text
    return text
