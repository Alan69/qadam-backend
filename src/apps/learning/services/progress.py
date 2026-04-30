"""Обновление LessonProgress по результатам мини-теста (max-merge)."""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User

from ..models import Lesson, LessonProgress


def update_progress_after_attempt(
    *,
    user: User,
    lesson: Lesson,
    score_percent: int,
    stars_earned: int,
) -> LessonProgress:
    """Зачислить результат попытки в `LessonProgress` через max-merge.

    Правила:
    - `stars = max(stars, stars_earned)` — пересдача не отбирает звёзды.
    - `best_quiz_score = max(best_quiz_score, score_percent)`.
    - `attempts_count += 1` — каждая submitted-попытка считается.
    - `last_attempt_at = now()`.
    - `completed_at` ставится **один раз** — в момент когда впервые получена
      хотя бы 1 звезда (≥60%). Дальше не обновляется.
    """
    progress, _ = LessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson,
        defaults={"stars": 0, "best_quiz_score": 0, "attempts_count": 0},
    )

    is_first_completion = progress.stars == 0 and stars_earned >= 1

    progress.stars = max(progress.stars, stars_earned)
    progress.best_quiz_score = max(progress.best_quiz_score, score_percent)
    progress.attempts_count += 1
    progress.last_attempt_at = timezone.now()
    if is_first_completion:
        progress.completed_at = timezone.now()

    progress.save()
    return progress
