"""Восстановление пароля (3 шага, аналогично регистрации)."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.accounts.validators import normalize_phone
from apps.common.exceptions import QadamAPIError
from services.sms import get_sms_provider

from .otp import OTPPurpose, generate_and_store_otp, verify_otp
from .verification_token import decode_verification_token, issue_verification_token

OTP_MESSAGE_TEMPLATE = _("Qadam: код для восстановления пароля — {code}")


def request_password_reset(*, raw_phone: str) -> int:
    phone = normalize_phone(raw_phone)
    # Намеренно НЕ раскрываем существование пользователя:
    # код «отправляется» в любом случае, чтобы не помогать атакующим.
    if User.objects.filter(phone=phone).exists():
        code = generate_and_store_otp(purpose=OTPPurpose.PASSWORD_RESET, phone=phone)
        get_sms_provider().send(
            phone=phone,
            message=str(OTP_MESSAGE_TEMPLATE).format(code=code),
        )
    return settings.QADAM["OTP_TTL_SECONDS"]


def verify_password_reset_code(*, raw_phone: str, code: str) -> str:
    phone = normalize_phone(raw_phone)
    verify_otp(purpose=OTPPurpose.PASSWORD_RESET, phone=phone, code=code)
    return issue_verification_token(phone=phone, purpose=OTPPurpose.PASSWORD_RESET.value)


def confirm_password_reset(*, reset_token: str, new_password: str) -> User:
    phone = decode_verification_token(
        reset_token, expected_purpose=OTPPurpose.PASSWORD_RESET.value
    )
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist as exc:
        raise QadamAPIError(
            message="Пользователь не найден.", code="USER_NOT_FOUND"
        ) from exc

    validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    return user
