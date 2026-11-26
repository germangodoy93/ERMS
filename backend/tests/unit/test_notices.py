from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.modules.notices.catalog import (
    DEFAULT_TEMPLATES,
    PLACEHOLDERS,
    NoticeKind,
    render,
    template_errors,
)
from app.modules.notices.models import WorkOrderNotice
from app.modules.notices.service import suggest, whatsapp_number, whatsapp_url
from app.modules.workorders.catalog import Status
from app.modules.workorders.models import WorkOrder, WorkOrderStatusHistory

T0 = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)
K = NoticeKind
S = Status


def _order(status: Status) -> WorkOrder:
    return WorkOrder(status=status.value, received_at=T0)


def _moves(*steps: tuple[Status | None, Status, int]) -> list[WorkOrderStatusHistory]:
    """(from, to, day offset from T0)."""
    return [
        WorkOrderStatusHistory(
            from_status=source.value if source else None,
            to_status=target.value,
            changed_at=T0 + timedelta(days=day),
        )
        for source, target, day in steps
    ]


def _notice(kind: NoticeKind, day: float) -> WorkOrderNotice:
    return WorkOrderNotice(kind=kind.value, prepared_at=T0 + timedelta(days=day))


# --- Templates ---------------------------------------------------------------------------


def test_default_templates_are_valid_and_complete() -> None:
    assert set(DEFAULT_TEMPLATES) == set(NoticeKind)
    for body in DEFAULT_TEMPLATES.values():
        assert template_errors(body) == []
    values = dict.fromkeys(PLACEHOLDERS, "x")
    for body in DEFAULT_TEMPLATES.values():
        assert "{" not in render(body, values)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("Hola {nombre}", "{nombre} no existe"),
        ("Hola {cliente.__class__}", "no existe"),
        ("Hola {0}", "{0} no existe"),
        ("Hola {}", "{} no existe"),
        ("Total {total:>10}", "sin formato adicional"),
        ("Total {total!r}", "sin formato adicional"),
        ("Hola {cliente", "llaves"),
        ("Hola cliente}", "llaves"),
    ],
)
def test_template_errors(body: str, message: str) -> None:
    errors = template_errors(body)
    assert errors
    assert message in " ".join(errors)


def test_render_never_formats_values_again() -> None:
    values = dict.fromkeys(PLACEHOLDERS, "")
    values["cliente"] = "{orden} {0}"
    assert render("Hola {cliente}", values) == "Hola {orden} {0}"
    assert render("Llaves literales {{así}}", values) == "Llaves literales {así}"


# --- WhatsApp link -------------------------------------------------------------------------


def test_whatsapp_number_rules() -> None:
    assert whatsapp_number("+573505985604") == ("573505985604", None)
    assert whatsapp_number("+14155550100") == ("14155550100", None)
    digits, reason = whatsapp_number("+576015551234")
    assert digits is None
    assert reason is not None
    assert "fijo" in reason
    assert whatsapp_number(None)[0] is None


def test_whatsapp_url_encodes_the_whole_message() -> None:
    body = "Hola Ána & José: ¿autoriza? Total $ 1.200.000\nResponda SÍ #1 +57"
    url = whatsapp_url("573000000001", body)
    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "wa.me"
    assert parsed.path == "/573000000001"
    assert parse_qs(parsed.query)["text"] == [body]
    assert " " not in url
    assert "\n" not in url


# --- Suggested notice ----------------------------------------------------------------------


def test_reception_and_delivery_are_suggested_but_never_pending() -> None:
    received = suggest(_order(S.RECIBIDO), _moves((None, S.RECIBIDO, 0)), [], T0)
    assert (received.kind, received.pending) == (K.RECEIVED, False)
    delivered = suggest(_order(S.ENTREGADO), _moves((S.LISTO_ENTREGA, S.ENTREGADO, 3)), [], T0)
    assert (delivered.kind, delivered.pending) == (K.DELIVERED, False)
    working = suggest(_order(S.EN_REPARACION), [], [], T0)
    assert (working.kind, working.pending) == (K.FREE, False)


def test_quote_is_pending_until_a_notice_after_sending_it() -> None:
    history = _moves((S.COTIZACION, S.PENDIENTE_AUTORIZACION, 2))
    order = _order(S.PENDIENTE_AUTORIZACION)
    first = suggest(order, history, [], T0 + timedelta(days=2))
    assert (first.kind, first.pending, first.since) == (K.QUOTE_READY, True, T0 + timedelta(days=2))
    # A quote notice prepared before the quote was sent does not count.
    assert suggest(order, history, [_notice(K.QUOTE_READY, 1)], T0).pending
    assert not suggest(order, history, [_notice(K.QUOTE_READY, 2.1)], T0).pending


def test_repaired_device_ready_then_reminder_every_seven_days() -> None:
    history = _moves((S.CONTROL_CALIDAD, S.LISTO_ENTREGA, 5))
    order = _order(S.LISTO_ENTREGA)
    now = T0 + timedelta(days=5, hours=1)
    assert suggest(order, history, [], now).kind is K.READY
    assert suggest(order, history, [], now).pending

    told = [_notice(K.READY, 5.1)]
    calm = suggest(order, history, told, T0 + timedelta(days=12))
    assert (calm.kind, calm.pending) == (K.READY, False)
    due = suggest(order, history, told, T0 + timedelta(days=12, hours=3))
    assert (due.kind, due.pending) == (K.REMINDER, True)
    assert due.since == T0 + timedelta(days=12.1)

    reminded = [*told, _notice(K.REMINDER, 12.2)]
    assert not suggest(order, history, reminded, T0 + timedelta(days=19)).pending
    assert suggest(order, history, reminded, T0 + timedelta(days=19.3)).kind is K.REMINDER


@pytest.mark.parametrize("stop", [S.CANCELADO, S.NO_REPARABLE, S.COTIZACION_RECHAZADA])
def test_not_repaired_counts_notices_from_the_stop_on(stop: Status) -> None:
    history = _moves((S.DIAGNOSTICO, stop, 3), (stop, S.LISTO_ENTREGA, 4))
    order = _order(S.LISTO_ENTREGA)
    pending = suggest(order, history, [], T0 + timedelta(days=4))
    assert (pending.kind, pending.pending) == (K.NOT_REPAIRED, True)
    # Told while cancelled: still counts once the device is ready to pick up.
    told = [_notice(K.NOT_REPAIRED, 3.5)]
    assert not suggest(order, history, told, T0 + timedelta(days=5)).pending
    in_stop = suggest(_order(stop), history[:1], [], T0 + timedelta(days=3))
    assert (in_stop.kind, in_stop.pending) == (K.NOT_REPAIRED, True)
