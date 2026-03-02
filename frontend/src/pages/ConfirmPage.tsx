import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useBookingStore, useAppStore } from "../store";
import BackButton from "../components/BackButton";
import {
  createBooking,
  createPayment,
} from "../api";

export default function ConfirmPage() {
  const navigate = useNavigate();
  const { haptic, telegramUser, syncTelegramUser } = useAppStore();

  useEffect(() => {
    syncTelegramUser();
  }, [syncTelegramUser]);
  const {
    selectedCarwash,
    selectedDate,
    selectedSlot,
    selectedService,
    setCurrentBooking,
  } = useBookingStore();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const telegramId = telegramUser?.id;
  const price = selectedService?.price ?? 0;
  const prepayment = price * 0.5;

  const handlePay = async () => {
    syncTelegramUser();
    const currentId = useAppStore.getState().telegramUser?.id;
    if (
      !selectedCarwash ||
      !selectedDate ||
      !selectedSlot ||
      !selectedService
    ) {
      setError("Заполните все поля");
      return;
    }
    if (!currentId) {
      setError("Откройте приложение из Telegram для оплаты.");
      return;
    }
    setIsLoading(true);
    setError(null);
    haptic("medium");
    try {
      const booking = await createBooking(
        currentId,
        selectedCarwash.id,
        selectedService.id,
        selectedDate,
        selectedSlot.start_time
      );
      setCurrentBooking(booking);

      const payment = await createPayment(booking.id, prepayment);
      if (payment.confirmation_url) {
        window.location.href = payment.confirmation_url;
      } else {
        setError("Ошибка создания платежа");
        setIsLoading(false);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка бронирования");
      setIsLoading(false);
    }
  };

  if (!selectedCarwash || !selectedService || !selectedDate || !selectedSlot) {
    return (
      <div className="px-4 pt-4">
        <BackButton className="mb-4" />
        <p className="text-gray-500">
          Выберите мойку, услугу, дату и время
        </p>
      </div>
    );
  }

  return (
    <div className="px-4 pt-4 pb-24">
      <BackButton className="mb-4" />
      <h2 className="text-xl font-bold mb-4">Подтверждение</h2>

      <div className="card mb-4">
        <h3 className="font-semibold text-lg mb-3">{selectedCarwash.name}</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Адрес</span>
            <span>{selectedCarwash.address}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Дата</span>
            <span>{selectedDate}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Время</span>
            <span>
              {selectedSlot.start_time} - {selectedSlot.end_time}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Услуга</span>
            <span>{selectedService.name}</span>
          </div>
        </div>
      </div>

      <div className="card mb-4 bg-wash-primary/5 border-wash-primary/20">
        <div className="flex justify-between items-center mb-2">
          <span className="text-gray-600">Стоимость услуги</span>
          <span className="font-semibold">{price}₽</span>
        </div>
        <div className="flex justify-between items-center text-lg">
          <span className="font-semibold">Предоплата (50%)</span>
          <span className="font-bold text-wash-primary">{prepayment}₽</span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Оставшиеся {prepayment}₽ оплачиваются на месте
        </p>
      </div>

      <p className="text-xs text-gray-500 text-center mb-4">
        Отмена бесплатна за 2+ часа до начала
      </p>

      {error && (
        <p className="text-red-600 text-sm text-center mb-4">{error}</p>
      )}

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t">
        <button
          type="button"
          onClick={handlePay}
          disabled={isLoading}
          className="btn-primary w-full flex items-center justify-center gap-2 min-h-[48px] cursor-pointer"
        >
          {isLoading ? (
            <>
              <span className="animate-spin">⏳</span>
              <span>Обработка...</span>
            </>
          ) : (
            <>
              <span>💳</span>
              <span>Оплатить {prepayment}₽</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
