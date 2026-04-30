"""Промежуточный verification-токен между шагами OTP-verify и complete.

Используется во флоу регистрации и восстановления пароля. Подписывается тем же
SECRET_KEY, что и Django, имеет короткий TTL и собственный claim `purpose`,
чтобы токен из одного флоу нельзя было использовать в другом.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings

from apps.common.exceptions import InvalidVerificationTokenError

ALGORITHM = "HS256"


def issue_verification_token(*, phone: str, purpose: str) -> str:
    cfg = settings.QADAM
    now = datetime.now(UTC)
    payload = {
        "phone": phone,
        "purpose": purpose,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=cfg["VERIFICATION_TOKEN_LIFETIME_MINUTES"])).timestamp()
        ),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_verification_token(token: str, *, expected_purpose: str) -> str:
    """Возвращает phone из токена. Бросает InvalidVerificationTokenError при проблемах."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidVerificationTokenError(
            message="Срок действия токена верификации истёк."
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidVerificationTokenError() from exc

    if payload.get("purpose") != expected_purpose:
        raise InvalidVerificationTokenError(
            message="Токен верификации не подходит для этой операции."
        )
    phone = payload.get("phone")
    if not phone:
        raise InvalidVerificationTokenError()
    return str(phone)
