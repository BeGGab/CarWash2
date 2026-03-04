import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import engine
from .routers import admin, auth, bookings, carwashes, config_router, payments, services, system_admin
from .services.reminder_scheduler import start_scheduler, stop_scheduler

# Импорт после настроек (bot использует settings)
from bot.bot import get_webhook_router, setup_webhook, teardown_webhook


def _run_alembic_upgrade() -> None:
    """Применяет миграции Alembic (синхронно)."""
    root = Path(__file__).resolve().parent.parent.parent
    alembic_ini = root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = logging.getLogger("uvicorn.error")
    log.info("Lifespan: applying Alembic migrations...")
    await asyncio.to_thread(_run_alembic_upgrade)
    log.info("Lifespan: migrations done, starting scheduler...")
    start_scheduler()
    log.info("Lifespan: setting Telegram webhook...")
    await setup_webhook(settings.backend_url)
    log.info("Lifespan: startup complete.")
    try:
        yield
    finally:
        await teardown_webhook()
        stop_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

def _cors_origins():
    origins = [settings.frontend_url, "http://localhost", "http://localhost:5173", "https://localhost:5173"]
    if settings.cors_extra_origins:
        for o in settings.cors_extra_origins.split(","):
            o = o.strip()
            if o:
                origins.append(o)
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(config_router.router, prefix="/api")
app.include_router(carwashes.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(system_admin.router, prefix="/api")
app.include_router(get_webhook_router(), prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}

