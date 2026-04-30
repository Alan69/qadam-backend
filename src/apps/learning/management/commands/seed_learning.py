"""Management-команда для наполнения БД демо-контентом.

Создаёт 2 предмета (Математика, Физика), по 1 разделу с 1 темой и 3 уроками,
у каждого урока 5 вопросов в мини-тесте. Также один тариф «Стандарт» с обоими
предметами и одного куратора.

Использование:
    docker compose exec web python manage.py seed_learning
    docker compose exec web python manage.py seed_learning --reset
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.learning.models import (
    Lesson,
    Quiz,
    QuizQuestion,
    Section,
    Subject,
    Topic,
)
from apps.payments.models import Tariff


class Command(BaseCommand):
    help = "Создать демо-контент для модуля обучения (2 предмета, 6 уроков, тариф)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить существующий контент перед созданием.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        if options["reset"]:
            self.stdout.write("Удаляю существующий learning-контент...")
            Subject.objects.all().delete()
            Tariff.objects.all().delete()

        # Куратор
        curator, _ = User.objects.get_or_create(
            phone="+77770000001",
            defaults={"role": User.Role.CURATOR, "is_active": True},
        )
        if not curator.has_usable_password():
            curator.set_password("CuratorPass123!")
            curator.save()

        # Предметы
        math = self._create_subject(
            name="Математика",
            description="Алгебра, геометрия, функции — подготовка к ЕНТ",
            icon="math",
        )
        physics = self._create_subject(
            name="Физика",
            description="Механика, термодинамика, электричество",
            icon="physics",
        )

        for subject in (math, physics):
            self._create_subject_content(subject)

        # Тариф
        tariff = Tariff.objects.create(
            name="Стандарт",
            price=9990,
            duration_days=30,
            has_learning=True,
            has_testing=True,
            has_ai_tutor=False,
            is_active=True,
        )
        tariff.subjects.set([math, physics])

        self.stdout.write(self.style.SUCCESS("✓ Demo learning content создан."))
        self.stdout.write(f"  Предметы: {math.name}, {physics.name}")
        self.stdout.write(f"  Уроков всего: {Lesson.objects.count()}")
        self.stdout.write(f"  Вопросов всего: {QuizQuestion.objects.count()}")
        self.stdout.write(f"  Тариф: {tariff.name} ({tariff.price} KZT)")
        self.stdout.write(f"  Куратор: {curator.phone}")

    # ─── helpers ─────────────────────────────────────────────────────────────
    def _create_subject(self, *, name: str, description: str, icon: str) -> Subject:
        return Subject.objects.create(name=name, description=description, icon=icon)

    def _create_subject_content(self, subject: Subject) -> None:
        section = Section.objects.create(subject=subject, name="Раздел 1", order=0)
        topic = Topic.objects.create(section=section, name="Тема 1", order=0)
        for i in range(3):
            lesson = Lesson.objects.create(
                topic=topic,
                title=f"{subject.name}: урок {i + 1}",
                video_url="https://example.com/video.mp4",
                theory=f"Теория для урока {i + 1} ({subject.name}).",
                order=i,
                content_status=Lesson.ContentStatus.PUBLISHED,
            )
            quiz = Quiz.objects.create(lesson=lesson)
            for j in range(5):
                QuizQuestion.objects.create(
                    quiz=quiz,
                    type=QuizQuestion.QuestionType.SINGLE,
                    text=f"Вопрос {j + 1} для урока {i + 1} ({subject.name})?",
                    options=["A", "B", "C", "D"],
                    correct_answers=["B"],
                    order=j,
                )
