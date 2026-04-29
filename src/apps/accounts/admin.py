"""Django Admin для пользователей и login-событий."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserChangeForm, UserCreationForm
from .models import LoginEvent, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    ordering = ("-created_at",)
    list_display = ("phone", "role", "is_active", "is_staff", "created_at")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("phone",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Роль и доступ"), {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        (_("Permissions"), {"fields": ("groups", "user_permissions")}),
        (_("Даты"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("last_login", "created_at", "updated_at")
    filter_horizontal = ("groups", "user_permissions")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("phone", "success", "failure_reason", "ip_address", "created_at")
    list_filter = ("success", "failure_reason")
    search_fields = ("phone", "ip_address")
    readonly_fields = (
        "user",
        "phone",
        "ip_address",
        "user_agent",
        "success",
        "failure_reason",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
