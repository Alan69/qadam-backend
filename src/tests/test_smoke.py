"""Smoke-тесты: миграции применяются, admin регистрирует все модели."""
import pytest
from django.apps import apps
from django.contrib import admin
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_all_local_apps_have_admin():
    """Каждая модель из apps.* должна быть видна в Django Admin."""
    local_apps = [a for a in apps.get_app_configs() if a.name.startswith("apps.")]
    missing = []
    for app_config in local_apps:
        for model in app_config.get_models():
            # Логи входов / абстрактные модели — кроме них всё должно быть зарегистрировано
            if model._meta.abstract:
                continue
            if not admin.site.is_registered(model):
                missing.append(f"{app_config.label}.{model.__name__}")
    assert not missing, f"Не зарегистрированы в admin: {missing}"


@pytest.mark.django_db
def test_admin_index_page_loads(super_admin):
    """Базовая проверка что admin загружается без ошибок."""
    client = Client()
    client.force_login(super_admin)
    response = client.get(reverse("admin:index"))
    assert response.status_code == 200


def test_health_endpoint_returns_ok():
    """Health-check endpoint доступен без авторизации."""
    client = Client()
    response = client.get("/api/v1/health/")
    assert response.status_code in (200, 503)
    assert "status" in response.json()


@pytest.mark.django_db
def test_swagger_schema_renders():
    """OpenAPI схема собирается без ошибок (нет битых serializer'ов / view'шек)."""
    client = Client()
    response = client.get("/api/schema/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")
