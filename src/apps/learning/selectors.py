"""Read-only селекторы — выдают данные в формате готовом для сериализации.

Принципы:
- Никаких побочных эффектов.
- Минимум обращений к БД (annotate / prefetch_related).
- Чисто словарные структуры на выходе. Сериалайзер только переименовывает / выкидывает поля.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Prefetch, Q, Sum

from apps.accounts.models import User

from .access import (
    has_subscription_access,
    is_lesson_free,
    lock_reason_for_lesson,
)
from .models import (
    Lesson,
    LessonProgress,
    Section,
    Subject,
    Topic,
)


# ─── subject_list_for_user ───────────────────────────────────────────────────
def subject_list_for_user(user: User) -> list[dict[str, Any]]:
    """Все опубликованные предметы с агрегатами по этому ученику."""
    # Опубликованные уроки — единственный источник правды о «общем количестве»
    # уроков предмета (в админке могут лежать черновики, но ученик их не видит).
    subjects = Subject.objects.annotate(
        lessons_total=Count(
            "sections__topics__lessons",
            filter=Q(sections__topics__lessons__content_status=Lesson.ContentStatus.PUBLISHED),
            distinct=True,
        ),
    ).order_by("name")

    # За один запрос вытаскиваем прогресс ученика по всем урокам всех предметов.
    progress_rows = LessonProgress.objects.filter(user=user).values(
        "lesson__topic__section__subject_id",
        "stars",
        "completed_at",
    )

    # Агрегируем в Python (быстро — кол-во записей маленькое).
    completed_by_subject: dict[int, int] = {}
    stars_by_subject: dict[int, int] = {}
    for row in progress_rows:
        sid = row["lesson__topic__section__subject_id"]
        if row["completed_at"] is not None:
            completed_by_subject[sid] = completed_by_subject.get(sid, 0) + 1
        stars_by_subject[sid] = stars_by_subject.get(sid, 0) + row["stars"]

    result: list[dict[str, Any]] = []
    for subject in subjects:
        completed = completed_by_subject.get(subject.id, 0)
        stars = stars_by_subject.get(subject.id, 0)
        total = subject.lessons_total
        progress_percent = (completed * 100 // total) if total else 0
        is_locked = not has_subscription_access(user, subject)
        result.append(
            {
                "id": subject.id,
                "name": subject.name,
                "icon": subject.icon,
                "is_locked": is_locked,
                "lessons_total": total,
                "lessons_completed": completed,
                "stars_total": stars,
                "stars_max": total * 3,
                "progress_percent": progress_percent,
            }
        )
    return result


# ─── subject_detail_for_user ─────────────────────────────────────────────────
def subject_detail_for_user(user: User, subject_id: int) -> dict[str, Any] | None:
    """Полная иерархия предмета с lock-флагами и прогрессом по каждому уроку."""
    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return None

    lesson_qs = Lesson.objects.filter(content_status=Lesson.ContentStatus.PUBLISHED).order_by(
        "order", "id"
    )
    topic_qs = Topic.objects.prefetch_related(Prefetch("lessons", queryset=lesson_qs)).order_by(
        "order", "id"
    )
    section_qs = (
        Section.objects.filter(subject=subject)
        .prefetch_related(Prefetch("topics", queryset=topic_qs))
        .order_by("order", "id")
    )

    progress_map = {
        p.lesson_id: p
        for p in LessonProgress.objects.filter(user=user, lesson__topic__section__subject=subject)
    }

    sections_data = []
    for section in section_qs:
        topics_data = []
        for topic in section.topics.all():
            lessons_data = []
            for lesson in topic.lessons.all():
                lock_reason = lock_reason_for_lesson(user, lesson)
                progress = progress_map.get(lesson.id)
                lessons_data.append(
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "order": lesson.order,
                        "is_locked": lock_reason is not None,
                        "lock_reason": lock_reason,
                        "is_free": is_lesson_free(lesson),
                        "stars": progress.stars if progress else 0,
                        "best_score": progress.best_quiz_score if progress else 0,
                        "completed_at": progress.completed_at if progress else None,
                    }
                )
            topics_data.append(
                {
                    "id": topic.id,
                    "name": topic.name,
                    "order": topic.order,
                    "lessons": lessons_data,
                }
            )
        sections_data.append(
            {
                "id": section.id,
                "name": section.name,
                "order": section.order,
                "topics": topics_data,
            }
        )

    return {
        "id": subject.id,
        "name": subject.name,
        "description": subject.description,
        "icon": subject.icon,
        "is_locked": not has_subscription_access(user, subject),
        "sections": sections_data,
    }


# ─── lesson_detail_for_user ──────────────────────────────────────────────────
def lesson_detail_for_user(user: User, lesson_id: int) -> dict[str, Any] | None:
    """Детали урока с прогрессом ученика и id следующего урока."""
    from .access import next_lesson  # local import — избегаем циклической зависимости

    try:
        lesson = Lesson.objects.select_related("topic__section__subject").get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return None

    lock_reason = lock_reason_for_lesson(user, lesson)
    progress = LessonProgress.objects.filter(user=user, lesson=lesson).first()
    nxt = next_lesson(lesson)

    has_quiz = hasattr(lesson, "quiz") and lesson.quiz is not None

    return {
        "id": lesson.id,
        "title": lesson.title,
        "video_url": lesson.video_url,
        "theory": lesson.theory,
        "topic": {
            "id": lesson.topic_id,
            "name": lesson.topic.name,
            "order": lesson.topic.order,
        },
        "section": {
            "id": lesson.topic.section_id,
            "name": lesson.topic.section.name,
            "order": lesson.topic.section.order,
        },
        "subject": {
            "id": lesson.topic.section.subject_id,
            "name": lesson.topic.section.subject.name,
        },
        "is_locked": lock_reason is not None,
        "lock_reason": lock_reason,
        "is_free": is_lesson_free(lesson),
        "has_quiz": has_quiz,
        "progress": {
            "stars": progress.stars if progress else 0,
            "best_score": progress.best_quiz_score if progress else 0,
            "attempts_count": progress.attempts_count if progress else 0,
            "completed_at": progress.completed_at if progress else None,
        },
        "next_lesson_id": nxt.id if nxt else None,
    }


# ─── learning data for dashboard ─────────────────────────────────────────────
def dashboard_learning_data(user: User) -> dict[str, Any]:
    """Данные для блоков `progress` и `stars` дашборда."""
    subjects = subject_list_for_user(user)

    total_completed = sum(s["lessons_completed"] for s in subjects)
    total_stars = sum(s["stars_total"] for s in subjects)
    max_stars = sum(s["stars_max"] for s in subjects)

    last_progress = (
        LessonProgress.objects.filter(user=user)
        .order_by("-last_attempt_at")
        .values_list("last_attempt_at", flat=True)
        .first()
    )

    # Звёзды за неделю
    from datetime import timedelta

    from django.utils import timezone

    week_ago = timezone.now() - timedelta(days=7)
    stars_this_week = (
        LessonProgress.objects.filter(user=user, last_attempt_at__gte=week_ago).aggregate(
            total=Sum("stars")
        )["total"]
        or 0
    )

    return {
        "progress": {
            "lessons_completed": total_completed,
            "by_subject": [
                {
                    "subject_id": s["id"],
                    "name": s["name"],
                    "completed": s["lessons_completed"],
                    "total": s["lessons_total"],
                    "percent": s["progress_percent"],
                }
                for s in subjects
            ],
            "last_activity": last_progress,
        },
        "stars": {
            "total": total_stars,
            "this_week": stars_this_week,
            "max_possible": max_stars,
        },
    }
