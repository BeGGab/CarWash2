import React, { useEffect, useState } from "react";
import "./styles.css";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

declare global {
  interface Window {
    Telegram?: { WebApp?: { initDataUnsafe?: { user?: { id: number } }; ready?: () => void } };
  }
}

type CarWash = {
  id: number;
  name: string;
  address: string;
  is_approved: boolean;
};

type Stats = {
  total_carwashes: number;
  total_approved_carwashes: number;
  total_bookings: number;
  total_payments_sum: number;
  commission_percent: number;
  total_commission: number;
};

export const SystemAdminApp: React.FC = () => {
  const [telegramId, setTelegramId] = useState<number | null>(null);
  const [pending, setPending] = useState<CarWash[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    if (telegramId == null) return;
    void loadData();
  }, [telegramId]);

  async function loadData() {
    if (telegramId == null) return;
    setError(null);
    const q = `telegram_id=${telegramId}`;
    const [pendingRes, statsRes] = await Promise.all([
      fetch(`${BACKEND_URL}/api/system/carwashes/pending?${q}`),
      fetch(`${BACKEND_URL}/api/system/statistics/overview?${q}`),
    ]);
    if (!pendingRes.ok) {
      setError("Не удалось загрузить список моек");
      return;
    }
    if (!statsRes.ok) {
      setError("Не удалось загрузить статистику");
      return;
    }
    const pendingData = (await pendingRes.json()) as CarWash[];
    const statsData = (await statsRes.json()) as Stats;
    setPending(pendingData);
    setStats(statsData);
  }

  async function approve(id: number) {
    if (telegramId == null) return;
    const res = await fetch(
      `${BACKEND_URL}/api/system/carwashes/${id}/approve?telegram_id=${telegramId}`,
      { method: "POST" }
    );
    if (!res.ok) {
      setError("Не удалось подтвердить автомойку");
      return;
    }
    await loadData();
  }

  if (telegramId == null) {
    return (
      <div className="app-root">
        <h1>Системный администратор</h1>
        <p>Откройте приложение из Telegram или укажите ?telegram_id=… в адресе.</p>
      </div>
    );
  }

  return (
    <div className="app-root">
      <h1>Системный администратор</h1>
      {error && <p className="error">{error}</p>}

      <div className="card">
        <h2>Статистика</h2>
        {stats ? (
          <>
            <p>Всего моек: {stats.total_carwashes}</p>
            <p>Подтверждённых моек: {stats.total_approved_carwashes}</p>
            <p>Всего броней: {stats.total_bookings}</p>
            <p>Сумма предоплат: {stats.total_payments_sum.toFixed(2)} ₽</p>
            <p>
              Комиссия агрегатора: {stats.commission_percent}% (
              {stats.total_commission.toFixed(2)} ₽)
            </p>
          </>
        ) : (
          <p>Загрузка…</p>
        )}
      </div>

      <div className="card">
        <h2>Мойки на модерации</h2>
        {pending.length === 0 && <p>Нет моек в ожидании.</p>}
        {pending.map((cw) => (
          <p key={cw.id}>
            #{cw.id} — {cw.name}, {cw.address}{" "}
            <button type="button" onClick={() => approve(cw.id)}>
              Подтвердить
            </button>
          </p>
        ))}
      </div>
    </div>
  );
};

export default SystemAdminApp;

