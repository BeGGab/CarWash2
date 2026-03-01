from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import admin, auth, bookings, carwashes, payments, services, system_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(carwashes.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(system_admin.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}

