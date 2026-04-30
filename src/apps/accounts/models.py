"""User model (custom, phone-based) and login event log."""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.common.models import TimestampedModel

from .managers import UserManager
from .validators import validate_phone


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    class Role(models.TextChoices):
        STUDENT = "student", "Ученик"
        CURATOR = "curator", "Куратор"
        CONTENT_MANAGER = "content_manager", "Контент-менеджер"
        SALES_MANAGER = "sales_manager", "Менеджер по продажам"
        SUPER_ADMIN = "super_admin", "Супер-админ"

    phone = models.CharField(
        "телефон",
        max_length=16,
        unique=True,
        validators=[validate_phone],
        help_text="В формате E.164, напр. +77001234567",
    )
    role = models.CharField(
        "роль",
        max_length=32,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )
    is_active = models.BooleanField("активен", default=True)
    is_staff = models.BooleanField("персонал", default=False)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.phone} ({self.get_role_display()})"

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_curator(self) -> bool:
        return self.role == self.Role.CURATOR

    @property
    def is_content_manager(self) -> bool:
        return self.role == self.Role.CONTENT_MANAGER

    @property
    def is_sales_manager(self) -> bool:
        return self.role == self.Role.SALES_MANAGER

    @property
    def is_super_admin(self) -> bool:
        return self.role == self.Role.SUPER_ADMIN


class LoginEvent(TimestampedModel):
    """Audit-лог попыток входа (успешных и неуспешных)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="login_events",
        null=True,
        blank=True,
        help_text="null если попытка входа была с несуществующим телефоном",
    )
    phone = models.CharField("телефон", max_length=16, db_index=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("User-Agent", max_length=512, blank=True)
    success = models.BooleanField("успех", default=False)
    failure_reason = models.CharField("причина неудачи", max_length=64, blank=True)

    class Meta:
        verbose_name = "Событие входа"
        verbose_name_plural = "События входа"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["phone", "-created_at"]),
            models.Index(fields=["success", "-created_at"]),
        ]

    def __str__(self) -> str:
        result = "OK" if self.success else f"FAIL ({self.failure_reason})"
        return f"{self.phone} — {result} @ {self.created_at:%Y-%m-%d %H:%M}"
