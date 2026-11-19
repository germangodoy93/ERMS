"""Outgoing email through any SMTP server (Mailpit in development).

The `Mailer` protocol lets tests capture messages without a server.
"""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str


class Mailer(Protocol):
    def send(self, message: OutgoingEmail) -> None: ...


class SmtpMailer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, message: OutgoingEmail) -> None:
        settings = self._settings
        if not settings.smtp_host:
            # No SMTP configured: never log the body (it may contain a reset link).
            logger.error(
                "Email not sent: SMTP_HOST is not configured",
                extra={"subject": message.subject},
            )
            return

        email = EmailMessage()
        email["From"] = settings.smtp_from
        email["To"] = message.to
        email["Subject"] = message.subject
        email.set_content(message.text)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_username and settings.smtp_password:
                    smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
                smtp.send_message(email)
        except (smtplib.SMTPException, OSError):
            logger.exception("Email delivery failed", extra={"subject": message.subject})
            return
        logger.info("Email sent", extra={"subject": message.subject})


@lru_cache
def get_mailer() -> Mailer:
    return SmtpMailer(get_settings())
