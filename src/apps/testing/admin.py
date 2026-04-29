from django.contrib import admin

from .models import ENTAnswer, ENTQuestion, ENTSubjectResult, ENTTestSession


@admin.register(ENTQuestion)
class ENTQuestionAdmin(admin.ModelAdmin):
    list_display = ("subject", "type", "difficulty", "related_lesson")
    list_filter = ("subject", "difficulty", "type")
    search_fields = ("text",)
    autocomplete_fields = ("subject", "related_lesson")


class ENTSubjectResultInline(admin.TabularInline):
    model = ENTSubjectResult
    extra = 0


@admin.register(ENTTestSession)
class ENTTestSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "total_score", "started_at", "finished_at")
    list_filter = ("status",)
    search_fields = ("user__phone",)
    autocomplete_fields = ("user", "profile_subject_1", "profile_subject_2")
    inlines = (ENTSubjectResultInline,)
    date_hierarchy = "started_at"


@admin.register(ENTSubjectResult)
class ENTSubjectResultAdmin(admin.ModelAdmin):
    list_display = ("session", "subject", "score", "errors_count", "time_seconds")
    autocomplete_fields = ("session", "subject")


@admin.register(ENTAnswer)
class ENTAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "is_correct", "time_spent_seconds")
    list_filter = ("is_correct",)
    autocomplete_fields = ("session", "question")
