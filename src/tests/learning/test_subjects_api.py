"""Тесты GET /subjects/ и /subjects/{id}/."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.learning.models import LessonProgress
from tests.factories import (
    LessonFactory,
    SubscriptionFactory,
    TariffFactory,
    UserFactory,
    make_lesson_with_quiz,
)


@pytest.mark.django_db
class TestSubjectListAPI:
    def test_anonymous_denied(self, api_client: APIClient):
        r = api_client.get("/api/v1/learning/subjects/")
        assert r.status_code == 401

    def test_curator_denied(self, api_client: APIClient, curator):
        api_client.force_authenticate(user=curator)
        r = api_client.get("/api/v1/learning/subjects/")
        assert r.status_code == 403

    def test_student_sees_published_subjects(self, api_client: APIClient):
        student = UserFactory()
        s1 = make_lesson_with_quiz().topic.section.subject
        s2 = make_lesson_with_quiz().topic.section.subject
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/learning/subjects/")
        assert r.status_code == 200
        ids = [s["id"] for s in r.data]
        assert s1.id in ids and s2.id in ids

    def test_locked_when_no_subscription(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/learning/subjects/")
        item = next(s for s in r.data if s["id"] == lesson.topic.section.subject_id)
        assert item["is_locked"] is True

    def test_unlocked_with_subscription(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        subject = lesson.topic.section.subject
        SubscriptionFactory(user=student, tariff=TariffFactory(subjects=[subject]))
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/learning/subjects/")
        item = next(s for s in r.data if s["id"] == subject.id)
        assert item["is_locked"] is False

    def test_aggregates_completed_lessons_and_stars(self, api_client: APIClient):
        student = UserFactory()
        lesson = make_lesson_with_quiz()
        LessonProgress.objects.create(
            user=student,
            lesson=lesson,
            stars=2,
            best_quiz_score=85,
            attempts_count=1,
            completed_at="2026-04-28T12:00:00Z",
        )
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/learning/subjects/")
        item = next(s for s in r.data if s["id"] == lesson.topic.section.subject_id)
        assert item["lessons_completed"] == 1
        assert item["stars_total"] == 2


@pytest.mark.django_db
class TestSubjectDetailAPI:
    def test_returns_full_hierarchy(self, api_client: APIClient):
        student = UserFactory()
        first = make_lesson_with_quiz()
        # Второй урок в той же теме
        LessonFactory(topic=first.topic, order=1)
        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/subjects/{first.topic.section.subject_id}/")
        assert r.status_code == 200
        sections = r.data["sections"]
        assert len(sections) == 1
        topics = sections[0]["topics"]
        assert len(topics) == 1
        lessons = topics[0]["lessons"]
        assert len(lessons) == 2

    def test_lock_flags_per_lesson(self, api_client: APIClient):
        student = UserFactory()
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        api_client.force_authenticate(user=student)
        r = api_client.get(f"/api/v1/learning/subjects/{first.topic.section.subject_id}/")
        lessons = r.data["sections"][0]["topics"][0]["lessons"]
        # Первый — бесплатный, разблокирован
        assert lessons[0]["id"] == first.id
        assert lessons[0]["is_locked"] is False
        assert lessons[0]["is_free"] is True
        # Второй — заблокирован (paywall)
        assert lessons[1]["id"] == second.id
        assert lessons[1]["is_locked"] is True
        assert lessons[1]["lock_reason"] == "no_subscription"

    def test_404_for_missing_subject(self, api_client: APIClient):
        student = UserFactory()
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/learning/subjects/99999/")
        assert r.status_code == 404
