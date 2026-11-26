"""Colombian holidays and the service-hours rules of the agenda (PM-04, sprint R1)."""

from datetime import date, datetime, time

import pytest

from app.modules.appointments.catalog import DEFAULT_HOURS, LOCALITIES
from app.modules.appointments.schemas import AppointmentCreate, HoursDay, HoursUpdate
from app.modules.appointments.service import hours_of, schedule_problem
from app.modules.organizations.models import Organization
from app.shared.context import BOGOTA
from app.shared.holidays import easter_sunday, holiday_name, holidays

# Official list published for 2026 (Ley 51 de 1983 applied).
HOLIDAYS_2026 = [
    date(2026, 1, 1),
    date(2026, 1, 12),
    date(2026, 3, 23),
    date(2026, 4, 2),
    date(2026, 4, 3),
    date(2026, 5, 1),
    date(2026, 5, 18),
    date(2026, 6, 8),
    date(2026, 6, 15),
    date(2026, 6, 29),
    date(2026, 7, 20),
    date(2026, 8, 7),
    date(2026, 8, 17),
    date(2026, 10, 12),
    date(2026, 11, 2),
    date(2026, 11, 16),
    date(2026, 12, 8),
    date(2026, 12, 25),
]


def test_holidays_2026_match_the_official_calendar() -> None:
    assert list(holidays(2026)) == HOLIDAYS_2026
    assert holiday_name(date(2026, 4, 3)) == "Viernes Santo"
    assert holiday_name(date(2026, 1, 12)) == "Reyes Magos"
    assert holiday_name(date(2026, 1, 6)) is None


@pytest.mark.parametrize(
    ("year", "easter"),
    [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2027, date(2027, 3, 28))],
)
def test_easter_sunday(year: int, easter: date) -> None:
    assert easter_sunday(year) == easter


def test_holidays_2027_move_to_monday() -> None:
    days = holidays(2027)
    assert len(days) == 18
    # Moved holidays always fall on Monday; the fixed ones keep their date.
    fixed = {(1, 1), (5, 1), (7, 20), (8, 7), (12, 8), (12, 25)}
    easter = easter_sunday(2027)
    for day in days:
        if (day.month, day.day) in fixed or (easter - day).days in (2, 3):
            continue
        assert day.weekday() == 0, day
    assert date(2027, 3, 25) in days  # Holy Thursday
    assert date(2027, 1, 11) in days  # Reyes Magos, moved from Wednesday 6


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), BOGOTA)


def _default_hours() -> list[HoursDay]:
    return hours_of(Organization(field_service_hours=None))


def test_default_hours() -> None:
    hours = _default_hours()
    assert [(d.opens, d.closes) for d in hours][:2] == [(time(8), time(18))] * 2
    assert (hours[5].opens, hours[5].closes) == (time(8), time(12))
    assert hours[6].opens is None
    assert len(DEFAULT_HOURS) == 7


def test_schedule_rules() -> None:
    hours = _default_hours()
    monday = date(2026, 11, 30)
    saturday = date(2026, 11, 28)
    assert schedule_problem(hours, _at(monday, 8), _at(monday, 9)) is None
    assert schedule_problem(hours, _at(monday, 17), _at(monday, 18)) is None
    assert "Fuera del horario" in (
        schedule_problem(hours, _at(monday, 17), _at(monday, 18, 30)) or ""
    )
    assert "Fuera del horario" in (
        schedule_problem(hours, _at(monday, 7, 30), _at(monday, 8, 30)) or ""
    )
    assert schedule_problem(hours, _at(saturday, 11), _at(saturday, 12)) is None
    assert "Fuera del horario" in (
        schedule_problem(hours, _at(saturday, 11, 30), _at(saturday, 12, 30)) or ""
    )
    assert "no hay servicio" in (
        schedule_problem(hours, _at(date(2026, 11, 29), 9), _at(date(2026, 11, 29), 10)) or ""
    )
    assert "festivo (Inmaculada Concepción)" in (
        schedule_problem(hours, _at(date(2026, 12, 8), 9), _at(date(2026, 12, 8), 10)) or ""
    )
    late = schedule_problem(hours, _at(monday, 17), _at(date(2026, 12, 1), 9))
    assert late == "La cita debe empezar y terminar el mismo día."
    # Times in UTC are read in Bogotá: 13:00 UTC is 8:00 in Bogotá.
    assert (
        schedule_problem(
            hours,
            datetime.fromisoformat("2026-11-30T13:00:00+00:00"),
            datetime.fromisoformat("2026-11-30T14:00:00+00:00"),
        )
        is None
    )


def test_stored_hours_replace_the_defaults() -> None:
    hours = hours_of(Organization(field_service_hours={"0": ["10:00", "14:00"], "1": None}))
    assert (hours[0].opens, hours[0].closes) == (time(10), time(14))
    assert hours[1].opens is None
    assert hours[5].opens is None  # missing day: no service


def test_hours_validation() -> None:
    with pytest.raises(ValueError, match="posterior"):
        HoursDay(weekday=0, opens=time(10), closes=time(9))
    with pytest.raises(ValueError, match="o deje el día"):
        HoursDay(weekday=0, opens=time(10), closes=None)
    days = [HoursDay(weekday=d, opens=None, closes=None) for d in range(6)]
    with pytest.raises(ValueError, match="siete días"):
        HoursUpdate(days=[*days, HoursDay(weekday=0, opens=None, closes=None)])


def test_appointment_input_rules() -> None:
    base = {
        "customer_id": "00000000-0000-0000-0000-000000000001",
        "service_id": "00000000-0000-0000-0000-000000000002",
        "starts_at": "2026-11-30T09:00:00-05:00",
        "reason": "No enciende el computador.",
    }
    assert AppointmentCreate.model_validate({**base, "locality": "Suba"}).locality == "Suba"
    with pytest.raises(ValueError, match="zona horaria"):
        AppointmentCreate.model_validate({**base, "starts_at": "2026-11-30T09:00:00"})
    with pytest.raises(ValueError, match="localidad"):
        AppointmentCreate.model_validate({**base, "locality": "Narnia"})
    with pytest.raises(ValueError, match="multiple of 5"):
        AppointmentCreate.model_validate({**base, "duration_minutes": 7})
    assert "Otro municipio" in LOCALITIES
    assert len(LOCALITIES) == 21
