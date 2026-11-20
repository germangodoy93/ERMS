"""Request metadata used for auditing (who did what, from where)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from fastapi import Request

# Colombia has no daylight saving time: a fixed offset avoids depending on tzdata.
BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class RequestContext:
    ip_address: str | None = None
    user_agent: str | None = None


def get_request_context(request: Request) -> RequestContext:
    # With uvicorn --proxy-headers, request.client reflects X-Forwarded-For from trusted proxies.
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return RequestContext(
        ip_address=ip[:45] if ip else None,
        user_agent=user_agent[:255] if user_agent else None,
    )
