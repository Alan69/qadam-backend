"""Тесты quiz-эндпоинтов: start, submit, history, attempt-detail."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.learning.models import QuizAttempt
from tests.factories import (
    LessonFactory,
    QuizFactory,
    UserFactory,
    make_lesson_with_quiz,
)


@pytest.mark.django_db
class TestQuizStartAPI:
    def test_start_returns_questions_without_correct_answers(
        self, api_client: APIClient
    ):
        student = UserFactory()
        lesson = make_lesson_with_quiz(questions=3)
        api_client.force_authenticate(user=student)
        r = api_client.post(f"/api/v1/learning/lessons/{lesson.id}/quiz/start/")
        assert r.status_code == 200, r.data
        assert "attempt_id" in r.data
        assert len(r.data["questions"]) == 3
        for q in r.data["questions"]:
            assert "correct_answers" not in q
            assert "explanation" not in q

    def test_start_locked_lesson_returns_403(self, api_client: APIClient):
        student = UserFactory()
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        QuizFactory(lesson=second)
        api_client.force_authenticate(user=student)
        r = api_client.post(f"/api/v1/learning/lessons/{second.id}/quiz/start/")
        assert r.status_code == 403
        assert r.data["error"]["code"] == "LESSON_LOCKED"

    def test_start_resumes_existing_in_progress(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        api_client.force_authenticate(user=student)
        r1 = api_client.post(f"/api/v1/learning/lessons/{lesson.id}/quiz/start/")
        r2 = api_client.post(f"/api/v1/learning/lessons/{lesson.id}/quiz/start/")
        assert r1.data["attempt_id"] == r2.data["attempt_id"]


@pytest.mark.django_db
class TestQuizSubmitAPI:
    def _start_and_get_correct_answers(self, api_client, student, lesson):
        api_client.force_authenticate(user=student)
        r = api_client.post(f"/api/v1/learning/lessons/{lesson.id}/quiz/start/")
        attempt_id = r.data["attempt_id"]
        # Берём правильные ответы из БД (они не в /start/ payload)
        questions = lesson.quiz.questions.all().order_by("order", "id")
        return attempt_id, [
            {"question_id": q.id, "value": q.correct_answers} for q in questions
        ]

    def test_submit_perfect_score(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)
        attempt_id, answers = self._start_and_get_correct_answers(
            api_client, student, lesson
        )
        r = api_client.post(
            f"/api/v1/learning/quiz-attempts/{attempt_id}/submit/",
            {"answers": answers},
            format="json",
        )
        assert r.status_code == 200, r.data
        assert r.data["score_percent"] == 100
        assert r.data["stars_earned"] == 3
        assert r.data["lesson_completed"] is True
        # Review должен включать правильные ответы
        for entry in r.data["review"]:
            assert "correct_answer" in entry

    def test_submit_partial_score(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz(questions=5)
        api_client.force_authenticate(user=student)
        r1 = api_client.post(f"/api/v1/learning/lessons/{lesson.id}/quiz/start/")
        attempt_id = r1.data["attempt_id"]

        questions = list(lesson.quiz.questions.all().order_by("order", "id"))
        # 3 правильных, 2 неправильных = 60% = 1 звезда
        answers = []
        for i, q in enumerate(questions):
            answers.append(
                {
                    "question_id": q.id,
                    "value": q.correct_answers if i < 3 else ["WRONG"],
                }
            )
        r = api_client.post(
            f"/api/v1/learning/quiz-attempts/{attempt_id}/submit/",
            {"answers": answers},
            format="json",
        )
        assert r.data["score_percent"] == 60
        assert r.data["stars_earned"] == 1

    def test_submit_other_users_attempt_returns_403(self, api_client: APIClient):
        student_a = UserFactory()
        student_b = UserFactory()
        lesson = make_lesson_with_quiz()
        attempt_id, answers = self._start_and_get_correct_answers(
            api_client, student_a, lesson
        )

        api_client.force_authenticate(user=student_b)
        r = api_client.post(
            f"/api/v1/learning/quiz-attempts/{attempt_id}/submit/",
            {"answers": answers},
            format="json",
        )
        assert r.status_code == 403
        assert r.data["error"]["code"] == "ATTEMPT_NOT_OWNED"

    def test_double_submit_returns_400(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        attempt_id, answers = self._start_and_get_correct_answers(
            api_client, student, lesson
        )
        api_client.post(
            f"/api/v1/learning/quiz-attempts/{attempt_id}/submit/",
            {"answers": answers},
            format="json",
        )
        r = api_client.post(
            f"/api/v1/learning/quiz-attempts/{attempt_id}/submit/",
            {"answers": answers},
            format="json",
        )
        assert r.status_code == 400
        assert r.data["error"]["code"] == "ATTEMPT_ALREADY_FINISHED"


@pytest.mark.django_db
class TestAttemptHistoryAPI:
    def test_returns_attempts_for_lesson(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        # Создаём 2 попытки
        QuizAttempt.objects.create(
            user=student,
            quiz=lesson.quiz,
            status=QuizAttempt.Status.FINISHED,
            score=80,
            correct_count=4,
            total_count=5,
        )
        QuizAttempt.objects.create(
            user=student,
            quiz=lesson.quiz,
            status=QuizAttempt.Status.FINISHED,
            score=100,
            correct_count=5,
            total_count=5,
        )
        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/lessons/{lesson.id}/attempts/")
        assert r.status_code == 200
        assert len(r.data) == 2

    def test_does_not_return_other_users_attempts(self, api_client: APIClient):
        student_a = UserFactory()
        student_b = UserFactory()
        lesson = make_lesson_with_quiz()
        QuizAttempt.objects.create(
            user=student_a,
            quiz=lesson.quiz,
            status=QuizAttempt.Status.FINISHED,
            score=80,
        )
        api_client.force_authenticate(user=student_b)
        r = api_client.get(f"/api/v1/learning/lessons/{lesson.id}/attempts/")
        assert r.status_code == 200
        assert r.data == []


@pytest.mark.django_db
class TestQuizAttemptDetailAPI:
    def test_returns_review_for_own_attempt(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz(questions=2)
        api_client.force_authenticate(user=student)
        r1 = api_client.post(f"/api/v1/learning/lessons/{lesson.id}/quiz/start/")
        attempt_id = r1.data["attempt_id"]
        questions = list(lesson.quiz.questions.all().order_by("order", "id"))
        answers = [
            {"question_id": q.id, "value": q.correct_answers} for q in questions
        ]
        api_client.post(
            f"/api/v1/learning/quiz-attempts/{attempt_id}/submit/",
            {"answers": answers},
            format="json",
        )
        r = api_client.get(f"/api/v1/learning/quiz-attempts/{attempt_id}/")
        assert r.status_code == 200
        assert r.data["score_percent"] == 100
        assert len(r.data["review"]) == 2

    def test_other_users_attempt_returns_403(self, api_client: APIClient):
        student_a = UserFactory()
        student_b = UserFactory()
        lesson = make_lesson_with_quiz()
        attempt = QuizAttempt.objects.create(
            user=student_a,
            quiz=lesson.quiz,
            status=QuizAttempt.Status.FINISHED,
            score=80,
        )
        api_client.force_authenticate(user=student_b)
        r = api_client.get(f"/api/v1/learning/quiz-attempts/{attempt.id}/")
        assert r.status_code == 403
        assert r.data["error"]["code"] == "ATTEMPT_NOT_OWNED"
