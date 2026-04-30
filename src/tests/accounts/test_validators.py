"""Тесты на нормализацию телефонов."""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import normalize_phone


class TestPhoneNormalization:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("+77001234567", "+77001234567"),
            ("87001234567", "+77001234567"),  # leading 8 → +7
            ("7 700 123 45 67", "+77001234567"),  # пробелы
            ("+7-700-123-45-67", "+77001234567"),  # дефисы
        ],
    )
    def test_valid_phones_normalized_to_e164(self, raw: str, expected: str):
        assert normalize_phone(raw) == expected

    @pytest.mark.parametrize("raw", ["", "не-телефон", "12345"])
    def test_invalid_phone_raises(self, raw: str):
        with pytest.raises(ValidationError):
            normalize_phone(raw)
