"""Unified API error format and exception handler.

Все ошибки приводятся к виду:
    {"error": {"code": "...", "message": "...", "details": {...}}}
"""

from __future__ import annotations

from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class QadamAPIError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Запрос некорректен."
    default_code = "BAD_REQUEST"

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_detail
        self.code = code or self.default_code
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=self.message, code=self.code)


class InvalidOTPCodeError(QadamAPIError):
    default_detail = "Код подтверждения неверный или истёк."
    default_code = "INVALID_OTP_CODE"


class OTPRateLimitError(QadamAPIError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Слишком много запросов. Попробуйте позже."
    default_code = "OTP_RATE_LIMIT"


class InvalidVerificationTokenError(QadamAPIError):
    default_detail = "Токен верификации недействителен или истёк."
    default_code = "INVALID_VERIFICATION_TOKEN"


class InvalidCredentialsError(QadamAPIError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Неверный телефон или пароль."
    default_code = "INVALID_CREDENTIALS"


class AccountInactiveError(QadamAPIError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Аккаунт деактивирован."
    default_code = "ACCOUNT_INACTIVE"


class LoginRateLimitError(QadamAPIError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Слишком много неуспешных попыток. Попробуйте позже."
    default_code = "LOGIN_RATE_LIMIT"


def qadam_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Обёртка над DRF-обработчиком: формирует единый JSON-формат ошибок."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, QadamAPIError):
        payload = {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
    elif isinstance(exc, exceptions.ValidationError):
        payload = {
            "code": "VALIDATION_ERROR",
            "message": "Проверьте корректность переданных данных.",
            "details": _normalize_validation_errors(response.data),
        }
    else:
        payload = {
            "code": getattr(exc, "default_code", "ERROR"),
            "message": _extract_message(response.data),
            "details": {},
        }

    response.data = {"error": payload}
    return response


def _normalize_validation_errors(data: Any) -> dict[str, Any]:
    """DRF возвращает разнородные структуры — приводим к dict[field -> list[str]]."""
    if isinstance(data, dict):
        return {k: _coerce_to_list(v) for k, v in data.items()}
    if isinstance(data, list):
        return {"non_field_errors": _coerce_to_list(data)}
    return {"non_field_errors": [str(data)]}


def _coerce_to_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _extract_message(data: Any) -> str:
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    if isinstance(data, str):
        return data
    return "Произошла ошибка."
