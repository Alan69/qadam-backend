"""Custom user manager — phone is the username field."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import BaseUserManager

from .validators import normalize_phone

if TYPE_CHECKING:
    from .models import User


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(
        self,
        phone: str,
        password: str | None,
        **extra_fields: Any,
    ) -> User:
        if not phone:
            raise ValueError("Номер телефона обязателен.")
        phone = normalize_phone(phone)
        user = self.model(phone=phone, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        phone: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", self.model.Role.STUDENT)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(
        self,
        phone: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.SUPER_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone, password, **extra_fields)
