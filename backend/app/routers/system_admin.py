from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..config import settings
from ..db import get_async_session
from ..models import BlockedSlot, Booking, CarWash, Payment, PaymentStatus, Service, User, UserRole
from ..schemas import AssignCarwashAdminRequest, CarWashRead, CarWashSystemUpdate, CarWashWithOwner, UserRead

router = APIRouter(prefix="/system", tags=["system-admin"])


def require_system_admin(
    telegram_id: int = Query(..., description="Telegram ID системного администратора"),
) -> int:
    if telegram_id not in settings.system_admin_telegram_ids:
        raise HTTPException(status_code=403, detail="Forbidden: only system administrator")
    return telegram_id


@router.get("/carwashes/pending")
async def list_pending_carwashes(
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(CarWash).where(CarWash.is_approved.is_(False))
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.get("/carwashes/all", response_model=List[CarWashWithOwner])
async def list_all_carwashes(
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(CarWash)
        .options(joinedload(CarWash.owner))
        .order_by(CarWash.id)
    )
    res = await session.execute(stmt)
    carwashes = list(res.unique().scalars().all())
    result = []
    for c in carwashes:
        base = CarWashRead.model_validate(c)
        result.append(
            CarWashWithOwner(
                **base.model_dump(),
                owner_telegram_id=c.owner.telegram_id if c.owner else None,
                owner_full_name=c.owner.full_name if c.owner else None,
                owner_phone=c.owner.phone if c.owner else None,
            )
        )
    return result


@router.post("/carwashes/{carwash_id}/approve")
async def approve_carwash(
    carwash_id: int,
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    carwash = await session.get(CarWash, carwash_id)
    if not carwash:
        raise HTTPException(status_code=404, detail="Car wash not found")
    carwash.is_approved = True
    await session.commit()
    await session.refresh(carwash)
    return carwash


@router.patch("/carwashes/{carwash_id}", response_model=CarWashRead)
async def update_carwash_system(
    carwash_id: int,
    payload: CarWashSystemUpdate,
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    carwash = await session.get(CarWash, carwash_id)
    if not carwash:
        raise HTTPException(status_code=404, detail="Car wash not found")
    if payload.is_approved is not None:
        carwash.is_approved = payload.is_approved
    await session.commit()
    await session.refresh(carwash)
    return carwash


@router.delete("/carwashes/{carwash_id}")
async def delete_carwash(
    carwash_id: int,
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    carwash = await session.get(CarWash, carwash_id)
    if not carwash:
        raise HTTPException(status_code=404, detail="Car wash not found")
    bookings_count = await session.scalar(select(func.count(Booking.id)).where(Booking.carwash_id == carwash_id))
    if bookings_count and bookings_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить мойку с существующими бронированиями",
        )
    await session.execute(BlockedSlot.__table__.delete().where(BlockedSlot.carwash_id == carwash_id))
    await session.execute(Service.__table__.delete().where(Service.carwash_id == carwash_id))
    await session.delete(carwash)
    await session.commit()
    return {"status": "ok"}


@router.get("/users/carwash-admins", response_model=List[UserRead])
async def list_carwash_admins(
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(User).where(User.role == UserRole.CARWASH_ADMIN).order_by(User.id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.get("/statistics/overview")
async def statistics_overview(
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    total_carwashes = await session.scalar(select(func.count(CarWash.id)))
    total_approved_carwashes = await session.scalar(
        select(func.count(CarWash.id)).where(CarWash.is_approved.is_(True))
    )
    total_bookings = await session.scalar(select(func.count(Booking.id)))

    total_payments_query = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    total_payments_sum: Decimal = total_payments_query.scalar_one()
    total_payments_float = float(total_payments_sum)

    commission_percent = settings.aggregator_commission_percent
    total_commission = total_payments_float * commission_percent / 100.0

    return {
        "total_carwashes": total_carwashes or 0,
        "total_approved_carwashes": total_approved_carwashes or 0,
        "total_bookings": total_bookings or 0,
        "total_payments_sum": total_payments_float,
        "commission_percent": commission_percent,
        "total_commission": total_commission,
    }


@router.post("/users/assign-carwash-admin", response_model=UserRead)
async def assign_carwash_admin(
    payload: AssignCarwashAdminRequest,
    _admin_id: int = Depends(require_system_admin),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(User).where(User.telegram_id == payload.telegram_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = UserRole.CARWASH_ADMIN
    await session.commit()
    await session.refresh(user)
    return user

