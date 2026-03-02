import React from "react";

type Carwash = {
  id: number;
  name: string;
  address: string;
  distance?: number;
  rating?: number | null;
  nearest_slots?: Array<{ is_available: boolean }>;
};

export default function CarwashCard({
  carwash,
  onClick,
}: {
  carwash: Carwash;
  onClick: () => void;
}) {
  const availableCount =
    carwash.nearest_slots?.filter((s) => s.is_available).length ?? 0;

  return (
    <div
      onClick={onClick}
      className="card card-hover cursor-pointer animate-in"
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900">{carwash.name}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{carwash.address}</p>
          <div className="flex items-center gap-3 mt-3">
            {carwash.distance != null && (
              <span className="text-xs text-gray-500 flex items-center gap-1">
                📍 {carwash.distance.toFixed(1)} км
              </span>
            )}
            {carwash.rating != null && (
              <span className="text-xs text-gray-500 flex items-center gap-1">
                ⭐ {String(carwash.rating)}
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          {availableCount > 0 ? (
            <span className="badge badge-success">
              ✓ {availableCount} слотов
            </span>
          ) : (
            <span className="badge badge-error">Нет мест</span>
          )}
        </div>
      </div>
    </div>
  );
}
