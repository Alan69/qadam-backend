"""Production WhatsApp provider — пока заглушка.

Готова к подключению реального API (например, 360dialog, Twilio, Wazzup24,
Meta WhatsApp Business API). Чтобы внедрить:

1. В .env: SMS_PROVIDER=whatsapp + WHATSAPP_API_URL + WHATSAPP_API_TOKEN.
2. Заменить тело `send()` на реальный HTTP-запрос (httpx / requests).
3. Не забыть подключить ретраи и таймауты.
"""
from __future__ import annotations

import logging

from django.conf import settings

from .base import SmsProvider, SmsSendResult

logger = logging.getLogger("qadam.sms")


class WhatsAppSmsProvider(SmsProvider):
    name = "whatsapp"

    def __init__(self) -> None:
        self.api_url = settings.QADAM["WHATSAPP_API_URL"]
        self.api_token = settings.QADAM["WHATSAPP_API_TOKEN"]
        self.template_name = settings.QADAM["WHATSAPP_TEMPLATE_NAME"]

    def send(self, *, phone: str, message: str) -> SmsSendResult:
        if not self.api_url or not self.api_token:
            logger.warning(
                "[sms:whatsapp] стаб: api credentials не настроены, "
                "сообщение для %s не отправлено: %s",
                phone,
                message,
            )
            return SmsSendResult(success=False, error="WhatsApp credentials not configured")

        # Реальная интеграция — замените тело метода и удалите NotImplementedError.
        raise NotImplementedError(
            "Реальная интеграция WhatsApp ещё не реализована. "
            "Подключите HTTP-клиент к {url}.".format(url=self.api_url)
        )
