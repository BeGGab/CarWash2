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

Убедитесь, что PostgreSQL запущен и база `carwash` создана.

```bash
createdb carwash
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

В BotFather:

- установите домен Mini App: `https://ВАШ_ДОМЕН` или на этапе разработки `https://<ngrok-адрес>`
- пропишите WebApp URL для кнопки (тот же, что `FRONTEND_URL` или туннель до `localhost:5173`)

Функционал бота:

- `/start` — запрос контакта (телефон), регистрация пользователя через `/api/auth/register`
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

Дополнительно в `frontend/.env` можно указать:

```env
VITE_BACKEND_URL=http://localhost:8000
```

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

