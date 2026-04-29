"""API endpoints для /api/v1/profile/."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudent
from apps.common.exceptions import QadamAPIError

from .serializers import (
    CuratorContactSerializer,
    DashboardSerializer,
    StudentProfileReadSerializer,
    StudentProfileUpdateSerializer,
)


def _get_profile(request):
    if not request.user.is_student:
        raise QadamAPIError(
            message="Профиль доступен только пользователям с ролью ученика.",
            code="NOT_A_STUDENT",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    try:
        return request.user.student_profile
    except Exception as exc:
        raise QadamAPIError(
            message="Профиль ученика не найден.",
            code="PROFILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        ) from exc


class ProfileView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    @extend_schema(
        responses={200: StudentProfileReadSerializer},
        operation_id="profile_get",
    )
    def get(self, request: Request) -> Response:
        return Response(StudentProfileReadSerializer(_get_profile(request)).data)

    @extend_schema(
        request=StudentProfileUpdateSerializer,
        responses={200: StudentProfileReadSerializer},
        operation_id="profile_update",
    )
    def patch(self, request: Request) -> Response:
        profile = _get_profile(request)
        s = StudentProfileUpdateSerializer(profile, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(StudentProfileReadSerializer(profile).data)


class DashboardView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    @extend_schema(
        responses={200: DashboardSerializer},
        operation_id="profile_dashboard",
        description=(
            "Агрегированный дашборд ученика. На текущем этапе возвращает "
            "пустую структуру; будет наполняться по мере реализации модулей "
            "learning, testing, gamification, payments."
        ),
    )
    def get(self, request: Request) -> Response:
        from apps.learning.selectors import dashboard_learning_data
        from apps.payments.services import get_active_subscription

        profile = _get_profile(request)
        learning = dashboard_learning_data(request.user)
        sub = get_active_subscription(request.user)

        if sub is not None:
            subscription_payload = {
                "active": True,
                "tariff": {
                    "id": sub.tariff_id,
                    "name": sub.tariff.name,
                    "price": str(sub.tariff.price),
                },
                "subjects": list(sub.tariff.subjects.values_list("id", flat=True)),
                "expires_at": sub.expires_at,
            }
        else:
            subscription_payload = {
                "active": False,
                "tariff": None,
                "subjects": [],
                "expires_at": None,
            }

        return Response(
            {
                "progress": learning["progress"],
                "stars": learning["stars"],
                "subscription": subscription_payload,
                # Заглушки до недели 5+
                "results": {
                    "tests_total": 0,
                    "tests": [],
                    "average_score": None,
                    "max_score": None,
                },
                "analytics": {
                    "weak_topics": [],
                    "frequent_errors": [],
                    "recommendations": [],
                },
                "league": {"current": "bronze", "stars_total": learning["stars"]["total"]},
                "profile_summary": {
                    "name": profile.name,
                    "grade": profile.grade,
                    "language": profile.learning_language,
                    "target_score": profile.target_score,
                },
            }
        )


class CuratorView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    @extend_schema(
        responses={200: CuratorContactSerializer},
        operation_id="profile_curator",
    )
    def get(self, request: Request) -> Response:
        profile = _get_profile(request)
        curator = profile.assigned_curator
        if curator is None:
            return Response(
                {
                    "id": None,
                    "name": "",
                    "phone": "",
                    "whatsapp": "",
                }
            )
        return Response(
            {
                "id": curator.id,
                "name": curator.phone,  # имя куратора храним позже, пока phone
                "phone": curator.phone,
                "whatsapp": curator.phone,
            }
        )
