"""Student profile + curator assignment history."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.accounts.validators import validate_phone
from apps.common.models import TimestampedModel


class StudentProfile(TimestampedModel):
    class Grade(models.IntegerChoices):
        TENTH = 10, "10"
        ELEVENTH = 11, "11"

    class Language(models.TextChoices):
        RUSSIAN = "ru", "Русский"
        KAZAKH = "kk", "Қазақ"

    class SalesStatus(models.TextChoices):
        NEW = "new", "Новый"
        IN_WORK = "in_work", "В работе"
        REGISTERED = "registered", "Оформил"
        PAID = "paid", "Оплатил"
        RENEWAL = "renewal", "На продление"
        REJECTED = "rejected", "Отказ"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        primary_key=True,
    )
    name = models.CharField("ФИО", max_length=128)
    parent_phone = models.CharField(
        "телефон родителя",
        max_length=16,
        validators=[validate_phone],
    )
    grade = models.IntegerField("класс", choices=Grade.choices)
    learning_language = models.CharField(
        "язык обучения", max_length=8, choices=Language.choices
    )
    target_score = models.PositiveIntegerField("целевой балл", null=True, blank=True)
    current_level = models.PositiveIntegerField("текущий уровень", default=0)

    region = models.ForeignKey(
        "universities.Region",
        on_delete=models.SET_NULL,
        related_name="student_profiles",
        null=True,
        blank=True,
    )
    city = models.ForeignKey(
        "universities.City",
        on_delete=models.SET_NULL,
        related_name="student_profiles",
        null=True,
        blank=True,
    )
    selected_subjects = models.ManyToManyField(
        "learning.Subject",
        related_name="interested_students",
        blank=True,
    )
    target_universities = models.ManyToManyField(
        "universities.University",
        related_name="aspiring_students",
        blank=True,
    )
    target_specialities = models.ManyToManyField(
        "universities.Speciality",
        related_name="aspiring_students",
        blank=True,
    )

    assigned_curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="curated_students",
        null=True,
        blank=True,
        limit_choices_to={"role": "curator"},
    )

    sales_status = models.CharField(
        "статус продаж",
        max_length=16,
        choices=SalesStatus.choices,
        default=SalesStatus.NEW,
        db_index=True,
    )

    class Meta:
        verbose_name = "Профиль ученика"
        verbose_name_plural = "Профили учеников"

    def __str__(self) -> str:
        return f"{self.name} ({self.user.phone})"


class CuratorAssignmentHistory(TimestampedModel):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="curator_history",
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_assignments",
        limit_choices_to={"role": "curator"},
    )
    assigned_at = models.DateTimeField("назначен", auto_now_add=True)
    unassigned_at = models.DateTimeField("снят", null=True, blank=True)

    class Meta:
        verbose_name = "Назначение куратора"
        verbose_name_plural = "Назначения кураторов"
        ordering = ("-assigned_at",)
        indexes = [models.Index(fields=["student", "-assigned_at"])]

    def __str__(self) -> str:
        active = " (активен)" if self.unassigned_at is None else ""
        return f"{self.student} ← {self.curator}{active}"
