import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useBookingStore, useAppStore } from "../store";
import DateSelector from "../components/DateSelector";
import TimeSlots from "../components/TimeSlots";
import WashTypeSelector from "../components/WashTypeSelector";
import Loader from "../components/Loader";
import BackButton from "../components/BackButton";
import {
  getCarwash,
  getCarwashSlots,
  getServices,
} from "../api";
import type { CarWash, Service, Slot } from "../api";

export default function CarwashPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { haptic } = useAppStore();
  const {
    selectedDate,
    selectedSlot,
    selectedService,
    setSelectedCarwash,
    setSelectedDate,
    setSelectedSlot,
    setSelectedService,
  } = useBookingStore();

  const [carwash, setCarwash] = useState<CarWash | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const carwashId = id ? parseInt(id, 10) : NaN;

  useEffect(() => {
    if (isNaN(carwashId)) return;
    setLoading(true);
    setError(null);
    Promise.all([
      getCarwash(carwashId),
      getServices(carwashId),
    ])
      .then(([cw, svc]) => {
        setCarwash(cw);
        setServices(svc);
        setSelectedCarwash({
          id: cw.id,
          name: cw.name,
          address: cw.address,
        });
        if (svc.length > 0) {
          setSelectedService({
            id: svc[0].id,
            name: svc[0].name,
            price: svc[0].price,
            duration_minutes: svc[0].duration_minutes,
          });
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [carwashId]);

  useEffect(() => {
    if (!carwashId || !selectedDate || isNaN(carwashId)) return;
    getCarwashSlots(carwashId, selectedDate)
      .then(setSlots)
      .catch(() => setSlots([]));
    setSelectedSlot(null);
  }, [carwashId, selectedDate]);

  const handleContinue = () => {
    haptic("medium");
    navigate("/confirm");
  };

  const openTime =
    carwash?.open_time != null
      ? String(carwash.open_time).slice(0, 5)
      : "—";
  const closeTime =
    carwash?.close_time != null
      ? String(carwash.close_time).slice(0, 5)
      : "—";

  if (loading || !carwash) {
    return <Loader />;
  }

  if (error) {
    return (
      <div className="px-4 pt-4">
        <BackButton to="/" className="mb-4" />
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="px-4 pt-4 pb-24">
      <BackButton to="/" className="mb-4" />
      <div className="card mb-4">
        <h2 className="text-xl font-bold">{carwash.name}</h2>
        <p className="text-sm text-gray-500">{carwash.address}</p>
        <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
          {carwash.rating != null && (
            <span>⭐ {String(carwash.rating)}</span>
          )}
          <span>🕐 {openTime} - {closeTime}</span>
        </div>
      </div>

      <div className="mb-4">
        <h3 className="font-semibold mb-2">Тип мойки</h3>
        <WashTypeSelector
          services={services}
          selected={selectedService}
          onSelect={(s) => {
            haptic("light");
            setSelectedService({
              id: s.id,
              name: s.name,
              price: s.price,
              duration_minutes: s.duration_minutes,
            });
          }}
        />
      </div>

      <div className="mb-4">
        <h3 className="font-semibold mb-2">Дата</h3>
        <DateSelector
          selected={selectedDate}
          onSelect={(d) => {
            haptic("light");
            setSelectedDate(d);
            setSelectedSlot(null);
          }}
        />
      </div>

      {selectedDate && (
        <div className="mb-4 animate-in">
          <h3 className="font-semibold mb-2">Время</h3>
          <TimeSlots
            slots={slots}
            selected={selectedSlot}
            onSelect={(s) => {
              haptic("light");
              setSelectedSlot(s);
            }}
          />
        </div>
      )}

      {selectedService && selectedDate && selectedSlot && (
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t animate-in">
          <button type="button" onClick={handleContinue} className="btn-primary w-full min-h-[48px] cursor-pointer">
            Продолжить — {selectedService.price}₽
          </button>
        </div>
      )}
    </div>
  );
}
