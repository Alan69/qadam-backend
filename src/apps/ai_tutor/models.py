"""Скелет AI Tutor. ТЗ §9.

Реальная интеграция с Gemini + Qdrant — на следующих этапах. Пока модели
для хранения диалогов и оценок качества.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class Conversation(TimestampedModel):
    class Mode(models.TextChoices):
        HELPER = "helper", "Помощник"
        LEARNING = "learning", "Обучение"
        GRANT_SEARCH = "grant_search", "Поиск гранта"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations"
    )
    lesson = models.ForeignKey(
        "learning.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_conversations",
    )
    mode = models.CharField("режим", max_length=16, choices=Mode.choices, default=Mode.HELPER)
    started_at = models.DateTimeField("начало", auto_now_add=True)

    class Meta:
        verbose_name = "Диалог с AI Tutor"
        verbose_name_plural = "Диалоги с AI Tutor"
        ordering = ("-started_at",)
        indexes = [models.Index(fields=["user", "-started_at"])]


class Message(TimestampedModel):
    class Role(models.TextChoices):
        USER = "user", "Пользователь"
        ASSISTANT = "assistant", "AI"

    class Helpful(models.TextChoices):
        POSITIVE = "positive", "Полезно"
        NEGATIVE = "negative", "Не нашёл ответ"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField("роль", max_length=16, choices=Role.choices)
    content = models.TextField("контент")
    helpful_rating = models.CharField(
        "оценка",
        max_length=16,
        choices=Helpful.choices,
        blank=True,
    )

    class Meta:
        verbose_name = "Сообщение AI Tutor"
        verbose_name_plural = "Сообщения AI Tutor"
        ordering = ("created_at",)
