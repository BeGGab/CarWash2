import base64
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_async_session
from ..models import Booking, BookingStatus, Payment, PaymentStatus, Refund, RefundStatus
from ..schemas import PaymentCreate, PaymentRead, RefundCreate, RefundRead
from ..services.refund_service import create_refund as do_create_refund

router = APIRouter(prefix="/payments", tags=["payments"])


def _yookassa_auth_header() -> str:
    # YooKassa uses HTTP Basic with shop_id:secret_key
    token = f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}"
    return base64.b64encode(token.encode()).decode()


@router.post("/create", response_model=PaymentRead)
async def create_yookassa_payment(
    payload: PaymentCreate,
    session: AsyncSession = Depends(get_async_session),
):
    booking = await session.get(Booking, payload.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    amount_rub = float(payload.amount)

    existing_stmt = select(Payment).where(Payment.booking_id == booking.id)
    existing_res = await session.execute(existing_stmt)
    existing_payment = existing_res.scalar_one_or_none()
    if existing_payment:
        raise HTTPException(status_code=400, detail="Payment already exists for booking")

    payment = Payment(
        booking_id=booking.id,
        amount=amount_rub,
        currency=settings.yookassa_currency,
        status=PaymentStatus.PENDING,
    )
    session.add(payment)
    await session.flush()

    confirmation_return_url = f"{settings.frontend_url}/payment-success?booking_id={booking.id}"

    request_body: Dict[str, Any] = {
        "amount": {
            "value": f"{amount_rub:.2f}",
            "currency": settings.yookassa_currency,
        },
        "capture": True,
        "description": f"Предоплата за мойку #{booking.id}",
        "confirmation": {
            "type": "redirect",
            "return_url": confirmation_return_url,
        },
        "metadata": {
            "booking_id": booking.id,
        },
    }

    headers = {
        "Authorization": f"Basic {_yookassa_auth_header()}",
        "Content-Type": "application/json",
        "Idempotence-Key": str(payment.id),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.yookassa.ru/v3/payments",
            json=request_body,
            headers=headers,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="YooKassa error")

    data = resp.json()
    payment.provider_payment_id = data.get("id")
    payment.confirmation_url = (data.get("confirmation") or {}).get("confirmation_url")
    payment.raw_response = data
    await session.commit()
    await session.refresh(payment)

    return payment


@router.post("/yookassa/webhook")
async def yookassa_webhook(request: Request, session: AsyncSession = Depends(get_async_session)):
    payload = await request.json()
    event = payload.get("event")
    payment_data = payload.get("object") or {}
    provider_payment_id = payment_data.get("id")
    metadata = payment_data.get("metadata") or {}
    booking_id = metadata.get("booking_id")

    if not provider_payment_id or not booking_id:
        return {"status": "ignored"}

    result = await session.execute(
        select(Payment).where(Payment.provider_payment_id == provider_payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        result = await session.execute(select(Payment).where(Payment.booking_id == booking_id))
        payment = result.scalar_one_or_none()
    if not payment:
        return {"status": "not_found"}

    booking = await session.get(Booking, booking_id)

    if event == "payment.succeeded":
        payment.status = PaymentStatus.SUCCEEDED
        payment.raw_response = payment_data
        if booking:
            booking.status = BookingStatus.PAID
    elif event == "payment.canceled":
        payment.status = PaymentStatus.CANCELED
        payment.raw_response = payment_data
        if booking and booking.status == BookingStatus.PENDING_PAYMENT:
            booking.status = BookingStatus.CANCELLED

    await session.commit()
    return {"status": "ok"}


@router.post("/{payment_id}/refund", response_model=RefundRead)
async def create_refund(
    payment_id: int,
    payload: RefundCreate,
    session: AsyncSession = Depends(get_async_session),
):
    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != PaymentStatus.SUCCEEDED:
        raise HTTPException(status_code=400, detail="Payment is not succeeded, cannot refund")

    amount_rub = float(payload.amount)
    try:
        refund, _ = await do_create_refund(
            payment, amount_rub, payload.reason,
            idempotence_key=f"refund-{payment.id}-{amount_rub}",
        )
    except RuntimeError:
        raise HTTPException(status_code=502, detail="YooKassa refund error")
    session.add(refund)
    await session.commit()
    await session.refresh(refund)
    return refund
