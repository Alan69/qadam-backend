"""ВУЗы / Регион → Город → Университет → Специальность.

Иерархия из ТЗ §8. На текущем этапе — только модели + admin, без эндпоинтов.
Поля name/description мультиязычны (см. translation.py).
"""
from __future__ import annotations

from django.db import models

from apps.common.models import TimestampedModel


class Region(TimestampedModel):
    name = models.CharField("название", max_length=128)

    class Meta:
        verbose_name = "Область"
        verbose_name_plural = "Области"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class City(TimestampedModel):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="cities")
    name = models.CharField("название", max_length=128)

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        unique_together = (("region", "name"),)
        ordering = ("region__name", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.region.name})"


class University(TimestampedModel):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="universities")
    name = models.CharField("название", max_length=256)
    description = models.TextField("описание", blank=True)
    website = models.URLField("сайт", blank=True)

    class Meta:
        verbose_name = "ВУЗ"
        verbose_name_plural = "ВУЗы"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Speciality(TimestampedModel):
    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="specialities"
    )
    name = models.CharField("название", max_length=256)
    code = models.CharField("код", max_length=32, blank=True)
    description = models.TextField("описание", blank=True)
    threshold_score = models.PositiveIntegerField(
        "проходной балл (прошлый год)", null=True, blank=True
    )
    required_subjects = models.ManyToManyField(
        "learning.Subject",
        related_name="for_specialities",
        blank=True,
    )

    class Meta:
        verbose_name = "Специальность"
        verbose_name_plural = "Специальности"
        ordering = ("university__name", "name")
        indexes = [models.Index(fields=["threshold_score"])]

    def __str__(self) -> str:
        return f"{self.name} — {self.university.name}"
