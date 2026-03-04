# CarWash Aggregator — Telegram Mini App

Сервис-агрегатор автомоек: бэкенд API, Telegram-бот и Mini App (WebApp).

- **Backend:** FastAPI, SQLAlchemy (async), PostgreSQL, ЮKassa
- **Бот:** aiogram 3, работа по **webhooks** (обновления приходят на API)
- **Mini App:** Vite + React — поиск моек, слоты, бронирование, предоплата 50%

---

## Структура проекта

```
carwash2/
├── backend/                 # FastAPI-приложение
│   └── app/
│       ├── main.py         # Точка входа, CORS, роутеры, lifespan (Alembic, webhook)
│       ├── config.py       # Настройки только из .env (без дефолтов в коде)
│       ├── db.py           # Async engine и сессии SQLAlchemy
│       ├── models.py       # Модели БД
│       ├── schemas.py      # Pydantic-схемы
│       ├── routers/        # Эндпоинты API (auth, carwashes, bookings, payments и др.)
│       └── services/       # Напоминания, возвраты, отправка в Telegram
├── bot/
│   └── bot.py              # Логика бота (handlers), роутер webhook, set/delete webhook
├── frontend/               # Mini App (Vite + React)
│   ├── index.html
│   ├── package.json
│   ├── public/
│   │   └── config.example.json
│   ├── scripts/            # write-config.cjs — запись config.json из BACKEND_URL
│   └── src/
│       ├── main.tsx, App.tsx
│       ├── api.ts
│       ├── pages/          # Страницы приложения
│       ├── components/
│       └── store/
├── docs/                   # Инструкции (деплой Amvera, тесты оплаты и др.)
├── requirements.txt
├── amvera.yaml             # Деплой бэкенда на Amvera (Python)
└── Dockerfile              # Деплой бэкенда на Amvera (Docker)
```

Фронтенд для облака лежит в `frontend/`; там же конфигурация сборки/запуска под Node (Amvera).

---

## Установка зависимостей

```bash
cd d:\carwash2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install
```

---

## Настройка окружения

Все настройки приложения берутся из переменных окружения. В корне проекта создайте `.env` и задайте все необходимые переменные (без значений по умолчанию в коде они обязательны для работы):

```env
APP_NAME=CarWash Aggregator
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/carwash

TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_БОТА
SYSTEM_ADMIN_TELEGRAM_IDS=123456789,987654321
REFUND_HOURS_BEFORE_START=2

YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
YOOKASSA_CURRENCY=RUB
AGGREGATOR_COMMISSION_PERCENT=5.0
```

PostgreSQL должен быть запущен до старта бэкенда. Можно поднять БД через Docker или установить локально и создать базу `carwash`.

---

## Запуск backend (FastAPI)

```bash
cd d:\carwash2
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Бэкенд отдаёт API и **принимает обновления бота по webhook** на `POST /api/telegram/webhook`. В lifespan при старте: применяются миграции Alembic, запускается планировщик напоминаний, регистрируется webhook бота в Telegram; при остановке webhook снимается. Бот работает только вместе с FastAPI (отдельный процесс не нужен).

---

## Запуск бота локально (long polling)

Для разработки можно запускать бота в режиме long polling (без webhook):

```bash
cd d:\carwash2
.venv\Scripts\activate
python -m bot.bot
```

При этом бэкенд (uvicorn) должен быть запущен отдельно; в `.env` у бота используется `BACKEND_URL` для запросов к API. В BotFather укажите **URL Web App** = адрес фронта (`FRONTEND_URL`). Подробнее про туннели и 502 — [docs/URL_AND_DEPLOY.md](docs/URL_AND_DEPLOY.md).

Деплой в облако Amvera описан в двух вариантах: [docs/DEPLOY_AMVERA_PYTHON_NODE.md](docs/DEPLOY_AMVERA_PYTHON_NODE.md) (Python + Node) и [docs/DEPLOY_AMVERA_DOCKER.md](docs/DEPLOY_AMVERA_DOCKER.md) (Docker).

---

## Запуск Mini App (Vite + React)

```bash
cd d:\carwash2\frontend
npm run dev
```

Фронт доступен на `http://localhost:5173`. Для работы с телефона (WebApp) нужен публичный URL бэкенда в `config.json` (пример — `frontend/public/config.example.json`) или переменная `VITE_BACKEND_URL` при сборке.

---

## Функционал

- **Пользователь:** регистрация по телефону, поиск моек по геолокации, бронирование с предоплатой 50% (ЮKassa), «Мои брони».
- **Админ автомойки:** регистрация точки, услуги, просмотр броней, завершение по QR.
- **Системный админ:** модерация моек, статистика, назначение админов моек (`/add_carwash_admin` в боте).

Возврат предоплаты при отмене брони (если не позже `REFUND_HOURS_BEFORE_START` до начала) и ручной возврат из кабинета админа. Подробнее по тестовой оплате — [docs/TEST_BOOKING_AND_PAYMENT.md](docs/TEST_BOOKING_AND_PAYMENT.md).
