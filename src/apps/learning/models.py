"""Скелет модуля обучения. Иерархия: Класс → Предмет → Раздел → Тема (урок).

ТЗ §6. Бизнес-логика последовательного открытия уроков и звёзд — на следующих
этапах. Здесь только структура данных + content_status (для контент-менеджера).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class Class(TimestampedModel):
    number = models.PositiveSmallIntegerField("номер класса", unique=True)

    class Meta:
        verbose_name = "Класс"
        verbose_name_plural = "Классы"
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.number} класс"


class Subject(TimestampedModel):
    name = models.CharField("название", max_length=128)
    description = models.TextField("описание", blank=True)
    icon = models.CharField("иконка (slug или url)", max_length=128, blank=True)

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Section(TimestampedModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField("название", max_length=256)
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "Раздел"
        verbose_name_plural = "Разделы"
        ordering = ("subject__name", "order")

    def __str__(self) -> str:
        return f"{self.subject.name} / {self.name}"


class Topic(TimestampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField("название", max_length=256)
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "Тема"
        verbose_name_plural = "Темы"
        ordering = ("section__order", "order")

    def __str__(self) -> str:
        return self.name


class Lesson(TimestampedModel):
    class ContentStatus(models.TextChoices):
        NEW = "new", "Новый"
        REVIEW = "review", "Экспертиза"
        APPROVED = "approved", "Одобрен"
        PUBLISHED = "published", "Опубликован"

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField("название урока", max_length=256)
    video_url = models.URLField("видео", blank=True)
    theory = models.TextField("теория", blank=True)
    order = models.PositiveIntegerField("порядок", default=0)
    content_status = models.CharField(
        "статус", max_length=16, choices=ContentStatus.choices, default=ContentStatus.NEW
    )

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ("topic__section__order", "topic__order", "order")
        indexes = [models.Index(fields=["content_status"])]

    def __str__(self) -> str:
        return self.title


class PracticeTask(TimestampedModel):
    class TaskType(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Один правильный"
        MULTI_CHOICE = "multi_choice", "Несколько правильных"
        MATCH = "match", "На соответствие"
        CONTEXT = "context", "Контекстное"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="practice_tasks")
    type = models.CharField("тип", max_length=16, choices=TaskType.choices)
    payload = models.JSONField("данные задания", default=dict)
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "Практическое задание"
        verbose_name_plural = "Практические задания"
        ordering = ("lesson", "order")


class Quiz(TimestampedModel):
    """Мини-тест в конце урока (10 вопросов max, см. ТЗ §6.3)."""

    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="quiz")

    class Meta:
        verbose_name = "Мини-тест"
        verbose_name_plural = "Мини-тесты"

    def __str__(self) -> str:
        return f"Мини-тест: {self.lesson.title}"


class QuizQuestion(TimestampedModel):
    class QuestionType(models.TextChoices):
        SINGLE = "single_choice", "Один правильный"
        MULTI = "multi_choice", "Несколько правильных"
        MATCH = "match", "На соответствие"
        CONTEXT = "context", "Контекстное"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    type = models.CharField("тип", max_length=16, choices=QuestionType.choices)
    text = models.TextField("текст вопроса")
    options = models.JSONField("варианты ответа", default=list)
    correct_answers = models.JSONField("правильные ответы", default=list)
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "Вопрос мини-теста"
        verbose_name_plural = "Вопросы мини-теста"
        ordering = ("quiz", "order")


class LessonProgress(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress"
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    stars = models.PositiveSmallIntegerField("звёзды (0-3)", default=0)
    best_quiz_score = models.PositiveSmallIntegerField("лучший балл (%)", default=0)
    attempts_count = models.PositiveIntegerField("кол-во попыток", default=0)
    completed_at = models.DateTimeField("завершён", null=True, blank=True)
    last_attempt_at = models.DateTimeField("последняя попытка", null=True, blank=True)

    class Meta:
        verbose_name = "Прогресс по уроку"
        verbose_name_plural = "Прогресс по урокам"
        unique_together = (("user", "lesson"),)
        indexes = [models.Index(fields=["user", "-last_attempt_at"])]


class QuizAttempt(TimestampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "В процессе"
        FINISHED = "finished", "Завершена"
        EXPIRED = "expired", "Истекла"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(
        "статус",
        max_length=16,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        db_index=True,
    )
    score = models.PositiveSmallIntegerField("балл (%)", default=0)
    correct_count = models.PositiveSmallIntegerField("верных ответов", default=0)
    total_count = models.PositiveSmallIntegerField("всего вопросов", default=0)
    answers = models.JSONField(
        "ответы ученика",
        default=list,
        blank=True,
        help_text="Снапшот ответов: [{question_id, value, is_correct}, ...]",
    )
    started_at = models.DateTimeField("начало", auto_now_add=True)
    finished_at = models.DateTimeField("конец", null=True, blank=True)

    class Meta:
        verbose_name = "Попытка мини-теста"
        verbose_name_plural = "Попытки мини-тестов"
        ordering = ("-started_at",)
        indexes = [models.Index(fields=["user", "quiz", "-started_at"])]
        constraints = [
            # Только одна активная попытка на (ученик, мини-тест) одновременно.
            # Завершённые/просроченные не блокируют создание новой.
            models.UniqueConstraint(
                fields=["user", "quiz"],
                condition=models.Q(status="in_progress"),
                name="unique_active_quiz_attempt",
            ),
        ]
