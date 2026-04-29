"""Abstract SMS / WhatsApp provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class SmsSendResult:
    """Структурированный ответ от отправки сообщения.

    `provider_message_id` — id сообщения у провайдера (для трейсинга).
    """

    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class SmsProvider(ABC):
    """Базовый класс для всех SMS/WhatsApp-отправителей."""

    name: str = "abstract"

    @abstractmethod
    def send(self, *, phone: str, message: str) -> SmsSendResult:
        raise NotImplementedError
