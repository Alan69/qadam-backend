"""Кастомные формы для Django Admin (т.к. наш User использует phone, а не username)."""

from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class UserCreationForm(forms.ModelForm):
    """Форма создания пользователя в admin (Add)."""

    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("phone", "role")

    def clean_password2(self) -> str:
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Пароли не совпадают.")
        return p2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Форма редактирования: пароль не редактируется напрямую (только хеш)."""

    password = ReadOnlyPasswordHashField(
        label="Пароль (хеш)",
        help_text='Пароль хранится в хешированном виде. Изменить — через <a href="../password/">эту форму</a>.',
    )

    class Meta:
        model = User
        fields = (
            "phone",
            "password",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
