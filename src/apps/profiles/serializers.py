"""Serializers для profile API."""
from __future__ import annotations

from rest_framework import serializers

from .models import StudentProfile


class CuratorContactSerializer(serializers.Serializer):
    """Серилайзер для GET /profile/curator/."""

    id = serializers.IntegerField()
    name = serializers.CharField(allow_blank=True)
    phone = serializers.CharField()
    whatsapp = serializers.CharField()


class StudentProfileReadSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="user.phone", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = StudentProfile
        fields = (
            "phone",
            "role",
            "name",
            "parent_phone",
            "grade",
            "learning_language",
            "target_score",
            "current_level",
            "region",
            "city",
            "selected_subjects",
            "target_universities",
            "target_specialities",
            "sales_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "phone",
            "role",
            "parent_phone",  # ТЗ §2.4 — только через админа
            "current_level",
            "sales_status",
            "created_at",
            "updated_at",
        )


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """ТЗ §2.4: ученик может редактировать только эти поля."""

    class Meta:
        model = StudentProfile
        fields = (
            "name",
            "learning_language",
            "target_score",
            "selected_subjects",
            "target_universities",
            "target_specialities",
            "region",
            "city",
        )


class DashboardSerializer(serializers.Serializer):
    """Агрегированный дашборд. На фундаменте возвращает заготовленную структуру.

    На следующих этапах сюда подключатся данные из learning, testing,
    gamification, payments.
    """

    progress = serializers.DictField()
    results = serializers.DictField()
    analytics = serializers.DictField()
    league = serializers.DictField()
    stars = serializers.DictField()
    subscription = serializers.DictField()
