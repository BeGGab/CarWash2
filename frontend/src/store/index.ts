import { create } from "zustand";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initDataUnsafe?: { user?: { id: number; first_name?: string } };
        ready?: () => void;
        MainButton?: {
          setText: (t: string) => void;
          onClick: (cb: () => void) => void;
          show: () => void;
          hide: () => void;
        };
        HapticFeedback?: {
          impactOccurred: (t: "light" | "medium" | "heavy" | "success" | "warning") => void;
        };
      };
    };
  }
}

const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;

export interface LocationCoords {
  latitude: number;
  longitude: number;
}

export type DefaultCity = { name: string; lat: number; lon: number };

export const useAppStore = create<{
  telegramUser: { id: number; first_name?: string } | null;
  location: LocationCoords | null;
  setLocation: (loc: LocationCoords | null) => void;
  haptic: (t?: "light" | "medium" | "heavy" | "success" | "warning") => void;
  defaultCity: DefaultCity | null;
  defaultRadiusKm: number;
  setAppConfig: (city: DefaultCity | null, radiusKm: number) => void;
  locationCityName: string | null;
  setLocationCityName: (name: string | null) => void;
  /** Синхронизировать telegramUser из window.Telegram (вызывать при монтировании страниц и при фокусе). */
  syncTelegramUser: () => void;
  /** true после загрузки config.json и настроек (нужно для корректного BACKEND_URL с телефона). */
  backendReady: boolean;
  setBackendReady: (v: boolean) => void;
}>((set, get) => ({
  telegramUser: tg?.initDataUnsafe?.user
    ? { id: tg.initDataUnsafe.user.id, first_name: tg.initDataUnsafe.user.first_name }
    : null,
  location: null,
  setLocation: (loc) => set({ location: loc }),
  haptic: (t = "light") => {
    tg?.HapticFeedback?.impactOccurred(t);
  },
  defaultCity: null,
  defaultRadiusKm: 25,
  setAppConfig: (city, radiusKm) => set({ defaultCity: city, defaultRadiusKm: radiusKm }),
  locationCityName: null,
  setLocationCityName: (name) => set({ locationCityName: name }),
  syncTelegramUser: () => {
    const w = typeof window !== "undefined" ? window : null;
    const fromTg = w?.Telegram?.WebApp?.initDataUnsafe?.user;
    const debugId = w ? Number(new URLSearchParams(w.location.search).get("telegram_id")) : NaN;
    if (fromTg?.id) {
      set({ telegramUser: { id: fromTg.id, first_name: fromTg.first_name } });
    } else if (Number.isFinite(debugId) && debugId) {
      set({ telegramUser: { id: debugId, first_name: undefined } });
    }
  },
  backendReady: false,
  setBackendReady: (v) => set({ backendReady: v }),
}));

export type ServiceSelection = {
  id: number;
  name: string;
  price: number;
  duration_minutes: number;
};

export type SlotSelection = {
  start_time: string;
  end_time: string;
  is_available: boolean;
};

export const useBookingStore = create<{
  selectedCarwash: { id: number; name: string; address: string } | null;
  selectedDate: string | null;
  selectedSlot: SlotSelection | null;
  selectedService: ServiceSelection | null;
  currentBooking: any | null;
  setSelectedCarwash: (c: { id: number; name: string; address: string } | null) => void;
  setSelectedDate: (d: string | null) => void;
  setSelectedSlot: (s: SlotSelection | null) => void;
  setSelectedService: (s: ServiceSelection | null) => void;
  setCurrentBooking: (b: any | null) => void;
  reset: () => void;
}>((set) => ({
  selectedCarwash: null,
  selectedDate: null,
  selectedSlot: null,
  selectedService: null,
  currentBooking: null,
  setSelectedCarwash: (c) => set({ selectedCarwash: c }),
  setSelectedDate: (d) => set({ selectedDate: d }),
  setSelectedSlot: (s) => set({ selectedSlot: s }),
  setSelectedService: (s) => set({ selectedService: s }),
  setCurrentBooking: (b) => set({ currentBooking: b }),
  reset: () =>
    set({
      selectedCarwash: null,
      selectedDate: null,
      selectedSlot: null,
      selectedService: null,
      currentBooking: null,
    }),
}));

export type CarwashListItem = {
  id: number;
  name: string;
  address: string;
  distance?: number;
  rating?: number | null;
  nearest_slots?: Array<{ is_available: boolean }>;
};

export const useCarwashesStore = create<{
  carwashes: CarwashListItem[];
  isLoading: boolean;
  error: string | null;
  setCarwashes: (c: CarwashListItem[]) => void;
  setLoading: (v: boolean) => void;
  setError: (e: string | null) => void;
}>((set) => ({
  carwashes: [],
  isLoading: false,
  error: null,
  setCarwashes: (c) => set({ carwashes: c }),
  setLoading: (v) => set({ isLoading: v }),
  setError: (e) => set({ error: e }),
}));
