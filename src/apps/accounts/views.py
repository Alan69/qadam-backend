"""Auth API views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import QadamAPIError

from .serializers import (
    CompleteRegistrationSerializer,
    LoginSerializer,
    LogoutSerializer,
    OTPSentSerializer,
    PasswordResetConfirmSerializer,
    PhoneSerializer,
    RefreshSerializer,
    ResetTokenSerializer,
    TokenPairSerializer,
    UserSerializer,
    VerificationTokenSerializer,
    VerifyOTPSerializer,
)
from .services.jwt import blacklist_all_tokens, issue_token_pair
from .services.login import authenticate_and_login
from .services.password_reset import (
    confirm_password_reset,
    request_password_reset,
    verify_password_reset_code,
)
from .services.registration import (
    complete_registration,
    request_registration_code,
    verify_registration_code,
)


class _OpenView(APIView):
    """Базовый класс для public auth-эндпоинтов.

    `permission_classes = (AllowAny,)` — любой может звонить.
    `authentication_classes` оставляем дефолтное (JWTAuthentication), чтобы DRF
    корректно отдавал 401 (а не 403) при ошибках вроде blacklisted refresh —
    иначе `get_authenticate_header()` возвращает None и DRF подменяет статус.
    """

    permission_classes = (AllowAny,)


# ─── Регистрация ─────────────────────────────────────────────────────────────
class RegisterInitView(_OpenView):
    @extend_schema(
        request=PhoneSerializer,
        responses={200: OTPSentSerializer},
        operation_id="auth_register_init",
        description="Шаг 1: отправить OTP-код на указанный телефон.",
    )
    def post(self, request: Request) -> Response:
        s = PhoneSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ttl = request_registration_code(raw_phone=s.validated_data["phone"])
        return Response({"expires_in": ttl})


class RegisterVerifyView(_OpenView):
    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: VerificationTokenSerializer},
        operation_id="auth_register_verify",
        description="Шаг 2: проверить OTP-код, получить verification_token.",
    )
    def post(self, request: Request) -> Response:
        s = VerifyOTPSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        token = verify_registration_code(
            raw_phone=s.validated_data["phone"],
            code=s.validated_data["code"],
        )
        return Response({"verification_token": token})


class RegisterCompleteView(_OpenView):
    @extend_schema(
        request=CompleteRegistrationSerializer,
        responses={201: TokenPairSerializer},
        operation_id="auth_register_complete",
        description="Шаг 3: создать пользователя, выдать JWT pair.",
    )
    def post(self, request: Request) -> Response:
        s = CompleteRegistrationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = complete_registration(**s.validated_data)
        tokens = issue_token_pair(user)
        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ─── Логин ───────────────────────────────────────────────────────────────────
class LoginView(_OpenView):
    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenPairSerializer},
        operation_id="auth_login",
    )
    def post(self, request: Request) -> Response:
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = authenticate_and_login(
            raw_phone=s.validated_data["phone"],
            password=s.validated_data["password"],
            request=request,
        )
        tokens = issue_token_pair(user)
        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": UserSerializer(user).data,
            }
        )


# ─── JWT operations ──────────────────────────────────────────────────────────
class RefreshView(_OpenView):
    @extend_schema(
        request=RefreshSerializer,
        responses={200: TokenPairSerializer(partial=True)},
        operation_id="auth_refresh",
    )
    def post(self, request: Request) -> Response:
        s = RefreshSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            refresh = RefreshToken(s.validated_data["refresh"])
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc

        access = str(refresh.access_token)
        # ROTATE_REFRESH_TOKENS=True + BLACKLIST_AFTER_ROTATION=True:
        # blacklist старый refresh, выдаём новый (логика повторяет
        # simplejwt.TokenRefreshSerializer).
        try:
            refresh.blacklist()
        except AttributeError:
            pass
        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()
        return Response({"access": access, "refresh": str(refresh)})


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request=LogoutSerializer,
        responses={204: None},
        operation_id="auth_logout",
    )
    def post(self, request: Request) -> Response:
        s = LogoutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            RefreshToken(s.validated_data["refresh"]).blacklist()
        except TokenError as exc:
            raise QadamAPIError(
                message="Refresh-токен невалиден или уже отозван.",
                code="INVALID_REFRESH_TOKEN",
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={204: None},
        operation_id="auth_logout_all",
        description="Отозвать все refresh-токены пользователя (выйти со всех устройств).",
    )
    def post(self, request: Request) -> Response:
        blacklist_all_tokens(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionsView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="auth_sessions",
        description="Список активных refresh-токенов (outstanding и не в blacklist).",
    )
    def get(self, request: Request) -> Response:
        tokens = (
            OutstandingToken.objects.filter(user=request.user)
            .exclude(blacklistedtoken__isnull=False)
            .order_by("-created_at")
            .values("jti", "created_at", "expires_at")
        )
        return Response(list(tokens))


# ─── Восстановление пароля ───────────────────────────────────────────────────
class PasswordResetInitView(_OpenView):
    @extend_schema(
        request=PhoneSerializer,
        responses={200: OTPSentSerializer},
        operation_id="auth_password_reset_init",
    )
    def post(self, request: Request) -> Response:
        s = PhoneSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ttl = request_password_reset(raw_phone=s.validated_data["phone"])
        return Response({"expires_in": ttl})


class PasswordResetVerifyView(_OpenView):
    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: ResetTokenSerializer},
        operation_id="auth_password_reset_verify",
    )
    def post(self, request: Request) -> Response:
        s = VerifyOTPSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        token = verify_password_reset_code(
            raw_phone=s.validated_data["phone"],
            code=s.validated_data["code"],
        )
        return Response({"reset_token": token})


class PasswordResetConfirmView(_OpenView):
    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={204: None},
        operation_id="auth_password_reset_confirm",
    )
    def post(self, request: Request) -> Response:
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        confirm_password_reset(
            reset_token=s.validated_data["reset_token"],
            new_password=s.validated_data["new_password"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Текущий пользователь ────────────────────────────────────────────────────
class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={200: UserSerializer},
        operation_id="auth_me",
    )
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)
