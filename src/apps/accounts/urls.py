"""URL routing для /api/v1/auth/."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Регистрация
    path("register/init/", views.RegisterInitView.as_view(), name="register-init"),
    path("register/verify/", views.RegisterVerifyView.as_view(), name="register-verify"),
    path(
        "register/complete/",
        views.RegisterCompleteView.as_view(),
        name="register-complete",
    ),
    # Логин
    path("login/", views.LoginView.as_view(), name="login"),
    # JWT
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("logout-all/", views.LogoutAllView.as_view(), name="logout-all"),
    path("sessions/", views.SessionsView.as_view(), name="sessions"),
    # Восстановление пароля
    path(
        "password-reset/init/",
        views.PasswordResetInitView.as_view(),
        name="password-reset-init",
    ),
    path(
        "password-reset/verify/",
        views.PasswordResetVerifyView.as_view(),
        name="password-reset-verify",
    ),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    # Текущий пользователь
    path("me/", views.MeView.as_view(), name="me"),
]
