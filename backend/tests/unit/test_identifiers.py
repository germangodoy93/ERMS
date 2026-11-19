import pytest

from app.modules.privacy.catalog import ConsentPurpose
from app.modules.privacy.template import render_authorizations, render_policy
from app.shared.identifiers import (
    IdType,
    luhn_is_valid,
    nit_check_digit,
    normalize_id_number,
    normalize_imei,
    normalize_nit,
    normalize_phone,
    normalize_serial,
    search_key,
)

# Public, well-known NITs of Colombian entities (check digits published by DIAN).
KNOWN_NITS = [("890903938", 8), ("860034313", 7), ("899999068", 1)]


@pytest.mark.parametrize(("base", "dv"), KNOWN_NITS)
def test_nit_check_digit_matches_dian(base: str, dv: int) -> None:
    assert nit_check_digit(base) == dv


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("890.903.938-8", "890903938-8"),
        ("890903938", "890903938-8"),  # without DV: it is computed
        (" 890903938-8 ", "890903938-8"),
    ],
)
def test_normalize_nit(raw: str, expected: str) -> None:
    assert normalize_nit(raw) == expected


@pytest.mark.parametrize("raw", ["890903938-1", "12345", "ABC123456", "890903938-88"])
def test_normalize_nit_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError, match="NIT"):
        normalize_nit(raw)


@pytest.mark.parametrize(
    ("id_type", "raw", "expected"),
    [
        (IdType.CC, "1.020.304.050", "1020304050"),
        (IdType.CE, "000123456", "123456"),
        (IdType.PAS, "ab 123 456", "AB123456"),
        (IdType.NIT, "890903938", "890903938-8"),
    ],
)
def test_normalize_id_number(id_type: IdType, raw: str, expected: str) -> None:
    assert normalize_id_number(id_type, raw) == expected


@pytest.mark.parametrize(
    ("id_type", "raw"), [(IdType.CC, "12A45"), (IdType.TI, "12"), (IdType.PAS, "A1")]
)
def test_normalize_id_number_rejects_invalid(id_type: IdType, raw: str) -> None:
    with pytest.raises(ValueError, match="debe tener"):
        normalize_id_number(id_type, raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("300 123 4567", "+573001234567"),
        ("(300) 123-4567", "+573001234567"),
        ("+57 300 123 4567", "+573001234567"),
        ("573001234567", "+573001234567"),
        ("601 234 5678", "+576012345678"),  # Bogotá landline, national plan since 2021
        ("+1 415 555 0100", "+14155550100"),
    ],
)
def test_normalize_phone(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw", ["2345678", "4001234567", "300-123-456", "+57 1 2345678", "tel 300"]
)
def test_normalize_phone_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError, match="teléfono"):
        normalize_phone(raw)


def test_imei_luhn() -> None:
    # Example IMEI widely used in documentation (valid check digit).
    assert normalize_imei("49-015420-323751-8") == "490154203237518"
    assert luhn_is_valid("490154203237518")
    with pytest.raises(ValueError, match="no es válido"):
        normalize_imei("490154203237519")
    with pytest.raises(ValueError, match="15 dígitos"):
        normalize_imei("4901542032375")


def test_serial_is_normalized() -> None:
    assert normalize_serial(" c02x 1234 ab ") == "C02X1234AB"
    with pytest.raises(ValueError, match="serial"):
        normalize_serial("ab")


def test_search_key_ignores_accents_and_case() -> None:
    assert search_key("  José   MUÑOZ  Pérez ") == "jose munoz perez"


def test_policy_template_includes_responsible_data_and_flows() -> None:
    text = render_policy(
        legal_name="Taller Ficticio SAS",
        tax_id="890903938-8",
        address="Calle Falsa 123",
        city="Bogotá",
        phone="+573001234567",
        email="contacto@example.com",
    )
    for value in ("Taller Ficticio SAS", "890903938-8", "Calle Falsa 123", "contacto@example.com"):
        assert value in text
    # Legal minimums: rights, deadlines and the SIC.
    assert "diez (10) días hábiles" in text
    assert "quince (15) días hábiles" in text
    assert "Superintendencia de Industria y Comercio" in text
    # Hard wraps are removed: list items stay on their own line, sentences flow.
    assert "\na) Registrar al cliente y los equipos que entrega.\n" in text
    assert "1. RESPONSABLE DEL TRATAMIENTO\nTaller Ficticio SAS, identificado" in text


def test_authorization_texts_reference_policy_version() -> None:
    texts = render_authorizations(name="Taller Ficticio SAS", version=3)
    assert set(texts) == set(ConsentPurpose)
    assert "(versión 3)" in texts[ConsentPurpose.DATA_PROCESSING]
    assert "formateos" in texts[ConsentPurpose.DIAGNOSTIC_AGENT]
