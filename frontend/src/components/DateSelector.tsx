import React from "react";
import { format, addDays } from "date-fns";
import { ru } from "date-fns/locale";

export default function DateSelector({
  selected,
  onSelect,
  daysAhead = 14,
}: {
  selected: string | null;
  onSelect: (d: string) => void;
  daysAhead?: number;
}) {
  const today = new Date();
  const dates = Array.from({ length: daysAhead }, (_, i) => addDays(today, i));

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
      {dates.map((date, idx) => {
        const dateStr = format(date, "yyyy-MM-dd");
        const isSelected = selected === dateStr;
        const dayName =
          idx === 0 ? "Сегодня" : idx === 1 ? "Завтра" : format(date, "EE", { locale: ru });
        const dayNum = format(date, "d");

        return (
          <button
            key={date.toISOString()}
            onClick={() => onSelect(dateStr)}
            className={`flex-shrink-0 w-16 py-3 rounded-xl text-center transition-all ${
              isSelected
                ? "bg-wash-primary text-white"
                : "bg-white border border-gray-200 text-gray-700"
            }`}
          >
            <div className="text-xs opacity-75">{dayName}</div>
            <div className="text-lg font-semibold">{dayNum}</div>
          </button>
        );
      })}
    </div>
  );
}
