"""Factory: возвращает SmsProvider на основе настройки QADAM["SMS_PROVIDER"]."""

from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import SmsProvider
from .console import ConsoleSmsProvider
from .whatsapp import WhatsAppSmsProvider

_PROVIDERS: dict[str, type[SmsProvider]] = {
    "console": ConsoleSmsProvider,
    "whatsapp": WhatsAppSmsProvider,
}


@lru_cache(maxsize=1)
def get_sms_provider() -> SmsProvider:
    name = settings.QADAM["SMS_PROVIDER"].lower()
    try:
        return _PROVIDERS[name]()
    except KeyError as exc:
        raise ImproperlyConfigured(
            f"Unknown SMS_PROVIDER={name!r}. Allowed: {sorted(_PROVIDERS)}"
        ) from exc
