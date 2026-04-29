"""Admin endpoints under /api/v1/admin/users/ — только для SUPER_ADMIN."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.exceptions import QadamAPIError

from .models import User
from .permissions import IsSuperAdmin
from .serializers import UserSerializer


class AdminUserListSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ("id", "phone", "role", "is_active", "is_staff", "created_at")


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "phone", "role", "is_active", "password", "created_at")
        read_only_fields = ("id", "created_at")

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "role", "is_active")
        read_only_fields = ("id",)


class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.all().order_by("-created_at")
    permission_classes = (IsAuthenticated, IsSuperAdmin)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("phone",)
    ordering_fields = ("created_at", "phone", "role")

    def get_serializer_class(self):
        if self.action == "create":
            return AdminUserCreateSerializer
        if self.action in ("update", "partial_update"):
            return AdminUserUpdateSerializer
        return AdminUserListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))
        return qs

    @extend_schema(responses={204: None}, operation_id="admin_users_block")
    @action(detail=True, methods=["post"])
    def block(self, request: Request, pk: str | None = None) -> Response:
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={204: None}, operation_id="admin_users_unblock")
    @action(detail=True, methods=["post"])
    def unblock(self, request: Request, pk: str | None = None) -> Response:
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        responses={200: UserSerializer},
        operation_id="admin_users_assign_curator",
        description="Назначить или сменить куратора у студента.",
    )
    @action(detail=True, methods=["post"], url_path="assign-curator")
    def assign_curator(self, request: Request, pk: str | None = None) -> Response:
        user = self.get_object()
        if not user.is_student:
            raise QadamAPIError(
                message="Куратор назначается только ученикам.",
                code="ASSIGN_CURATOR_NOT_STUDENT",
            )
        curator_id = request.data.get("curator_id")
        if not curator_id:
            raise QadamAPIError(
                message="Поле curator_id обязательно.",
                code="CURATOR_ID_REQUIRED",
            )
        try:
            curator = User.objects.get(pk=curator_id, role=User.Role.CURATOR)
        except User.DoesNotExist as exc:
            raise QadamAPIError(
                message="Куратор не найден.", code="CURATOR_NOT_FOUND"
            ) from exc

        from apps.profiles.services import assign_curator  # late import

        assign_curator(student=user, curator=curator)
        return Response(UserSerializer(user).data)
