from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "helpful_rating", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("user", "mode", "lesson", "started_at")
    list_filter = ("mode",)
    search_fields = ("user__phone", "lesson__title")
    autocomplete_fields = ("user", "lesson")
    inlines = (MessageInline,)
    date_hierarchy = "started_at"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "helpful_rating", "created_at")
    list_filter = ("role", "helpful_rating")
    autocomplete_fields = ("conversation",)
