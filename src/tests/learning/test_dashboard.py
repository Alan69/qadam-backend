"""Тесты обновлённого /profile/dashboard/ — теперь с реальными данными."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.learning.models import LessonProgress
from apps.profiles.services import create_student_profile
from tests.factories import (
    SubscriptionFactory,
    TariffFactory,
    UserFactory,
    make_lesson_with_quiz,
)


@pytest.mark.django_db
class TestDashboard:
    def _make_student(self) -> UserFactory:
        user = UserFactory()
        create_student_profile(
            user=user,
            name="Test",
            parent_phone="+77001111111",
            grade=11,
            learning_language="ru",
        )
        return user

    def test_dashboard_aggregates_lessons_completed(self, api_client: APIClient):
        student = self._make_student()
        lesson = make_lesson_with_quiz()
        LessonProgress.objects.create(
            user=student, lesson=lesson, stars=2, completed_at="2026-04-28T12:00:00Z"
        )
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/profile/dashboard/")
        assert r.status_code == 200
        assert r.data["progress"]["lessons_completed"] == 1
        assert r.data["stars"]["total"] == 2

    def test_dashboard_by_subject_breakdown(self, api_client: APIClient):
        student = self._make_student()
        l1 = make_lesson_with_quiz()
        l2 = make_lesson_with_quiz()
        LessonProgress.objects.create(
            user=student, lesson=l1, stars=3, completed_at="2026-04-28T12:00:00Z"
        )
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/profile/dashboard/")
        by_subject = r.data["progress"]["by_subject"]
        assert len(by_subject) == 2
        # Один предмет полностью пройден, второй — 0
        completed = {s["subject_id"]: s["completed"] for s in by_subject}
        assert completed[l1.topic.section.subject_id] == 1
        assert completed[l2.topic.section.subject_id] == 0

    def test_dashboard_subscription_active(self, api_client: APIClient):
        student = self._make_student()
        lesson = make_lesson_with_quiz()
        subject = lesson.topic.section.subject
        SubscriptionFactory(user=student, tariff=TariffFactory(subjects=[subject]))
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/profile/dashboard/")
        sub = r.data["subscription"]
        assert sub["active"] is True
        assert sub["tariff"] is not None
        assert subject.id in sub["subjects"]

    def test_dashboard_subscription_inactive(self, api_client: APIClient):
        student = self._make_student()
        api_client.force_authenticate(user=student)
        r = api_client.get("/api/v1/profile/dashboard/")
        sub = r.data["subscription"]
        assert sub["active"] is False
        assert sub["tariff"] is None
