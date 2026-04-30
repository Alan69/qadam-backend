"""URL routing для /api/v1/learning/."""

from django.urls import path

from . import views

app_name = "learning"

urlpatterns = [
    path("subjects/", views.SubjectListView.as_view(), name="subjects-list"),
    path(
        "subjects/<int:subject_id>/",
        views.SubjectDetailView.as_view(),
        name="subjects-detail",
    ),
    path(
        "lessons/<int:lesson_id>/",
        views.LessonDetailView.as_view(),
        name="lessons-detail",
    ),
    path(
        "lessons/<int:lesson_id>/quiz/start/",
        views.QuizStartView.as_view(),
        name="quiz-start",
    ),
    path(
        "lessons/<int:lesson_id>/attempts/",
        views.LessonAttemptsHistoryView.as_view(),
        name="lesson-attempts",
    ),
    path(
        "quiz-attempts/<int:attempt_id>/submit/",
        views.QuizSubmitView.as_view(),
        name="quiz-submit",
    ),
    path(
        "quiz-attempts/<int:attempt_id>/",
        views.QuizAttemptDetailView.as_view(),
        name="quiz-attempt-detail",
    ),
]
