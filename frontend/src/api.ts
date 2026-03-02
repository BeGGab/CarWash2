let _backendUrl = "";

function getBackendUrlStatic(): string {
  const win = typeof window !== "undefined" ? window as Window & { __BACKEND_URL__?: string } : null;
  if (win?.__BACKEND_URL__) return win.__BACKEND_URL__.trim();
  const env = import.meta.env.VITE_BACKEND_URL;
  if (env && String(env).trim()) return String(env).trim();
  if (win?.location?.origin && /localhost|127\.0\.0\.1/.test(win.location.origin))
    return "http://localhost:8000";
  return win?.location?.origin ?? "http://localhost:8000";
}

export function getBackendUrl(): string {
  return _backendUrl || getBackendUrlStatic();
}

export function setBackendUrl(url: string): void {
  _backendUrl = url;
}

_backendUrl = getBackendUrlStatic();

export const BACKEND_URL = getBackendUrl();

export type AppConfig = {
  defaultCity: { name: string; lat: number; lon: number } | null;
  defaultRadiusKm: number;
};

export async function getAppConfig(): Promise<AppConfig> {
  try {
    const res = await fetch(`${getBackendUrl()}/api/config`);
    if (!res.ok) return { defaultCity: null, defaultRadiusKm: 25 };
    const data = await res.json();
    return {
      defaultCity: data.defaultCity ?? null,
      defaultRadiusKm: typeof data.defaultRadiusKm === "number" ? data.defaultRadiusKm : 25,
    };
  } catch {
    return { defaultCity: null, defaultRadiusKm: 25 };
  }
}

/** Определение города по координатам (Nominatim). */
export async function getCityNameFromCoords(lat: number, lon: number): Promise<string | null> {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=ru`;
    const res = await fetch(url, { headers: { "Accept": "application/json", "User-Agent": "CarWashMiniApp/1.0" } });
    if (!res.ok) return null;
    const data = await res.json();
    const a = data?.address;
    if (!a) return null;
    return a.city ?? a.town ?? a.village ?? a.municipality ?? a.county ?? a.state ?? null;
  } catch {
    return null;
  }
}

function timeToString(t: string): string {
  if (!t) return "";
  const parts = t.split(":");
  return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : t;
}

export type Slot = {
  start_time: string;
  end_time: string;
  is_available: boolean;
};

export type CarWashWithSlots = {
  id: number;
  name: string;
  address: string;
  lat: number;
  lon: number;
  rating?: number | null;
  wash_type: string;
  open_time: string;
  close_time: string;
  slot_duration_minutes: number;
  nearest_slots: Slot[];
};

export type CarWash = {
  id: number;
  name: string;
  address: string;
  lat: number;
  lon: number;
  rating?: number | null;
  wash_type: string;
  open_time: string;
  close_time: string;
  slot_duration_minutes: number;
};

export type Service = {
  id: number;
  carwash_id: number;
  name: string;
  description?: string | null;
  price: number;
  duration_minutes: number;
};

export type Booking = {
  id: number;
  carwash_id: number;
  service_id: number;
  date: string;
  start_time: string;
  end_time: string;
  status: string;
  total_price: number;
  qr_code_data: string;
  prepayment_percent: number;
  carwash_name?: string | null;
  carwash_address?: string | null;
  service_name?: string | null;
};

export type Payment = {
  id: number;
  confirmation_url: string | null;
};

function haversineKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export async function getNearbyCarwashes(
  lat: number,
  lon: number,
  radiusKm = 25,
  afterTime?: string
): Promise<CarWashWithSlots[]> {
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(radiusKm),
  });
  if (afterTime) params.set("after_time", afterTime);
  const res = await fetch(`${getBackendUrl()}/api/carwashes/nearby?${params}`);
  if (!res.ok) throw new Error("Ошибка загрузки списка моек");
  const data = await res.json();
  return data.map((cw: CarWashWithSlots) => ({
    ...cw,
    distance: haversineKm(lat, lon, cw.lat, cw.lon),
    nearest_slots: (cw.nearest_slots || []).map((s: Slot) => ({
      ...s,
      start_time: timeToString(s.start_time),
      end_time: timeToString(s.end_time),
    })),
  }));
}

export async function getCarwash(id: number): Promise<CarWash> {
  const res = await fetch(`${getBackendUrl()}/api/carwashes/${id}`);
  if (!res.ok) throw new Error("Мойка не найдена");
  return res.json();
}

export async function getCarwashSlots(
  carwashId: number,
  dateStr: string
): Promise<Slot[]> {
  const params = new URLSearchParams({ date_str: dateStr });
  const res = await fetch(
    `${getBackendUrl()}/api/carwashes/${carwashId}/slots?${params}`
  );
  if (!res.ok) throw new Error("Ошибка загрузки слотов");
  const data = await res.json();
  return data.map((s: Slot) => ({
    ...s,
    start_time: timeToString(s.start_time),
    end_time: timeToString(s.end_time),
  }));
}

export async function getServices(carwashId: number): Promise<Service[]> {
  const res = await fetch(`${getBackendUrl()}/api/services/by-carwash/${carwashId}`);
  if (!res.ok) throw new Error("Ошибка загрузки услуг");
  return res.json();
}

export async function createBooking(
  telegramId: number,
  carwashId: number,
  serviceId: number,
  dateStr: string,
  startTime: string
): Promise<Booking> {
  const [h, m] = startTime.split(":").map(Number);
  const startTimeISO = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00`;
  const res = await fetch(
    `${getBackendUrl()}/api/bookings?telegram_id=${telegramId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        carwash_id: carwashId,
        service_id: serviceId,
        date: dateStr,
        start_time: startTimeISO,
      }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Ошибка создания брони");
  }
  return res.json();
}

export async function getMyBookings(telegramId: number): Promise<Booking[]> {
  const res = await fetch(
    `${getBackendUrl()}/api/bookings/me?telegram_id=${telegramId}`
  );
  if (!res.ok) throw new Error("Ошибка загрузки броней");
  const data = await res.json();
  return data.map((b: Booking) => ({
    ...b,
    start_time: timeToString(b.start_time),
    end_time: timeToString(b.end_time),
  }));
}

export async function getBooking(bookingId: number): Promise<Booking> {
  const res = await fetch(`${getBackendUrl()}/api/bookings/${bookingId}`);
  if (!res.ok) throw new Error("Бронирование не найдено");
  const b = await res.json();
  return {
    ...b,
    start_time: timeToString(b.start_time),
    end_time: timeToString(b.end_time),
  };
}

export async function cancelBooking(
  bookingId: number,
  telegramId: number
): Promise<Booking> {
  const res = await fetch(
    `${getBackendUrl()}/api/bookings/${bookingId}/cancel?telegram_id=${telegramId}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Ошибка отмены брони");
  const b = await res.json();
  return {
    ...b,
    start_time: timeToString(b.start_time),
    end_time: timeToString(b.end_time),
  };
}

export async function createPayment(
  bookingId: number,
  amount: number
): Promise<Payment> {
  const res = await fetch(`${getBackendUrl()}/api/payments/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ booking_id: bookingId, amount }),
  });
  if (!res.ok) throw new Error("Ошибка создания платежа");
  return res.json();
}
