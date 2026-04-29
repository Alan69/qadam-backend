# Деплой на production-сервер

Этот гайд — для деплоя Qadam backend на Ubuntu-сервер с доменом `api.qadam-app.kz`. Подход: Docker Compose + Caddy с автоматическим Let's Encrypt SSL.

## Что в итоге получите

- `https://api.qadam-app.kz/api/v1/` — основной API
- `https://api.qadam-app.kz/api/docs/` — Swagger UI
- `https://api.qadam-app.kz/admin/` — Django Admin
- Автоматическое обновление SSL сертификата через Caddy
- Postgres + Redis + Celery worker + Celery beat в Docker

---

## Шаг 0. Перед деплоем — DNS + безопасность

### DNS

В DNS-провайдере домена `qadam-app.kz` создайте A-запись:

```
Тип:   A
Имя:   api
Адрес: 213.155.22.86
TTL:   3600
```

И AAAA если нужен IPv6:
```
Тип:   AAAA
Имя:   api
Адрес: 2a00:5da0:2005:1::80b
TTL:   3600
```

Проверка (с локальной машины, ПОСЛЕ распространения DNS — обычно 5-30 минут):
```bash
dig api.qadam-app.kz +short
# Должно вернуть 213.155.22.86
```

⚠️ **Важно:** Caddy получает SSL сертификат через HTTP-01 challenge. Без рабочего DNS первый запуск упадёт с ошибкой `no valid A/AAAA record`. Сначала DNS — потом запуск.

### SSH-ключ вместо пароля (опционально, но рекомендую)

С локальной машины:

```bash
# Если ещё нет ключа
ssh-keygen -t ed25519 -C "ваш-email@example.com"

# Скопировать на сервер (введёт пароль один раз)
ssh-copy-id ubuntu@213.155.22.86

# Проверка — должна войти без пароля
ssh ubuntu@213.155.22.86

# После этого можно отключить вход по паролю в /etc/ssh/sshd_config:
#   PasswordAuthentication no
```

---

## Шаг 1. Установка Docker + Compose на сервере

```bash
ssh ubuntu@213.155.22.86

# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker (официальный скрипт)
curl -fsSL https://get.docker.com | sudo sh

# Добавляем юзера в группу docker (чтобы не нужно было sudo)
sudo usermod -aG docker ubuntu

# Применить — нужно перелогиниться
exit
ssh ubuntu@213.155.22.86

# Проверяем
docker --version
docker compose version
```

---

## Шаг 2. Клонирование репо и настройка .env

```bash
# Клонируем репозиторий
cd ~
git clone https://github.com/Alan69/qadam-backend.git
cd qadam-backend

# Создаём .env из шаблона
cp .env.prod.example .env

# Генерируем SECRET_KEY и пароль для Postgres
python3 -c 'import secrets; print("SECRET_KEY=" + secrets.token_urlsafe(50))'
python3 -c 'import secrets; print("POSTGRES_PASSWORD=" + secrets.token_urlsafe(32))'

# Открываем .env и заполняем:
nano .env
```

В `.env` обязательно отредактируйте:

| Переменная | Значение |
|---|---|
| `SECRET_KEY` | результат первой команды выше |
| `POSTGRES_PASSWORD` | результат второй команды |
| `DATABASE_URL` | `postgres://qadam:<тот-же-POSTGRES_PASSWORD>@postgres:5432/qadam` |
| `ALLOWED_HOSTS` | `api.qadam-app.kz` |
| `DOMAIN` | `api.qadam-app.kz` |
| `CORS_ALLOWED_ORIGINS` | URL фронтенда (например `https://qadam-app.kz`) |

Сохраняем (`Ctrl+O`, `Enter`, `Ctrl+X`).

⚠️ Проверьте: пароль в `POSTGRES_PASSWORD` и в `DATABASE_URL` **должны совпадать**.

---

## Шаг 3. Открыть порты на сервере

```bash
# Если используется ufw (стандартный firewall Ubuntu)
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

---

## Шаг 4. Первый запуск

```bash
cd ~/qadam-backend

# Сборка образов (3-5 минут)
docker compose -f docker-compose.prod.yml build

# Запуск стека в фоне
docker compose -f docker-compose.prod.yml up -d

# Смотрим логи (Ctrl+C — выйти, контейнеры продолжат работать)
docker compose -f docker-compose.prod.yml logs -f
```

Что должно быть в логах:
- `postgres-1`: `database system is ready to accept connections`
- `redis-1`: `Ready to accept connections`
- `caddy-1`: что-то вроде `certificate obtained successfully` (получение SSL сертификата)
- `web-1`: `Listening at: http://0.0.0.0:8000`

Если Caddy жалуется на DNS — значит шаг 0 ещё не отработал, подождите распространения DNS и перезапустите: `docker compose -f docker-compose.prod.yml restart caddy`.

---

## Шаг 5. Миграции и суперпользователь

```bash
# Применяем миграции
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Создаём суперюзера для входа в /admin/
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
# Введёт: phone (например +77001234567), password
```

---

## Шаг 6. Проверка

С локальной машины:

```bash
# Health-check
curl https://api.qadam-app.kz/api/v1/health/
# Ожидается: {"status":"ok","db":true,"redis":true}

# Swagger UI — открыть в браузере
# https://api.qadam-app.kz/api/docs/

# Django Admin — открыть в браузере
# https://api.qadam-app.kz/admin/
# Войти под суперюзером
```

Если сертификат уже выдан — должна быть зелёная иконка замка в браузере.

---

## Шаг 7. Загрузить демо-контент (опционально)

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py seed_learning
```

Создаст 2 предмета (Математика, Физика), 6 уроков с мини-тестами и тариф «Стандарт».

---

## Управление в production

### Перезапуск после `git pull`

```bash
cd ~/qadam-backend
git pull origin main

# Если изменились зависимости или Dockerfile — пересобрать образ
docker compose -f docker-compose.prod.yml build

# Применить миграции если есть новые
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Применить collectstatic если изменилась статика (для admin / Swagger)
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Перезапуск web (без даунтайма postgres/redis)
docker compose -f docker-compose.prod.yml up -d --no-deps web celery celery-beat
```

### Просмотр логов

```bash
# Все сервисы
docker compose -f docker-compose.prod.yml logs -f

# Только Django
docker compose -f docker-compose.prod.yml logs -f web

# Caddy (полезно при проблемах с SSL)
docker compose -f docker-compose.prod.yml logs -f caddy
```

### Бэкап базы

```bash
# Дамп Postgres в файл на сервере
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U qadam qadam | gzip > ~/backups/qadam-$(date +%Y%m%d-%H%M).sql.gz

# Восстановление
gunzip < backup.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U qadam qadam
```

Рекомендую настроить cron на ежедневный бэкап с ротацией.

### Остановка / запуск

```bash
docker compose -f docker-compose.prod.yml down       # стоп
docker compose -f docker-compose.prod.yml up -d      # старт
docker compose -f docker-compose.prod.yml restart    # перезапуск всех сервисов
```

---

## Troubleshooting

### «no valid A/AAAA record found»
DNS ещё не распространился. Подождите 5-30 минут, проверьте `dig api.qadam-app.kz`.

### Caddy не выдаёт сертификат
Проверьте что порты 80 и 443 открыты в firewall + DNS правильно настроен. Логи: `docker compose -f docker-compose.prod.yml logs caddy`.

### `502 Bad Gateway`
Web-контейнер упал. Проверьте `docker compose -f docker-compose.prod.yml logs web`. Часто причина — неправильный `DATABASE_URL` или `SECRET_KEY` в `.env`.

### Миграции зависли
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U qadam qadam -c "SELECT * FROM pg_stat_activity;"
# Найти зависший запрос, прибить
```

### Порты 80/443 заняты
Проверьте что на сервере не запущен apache/nginx как системный сервис:
```bash
sudo systemctl status nginx apache2
sudo systemctl stop nginx apache2  # если запущены
sudo systemctl disable nginx apache2
```

---

## Что улучшить дальше (вне MVP)

1. **Managed Postgres** — вынести БД из Docker на managed сервис (DigitalOcean Managed Database, AWS RDS, etc.) — надёжнее, бэкапы из коробки.
2. **CI/CD** — GitHub Actions, который при пуше в `main` автоматически SSH'ится на сервер, делает `git pull` и перезапуск.
3. **Sentry** — раскомментировать `SENTRY_DSN` в `.env` для трекинга ошибок.
4. **Мониторинг** — Uptime-checker (Uptime Robot, Better Stack) на `/api/v1/health/`.
5. **Реальный WhatsApp-провайдер** — заполнить `WHATSAPP_API_URL` + `WHATSAPP_API_TOKEN` и реализовать тело `services/sms/whatsapp.py:send()`.
