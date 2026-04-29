"""Тесты OTP-сервиса (генерация, проверка, rate limits)."""
import pytest

from apps.accounts.services.otp import (
    OTPPurpose,
    generate_and_store_otp,
    verify_otp,
)
from apps.common.exceptions import InvalidOTPCodeError, OTPRateLimitError


@pytest.mark.django_db
class TestOTP:
    PHONE = "+77001234567"

    def test_generate_and_verify_success(self):
        code = generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE)
        assert len(code) == 6 and code.isdigit()
        verify_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE, code=code)

    def test_verify_with_wrong_code_raises(self):
        generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE)
        with pytest.raises(InvalidOTPCodeError):
            verify_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE, code="000000")

    def test_request_rate_limit(self, settings):
        settings.QADAM["OTP_REQUEST_RATE_LIMIT"] = 2
        generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE)
        generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE)
        with pytest.raises(OTPRateLimitError):
            generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE)

    def test_verify_attempts_lockout(self, settings):
        settings.QADAM["OTP_VERIFY_MAX_ATTEMPTS"] = 3
        generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE)
        for _ in range(3):
            with pytest.raises(InvalidOTPCodeError):
                verify_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE, code="000000")
        with pytest.raises(OTPRateLimitError):
            verify_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE, code="000000")

    def test_otp_one_time_use(self):
        code = generate_and_store_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE)
        verify_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE, code=code)
        with pytest.raises(InvalidOTPCodeError):
            verify_otp(purpose=OTPPurpose.REGISTER, phone=self.PHONE, code=code)
