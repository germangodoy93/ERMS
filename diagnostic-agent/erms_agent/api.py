"""HTTPS calls to the ERMS API (standard library only)."""

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from erms_agent import VERSION

TIMEOUT_SECONDS = 30


class ApiError(Exception):
    pass


def _post(url: str, payload: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    if not url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ApiError("El servidor debe usar HTTPS.")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"erms-agent/{VERSION}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(  # noqa: S310 - scheme validated above
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(  # noqa: S310 - scheme validated above
            request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
        ) as response:
            body: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            return body
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail")
        except (ValueError, AttributeError):
            detail = None
        raise ApiError(detail or f"El servidor respondió {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"No hay conexión con el servidor: {exc.reason}") from exc


def pair(server: str, code: str) -> dict[str, Any]:
    return _post(f"{server.rstrip('/')}/api/v1/diagnostics/agent/pair", {"code": code})


def send_report(server: str, token: str, report: dict[str, Any]) -> dict[str, Any]:
    return _post(f"{server.rstrip('/')}/api/v1/diagnostics/agent/report", report, token)
