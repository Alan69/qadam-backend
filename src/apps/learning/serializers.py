"""DRF serializers для learning API.

Большинство ответов формируются в `selectors.py` как готовые dict'ы — здесь
сериалайзеры используются как «схемы» для drf-spectacular (OpenAPI).
"""

from __future__ import annotations

from rest_framework import serializers


# ─── Hierarchy ───────────────────────────────────────────────────────────────
class SubjectListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    icon = serializers.CharField(allow_blank=True)
    is_locked = serializers.BooleanField()
    lessons_total = serializers.IntegerField()
    lessons_completed = serializers.IntegerField()
    stars_total = serializers.IntegerField()
    stars_max = serializers.IntegerField()
    progress_percent = serializers.IntegerField()


class LessonInListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    order = serializers.IntegerField()
    is_locked = serializers.BooleanField()
    lock_reason = serializers.CharField(allow_null=True)
    is_free = serializers.BooleanField()
    stars = serializers.IntegerField()
    best_score = serializers.IntegerField()
    completed_at = serializers.DateTimeField(allow_null=True)


class TopicInListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    order = serializers.IntegerField()
    lessons = LessonInListSerializer(many=True)


class SectionInListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    order = serializers.IntegerField()
    topics = TopicInListSerializer(many=True)


class SubjectDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    icon = serializers.CharField(allow_blank=True)
    is_locked = serializers.BooleanField()
    sections = SectionInListSerializer(many=True)


class LessonProgressSerializer(serializers.Serializer):
    stars = serializers.IntegerField()
    best_score = serializers.IntegerField()
    attempts_count = serializers.IntegerField()
    completed_at = serializers.DateTimeField(allow_null=True)


class _NamedRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    order = serializers.IntegerField(required=False)


class LessonDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    video_url = serializers.CharField(allow_blank=True)
    theory = serializers.CharField(allow_blank=True)
    topic = _NamedRefSerializer()
    section = _NamedRefSerializer()
    subject = _NamedRefSerializer()
    is_locked = serializers.BooleanField()
    lock_reason = serializers.CharField(allow_null=True)
    is_free = serializers.BooleanField()
    has_quiz = serializers.BooleanField()
    progress = LessonProgressSerializer()
    next_lesson_id = serializers.IntegerField(allow_null=True)


# ─── Quiz ────────────────────────────────────────────────────────────────────
class QuizQuestionPublicSerializer(serializers.Serializer):
    """Что отдаётся ученику на /start/. Без правильных ответов и объяснений."""

    id = serializers.IntegerField()
    type = serializers.CharField()
    text = serializers.CharField()
    options = serializers.ListField()
    order = serializers.IntegerField()


class QuizAttemptStartSerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField()
    started_at = serializers.DateTimeField()
    questions = QuizQuestionPublicSerializer(many=True)


class AnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    value = serializers.JSONField()


class QuizSubmitInputSerializer(serializers.Serializer):
    answers = AnswerInputSerializer(many=True)


class ReviewItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    user_answer = serializers.JSONField()
    correct_answer = serializers.JSONField()
    is_correct = serializers.BooleanField()
    explanation = serializers.CharField(allow_blank=True)


class QuizSubmitResultSerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField()
    score_percent = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    stars_earned = serializers.IntegerField()
    stars_now = serializers.IntegerField()
    lesson_completed = serializers.BooleanField()
    next_lesson_unlocked = serializers.BooleanField()
    next_lesson_id = serializers.IntegerField(allow_null=True)
    review = ReviewItemSerializer(many=True)


class QuizAttemptHistoryItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    score = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
