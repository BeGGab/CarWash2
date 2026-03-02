import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useAppStore } from "./store";
import { getAppConfig, setBackendUrl } from "./api";
import HomePage from "./pages/HomePage";
import CarwashPage from "./pages/CarwashPage";
import ConfirmPage from "./pages/ConfirmPage";
import MyBookingsPage from "./pages/MyBookingsPage";
import BookingDetailPage from "./pages/BookingDetailPage";
import PaymentSuccessPage from "./pages/PaymentSuccessPage";

export const App: React.FC = () => {
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    tg?.ready?.();
    const syncUser = () => useAppStore.getState().syncTelegramUser();
    syncUser();
    const t = setTimeout(syncUser, 300);
    const t2 = setTimeout(syncUser, 1000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") syncUser();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearTimeout(t);
      clearTimeout(t2);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  useEffect(() => {
    const loadConfigAndApp = async () => {
      try {
        const configRes = await fetch("/config.json");
        if (configRes.ok) {
          const cfg = await configRes.json();
          if (cfg?.backendUrl && typeof cfg.backendUrl === "string") {
            setBackendUrl(cfg.backendUrl.trim());
          }
        }
      } catch {
        // config.json не обязателен
      }
      try {
        const { defaultCity, defaultRadiusKm } = await getAppConfig();
        useAppStore.getState().setAppConfig(defaultCity, defaultRadiusKm);
      } finally {
        useAppStore.getState().setBackendReady(true);
      }
    };
    loadConfigAndApp();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/carwash/:id" element={<CarwashPage />} />
        <Route path="/confirm" element={<ConfirmPage />} />
        <Route path="/my-bookings" element={<MyBookingsPage />} />
        <Route path="/booking/:id" element={<BookingDetailPage />} />
        <Route path="/payment-success" element={<PaymentSuccessPage />} />
      </Routes>
    </BrowserRouter>
  );
};
