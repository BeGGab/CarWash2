### CarWash Aggregator — Telegram Mini App

Полностью готовый каркас сервиса агрегатора автомоек:

- **Backend**: `FastAPI` + `SQLAlchemy` (async) + `PostgreSQL` + интеграция с **ЮKassa**
- **Telegram-бот**: `aiogram 3` + `httpx`, авторизация по телефону, геолокация, запуск Mini App
- **Mini App (WebApp)**: `Vite + React`, поиск моек, слоты, бронирование и предоплата 50%

---

### 1. Установка зависимостей

```bash
cd d:\carwash2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install
```

---

### 2. Настройка окружения

Создайте файл `.env` в корне `d:\carwash2`:

```env
APP_NAME=CarWash Aggregator
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/carwash

TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_БОТА
# ID системных администраторов через запятую (для /add_carwash_admin и системного WebApp)
SYSTEM_ADMIN_TELEGRAM_IDS=123456789,987654321
# Часы до начала: при отмене брони не позже этого срока делается авто-возврат предоплаты
REFUND_HOURS_BEFORE_START=2

YOOKASSA_SHOP_ID=ВАШ_SHOP_ID
YOOKASSA_SECRET_KEY=ВАШ_SECRET_KEY
YOOKASSA_CURRENCY=RUB

AGGREGATOR_COMMISSION_PERCENT=5.0
```

**PostgreSQL должен быть запущен до старта бэкенда.** Иначе будет ошибка: `Connect call failed ('127.0.0.1', 5432)`.

**Вариант 1 — через Docker (рекомендуется):**
```bash
cd d:\carwash2
docker-compose up -d
```
Будет создана БД `carwash`, пользователь `carwash`, пароль `123456` (как в `DATABASE_URL` в `.env`).

**Вариант 2 — локальный PostgreSQL:** установите PostgreSQL, создайте базу и пользователя:
```bash
createdb carwash
# Либо в psql: CREATE USER carwash WITH PASSWORD '123456'; CREATE DATABASE carwash OWNER carwash;
```

---

### 3. Запуск backend (FastAPI)

```bash
cd d:\carwash2
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend поднимется на `http://localhost:8000`, health-check: `/health`.

---

### 4. Запуск Telegram-бота (aiogram 3)

```bash
cd d:\carwash2
.venv\Scripts\activate
python -m bot.bot
```

**Важно:** Бот ходит в API по адресу из `BACKEND_URL` в `.env` (должен быть URL **бэкенда**, не фронта). Для доступа с телефона нужны два туннеля: один до фронта (порт 5173) → его URL в `FRONTEND_URL` и в Telegram; второй до бэкенда (порт 8000) → его URL в `BACKEND_URL` и в `config.json` → `backendUrl`. Если при открытии WebApp появляется **502** — туннель для фронта не доходит до вашего ПК или фронт (`npm run dev`) не запущен; см. [docs/URL_AND_DEPLOY.md](docs/URL_AND_DEPLOY.md).

В BotFather (или в настройках кнопки бота) укажите **URL Web App** = адрес, по которому открывается **фронт** (то же значение, что и `FRONTEND_URL`). Не путайте: в Telegram указывается URL **фронта**, а не бэкенда.

**Подробно:** когда и где указывать BACKEND_URL, FRONTEND_URL, какой URL вставить в Telegram и как устранить ошибку 502 — см. **[docs/URL_AND_DEPLOY.md](docs/URL_AND_DEPLOY.md)**.  
**Деплой бота и бэкенда в облако:** пошаговая инструкция для **Amverum Cloud** — см. **[docs/DEPLOY_AMVERUM.md](docs/DEPLOY_AMVERUM.md)**.  
**Деплой фронтенда (WebApp) в контейнере:** сборка и запуск Docker-образа с nginx — см. **[docs/DEPLOY_FRONTEND.md](docs/DEPLOY_FRONTEND.md)**.

Функционал бота:

- `/start` — если пользователь уже есть в БД (по `telegram_id`), показывается меню; иначе запрос контакта и регистрация через `/api/auth/register`
- кнопка **«Отправить местоположение»** — запрос геолокации, поиск моек через `/api/carwashes/nearby`
- кнопка **«Открыть мини-приложение»** — открытие Vite-приложения как Telegram WebApp
- кнопка **«Мои брони»** — список броней через `/api/bookings/me`
- **Системный администратор** (если его `telegram_id` указан в `SYSTEM_ADMIN_TELEGRAM_IDS`): команда `/add_carwash_admin <telegram_id>` — назначает пользователя администратором автомойки (тот сможет добавить точку в админском WebApp). При запуске бота выводится проверка: если список системных админов пуст — предупреждение в лог.

---

### 5. Запуск Mini App (Vite + React)

```bash
cd d:\carwash2\frontend
npm run dev
```

Frontend доступен на `http://localhost:5173`.

Дополнительно в `frontend/.env` или при сборке можно указать:

```env
VITE_BACKEND_URL=http://localhost:8000
```

**Важно для запуска с телефона (Telegram WebApp):** чтобы не было ошибки «Failed to fetch», клиент должен знать URL бэкенда. Два варианта: (1) при сборке задать `VITE_BACKEND_URL=https://ВАШ_ПУБЛИЧНЫЙ_БЭКЕНД`; (2) положить в корень фронта (рядом с `index.html`) файл `config.json` с содержимым `{"backendUrl": "https://ВАШ_ПУБЛИЧНЫЙ_БЭКЕНД"}` — пример в `frontend/public/config.example.json`. В `.env` бэкенда укажите `FRONTEND_URL` на адрес WebApp; при необходимости добавьте `CORS_EXTRA_ORIGINS=https://ваш-фронт.serveo.net` (через запятую несколько origins).

Mini App:

- получает `telegram_id` через `Telegram.WebApp.initDataUnsafe.user.id`
- запрашивает геолокацию браузера и обращается к `/api/carwashes/nearby`
- показывает карточки моек + ближайшие свободные слоты
- по клику на слот:
  - запрашивает услуги мойки `/api/services/by-carwash/{id}`
  - создаёт бронь `/api/bookings?telegram_id=...`
  - создаёт платёж 50% `/api/payments/create`
  - перенаправляет на `confirmation_url` ЮKassa

После успешной оплаты ЮKassa шлёт webhook на `/api/payments/yookassa/webhook`, бронь получает статус **PAID**.

**Напоминания:** при создании брони админу мойки (владельцу) приходит уведомление в Telegram. Если бронь оплачена и до визита больше 24 часов, клиенту автоматически планируется напоминание за 24 часа до времени записи (APScheduler). При отмене брони задача напоминания удаляется.

Подробная инструкция по **тестовой оплате и доведению брони до конца**: см. [docs/TEST_BOOKING_AND_PAYMENT.md](docs/TEST_BOOKING_AND_PAYMENT.md).

---

### 6. Модули администрирования

- **Админ автомойки (через API / Telegram)**:
  - регистрация точки: `POST /api/admin/carwashes?telegram_id=...`
  - добавление услуг: `POST /api/admin/services?telegram_id=...`
  - просмотр броней: `GET /api/admin/bookings?telegram_id=...`
  - поиск брони по QR-коду: `GET /api/admin/bookings/by-qr/{qr_code}?telegram_id=...`
  - завершение мойки: `POST /api/admin/bookings/{booking_id}/complete?telegram_id=...`

- **Администратор системы** (в запросе обязателен `?telegram_id=<id>` из `SYSTEM_ADMIN_TELEGRAM_IDS`):
  - список не подтверждённых моек: `GET /api/system/carwashes/pending?telegram_id=...`
  - подтверждение мойки: `POST /api/system/carwashes/{id}/approve?telegram_id=...`
  - общая статистика: `GET /api/system/statistics/overview?telegram_id=...`
  - назначить админа автомойки: `POST /api/system/users/assign-carwash-admin?telegram_id=...` с телом `{"telegram_id": <id_пользователя>}`

Возврат предоплаты:

- Пользователь отменяет бронь: `POST /api/bookings/{id}/cancel?telegram_id=...`. Если до начала брони не меньше `REFUND_HOURS_BEFORE_START` часов и платёж успешен — выполняется авто-возврат в ЮKassa.
- Админ в WebApp «Кабинет автомойки»: кнопка **«Вернуть предоплату»** у оплаченных броней → `POST /api/payments/{payment_id}/refund` (тело: `payment_id`, `amount`, `reason`).

Эти эндпоинты готовы для подключения к отдельной веб-панели или к отдельным Telegram-интерфейсам.

---

### 7. Что уже реализовано из ТЗ

- **Пользователь**:
  - регистрация по номеру телефона (через Telegram-контакт)
  - поиск моек по геолокации (бот + Mini App)
  - фильтрация по расстоянию и времени (через параметр `after_time`, базовая логика слотов)
  - отображение карточек моек и ближайших слотов
  - бронирование слота с предоплатой 50% через ЮKassa
  - личный кабинет: «Мои брони» (бот) + данные в БД

- **Админ автомойки**:
  - регистрация точки с геометкой, расписанием, услугами
  - просмотр броней своих моек
  - подтверждение оказания услуги по QR (через API)

- **Админ системы**:
  - модерация моек
  - базовая финансовая статистика и комиссия агрегатора

Дальше можно наращивать UX (отдельные админские WebApp, более сложные фильтры, продвинутую работу с расписанием и возвратами платежей), но базовый рабочий скелет сервиса уже готов.

