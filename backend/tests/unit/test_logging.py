import json
import logging

from app.core.logging import JsonFormatter


def test_json_formatter_includes_extras() -> None:
    record = logging.LogRecord("erms.test", logging.INFO, __file__, 1, "hola %s", ("mundo",), None)
    record.order_number = "ER-2026-000001"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "hola mundo"
    assert payload["context"] == {"order_number": "ER-2026-000001"}
    assert payload["timestamp"].endswith("+00:00")
