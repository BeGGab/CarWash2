from datetime import datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..config import settings
from ..db import get_async_session
from ..models import Booking, BookingStatus, CarWash, PaymentStatus, Service, User
from ..schemas import BookingCreate, BookingRead
from ..services.refund_service import create_refund as do_create_refund

router = APIRouter(prefix="/bookings", tags=["bookings"])


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


@router.post("", response_model=BookingRead)
async def create_booking(
    payload: BookingCreate,
    telegram_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    carwash = await session.get(CarWash, payload.carwash_id)
    service = await session.get(Service, payload.service_id)
    if not carwash or not service:
        raise HTTPException(status_code=404, detail="Car wash or service not found")

    start_dt = datetime.combine(payload.date, payload.start_time)
    end_dt = start_dt + timedelta(minutes=service.duration_minutes)

    # check overlapping bookings
    stmt = select(Booking).where(
        and_(
            Booking.carwash_id == carwash.id,
            Booking.date == payload.date,
            Booking.start_time == payload.start_time,
            Booking.status != BookingStatus.CANCELLED,
        )
    )
    res = await session.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slot already booked")

    qr_code_data = token_urlsafe(16)

    booking = Booking(
        user_id=user.id,
        carwash_id=carwash.id,
        service_id=service.id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=end_dt.time(),
        status=BookingStatus.PENDING_PAYMENT,
        prepayment_percent=50,
        total_price=float(service.price),
        qr_code_data=qr_code_data,
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


@router.get("/me", response_model=list[BookingRead])
async def list_my_bookings(
    telegram_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Booking).where(Booking.user_id == user.id).order_by(Booking.created_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(booking_id: int, session: AsyncSession = Depends(get_async_session)):
    booking = await session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking(
    booking_id: int,
    telegram_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(joinedload(Booking.payment))
    )
    res = await session.execute(stmt)
    booking = res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    user = await get_user_by_telegram_id(session, telegram_id)
    if not user or booking.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    booking_start = datetime.combine(booking.date, booking.start_time)
    now = datetime.utcnow()
    hours_before = settings.refund_hours_before_start
    can_refund = (booking_start - now) >= timedelta(hours=hours_before)

    if (
        can_refund
        and booking.payment
        and booking.payment.status == PaymentStatus.SUCCEEDED
    ):
        try:
            refund, _ = await do_create_refund(
                booking.payment,
                float(booking.payment.amount),
                "Отмена пользователем",
                idempotence_key=f"cancel-booking-{booking.id}",
            )
            session.add(refund)
        except RuntimeError:
            pass  # отмена без возврата при ошибке ЮKassa

    booking.status = BookingStatus.CANCELLED
    booking.canceled_at = now
    await session.commit()
    await session.refresh(booking)
    return booking
