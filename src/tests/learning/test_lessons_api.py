"""Тесты GET /lessons/{id}/."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.learning.models import LessonProgress
from tests.factories import (
    LessonFactory,
    QuizFactory,
    SubscriptionFactory,
    TariffFactory,
    UserFactory,
    make_lesson_with_quiz,
)


@pytest.mark.django_db
class TestLessonDetailAPI:
    def test_first_lesson_accessible(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/lessons/{lesson.id}/")
        assert r.status_code == 200
        assert r.data["id"] == lesson.id
        assert r.data["is_free"] is True
        assert r.data["has_quiz"] is True

    def test_locked_lesson_returns_403(self, api_client: APIClient):
        student = UserFactory()
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        QuizFactory(lesson=second)
        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/lessons/{second.id}/")
        assert r.status_code == 403
        assert r.data["error"]["code"] == "LESSON_LOCKED"

    def test_404_for_missing_lesson(self, api_client: APIClient):
        student = UserFactory()
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/learning/lessons/99999/")
        assert r.status_code == 404

    def test_includes_progress_data(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        LessonProgress.objects.create(
            user=student, lesson=lesson, stars=2, best_quiz_score=85, attempts_count=3
        )
        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/lessons/{lesson.id}/")
        assert r.data["progress"]["stars"] == 2
        assert r.data["progress"]["best_score"] == 85
        assert r.data["progress"]["attempts_count"] == 3

    def test_next_lesson_id_when_present(self, api_client: APIClient):
        student = UserFactory()
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        QuizFactory(lesson=second)
        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/lessons/{first.id}/")
        assert r.data["next_lesson_id"] == second.id

    def test_subscription_unlocks_subsequent(self, api_client: APIClient):
        student = UserFactory()
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        QuizFactory(lesson=second)
        # Прохождение первого + подписка на предмет
        LessonProgress.objects.create(user=student, lesson=first, stars=1)
        subject = first.topic.section.subject
        SubscriptionFactory(user=student, tariff=TariffFactory(subjects=[subject]))

        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/lessons/{second.id}/")
        assert r.status_code == 200
