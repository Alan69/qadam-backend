"""Тесты Profile API."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.profiles.services import create_student_profile


@pytest.mark.django_db
class TestProfileAPI:
    @pytest.fixture
    def student_with_profile(self, db) -> User:
        user = User.objects.create_user(phone="+77001234567", password="x")
        create_student_profile(
            user=user,
            name="Тестовый Ученик",
            parent_phone="+77001111111",
            grade=11,
            learning_language="ru",
        )
        return user

    def test_get_profile_returns_student_data(
        self, api_client: APIClient, student_with_profile: User
    ):
        api_client.force_authenticate(user=student_with_profile)
        r = api_client.get("/api/v1/profile/")
        assert r.status_code == 200
        assert r.data["name"] == "Тестовый Ученик"
        assert r.data["grade"] == 11
        assert r.data["phone"] == "+77001234567"

    def test_patch_profile_updates_allowed_fields(
        self, api_client: APIClient, student_with_profile: User
    ):
        api_client.force_authenticate(user=student_with_profile)
        r = api_client.patch(
            "/api/v1/profile/",
            {"name": "Новое Имя", "target_score": 130},
            format="json",
        )
        assert r.status_code == 200, r.data
        assert r.data["name"] == "Новое Имя"
        assert r.data["target_score"] == 130

    def test_patch_cannot_change_parent_phone(
        self, api_client: APIClient, student_with_profile: User
    ):
        """ТЗ §2.4: parent_phone редактируется только админом."""
        api_client.force_authenticate(user=student_with_profile)
        old_parent = student_with_profile.student_profile.parent_phone
        api_client.patch(
            "/api/v1/profile/",
            {"parent_phone": "+77002222222"},
            format="json",
        )
        student_with_profile.student_profile.refresh_from_db()
        assert student_with_profile.student_profile.parent_phone == old_parent

    def test_dashboard_returns_aggregated_structure(
        self, api_client: APIClient, student_with_profile: User
    ):
        api_client.force_authenticate(user=student_with_profile)
        r = api_client.get("/api/v1/profile/dashboard/")
        assert r.status_code == 200
        for key in ("progress", "results", "analytics", "league", "stars", "subscription"):
            assert key in r.data

    def test_curator_endpoint_returns_empty_for_unassigned(
        self, api_client: APIClient, student_with_profile: User
    ):
        api_client.force_authenticate(user=student_with_profile)
        r = api_client.get("/api/v1/profile/curator/")
        assert r.status_code == 200
        assert r.data["id"] is None

    def test_non_student_denied(self, api_client: APIClient, curator: User):
        api_client.force_authenticate(user=curator)
        r = api_client.get("/api/v1/profile/")
        assert r.status_code == 403
