from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..db import get_async_session
from ..models import BlockedSlot, Booking, BookingStatus, CarWash, Service, User, UserRole
from ..schemas import (
    BlockedSlotCreate,
    BlockedSlotRead,
    BookingRead,
    CarWashCreate,
    CarWashRead,
    ServiceCreate,
    ServiceRead,
)

router = APIRouter(prefix="/admin", tags=["admin-carwash"])


async def _get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


@router.post("/carwashes", response_model=CarWashRead)
async def create_carwash(
    payload: CarWashCreate,
    telegram_id: int,
    session: AsyncSession = Depends (get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == UserRole.USER:
        user.role = UserRole.CARWASH_ADMIN

    carwash = CarWash(
        owner_id=user.id,
        name=payload.name,
        address=payload.address,
        lat=payload.lat,
        lon=payload.lon,
        description=payload.description,
        photos=payload.photos,
        wash_type=payload.wash_type,
        additional_services=payload.additional_services,
        open_time=payload.open_time,
        close_time=payload.close_time,
        slot_duration_minutes=payload.slot_duration_minutes,
        is_approved=False,
    )
    session.add(carwash)
    await session.commit()
    await session.refresh(carwash)
    return carwash


@router.get("/carwashes/me", response_model=List[CarWashRead])
async def list_my_carwashes(
    telegram_id: int,
    session: AsyncSession = Depends (get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(CarWash).where(CarWash.owner_id == user.id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.post("/services", response_model=ServiceRead)
async def create_service(
    payload: ServiceCreate,
    telegram_id: int,
    session: AsyncSession = Depends (get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    carwash = await session.get(CarWash, payload.carwash_id)
    if not carwash or carwash.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    service = Service(
        carwash_id=payload.carwash_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        duration_minutes=payload.duration_minutes,
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


@router.post("/blocked-slots", response_model=BlockedSlotRead)
async def create_blocked_slot(
    payload: BlockedSlotCreate,
    telegram_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    carwash = await session.get(CarWash, payload.carwash_id)
    if not carwash or carwash.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    blocked = BlockedSlot(
        carwash_id=payload.carwash_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason,
    )
    session.add(blocked)
    await session.commit()
    await session.refresh(blocked)
    return blocked


@router.get("/blocked-slots", response_model=list[BlockedSlotRead])
async def list_blocked_slots(
    carwash_id: int,
    telegram_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    carwash = await session.get(CarWash, carwash_id)
    if not carwash or carwash.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = select(BlockedSlot).where(BlockedSlot.carwash_id == carwash_id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.delete("/blocked-slots/{blocked_id}")
async def delete_blocked_slot(
    blocked_id: int,
    telegram_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    blocked = await session.get(BlockedSlot, blocked_id)
    if not blocked:
        raise HTTPException(status_code=404, detail="Blocked slot not found")

    carwash = await session.get(CarWash, blocked.carwash_id)
    if not carwash or carwash.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await session.delete(blocked)
    await session.commit()
    return {"status": "deleted"}


@router.get("/bookings", response_model=List[BookingRead])
async def list_carwash_bookings(
    telegram_id: int,
    session: AsyncSession = Depends (get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    carwashes_stmt = select(CarWash.id).where(CarWash.owner_id == user.id)
    carwashes_res = await session.execute(carwashes_stmt)
    carwash_ids = [row[0] for row in carwashes_res.all()]

    if not carwash_ids:
        return []

    bookings_stmt = (
        select(Booking)
        .where(Booking.carwash_id.in_(carwash_ids))
        .options(joinedload(Booking.payment))
        .order_by(Booking.date.desc(), Booking.start_time.desc())
    )
    bookings_res = await session.execute(bookings_stmt)
    return list(bookings_res.scalars().all())


@router.get("/bookings/by-qr/{qr_code}", response_model=BookingRead)
async def get_booking_by_qr(
    qr_code: str,
    telegram_id: int,
    session: AsyncSession = Depends (get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    booking_stmt = select(Booking).where(Booking.qr_code_data == qr_code)
    booking_res = await session.execute(booking_stmt)
    booking = booking_res.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    carwash = await session.get(CarWash, booking.carwash_id)
    if not carwash or carwash.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return booking


@router.post("/bookings/{booking_id}/start", response_model=BookingRead)
async def start_wash(
    booking_id: int,
    telegram_id: int,
    session: AsyncSession = Depends (get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    booking = await session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    carwash = await session.get(CarWash, booking.carwash_id)
    if not carwash or carwash.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if booking.status != BookingStatus.PAID:
        raise HTTPException(status_code=400, detail="Booking is not paid")

    # Можно добавить отдельный статус "in_progress", пока ограничимся логированием начала
    booking.status = BookingStatus.PAID
    await session.commit()
    await session.refresh(booking)
    return booking


@router.post("/bookings/{booking_id}/complete", response_model=BookingRead)
async def complete_wash(
    booking_id: int,
    telegram_id: int,
    session: AsyncSession = Depends (get_async_session),
):
    user = await _get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    booking = await session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    carwash = await session.get(CarWash, booking.carwash_id)
    if not carwash or carwash.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if booking.status not in (BookingStatus.PAID, BookingStatus.COMPLETED):
        raise HTTPException(status_code=400, detail="Booking is not in correct state")

    booking.status = BookingStatus.COMPLETED
    booking.completed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(booking)
    return booking

