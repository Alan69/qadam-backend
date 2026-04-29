# GitHub Actions CI / CD

Этот гайд — про настройку автоматического тестирования и деплоя через GitHub Actions.

## Что у вас будет

- **На каждый push и PR в `main`:** запускаются `lint` + `tests` (с PostgreSQL + Redis сервисами)
- **На push в `main` (после прохождения CI):** автоматический деплой на сервер через SSH
- **Ручной триггер:** в GitHub UI → Actions → Deploy → Run workflow

---

## Шаг 1. Сгенерировать deploy-ключ

Создайте отдельный SSH-ключ специально для GitHub Actions (НЕ переиспользуйте свой личный — отдельный ключ можно отозвать без потери доступа).

### На локальной машине

```bash
ssh-keygen -t ed25519 -f ~/.ssh/qadam_deploy -N "" -C "github-actions@qadam-backend"
```

Создаст два файла:
- `~/.ssh/qadam_deploy` — приватный ключ (пойдёт в GitHub Secrets)
- `~/.ssh/qadam_deploy.pub` — публичный ключ (положим на сервер)

### Положить публичный ключ на сервер

```bash
ssh-copy-id -i ~/.ssh/qadam_deploy.pub ubuntu@213.155.22.86

# Проверка — вход без пароля по новому ключу
ssh -i ~/.ssh/qadam_deploy ubuntu@213.155.22.86 "echo OK"
```

Должно вернуть `OK` без запроса пароля.

---

## Шаг 2. Добавить секреты в GitHub

Откройте репо: https://github.com/Alan69/qadam-backend → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Добавьте 3 секрета:

| Имя | Значение |
|---|---|
| `DEPLOY_HOST` | `213.155.22.86` |
| `DEPLOY_USER` | `ubuntu` |
| `DEPLOY_SSH_KEY` | **полное содержимое** файла `~/.ssh/qadam_deploy` (приватный ключ) — `cat ~/.ssh/qadam_deploy` и скопируйте всё, включая строки `-----BEGIN ...-----` и `-----END ...-----` |

(Опционально: `DEPLOY_PORT` если SSH не на 22)

⚠️ Приватный ключ **никогда** не коммитьте в репо — только в GitHub Secrets.

---

## Шаг 3. Проверить что workflows на месте

После того как `.github/workflows/` будет в репо (после `git push`), откройте в GitHub:

```
https://github.com/Alan69/qadam-backend/actions
```

Должны быть видны два workflow: **CI** и **Deploy**.

---

## Шаг 4. Первый прогон

```bash
# Локально:
git pull origin main   # подтянуть .github/workflows/
# сделать любую правку или просто:
git commit --allow-empty -m "trigger ci"
git push origin main
```

Теперь:
1. Открывается страница Actions → видна задача **CI**.
2. Внутри CI запускаются параллельно **Lint** и **Tests**.
3. Если оба зелёные → автоматически стартует **Deploy** на сервер.
4. Через 1-2 минуты сайт обновится: `curl https://api.qadam-app.kz/api/v1/health/`.

---

## Что происходит на сервере при деплое

[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) запускает по SSH такой скрипт:

```bash
cd ~/qadam-backend
git fetch origin main
git reset --hard origin/main          # ← важно: локальные правки на сервере СМЕТАЮТСЯ
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker image prune -f
```

Ключевые решения:

- **`git reset --hard origin/main`** — на сервере не должно быть несинхронных правок. Если они есть — деплой их сметёт. Если нужно временно изменить код на сервере (для отладки) — делайте это через `docker compose exec`, не правя файлы напрямую.
- **`run --rm`** — миграции применяются **новым** образом через одноразовый контейнер. Если миграция упала, `set -e` остановит скрипт и старые контейнеры продолжат работать (минимизация даунтайма).
- **`up -d --remove-orphans`** — пересоздаёт только те сервисы, у которых поменялся образ (postgres / redis не трогаются).
- **`docker image prune -f`** — чистит старые слои чтобы не забивался диск.

---

## Когда деплой НЕ запускается

| Ситуация | Что делать |
|---|---|
| CI упал (lint или tests красные) | Зайти в Actions → CI → посмотреть лог конкретного шага. Деплой не пойдёт пока не позеленеет. |
| Push в feature-ветку | CI пробежит, но деплой только на `main`. |
| PR из форка | CI пробежит, деплой не пойдёт (нужен push, не PR). |
| Хочется задеплоить руками | Actions → Deploy → **Run workflow** → Run. |

---

## Откат (rollback)

Если новая версия сломала прод:

```bash
ssh ubuntu@213.155.22.86
cd ~/qadam-backend
git log --oneline | head    # найти SHA рабочей версии
git reset --hard <SHA>
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml up -d
```

⚠️ Если миграция накатила необратимые изменения схемы (drop column, drop table) — простой `git reset` не вернёт схему. В таких случаях нужен бэкап БД. Поэтому см. [`deployment.md` → Бэкап базы](deployment.md#бэкап-базы).

---

## Troubleshooting

### Deploy упал с `Permission denied (publickey)`
Публичный ключ не добавлен в `~/.ssh/authorized_keys` на сервере, или приватный ключ в `DEPLOY_SSH_KEY` неполный/повреждён. Проверьте: `cat ~/.ssh/qadam_deploy.pub` и `cat ~/.ssh/qadam_deploy` — оба должны быть.

### Tests падают только в CI, локально зелёные
Чаще всего — другая версия PostgreSQL или env-переменная отличается. Сравните `make test` локально (внутри Docker — он использует те же версии) и логи CI.

### CI слишком медленный
Кэшируйте установку зависимостей. Сейчас `astral-sh/setup-uv@v3` и `uv pip install` уже довольно быстры (10-15 сек), но при росте можно добавить `actions/cache` для `~/.cache/uv`.

### Деплой не запускается после CI
- Проверьте что push был именно в `main`, а не в другую ветку.
- Откройте deploy.yml workflow в Actions: какой статус? Если skipped — посмотрите conditions (например `workflow_run.conclusion == 'success'`).

---

## Что улучшить дальше

1. **Branch protection** — в GitHub → Settings → Branches → Rule: require CI pass для merge в main, запретить push в main без PR.
2. **Slack / Telegram уведомления** на failed deploy — добавить step в deploy.yml (action `8398a7/action-slack` или telegram bot).
3. **Smoke-test после деплоя** — `curl -f https://api.qadam-app.kz/api/v1/health/` в конце deploy.yml, если падает — откатиться.
4. **Отдельный staging-сервер** — выделить ветку `staging` с отдельным деплоем, чтобы тестировать перед prod.
