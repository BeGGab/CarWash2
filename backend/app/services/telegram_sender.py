"""Отправка сообщений в Telegram через Bot API."""
import httpx
from ..config import settings

TELEGRAM_API = "https://api.telegram.org"


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Отправить сообщение пользователю. chat_id — telegram_id пользователя."""
    if not settings.telegram_bot_token or settings.telegram_bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
        return False
    url = f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                url,
                json={"chat_id": chat_id, "text": text},
            )
            return r.status_code == 200
    except Exception:
        return False
