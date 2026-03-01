import React, { useEffect, useState } from "react";
import "./styles.css";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

declare global {
  interface Window {
    Telegram?: any;
  }
}

type CarWash = {
  id: number;
  name: string;
  address: string;
};

type Service = {
  id: number;
  name: string;
  price: number;
  duration_minutes: number;
};

type Booking = {
  id: number;
  date: string;
  start_time: string;
  status: string;
  payment_id?: number | null;
  prepayment_amount?: number | null;
};

type BlockedSlot = {
  id: number;
  date: string;
  start_time: string;
  end_time: string;
  reason?: string | null;
};

export const AdminCarwashApp: React.FC = () => {
  const [telegramId, setTelegramId] = useState<number | null>(null);
  const [carwashes, setCarwashes] = useState<CarWash[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [blockedSlots, setBlockedSlots] = useState<BlockedSlot[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [newCarwash, setNewCarwash] = useState({
    name: "",
    address: "",
    lat: "",
    lon: "",
    open_time: "09:00",
    close_time: "21:00",
    slot_duration_minutes: 30,
  });

  const [newService, setNewService] = useState({
    name: "",
    price: "",
    duration_minutes: 60,
  });

  const [newBlocked, setNewBlocked] = useState({
    date: "",
    start_time: "",
    end_time: "",
    reason: "",
  });

  useEffect(() => {
    const fromUrl = Number(new URLSearchParams(window.location.search).get("telegram_id"));
    if (fromUrl) {
      setTelegramId(fromUrl);
      return;
    }
    const tg = window.Telegram?.WebApp;
    if (tg?.initDataUnsafe?.user?.id) {
      setTelegramId(tg.initDataUnsafe.user.id);
      tg.ready?.();
    } else {
      const t = setTimeout(() => {
        if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
          setTelegramId(window.Telegram.WebApp.initDataUnsafe.user.id);
        }
      }, 300);
      return () => clearTimeout(t);
    }
  }, []);

  useEffect(() => {
    if (!telegramId) return;
    void loadCarwashes();
    void loadBookings();
  }, [telegramId]);

  async function loadCarwashes() {
    if (!telegramId) return;
    setError(null);
    const res = await fetch(
      `${BACKEND_URL}/api/admin/carwashes/me?telegram_id=${telegramId}`
    );
    if (!res.ok) {
      setError("Не удалось загрузить ваши автомойки");
      return;
    }
    const data = (await res.json()) as CarWash[];
    setCarwashes(data);
    if (data[0]) {
      void loadServices(data[0].id);
      void loadBlockedSlots(data[0].id);
    }
  }

  async function loadServices(carwashId: number) {
    const res = await fetch(`${BACKEND_URL}/api/services/by-carwash/${carwashId}`);
    if (!res.ok) return;
    const data = (await res.json()) as Service[];
    setServices(data);
  }

  async function loadBookings() {
    if (!telegramId) return;
    const res = await fetch(
      `${BACKEND_URL}/api/admin/bookings?telegram_id=${telegramId}`
    );
    if (!res.ok) return;
    const data = (await res.json()) as Booking[];
    setBookings(data);
  }

  async function loadBlockedSlots(carwashId: number) {
    if (!telegramId) return;
    const res = await fetch(
      `${BACKEND_URL}/api/admin/blocked-slots?carwash_id=${carwashId}&telegram_id=${telegramId}`
    );
    if (!res.ok) return;
    const data = (await res.json()) as BlockedSlot[];
    setBlockedSlots(data);
  }

  async function createCarwash(e: React.FormEvent) {
    e.preventDefault();
    if (!telegramId) {
      setError("Не определён пользователь. Откройте из Telegram или добавьте ?telegram_id= в адрес.");
      return;
    }
    const lat = Number(newCarwash.lat) || 0;
    const lon = Number(newCarwash.lon) || 0;
    if (!newCarwash.name.trim()) {
      setError("Укажите название автомойки");
      return;
    }
    if (!newCarwash.address.trim()) {
      setError("Укажите адрес");
      return;
    }
    setError(null);
    const body = {
      name: newCarwash.name.trim(),
      address: newCarwash.address.trim(),
      lat,
      lon,
      description: "",
      photos: [],
      wash_type: "contact",
      additional_services: [],
      open_time: newCarwash.open_time,
      close_time: newCarwash.close_time,
      slot_duration_minutes: newCarwash.slot_duration_minutes,
    };
    const res = await fetch(
      `${BACKEND_URL}/api/admin/carwashes?telegram_id=${telegramId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    if (!res.ok) {
      setError("Не удалось создать автомойку");
      return;
    }
    await loadCarwashes();
  }

  async function createService(e: React.FormEvent) {
    e.preventDefault();
    if (!telegramId || !carwashes[0]) return;
    const body = {
      carwash_id: carwashes[0].id,
      name: newService.name,
      description: "",
      price: Number(newService.price),
      duration_minutes: newService.duration_minutes,
    };
    const res = await fetch(
      `${BACKEND_URL}/api/admin/services?telegram_id=${telegramId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    if (!res.ok) {
      setError("Не удалось добавить услугу");
      return;
    }
    await loadServices(carwashes[0].id);
  }

  async function completeBooking(id: number) {
    if (!telegramId) return;
    const res = await fetch(
      `${BACKEND_URL}/api/admin/bookings/${id}/complete?telegram_id=${telegramId}`,
      { method: "POST" }
    );
    if (!res.ok) {
      setError("Не удалось завершить мойку");
      return;
    }
    await loadBookings();
  }

  async function refundBooking(paymentId: number, amount: number) {
    setError(null);
    const res = await fetch(
      `${BACKEND_URL}/api/payments/${paymentId}/refund`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payment_id: paymentId,
          amount,
          reason: "Отмена администратором",
        }),
      }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.detail || "Не удалось вернуть предоплату");
      return;
    }
    await loadBookings();
  }

  async function createBlockedSlot(e: React.FormEvent) {
    e.preventDefault();
    if (!telegramId || !carwashes[0]) return;
    const body = {
      carwash_id: carwashes[0].id,
      date: newBlocked.date,
      start_time: newBlocked.start_time,
      end_time: newBlocked.end_time,
      reason: newBlocked.reason || undefined,
    };
    const res = await fetch(
      `${BACKEND_URL}/api/admin/blocked-slots?telegram_id=${telegramId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    if (!res.ok) {
      setError("Не удалось создать блокировку");
      return;
    }
    await loadBlockedSlots(carwashes[0].id);
  }

  async function deleteBlockedSlot(id: number) {
    if (!telegramId) return;
    const res = await fetch(
      `${BACKEND_URL}/api/admin/blocked-slots/${id}?telegram_id=${telegramId}`,
      { method: "DELETE" }
    );
    if (!res.ok) return;
    if (carwashes[0]) {
      await loadBlockedSlots(carwashes[0].id);
    }
  }

  return (
    <div className="app-root">
      <h1>Кабинет автомойки</h1>
      {error && <p className="error">{error}</p>}

      {!carwashes.length && (
        <form onSubmit={createCarwash} className="card">
          <h2>Регистрация автомойки</h2>
          <input
            placeholder="Название"
            value={newCarwash.name}
            onChange={(e) => setNewCarwash({ ...newCarwash, name: e.target.value })}
          />
          <input
            placeholder="Адрес"
            value={newCarwash.address}
            onChange={(e) => setNewCarwash({ ...newCarwash, address: e.target.value })}
          />
          <input
            placeholder="Широта (lat)"
            value={newCarwash.lat}
            onChange={(e) => setNewCarwash({ ...newCarwash, lat: e.target.value })}
          />
          <input
            placeholder="Долгота (lon)"
            value={newCarwash.lon}
            onChange={(e) => setNewCarwash({ ...newCarwash, lon: e.target.value })}
          />
          <label>
            Время работы:
            <input
              type="time"
              value={newCarwash.open_time}
              onChange={(e) =>
                setNewCarwash({ ...newCarwash, open_time: e.target.value })
              }
            />
            {" - "}
            <input
              type="time"
              value={newCarwash.close_time}
              onChange={(e) =>
                setNewCarwash({ ...newCarwash, close_time: e.target.value })
              }
            />
          </label>
          <button type="submit" className="primary">
            Создать автомойку
          </button>
        </form>
      )}

      {carwashes[0] && (
        <>
          <div className="carwash-card">
            <h2>{carwashes[0].name}</h2>
            <p>{carwashes[0].address}</p>
          </div>

          <form onSubmit={createService} className="card">
            <h3>Добавить услугу</h3>
            <input
              placeholder="Название услуги"
              value={newService.name}
              onChange={(e) => setNewService({ ...newService, name: e.target.value })}
            />
            <input
              placeholder="Цена, ₽"
              value={newService.price}
              onChange={(e) => setNewService({ ...newService, price: e.target.value })}
            />
            <input
              placeholder="Длительность, мин"
              value={newService.duration_minutes}
              onChange={(e) =>
                setNewService({
                  ...newService,
                  duration_minutes: Number(e.target.value),
                })
              }
            />
            <button type="submit" className="primary">
              Добавить
            </button>
          </form>

          <div className="card">
            <h3>Услуги</h3>
            {services.map((s) => (
              <p key={s.id}>
                {s.name} — {s.price} ₽, {s.duration_minutes} мин
              </p>
            ))}
          </div>

          <form onSubmit={createBlockedSlot} className="card">
            <h3>Закрыть слоты (обед / техперерыв)</h3>
            <input
              type="date"
              value={newBlocked.date}
              onChange={(e) => setNewBlocked({ ...newBlocked, date: e.target.value })}
            />
            <input
              type="time"
              value={newBlocked.start_time}
              onChange={(e) =>
                setNewBlocked({ ...newBlocked, start_time: e.target.value })
              }
            />
            <input
              type="time"
              value={newBlocked.end_time}
              onChange={(e) =>
                setNewBlocked({ ...newBlocked, end_time: e.target.value })
              }
            />
            <input
              placeholder="Комментарий (необязательно)"
              value={newBlocked.reason}
              onChange={(e) =>
                setNewBlocked({ ...newBlocked, reason: e.target.value })
              }
            />
            <button type="submit" className="primary">
              Закрыть время
            </button>
          </form>

          <div className="card">
            <h3>Закрытые слоты</h3>
            {blockedSlots.map((b) => (
              <p key={b.id}>
                {b.date} {b.start_time}-{b.end_time} {b.reason && `(${b.reason})`}{" "}
                <button
                  type="button"
                  onClick={() => deleteBlockedSlot(b.id)}
                >
                  ×
                </button>
              </p>
            ))}
          </div>

          <div className="card">
            <h3>Брони</h3>
            {bookings.map((b) => (
              <p key={b.id}>
                #{b.id} — {b.date} {b.start_time} — {b.status}{" "}
                {b.status !== "completed" && (
                  <button type="button" onClick={() => completeBooking(b.id)}>
                    Завершить
                  </button>
                )}{" "}
                {b.status === "paid" &&
                  b.payment_id != null &&
                  b.prepayment_amount != null && (
                    <button
                      type="button"
                      className="refund-btn"
                      onClick={() =>
                        refundBooking(b.payment_id!, b.prepayment_amount!)
                      }
                    >
                      Вернуть предоплату
                    </button>
                  )}
              </p>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default AdminCarwashApp;

