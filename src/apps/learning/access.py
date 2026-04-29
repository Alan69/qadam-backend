"""Чистые функции доступа: paywall, sequential unlock, видимость контента.

Эти функции должны оставаться без побочных эффектов — они вызываются
многократно (в каждом сериалайзере иерархии), и тесты на них дешёвые.
"""
from __future__ import annotations

from django.db.models import Q

from apps.accounts.models import User
from apps.payments.services import get_active_subscription

from .models import Lesson, LessonProgress, Subject


# Энум причин блокировки — для UI (фронт использует чтобы показать нужный CTA).
LOCK_REASON_UNPUBLISHED = "unpublished"
LOCK_REASON_NO_SUBSCRIPTION = "no_subscription"
LOCK_REASON_PREVIOUS_NOT_COMPLETED = "previous_not_completed"


def has_subscription_access(user: User, subject: Subject) -> bool:
    """У пользователя есть активная подписка, покрывающая этот предмет?"""
    sub = get_active_subscription(user)
    if sub is None:
        return False
    if not sub.tariff.has_learning:
        return False
    return sub.tariff.subjects.filter(pk=subject.pk).exists()


def is_lesson_free(lesson: Lesson) -> bool:
    """Первый урок предмета (детерминированно по `order=0` на каждом уровне)."""
    return (
        lesson.order == 0
        and lesson.topic.order == 0
        and lesson.topic.section.order == 0
    )


def previous_lesson(lesson: Lesson) -> Lesson | None:
    """Предыдущий урок предмета по плоскому порядку.

    Сортировка: `(section.order, topic.order, lesson.order, lesson.id)`.
    Последнее поле — стабильный tie-breaker если контент-менеджер забыл выставить order.
    Берём только опубликованные уроки.
    """
    s_order = lesson.topic.section.order
    t_order = lesson.topic.order
    l_order = lesson.order
    subject_id = lesson.topic.section.subject_id

    return (
        Lesson.objects.filter(
            topic__section__subject_id=subject_id,
            content_status=Lesson.ContentStatus.PUBLISHED,
        )
        .exclude(pk=lesson.pk)
        .filter(
            Q(topic__section__order__lt=s_order)
            | Q(topic__section__order=s_order, topic__order__lt=t_order)
            | Q(
                topic__section__order=s_order,
                topic__order=t_order,
                order__lt=l_order,
            )
            | Q(
                topic__section__order=s_order,
                topic__order=t_order,
                order=l_order,
                id__lt=lesson.id,
            )
        )
        .order_by(
            "-topic__section__order",
            "-topic__order",
            "-order",
            "-id",
        )
        .first()
    )


def next_lesson(lesson: Lesson) -> Lesson | None:
    """Следующий урок предмета по плоскому порядку (зеркало `previous_lesson`)."""
    s_order = lesson.topic.section.order
    t_order = lesson.topic.order
    l_order = lesson.order
    subject_id = lesson.topic.section.subject_id

    return (
        Lesson.objects.filter(
            topic__section__subject_id=subject_id,
            content_status=Lesson.ContentStatus.PUBLISHED,
        )
        .exclude(pk=lesson.pk)
        .filter(
            Q(topic__section__order__gt=s_order)
            | Q(topic__section__order=s_order, topic__order__gt=t_order)
            | Q(
                topic__section__order=s_order,
                topic__order=t_order,
                order__gt=l_order,
            )
            | Q(
                topic__section__order=s_order,
                topic__order=t_order,
                order=l_order,
                id__gt=lesson.id,
            )
        )
        .order_by(
            "topic__section__order",
            "topic__order",
            "order",
            "id",
        )
        .first()
    )


def lock_reason_for_lesson(user: User, lesson: Lesson) -> str | None:
    """Возвращает причину блокировки или None если урок открыт.

    Порядок проверок важен — самая «жёсткая» причина возвращается первой.
    """
    if lesson.content_status != Lesson.ContentStatus.PUBLISHED:
        return LOCK_REASON_UNPUBLISHED

    if not is_lesson_free(lesson):
        subject = lesson.topic.section.subject
        if not has_subscription_access(user, subject):
            return LOCK_REASON_NO_SUBSCRIPTION

    prev = previous_lesson(lesson)
    if prev is not None and not _has_at_least_one_star(user, prev):
        return LOCK_REASON_PREVIOUS_NOT_COMPLETED

    return None


def is_lesson_unlocked_for_user(user: User, lesson: Lesson) -> bool:
    """True если ученик может открыть содержимое урока и начать мини-тест."""
    return lock_reason_for_lesson(user, lesson) is None


def _has_at_least_one_star(user: User, lesson: Lesson) -> bool:
    return LessonProgress.objects.filter(
        user=user, lesson=lesson, stars__gte=1
    ).exists()
