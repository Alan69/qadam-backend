"""Phone number validation in E.164 format using `phonenumbers` library."""

import phonenumbers
from django.core.exceptions import ValidationError


def normalize_phone(value: str) -> str:
    """Возвращает phone в формате E.164 (`+77001234567`).

    Бросает ValidationError если номер не валидный.
    """
    if not value:
        raise ValidationError("Номер телефона обязателен.")
    try:
        parsed = phonenumbers.parse(value, "KZ")
    except phonenumbers.NumberParseException as exc:
        raise ValidationError("Некорректный формат номера телефона.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError("Номер телефона невалиден.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def validate_phone(value: str) -> None:
    """Django field validator wrapper."""
    normalize_phone(value)
