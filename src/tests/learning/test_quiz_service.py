"""Тесты сервиса мини-тестов: start_attempt, submit_attempt, скоринг, прогресс."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.common.exceptions import QadamAPIError
from apps.learning.models import Lesson, LessonProgress, QuizAttempt, QuizQuestion
from apps.learning.services.quiz import (
    is_answer_correct,
    start_attempt,
    stars_for_score,
    submit_attempt,
)
from tests.factories import (
    LessonFactory,
    QuizFactory,
    QuizQuestionFactory,
    SubscriptionFactory,
    TariffFactory,
    UserFactory,
    make_lesson_with_quiz,
)


# ─── stars_for_score ─────────────────────────────────────────────────────────
class TestStarsForScore:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0, 0),
            (59, 0),
            (60, 1),
            (79, 1),
            (80, 2),
            (99, 2),
            (100, 3),
        ],
    )
    def test_thresholds(self, score: int, expected: int):
        assert stars_for_score(score) == expected


# ─── is_answer_correct ───────────────────────────────────────────────────────
@pytest.mark.django_db
class TestIsAnswerCorrect:
    def test_single_choice_correct(self):
        q = QuizQuestionFactory(
            type=QuizQuestion.QuestionType.SINGLE,
            options=["A", "B", "C"],
            correct_answers=["B"],
        )
        assert is_answer_correct(q, ["B"]) is True

    def test_single_choice_wrong(self):
        q = QuizQuestionFactory(
            type=QuizQuestion.QuestionType.SINGLE,
            correct_answers=["B"],
        )
        assert is_answer_correct(q, ["A"]) is False

    def test_multi_choice_all_or_nothing(self):
        q = QuizQuestionFactory(
            type=QuizQuestion.QuestionType.MULTI,
            correct_answers=["A", "C"],
        )
        assert is_answer_correct(q, ["A", "C"]) is True
        assert is_answer_correct(q, ["C", "A"]) is True  # порядок не важен
        assert is_answer_correct(q, ["A"]) is False  # частичный ответ
        assert is_answer_correct(q, ["A", "B", "C"]) is False  # лишний

    def test_match_as_dict(self):
        q = QuizQuestionFactory(
            type=QuizQuestion.QuestionType.MATCH,
            correct_answers={"a": "1", "b": "2"},
        )
        assert is_answer_correct(q, {"a": "1", "b": "2"}) is True
        assert is_answer_correct(q, {"a": "2", "b": "1"}) is False

    def test_match_as_list_of_pairs(self):
        q = QuizQuestionFactory(
            type=QuizQuestion.QuestionType.MATCH,
            correct_answers=[["a", "1"], ["b", "2"]],
        )
        assert is_answer_correct(q, [["a", "1"], ["b", "2"]]) is True
        assert is_answer_correct(q, [["b", "2"], ["a", "1"]]) is True


# ─── start_attempt ───────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestStartAttempt:
    def test_creates_in_progress_attempt(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz()
        attempt = start_attempt(user=user, lesson=lesson)
        assert attempt.status == QuizAttempt.Status.IN_PROGRESS
        assert attempt.user == user
        assert attempt.quiz == lesson.quiz

    def test_resumes_existing_in_progress(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz()
        first = start_attempt(user=user, lesson=lesson)
        second = start_attempt(user=user, lesson=lesson)
        assert first.id == second.id

    def test_expires_old_and_creates_new_after_24h(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz()

        with freeze_time("2026-04-28 12:00:00"):
            old = start_attempt(user=user, lesson=lesson)

        with freeze_time("2026-04-29 13:00:00"):  # 25 часов спустя
            new = start_attempt(user=user, lesson=lesson)

        old.refresh_from_db()
        assert old.status == QuizAttempt.Status.EXPIRED
        assert new.id != old.id
        assert new.status == QuizAttempt.Status.IN_PROGRESS

    def test_locked_lesson_raises(self):
        user = UserFactory()
        first = make_lesson_with_quiz()
        # Второй урок без подписки/прохождения первого
        second = LessonFactory(topic=first.topic, order=1)
        QuizFactory(lesson=second)
        with pytest.raises(QadamAPIError) as exc_info:
            start_attempt(user=user, lesson=second)
        assert exc_info.value.code == "LESSON_LOCKED"

    def test_lesson_without_quiz_raises(self):
        user = UserFactory()
        # Создаём lesson вручную без QuizFactory — first lesson, бесплатный
        lesson = LessonFactory()  # без quiz
        with pytest.raises(QadamAPIError) as exc_info:
            start_attempt(user=user, lesson=lesson)
        assert exc_info.value.code == "LESSON_HAS_NO_QUIZ"


# ─── submit_attempt ──────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestSubmitAttempt:
    def _make_attempt(self, user, lesson, *, all_correct: bool = True):
        """Создать попытку и подготовить answers для теста.

        Возвращает (attempt, answers).
        """
        attempt = start_attempt(user=user, lesson=lesson)
        questions = lesson.quiz.questions.all().order_by("order", "id")
        answers = []
        for i, q in enumerate(questions):
            # All-correct если флаг включён, иначе только первый вопрос правильный
            if all_correct or i == 0:
                answers.append({"question_id": q.id, "value": q.correct_answers})
            else:
                answers.append({"question_id": q.id, "value": ["WRONG"]})
        return attempt, answers

    def test_perfect_score_gives_3_stars(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)
        attempt, answers = self._make_attempt(user, lesson, all_correct=True)
        result = submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        assert result["score_percent"] == 100
        assert result["stars_earned"] == 3
        assert result["correct_count"] == 5
        assert result["total_count"] == 5

    def test_60_percent_gives_1_star(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)
        # 3 из 5 правильных = 60%
        attempt = start_attempt(user=user, lesson=lesson)
        questions = list(lesson.quiz.questions.all().order_by("order", "id"))
        answers = []
        for i, q in enumerate(questions):
            answers.append(
                {
                    "question_id": q.id,
                    "value": q.correct_answers if i < 3 else ["WRONG"],
                }
            )
        result = submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        assert result["score_percent"] == 60
        assert result["stars_earned"] == 1

    def test_below_60_gives_0_stars(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)
        attempt = start_attempt(user=user, lesson=lesson)
        questions = list(lesson.quiz.questions.all().order_by("order", "id"))
        answers = [{"question_id": q.id, "value": ["WRONG"]} for q in questions]
        result = submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        assert result["score_percent"] == 0
        assert result["stars_earned"] == 0

    def test_max_merge_keeps_higher_stars_after_pass_then_fail(self):
        """Получил 3⭐ → пересдал на 1⭐ → должно остаться 3⭐."""
        user = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)

        # Первая попытка — все правильно
        a1 = start_attempt(user=user, lesson=lesson)
        questions = list(lesson.quiz.questions.all().order_by("order", "id"))
        all_correct = [{"question_id": q.id, "value": q.correct_answers} for q in questions]
        submit_attempt(user=user, attempt_id=a1.id, answers=all_correct)

        # Вторая попытка — почти всё неправильно (1 правильный, 20%)
        a2 = start_attempt(user=user, lesson=lesson)
        mostly_wrong = [
            {"question_id": q.id, "value": q.correct_answers if i == 0 else ["WRONG"]}
            for i, q in enumerate(questions)
        ]
        result2 = submit_attempt(user=user, attempt_id=a2.id, answers=mostly_wrong)

        assert result2["stars_earned"] == 0
        assert result2["stars_now"] == 3  # max сохранился

        progress = LessonProgress.objects.get(user=user, lesson=lesson)
        assert progress.stars == 3
        assert progress.attempts_count == 2
        assert progress.best_quiz_score == 100

    def test_completed_at_set_on_first_passing_attempt(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)
        attempt, answers = self._make_attempt(user, lesson, all_correct=True)
        submit_attempt(user=user, attempt_id=attempt.id, answers=answers)

        progress = LessonProgress.objects.get(user=user, lesson=lesson)
        assert progress.completed_at is not None

    def test_completed_at_not_changed_on_subsequent_attempts(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)

        # Первая успешная
        a1 = start_attempt(user=user, lesson=lesson)
        questions = list(lesson.quiz.questions.all().order_by("order", "id"))
        all_correct = [{"question_id": q.id, "value": q.correct_answers} for q in questions]

        with freeze_time("2026-04-28 12:00:00"):
            submit_attempt(user=user, attempt_id=a1.id, answers=all_correct)

        first_completed = LessonProgress.objects.get(user=user, lesson=lesson).completed_at

        # Вторая, тоже успешная — позже
        a2 = start_attempt(user=user, lesson=lesson)
        with freeze_time("2026-04-29 12:00:00"):
            submit_attempt(user=user, attempt_id=a2.id, answers=all_correct)

        second_completed = LessonProgress.objects.get(user=user, lesson=lesson).completed_at
        assert first_completed == second_completed

    def test_next_lesson_unlocked_when_score_above_60(self):
        user = UserFactory()
        first = make_lesson_with_quiz(questions=5)
        subject = first.topic.section.subject
        SubscriptionFactory(user=user, tariff=TariffFactory(subjects=[subject]))
        second = LessonFactory(topic=first.topic, order=1)
        QuizFactory(lesson=second)

        attempt, answers = self._make_attempt(user, first, all_correct=True)
        result = submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        assert result["next_lesson_unlocked"] is True
        assert result["next_lesson_id"] == second.id

    def test_next_lesson_locked_when_score_below_60(self):
        user = UserFactory()
        first = make_lesson_with_quiz(questions=5)
        subject = first.topic.section.subject
        SubscriptionFactory(user=user, tariff=TariffFactory(subjects=[subject]))
        second = LessonFactory(topic=first.topic, order=1)
        QuizFactory(lesson=second)

        attempt = start_attempt(user=user, lesson=first)
        questions = list(first.quiz.questions.all().order_by("order", "id"))
        wrong = [{"question_id": q.id, "value": ["WRONG"]} for q in questions]
        result = submit_attempt(user=user, attempt_id=attempt.id, answers=wrong)
        assert result["next_lesson_unlocked"] is False

    def test_review_payload_includes_correct_answers(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz(questions=3)
        attempt, answers = self._make_attempt(user, lesson, all_correct=True)
        result = submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        assert len(result["review"]) == 3
        for entry in result["review"]:
            assert "correct_answer" in entry
            assert "is_correct" in entry

    def test_other_user_cannot_submit(self):
        user_a = UserFactory()
        user_b = UserFactory()
        lesson = make_lesson_with_quiz()
        attempt, answers = self._make_attempt(user_a, lesson)
        with pytest.raises(QadamAPIError) as exc_info:
            submit_attempt(user=user_b, attempt_id=attempt.id, answers=answers)
        assert exc_info.value.code == "ATTEMPT_NOT_OWNED"

    def test_cannot_submit_finished_attempt_twice(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz()
        attempt, answers = self._make_attempt(user, lesson)
        submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        with pytest.raises(QadamAPIError) as exc_info:
            submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        assert exc_info.value.code == "ATTEMPT_ALREADY_FINISHED"

    def test_expired_attempt_cannot_submit(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz()
        with freeze_time("2026-04-28 12:00:00"):
            attempt, answers = self._make_attempt(user, lesson)
        with freeze_time("2026-04-29 13:00:00"):  # 25h позже
            with pytest.raises(QadamAPIError) as exc_info:
                submit_attempt(user=user, attempt_id=attempt.id, answers=answers)
        assert exc_info.value.code == "ATTEMPT_EXPIRED"
