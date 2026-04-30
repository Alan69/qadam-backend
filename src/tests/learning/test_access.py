"""Тесты paywall, sequential unlock и lock_reason."""

from __future__ import annotations

import pytest

from apps.learning.access import (
    LOCK_REASON_NO_SUBSCRIPTION,
    LOCK_REASON_PREVIOUS_NOT_COMPLETED,
    LOCK_REASON_UNPUBLISHED,
    has_subscription_access,
    is_lesson_free,
    is_lesson_unlocked_for_user,
    lock_reason_for_lesson,
    previous_lesson,
)
from apps.learning.models import Lesson, LessonProgress
from tests.factories import (
    ExpiredSubscriptionFactory,
    LessonFactory,
    SectionFactory,
    SubjectFactory,
    SubscriptionFactory,
    TariffFactory,
    TopicFactory,
    UserFactory,
    make_lesson_with_quiz,
)


# ─── is_lesson_free ──────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestIsLessonFree:
    def test_first_lesson_of_subject_is_free(self):
        lesson = make_lesson_with_quiz()  # все order=0
        assert is_lesson_free(lesson) is True

    def test_second_lesson_in_topic_is_not_free(self):
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        assert is_lesson_free(second) is False

    def test_first_lesson_of_second_topic_is_not_free(self):
        first_topic_lesson = make_lesson_with_quiz()
        second_topic = TopicFactory(section=first_topic_lesson.topic.section, order=1)
        lesson = LessonFactory(topic=second_topic, order=0)
        assert is_lesson_free(lesson) is False

    def test_first_lesson_of_second_section_is_not_free(self):
        first_section_lesson = make_lesson_with_quiz()
        subject = first_section_lesson.topic.section.subject
        second_section = SectionFactory(subject=subject, order=1)
        topic = TopicFactory(section=second_section, order=0)
        lesson = LessonFactory(topic=topic, order=0)
        assert is_lesson_free(lesson) is False


# ─── has_subscription_access ─────────────────────────────────────────────────
@pytest.mark.django_db
class TestHasSubscriptionAccess:
    def test_no_subscription_returns_false(self):
        user = UserFactory()
        subject = SubjectFactory()
        assert has_subscription_access(user, subject) is False

    def test_active_subscription_with_subject_in_tariff_returns_true(self):
        user = UserFactory()
        subject = SubjectFactory()
        tariff = TariffFactory(subjects=[subject])
        SubscriptionFactory(user=user, tariff=tariff)
        assert has_subscription_access(user, subject) is True

    def test_active_subscription_with_other_subject_returns_false(self):
        user = UserFactory()
        my_subject = SubjectFactory()
        other_subject = SubjectFactory()
        tariff = TariffFactory(subjects=[other_subject])
        SubscriptionFactory(user=user, tariff=tariff)
        assert has_subscription_access(user, my_subject) is False

    def test_expired_subscription_returns_false(self):
        user = UserFactory()
        subject = SubjectFactory()
        tariff = TariffFactory(subjects=[subject])
        ExpiredSubscriptionFactory(user=user, tariff=tariff)
        assert has_subscription_access(user, subject) is False

    def test_tariff_without_learning_returns_false(self):
        user = UserFactory()
        subject = SubjectFactory()
        tariff = TariffFactory(subjects=[subject], has_learning=False)
        SubscriptionFactory(user=user, tariff=tariff)
        assert has_subscription_access(user, subject) is False


# ─── previous_lesson ─────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPreviousLesson:
    def test_first_lesson_has_no_previous(self):
        lesson = make_lesson_with_quiz()
        assert previous_lesson(lesson) is None

    def test_second_lesson_returns_first(self):
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        assert previous_lesson(second) == first

    def test_first_of_next_topic_returns_last_of_previous(self):
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        next_topic = TopicFactory(section=first.topic.section, order=1)
        first_of_next_topic = LessonFactory(topic=next_topic, order=0)
        assert previous_lesson(first_of_next_topic) == second

    def test_unpublished_lessons_skipped(self):
        first = make_lesson_with_quiz()
        unpublished = LessonFactory(
            topic=first.topic, order=1, content_status=Lesson.ContentStatus.NEW
        )
        third = LessonFactory(topic=first.topic, order=2)
        # third's previous должен быть first (минуя unpublished)
        assert previous_lesson(third) == first
        # А вот для unpublished previous всё равно first
        assert previous_lesson(unpublished) == first


# ─── is_lesson_unlocked_for_user / lock_reason ───────────────────────────────
@pytest.mark.django_db
class TestUnlockLogic:
    def test_first_lesson_always_unlocked(self):
        user = UserFactory()
        lesson = make_lesson_with_quiz()
        assert is_lesson_unlocked_for_user(user, lesson) is True
        assert lock_reason_for_lesson(user, lesson) is None

    def test_second_lesson_locked_without_completion(self):
        user = UserFactory()
        first = make_lesson_with_quiz()
        second = LessonFactory(topic=first.topic, order=1)
        assert is_lesson_unlocked_for_user(user, second) is False
        # Второй урок не первый-в-предмете (paywall) И первый не пройден.
        # Paywall срабатывает первым в lock_reason.
        assert lock_reason_for_lesson(user, second) == LOCK_REASON_NO_SUBSCRIPTION

    def test_second_lesson_with_subscription_locked_until_first_passed(self):
        user = UserFactory()
        first = make_lesson_with_quiz()
        subject = first.topic.section.subject
        tariff = TariffFactory(subjects=[subject])
        SubscriptionFactory(user=user, tariff=tariff)
        second = LessonFactory(topic=first.topic, order=1)

        assert is_lesson_unlocked_for_user(user, second) is False
        assert lock_reason_for_lesson(user, second) == LOCK_REASON_PREVIOUS_NOT_COMPLETED

    def test_second_lesson_unlocks_after_first_gets_one_star(self):
        user = UserFactory()
        first = make_lesson_with_quiz()
        subject = first.topic.section.subject
        tariff = TariffFactory(subjects=[subject])
        SubscriptionFactory(user=user, tariff=tariff)
        second = LessonFactory(topic=first.topic, order=1)

        LessonProgress.objects.create(user=user, lesson=first, stars=1)

        assert is_lesson_unlocked_for_user(user, second) is True
        assert lock_reason_for_lesson(user, second) is None

    def test_first_lesson_remains_unlocked_when_unpublished(self):
        """Первый урок с content_status=NEW всё равно заблокирован."""
        user = UserFactory()
        lesson = make_lesson_with_quiz()
        lesson.content_status = Lesson.ContentStatus.NEW
        lesson.save()
        assert is_lesson_unlocked_for_user(user, lesson) is False
        assert lock_reason_for_lesson(user, lesson) == LOCK_REASON_UNPUBLISHED

    def test_zero_stars_does_not_unlock_next(self):
        """Если ученик набрал 0 звёзд (<60%) — следующий урок остаётся заблокированным."""
        user = UserFactory()
        first = make_lesson_with_quiz()
        subject = first.topic.section.subject
        SubscriptionFactory(user=user, tariff=TariffFactory(subjects=[subject]))
        second = LessonFactory(topic=first.topic, order=1)

        LessonProgress.objects.create(user=user, lesson=first, stars=0)

        assert is_lesson_unlocked_for_user(user, second) is False
        assert lock_reason_for_lesson(user, second) == LOCK_REASON_PREVIOUS_NOT_COMPLETED
