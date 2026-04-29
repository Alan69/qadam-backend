"""API endpoints для модуля обучения."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudent
from apps.common.exceptions import QadamAPIError

from .access import is_lesson_unlocked_for_user
from .models import Lesson, QuizAttempt
from .selectors import (
    lesson_detail_for_user,
    subject_detail_for_user,
    subject_list_for_user,
)
from .serializers import (
    LessonDetailSerializer,
    QuizAttemptHistoryItemSerializer,
    QuizAttemptStartSerializer,
    QuizSubmitInputSerializer,
    QuizSubmitResultSerializer,
    SubjectDetailSerializer,
    SubjectListItemSerializer,
)
from .services.quiz import start_attempt, submit_attempt


class _StudentView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)


# ─── Иерархия ────────────────────────────────────────────────────────────────
class SubjectListView(_StudentView):
    @extend_schema(
        responses={200: SubjectListItemSerializer(many=True)},
        operation_id="learning_subjects_list",
    )
    def get(self, request: Request) -> Response:
        return Response(subject_list_for_user(request.user))


class SubjectDetailView(_StudentView):
    @extend_schema(
        responses={200: SubjectDetailSerializer},
        operation_id="learning_subjects_detail",
    )
    def get(self, request: Request, subject_id: int) -> Response:
        data = subject_detail_for_user(request.user, subject_id)
        if data is None:
            raise QadamAPIError(
                message="Предмет не найден.",
                code="SUBJECT_NOT_FOUND",
                status_code=404,
            )
        return Response(data)


class LessonDetailView(_StudentView):
    @extend_schema(
        responses={200: LessonDetailSerializer},
        operation_id="learning_lessons_detail",
    )
    def get(self, request: Request, lesson_id: int) -> Response:
        try:
            lesson = Lesson.objects.get(pk=lesson_id)
        except Lesson.DoesNotExist as exc:
            raise QadamAPIError(
                message="Урок не найден.",
                code="LESSON_NOT_FOUND",
                status_code=404,
            ) from exc

        if not is_lesson_unlocked_for_user(request.user, lesson):
            raise QadamAPIError(
                message="Урок заблокирован.",
                code="LESSON_LOCKED",
                status_code=403,
            )

        return Response(lesson_detail_for_user(request.user, lesson_id))


# ─── Мини-тест ───────────────────────────────────────────────────────────────
class QuizStartView(_StudentView):
    @extend_schema(
        request=None,
        responses={200: QuizAttemptStartSerializer},
        operation_id="learning_quiz_start",
        description="Начать или возобновить попытку прохождения мини-теста урока.",
    )
    def post(self, request: Request, lesson_id: int) -> Response:
        try:
            lesson = Lesson.objects.get(pk=lesson_id)
        except Lesson.DoesNotExist as exc:
            raise QadamAPIError(
                message="Урок не найден.",
                code="LESSON_NOT_FOUND",
                status_code=404,
            ) from exc

        attempt = start_attempt(user=request.user, lesson=lesson)
        questions = [
            {
                "id": q.id,
                "type": q.type,
                "text": q.text,
                "options": q.options,
                "order": q.order,
            }
            for q in attempt.quiz.questions.all().order_by("order", "id")
        ]
        return Response(
            {
                "attempt_id": attempt.id,
                "started_at": attempt.started_at,
                "questions": questions,
            }
        )


class QuizSubmitView(_StudentView):
    @extend_schema(
        request=QuizSubmitInputSerializer,
        responses={200: QuizSubmitResultSerializer},
        operation_id="learning_quiz_submit",
        description=(
            "Засабмитить ответы на мини-тест. В ответе — балл, звёзды, "
            "разблокировка следующего урока, review (с правильными ответами)."
        ),
    )
    def post(self, request: Request, attempt_id: int) -> Response:
        s = QuizSubmitInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = submit_attempt(
            user=request.user,
            attempt_id=attempt_id,
            answers=s.validated_data["answers"],
        )
        return Response(result)


class LessonAttemptsHistoryView(_StudentView):
    @extend_schema(
        responses={200: QuizAttemptHistoryItemSerializer(many=True)},
        operation_id="learning_lesson_attempts",
    )
    def get(self, request: Request, lesson_id: int) -> Response:
        attempts = (
            QuizAttempt.objects.filter(
                user=request.user, quiz__lesson_id=lesson_id
            )
            .order_by("-started_at")
            .values(
                "id",
                "score",
                "correct_count",
                "total_count",
                "status",
                "started_at",
                "finished_at",
            )
        )
        return Response(list(attempts))


class QuizAttemptDetailView(_StudentView):
    """Просмотр прошлой попытки в режиме «работа над ошибками»."""

    @extend_schema(
        responses={200: QuizSubmitResultSerializer},
        operation_id="learning_quiz_attempt_detail",
    )
    def get(self, request: Request, attempt_id: int) -> Response:
        try:
            attempt = QuizAttempt.objects.select_related(
                "quiz__lesson"
            ).get(pk=attempt_id)
        except QuizAttempt.DoesNotExist as exc:
            raise QadamAPIError(
                message="Попытка не найдена.",
                code="ATTEMPT_NOT_FOUND",
                status_code=404,
            ) from exc

        if attempt.user_id != request.user.id:
            raise QadamAPIError(
                message="Это чужая попытка.",
                code="ATTEMPT_NOT_OWNED",
                status_code=403,
            )

        questions_by_id = {q.id: q for q in attempt.quiz.questions.all()}
        review = []
        for snap in attempt.answers:
            q = questions_by_id.get(snap["question_id"])
            review.append(
                {
                    "question_id": snap["question_id"],
                    "user_answer": snap.get("value", []),
                    "correct_answer": q.correct_answers if q else [],
                    "is_correct": snap.get("is_correct", False),
                    "explanation": "",
                }
            )

        return Response(
            {
                "attempt_id": attempt.id,
                "score_percent": attempt.score,
                "correct_count": attempt.correct_count,
                "total_count": attempt.total_count,
                "stars_earned": 0,  # для прошлых попыток stars_earned не показываем
                "stars_now": 0,
                "lesson_completed": attempt.status == QuizAttempt.Status.FINISHED
                and attempt.score >= 60,
                "next_lesson_unlocked": False,
                "next_lesson_id": None,
                "review": review,
            }
        )
