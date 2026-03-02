import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAppStore, useBookingStore } from "../store";
import { QRCodeSVG } from "qrcode.react";
import Loader from "../components/Loader";
import BackButton from "../components/BackButton";
import { getBooking, cancelBooking } from "../api";
import type { Booking } from "../api";

export default function BookingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { haptic, telegramUser } = useAppStore();
  const { currentBooking } = useBookingStore();

  const [booking, setBooking] = useState<Booking | null>(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [loading, setLoading] = useState(true);

  const bookingId = id ? parseInt(id, 10) : NaN;
  const telegramId = telegramUser?.id;

  useEffect(() => {
    if (isNaN(bookingId)) {
      setLoading(false);
      return;
    }
    if (currentBooking && currentBooking.id === bookingId) {
      setBooking(currentBooking);
      setLoading(false);
      return;
    }
    setLoading(true);
    getBooking(bookingId)
      .then(setBooking)
      .catch(() => setBooking(null))
      .finally(() => setLoading(false));
  }, [bookingId, currentBooking]);

  const handleCancel = () => {
    haptic("warning");
    setShowCancelModal(true);
  };

  const confirmCancel = async () => {
    if (!telegramId || !bookingId) return;
    haptic("medium");
    try {
      await cancelBooking(bookingId, telegramId);
      navigate("/my-bookings");
    } catch {
      setShowCancelModal(false);
    }
  };

  if (loading || !booking) {
    return (
      <div className="px-4 pt-4">
        <BackButton to="/my-bookings" className="mb-4" />
        <Loader />
      </div>
    );
  }

  const statusConfig: Record<
    string,
    { icon: string; text: string; bg: string }
  > = {
    pending_payment: {
      icon: "⏳",
      text: "Ожидает оплаты",
      bg: "bg-yellow-100 text-yellow-800",
    },
    paid: {
      icon: "✅",
      text: "Подтверждено",
      bg: "bg-green-100 text-green-800",
    },
    completed: {
      icon: "✔️",
      text: "Завершено",
      bg: "bg-gray-100 text-gray-800",
    },
    cancelled: {
      icon: "❌",
      text: "Отменено",
      bg: "bg-red-100 text-red-800",
    },
  };

  const status = statusConfig[booking.status] ?? {
    icon: "•",
    text: booking.status,
    bg: "bg-gray-100 text-gray-800",
  };
  const canCancel = ["pending_payment", "paid"].includes(booking.status);
  const showQR = booking.status === "paid";
  const name = booking.carwash_name ?? `Мойка #${booking.carwash_id}`;
  const address = booking.carwash_address ?? "";
  const serviceName =
    booking.service_name ?? `Услуга #${booking.service_id}`;

  return (
    <div className="px-4 pt-4 pb-24">
      <BackButton to="/my-bookings" className="mb-4" />
      <div className="flex justify-center mb-4">
        <span className={`badge text-sm px-4 py-1.5 ${status.bg}`}>
          {status.icon} {status.text}
        </span>
      </div>

      {showQR && (
        <div className="card flex flex-col items-center py-6 mb-4">
          <div className="bg-white p-4 rounded-xl shadow-inner mb-3">
            <QRCodeSVG
              value={booking.qr_code_data}
              size={180}
              level="H"
            />
          </div>
          <p className="text-sm text-gray-500 text-center">
            Покажите этот QR-код
            <br />
            администратору мойки
          </p>
        </div>
      )}

      <div className="card mb-4">
        <h3 className="font-semibold text-lg mb-3">{name}</h3>
        <div className="space-y-2 text-sm">
          {address && (
            <div className="flex items-start gap-2">
              <span>📍</span>
              <span>{address}</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <span>📅</span>
            <span>{booking.date}</span>
          </div>
          <div className="flex items-center gap-2">
            <span>⏰</span>
            <span>
              {booking.start_time} - {booking.end_time}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span>🧽</span>
            <span>{serviceName}</span>
          </div>
        </div>
        <div className="mt-4 pt-3 border-t flex justify-between items-center">
          <span className="text-gray-500">Стоимость</span>
          <span className="text-xl font-bold">{booking.total_price}₽</span>
        </div>
      </div>

      {canCancel && (
        <button
          onClick={handleCancel}
          className="w-full py-3 text-red-600 font-medium"
        >
          Отменить бронирование
        </button>
      )}

      {showCancelModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-end z-50"
          onClick={() => setShowCancelModal(false)}
        >
          <div
            className="bg-white w-full rounded-t-2xl p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-center mb-2">
              Отменить бронирование?
            </h3>
            <p className="text-sm text-gray-500 text-center mb-4">
              При отмене менее чем за 2 часа возврат не производится
            </p>
            <div className="space-y-2">
              <button
                onClick={confirmCancel}
                className="w-full py-3 bg-red-500 text-white rounded-xl font-medium"
              >
                Да, отменить
              </button>
              <button
                onClick={() => setShowCancelModal(false)}
                className="w-full py-3 bg-gray-100 rounded-xl font-medium"
              >
                Нет, оставить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
