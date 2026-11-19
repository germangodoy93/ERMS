"""Normalization and validation of Colombian identifiers, phones and device identifiers.

Pure functions (no I/O) so they are reused by Pydantic schemas and services and are easy
to unit test. Every function returns the canonical form that is stored, or raises
`ValueError` with a message in Spanish suitable for the API response.
"""

import re
import unicodedata
from enum import StrEnum


class IdType(StrEnum):
    CC = "CC"  # Cédula de ciudadanía
    CE = "CE"  # Cédula de extranjería
    NIT = "NIT"  # Número de identificación tributaria
    PAS = "PAS"  # Pasaporte
    TI = "TI"  # Tarjeta de identidad
    PPT = "PPT"  # Permiso por protección temporal


# DIAN weights for the NIT check digit, applied from the rightmost digit.
_NIT_WEIGHTS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
_SEPARATORS = re.compile(r"[\s.\-()]")


def collapse_spaces(value: str | None) -> str | None:
    """Trim and collapse internal whitespace; empty strings become None."""
    if value is None:
        return None
    value = " ".join(value.split())
    return value or None


def search_key(value: str) -> str:
    """Lower-case text without accents, used to search names regardless of tildes."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_marks.lower().split())


def nit_check_digit(base: str) -> int:
    """Check digit (dígito de verificación) of a NIT according to DIAN."""
    total = sum(int(d) * w for d, w in zip(reversed(base), _NIT_WEIGHTS, strict=False))
    remainder = total % 11
    return remainder if remainder < 2 else 11 - remainder


def normalize_nit(raw: str) -> str:
    """Returns `<base>-<dv>`. Accepts the NIT with or without check digit."""
    text = raw.strip().replace(".", "").replace(" ", "")
    if "-" in text:
        base, _, dv = text.partition("-")
        if not (base.isdigit() and dv.isdigit() and len(dv) == 1):
            raise ValueError("El NIT debe tener el formato 900123456-7.")
    else:
        base, dv = text, ""
    if not base.isdigit() or not 6 <= len(base) <= 15:
        raise ValueError("El NIT debe tener entre 6 y 15 dígitos antes del dígito de verificación.")
    expected = nit_check_digit(base)
    if dv and int(dv) != expected:
        raise ValueError("El dígito de verificación del NIT no es válido.")
    return f"{base}-{expected}"


def normalize_id_number(id_type: IdType, raw: str) -> str:
    if id_type is IdType.NIT:
        return normalize_nit(raw)
    if id_type is IdType.PAS:
        text = _SEPARATORS.sub("", raw).upper()
        if not text.isalnum() or not 4 <= len(text) <= 20:
            raise ValueError("El pasaporte debe tener entre 4 y 20 letras o números.")
        return text
    text = _SEPARATORS.sub("", raw)
    if not text.isdigit() or not 3 <= len(text) <= 15:
        raise ValueError("El número de documento debe tener entre 3 y 15 dígitos.")
    return text.lstrip("0") or "0"


def normalize_phone(raw: str) -> str:
    """Stores phones in E.164. Colombian numbers may be written without +57.

    Valid Colombian numbers have 10 digits: mobiles start with 3 and landlines with 60
    (national dialing plan in force since 2021). Foreign numbers must start with '+'.
    """
    text = _SEPARATORS.sub("", raw.strip())
    if text.startswith("+"):
        digits = text[1:]
        if not digits.isdigit():
            raise ValueError("El teléfono solo puede tener números.")
        if digits.startswith("57"):
            return "+57" + _colombian_number(digits[2:])
        if not 8 <= len(digits) <= 15:
            raise ValueError("El teléfono internacional debe tener entre 8 y 15 dígitos.")
        return "+" + digits
    if not text.isdigit():
        raise ValueError("El teléfono solo puede tener números.")
    if len(text) == 12 and text.startswith("57"):
        text = text[2:]
    return "+57" + _colombian_number(text)


def _colombian_number(digits: str) -> str:
    if len(digits) != 10 or not (digits.startswith("3") or digits.startswith("60")):
        raise ValueError(
            "El teléfono colombiano debe tener 10 dígitos: celular (3XX) o fijo (60X)."
        )
    return digits


def luhn_is_valid(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def normalize_imei(raw: str) -> str:
    text = _SEPARATORS.sub("", raw).replace("/", "")
    if not text.isdigit() or len(text) != 15:
        raise ValueError("El IMEI debe tener 15 dígitos (marque *#06# en el celular).")
    if not luhn_is_valid(text):
        raise ValueError("El IMEI no es válido: revise los dígitos.")
    return text


def normalize_serial(raw: str) -> str:
    text = re.sub(r"\s+", "", raw).upper()
    if not 3 <= len(text) <= 64:
        raise ValueError("El serial debe tener entre 3 y 64 caracteres.")
    return text
