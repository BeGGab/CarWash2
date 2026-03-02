import React, { useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";

export default function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const bookingId = searchParams.get("booking_id");

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    tg?.ready?.();
  }, []);

  return (
    <div className="px-4 pt-4 flex flex-col items-center justify-center min-h-[60vh]">
      <div className="text-4xl mb-4">✅</div>
      <h2 className="text-xl font-semibold mb-2">Оплата прошла!</h2>
      <p className="text-gray-500 text-sm text-center mb-6">
        Бронирование подтверждено
      </p>
      {bookingId && (
        <button
          onClick={() => navigate(`/booking/${bookingId}`)}
          className="btn-primary"
        >
          Открыть бронирование
        </button>
      )}
      <button
        onClick={() => navigate("/")}
        className="btn-secondary mt-3"
      >
        На главную
      </button>
    </div>
  );
}
