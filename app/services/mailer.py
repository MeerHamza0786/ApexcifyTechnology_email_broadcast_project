from __future__ import annotations

import asyncio
from email.message import EmailMessage
from typing import Callable, Iterable, Sequence

import aiosmtplib

from app.config import DEFAULT_CONCURRENCY, SMTPSettings
from app.core.message import BroadcastMessage
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BulkMailer:
    """High-level interface for broadcasting a single message to many recipients."""

    def __init__(self, settings: SMTPSettings | None = None) -> None:
        self.settings = settings or SMTPSettings()

    def _build_message(self, message: BroadcastMessage, recipient: str) -> EmailMessage:
        email = EmailMessage()
        email["Subject"] = message.subject
        email["From"] = f"{self.settings.sender_name} <{self.settings.username}>"
        email["To"] = recipient
        email.set_content(message.body_text)
        email.add_alternative(message.body_html, subtype="html")
        return email

    async def _send_one(self, recipient: str, message: BroadcastMessage) -> None:
        email = self._build_message(message, recipient)
        try:
            await aiosmtplib.send(
                email,
                hostname=self.settings.server,
                port=self.settings.port,
                start_tls=True,
                username=self.settings.username,
                password=self.settings.password,
                timeout=30,
            )
            logger.info("Delivered to %s", recipient)
        except Exception as e:
            error_msg = str(e)
            if "535" in error_msg or "BadCredentials" in error_msg or "not accepted" in error_msg:
                logger.error(
                    "SMTP Authentication failed. Please check your SMTP credentials in .env file. "
                    "For Gmail, you need an App Password (not your regular password). "
                    "Get one at: https://myaccount.google.com/apppasswords"
                )
            raise

    async def send_async(
        self,
        recipients: Sequence[str],
        message: BroadcastMessage,
        *,
        concurrency: int | None = None,
        progress_hook: Callable[[str], None] | None = None,
    ) -> None:
        limit = max(1, concurrency or DEFAULT_CONCURRENCY)
        logger.info(
            "Starting broadcast to %d recipients (concurrency=%d)",
            len(recipients),
            limit,
        )
        semaphore = asyncio.Semaphore(limit)

        async def worker(address: str) -> None:
            async with semaphore:
                await self._send_one(address, message)
                if progress_hook:
                    progress_hook(address)

        await asyncio.gather(*(worker(address) for address in recipients))
        logger.info("Broadcast completed.")

    def send_blocking(
        self,
        recipients: Sequence[str],
        message: BroadcastMessage,
        *,
        concurrency: int | None = None,
        progress_hook: Callable[[str], None] | None = None,
    ) -> None:
        asyncio.run(
            self.send_async(
                recipients, message, concurrency=concurrency, progress_hook=progress_hook
            )
        )


def validate_recipients(addresses: Iterable[str]) -> list[str]:
    valid = []
    for address in addresses:
        trimmed = address.strip()
        if "@" in trimmed:
            valid.append(trimmed)
        else:
            logger.warning("Skipped invalid address: %s", address)
    return valid


def send_bulk_email(
    *,
    subject: str,
    message: str,
    recipients: Sequence[str],
    concurrency: int | None = None,
) -> None:
    """Compatibility helper for the Flask UI."""
    body_html = "<br/>".join(message.splitlines()) or message
    broadcast = BroadcastMessage(subject=subject, body_text=message, body_html=body_html)
    BulkMailer().send_blocking(recipients, broadcast, concurrency=concurrency)


