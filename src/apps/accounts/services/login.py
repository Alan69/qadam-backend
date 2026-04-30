"""Login со счётчиком неудачных попыток в Redis."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest

from apps.accounts.models import LoginEvent, User
from apps.accounts.validators import normalize_phone
from apps.common.exceptions import (
    AccountInactiveError,
    InvalidCredentialsError,
    LoginRateLimitError,
)


def _attempts_key(phone: str) -> str:
    return f"login:attempts:{phone}"


def authenticate_and_login(
    *,
    raw_phone: str,
    password: str,
    request: HttpRequest | None = None,
) -> User:
    """Проверить credentials, залогировать попытку. Бросает API-ошибки при неудаче.

    Используем `check_password` напрямую вместо `django.contrib.auth.authenticate`,
    потому что стандартный `ModelBackend` для inactive пользователей возвращает
    None — мы потеряли бы возможность отдавать 403 (ACCOUNT_INACTIVE) отдельно
    от 401 (INVALID_CREDENTIALS).
    """
    cfg = settings.QADAM
    phone = normalize_phone(raw_phone)
    key = _attempts_key(phone)

    attempts = cache.get(key, 0)
    if attempts >= cfg["LOGIN_MAX_ATTEMPTS"]:
        _record_event(phone, None, request, success=False, reason="rate_limited")
        raise LoginRateLimitError()

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        cache.set(key, attempts + 1, timeout=cfg["LOGIN_LOCKOUT_SECONDS"])
        _record_event(phone, None, request, success=False, reason="invalid_credentials")
        raise InvalidCredentialsError() from None

    if not user.check_password(password):
        cache.set(key, attempts + 1, timeout=cfg["LOGIN_LOCKOUT_SECONDS"])
        _record_event(phone, user, request, success=False, reason="invalid_credentials")
        raise InvalidCredentialsError()

    if not user.is_active:
        _record_event(phone, user, request, success=False, reason="inactive")
        raise AccountInactiveError()

    cache.delete(key)
    _record_event(phone, user, request, success=True, reason="")
    return user


def _record_event(
    phone: str,
    user: User | None,
    request: HttpRequest | None,
    *,
    success: bool,
    reason: str,
) -> None:
    LoginEvent.objects.create(
        user=user,
        phone=phone,
        ip_address=_extract_ip(request),
        user_agent=_extract_ua(request),
        success=success,
        failure_reason=reason,
    )


def _extract_ip(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _extract_ua(request: HttpRequest | None) -> str:
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:512]
