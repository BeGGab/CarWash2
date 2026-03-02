import React, { useState } from "react";
import type { LocationCoords } from "../store";

export default function LocationButton({
  location,
  onLocationUpdate,
  locationLabel,
}: {
  location: LocationCoords | null;
  onLocationUpdate: (loc: LocationCoords) => void;
  locationLabel?: string;
}) {
  const [isLoading, setIsLoading] = useState(false);

  const requestLocation = () => {
    setIsLoading(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          onLocationUpdate({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
          setIsLoading(false);
        },
        () => {
          setIsLoading(false);
          onLocationUpdate({ latitude: 55.7558, longitude: 37.6173 });
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      setIsLoading(false);
      onLocationUpdate({ latitude: 55.7558, longitude: 37.6173 });
    }
  };

  return (
    <button
      type="button"
      onClick={requestLocation}
      disabled={isLoading}
      className={`w-full mb-4 py-3 px-4 rounded-xl flex items-center justify-center gap-2 font-medium transition-all min-h-[48px] ${
        location
          ? "bg-green-50 text-green-700 border border-green-200"
          : "bg-wash-primary text-white"
      }`}
    >
      {isLoading ? (
        <>
          <span className="animate-spin">⏳</span>
          <span>Определение...</span>
        </>
      ) : location ? (
        <>
          <span>📍</span>
          <span>{locationLabel ?? "Геолокация получена"}</span>
        </>
      ) : (
        <>
          <span>📍</span>
          <span>Отправить местоположение</span>
        </>
      )}
    </button>
  );
}
