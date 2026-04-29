from django.contrib import admin

from .models import Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "template", "channel", "status", "sent_at", "read_at")
    list_filter = ("channel", "status")
    search_fields = ("user__phone", "template__code")
    autocomplete_fields = ("user", "template")
    date_hierarchy = "created_at"
