from datetime import date, datetime, timedelta, time as time_type
from math import cos, radians
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_session
from ..models import BlockedSlot, Booking, BookingStatus, CarWash, WashType
from ..schemas import CarWashRead, CarWashWithSlots, NearbyCarWashFilter, Slot

router = APIRouter(prefix="/carwashes", tags=["carwashes"])


EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, sin, sqrt

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_KM * c


@router.get("/nearby", response_model=List[CarWashWithSlots])
async def get_nearby_carwashes(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(25.0, ge=0.5, le=100.0),
    after_time: str | None = Query(None),
    wash_types: list[WashType] | None = Query(None),
    additional_services: list[str] | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(CarWash).where(CarWash.is_approved.is_(True))
    result = await session.execute(stmt)
    carwashes: list[CarWash] = list(result.scalars().all())

    # Сначала отбираем мойки в радиусе
    in_radius: list[tuple[CarWash, float]] = []
    for cw in carwashes:
        d = haversine_distance_km(lat, lon, cw.lat, cw.lon)
        if d <= radius_km:
            if wash_types and cw.wash_type not in wash_types:
                continue
            if additional_services:
                cw_services = set((cw.additional_services or []))
                if not cw_services.intersection(additional_services):
                    continue
            in_radius.append((cw, d))

    # Если в радиусе ни одной — отдаём ближайшие по расстоянию (до 10), чтобы не показывать "Моек не найдено"
    if not in_radius:
        with_distance: list[tuple[CarWash, float]] = []
        for cw in carwashes:
            if wash_types and cw.wash_type not in wash_types:
                continue
            if additional_services:
                cw_services = set((cw.additional_services or []))
                if not cw_services.intersection(additional_services):
                    continue
            d = haversine_distance_km(lat, lon, cw.lat, cw.lon)
            with_distance.append((cw, d))
        with_distance.sort(key=lambda x: x[1])
        in_radius = with_distance[:10]

    filtered: list[CarWash] = [cw for cw, _ in in_radius]

    # Compute simple nearest free slots for today
    now = datetime.now()
    today_date = now.date()
    time_threshold: time_type | None = None
    if after_time:
        try:
            hh, mm = map(int, after_time.split(":"))
            time_threshold = time_type(hour=hh, minute=mm)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid after_time format, use HH:MM")

    response: list[CarWashWithSlots] = []
    for cw in filtered:
        slots: list[Slot] = []
        start = cw.open_time
        end = cw.close_time
        slot_delta = timedelta(minutes=cw.slot_duration_minutes)

        current_dt = datetime.combine(today_date, start)
        end_dt = datetime.combine(today_date, end)

        while current_dt + slot_delta <= end_dt:
            slot_start = current_dt.time()
            slot_end = (current_dt + slot_delta).time()

            if time_threshold and slot_start <= time_threshold:
                current_dt += slot_delta
                continue

            # check for existing bookings
            booking_stmt = select(Booking).where(
                and_(
                    Booking.carwash_id == cw.id,
                    Booking.date == today_date,
                    Booking.start_time == slot_start,
                )
            )
            booking_res = await session.execute(booking_stmt)
            existing = booking_res.scalar_one_or_none()

            # check for blocked slots (обед, техперерыв и т.п.)
            blocked_stmt = select(BlockedSlot).where(
                and_(
                    BlockedSlot.carwash_id == cw.id,
                    BlockedSlot.date == today_date,
                    BlockedSlot.start_time <= slot_start,
                    BlockedSlot.end_time >= slot_end,
                )
            )
            blocked_res = await session.execute(blocked_stmt)
            blocked = blocked_res.scalar_one_or_none()

            is_available = existing is None and blocked is None

            slots.append(Slot(start_time=slot_start, end_time=slot_end, is_available=is_available))
            if len(slots) >= 5:
                break
            current_dt += slot_delta

        response.append(
            CarWashWithSlots(
                id=cw.id,
                name=cw.name,
                address=cw.address,
                lat=cw.lat,
                lon=cw.lon,
                description=cw.description,
                photos=cw.photos,
                wash_type=cw.wash_type,
                additional_services=cw.additional_services,
                open_time=cw.open_time,
                close_time=cw.close_time,
                slot_duration_minutes=cw.slot_duration_minutes,
                rating=cw.rating,
                is_approved=cw.is_approved,
                nearest_slots=slots,
            )
        )

    return response


@router.get("/{carwash_id}", response_model=CarWashRead)
async def get_carwash(carwash_id: int, session: AsyncSession = Depends(get_async_session)):
    carwash = await session.get(CarWash, carwash_id)
    if not carwash or not carwash.is_approved:
        raise HTTPException(status_code=404, detail="Car wash not found")
    return carwash


@router.get("/{carwash_id}/slots", response_model=List[Slot])
async def get_carwash_slots(
    carwash_id: int,
    date_str: str = Query(..., description="Date YYYY-MM-DD"),
    session: AsyncSession = Depends(get_async_session),
):
    carwash = await session.get(CarWash, carwash_id)
    if not carwash or not carwash.is_approved:
        raise HTTPException(status_code=404, detail="Car wash not found")

    try:
        slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    start = carwash.open_time
    end = carwash.close_time
    slot_delta = timedelta(minutes=carwash.slot_duration_minutes)

    current_dt = datetime.combine(slot_date, start)
    end_dt = datetime.combine(slot_date, end)
    slots: list[Slot] = []

    while current_dt + slot_delta <= end_dt:
        slot_start = current_dt.time()
        slot_end = (current_dt + slot_delta).time()

        booking_stmt = select(Booking).where(
            and_(
                Booking.carwash_id == carwash_id,
                Booking.date == slot_date,
                Booking.start_time == slot_start,
                Booking.status != BookingStatus.CANCELLED,
            )
        )
        booking_res = await session.execute(booking_stmt)
        existing = booking_res.scalar_one_or_none()

        blocked_stmt = select(BlockedSlot).where(
            and_(
                BlockedSlot.carwash_id == carwash_id,
                BlockedSlot.date == slot_date,
                BlockedSlot.start_time <= slot_start,
                BlockedSlot.end_time >= slot_end,
            )
        )
        blocked_res = await session.execute(blocked_stmt)
        blocked = blocked_res.scalar_one_or_none()

        is_available = existing is None and blocked is None
        slots.append(Slot(start_time=slot_start, end_time=slot_end, is_available=is_available))
        current_dt += slot_delta

    return slots
