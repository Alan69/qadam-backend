"""Pytest fixtures."""

from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture(autouse=True)
def clear_cache():
    """Между тестами Redis-кэш очищаем — иначе rate limits и OTP протекают."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def student(db) -> User:
    return User.objects.create_user(phone="+77001234567", password="StrongPass123!")


@pytest.fixture
def curator(db) -> User:
    return User.objects.create_user(
        phone="+77002222222", password="StrongPass123!", role=User.Role.CURATOR
    )


@pytest.fixture
def super_admin(db) -> User:
    return User.objects.create_superuser(phone="+77009999999", password="StrongPass123!")


@pytest.fixture
def authed_client(api_client: APIClient, student: User) -> APIClient:
    api_client.force_authenticate(user=student)
    return api_client
