"""Бизнес-операции по мини-тесту: старт, сабмит, скоринг."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import QadamAPIError

from ..access import is_lesson_unlocked_for_user, next_lesson
from ..models import Lesson, Quiz, QuizAttempt, QuizQuestion
from .progress import update_progress_after_attempt

# TTL «брошенной» попытки до автоматического expired.
ATTEMPT_TTL = timedelta(hours=24)


# ─── Скоринг ─────────────────────────────────────────────────────────────────
def stars_for_score(score_percent: int) -> int:
    """Маппинг % → звёзды по ТЗ §6.5/§4.3."""
    if score_percent >= 100:
        return 3
    if score_percent >= 80:
        return 2
    if score_percent >= 60:
        return 1
    return 0


def is_answer_correct(question: QuizQuestion, user_answer: Any) -> bool:
    """Сравнение ответа ученика с правильными ответами вопроса.

    Все типы реализуют логику «всё-или-ничего» — частичных баллов нет.

    Форматы:
    - single_choice / multi_choice / context: `["a"]` или `["a", "c"]`
    - match: список пар `[["left1", "right1"], ["left2", "right2"]]` ИЛИ
      словарь `{"left1": "right1", "left2": "right2"}`. Сравнивается как множество пар.
    """
    correct = question.correct_answers
    qtype = question.type

    if qtype == QuizQuestion.QuestionType.MATCH:
        return _normalize_match(user_answer) == _normalize_match(correct)

    return _normalize_set(user_answer) == _normalize_set(correct)


def _normalize_set(value: Any) -> frozenset:
    if not isinstance(value, list):
        return frozenset()
    return frozenset(str(v) for v in value)


def _normalize_match(value: Any) -> frozenset:
    if isinstance(value, dict):
        return frozenset((str(k), str(v)) for k, v in value.items())
    if isinstance(value, list):
        return frozenset(
            (str(pair[0]), str(pair[1]))
            for pair in value
            if isinstance(pair, (list, tuple)) and len(pair) == 2
        )
    return frozenset()


# ─── start_attempt ───────────────────────────────────────────────────────────
def start_attempt(*, user: User, lesson: Lesson) -> QuizAttempt:
    """Создать или возобновить попытку прохождения мини-теста урока."""
    if not is_lesson_unlocked_for_user(user, lesson):
        raise QadamAPIError(
            message="Урок заблокирован.",
            code="LESSON_LOCKED",
            status_code=403,
        )

    quiz = _get_quiz_for_lesson(lesson)

    existing = QuizAttempt.objects.filter(
        user=user,
        quiz=quiz,
        status=QuizAttempt.Status.IN_PROGRESS,
    ).first()

    if existing is not None:
        if timezone.now() - existing.started_at < ATTEMPT_TTL:
            return existing
        # Старая попытка протухла — помечаем expired, идём создавать новую
        existing.status = QuizAttempt.Status.EXPIRED
        existing.save(update_fields=["status", "updated_at"])

    return QuizAttempt.objects.create(
        user=user,
        quiz=quiz,
        status=QuizAttempt.Status.IN_PROGRESS,
    )


# ─── submit_attempt ──────────────────────────────────────────────────────────
def submit_attempt(
    *,
    user: User,
    attempt_id: int,
    answers: list[dict],
) -> dict:
    """Засабмитить ответы, посчитать балл, обновить прогресс, вернуть review-payload."""
    try:
        attempt = QuizAttempt.objects.select_related("quiz__lesson__topic__section__subject").get(
            pk=attempt_id
        )
    except QuizAttempt.DoesNotExist as exc:
        raise QadamAPIError(
            message="Попытка не найдена.",
            code="ATTEMPT_NOT_FOUND",
            status_code=404,
        ) from exc

    if attempt.user_id != user.id:
        raise QadamAPIError(
            message="Это чужая попытка.",
            code="ATTEMPT_NOT_OWNED",
            status_code=403,
        )

    if attempt.status == QuizAttempt.Status.FINISHED:
        raise QadamAPIError(
            message="Эта попытка уже завершена.",
            code="ATTEMPT_ALREADY_FINISHED",
        )

    if (
        attempt.status == QuizAttempt.Status.EXPIRED
        or timezone.now() - attempt.started_at > ATTEMPT_TTL
    ):
        if attempt.status != QuizAttempt.Status.EXPIRED:
            attempt.status = QuizAttempt.Status.EXPIRED
            attempt.save(update_fields=["status", "updated_at"])
        raise QadamAPIError(
            message="Срок попытки истёк, начните новую.",
            code="ATTEMPT_EXPIRED",
        )

    answer_map = {a["question_id"]: a.get("value", []) for a in answers}
    questions = list(attempt.quiz.questions.all().order_by("order", "id"))

    review_payload: list[dict] = []
    answers_snapshot: list[dict] = []
    correct_count = 0

    for q in questions:
        user_answer = answer_map.get(q.id, [])
        is_correct = is_answer_correct(q, user_answer)
        if is_correct:
            correct_count += 1
        review_payload.append(
            {
                "question_id": q.id,
                "user_answer": user_answer,
                "correct_answer": q.correct_answers,
                "is_correct": is_correct,
                "explanation": "",  # поле для будущего расширения (объяснение от методиста)
            }
        )
        answers_snapshot.append(
            {"question_id": q.id, "value": user_answer, "is_correct": is_correct}
        )

    total_count = len(questions)
    score_percent = (correct_count * 100) // total_count if total_count else 0
    stars_earned = stars_for_score(score_percent)

    lesson = attempt.quiz.lesson

    with transaction.atomic():
        attempt.status = QuizAttempt.Status.FINISHED
        attempt.finished_at = timezone.now()
        attempt.score = score_percent
        attempt.correct_count = correct_count
        attempt.total_count = total_count
        attempt.answers = answers_snapshot
        attempt.save()

        progress = update_progress_after_attempt(
            user=user,
            lesson=lesson,
            score_percent=score_percent,
            stars_earned=stars_earned,
        )

    nxt = next_lesson(lesson)
    next_unlocked = nxt is not None and is_lesson_unlocked_for_user(user, nxt)

    return {
        "attempt_id": attempt.id,
        "score_percent": score_percent,
        "correct_count": correct_count,
        "total_count": total_count,
        "stars_earned": stars_earned,
        "stars_now": progress.stars,
        "lesson_completed": progress.completed_at is not None,
        "next_lesson_unlocked": next_unlocked,
        "next_lesson_id": nxt.id if nxt is not None else None,
        "review": review_payload,
    }


# ─── helpers ─────────────────────────────────────────────────────────────────
def _get_quiz_for_lesson(lesson: Lesson) -> Quiz:
    quiz = getattr(lesson, "quiz", None)
    if quiz is None:
        raise QadamAPIError(
            message="У этого урока нет мини-теста.",
            code="LESSON_HAS_NO_QUIZ",
        )
    return quiz
