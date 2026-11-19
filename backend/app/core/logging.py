"""Structured logging using only the standard library.

Production emits one JSON object per line (ready for Railway log search);
development can switch to a human-readable format with LOG_JSON=false.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_RESERVED_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys() | {"message", "asctime"}
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in _RESERVED_ATTRS}
        if extras:
            payload["context"] = extras
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Uvicorn installs its own handlers; route them through ours for a single format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
