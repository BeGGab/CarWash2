import React, { useEffect, useState } from "react";
import "./index.css";
import { BACKEND_URL } from "./api";

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

type CarWashWithOwner = CarWash & {
  owner_telegram_id?: number | null;
  owner_full_name?: string | null;
  owner_phone?: string | null;
};

type CarwashAdmin = {
  id: number;
  telegram_id: number;
  full_name?: string | null;
  phone?: string | null;
  role: string;
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
  const [telegramCheckDone, setTelegramCheckDone] = useState(false);
  const [pending, setPending] = useState<CarWash[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [allCarwashes, setAllCarwashes] = useState<CarWashWithOwner[]>([]);
  const [allAdmins, setAllAdmins] = useState<CarwashAdmin[]>([]);
  const [loadingAll, setLoadingAll] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const fromUrl = Number(new URLSearchParams(window.location.search).get("telegram_id"));
    if (fromUrl) {
      setTelegramId(fromUrl);
      setTelegramCheckDone(true);
      return;
    }
    const readTelegram = () => {
      const tg = window.Telegram?.WebApp;
      if (tg?.initDataUnsafe?.user?.id) {
        setTelegramId(tg.initDataUnsafe.user.id);
        tg.ready?.();
        setTelegramCheckDone(true);
        return true;
      }
      return false;
    };
    if (readTelegram()) return;
    const t1 = setTimeout(() => { if (readTelegram()) return; setTelegramCheckDone(true); }, 500);
    const t2 = setTimeout(() => { readTelegram(); setTelegramCheckDone(true); }, 1500);
    return () => { clearTimeout(t1); clearTimeout(t2); };
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
    if (showAll) loadAll();
  }

  async function loadAll() {
    if (telegramId == null) return;
    setLoadingAll(true);
    setError(null);
    const q = `telegram_id=${telegramId}`;
    try {
      const [cwRes, admRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/system/carwashes/all?${q}`),
        fetch(`${BACKEND_URL}/api/system/users/carwash-admins?${q}`),
      ]);
      if (!cwRes.ok) throw new Error("Не удалось загрузить список моек");
      if (!admRes.ok) throw new Error("Не удалось загрузить список админов");
      const cwData = (await cwRes.json()) as CarWashWithOwner[];
      const admData = (await admRes.json()) as CarwashAdmin[];
      setAllCarwashes(cwData);
      setAllAdmins(admData);
      setShowAll(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoadingAll(false);
    }
  }

  async function toggleApproved(cw: CarWashWithOwner) {
    if (telegramId == null) return;
    const res = await fetch(
      `${BACKEND_URL}/api/system/carwashes/${cw.id}?telegram_id=${telegramId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_approved: !cw.is_approved }),
      }
    );
    if (!res.ok) {
      setError("Не удалось изменить статус");
      return;
    }
    setAllCarwashes((prev) =>
      prev.map((c) => (c.id === cw.id ? { ...c, is_approved: !c.is_approved } : c))
    );
    await loadData();
  }

  async function deleteCarwash(id: number) {
    if (telegramId == null) return;
    if (!confirm("Удалить автомойку? Услуги и закрытые слоты будут удалены.")) return;
    const res = await fetch(
      `${BACKEND_URL}/api/system/carwashes/${id}?telegram_id=${telegramId}`,
      { method: "DELETE" }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.detail || "Не удалось удалить");
      return;
    }
    setAllCarwashes((prev) => prev.filter((c) => c.id !== id));
    await loadData();
  }

  if (!telegramCheckDone || telegramId == null) {
    return (
      <div className="app-root">
        <h1>Системный администратор</h1>
        {!telegramCheckDone ? (
          <p className="text-gray-500 py-4">Загрузка…</p>
        ) : (
          <p>Откройте приложение из Telegram или укажите в адресе: ?telegram_id=ВАШ_ID</p>
        )}
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

      <div className="card mt-4">
        <h2>Все автомойки и админы</h2>
        {!showAll ? (
          <button
            type="button"
            onClick={loadAll}
            disabled={loadingAll}
            className="btn-primary mt-2"
          >
            {loadingAll ? "Загрузка…" : "Получить все автомойки и админов"}
          </button>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-2">
              Автомоек: {allCarwashes.length}, Админов: {allAdmins.length}
            </p>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {allCarwashes.map((cw) => (
                <div
                  key={cw.id}
                  className="border border-gray-200 rounded-xl p-3 text-sm"
                >
                  <div className="font-medium">#{cw.id} — {cw.name}</div>
                  <div className="text-gray-600">{cw.address}</div>
                  <div className="text-gray-500 mt-1">
                    Админ: telegram_id {cw.owner_telegram_id ?? "—"}
                    {cw.owner_full_name && `, ${cw.owner_full_name}`}
                    {cw.owner_phone && `, ${cw.owner_phone}`}
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <span
                      className={`badge ${cw.is_approved ? "badge-success" : "badge-warning"}`}
                    >
                      {cw.is_approved ? "Подтверждена" : "На модерации"}
                    </span>
                    <button
                      type="button"
                      onClick={() => toggleApproved(cw)}
                      className="text-xs text-wash-primary"
                    >
                      {cw.is_approved ? "Снять подтверждение" : "Подтвердить"}
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteCarwash(cw.id)}
                      className="text-xs text-red-600"
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <h3 className="font-semibold mt-4 mb-2">Админы моек</h3>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
              {allAdmins.map((u) => (
                <li key={u.id}>
                  telegram_id: {u.telegram_id}
                  {u.full_name && `, ${u.full_name}`}
                  {u.phone && `, ${u.phone}`}
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => loadAll()}
              className="btn-secondary mt-3 text-sm"
            >
              Обновить список
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default SystemAdminApp;

