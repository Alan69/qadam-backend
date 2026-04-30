"""Dev SMS provider — пишет сообщения в логи."""

from __future__ import annotations

import logging
import secrets

from .base import SmsProvider, SmsSendResult

logger = logging.getLogger("qadam.sms")


class ConsoleSmsProvider(SmsProvider):
    name = "console"

    def send(self, *, phone: str, message: str) -> SmsSendResult:
        message_id = secrets.token_hex(8)
        logger.info(
            "[sms:console] → %s: %s (id=%s)",
            phone,
            message,
            message_id,
        )
        return SmsSendResult(success=True, provider_message_id=message_id)
