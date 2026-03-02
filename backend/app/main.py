from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import admin, auth, bookings, carwashes, config_router, payments, services, system_admin
from .services.reminder_scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    try:
        yield
    finally:
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


@app.get("/health")
async def health():
    return {"status": "ok"}

