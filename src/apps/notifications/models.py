"""Скелет уведомлений. ТЗ §5."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class NotificationTemplate(TimestampedModel):
    code = models.SlugField("код", max_length=64, unique=True)
    title = models.CharField("заголовок", max_length=256)
    body = models.TextField("текст")
    channels = models.JSONField(
        "каналы",
        default=list,
        help_text='список каналов: ["in_app", "whatsapp"]',
    )
    is_active = models.BooleanField("активен", default=True)

    class Meta:
        verbose_name = "Шаблон уведомления"
        verbose_name_plural = "Шаблоны уведомлений"

    def __str__(self) -> str:
        return self.code


class Notification(TimestampedModel):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "В приложении"
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SENT = "sent", "Отправлено"
        DELIVERED = "delivered", "Доставлено"
        READ = "read", "Прочитано"
        FAILED = "failed", "Ошибка"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    channel = models.CharField("канал", max_length=16, choices=Channel.choices)
    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.PENDING
    )
    payload = models.JSONField("контекст", default=dict, blank=True)
    sent_at = models.DateTimeField("отправлено", null=True, blank=True)
    read_at = models.DateTimeField("прочитано", null=True, blank=True)
    error = models.TextField("ошибка", blank=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]
