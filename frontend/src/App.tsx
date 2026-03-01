import React, { useEffect, useState } from "react";

type Slot = {
  start_time: string;
  end_time: string;
  is_available: boolean;
};

type CarWash = {
  id: number;
  name: string;
  address: string;
  rating?: number | null;
  wash_type: string;
  nearest_slots: Slot[];
};

type Service = {
  id: number;
  name: string;
  price: number;
  duration_minutes: number;
};

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

declare global {
  interface Window {
    Telegram?: any;
  }
}

export const App: React.FC = () => {
  const [telegramId, setTelegramId] = useState<number | null>(null);
  const [carwashes, setCarwashes] = useState<CarWash[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [afterTime, setAfterTime] = useState<string>("");
  const [washTypeFilter, setWashTypeFilter] = useState<string>("");
  const [serviceFilter, setServiceFilter] = useState<string>("");

  const [selectedCarwash, setSelectedCarwash] = useState<CarWash | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [selectedServiceId, setSelectedServiceId] = useState<number | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg && tg.initDataUnsafe?.user?.id) {
      setTelegramId(tg.initDataUnsafe.user.id);
      tg.ready();
    } else {
      const debugId = Number(new URLSearchParams(window.location.search).get("telegram_id"));
      if (debugId) {
        setTelegramId(debugId);
      }
    }
  }, []);

  async function loadCarwashes() {
    if (!navigator.geolocation) return;

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const params = new URLSearchParams({
            lat: String(pos.coords.latitude),
            lon: String(pos.coords.longitude),
            radius_km: "10",
          });
          if (afterTime) params.set("after_time", afterTime);
          if (washTypeFilter) params.append("wash_types", washTypeFilter);
          if (serviceFilter) params.append("additional_services", serviceFilter);

          const res = await fetch(`${BACKEND_URL}/api/carwashes/nearby?${params.toString()}`);
          if (!res.ok) throw new Error("Ошибка загрузки списка моек");
          const data = (await res.json()) as CarWash[];
          setCarwashes(data);
        } catch (e: any) {
          setError(e.message ?? "Ошибка");
        } finally {
          setLoading(false);
        }
      },
      (err) => {
        console.error(err);
        setError("Разрешите доступ к геопозиции для поиска ближайших моек.");
        setLoading(false);
      }
    );
  }

  useEffect(() => {
    void loadCarwashes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openBooking(cw: CarWash, slot: Slot) {
    setSelectedCarwash(cw);
    setSelectedSlot(slot);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/services/by-carwash/${cw.id}`);
      if (!res.ok) throw new Error("Не удалось загрузить услуги");
      const data = (await res.json()) as Service[];
      setServices(data);
      if (data.length > 0) setSelectedServiceId(data[0].id);
    } catch (e: any) {
      setError(e.message ?? "Ошибка");
    }
  }

  async function createBookingAndPay() {
    if (!telegramId || !selectedCarwash || !selectedSlot || !selectedServiceId) return;

    try {
      setError(null);

      const today = new Date();
      const dateStr = today.toISOString().slice(0, 10);

      const bookingRes = await fetch(
        `${BACKEND_URL}/api/bookings?telegram_id=${telegramId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            carwash_id: selectedCarwash.id,
            service_id: selectedServiceId,
            date: dateStr,
            start_time: selectedSlot.start_time,
          }),
        }
      );
      if (!bookingRes.ok) throw new Error("Ошибка создания брони");
      const booking = await bookingRes.json();

      const prepaymentAmount =
        (Number(booking.total_price) * Number(booking.prepayment_percent)) / 100;

      const paymentRes = await fetch(`${BACKEND_URL}/api/payments/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          booking_id: booking.id,
          amount: prepaymentAmount,
        }),
      });
      if (!paymentRes.ok) throw new Error("Ошибка создания платежа");
      const payment = await paymentRes.json();

      const url = payment.confirmation_url;
      if (url) {
        window.location.href = url;
      } else {
        setError("Платёж создан, но отсутствует ссылка на оплату.");
      }
    } catch (e: any) {
      setError(e.message ?? "Ошибка при бронировании");
    }
  }

  return (
    <div className="app-root">
      <h1>Автомойки рядом</h1>

       <div className="filters">
        <input
          type="time"
          value={afterTime}
          onChange={(e) => setAfterTime(e.target.value)}
          placeholder="После времени"
        />
        <select
          value={washTypeFilter}
          onChange={(e) => setWashTypeFilter(e.target.value)}
        >
          <option value="">Любой тип</option>
          <option value="contact">Контактная</option>
          <option value="touchless">Бесконтактная</option>
          <option value="self_service">Самообслуживание</option>
        </select>
        <input
          type="text"
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
          placeholder="Доп. услуга (химчистка)"
        />
        <button type="button" onClick={loadCarwashes}>
          Применить
        </button>
      </div>

      {loading && <p>Загружаем список моек…</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !carwashes.length && !error && (
        <p>Моек рядом не найдено. Попробуйте позже.</p>
      )}

      <div className="carwash-list">
        {carwashes.map((cw) => (
          <div key={cw.id} className="carwash-card">
            <h2>{cw.name}</h2>
            <p>{cw.address}</p>
            {cw.rating != null && <p>Рейтинг: {cw.rating.toFixed(1)}</p>}
            <p>Тип: {cw.wash_type}</p>
            <div className="slots">
              {cw.nearest_slots && cw.nearest_slots.length > 0 ? (
                cw.nearest_slots
                  .filter((s) => s.is_available)
                  .map((slot) => (
                    <button
                      key={slot.start_time}
                      className="slot-btn"
                      onClick={() => openBooking(cw, slot)}
                    >
                      {slot.start_time}
                    </button>
                  ))
              ) : (
                <p>Сегодня свободных слотов нет</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {selectedCarwash && selectedSlot && (
        <div className="booking-panel">
          <h2>Бронирование</h2>
          <p>
            <b>{selectedCarwash.name}</b>, {selectedSlot.start_time}
          </p>

          {services.length > 0 ? (
            <select
              value={selectedServiceId ?? ""}
              onChange={(e) => setSelectedServiceId(Number(e.target.value))}
            >
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} — {s.price} ₽
                </option>
              ))}
            </select>
          ) : (
            <p>Для этой мойки услуги не заданы.</p>
          )}

          <button
            className="primary"
            disabled={!services.length || !telegramId}
            onClick={createBookingAndPay}
          >
            Забронировать и оплатить 50%
          </button>
        </div>
      )}
    </div>
  );
};

