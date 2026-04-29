"""DRF permission classes for RBAC."""
from __future__ import annotations

from typing import ClassVar

from rest_framework.permissions import BasePermission

from .models import User


class _RolePermission(BasePermission):
    role: ClassVar[str] = ""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.role == self.role


class IsStudent(_RolePermission):
    role = User.Role.STUDENT


class IsCurator(_RolePermission):
    role = User.Role.CURATOR


class IsContentManager(_RolePermission):
    role = User.Role.CONTENT_MANAGER


class IsSalesManager(_RolePermission):
    role = User.Role.SALES_MANAGER


class IsSuperAdmin(_RolePermission):
    role = User.Role.SUPER_ADMIN


class HasAnyRole(BasePermission):
    """Использование: `permission_classes = [HasAnyRole.of(User.Role.STUDENT, User.Role.CURATOR)]`"""

    allowed_roles: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def of(cls, *roles: str) -> type[HasAnyRole]:
        return type(
            f"HasAnyRole({','.join(roles)})",
            (cls,),
            {"allowed_roles": tuple(roles)},
        )

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.role in self.allowed_roles
