"""DRF serializers для auth-эндпоинтов."""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


# ─── Запросные сериалайзеры ──────────────────────────────────────────────────
class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    code = serializers.CharField(min_length=4, max_length=10)


class CompleteRegistrationSerializer(serializers.Serializer):
    verification_token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=128)
    parent_phone = serializers.CharField(max_length=32)
    grade = serializers.IntegerField(min_value=10, max_value=11)
    learning_language = serializers.ChoiceField(choices=["ru", "kk"])

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)


# ─── Ответные сериалайзеры ───────────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "role", "is_active", "created_at")
        read_only_fields = fields


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class VerificationTokenSerializer(serializers.Serializer):
    verification_token = serializers.CharField()


class ResetTokenSerializer(serializers.Serializer):
    reset_token = serializers.CharField()


class OTPSentSerializer(serializers.Serializer):
    expires_in = serializers.IntegerField()
