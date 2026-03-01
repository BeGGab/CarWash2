from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_session
from ..models import CarWash, Service
from ..schemas import ServiceRead

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/by-carwash/{carwash_id}", response_model=List[ServiceRead])
async def list_services_for_carwash(
    carwash_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    carwash = await session.get(CarWash, carwash_id)
    if not carwash:
        raise HTTPException(status_code=404, detail="Car wash not found")

    stmt = select(Service).where(Service.carwash_id == carwash_id)
    res = await session.execute(stmt)
    return list(res.scalars().all())

