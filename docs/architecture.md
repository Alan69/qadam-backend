# Qadam Backend — Архитектура

## Слои

```
┌──────────────────────────────────────────────────────────────┐
│                        HTTP / DRF                            │
│  views.py / admin_views.py — тонкие, только HTTP-обвязка     │
└────────────────────────────────┬─────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────┐
│                     Бизнес-сервисы                           │
│  services/ — вся логика операций (registration, login, ...)  │
│  Без зависимости от HTTP / request                           │
└────────────────────────────────┬─────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────┐
│                       Модели + ORM                           │
│  models.py — структура данных, валидация, constraints в БД   │
└────────────────────────────────┬─────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────┐
│                    Инфраструктура                            │
│  PostgreSQL (данные) | Redis (OTP, blacklist, throttling)    │
│  Celery (фоновые задачи) | services/sms/ (внешние провайдеры)│
└──────────────────────────────────────────────────────────────┘
```

## Принципы

1. **Тонкие views.** View достаёт данные из request, валидирует через serializer, вызывает сервис, оборачивает ответ. Бизнес-правил во view нет.
2. **Бизнес-логика — в `services/`.** Это обычные функции (или классы) без зависимости от Django HTTP. Их легко тестировать и переиспользовать в Celery-задачах / management-командах / WebSocket'ах.
3. **Constraints — в БД.** Где можно (например, "одна активная подписка на пользователя") — выражаем через `UniqueConstraint` с `condition`. БД ловит race conditions, которые приложение могло бы пропустить.
4. **Адаптеры для внешних систем.** Всё, что зависит от внешнего API (SMS, платёжки, AI), скрывается за абстрактным интерфейсом. В dev — заглушка, в prod — реальная реализация. Переключение через `settings`.
5. **Единый формат ошибок.** Все API-ошибки через `apps.common.exceptions.QadamAPIError`, обработчик приводит ответ к виду `{"error": {"code", "message", "details"}}`. Клиент пишет один обработчик.

## Ключевые потоки

### Регистрация
1. **POST `/auth/register/init/`** → `services/registration.py:request_registration_code()` → генерирует OTP, кладёт в Redis с TTL, вызывает `services/sms/` адаптер.
2. **POST `/auth/register/verify/`** → `services/otp.py:verify_otp()` → валидирует код, удаляет из Redis (одноразовость), выдаёт `verification_token` (короткоживущий JWT с `purpose=register`).
3. **POST `/auth/register/complete/`** → `services/registration.py:complete_registration()` → создаёт `User` + `StudentProfile` в одной транзакции, назначает куратора (round-robin), выдаёт JWT pair.

### Login
1. **POST `/auth/login/`** → `services/login.py:authenticate_and_login()` → проверяет credentials, ведёт счётчик неудач в Redis, пишет `LoginEvent` в БД, выдаёт JWT pair.

### JWT-операции
- **`/auth/refresh/`** — refresh rotation (старый сразу инвалидируется).
- **`/auth/logout/`** — blacklist refresh-токена в Redis.
- **`/auth/logout-all/`** — blacklist всех outstanding refresh-токенов пользователя.

### Восстановление пароля
Аналогично регистрации: `init` → `verify` → `confirm` (с другим `purpose` в verification-токене, чтобы нельзя было использовать токен из другого флоу).

## RBAC

Роль хранится на `User.role` (enum: STUDENT / CURATOR / CONTENT_MANAGER / SALES_MANAGER / SUPER_ADMIN). Permission классы в `apps/accounts/permissions.py`:

- `IsStudent`, `IsCurator`, `IsContentManager`, `IsSalesManager`, `IsSuperAdmin` — по одной роли.
- `HasAnyRole.of(*roles)` — для случаев "любой из".

На view-уровне: `permission_classes = [IsAuthenticated, IsStudent]`.

## Зависимости между приложениями

```
accounts ── базовый, ни от кого не зависит
profiles ── зависит от accounts, universities, learning
learning ── базовый (для контента)
testing ── зависит от learning
payments ── зависит от learning (через Tariff.subjects)
gamification ── зависит от learning (через Star.lesson)
notifications ── только зависит от accounts (User)
universities ── зависит от learning (Speciality.required_subjects)
ai_tutor ── зависит от learning (Conversation.lesson)
crm ── зависит от profiles
common ── базовый (TimestampedModel и пр.)
```

Циклов нет. `accounts` ← `profiles` односторонне; `profiles` импортируется из `accounts/services/registration.py` через late import (внутри функции), чтобы избежать circular import.

## Многоязычность

`django-modeltranslation` добавляет суффиксные поля `*_kz`, `*_ru` к контентным моделям (Subject, Lesson, NotificationTemplate, etc.). Активный язык запроса определяется через `Accept-Language` header или `?lang=kk|ru`. Для UI самой админки — стандартный механизм Django i18n.

Регистрации переводов лежат в `apps/<name>/translation.py` (автоматически подхватываются при старте Django).

## Where things live

| Хочу... | Смотри... |
|---|---|
| Изменить TTL OTP / лимиты | `.env` (`OTP_*` переменные), `config/settings/base.py:QADAM` |
| Добавить новую роль | `apps/accounts/models.py:User.Role` + `apps/accounts/permissions.py` |
| Добавить новый OTP-флоу | `apps/accounts/services/otp.py:OTPPurpose` + новый сервис рядом с `registration.py` |
| Подключить реальный WhatsApp | `services/sms/whatsapp.py` (заполнить тело `send()`) + `.env` (`SMS_PROVIDER=whatsapp`, креды) |
| Изменить формат ошибок | `apps/common/exceptions.py:qadam_exception_handler` |
| Добавить переводимое поле | `apps/<app>/translation.py`, потом `make migrations` |
