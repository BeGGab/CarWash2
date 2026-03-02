import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore, useCarwashesStore, useBookingStore } from "../store";
import CarwashCard from "../components/CarwashCard";
import Loader from "../components/Loader";
import LocationButton from "../components/LocationButton";
import { getNearbyCarwashes, getCityNameFromCoords } from "../api";

const MOSCOW_FALLBACK = { latitude: 55.7558, longitude: 37.6173 };

export default function HomePage() {
  const navigate = useNavigate();
  const { location, setLocation, haptic, defaultCity, defaultRadiusKm, setLocationCityName, locationCityName, backendReady } = useAppStore();
  const {
    carwashes,
    setCarwashes,
    isLoading,
    setLoading,
    setError,
    error,
  } = useCarwashesStore();
  const { reset: resetBooking } = useBookingStore();
  const autoRequestDone = useRef(false);

  const fallbackLocation = defaultCity
    ? { latitude: defaultCity.lat, longitude: defaultCity.lon }
    : MOSCOW_FALLBACK;
  const fallbackButtonLabel = defaultCity
    ? `Показать моики в ${defaultCity.name}`
    : "Показать моики рядом с Москвой";
  const locationLabel = locationCityName
    ? `Геолокация: ${locationCityName}`
    : "Геолокация получена";

  useEffect(() => {
    resetBooking();
  }, [resetBooking]);

  useEffect(() => {
    if (!location) {
      setCarwashes([]);
      setLoading(false);
      return;
    }
    if (!backendReady) {
      setLoading(true);
      return;
    }
    setLoading(true);
    setError(null);
    getNearbyCarwashes(location.latitude, location.longitude, defaultRadiusKm)
      .then((data) => setCarwashes(data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [location, backendReady, setCarwashes, setLoading, setError, defaultRadiusKm]);

  useEffect(() => {
    if (!location) {
      setLocationCityName(null);
      return;
    }
    getCityNameFromCoords(location.latitude, location.longitude).then(setLocationCityName);
  }, [location, setLocationCityName]);

  useEffect(() => {
    if (location) return;
    if (!navigator.geolocation) {
      setLocation(fallbackLocation);
      return;
    }
    if (autoRequestDone.current) return;
    autoRequestDone.current = true;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
      },
      () => {
        setLocation(fallbackLocation);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }, [location, setLocation, fallbackLocation]);

  return (
    <div className="px-4 pt-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🚗 CarWash</h1>
          <p className="text-sm text-gray-500">Бронирование без очередей</p>
        </div>
        <button
          onClick={() => {
            haptic("light");
            navigate("/my-bookings");
          }}
          className="w-10 h-10 bg-white rounded-full shadow-sm flex items-center justify-center"
        >
          <span>📋</span>
        </button>
      </div>

      <LocationButton
        location={location}
        onLocationUpdate={setLocation}
        locationLabel={location ? locationLabel : undefined}
      />

      {!location && (
        <div className="space-y-3 pb-4">
          <p className="text-sm text-gray-500 text-center">
            Определяем местоположение…
          </p>
          <button
            type="button"
            onClick={() => setLocation(fallbackLocation)}
            className="w-full py-2 text-sm text-gray-600 border border-gray-200 rounded-xl"
          >
            {fallbackButtonLabel}
          </button>
        </div>
      )}

      {location && isLoading && <Loader />}

      {location && !isLoading && error && (
        <p className="text-red-600 text-sm text-center py-4">{error}</p>
      )}

      {location && !isLoading && !error && (
        <div className="space-y-3 pb-8">
          {carwashes.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              Моек рядом не найдено
            </p>
          ) : (
            carwashes.map((cw) => (
              <CarwashCard
                key={cw.id}
                carwash={cw}
                onClick={() => {
                  haptic("light");
                  navigate(`/carwash/${cw.id}`);
                }}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
