from datetime import date, time, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .models import BookingStatus, PaymentStatus, RefundStatus, UserRole, WashType


class UserBase(BaseModel):
    telegram_id: int
    phone: Optional[str] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class AssignCarwashAdminRequest(BaseModel):
    telegram_id: int


class CarWashBase(BaseModel):
    name: str
    address: str
    lat: float
    lon: float
    description: Optional[str] = None
    photos: Optional[list[str]] = None
    wash_type: WashType
    additional_services: Optional[list[str]] = None
    open_time: time
    close_time: time
    slot_duration_minutes: int = 30


class CarWashCreate(CarWashBase):
    pass


class CarWashRead(CarWashBase):
    id: int
    rating: Optional[float] = None
    is_approved: bool

    class Config:
        from_attributes = True


class CarWashWithOwner(CarWashRead):
    owner_telegram_id: Optional[int] = None
    owner_full_name: Optional[str] = None
    owner_phone: Optional[str] = None


class CarWashSystemUpdate(BaseModel):
    is_approved: Optional[bool] = None


class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    duration_minutes: int = 60


class ServiceCreate(ServiceBase):
    carwash_id: int


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    duration_minutes: Optional[int] = None


class ServiceRead(ServiceBase):
    id: int
    carwash_id: int

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    carwash_id: int
    service_id: int
    date: date
    start_time: time


class BookingRead(BaseModel):
    id: int
    user_id: int
    carwash_id: int
    service_id: int
    date: date
    start_time: time
    end_time: time
    status: BookingStatus
    prepayment_percent: int
    total_price: float
    qr_code_data: str
    created_at: datetime
    canceled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    payment_id: Optional[int] = None
    prepayment_amount: Optional[float] = None

    class Config:
        from_attributes = True


class BookingReadEnriched(BookingRead):
    carwash_name: Optional[str] = None
    carwash_address: Optional[str] = None
    service_name: Optional[str] = None


class PaymentCreate(BaseModel):
    booking_id: int
    amount: float


class PaymentRead(BaseModel):
    id: int
    booking_id: int
    provider: str
    provider_payment_id: Optional[str]
    amount: float
    currency: str
    status: PaymentStatus
    confirmation_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RefundCreate(BaseModel):
    payment_id: int
    amount: float
    reason: Optional[str] = None


class RefundRead(BaseModel):
    id: int
    payment_id: int
    provider_refund_id: Optional[str]
    amount: float
    currency: str
    status: RefundStatus
    reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NearbyCarWashFilter(BaseModel):
    lat: float
    lon: float
    radius_km: float = Field(default=10.0, ge=0.5, le=50.0)
    after_time: Optional[time] = None
    wash_types: Optional[List[WashType]] = None
    additional_services: Optional[List[str]] = None


class Slot(BaseModel):
    start_time: time
    end_time: time
    is_available: bool


class CarWashWithSlots(CarWashRead):
    nearest_slots: List[Slot]


class BlockedSlotBase(BaseModel):
    carwash_id: int
    date: date
    start_time: time
    end_time: time
    reason: Optional[str] = None


class BlockedSlotCreate(BlockedSlotBase):
    pass


class BlockedSlotRead(BlockedSlotBase):
    id: int

    class Config:
        from_attributes = True
