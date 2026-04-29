from django.contrib import admin

from .models import (
    Class,
    Lesson,
    LessonProgress,
    PracticeTask,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    Section,
    Subject,
    Topic,
)


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("number",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "order")
    list_filter = ("subject",)
    search_fields = ("name",)
    autocomplete_fields = ("subject",)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "order")
    list_filter = ("section__subject",)
    search_fields = ("name",)
    autocomplete_fields = ("section",)


class PracticeTaskInline(admin.TabularInline):
    model = PracticeTask
    extra = 0


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "order", "content_status")
    list_filter = ("content_status", "topic__section__subject")
    search_fields = ("title",)
    autocomplete_fields = ("topic",)
    inlines = (PracticeTaskInline,)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("lesson",)
    search_fields = ("lesson__title",)
    autocomplete_fields = ("lesson",)
    inlines = (QuizQuestionInline,)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "type", "order")
    list_filter = ("type",)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "stars", "best_quiz_score", "completed_at")
    list_filter = ("stars",)
    autocomplete_fields = ("user", "lesson")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "score", "started_at", "finished_at")
    autocomplete_fields = ("user", "quiz")


@admin.register(PracticeTask)
class PracticeTaskAdmin(admin.ModelAdmin):
    list_display = ("lesson", "type", "order")
    list_filter = ("type",)
    autocomplete_fields = ("lesson",)
