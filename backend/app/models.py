import enum
from datetime import datetime, time
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class UserRole(str, enum.Enum):
    USER = "user"
    CARWASH_ADMIN = "carwash_admin"
    SYSTEM_ADMIN = "system_admin"


class WashType(str, enum.Enum):
    CONTACT = "contact"
    TOUCHLESS = "touchless"
    SELF_SERVICE = "self_service"


class BookingStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    carwashes: Mapped[list["CarWash"]] = relationship(back_populates="owner")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class CarWash(Base):
    __tablename__ = "carwashes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(512))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photos: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)

    wash_type: Mapped[WashType] = mapped_column(Enum(WashType))
    additional_services: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)

    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    open_time: Mapped[time] = mapped_column()
    close_time: Mapped[time] = mapped_column()
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)

    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="carwashes")
    services: Mapped[list["Service"]] = relationship(back_populates="carwash")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="carwash")
    blocked_slots: Mapped[list["BlockedSlot"]] = relationship(
        back_populates="carwash", cascade="all, delete-orphan"
    )


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    carwash_id: Mapped[int] = mapped_column(ForeignKey("carwashes.id"))

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)

    carwash: Mapped[CarWash] = relationship(back_populates="services")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    carwash_id: Mapped[int] = mapped_column(ForeignKey("carwashes.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))

    date: Mapped[Date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column()
    end_time: Mapped[time] = mapped_column()

    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.PENDING_PAYMENT)
    prepayment_percent: Mapped[int] = mapped_column(Integer, default=50)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2))

    qr_code_data: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="bookings")
    carwash: Mapped[CarWash] = relationship(back_populates="bookings")
    service: Mapped[Service] = relationship(back_populates="bookings")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="booking", uselist=False)

    @property
    def payment_id(self) -> Optional[int]:
        return self.payment.id if self.payment else None

    @property
    def prepayment_amount(self) -> Optional[float]:
        if self.payment and self.payment.status == PaymentStatus.SUCCEEDED:
            return float(self.payment.amount)
        return None


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)

    provider: Mapped[str] = mapped_column(String(32), default="yookassa")
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    confirmation_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    booking: Mapped[Booking] = relationship(back_populates="payment")


class BlockedSlot(Base):
    __tablename__ = "blocked_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    carwash_id: Mapped[int] = mapped_column(ForeignKey("carwashes.id"))
    date: Mapped[Date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column()
    end_time: Mapped[time] = mapped_column()
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    carwash: Mapped[CarWash] = relationship(back_populates="blocked_slots")


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"))
    provider_refund_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    status: Mapped[RefundStatus] = mapped_column(Enum(RefundStatus), default=RefundStatus.PENDING)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
