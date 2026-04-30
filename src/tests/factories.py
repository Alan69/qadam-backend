"""factory_boy фабрики для тестов модуля обучения."""

from __future__ import annotations

from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.learning.models import (
    Lesson,
    Quiz,
    QuizQuestion,
    Section,
    Subject,
    Topic,
)
from apps.payments.models import Payment, Subscription, Tariff
from apps.profiles.models import StudentProfile


# ─── accounts ────────────────────────────────────────────────────────────────
class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    phone = factory.Sequence(lambda n: f"+7700{n:07d}")
    role = User.Role.STUDENT
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "StrongPass123!")
        user = model_class.objects.create_user(password=password, **kwargs)
        return user


class CuratorFactory(UserFactory):
    role = User.Role.CURATOR


# ─── profiles ────────────────────────────────────────────────────────────────
class StudentProfileFactory(DjangoModelFactory):
    class Meta:
        model = StudentProfile

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name", locale="ru_RU")
    parent_phone = factory.Sequence(lambda n: f"+7701{n:07d}")
    grade = 11
    learning_language = StudentProfile.Language.RUSSIAN


# ─── learning ────────────────────────────────────────────────────────────────
class SubjectFactory(DjangoModelFactory):
    class Meta:
        model = Subject

    name = factory.Sequence(lambda n: f"Предмет {n}")
    description = "Тестовый предмет"


class SectionFactory(DjangoModelFactory):
    class Meta:
        model = Section

    subject = factory.SubFactory(SubjectFactory)
    name = factory.Sequence(lambda n: f"Раздел {n}")
    order = 0


class TopicFactory(DjangoModelFactory):
    class Meta:
        model = Topic

    section = factory.SubFactory(SectionFactory)
    name = factory.Sequence(lambda n: f"Тема {n}")
    order = 0


class LessonFactory(DjangoModelFactory):
    class Meta:
        model = Lesson

    topic = factory.SubFactory(TopicFactory)
    title = factory.Sequence(lambda n: f"Урок {n}")
    video_url = "https://example.com/video.mp4"
    theory = "Теоретический материал"
    order = 0
    content_status = Lesson.ContentStatus.PUBLISHED


class QuizFactory(DjangoModelFactory):
    class Meta:
        model = Quiz

    lesson = factory.SubFactory(LessonFactory)


class QuizQuestionFactory(DjangoModelFactory):
    class Meta:
        model = QuizQuestion

    quiz = factory.SubFactory(QuizFactory)
    type = QuizQuestion.QuestionType.SINGLE
    text = factory.Sequence(lambda n: f"Вопрос {n}: что такое 2+2?")
    options = ["3", "4", "5", "6"]
    correct_answers = ["4"]
    order = factory.Sequence(lambda n: n)


def make_lesson_with_quiz(
    *,
    subject: Subject | None = None,
    section_order: int = 0,
    topic_order: int = 0,
    lesson_order: int = 0,
    questions: int = 5,
    content_status: str = Lesson.ContentStatus.PUBLISHED,
) -> Lesson:
    """Удобная фабрика: создаёт целую цепочку Subject → Section → Topic → Lesson + Quiz + N вопросов."""
    if subject is None:
        subject = SubjectFactory()
    section = SectionFactory(subject=subject, order=section_order)
    topic = TopicFactory(section=section, order=topic_order)
    lesson = LessonFactory(
        topic=topic,
        order=lesson_order,
        content_status=content_status,
    )
    quiz = QuizFactory(lesson=lesson)
    for i in range(questions):
        QuizQuestionFactory(quiz=quiz, order=i)
    return lesson


# ─── payments ────────────────────────────────────────────────────────────────
class TariffFactory(DjangoModelFactory):
    class Meta:
        model = Tariff
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Тариф {n}")
    price = 9990
    duration_days = 30
    has_learning = True
    has_testing = True
    has_ai_tutor = False
    is_active = True

    @factory.post_generation
    def subjects(self, create: bool, extracted, **kwargs) -> None:
        if not create:
            return
        if extracted:
            self.subjects.set(extracted)


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    tariff = factory.SubFactory(TariffFactory)
    status = Subscription.Status.ACTIVE
    source = Subscription.Source.SELF_PAYMENT
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))


class ExpiredSubscriptionFactory(SubscriptionFactory):
    expires_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=1))


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    user = factory.SubFactory(UserFactory)
    subscription = factory.SubFactory(SubscriptionFactory)
    amount = 9990
    method = Payment.Method.CARD
    status = Payment.Status.SUCCESS
    paid_at = factory.LazyFunction(timezone.now)
