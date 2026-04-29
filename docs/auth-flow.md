# Auth-флоу

## Регистрация

```
Клиент                        API                       Redis        SMS        DB
  │                            │                          │           │          │
  │ POST /register/init/       │                          │           │          │
  │ { phone }                  │                          │           │          │
  ├───────────────────────────▶│                          │           │          │
  │                            │ check User.exists?       │           │          │
  │                            ├──────────────────────────┼───────────┼─────────▶│
  │                            │ check rate limit         │           │          │
  │                            ├─────────────────────────▶│           │          │
  │                            │ generate OTP, store      │           │          │
  │                            ├─────────────────────────▶│           │          │
  │                            │ provider.send(phone, msg)│           │          │
  │                            ├──────────────────────────┼──────────▶│          │
  │ 200 { expires_in: 300 }    │                          │           │          │
  │◀───────────────────────────┤                          │           │          │
  │                            │                          │           │          │
  │ POST /register/verify/     │                          │           │          │
  │ { phone, code }            │                          │           │          │
  ├───────────────────────────▶│                          │           │          │
  │                            │ check verify-attempts    │           │          │
  │                            ├─────────────────────────▶│           │          │
  │                            │ get OTP, compare         │           │          │
  │                            ├─────────────────────────▶│           │          │
  │                            │ delete OTP (one-time)    │           │          │
  │                            ├─────────────────────────▶│           │          │
  │                            │ issue JWT (purpose=reg)  │           │          │
  │ 200 { verification_token } │                          │           │          │
  │◀───────────────────────────┤                          │           │          │
  │                            │                          │           │          │
  │ POST /register/complete/   │                          │           │          │
  │ { token, password, ... }   │                          │           │          │
  ├───────────────────────────▶│                          │           │          │
  │                            │ decode token             │           │          │
  │                            │ validate password        │           │          │
  │                            │ create User+Profile (TX) │           │          │
  │                            ├──────────────────────────┼───────────┼─────────▶│
  │                            │ pick curator (round-robin)           │          │
  │                            ├──────────────────────────┼───────────┼─────────▶│
  │                            │ assign curator           │           │          │
  │                            │ issue JWT pair           │           │          │
  │ 201 { access, refresh,     │                          │           │          │
  │       user }               │                          │           │          │
  │◀───────────────────────────┤                          │           │          │
```

**Лимиты:**
- На `init/` — 3 запроса в 10 минут на номер.
- На `verify/` — 5 неверных вводов, потом блок на 15 минут.
- TTL OTP-кода — 5 минут.
- TTL `verification_token` — 10 минут.

**Возможные ошибки:**

| Код | Когда | HTTP |
|---|---|---|
| `PHONE_ALREADY_REGISTERED` | На init: пользователь уже есть | 400 |
| `OTP_RATE_LIMIT` | Превышен лимит запросов кода | 429 |
| `INVALID_OTP_CODE` | Неверный или истёкший код | 400 |
| `OTP_VERIFY_LOCKED` | 5 неверных попыток подряд | 429 |
| `INVALID_VERIFICATION_TOKEN` | На complete: токен невалиден / истёк / не для этого флоу | 400 |
| `VALIDATION_ERROR` | Поля не прошли валидацию | 400 |

---

## Login

```
Клиент → POST /auth/login/ { phone, password }
       ← 200 { access, refresh, user }
```

**Лимиты:** 5 неудачных попыток на номер → блок на 15 минут.

**Возможные ошибки:**

| Код | HTTP |
|---|---|
| `INVALID_CREDENTIALS` | 401 |
| `ACCOUNT_INACTIVE` | 403 |
| `LOGIN_RATE_LIMIT` | 429 |

Каждая попытка (успешная или нет) пишется в `LoginEvent`.

---

## Восстановление пароля

Аналогично регистрации, 3 шага:

1. `POST /auth/password-reset/init/` — `{ phone }` → отправляется код. *(Существование пользователя НЕ раскрывается — ответ всегда одинаковый.)*
2. `POST /auth/password-reset/verify/` — `{ phone, code }` → выдаётся `reset_token`.
3. `POST /auth/password-reset/confirm/` — `{ reset_token, new_password }` → пароль меняется.

Verification-токены из регистрации и из reset не взаимозаменяемы — в JWT-claim `purpose` лежит `reg` или `pwd`.

---

## JWT

- **Access** — 15 минут, в заголовке `Authorization: Bearer <token>`.
- **Refresh** — 30 дней, передаётся в теле запроса `/auth/refresh/`.
- **Rotation** — на `/refresh/` старый refresh инвалидируется, выдаётся новый.
- **Blacklist** — все blacklisted токены хранятся в БД (`token_blacklist` app), проверка на каждый refresh.

**Logout:**
- `/auth/logout/` `{ refresh }` — blacklist одного refresh.
- `/auth/logout-all/` — blacklist всех outstanding refresh пользователя.
- `/auth/sessions/` — список активных refresh-токенов (jti, created_at, expires_at).

---

## Куда смотреть в коде

- Endpoints: [`apps/accounts/views.py`](../src/apps/accounts/views.py), [`apps/accounts/urls.py`](../src/apps/accounts/urls.py)
- Сервисы: [`apps/accounts/services/`](../src/apps/accounts/services/)
- OTP в Redis: [`apps/accounts/services/otp.py`](../src/apps/accounts/services/otp.py)
- Verification-токен: [`apps/accounts/services/verification_token.py`](../src/apps/accounts/services/verification_token.py)
- SMS-адаптер: [`services/sms/`](../src/services/sms/)
- Тесты: [`tests/accounts/`](../src/tests/accounts/)
