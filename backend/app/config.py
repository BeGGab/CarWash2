from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CarWash Aggregator"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    @field_validator("backend_url", "frontend_url", mode="before")
    @classmethod
    def strip_url(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip().rstrip("/")
        return v

    # Доп. разрешённые origins для CORS (через запятую), например URL WebApp в Telegram
    cors_extra_origins: str = ""

    database_url: str = "postgresql+asyncpg://carwash:123456@localhost:5432/carwash"

    # Центральный город: геопозиция и радиус поиска от этой точки, если заданы системным администратором
    default_city_name: Optional[str] = "Ростов на Дону"
    default_city_lat: Optional[float] = 47.222109
    default_city_lon: Optional[float] = 39.718813
    default_radius_km: float = 25.0

    # Telegram / Bot
    telegram_bot_token: str = "YOUR_TELEGRAM_BOT_TOKEN"
    # ID системных администраторов (через запятую). Проверка при запуске бота и в API.
    system_admin_telegram_ids: List[int] = [1707332723, 138416420]

    # Отмена: авто-возврат предоплаты, если пользователь отменил бронь не менее чем за N часов до начала
    refund_hours_before_start: int = 2

    # YooKassa
    yookassa_shop_id: str = "1290986"
    yookassa_secret_key: str = "test_bzj7Xe4-acY1okaDXimKi3iaBGw4xQxFKXcA-5mKstY"
    yookassa_currency: str = "RUB"

    aggregator_commission_percent: float = 5.0

    @field_validator("system_admin_telegram_ids", mode="before")
    @classmethod
    def parse_system_admin_ids(cls, v: str | List[int] | None) -> List[int]:
        if v is None or (isinstance(v, list) and len(v) == 0):
            return []
        if isinstance(v, list):
            return v
        s = str(v).strip()
        if not s:
            return []
        # Поддержка вида "123,456" или "[123, 456]" из .env
        if s.startswith("["):
            s = s[1:]
        if s.endswith("]"):
            s = s[:-1]
        result = []
        for x in s.split(","):
            x = x.strip().rstrip("]").strip()
            if x:
                result.append(int(x))
        return result

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
