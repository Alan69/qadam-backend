# Qadam Backend — Модуль обучения (Неделя 3-4)

**Дата:** 2026-04-28
**Автор:** Claude (по согласованию с владельцем)
**Источник требований:** `ТЗ проекта Qadam.pdf` §6 (Обучение), §3.4-3.5 (Подписки и paywall), §4.3 (Звёзды)
**Срок реализации:** 2 недели (10 рабочих дней)
**Предшествующий спринт:** [Фундамент (Неделя 1-2)](2026-04-27-qadam-backend-foundation-design.md)

---

## 1. Контекст и scope

### 1.1. Что делаем

Реализация модуля обучения — ученик может видеть структуру предметов, проходить уроки (видео + теория + мини-тест), зарабатывать звёзды и линейно разблокировать следующие уроки. Подключаем paywall: первый урок в каждом предмете бесплатный, остальное — только по активной подписке.

### 1.2. Что входит

- **API для ученика** — иерархия Класс → Предмет → Раздел → Тема → Урок, контент урока, история прохождения мини-тестов.
- **Server-driven мини-тест** — `start` + `submit`. Правильные ответы никогда не утекают в клиент.
- **Paywall + гейтинг** — `is_locked` флаги на всех уровнях иерархии, бесплатный первый урок предмета (детерминированно — `order=0` на каждом уровне).
- **Sequential unlock** — следующий урок открывается, когда у предыдущего стало ≥1 звезды (≥60% за мини-тест).
- **Звёзды** — `max`-merge между попытками. Пересдача не отбирает звёзды.
- **Прогресс ученика** — `LessonProgress` обновляется на каждой попытке. `/profile/dashboard/` подключаем к реальным данным.
- **Контент-менеджмент** — через Django Admin (отдельных endpoints не делаем).

### 1.3. Что НЕ входит (намеренно)

- **Practice (PracticeTask)** — модели остаются, endpoint'ов нет. Это большая отдельная фича (Duolingo-механика).
- **AI Tutor контекст в уроке** — Неделя 8.
- **Связь с ЕНТ ошибками** — Неделя 5-6.
- **Уведомления о новых уроках** — отдельный модуль.
- **Админ-API для контент-менеджера** — Django Admin покрывает.

### 1.4. Definition of Done

- ✅ Ученик регистрируется без подписки → видит все предметы → проходит первый урок каждого.
- ✅ После выдачи подписки на 1 предмет (через admin) — весь предмет разблокируется линейно.
- ✅ Мини-тест: правильные ответы не светятся в `/start/` payload.
- ✅ Звёзды по 60/80/100 порогам, max-merge.
- ✅ Следующий урок разблокируется при ≥60% (≥1 звезда).
- ✅ `/profile/dashboard/` отдаёт реальный прогресс.
- ✅ Тесты зелёные, coverage `apps/learning/` ≥ 90%.
- ✅ Swagger UI документирует новые endpoints.
- ✅ `docs/learning-flow.md` написан.

---

## 2. Решения, принятые на брейнсторминге

| № | Тема | Решение |
|---|---|---|
| 1 | Scope | Вариант A — обучение + мини-тест + paywall (без Practice/AI/ENT) |
| 2 | "Первый бесплатный урок" | Детерминированно: `section.order=0 ∧ topic.order=0 ∧ lesson.order=0` |
| 3 | Звёзды при пересдаче | `max` за все попытки. Разблокировка тоже не откатывается. |
| 4 | Видимость залоченного | Всё видно с `is_locked` флагом (Duolingo-стайл) |
| 5 | Мини-тест | Server-driven: правильные ответы не уезжают на клиент |
| 5а | Таймер в мини-тесте | Нет таймера — ТЗ не требует. Время попытки логируем. |
| 5б | Порядок вопросов | Стабильный (по `order`), без рандомизации |
| 5в | Брошенные attempts | Истекают через 24 ч → `status=expired` |
| 5г | Скоринг multi_choice | Всё-или-ничего (нет частичных баллов) |
| 5д | Параллельные attempts | Один `in_progress` на (user, quiz). Resume вместо нового. |

---

## 3. Доменная логика

### 3.1. Helpers — `apps/learning/access.py`

Чистые функции без побочных эффектов:

```python
def has_subscription_access(user, subject) -> bool
def is_lesson_free(lesson) -> bool
def previous_lesson(lesson) -> Lesson | None
def is_lesson_unlocked_for_user(user, lesson) -> bool
def lock_reason_for_lesson(user, lesson) -> str | None
```

`is_lesson_unlocked_for_user(user, lesson)` возвращает `True`, когда выполнено всё:

1. `lesson.content_status == PUBLISHED`
2. **Paywall**: `is_lesson_free(lesson)` ИЛИ `has_subscription_access(user, lesson.subject)`
3. **Sequential**: `previous_lesson(lesson)` либо `None` (это первый урок предмета), либо у него есть `LessonProgress` с `stars >= 1`.

`lock_reason_for_lesson` — для UI: возвращает `"no_subscription"`, `"previous_not_completed"`, `"unpublished"` или `None`.

### 3.2. "Предыдущий урок" в плоском списке предмета

Уроки внутри предмета упорядочены тройкой `(section.order, topic.order, lesson.order)`. Для нахождения предыдущего урока используем составное сравнение через ORM (никаких циклов в питоне).

**Граничный случай:** если контент-менеджер вставил новый урок между уже пройденными, для ученика он окажется заблокированным (т.к. `previous_lesson` указывает на новый урок без прогресса). Это правильное поведение — ученик увидит новый материал.

### 3.3. Стартовая логика мини-теста — `services/quiz.py:start_attempt`

```
def start_attempt(user, lesson) -> QuizAttempt:
    1. Проверить is_lesson_unlocked_for_user(user, lesson). Иначе 403.
    2. Найти существующий QuizAttempt(user=user, quiz=lesson.quiz, status=in_progress).
       Если есть и не старше 24 ч — вернуть его (resume).
       Если есть и старше — пометить status=expired, идти дальше.
    3. Создать новый QuizAttempt(status=in_progress).
    4. Вернуть.
```

### 3.4. Скоринг и обновление прогресса — `services/quiz.py:submit_attempt`

```
def submit_attempt(user, attempt_id, answers) -> SubmitResult:
    1. Найти attempt. Проверить владелец и статус (in_progress).
    2. Прогнать каждый ответ через is_answer_correct() с учётом типа вопроса.
    3. Посчитать correct_count, total_count, score_percent.
    4. Определить stars_earned по таблице 60/80/100 → 1/2/3.
    5. attempt.status = finished, finished_at = now(), сохранить answers (JSON).
    6. update_progress_after_attempt(user, lesson, score_percent, stars_earned)
       — max-merge: stars = max(stars, stars_earned), best_quiz_score = max(...).
       — completed_at выставляется при первой звезде, дальше не трогается.
    7. Вернуть SubmitResult с review-payload (включая правильные ответы и объяснения).
```

### 3.5. Скоринг по типам вопросов — `is_answer_correct`

| Тип | Логика |
|---|---|
| `single_choice` | `set(user_answer) == set(correct_answers)` (один элемент с обеих сторон) |
| `multi_choice` | `set(user_answer) == set(correct_answers)` — всё-или-ничего |
| `match` | `dict(user_answer) == dict(correct_answers)` |
| `context` | `set(user_answer) == set(correct_answers)` |

### 3.6. Helper в `apps/payments/services.py`

```python
def get_active_subscription(user) -> Subscription | None:
    """Subscription со status='active' AND expires_at > now(). Иначе None."""
```

Используется в `has_subscription_access`. Будущая логика истечения подписок (Celery-task, понижение в access) тоже будет жить здесь.

---

## 4. API endpoints (`/api/v1/learning/`)

Auth на всех: `IsAuthenticated + IsStudent`.

### 4.1. Иерархия (read-only)

| Метод и путь | Назначение |
|---|---|
| `GET /subjects/` | Список всех опубликованных предметов с агрегатами по ученику (`is_locked`, `lessons_completed`, `stars_total`, `progress_percent`) |
| `GET /subjects/{id}/` | Детальная иерархия предмета: sections → topics → lessons. На каждом уровне `is_locked` и `lock_reason`. На уроке также `stars`, `best_score`, `completed_at` |
| `GET /lessons/{id}/` | Содержимое урока (видео, теория, метаданные). `403` если урок залочен. Включает `next_lesson_id` |

### 4.2. Мини-тест

| Метод и путь | Назначение |
|---|---|
| `POST /lessons/{id}/quiz/start/` | Создать или возобновить попытку. Возвращает `attempt_id` + список вопросов **без** правильных ответов |
| `POST /quiz-attempts/{attempt_id}/submit/` | Засабмитить ответы. Возвращает балл, звёзды, разблокировку, review-payload (с правильными ответами и объяснениями) |
| `GET /lessons/{id}/attempts/` | История попыток ученика по уроку |
| `GET /quiz-attempts/{id}/` | Детали прошлой попытки (review-режим) |

### 4.3. Контракты ответов

**`/start/` payload:**
```json
{
  "attempt_id": 555,
  "started_at": "2026-04-28T...",
  "questions": [
    {
      "id": 800,
      "type": "single_choice",
      "text": "...",
      "options": ["A", "B", "C", "D"],
      "order": 0
    }
  ]
}
```

⚠️ Поля `correct_answers`, `explanation` НЕ в payload.

**`/submit/` payload:**
```json
{
  "attempt_id": 555,
  "score_percent": 80,
  "correct_count": 8,
  "total_count": 10,
  "stars_earned": 2,
  "stars_now": 2,
  "lesson_completed": true,
  "next_lesson_unlocked": true,
  "next_lesson_id": 101,
  "review": [
    {
      "question_id": 800,
      "user_answer": ["A"],
      "correct_answer": ["A"],
      "is_correct": true,
      "explanation": "..."
    }
  ]
}
```

### 4.4. Стандарт ошибок

Используется единый формат из фундамента (`apps/common/exceptions.py`). Новые коды:

| Код | HTTP | Когда |
|---|---|---|
| `LESSON_LOCKED` | 403 | Попытка открыть/начать тест залоченного урока |
| `LESSON_HAS_NO_QUIZ` | 400 | У урока нет связанного `Quiz` |
| `ATTEMPT_NOT_OWNED` | 403 | Чужой `attempt_id` |
| `ATTEMPT_ALREADY_FINISHED` | 400 | Попытка submit на уже завершённом attempt |
| `ATTEMPT_EXPIRED` | 400 | Submit на устаревшем (>24h) attempt |

### 4.5. Обновлённый `/profile/dashboard/`

Структура та же что в фундаменте (`progress`, `stars`, `subscription`, ...), но заполнена реальными данными вместо нулей. `results`, `analytics`, `league` — остаются заглушками (для следующих недель).

---

## 5. Изменения в моделях (миграции)

Одна новая миграция в `apps.learning`:

### 5.1. `QuizAttempt` — добавляем поля

```python
class QuizAttempt(TimestampedModel):
    # ... существующие поля ...
    status = models.CharField(
        max_length=16,
        choices=[("in_progress", ...), ("finished", ...), ("expired", ...)],
        default="finished",
    )
    answers = models.JSONField(default=list)
    correct_count = models.PositiveSmallIntegerField(default=0)
    total_count = models.PositiveSmallIntegerField(default=0)
```

### 5.2. Constraint — один in_progress на (user, quiz)

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["user", "quiz"],
            condition=Q(status="in_progress"),
            name="unique_active_quiz_attempt",
        ),
    ]
```

### 5.3. Остальные модели

`Lesson`, `Quiz`, `QuizQuestion`, `LessonProgress`, `Subject`, `Section`, `Topic` — без изменений (структура из фундамента достаточна).

---

## 6. Структура файлов

```
src/apps/learning/
├── models.py                  ← правки QuizAttempt
├── admin.py                   ← без изменений
├── translation.py             ← без изменений
├── access.py                  ← НОВЫЙ
├── selectors.py               ← НОВЫЙ
├── services/
│   ├── __init__.py
│   ├── quiz.py                ← НОВЫЙ
│   └── progress.py            ← НОВЫЙ
├── serializers.py             ← НОВЫЙ
├── views.py                   ← НОВЫЙ
├── urls.py                    ← НОВЫЙ
├── permissions.py             ← НОВЫЙ
└── migrations/
    └── 0002_quizattempt_status.py

src/apps/payments/
└── services.py                ← НОВЫЙ: get_active_subscription(user)

src/config/urls.py             ← добавить include('apps.learning.urls')

src/tests/
├── factories.py               ← НОВЫЙ: factory_boy для всех нужных моделей
└── learning/
    ├── __init__.py
    ├── test_access.py
    ├── test_quiz_service.py
    ├── test_subjects_api.py
    ├── test_lessons_api.py
    ├── test_quiz_api.py
    └── test_dashboard.py
```

### Принципы (из существующего architecture.md)

- **`access.py`** — чистые функции, легко тестируется.
- **`selectors.py`** — read-only ORM-запросы и агрегаты. Никакой записи.
- **`services/`** — пишущие операции. Транзакции живут здесь.
- **`views.py`** — тонкие. `serializer.is_valid()` → `service.x()` → `Response()`.
- **`permissions.py`** — object-level проверки (`request.user` владеет `attempt_id`).

---

## 7. Тесты

Полное покрытие основных сценариев. `pytest` + `factory_boy`.

### 7.1. `factories.py`

Фабрики для: Subject, Section, Topic, Lesson (с Quiz и 5 вопросами по умолчанию), Tariff, Subscription, StudentProfile.

### 7.2. Файлы и кейсы

- **`test_access.py`** (~12 тестов) — paywall, sequential unlock, content_status фильтрация
- **`test_quiz_service.py`** (~10 тестов) — start_attempt, submit_attempt, скоринг по типам, max-merge
- **`test_subjects_api.py`** (~6 тестов) — иерархия, lock-флаги, агрегаты
- **`test_lessons_api.py`** (~5 тестов) — детали урока, 403 на залоченные
- **`test_quiz_api.py`** (~10 тестов) — start, submit, history, 403/400 ошибки
- **`test_dashboard.py`** (~3 теста) — реальные данные, агрегаты по предметам, статус подписки

### 7.3. Цели покрытия

- `apps/learning/access.py` — ≥ 95%
- `apps/learning/services/` — ≥ 95%
- `apps/learning/views.py` — ≥ 90%

После спринта total: **~75-80 тестов** (39 текущих + ~40 новых).

---

## 8. План работ (10 рабочих дней)

| День | Задача |
|---|---|
| 1 | Миграция `QuizAttempt` + `payments.services.get_active_subscription`. Запустить миграцию, проверить partial unique constraint. Обновить `factories.py`. |
| 2 | `apps/learning/access.py` + тесты в `test_access.py` (12 кейсов, ≥95% покрытие). |
| 3 | `services/quiz.py:start_attempt` + `services/progress.py`. Тесты для `start_attempt`. |
| 4 | `services/quiz.py:submit_attempt` — скоринг single/multi/match/context, начисление звёзд, разблокировка следующего. Тесты для submit. |
| 5 | `selectors.py` — `subject_list_for_user`, `subject_detail_for_user`, `lesson_detail_for_user`. Аккуратная агрегация без N+1. |
| 6 | API endpoints — иерархия (`/subjects/`, `/subjects/{id}/`, `/lessons/{id}/`). Permission `LessonAccessPermission`. Тесты `test_subjects_api.py` + `test_lessons_api.py`. |
| 7 | API endpoints — мини-тест (`/quiz/start/`, `/quiz-attempts/{id}/submit/`, `/lessons/{id}/attempts/`, `/quiz-attempts/{id}/`). Тесты `test_quiz_api.py`. |
| 8 | Обновлённый `/profile/dashboard/` с реальными данными. Тесты. Management command для seed-фикстур (2 предмета, 3 урока, по 5 вопросов). |
| 9 | Полировка: проверка multi-language (`?lang=kk`), фильтры по `content_status` в admin, Swagger-описания. |
| 10 | Финал: ручной QA полного флоу через Swagger UI, исправление найденного, `docs/learning-flow.md` (диаграмма sequential unlock, paywall логика, sequence-диаграмма мини-теста). |

### Резерв при отставании

Первыми режутся: казахская локализация (день 9), seed-фикстуры (день 8 — оставляем инструкцию в README), отдельный `GET /quiz-attempts/{id}/` (день 7 — заменяем на review из `/submit/`).

---

## 9. Открытые вопросы / следующие шаги

После завершения этого спринта:

1. **Неделя 5: ЕНТ-тестирование** — полный формат теста (5 предметов, 120 заданий, 240 минут), таймер, подсчёт баллов.
2. **Неделя 6: Аналитика** — графики результатов, история тестов, работа над ошибками с linkback'ом на уроки (требует данные из ЕНТ).
3. **Неделя 7: Платежи** — реальная интеграция Kaspi/Halyk, paywall (логика уже встроена в этот спринт, останется добавить чек-аут).
4. **Неделя 8: AI Tutor MVP** — Gemini + Qdrant, контекст урока в чате.

Каждый этап — отдельный брейнсторм + дизайн-документ.
