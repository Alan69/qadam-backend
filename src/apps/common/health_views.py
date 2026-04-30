"""Health-check view that pings DB and Redis."""

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: list = []
    throttle_classes: list = []

    @extend_schema(
        operation_id="health_check",
        description="Liveness/readiness probe: проверяет соединение с БД и Redis.",
    )
    def get(self, request) -> Response:
        db_ok = _check_db()
        redis_ok = _check_redis()
        ok = db_ok and redis_ok
        return Response(
            {
                "status": "ok" if ok else "degraded",
                "db": db_ok,
                "redis": redis_ok,
            },
            status=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _check_db() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        cache.set("health:ping", "pong", timeout=5)
        return cache.get("health:ping") == "pong"
    except Exception:
        return False
