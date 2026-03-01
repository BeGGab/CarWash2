from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_async_session
from ..models import Booking, CarWash, Payment, PaymentStatus, User, UserRole
from ..schemas import AssignCarwashAdminRequest, UserRead

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

