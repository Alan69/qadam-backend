from django.contrib import admin

from .models import Payment, Subscription, Tariff


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "is_active")
    list_filter = ("is_active", "has_learning", "has_testing", "has_ai_tutor")
    search_fields = ("name",)
    filter_horizontal = ("subjects",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "tariff", "status", "started_at", "expires_at", "source")
    list_filter = ("status", "source", "tariff")
    search_fields = ("user__phone", "tariff__name")
    autocomplete_fields = ("user", "tariff")
    date_hierarchy = "started_at"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "method", "status", "paid_at")
    list_filter = ("status", "method")
    search_fields = ("external_id", "user__phone")
    autocomplete_fields = ("user", "subscription")
    date_hierarchy = "created_at"
