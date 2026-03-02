import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../store";
import Loader from "../components/Loader";
import BackButton from "../components/BackButton";
import { getMyBookings } from "../api";
import type { Booking } from "../api";

export default function MyBookingsPage() {
  const navigate = useNavigate();
  const { haptic, telegramUser } = useAppStore();
  const [activeTab, setActiveTab] = useState<"active" | "history">("active");
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const telegramId = telegramUser?.id;

  useEffect(() => {
    if (!telegramId) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    getMyBookings(telegramId)
      .then(setBookings)
      .catch(() => setBookings([]))
      .finally(() => setIsLoading(false));
  }, [telegramId, activeTab]);

  const filteredBookings = bookings.filter((b) =>
    activeTab === "active"
      ? ["pending_payment", "paid"].includes(b.status)
      : ["completed", "cancelled"].includes(b.status)
  );

  const statusConfig: Record<
    string,
    { icon: string; text: string; color: string }
  > = {
    pending_payment: { icon: "⏳", text: "Ожидает оплаты", color: "text-yellow-600" },
    paid: { icon: "✅", text: "Подтверждено", color: "text-green-600" },
    completed: { icon: "✔️", text: "Завершено", color: "text-gray-600" },
    cancelled: { icon: "❌", text: "Отменено", color: "text-red-600" },
  };

  if (!telegramId) {
    return (
      <div className="px-4 pt-4">
        <p className="text-gray-500">Войдите через Telegram</p>
      </div>
    );
  }

  return (
    <div className="px-4 pt-4">
      <BackButton to="/" className="mb-4" />
      <h2 className="text-xl font-bold mb-4">Мои брони</h2>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => {
            haptic("light");
            setActiveTab("active");
          }}
          className={`flex-1 py-2 rounded-xl font-medium transition-all ${
            activeTab === "active" ? "bg-wash-primary text-white" : "bg-gray-100"
          }`}
        >
          Активные
        </button>
        <button
          onClick={() => {
            haptic("light");
            setActiveTab("history");
          }}
          className={`flex-1 py-2 rounded-xl font-medium transition-all ${
            activeTab === "history"
              ? "bg-wash-primary text-white"
              : "bg-gray-100"
          }`}
        >
          История
        </button>
      </div>

      {isLoading ? (
        <Loader />
      ) : (
        <div className="space-y-3 pb-8">
          {filteredBookings.length > 0 ? (
            filteredBookings.map((booking) => {
              const status = statusConfig[booking.status] ?? {
                icon: "•",
                text: booking.status,
                color: "text-gray-600",
              };
              const name =
                booking.carwash_name ?? `Мойка #${booking.carwash_id}`;
              const serviceName =
                booking.service_name ?? `Услуга #${booking.service_id}`;
              return (
                <div
                  key={booking.id}
                  onClick={() => {
                    haptic("light");
                    navigate(`/booking/${booking.id}`);
                  }}
                  className="card card-hover cursor-pointer"
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold">{name}</h3>
                    <span className={`text-xs font-medium ${status.color}`}>
                      {status.icon} {status.text}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>
                      📅 {booking.date} в {booking.start_time}
                    </div>
                    <div>🧽 {serviceName}</div>
                  </div>
                  <div className="mt-2 pt-2 border-t flex justify-between items-center">
                    <span className="text-sm text-gray-500">Стоимость</span>
                    <span className="font-semibold">{booking.total_price}₽</span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center py-12 text-gray-500">
              <p>
                {activeTab === "active"
                  ? "Нет активных бронирований"
                  : "История пуста"}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
