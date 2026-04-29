"""Тесты login / refresh / logout."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import LoginEvent, User


@pytest.mark.django_db
class TestLogin:
    PHONE = "+77001234567"
    PWD = "StrongPass123!"

    @pytest.fixture
    def user(self) -> User:
        return User.objects.create_user(phone=self.PHONE, password=self.PWD)

    def test_login_success_returns_tokens(self, api_client: APIClient, user: User):
        r = api_client.post(
            "/api/v1/auth/login/", {"phone": self.PHONE, "password": self.PWD}, format="json"
        )
        assert r.status_code == 200, r.data
        assert "access" in r.data and "refresh" in r.data
        assert r.data["user"]["phone"] == self.PHONE

        events = LoginEvent.objects.filter(phone=self.PHONE)
        assert events.count() == 1 and events.first().success

    def test_login_with_wrong_password_returns_401(self, api_client: APIClient, user: User):
        r = api_client.post(
            "/api/v1/auth/login/", {"phone": self.PHONE, "password": "wrong"}, format="json"
        )
        assert r.status_code == 401
        assert r.data["error"]["code"] == "INVALID_CREDENTIALS"

        event = LoginEvent.objects.filter(phone=self.PHONE).first()
        assert event is not None and not event.success
        assert event.failure_reason == "invalid_credentials"

    def test_login_inactive_user_returns_403(self, api_client: APIClient, user: User):
        user.is_active = False
        user.save()
        r = api_client.post(
            "/api/v1/auth/login/", {"phone": self.PHONE, "password": self.PWD}, format="json"
        )
        assert r.status_code == 403
        assert r.data["error"]["code"] == "ACCOUNT_INACTIVE"

    def test_login_rate_limited_after_5_failures(
        self, api_client: APIClient, user: User, settings
    ):
        settings.QADAM["LOGIN_MAX_ATTEMPTS"] = 3
        for _ in range(3):
            api_client.post(
                "/api/v1/auth/login/",
                {"phone": self.PHONE, "password": "wrong"},
                format="json",
            )
        r = api_client.post(
            "/api/v1/auth/login/", {"phone": self.PHONE, "password": self.PWD}, format="json"
        )
        assert r.status_code == 429
        assert r.data["error"]["code"] == "LOGIN_RATE_LIMIT"

    def test_logout_blacklists_refresh(self, api_client: APIClient, user: User):
        r1 = api_client.post(
            "/api/v1/auth/login/", {"phone": self.PHONE, "password": self.PWD}, format="json"
        )
        access = r1.data["access"]
        refresh = r1.data["refresh"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        r2 = api_client.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
        assert r2.status_code == 204

        # Используем тот же refresh повторно — должен быть запрещён
        r3 = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
        assert r3.status_code == 401
