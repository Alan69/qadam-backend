"""Helpers вокруг simplejwt — выдача JWT pair и logout-all."""
from __future__ import annotations

from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


def issue_token_pair(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def blacklist_all_tokens(user: User) -> int:
    """Заблеклистить все outstanding refresh-токены пользователя.

    Возвращает количество заблеклиcченных токенов.
    """
    tokens = OutstandingToken.objects.filter(user=user)
    count = 0
    for token in tokens:
        try:
            RefreshToken(token.token).blacklist()
            count += 1
        except Exception:
            # Уже в blacklist или невалиден — пропускаем.
            continue
    return count
