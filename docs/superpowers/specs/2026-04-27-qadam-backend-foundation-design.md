# Qadam Backend — Дизайн фундамента (Неделя 1-2)

**Дата:** 2026-04-27
**Автор:** Claude (по согласованию с владельцем)
**Источник требований:** `ТЗ проекта Qadam.pdf`
**Срок реализации:** 1-2 недели (10 рабочих дней)

---

## 1. Контекст и scope

### 1.1. Что делаем

Образовательная платформа Qadam — подготовка к ЕНТ. ТЗ описывает 13 функциональных модулей и оценивает MVP в 8 недель работы backend-разработчика. За доступные 1-2 недели реализуем **«Фундамент»** — то, что в ТЗ обозначено как «Неделя 1-2: База системы».

### 1.2. Что входит в фундамент

- ★ **Полная реализация:** auth (регистрация по телефону + код, логин, JWT, восстановление пароля, RBAC для 5 ролей), профиль ученика (CRUD, dashboard-агрегатор, информация о кураторе), endpoint'ы управления пользователями для супер-админа.
- ★ **Полная инфраструктура:** Django + DRF + PostgreSQL + Redis + Celery, Docker Compose для dev, отдельный Dockerfile для prod, Swagger UI, тесты, линтер, документация.
- **Скелеты:** модели 8 доменных apps (`learning`, `testing`, `payments`, `gamification`, `notifications`, `universities`, `ai_tutor`, `crm`) с миграциями и регистрацией в Django Admin — без endpoint'ов и бизнес-логики. Эти apps покрывают 9 доменных модулей ТЗ. Оставшиеся 2 модуля ТЗ — «Контент-менеджер» и «Супер-админ панель» — это интерфейсные роли, реализуются через Django Admin + RBAC + поле `content_status` на контентных моделях (отдельных apps не требуется).

### 1.3. Что НЕ входит (намеренно)

- Реальная интеграция с Kaspi / Halyk платежами.
- Реальная интеграция с Google Gemini / Qdrant.
- Реальная отправка WhatsApp кодов (только адаптер с заглушкой).
- Бизнес-логика обучения, ЕНТ-тестирования, геймификации, уведомлений, AI Tutor — модели готовы, эндпоинтов нет.
- Frontend (React) и mobile (Flutter) — другие исполнители.
- CI/CD пайплайн, реальный деплой на конкретную инфраструктуру.

### 1.4. Definition of Done (по итогам 2 недель)

- `make up` поднимает всё одной командой.
- Регистрация через API в 3 шага работает.
- Login → JWT → profile endpoint работает.
- Все 13 модулей видны в Django Admin, можно создавать данные руками.
- Swagger UI показывает все auth/profile endpoint'ы.
- Тесты зелёные, coverage в `apps/accounts/` и `apps/profiles/` ≥ 90 %.
- Production Dockerfile собирается и запускается.
- README позволяет развернуть локально за 10 минут.

---

## 2. Решения, принятые на брейнсторминге

| № | Тема | Решение |
|---|------|---------|
| 1 | Scope | Вариант A — «Фундамент» (Неделя 1-2 ТЗ) |
| 2 | WhatsApp код | Адаптер `SmsProvider` с реализациями `console` (dev) и `whatsapp` (заглушка под реального провайдера) |
| 3 | Тип токенов | JWT через `djangorestframework-simplejwt` + Redis blacklist |
| 4 | Скелеты моделей | Вариант C — модели всех 13 модулей + Django Admin |
| 5 | Окружение | Docker Compose (dev) + production Dockerfile |
| 6 | Многоязычность | `django-modeltranslation` (поля `*_kz`, `*_ru` автоматически) |

---

## 3. Стек

- **Python 3.12**
- **Django 5.x** + **Django REST Framework**
- **PostgreSQL 16** — основная БД
- **Redis 7** — кэш OTP, JWT blacklist, throttling, Celery broker
- **Celery + celery-beat** — фоновые задачи (отправка кодов, скоро уведомления, периодические пересчёты рейтингов)
- **`djangorestframework-simplejwt`** — JWT с refresh rotation
- **`drf-spectacular`** — OpenAPI 3 / Swagger UI
- **`django-modeltranslation`** — KZ/RU поля
- **`pytest` + `pytest-django` + `factory_boy` + `freezegun`** — тесты
- **`ruff`** — линтер и форматтер
- **`uv`** — менеджер зависимостей (быстрее pip)

---

## 4. Структура проекта

```
qadam/
├── docker/
│   ├── Dockerfile.dev
│   └── Dockerfile.prod
├── docker-compose.yml
├── docker-compose.prod.yml
├── pyproject.toml
├── .env.example
├── Makefile
├── README.md
├── manage.py
└── src/
    ├── config/
    │   ├── settings/
    │   │   ├── base.py
    │   │   ├── dev.py
    │   │   └── prod.py
    │   ├── urls.py
    │   ├── wsgi.py
    │   ├── asgi.py
    │   └── celery.py
    ├── apps/
    │   ├── common/         # TimestampedModel, mixins, exceptions
    │   ├── accounts/       # ★ User, Auth, OTP, JWT, RBAC
    │   ├── profiles/       # ★ StudentProfile, dashboard
    │   ├── learning/       # скелет
    │   ├── testing/        # скелет
    │   ├── payments/       # скелет
    │   ├── gamification/   # скелет
    │   ├── notifications/  # скелет
    │   ├── universities/   # скелет
    │   ├── ai_tutor/       # скелет
    │   └── crm/            # скелет
    ├── services/
    │   └── sms/
    │       ├── base.py     # абстрактный SmsProvider
    │       ├── console.py  # dev
    │       └── whatsapp.py # prod stub
    └── tests/              # параллельная структура apps/
```

**Принципы:**
- ★ — модули с полной реализацией.
- Каждый «полный» app содержит: `models.py`, `admin.py`, `serializers.py`, `views.py`, `urls.py`, `permissions.py`, `selectors.py` (читающая логика), `services.py` (изменяющая логика).
- Скелетный app содержит только `models.py`, `admin.py`, `apps.py`, `migrations/`.
- `services/sms/` отдельно от `apps/`, так как это инфраструктурный адаптер, а не доменное приложение.

---

## 5. Auth-флоу (детально)

### 5.1. User-модель (`apps/accounts/models.py`)

```
User (AbstractBaseUser + PermissionsMixin)
├── phone           CharField(unique, validators=[E.164])  — основной идентификатор
├── password        (Argon2)
├── role            CharField(choices=STUDENT|CURATOR|CONTENT_MANAGER|SALES_MANAGER|SUPER_ADMIN)
├── is_active       Boolean
├── is_staff        Boolean (доступ в Django Admin)
├── is_superuser    Boolean
├── created_at, updated_at
└── USERNAME_FIELD = 'phone'
```

### 5.2. StudentProfile (`apps/profiles/models.py`)

OneToOne к User, создаётся только для роли STUDENT:

- `name`, `parent_phone`, `grade` (10/11), `learning_language` (kz/ru)
- `region` (FK), `city` (FK)
- `selected_subjects` (M2M Subject), `target_universities` (M2M), `target_specialities` (M2M)
- `target_score` (опционально), `current_level` (вычисляемое, пока 0)
- `assigned_curator` (FK User с role=CURATOR)
- `sales_status` (NEW/IN_WORK/REGISTERED/PAID/RENEWAL/REJECTED) — для CRM-модуля менеджера

`CuratorAssignmentHistory` — история назначений (student, curator, assigned_at, unassigned_at).

### 5.3. Регистрация (3 шага)

**Шаг 1 — отправка кода:**
```
POST /api/v1/auth/register/init/   { "phone": "+77001234567" }
→ генерирует 6-значный код, сохраняет в Redis: otp:reg:{phone} = code (TTL 5 мин)
→ SmsProvider.send(phone, "Qadam код: {code}")
→ rate limit: 3 запроса / 10 мин на телефон
→ 200 OK { "expires_in": 300 }
```

**Шаг 2 — подтверждение:**
```
POST /api/v1/auth/register/verify/   { "phone", "code" }
→ читает Redis, при совпадении удаляет ключ
→ выдаёт verification_token (JWT, 10 мин, claim purpose=register)
→ rate limit: 5 попыток ввода кода
→ 200 OK { "verification_token" }
```

**Шаг 3 — заполнение профиля:**
```
POST /api/v1/auth/register/complete/
{ "verification_token", "password", "name", "parent_phone", "grade", "learning_language" }
→ валидирует токен (purpose=register)
→ создаёт User(phone=из токена, role=STUDENT) + StudentProfile
→ автоназначает куратора (round-robin из активных)
→ возвращает JWT pair { access, refresh }
→ 201 Created
```

### 5.4. Login

```
POST /api/v1/auth/login/   { "phone", "password" }
→ проверка: пользователь существует, password верный, is_active=True
→ rate limit: 5 попыток / 15 мин на телефон
→ создаёт LoginEvent (user, ip, user_agent, success, created_at)
→ выдаёт JWT pair
```

### 5.5. Восстановление пароля

`/api/v1/auth/password-reset/init/` → `/verify/` → `/confirm/`. Аналогичный поток с verification_token (purpose=password_reset, 10 мин).

### 5.6. JWT-операции

```
POST /api/v1/auth/refresh/      { refresh } → { access, refresh } (rotation)
POST /api/v1/auth/logout/       { refresh } → blacklist refresh в Redis
POST /api/v1/auth/logout-all/   → blacklist все refresh пользователя
GET  /api/v1/auth/sessions/     → список активных refresh-токенов
```

**Настройки JWT:**
- access TTL — 15 минут
- refresh TTL — 30 дней
- refresh rotation включён (старый сразу инвалидируется)
- blacklist через Redis с TTL = TTL refresh

### 5.7. RBAC

`role` поле на User + DRF permission классы:

```python
class IsStudent(BasePermission): ...
class IsCurator(BasePermission): ...
class IsContentManager(BasePermission): ...
class IsSalesManager(BasePermission): ...
class IsSuperAdmin(BasePermission): ...
class HasAnyRole(BasePermission):  # принимает список
    ...
```

Применяются на view-уровне: `permission_classes = [IsAuthenticated, IsStudent]`.

### 5.8. Соответствие требованиям безопасности (ТЗ §1.8)

- ✅ JWT-токены
- ✅ Auto-сохранение сессии (refresh rotation)
- ✅ Rate limit на ввод кода (5 попыток)
- ✅ TTL кода 5 минут (ТЗ требует 2-5 мин)
- ✅ Логирование входов (`LoginEvent`)
- ✅ Logout со всех устройств
- ✅ HTTPS в prod через nginx
- ✅ Argon2 для паролей

---

## 6. Схема БД (модели всех 13 модулей)

Все модели наследуют `TimestampedModel` (created_at, updated_at). Поля `name`, `title`, `text`, `description` автоматически дублируются как `*_kz` и `*_ru` через `django-modeltranslation`.

### 6.1. `accounts` ★
- **User** — phone, password, role, is_active, is_staff, is_superuser
- **LoginEvent** — user, ip, user_agent, success, created_at

### 6.2. `profiles` ★
- **StudentProfile** — см. §5.2
- **CuratorAssignmentHistory** — student, curator, assigned_at, unassigned_at

### 6.3. `learning` (скелет)
- **Class** — number (10/11)
- **Subject** — name, description, icon
- **Section** — subject, name, order
- **Topic** — section, name, order
- **Lesson** — topic, title, video_url, theory (rich text), order, content_status (NEW/REVIEW/APPROVED/PUBLISHED)
- **PracticeTask** — lesson, type (single_choice/multi_choice/match/context), payload (JSON), order
- **Quiz** — lesson (1:1), мини-тест
- **QuizQuestion** — quiz, type, text, options (JSON), correct_answers (JSON), order
- **LessonProgress** — user, lesson, stars (0-3), best_quiz_score, attempts_count, completed_at, last_attempt_at
- **QuizAttempt** — user, quiz, score, started_at, finished_at

### 6.4. `testing` (скелет, ЕНТ)
- **ENTTestSession** — user, started_at, finished_at, total_score, status (in_progress/finished/expired), profile_subject_1, profile_subject_2
- **ENTSubjectResult** — session, subject, score, errors_count, time_seconds
- **ENTQuestion** — отдельный пул вопросов (subject, type, difficulty, text, options, correct_answers)
- **ENTAnswer** — session, question, user_answer (JSON), is_correct, time_spent_seconds

  *Замечание:* ЕНТ-вопросы отделены от мини-тестов уроков, так как имеют отдельный жизненный цикл (банк, импорт партиями, сложность).

### 6.5. `payments` (скелет)
- **Tariff** — name, price, duration_days, has_learning, has_testing, has_ai_tutor, subjects (M2M Subject), is_active
- **Subscription** — user, tariff, status (active/expired/cancelled), started_at, expires_at, source (self_payment/via_curator/via_manager)
- **Payment** — user, subscription, amount, method (card/kaspi_qr/halyk_qr/manual), status (pending/success/failed), external_id, paid_at
- *Constraint:* у пользователя ≤ 1 активной подписки (partial unique index в БД)

### 6.6. `gamification` (скелет)
- **League** — code (BRONZE/SILVER/GOLD), min_stars, max_stars
- **UserLeague** — user (1:1), current_league, updated_at
- **Star** — user, lesson, count (1-3), earned_at
- **AvatarItem** — type (clothing/accessory/armor/weapon), rarity, required_league
- **UserAvatar** — user (1:1), equipped_items (M2M)
- **Chest** — user, opened_at, contained_items (M2M)
- **Tournament** — type (weekly/event), starts_at, ends_at, status
- **TournamentParticipant** — tournament, user, score, position
- **Clan** — name, owner, rating, created_at
- **ClanMember** — clan, user, joined_at
- **ClanBattle** — clan_a, clan_b, format (3v3/5v5/10v10), status, winner, started_at
- **Friendship** — user_a, user_b, created_at (unique pair)
- **Challenge** — created_by, title, target_metric, target_value, deadline, scope (global/clan/user)
- **ChallengeParticipant** — challenge, user, progress, completed_at

### 6.7. `notifications` (скелет)
- **NotificationTemplate** — code, title, body, channels (in_app/whatsapp), is_active
- **Notification** — user, template, channel, status (pending/sent/delivered/read/failed), sent_at, read_at, payload (JSON)

### 6.8. `universities` (скелет)
- **Region** — name
- **City** — region, name
- **University** — city, name, description, website
- **Speciality** — university, name, description, code, threshold_score, required_subjects (M2M Subject)

### 6.9. `ai_tutor` (скелет)
- **Conversation** — user, lesson (nullable), mode (helper/learning/grant_search), started_at
- **Message** — conversation, role (user/assistant), content, helpful_rating (null/positive/negative), created_at

### 6.10. `crm` (скелет)
- **SalesNote** — student (FK StudentProfile), manager (FK User), text, created_at
- **StatusChangeLog** — student, old_status, new_status, changed_by, changed_at

  Статус клиента (`sales_status`) хранится прямо в `StudentProfile`.

### 6.11. `common`
- **TimestampedModel** (abstract) — created_at, updated_at

---

## 7. API endpoints (v1)

### 7.1. `accounts/` ★
```
POST   /api/v1/auth/register/init/             { phone } → 200
POST   /api/v1/auth/register/verify/           { phone, code } → { verification_token }
POST   /api/v1/auth/register/complete/         { verification_token, password, name, parent_phone, grade, learning_language } → { access, refresh, user }
POST   /api/v1/auth/login/                     { phone, password } → { access, refresh, user }
POST   /api/v1/auth/refresh/                   { refresh } → { access, refresh }
POST   /api/v1/auth/logout/                    { refresh } → 204
POST   /api/v1/auth/logout-all/                → 204
GET    /api/v1/auth/sessions/                  → [{ device, last_used, created_at }]
POST   /api/v1/auth/password-reset/init/       { phone } → 200
POST   /api/v1/auth/password-reset/verify/     { phone, code } → { reset_token }
POST   /api/v1/auth/password-reset/confirm/    { reset_token, new_password } → 204
GET    /api/v1/auth/me/                        → { id, phone, role, ... }
```

### 7.2. `profiles/` ★ (только STUDENT)
```
GET    /api/v1/profile/                        → полный StudentProfile
PATCH  /api/v1/profile/                        → редактирование (name, learning_language, target_score, selected_subjects, target_universities)
                                                 ❌ phone, parent_phone — только через админа (ТЗ §2.4)
GET    /api/v1/profile/dashboard/              → { progress, results, analytics, league, stars }
GET    /api/v1/profile/curator/                → { name, phone, whatsapp }
```

### 7.3. `users/` (только SUPER_ADMIN)
```
GET    /api/v1/admin/users/                    → список с фильтрами
POST   /api/v1/admin/users/                    → создание пользователя
GET    /api/v1/admin/users/{id}/
PATCH  /api/v1/admin/users/{id}/
POST   /api/v1/admin/users/{id}/block/
POST   /api/v1/admin/users/{id}/unblock/
POST   /api/v1/admin/users/{id}/assign-curator/  { curator_id }
```

### 7.4. Скелетные модули
**Endpoint'ов нет.** Только модели + Django Admin.

### 7.5. Системные
```
GET    /api/v1/health/                         → { status: "ok", db, redis }
GET    /api/docs/                              → Swagger UI
GET    /api/schema/                            → OpenAPI 3 JSON
GET    /admin/                                 → Django Admin
```

### 7.6. Throttling

- Анонимные: 60/min
- Авторизованные: 600/min
- `/auth/register/init/`, `/auth/password-reset/init/`: 3/10min на телефон
- `/auth/login/`: 5/15min на телефон
- `/auth/register/verify/`, `/password-reset/verify/`: 5 попыток на verification flow

### 7.7. Стандарт ошибок

```json
{
  "error": {
    "code": "INVALID_OTP_CODE",
    "message": "Код подтверждения неверный или истёк.",
    "details": { ... }
  }
}
```

Ошибки валидации полей: 400 с `details: { field: ["error message"] }`.

---

## 8. Docker и деплой

### 8.1. `docker-compose.yml` (dev)

Сервисы:
- **`web`** — Django runserver, монтирует код, hot-reload, порт 8000
- **`postgres`** — PostgreSQL 16, named volume `postgres_data`
- **`redis`** — Redis 7-alpine
- **`celery`** — celery worker (та же image что web)
- **`celery-beat`** — celery beat scheduler

### 8.2. `docker-compose.prod.yml`

- **`web`** — gunicorn (3 workers), без hot-reload
- **`nginx`** — обратный прокси, SSL termination, статика, медиа
- **`postgres`**, **`redis`** — опциональные (обычно managed)
- **`celery`**, **`celery-beat`** — production-режим

### 8.3. `docker/Dockerfile.dev`

- Python 3.12-slim, `uv` для зависимостей
- Non-root user
- Кэшируемые слои (зависимости копируются отдельно от кода)
- `CMD: python manage.py runserver 0.0.0.0:8000`

### 8.4. `docker/Dockerfile.prod`

Multi-stage:
1. **builder** — ставит зависимости в virtualenv через `uv`
2. **runtime** — python-slim, копирует venv и код, выполняет `collectstatic`
- `CMD: gunicorn config.wsgi:application --workers=3 --bind=0.0.0.0:8000`

### 8.5. `.env.example`

```
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=change-me
DATABASE_URL=postgres://qadam:qadam@postgres:5432/qadam
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

JWT_ACCESS_LIFETIME_MINUTES=15
JWT_REFRESH_LIFETIME_DAYS=30

OTP_TTL_SECONDS=300
OTP_RATE_LIMIT_PER_PHONE=3
OTP_RATE_LIMIT_WINDOW_SECONDS=600

SMS_PROVIDER=console
WHATSAPP_API_URL=
WHATSAPP_API_TOKEN=

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
ALLOWED_HOSTS=localhost,127.0.0.1

SENTRY_DSN=
LOG_LEVEL=INFO
```

### 8.6. `Makefile`

```
make up          # docker-compose up
make down
make logs
make shell       # bash в web-контейнере
make dj          # ./manage.py shell_plus
make migrate
make migrations  # makemigrations
make test
make lint        # ruff check
make format      # ruff format
make superuser   # createsuperuser
make seed        # тестовые фикстуры
```

### 8.7. SmsProvider адаптер

```
services/sms/base.py      — abstract class SmsProvider, метод send(phone, message)
services/sms/console.py   — ConsoleProvider: print + logger.info
services/sms/whatsapp.py  — WhatsAppProvider: stub, raises NotImplementedError, готов к реальному API
```

Выбор провайдера — через env `SMS_PROVIDER=console|whatsapp` и factory в settings.

---

## 9. Тесты и качество кода

### 9.1. Покрытие тестами

- ✅ **Auth flow** (~25-30 тестов): все 3 шага регистрации, login, refresh, logout, logout-all, password reset, rate limits, expired/invalid OTP, неправильный пароль, заблокированный пользователь, RBAC permissions для каждой роли.
- ✅ **Profile API** (~10-15 тестов): чтение, edit allowed/forbidden, dashboard structure, curator info.
- ✅ **User admin endpoints** (~8 тестов): CRUD под SUPER_ADMIN, отказ доступа другим ролям.
- ✅ **SmsProvider**: интерфейс + ConsoleProvider пишет код в логи.
- ✅ **Smoke-тест скелетов**: миграции применяются, Django Admin регистрирует все модели без ошибок.

**Цель:** ≥ 90 % coverage в `apps/accounts/` и `apps/profiles/`. Глобальный coverage будет ниже из-за скелетов.

### 9.2. Качество кода

- **`ruff`** — линтинг и форматирование (одна команда)
- **`mypy`** + `django-stubs` — без strict-режима, чтобы не блокировать темп
- **pre-commit hook** — ruff check + ruff format + миграции up-to-date check
- **Makefile-команды** готовы к подключению в любой CI

### 9.3. Документация

- `README.md` — quick start, краткое описание стека и архитектуры
- `docs/architecture.md` — диаграмма модулей, связи, ответственности
- `docs/auth-flow.md` — последовательные диаграммы для регистрации/логина/восстановления
- `docs/api.md` — ссылка на `/api/docs/` + примеры curl
- Inline docstrings — только где нетривиально

---

## 10. План работ (10 рабочих дней)

| День | Задача |
|------|--------|
| 1 | Скелет проекта: Docker, settings, базовые dependencies, `apps/common/`, ruff/pytest, Makefile |
| 2 | `apps/accounts/`: User модель, миграции, Django Admin, JWT настройка |
| 3 | Auth flow: регистрация (3 шага), `services/sms/` адаптер, OTP в Redis, rate limits |
| 4 | Auth flow: login, logout, logout-all, refresh, password reset, LoginEvent, тесты |
| 5 | RBAC: permission классы, тесты для всех ролей, `apps/users/` admin endpoints |
| 6 | `apps/profiles/`: StudentProfile, API endpoints, dashboard заготовка, тесты |
| 7 | Скелет моделей: `learning`, `testing`, `payments` + Django Admin |
| 8 | Скелет моделей: `gamification`, `notifications`, `universities`, `ai_tutor`, `crm` + Django Admin |
| 9 | django-modeltranslation интеграция, проверка KZ/RU полей, swagger полировка |
| 10 | Документация (README, architecture.md, auth-flow.md), production Dockerfile, финальный прогон тестов, smoke-test полного флоу |

**Резерв при отставании:** первыми режутся дополнительные admin endpoints (день 5) и часть скелетов геймификации (день 8 — оставить только базовые League/Star).

---

## 11. Открытые вопросы / следующие шаги

После завершения фундамента, в порядке приоритета (по ТЗ):

1. **Неделя 3-4:** Модуль обучения (Класс → Предмет → Раздел → Тема → Урок), бизнес-логика последовательного открытия, мини-тесты, начисление звёзд.
2. **Неделя 5:** ЕНТ-тестирование (полный формат, таймер, подсчёт баллов, результаты).
3. **Неделя 6:** Аналитика (графики результатов, история тестов, работа над ошибками).
4. **Неделя 7:** Платежи и подписки (реальная интеграция Kaspi / Halyk, paywall).
5. **Неделя 8:** AI Tutor MVP (интеграция с Gemini, режим помощника).

Каждый из этих этапов потребует отдельного брейнсторминга и дизайн-документа.
