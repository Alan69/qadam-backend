"""Скелет геймификации. ТЗ §4.

Звёзды (за уроки), лиги (Bronze/Silver/Gold), персонаж + предметы из сундуков,
турниры, кланы, друзья, челленджи. Бизнес-логика — на следующих этапах.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class League(TimestampedModel):
    class Code(models.TextChoices):
        BRONZE = "bronze", "Бронза"
        SILVER = "silver", "Серебро"
        GOLD = "gold", "Золото"

    code = models.CharField("код", max_length=8, choices=Code.choices, unique=True)
    min_stars = models.PositiveIntegerField("минимум звёзд")
    max_stars = models.PositiveIntegerField("максимум звёзд")

    class Meta:
        verbose_name = "Лига"
        verbose_name_plural = "Лиги"
        ordering = ("min_stars",)

    def __str__(self) -> str:
        return self.get_code_display()


class UserLeague(TimestampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="league_status"
    )
    current_league = models.ForeignKey(League, on_delete=models.PROTECT, related_name="members")

    class Meta:
        verbose_name = "Лига пользователя"
        verbose_name_plural = "Лиги пользователей"


class Star(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stars"
    )
    lesson = models.ForeignKey(
        "learning.Lesson", on_delete=models.CASCADE, related_name="awarded_stars"
    )
    count = models.PositiveSmallIntegerField("кол-во (1-3)")
    earned_at = models.DateTimeField("получено", auto_now_add=True)

    class Meta:
        verbose_name = "Звезда"
        verbose_name_plural = "Звёзды"
        unique_together = (("user", "lesson"),)
        indexes = [models.Index(fields=["user", "-earned_at"])]


class AvatarItem(TimestampedModel):
    class Type(models.TextChoices):
        CLOTHING = "clothing", "Одежда"
        ACCESSORY = "accessory", "Аксессуар"
        ARMOR = "armor", "Броня"
        WEAPON = "weapon", "Оружие"

    class Rarity(models.TextChoices):
        COMMON = "common", "Базовый"
        IMPROVED = "improved", "Улучшенный"
        RARE = "rare", "Редкий"

    name = models.CharField("название", max_length=128)
    type = models.CharField("тип", max_length=16, choices=Type.choices)
    rarity = models.CharField("редкость", max_length=16, choices=Rarity.choices)
    image_url = models.URLField("картинка", blank=True)
    required_league = models.ForeignKey(
        League,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unlockable_items",
    )

    class Meta:
        verbose_name = "Предмет аватара"
        verbose_name_plural = "Предметы аватара"


class UserAvatar(TimestampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="avatar"
    )
    equipped_items = models.ManyToManyField(AvatarItem, blank=True, related_name="equipped_by")

    class Meta:
        verbose_name = "Аватар пользователя"
        verbose_name_plural = "Аватары пользователей"


class Chest(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chests"
    )
    contained_items = models.ManyToManyField(AvatarItem, blank=True)
    opened_at = models.DateTimeField("открыт", null=True, blank=True)

    class Meta:
        verbose_name = "Сундук"
        verbose_name_plural = "Сундуки"


class Tournament(TimestampedModel):
    class Type(models.TextChoices):
        WEEKLY = "weekly", "Еженедельный"
        EVENT = "event", "Событие"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        ACTIVE = "active", "Активный"
        FINISHED = "finished", "Завершён"

    type = models.CharField("тип", max_length=16, choices=Type.choices)
    status = models.CharField("статус", max_length=16, choices=Status.choices)
    starts_at = models.DateTimeField("начало")
    ends_at = models.DateTimeField("конец")

    class Meta:
        verbose_name = "Турнир"
        verbose_name_plural = "Турниры"
        ordering = ("-starts_at",)


class TournamentParticipant(TimestampedModel):
    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tournament_entries",
    )
    score = models.PositiveIntegerField("счёт", default=0)
    position = models.PositiveIntegerField("позиция", null=True, blank=True)

    class Meta:
        verbose_name = "Участник турнира"
        verbose_name_plural = "Участники турниров"
        unique_together = (("tournament", "user"),)


class Clan(TimestampedModel):
    name = models.CharField("название", max_length=64, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_clans"
    )
    rating = models.PositiveIntegerField("рейтинг", default=0)

    class Meta:
        verbose_name = "Клан"
        verbose_name_plural = "Кланы"
        ordering = ("-rating",)


class ClanMember(TimestampedModel):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clan_membership"
    )
    joined_at = models.DateTimeField("вступил", auto_now_add=True)

    class Meta:
        verbose_name = "Участник клана"
        verbose_name_plural = "Участники кланов"
        unique_together = (("clan", "user"),)


class ClanBattle(TimestampedModel):
    class Format(models.TextChoices):
        THREE = "3v3", "3 vs 3"
        FIVE = "5v5", "5 vs 5"
        TEN = "10v10", "10 vs 10"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Запланирована"
        IN_PROGRESS = "in_progress", "В процессе"
        FINISHED = "finished", "Завершена"

    clan_a = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="battles_as_a")
    clan_b = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="battles_as_b")
    format = models.CharField("формат", max_length=8, choices=Format.choices)
    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )
    winner = models.ForeignKey(
        Clan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="battles_won",
    )
    started_at = models.DateTimeField("начало", null=True, blank=True)

    class Meta:
        verbose_name = "Битва кланов"
        verbose_name_plural = "Битвы кланов"


class Friendship(TimestampedModel):
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_as_a"
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_as_b"
    )

    class Meta:
        verbose_name = "Дружба"
        verbose_name_plural = "Дружбы"
        unique_together = (("user_a", "user_b"),)


class Challenge(TimestampedModel):
    class Scope(models.TextChoices):
        GLOBAL = "global", "Глобальный"
        CLAN = "clan", "Клан"
        USER = "user", "Личный"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="challenges"
    )
    title = models.CharField("название", max_length=256)
    description = models.TextField("описание", blank=True)
    target_metric = models.CharField(
        "метрика", max_length=64, help_text="напр. lessons_completed, stars_earned, tests_passed"
    )
    target_value = models.PositiveIntegerField("целевое значение")
    deadline = models.DateTimeField("дедлайн", null=True, blank=True)
    scope = models.CharField("область", max_length=16, choices=Scope.choices)

    class Meta:
        verbose_name = "Челлендж"
        verbose_name_plural = "Челленджи"


class ChallengeParticipant(TimestampedModel):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_entries",
    )
    progress = models.PositiveIntegerField("прогресс", default=0)
    completed_at = models.DateTimeField("завершено", null=True, blank=True)

    class Meta:
        verbose_name = "Участник челленджа"
        verbose_name_plural = "Участники челленджей"
        unique_together = (("challenge", "user"),)
