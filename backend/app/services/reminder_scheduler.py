"""Планировщик напоминаний за 24 часа до записи (APScheduler AsyncIOScheduler)."""
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .telegram_sender import send_telegram_message

REMINDER_JOB_PREFIX = "reminder_"

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def job_id_for_booking(booking_id: int) -> str:
    return f"{REMINDER_JOB_PREFIX}{booking_id}"


async def _send_reminder(client_telegram_id: int, time_str: str) -> None:
    text = (
        f"Напоминаем, что у вас забронирована мойка на завтра на то время, "
        f"которое вы выбрали — {time_str}. Ждём Вас!"
    )
    await send_telegram_message(client_telegram_id, text)


def add_reminder(
    booking_id: int,
    run_at: datetime,
    client_telegram_id: int,
    time_str: str,
) -> None:
    """Запланировать напоминание клиенту за 24 часа до записи."""
    s = get_scheduler()
    if not s:
        return
    jid = job_id_for_booking(booking_id)
    try:
        s.remove_job(jid)
    except Exception:
        pass
    s.add_job(
        _send_reminder,
        "date",
        run_date=run_at,
        id=jid,
        args=[client_telegram_id, time_str],
    )


def remove_reminder(booking_id: int) -> None:
    """Удалить задачу напоминания при отмене записи."""
    s = get_scheduler()
    if not s:
        return
    jid = job_id_for_booking(booking_id)
    try:
        s.remove_job(jid)
    except Exception:
        pass
