"""Скелет ЕНТ-тестирования. ТЗ §7.

Отдельный пул вопросов от мини-тестов уроков (банк ЕНТ-вопросов имеет свой
жизненный цикл — импорт партиями, метки сложности).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class ENTQuestion(TimestampedModel):
    class QuestionType(models.TextChoices):
        SINGLE = "single_choice", "Один правильный"
        MULTI = "multi_choice", "Несколько правильных"
        MATCH = "match", "На соответствие"
        CONTEXT = "context", "Контекстное"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Лёгкий"
        MEDIUM = "medium", "Средний"
        HARD = "hard", "Сложный"

    subject = models.ForeignKey(
        "learning.Subject", on_delete=models.CASCADE, related_name="ent_questions"
    )
    type = models.CharField("тип", max_length=16, choices=QuestionType.choices)
    difficulty = models.CharField(
        "сложность", max_length=8, choices=Difficulty.choices, default=Difficulty.MEDIUM
    )
    text = models.TextField("текст")
    options = models.JSONField("варианты", default=list)
    correct_answers = models.JSONField("правильные ответы", default=list)
    explanation = models.TextField("объяснение", blank=True)
    related_lesson = models.ForeignKey(
        "learning.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ent_questions",
        help_text="Урок, к которому относится вопрос (для рекомендаций по работе над ошибками)",
    )

    class Meta:
        verbose_name = "Вопрос ЕНТ"
        verbose_name_plural = "Вопросы ЕНТ"
        indexes = [models.Index(fields=["subject", "difficulty"])]


class ENTTestSession(TimestampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "В процессе"
        FINISHED = "finished", "Завершён"
        EXPIRED = "expired", "По таймеру"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ent_sessions"
    )
    profile_subject_1 = models.ForeignKey(
        "learning.Subject",
        on_delete=models.PROTECT,
        related_name="as_first_profile_in_sessions",
    )
    profile_subject_2 = models.ForeignKey(
        "learning.Subject",
        on_delete=models.PROTECT,
        related_name="as_second_profile_in_sessions",
    )
    started_at = models.DateTimeField("начало", auto_now_add=True)
    finished_at = models.DateTimeField("конец", null=True, blank=True)
    total_score = models.PositiveIntegerField("итоговый балл", default=0)
    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.IN_PROGRESS
    )

    class Meta:
        verbose_name = "Сессия ЕНТ"
        verbose_name_plural = "Сессии ЕНТ"
        ordering = ("-started_at",)
        indexes = [models.Index(fields=["user", "-started_at"])]


class ENTSubjectResult(TimestampedModel):
    session = models.ForeignKey(
        ENTTestSession, on_delete=models.CASCADE, related_name="subject_results"
    )
    subject = models.ForeignKey(
        "learning.Subject", on_delete=models.PROTECT, related_name="ent_results"
    )
    score = models.PositiveIntegerField("балл", default=0)
    errors_count = models.PositiveIntegerField("ошибок", default=0)
    time_seconds = models.PositiveIntegerField("время (сек)", default=0)

    class Meta:
        verbose_name = "Результат по предмету"
        verbose_name_plural = "Результаты по предметам"
        unique_together = (("session", "subject"),)


class ENTAnswer(TimestampedModel):
    session = models.ForeignKey(
        ENTTestSession, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        ENTQuestion, on_delete=models.PROTECT, related_name="user_answers"
    )
    user_answer = models.JSONField("ответ ученика", default=list)
    is_correct = models.BooleanField("верно", default=False)
    time_spent_seconds = models.PositiveIntegerField("время (сек)", default=0)

    class Meta:
        verbose_name = "Ответ в ЕНТ"
        verbose_name_plural = "Ответы в ЕНТ"
        indexes = [models.Index(fields=["session", "question"])]
