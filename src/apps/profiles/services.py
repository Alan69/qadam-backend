"""Бизнес-операции над профилями."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import CuratorAssignmentHistory, StudentProfile


@transaction.atomic
def create_student_profile(
    *,
    user: User,
    name: str,
    parent_phone: str,
    grade: int,
    learning_language: str,
) -> StudentProfile:
    profile = StudentProfile.objects.create(
        user=user,
        name=name,
        parent_phone=parent_phone,
        grade=grade,
        learning_language=learning_language,
    )
    curator = pick_curator()
    if curator is not None:
        _attach_curator(profile, curator)
    return profile


def pick_curator() -> User | None:
    """Round-robin: куратор с минимальным числом учеников.

    Если кураторов нет — возвращает None (регистрация всё равно проходит,
    куратора потом назначит супер-админ через admin endpoint).
    """
    from django.db.models import Count

    return (
        User.objects.filter(role=User.Role.CURATOR, is_active=True)
        .annotate(load=Count("curated_students"))
        .order_by("load", "id")
        .first()
    )


@transaction.atomic
def assign_curator(*, student: User, curator: User) -> None:
    """Сменить куратора у студента и записать в историю."""
    profile = student.student_profile
    if profile.assigned_curator_id == curator.id:
        return

    if profile.assigned_curator_id is not None:
        CuratorAssignmentHistory.objects.filter(
            student=profile,
            curator_id=profile.assigned_curator_id,
            unassigned_at__isnull=True,
        ).update(unassigned_at=timezone.now())

    _attach_curator(profile, curator)


def _attach_curator(profile: StudentProfile, curator: User) -> None:
    profile.assigned_curator = curator
    profile.save(update_fields=["assigned_curator", "updated_at"])
    CuratorAssignmentHistory.objects.create(student=profile, curator=curator)
