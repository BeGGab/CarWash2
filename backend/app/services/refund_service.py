from typing import Any, Dict

import httpx

from ..config import settings
from ..models import Payment, Refund, RefundStatus


def _yookassa_auth_header() -> str:
    import base64
    token = f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}"
    return base64.b64encode(token.encode()).decode()


async def create_refund(
    payment: Payment,
    amount: float,
    reason: str | None,
    *,
    idempotence_key: str | None = None,
) -> tuple[Refund, Dict[str, Any]]:
    """Создаёт возврат в ЮKassa и возвращает (Refund ORM, raw_response). Не коммитит сессию."""
    request_body: Dict[str, Any] = {
        "amount": {
            "value": f"{amount:.2f}",
            "currency": payment.currency,
        },
        "payment_id": payment.provider_payment_id,
        "description": reason or f"Refund for booking {payment.booking_id}",
    }
    key = idempotence_key or f"refund-{payment.id}-{amount}"
    headers = {
        "Authorization": f"Basic {_yookassa_auth_header()}",
        "Content-Type": "application/json",
        "Idempotence-Key": key,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.yookassa.ru/v3/refunds",
            json=request_body,
            headers=headers,
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError("YooKassa refund error")
    data = resp.json()
    raw_status = (data.get("status") or "pending").lower()
    status = (
        RefundStatus(raw_status)
        if raw_status in ("pending", "succeeded", "canceled")
        else RefundStatus.PENDING
    )
    refund = Refund(
        payment_id=payment.id,
        provider_refund_id=data.get("id"),
        amount=amount,
        currency=payment.currency,
        status=status,
        reason=reason,
        raw_response=data,
    )
    return refund, data
