# Модуль обучения — поток

## Иерархия контента

```
Subject (Математика)
└── Section (Алгебра, order=0)
    └── Topic (Дроби, order=0)
        └── Lesson (Простые дроби, order=0)
            ├── video_url
            ├── theory (rich text)
            └── Quiz (1:1)
                └── QuizQuestion × N
```

Уроки внутри предмета упорядочены по плоской тройке `(section.order, topic.order, lesson.order)`.

## Гейтинг — три уровня проверок

При определении доступности урока проверки идут в этом порядке (первая failed → причина блокировки):

```
                ┌──────────────────────────┐
                │  1. content_status?       │
                │  Published?               │
                └────────┬─────────────────┘
                         │ нет
                         ▼ "unpublished"
                         │
                         │ да
                ┌──────────────────────────┐
                │  2. Paywall              │
                │  is_lesson_free          │
                │  ИЛИ has_subscription?   │
                └────────┬─────────────────┘
                         │ нет
                         ▼ "no_subscription"
                         │
                         │ да
                ┌──────────────────────────┐
                │  3. Sequential unlock    │
                │  Предыдущий урок         │
                │  имеет ≥1 звезды?        │
                └────────┬─────────────────┘
                         │ нет
                         ▼ "previous_not_completed"
                         │
                         │ да (или нет prev)
                         ▼
                       UNLOCKED
```

### "Первый урок бесплатный"

Детерминированно: бесплатный = `section.order=0 ∧ topic.order=0 ∧ lesson.order=0`. Контент-менеджер сам решает, какой урок будет «вводным» — ставит соответствующий order.

### "Подписка покрывает предмет"

Подписка считается активной, если `status='active' AND expires_at > now()`. Проверяем что её тариф включает `has_learning=True` и предмет урока есть в `tariff.subjects`.

### "Предыдущий урок пройден"

Любая попытка с результатом ≥60% даёт ≥1 звезду → следующий урок разблокирован. **Max-merge**: если ученик потом пересдал и получил 0% — звёзды не отбираются и следующий остаётся открытым.

## Sequence-диаграмма мини-теста

```
Ученик                  API                         БД                      Redis
  │                      │                            │                         │
  │ POST /lessons/N/quiz/start/                       │                         │
  ├─────────────────────▶│                            │                         │
  │                      │ check is_lesson_unlocked   │                         │
  │                      ├───────────────────────────▶│                         │
  │                      │ select * from QuizAttempt  │                         │
  │                      │   where user, quiz, status=in_progress                │
  │                      ├───────────────────────────▶│                         │
  │                      │ → создать новую (или resume / expire старую)          │
  │                      ├───────────────────────────▶│                         │
  │ 200 { attempt_id,    │                            │                         │
  │       questions[без correct_answers] }            │                         │
  │◀─────────────────────┤                            │                         │
  │                      │                            │                         │
  │ ... ученик решает на клиенте ...                  │                         │
  │                      │                            │                         │
  │ POST /quiz-attempts/55/submit/                    │                         │
  │ { answers: [...] }   │                            │                         │
  ├─────────────────────▶│                            │                         │
  │                      │ check ownership + status   │                         │
  │                      ├───────────────────────────▶│                         │
  │                      │ for each q: is_answer_correct                        │
  │                      │ score% = correct / total × 100                        │
  │                      │ stars_earned = stars_for_score(score%)               │
  │                      │ TX: attempt.status=finished                          │
  │                      │     LessonProgress.stars = max(stars, stars_earned)  │
  │                      ├───────────────────────────▶│                         │
  │                      │ next_lesson + is_unlocked?                           │
  │ 200 { score_percent, │                            │                         │
  │       stars_earned, stars_now,                    │                         │
  │       lesson_completed, next_lesson_unlocked,     │                         │
  │       review[с правильными ответами] }            │                         │
  │◀─────────────────────┤                            │                         │
```

### Брошенные попытки

Если ученик начал тест, закрыл вкладку и пришёл через 25 часов:

1. `POST /quiz/start/` находит `in_progress` попытку → проверяет возраст.
2. `now() - started_at > 24h` → старая помечается `status=expired`.
3. Создаётся новая попытка.
4. Если ученик попытается засабмитить старую (с её `attempt_id`) — `400 ATTEMPT_EXPIRED`.

Constraint в БД (`UniqueConstraint(condition=Q(status='in_progress'))`) гарантирует что параллельных активных попыток не бывает.

## Скоринг по типам вопросов

Все типы — «всё-или-ничего». Нет частичных баллов.

| Тип | Логика сравнения |
|---|---|
| `single_choice` | `set(user_answer) == set(correct_answers)` (один элемент) |
| `multi_choice` | `set(user_answer) == set(correct_answers)` (полное совпадение множеств) |
| `match` | `dict(user_answer) == dict(correct_answers)` (или сет пар) |
| `context` | `set(user_answer) == set(correct_answers)` |

## Звёзды и пороги

| Score % | Звёзды |
|---|---|
| 0 – 59 | 0 |
| 60 – 79 | 1 |
| 80 – 99 | 2 |
| 100 | 3 |

Звёзды — `max` за все попытки. Пересдача может только улучшить, не ухудшить.

## Как протестировать вручную через Swagger

1. `POST /api/v1/auth/register/init/` → `verify/` → `complete/` (получить JWT).
2. В Swagger UI авторизоваться по Bearer.
3. `python manage.py seed_learning` (через `make shell`) — наполнить контент.
4. `GET /api/v1/learning/subjects/` — увидеть Математику и Физику. Оба `is_locked: true`.
5. `GET /api/v1/learning/subjects/{math_id}/` — раскрыть структуру. Первый урок `is_free: true, is_locked: false`, второй `is_locked: true, lock_reason: "no_subscription"`.
6. `POST /api/v1/learning/lessons/{first_id}/quiz/start/` — получить вопросы.
7. `POST /api/v1/learning/quiz-attempts/{id}/submit/` с правильными ответами (`["B"]` для всех в seed-данных) — получить 100%, 3 звезды, разблокировку второго урока.
8. Попытка `GET /api/v1/learning/lessons/{second_id}/` — вернёт 403 пока не выдадим подписку.
9. Через `/admin/`: создать `Subscription` для пользователя на тариф «Стандарт». Повторить шаг 8 — теперь 200, и можно проходить дальше линейно.

## Где смотреть код

- **Доступ / paywall**: [`apps/learning/access.py`](../src/apps/learning/access.py)
- **Скоринг и попытки**: [`apps/learning/services/quiz.py`](../src/apps/learning/services/quiz.py)
- **Прогресс**: [`apps/learning/services/progress.py`](../src/apps/learning/services/progress.py)
- **Селекторы для API**: [`apps/learning/selectors.py`](../src/apps/learning/selectors.py)
- **Endpoints**: [`apps/learning/views.py`](../src/apps/learning/views.py)
- **Подписки**: [`apps/payments/services.py`](../src/apps/payments/services.py)
- **Тесты**: [`tests/learning/`](../src/tests/learning/)
- **Demo seed**: [`apps/learning/management/commands/seed_learning.py`](../src/apps/learning/management/commands/seed_learning.py)
