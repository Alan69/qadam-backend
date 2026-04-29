"""Health-check endpoints (no auth required)."""
from django.urls import path

from .health_views import HealthView

urlpatterns = [
    path("", HealthView.as_view(), name="health"),
]
