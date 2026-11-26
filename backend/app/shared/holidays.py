"""Colombian public holidays, computed (no external service).

- Fixed dates: 1 Jan, 1 May, 20 Jul, 7 Aug, 8 Dec, 25 Dec.
- Ley 51 de 1983 ("Ley Emiliani"): these move to the next Monday when they do not fall on a
  Monday: 6 Jan, 19 Mar, 29 Jun, 15 Aug, 12 Oct, 1 Nov, 11 Nov.
- Easter based: Holy Thursday and Good Friday (fixed), and Ascension (+39), Corpus Christi
  (+60) and Sacred Heart (+68), moved to the next Monday (Easter + 43, + 64 and + 71).
"""

from datetime import date, timedelta
from functools import cache

FIXED: tuple[tuple[int, int, str], ...] = (
    (1, 1, "Año Nuevo"),
    (5, 1, "Día del Trabajo"),
    (7, 20, "Día de la Independencia"),
    (8, 7, "Batalla de Boyacá"),
    (12, 8, "Inmaculada Concepción"),
    (12, 25, "Navidad"),
)
MOVABLE: tuple[tuple[int, int, str], ...] = (
    (1, 6, "Reyes Magos"),
    (3, 19, "San José"),
    (6, 29, "San Pedro y San Pablo"),
    (8, 15, "Asunción de la Virgen"),
    (10, 12, "Día de la Raza"),
    (11, 1, "Todos los Santos"),
    (11, 11, "Independencia de Cartagena"),
)
EASTER_FIXED: tuple[tuple[int, str], ...] = ((-3, "Jueves Santo"), (-2, "Viernes Santo"))
EASTER_MOVED: tuple[tuple[int, str], ...] = (
    (43, "Ascensión del Señor"),
    (64, "Corpus Christi"),
    (71, "Sagrado Corazón"),
)


def easter_sunday(year: int) -> date:
    """Gregorian Easter (anonymous algorithm, Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def _next_monday(day: date) -> date:
    return day + timedelta(days=(7 - day.weekday()) % 7)


@cache
def holidays(year: int) -> dict[date, str]:
    """Holidays of the year, by date."""
    result: dict[date, str] = {date(year, m, d): name for m, d, name in FIXED}
    for m, d, name in MOVABLE:
        result[_next_monday(date(year, m, d))] = name
    easter = easter_sunday(year)
    for offset, name in EASTER_FIXED + EASTER_MOVED:
        result[easter + timedelta(days=offset)] = name
    return dict(sorted(result.items()))


def holiday_name(day: date) -> str | None:
    return holidays(day.year).get(day)
