"""Reusable Pydantic field validators built on `app.shared.identifiers`."""

from app.shared.identifiers import (
    collapse_spaces,
    normalize_imei,
    normalize_nit,
    normalize_phone,
    normalize_serial,
)


def clean_text(value: str | None) -> str | None:
    return collapse_spaces(value)


def clean_multiline(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def optional_phone(value: str | None) -> str | None:
    value = collapse_spaces(value)
    return normalize_phone(value) if value else None


def optional_nit(value: str | None) -> str | None:
    value = collapse_spaces(value)
    return normalize_nit(value) if value else None


def optional_email(value: str | None) -> str | None:
    value = collapse_spaces(value)
    return value.lower() if value else None


def optional_imei(value: str | None) -> str | None:
    value = collapse_spaces(value)
    return normalize_imei(value) if value else None


def optional_serial(value: str | None) -> str | None:
    value = collapse_spaces(value)
    return normalize_serial(value) if value else None
