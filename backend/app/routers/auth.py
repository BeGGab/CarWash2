from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_session
from ..models import User, UserRole
from ..schemas import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
async def register_or_get_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(User).where(User.telegram_id == payload.telegram_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if user:
        return user

    user = User(
        telegram_id=payload.telegram_id,
        phone=payload.phone,
        full_name=payload.full_name,
        role=UserRole.USER,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/me", response_model=UserRead)
async def get_me(telegram_id: int, session: AsyncSession = Depends(get_async_session)):
    stmt = select(User).where(User.telegram_id == telegram_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

