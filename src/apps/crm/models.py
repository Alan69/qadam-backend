"""Скелет CRM (для менеджера по продажам). ТЗ §12.

Сам статус клиента (NEW / IN_WORK / ...) хранится прямо в StudentProfile.sales_status.
Здесь — комментарии и история смены статусов.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class SalesNote(TimestampedModel):
    student = models.ForeignKey(
        "profiles.StudentProfile",
        on_delete=models.CASCADE,
        related_name="sales_notes",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sales_notes",
        limit_choices_to={"role__in": ["sales_manager", "super_admin"]},
    )
    text = models.TextField("заметка")

    class Meta:
        verbose_name = "Заметка менеджера"
        verbose_name_plural = "Заметки менеджера"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["student", "-created_at"])]


class StatusChangeLog(TimestampedModel):
    student = models.ForeignKey(
        "profiles.StudentProfile",
        on_delete=models.CASCADE,
        related_name="status_changes",
    )
    old_status = models.CharField("старый статус", max_length=16, blank=True)
    new_status = models.CharField("новый статус", max_length=16)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="crm_status_changes",
    )

    class Meta:
        verbose_name = "Смена статуса клиента"
        verbose_name_plural = "Смены статуса клиента"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["student", "-created_at"])]
