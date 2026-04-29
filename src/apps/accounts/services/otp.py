"""OTP-сервис: генерация, хранение в Redis, проверка с rate-limit."""
from __future__ import annotations

import secrets
from enum import StrEnum

from django.conf import settings
from django.core.cache import cache

from apps.common.exceptions import InvalidOTPCodeError, OTPRateLimitError


class OTPPurpose(StrEnum):
    REGISTER = "reg"
    PASSWORD_RESET = "pwd"


def _otp_key(purpose: OTPPurpose, phone: str) -> str:
    return f"otp:{purpose}:{phone}"


def _request_counter_key(purpose: OTPPurpose, phone: str) -> str:
    return f"otp:{purpose}:{phone}:reqs"


def _verify_attempts_key(purpose: OTPPurpose, phone: str) -> str:
    return f"otp:{purpose}:{phone}:attempts"


def generate_and_store_otp(*, purpose: OTPPurpose, phone: str) -> str:
    """Сгенерировать код, проверить лимит запросов, сохранить в Redis.

    Бросает OTPRateLimitError если превышен лимит запросов.
    Возвращает сгенерированный код (для передачи провайдеру).
    """
    cfg = settings.QADAM
    _check_request_rate_limit(purpose, phone)

    length = cfg["OTP_LENGTH"]
    code = "".join(str(secrets.randbelow(10)) for _ in range(length))

    cache.set(_otp_key(purpose, phone), code, timeout=cfg["OTP_TTL_SECONDS"])
    cache.delete(_verify_attempts_key(purpose, phone))
    return code


def verify_otp(*, purpose: OTPPurpose, phone: str, code: str) -> None:
    """Проверить код. Бросает InvalidOTPCodeError или OTPRateLimitError.

    При успехе удаляет код из Redis (одноразовость).
    """
    cfg = settings.QADAM
    attempts_key = _verify_attempts_key(purpose, phone)

    attempts = cache.get(attempts_key, 0)
    if attempts >= cfg["OTP_VERIFY_MAX_ATTEMPTS"]:
        raise OTPRateLimitError(
            message="Превышено количество попыток. Запросите новый код.",
            code="OTP_VERIFY_LOCKED",
        )

    stored = cache.get(_otp_key(purpose, phone))
    if stored is None or stored != code:
        cache.set(attempts_key, attempts + 1, timeout=cfg["OTP_VERIFY_LOCKOUT_SECONDS"])
        raise InvalidOTPCodeError()

    cache.delete(_otp_key(purpose, phone))
    cache.delete(attempts_key)


def _check_request_rate_limit(purpose: OTPPurpose, phone: str) -> None:
    cfg = settings.QADAM
    key = _request_counter_key(purpose, phone)
    current = cache.get(key, 0)
    if current >= cfg["OTP_REQUEST_RATE_LIMIT"]:
        raise OTPRateLimitError()
    cache.set(key, current + 1, timeout=cfg["OTP_REQUEST_RATE_WINDOW_SECONDS"])
