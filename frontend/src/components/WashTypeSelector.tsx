import React from "react";

type Service = {
  id: number;
  name: string;
  price: number;
  duration_minutes: number;
};

export default function WashTypeSelector({
  services,
  selected,
  onSelect,
}: {
  services: Service[];
  selected: Service | null;
  onSelect: (s: Service) => void;
}) {
  return (
    <div className="space-y-2">
      {services.map((s) => {
        const isSelected = selected?.id === s.id;
        return (
          <button
            key={s.id}
            onClick={() => onSelect(s)}
            className={`w-full p-3 rounded-xl text-left transition-all flex justify-between items-center ${
              isSelected
                ? "bg-wash-primary text-white"
                : "bg-white border border-gray-200"
            }`}
          >
            <div>
              <div className="font-medium">{s.name}</div>
              <div
                className={`text-xs ${
                  isSelected ? "text-white/75" : "text-gray-500"
                }`}
              >
                🕐 {s.duration_minutes} мин
              </div>
            </div>
            <div className="font-semibold">{s.price}₽</div>
          </button>
        );
      })}
    </div>
  );
}
