"""Регистрация ученика в 3 шага."""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.accounts.validators import normalize_phone
from apps.common.exceptions import QadamAPIError
from services.sms import get_sms_provider

from .otp import OTPPurpose, generate_and_store_otp, verify_otp
from .verification_token import decode_verification_token, issue_verification_token

OTP_MESSAGE_TEMPLATE = _("Ваш код подтверждения Qadam: {code}")


def request_registration_code(*, raw_phone: str) -> int:
    """Шаг 1: сгенерировать и отправить OTP на указанный телефон."""
    phone = normalize_phone(raw_phone)
    if User.objects.filter(phone=phone).exists():
        raise QadamAPIError(
            message="Пользователь с этим номером уже зарегистрирован.",
            code="PHONE_ALREADY_REGISTERED",
        )

    code = generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=phone)
    get_sms_provider().send(
        phone=phone,
        message=str(OTP_MESSAGE_TEMPLATE).format(code=code),
    )
    from django.conf import settings

    return settings.QADAM["OTP_TTL_SECONDS"]


def verify_registration_code(*, raw_phone: str, code: str) -> str:
    """Шаг 2: проверить код, выдать verification_token."""
    phone = normalize_phone(raw_phone)
    verify_otp(purpose=OTPPurpose.REGISTER, phone=phone, code=code)
    return issue_verification_token(phone=phone, purpose=OTPPurpose.REGISTER.value)


@transaction.atomic
def complete_registration(
    *,
    verification_token: str,
    password: str,
    name: str,
    parent_phone: str,
    grade: int,
    learning_language: str,
) -> User:
    """Шаг 3: создать User + StudentProfile, назначить куратора."""
    phone = decode_verification_token(
        verification_token, expected_purpose=OTPPurpose.REGISTER.value
    )
    if User.objects.filter(phone=phone).exists():
        raise QadamAPIError(
            message="Пользователь с этим номером уже зарегистрирован.",
            code="PHONE_ALREADY_REGISTERED",
        )

    parent_phone_normalized = normalize_phone(parent_phone)

    user = User.objects.create_user(phone=phone, password=password, role=User.Role.STUDENT)

    # Импорт здесь, чтобы избежать циклической зависимости accounts ↔ profiles.
    from apps.profiles.services import create_student_profile

    create_student_profile(
        user=user,
        name=name,
        parent_phone=parent_phone_normalized,
        grade=grade,
        learning_language=learning_language,
    )
    return user
