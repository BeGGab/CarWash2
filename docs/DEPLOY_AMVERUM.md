# Деплой бота и бэкенда CarWash на Amverum Cloud

Пошаговая инструкция по развёртыванию **Telegram-бота** и **FastAPI бэкенда** на [Amverum Cloud](https://amverum.com/) (облако для ботов и веб-приложений).

---

## Что будет задеплоено

- **Один контейнер** с двумя процессами:
  - **Backend (FastAPI)** — API на порту `PORT` (по умолчанию 8000), доступен снаружи по URL приложения Amverum.
  - **Telegram-бот** (aiogram) — работает в том же контейнере и обращается к API по `http://127.0.0.1:PORT`.
- **База данных** — управляемый PostgreSQL от Amverum (или своя, если уже есть).

Фронт (WebApp на Vite/React) можно оставить на другом сервисе (Vercel, Netlify, второй контейнер Amverum) и указать его URL в переменной `FRONTEND_URL`.

---

## 1. Регистрация и подготовка

### 1.1. Регистрация в Amverum

1. Перейдите на [amverum.com](https://amverum.com/).
2. Нажмите **«Sign up»** / **«Регистрация»** и создайте аккаунт.
3. Войдите в панель: [cloud.amvera.ru](https://cloud.amvera.ru/).
4. При регистрации обычно доступен тестовый баланс (около $1).

### 1.2. Подключение репозитория

Деплой в Amverum делается через **Git**.

- **Вариант A:** использовать **выделенный Git Amverum** (репозиторий создаётся в панели, затем делаете `git remote add amvera ...` и `git push amvera master`).
- **Вариант B:** подключить **свой репозиторий** (GitHub/GitLab и т.п.), если в интерфейсе есть «Подключить репозиторий».

Точные шаги см. в разделе **«Work with Git»** в [документации Amverum](https://docs-en-amverum-services.waw.amverum.cloud/applications/git.html) (или актуальной ссылке с [amverum.com](https://amverum.com/)).

---

## 2. База данных PostgreSQL

Бэкенду нужна PostgreSQL (для пользователей, моек, броней и т.д.).

### 2.1. Создание БД в Amverum

1. В панели Amverum откройте раздел **«Базы данных»** / **«Managed DBMS»** (или аналог).
2. Создайте **PostgreSQL** (тариф от $3/мес).
3. После создания сохраните:
   - **хост** (host);
   - **порт** (обычно 5432);
   - **имя базы** (database);
   - **пользователь** (user);
   - **пароль** (password).

### 2.2. Строка подключения

Соберите URL в формате:

```
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
```

Пример:

```
postgresql+asyncpg://carwash:SecretPass@pg-xxx.amverum.cloud:5432/carwash
```

Это значение понадобится для переменной окружения **`DATABASE_URL`** в приложении.

### 2.3. Миграции (схема таблиц)

Таблицы создаются при первом запросе к API (FastAPI при старте выполняет `Base.metadata.create_all`). Если используете Alembic, миграции можно запускать вручную один раз (например, локально с `DATABASE_URL` на облачную БД) или добавить шаг в скрипт запуска контейнера.

---

## 3. Создание приложения и конфигурация

### 3.1. Новое приложение

1. В панели Amverum нажмите **«Создать приложение»** / **«New Application»**.
2. Выберите способ развёртывания:
   - **Docker** — если будете использовать `Dockerfile`;
   - либо **указание репозитория и конфигурации** (например, `amverum.yaml`), если платформа поддерживает.

### 3.2. Конфигурация деплоя (Docker)

В корне проекта уже есть **`Dockerfile.amverum`**. В нём:

- Устанавливаются зависимости из `requirements.txt`.
- Копируются `backend/`, `bot/` и скрипт `scripts/start_amverum.sh`.
- При запуске контейнера вызывается `start_amverum.sh`: в фоне стартует **uvicorn**, затем запускается **бот** (`python -m bot.bot`).

В настройках приложения в Amverum укажите:

- **Путь к Dockerfile:** например, `Dockerfile.amverum` (или имя файла, который вы даёте платформе).
- **Корень сборки:** корень репозитория (где лежат `backend/`, `bot/`, `requirements.txt`).

Если платформа ожидает файл с именем `Dockerfile`, можно скопировать:

```bash
cp Dockerfile.amverum Dockerfile
```

и закоммитить, либо в UI указать путь к `Dockerfile.amverum`.

### 3.3. Переменные окружения

В панели приложения откройте раздел **«Переменные окружения»** / **«Environment variables»** и задайте все нужные переменные (без `.env` в репозитории — только в UI).

Обязательные:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DATABASE_URL` | Подключение к PostgreSQL (asyncpg) | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `TELEGRAM_BOT_TOKEN` | Токен бота от BotFather | `123456:ABC-...` |
| `BACKEND_URL` | **Не задавать** — в контейнере скрипт подставит `http://127.0.0.1:PORT` для бота. | — |
| `FRONTEND_URL` | Публичный URL вашего WebApp (фронт) | `https://your-webapp.vercel.app` или URL второго приложения |
| `SYSTEM_ADMIN_TELEGRAM_IDS` | ID системных админов через запятую | `123456789,987654321` |

Опционально (по необходимости):

| Переменная | Описание |
|------------|----------|
| `APP_NAME` | Название приложения |
| `REFUND_HOURS_BEFORE_START` | За сколько часов до начала разрешена отмена с возвратом (по умолчанию 2) |
| `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_CURRENCY` | Для приёма оплаты (ЮKassa) |
| `DEFAULT_CITY_NAME`, `DEFAULT_CITY_LAT`, `DEFAULT_CITY_LON`, `DEFAULT_RADIUS_KM` | Город и радиус поиска по умолчанию |
| `CORS_EXTRA_ORIGINS` | Доп. origins для CORS (через запятую) |

Важно:

- **FRONTEND_URL** — тот URL, с которого пользователи открывают Mini App (и куда ЮKassa делает редирект после оплаты). Если фронт деплоите отдельно (Vercel, другой контейнер Amverum), подставьте его сюда.
- После деплоя у приложения будет **свой URL** (например, `https://your-app-xxx.amverum.cloud`). Это и есть **публичный URL бэкенда**. Его нужно:
  - указать в **frontend/public/config.json** в поле **`backendUrl`** (чтобы WebApp с телефона ходил в API);
  - при необходимости использовать в других сервисах.

---

## 4. Деплой

### 4.1. Через Git (рекомендуется)

1. Убедитесь, что в репозитории есть:
   - `Dockerfile.amverum` (или скопирован как `Dockerfile`);
   - `scripts/start_amverum.sh`;
   - `backend/`, `bot/`, `requirements.txt`.
2. Добавьте remote Amverum (если используете их Git) и выполните push в нужную ветку (часто `master` или `main`):

   ```bash
   git add Dockerfile.amverum scripts/start_amverum.sh
   git commit -m "Add Amverum deployment"
   git push amvera master
   ```

   Либо сделайте push в подключённый свой репозиторий (если Amverum настроен на него).

3. В панели Amverum запустите **сборку и деплой** (если он не стартует автоматически после push).

### 4.2. Загрузка через интерфейс

Если в Amverum доступна **загрузка файлов (GUI)**:

1. Соберите архив с проектом (включая `backend/`, `bot/`, `requirements.txt`, `Dockerfile.amverum`, `scripts/start_amverum.sh`), без `.env` и без `node_modules`/`.venv`.
2. Загрузите архив через интерфейс и запустите деплой.

---

## 5. После деплоя

### 5.1. URL бэкенда

В панели приложения посмотрите **URL приложения** (например, `https://carwash-api-xxx.amverum.cloud`). Это и есть ваш **BACKEND_URL** для внешнего мира.

### 5.2. Проверка API

Откройте в браузере:

```
https://ВАШ-URL-ПРИЛОЖЕНИЯ/health
```

В ответ должно быть: `{"status":"ok"}`.

### 5.3. Настройка фронта и Telegram

1. **Фронт (WebApp):**  
   Если фронт развёрнут отдельно (см. раздел 6), в нём при старте контейнера подставляется `config.json` из переменной `BACKEND_URL`. Если фронт пока локальный или на другом хостинге — в `frontend/public/config.json` укажите `{"backendUrl": "https://ВАШ-URL-БЭКЕНДА-AMVERUM"}` (без завершающего слэша).

2. **Telegram (BotFather):**  
   URL кнопки Web App задайте равным **URL фронта** (где открывается Mini App), а не бэкенда.

3. **ЮKassa (если используете):**  
   В личном кабинете ЮKassa укажите:
   - **Webhook:** `https://ВАШ-URL-ПРИЛОЖЕНИЯ-AMVERUM/api/payments/yookassa/webhook`
   - Убедитесь, что в приложении заданы `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `FRONTEND_URL`.

### 5.4. Логи

В панели Amverum откройте **логи контейнера**. Там будут вывод uvicorn и бота. При старте бот проверяет доступность бэкенда по `http://127.0.0.1:PORT` — в логах будет сообщение «Бэкенд доступен» или предупреждение об ошибке.

---

## 6. Деплой фронтенда (WebApp) на Amverum Cloud

Фронт (Vite + React) разворачивается **отдельным приложением** в Amverum. В образе — собранная статика и nginx; при старте в контейнере из переменной `BACKEND_URL` формируется `config.json`, чтобы приложение знало адрес API.

### 6.1. Что нужно заранее

- Бэкенд уже задеплоен на Amverum (или где-то ещё) и у вас есть его **публичный URL** (например, `https://carwash-api-xxx.amverum.cloud`).
- В репозитории есть папка **`frontend/`** с файлами: `Dockerfile`, `nginx.conf`, `docker-entrypoint.sh`, `package.json`, `src/`, `index.html` и т.д.

### 6.2. Создание приложения фронта в Amverum

1. Войдите в панель [cloud.amvera.ru](https://cloud.amvera.ru/).
2. Нажмите **«Создать приложение»** / **«New Application»**.
3. Подключите **тот же репозиторий**, что и для бэкенда (или загрузите код с папкой `frontend/`).

### 6.3. Настройка сборки (Docker)

Важно: сборка должна идти **из папки `frontend/`**, а не из корня репозитория.

- **Контекст сборки (Build context):** укажите папку **`frontend`** (или путь к ней, например `./frontend`). В ней должны лежать `Dockerfile`, `package.json`, `src/`, `nginx.conf`, `docker-entrypoint.sh`.
- **Путь к Dockerfile:** укажите **`Dockerfile`** (относительно контекста — файл `frontend/Dockerfile`).

Если в Amverum нельзя задать подпапку как контекст и сборка идёт только из корня репозитория — создайте в **корне** файл `Dockerfile.frontend` (см. ниже) и укажите его как Dockerfile, контекст — корень.

### 6.4. Переменные окружения

В настройках приложения откройте **«Переменные окружения»** и добавьте:

| Переменная    | Значение | Обязательно |
|---------------|----------|-------------|
| **BACKEND_URL** | Публичный URL бэкенда (API), без слэша в конце | Да |

Пример: `BACKEND_URL=https://carwash-api-xxx.amverum.cloud`

Других переменных для фронта не нужно.

### 6.5. Запуск и получение URL

1. Запустите сборку и деплой приложения.
2. После успешного запуска скопируйте **внешний URL приложения** (например, `https://carwash-web-xxx.amverum.cloud`). Это и есть URL вашего WebApp.

### 6.6. Что сделать после деплоя фронта

1. **Telegram (BotFather):** в настройках кнопки Web App укажите этот URL (адрес фронта), например `https://carwash-web-xxx.amverum.cloud`.
2. **Бэкенд (приложение с API и ботом):** в переменных окружения задайте **`FRONTEND_URL`** = этот же URL фронта (для CORS и редиректа ЮKassa после оплаты). В панели Amverum откройте приложение бэкенда → переменные → добавьте или измените `FRONTEND_URL`.
3. **ЮKassa:** возврат после оплаты идёт на фронт, например `https://carwash-web-xxx.amverum.cloud/payment-success`.

### 6.7. Сборка из корня репозитория (Dockerfile в корне)

Если платформа не позволяет задать контекст `frontend/`, в репозитории уже есть файл **`Dockerfile.frontend`** в корне. В Amverum укажите:

- **Dockerfile:** `Dockerfile.frontend`
- **Контекст сборки:** корень репозитория

Образ соберётся из папки `frontend/` и будет таким же, как при сборке из `frontend/Dockerfile`.

---

## 7. Два контейнера (бэкенд и бот отдельно)

Если нужно разнести **API** и **бота** по разным приложениям Amverum:

1. **Приложение 1 — только бэкенд**
   - Dockerfile: образ только с `backend/`, команда: `uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
   - В переменных: `DATABASE_URL`, `FRONTEND_URL`, ЮKassa, CORS и т.д.
   - После деплоя получите URL API (например, `https://api-xxx.amverum.cloud`).

2. **Приложение 2 — только бот**
   - Dockerfile: образ только с `bot/`, команда: `python -m bot.bot`.
   - В переменных: `DATABASE_URL` (если бот напрямую с БД не работает, то не нужен), **`BACKEND_URL=https://api-xxx.amverum.cloud`** (URL приложения 1), `TELEGRAM_BOT_TOKEN`, `SYSTEM_ADMIN_TELEGRAM_IDS` и т.д.

В текущем проекте бот обращается только к API (по `BACKEND_URL`), не к БД, поэтому для варианта «два контейнера» боту достаточно `BACKEND_URL` и токена.

---

## 8. Полезные ссылки и поддержка

- **Сайт:** [amverum.com](https://amverum.com/)
- **Панель:** [cloud.amvera.ru](https://cloud.amvera.ru/)
- **Документация:** разделы «How to deploy the project», «Work with Git», «FAQ» — ссылки с главной страницы Amverum.
- **Поддержка:** support@amverum.com или [Telegram-чат](https://t.me/amverum_support).

Тарифы (на момент описания): от ~$1.9/мес (Trial) до более высоких для нагруженных сервисов; оплата за время работы контейнеров.
