"""Тесты RBAC permissions."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db
class TestAdminUsersEndpoint:
    """/api/v1/admin/users/ доступен только SUPER_ADMIN."""

    URL = "/api/v1/admin/users/"

    def test_anonymous_denied(self, api_client: APIClient):
        r = api_client.get(self.URL)
        assert r.status_code == 401

    def test_student_denied(self, api_client: APIClient, student: User):
        api_client.force_authenticate(user=student)
        r = api_client.get(self.URL)
        assert r.status_code == 403

    def test_curator_denied(self, api_client: APIClient, curator: User):
        api_client.force_authenticate(user=curator)
        r = api_client.get(self.URL)
        assert r.status_code == 403

    def test_super_admin_allowed(self, api_client: APIClient, super_admin: User):
        api_client.force_authenticate(user=super_admin)
        r = api_client.get(self.URL)
        assert r.status_code == 200

    def test_super_admin_can_block_user(
        self, api_client: APIClient, super_admin: User, student: User
    ):
        api_client.force_authenticate(user=super_admin)
        r = api_client.post(f"{self.URL}{student.id}/block/")
        assert r.status_code == 204
        student.refresh_from_db()
        assert not student.is_active
