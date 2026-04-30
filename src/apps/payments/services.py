"""Бизнес-операции вокруг подписок."""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User

from .models import Subscription


def get_active_subscription(user: User) -> Subscription | None:
    """Текущая активная подписка пользователя (или None).

    Активной считается подписка со `status='active'` и не истёкшим сроком.
    Constraint в БД (см. Subscription.Meta) гарантирует что таких ≤ 1.
    """
    return (
        Subscription.objects.filter(
            user=user,
            status=Subscription.Status.ACTIVE,
            expires_at__gt=timezone.now(),
        )
        .select_related("tariff")
        .prefetch_related("tariff__subjects")
        .first()
    )
