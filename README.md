# Qadam Backend

Образовательная платформа Qadam — backend на Django 5 для подготовки к ЕНТ.

Реализованные спринты:

- **Неделя 1-2** ([фундамент](docs/superpowers/specs/2026-04-27-qadam-backend-foundation-design.md)) — auth по телефону + код, профили, RBAC, скелеты всех 13 модулей в admin, инфраструктура (Docker, Redis, Celery, PostgreSQL).
- **Неделя 3-4** ([модуль обучения](docs/superpowers/specs/2026-04-28-qadam-learning-module-design.md)) — иерархия Класс → Предмет → Раздел → Тема → Урок, мини-тесты со server-driven скорингом, paywall, sequential unlock, звёзды, дашборд на реальных данных.

Не реализованные пока модули (модели + admin есть, эндпоинтов нет):
ЕНТ-тестирование, платежи Kaspi/Halyk, AI Tutor, геймификация (лиги/кланы/турниры), уведомления.

Полная спецификация: [docs/superpowers/specs/2026-04-27-qadam-backend-foundation-design.md](docs/superpowers/specs/2026-04-27-qadam-backend-foundation-design.md)

---

## Quick start

Требования: **Docker Desktop** (или Docker Engine + Compose плагин). Больше ничего ставить локально не нужно.

```bash
# 1. Клонировать репо
git clone <url> qadam && cd qadam

# 2. Скопировать env
cp .env.example .env
# при необходимости отредактируйте SECRET_KEY и пр.

# 3. Поднять стек
make up        # foreground; используйте make up-d для background

# 4. В соседнем терминале — миграции и суперюзер
make migrate
make superuser

# 5. Открыть в браузере
#  - API:        http://localhost:8000/api/v1/
#  - Swagger UI: http://localhost:8000/api/docs/
#  - Django Admin: http://localhost:8000/admin/
```

Всё. Health-check можно проверить через `curl http://localhost:8000/api/v1/health/`.

---

## Стек

- **Python 3.12** + **Django 5.1** + **DRF**
- **PostgreSQL 16** — основная БД
- **Redis 7** — кэш OTP, JWT blacklist, throttling, Celery broker
- **Celery + celery-beat** — фоновые задачи
- **JWT** через `djangorestframework-simplejwt` (rotation, blacklist)
- **drf-spectacular** — OpenAPI 3 / Swagger UI на `/api/docs/`
- **django-modeltranslation** — мультиязычные поля (KZ + RU)
- **pytest + pytest-django + factory_boy** — тесты
- **ruff** — линтер и форматтер
- **uv** — менеджер зависимостей

---

## Структура

```
src/
├── config/                  # Django settings (base/dev/prod), urls, celery
├── apps/
│   ├── common/              # TimestampedModel, exception handler, health
│   ├── accounts/            # ★ User, auth (3-step register, login, JWT, RBAC)
│   ├── profiles/            # ★ StudentProfile, dashboard, curator
│   ├── learning/            # скелет: Class/Subject/Section/Topic/Lesson/Quiz/...
│   ├── testing/             # скелет: ENT тесты, банк вопросов
│   ├── payments/            # скелет: Tariff/Subscription/Payment
│   ├── gamification/        # скелет: League/Star/Avatar/Tournament/Clan/...
│   ├── notifications/       # скелет: Notification + шаблоны
│   ├── universities/        # скелет: Region/City/University/Speciality
│   ├── ai_tutor/            # скелет: Conversation/Message
│   └── crm/                 # скелет: SalesNote/StatusChangeLog
├── services/
│   └── sms/                 # SmsProvider адаптер (console + whatsapp заглушка)
└── tests/                   # параллельно apps/

docker/
├── Dockerfile.dev
└── Dockerfile.prod
```

`★` — модули с полной реализацией; остальные — модели + админка, эндпоинты на следующих этапах.

---

## Команды (Makefile)

| Команда | Описание |
|---|---|
| `make up` | Поднять весь стек (foreground) |
| `make up-d` | То же, в background |
| `make down` | Остановить |
| `make build` | Пересобрать образы |
| `make logs` | Хвостить логи |
| `make shell` | Bash внутри `web` контейнера |
| `make dj` | Django shell_plus |
| `make migrate` | Применить миграции |
| `make migrations` | Создать новые миграции |
| `make test` | Прогнать тесты |
| `make test-cov` | Тесты + coverage report |
| `make lint` | ruff check |
| `make format` | ruff format + auto-fix |
| `make superuser` | Создать суперюзера |
| `make clean` | Снести контейнеры, тома, кэши |

### Демо-контент

```bash
docker compose exec web python manage.py seed_learning
```

Создаёт 2 предмета (Математика, Физика), по 3 урока с мини-тестами (правильный ответ всегда `B`), один тариф «Стандарт» и одного куратора. Удобно для ручного QA через Swagger UI.

---

## Auth-флоу (что уже работает)

**Регистрация (3 шага):**

```bash
# Шаг 1 — отправить код (в dev код пишется в логи `web` контейнера)
curl -X POST http://localhost:8000/api/v1/auth/register/init/ \
  -H 'Content-Type: application/json' \
  -d '{"phone": "+77001234567"}'

# Достать код из логов — make logs | grep "sms:console"

# Шаг 2 — проверить код, получить verification_token
curl -X POST http://localhost:8000/api/v1/auth/register/verify/ \
  -H 'Content-Type: application/json' \
  -d '{"phone": "+77001234567", "code": "123456"}'

# Шаг 3 — заполнить профиль, получить JWT pair
curl -X POST http://localhost:8000/api/v1/auth/register/complete/ \
  -H 'Content-Type: application/json' \
  -d '{
    "verification_token": "<из шага 2>",
    "password": "StrongPass123!",
    "name": "Иван Иванов",
    "parent_phone": "+77001111111",
    "grade": 11,
    "learning_language": "ru"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"phone": "+77001234567", "password": "StrongPass123!"}'
```

Полный список эндпоинтов и схема запросов/ответов — в [Swagger UI](http://localhost:8000/api/docs/).

---

## SMS / WhatsApp

OTP-коды отправляются через адаптер `services/sms/`:

- В dev `SMS_PROVIDER=console` — код пишется в логи (`make logs | grep sms:console`).
- Для prod есть заглушка `WhatsAppSmsProvider` — нужно вписать реальный API URL/токен и реализовать тело `send()`.

Подробнее: см. `src/services/sms/whatsapp.py`.

---

## Тесты

```bash
make test          # быстрый прогон
make test-cov      # с покрытием
```

Покрытие фокусируется на `apps/accounts/` и `apps/profiles/` (auth-флоу, RBAC, profile API). Скелетные модули покрываются smoke-тестами (`tests/test_smoke.py`): миграции применяются, все модели зарегистрированы в admin, OpenAPI-схема собирается без ошибок.

---

## Что дальше

Дорожная карта (по ТЗ):

| Неделя | Тема | Статус |
|---|---|---|
| 1-2 | Фундамент (auth, профили, инфра) | ✅ |
| 3-4 | Модуль обучения (мини-тесты, paywall, звёзды) | ✅ |
| 5 | ЕНТ-тестирование (полный формат, таймер, баллы) | ⏳ |
| 6 | Аналитика (графики, история, работа над ошибками) | ⏳ |
| 7 | Платежи Kaspi/Halyk + paywall фронт | ⏳ |
| 8 | AI Tutor MVP (Gemini + Qdrant) | ⏳ |

Каждая неделя — отдельный брейнсторм + спека + план реализации.

---

## Ссылки

- [Деплой на production-сервер](docs/deployment.md) — пошаговый гайд (Docker + Caddy + автоматический SSL)
- [GitHub Actions CI/CD](docs/cicd.md) — автотесты на PR + автодеплой на push в main
- [Спецификация фундамента](docs/superpowers/specs/2026-04-27-qadam-backend-foundation-design.md)
- [Спецификация модуля обучения](docs/superpowers/specs/2026-04-28-qadam-learning-module-design.md)
- [Auth-флоу подробно](docs/auth-flow.md)
- [Learning-флоу](docs/learning-flow.md) — гейтинг, paywall, sequence-диаграмма мини-теста
- [Архитектура](docs/architecture.md)
