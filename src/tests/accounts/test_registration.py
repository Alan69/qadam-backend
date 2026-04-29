"""End-to-end тесты регистрации (3 шага)."""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services.otp import OTPPurpose


@pytest.mark.django_db
class TestRegistrationFlow:
    PHONE = "+77001234567"

    def test_full_happy_path(self, api_client: APIClient, curator: User):
        # Шаг 1
        r1 = api_client.post("/api/v1/auth/register/init/", {"phone": self.PHONE}, format="json")
        assert r1.status_code == 200, r1.data
        assert r1.data["expires_in"] > 0

        # Извлекаем код из Redis (в dev провайдер console только логирует)
        code = cache.get(f"otp:{OTPPurpose.REGISTER}:{self.PHONE}")
        assert code is not None

        # Шаг 2
        r2 = api_client.post(
            "/api/v1/auth/register/verify/",
            {"phone": self.PHONE, "code": code},
            format="json",
        )
        assert r2.status_code == 200, r2.data
        verification_token = r2.data["verification_token"]

        # Шаг 3
        r3 = api_client.post(
            "/api/v1/auth/register/complete/",
            {
                "verification_token": verification_token,
                "password": "StrongPass123!",
                "name": "Тестовый Ученик",
                "parent_phone": "+77001111111",
                "grade": 11,
                "learning_language": "ru",
            },
            format="json",
        )
        assert r3.status_code == 201, r3.data
        assert "access" in r3.data and "refresh" in r3.data
        assert r3.data["user"]["phone"] == self.PHONE
        assert r3.data["user"]["role"] == User.Role.STUDENT

        user = User.objects.get(phone=self.PHONE)
        # Куратор был назначен (round-robin)
        assert user.student_profile.assigned_curator_id == curator.id

    def test_init_with_existing_phone_returns_error(self, api_client: APIClient):
        User.objects.create_user(phone=self.PHONE, password="x")
        r = api_client.post("/api/v1/auth/register/init/", {"phone": self.PHONE}, format="json")
        assert r.status_code == 400
        assert r.data["error"]["code"] == "PHONE_ALREADY_REGISTERED"

    def test_verify_with_wrong_code_returns_error(self, api_client: APIClient):
        api_client.post("/api/v1/auth/register/init/", {"phone": self.PHONE}, format="json")
        r = api_client.post(
            "/api/v1/auth/register/verify/",
            {"phone": self.PHONE, "code": "000000"},
            format="json",
        )
        assert r.status_code == 400
        assert r.data["error"]["code"] == "INVALID_OTP_CODE"

    def test_complete_with_invalid_token_returns_error(self, api_client: APIClient):
        r = api_client.post(
            "/api/v1/auth/register/complete/",
            {
                "verification_token": "garbage.token.value",
                "password": "StrongPass123!",
                "name": "X",
                "parent_phone": "+77001111111",
                "grade": 11,
                "learning_language": "ru",
            },
            format="json",
        )
        assert r.status_code == 400
        assert r.data["error"]["code"] == "INVALID_VERIFICATION_TOKEN"
