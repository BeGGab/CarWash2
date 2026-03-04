from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Все значения загружаются из переменных окружения (в т.ч. из .env)."""

    app_name: str = ""
    backend_url: str = ""
    frontend_url: str = ""

    @field_validator("backend_url", "frontend_url", mode="before")
    @classmethod
    def strip_url(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip().rstrip("/")
        return v

    cors_extra_origins: str = ""
    database_url: str = ""

    default_city_name: Optional[str] = None
    default_city_lat: Optional[float] = None
    default_city_lon: Optional[float] = None
    default_radius_km: float = 0.0

    telegram_bot_token: str = ""
    system_admin_telegram_ids: List[int] = []

    refund_hours_before_start: int = 0

    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_currency: str = ""

    aggregator_commission_percent: float = 0.0

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
