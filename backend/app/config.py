from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CarWash Aggregator"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    database_url: str = "postgresql+asyncpg://carwash:123456@localhost:5432/carwash"

    # Telegram / Bot
    telegram_bot_token: str = "YOUR_TELEGRAM_BOT_TOKEN"
    # ID системных администраторов (через запятую). Проверка при запуске бота и в API.
    system_admin_telegram_ids: List[int] = [1707332723, 138416420]

    # Отмена: авто-возврат предоплаты, если пользователь отменил бронь не менее чем за N часов до начала
    refund_hours_before_start: int = 2

    # YooKassa
    yookassa_shop_id: str = "YOUR_SHOP_ID"
    yookassa_secret_key: str = "YOUR_SECRET_KEY"
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
