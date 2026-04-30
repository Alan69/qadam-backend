"""Скелет тарифов / подписок / платежей. ТЗ §3.

Constraint «у пользователя не более одной активной подписки» обеспечивается
partial unique index на уровне БД (см. Meta.constraints).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class Tariff(TimestampedModel):
    name = models.CharField("название", max_length=128)
    price = models.DecimalField("цена (KZT)", max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField("срок (дней)")
    has_learning = models.BooleanField("доступ к обучению", default=True)
    has_testing = models.BooleanField("доступ к ЕНТ-тестам", default=True)
    has_ai_tutor = models.BooleanField("доступ к AI Tutor", default=False)
    subjects = models.ManyToManyField("learning.Subject", related_name="tariffs", blank=True)
    is_active = models.BooleanField("активен", default=True)

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ("price",)

    def __str__(self) -> str:
        return f"{self.name} — {self.price} KZT / {self.duration_days} дн."


class Subscription(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        EXPIRED = "expired", "Истекла"
        CANCELLED = "cancelled", "Отменена"

    class Source(models.TextChoices):
        SELF_PAYMENT = "self_payment", "Самостоятельная оплата"
        VIA_CURATOR = "via_curator", "Через куратора"
        VIA_MANAGER = "via_manager", "Через менеджера"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    source = models.CharField(
        "источник", max_length=16, choices=Source.choices, default=Source.SELF_PAYMENT
    )
    started_at = models.DateTimeField("начало", auto_now_add=True)
    expires_at = models.DateTimeField("истекает")

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ("-started_at",)
        constraints = [
            # ТЗ §3.13 — у одного пользователя не более одной активной подписки
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="unique_active_subscription_per_user",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]


class Payment(TimestampedModel):
    class Method(models.TextChoices):
        CARD = "card", "Карта"
        KASPI_QR = "kaspi_qr", "Kaspi QR"
        HALYK_QR = "halyk_qr", "Halyk QR"
        MANUAL = "manual", "Вручную"

    class Status(models.TextChoices):
        PENDING = "pending", "В обработке"
        SUCCESS = "success", "Успех"
        FAILED = "failed", "Не прошёл"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    amount = models.DecimalField("сумма (KZT)", max_digits=10, decimal_places=2)
    method = models.CharField("способ", max_length=16, choices=Method.choices)
    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.PENDING
    )
    external_id = models.CharField("id у провайдера", max_length=128, blank=True)
    paid_at = models.DateTimeField("дата оплаты", null=True, blank=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]
