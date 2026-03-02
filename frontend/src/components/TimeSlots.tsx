import React from "react";

type Slot = {
  start_time: string;
  end_time: string;
  is_available: boolean;
};

export default function TimeSlots({
  slots,
  selected,
  onSelect,
}: {
  slots: Slot[];
  selected: Slot | null;
  onSelect: (s: Slot) => void;
}) {
  const available = slots.filter((s) => s.is_available);

  if (!available.length) {
    return (
      <p className="text-sm text-gray-500 text-center py-4">
        Нет доступных слотов
      </p>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {available.map((slot) => {
        const isSelected =
          selected?.start_time === slot.start_time &&
          selected?.end_time === slot.end_time;
        return (
          <button
            key={`${slot.start_time}-${slot.end_time}`}
            onClick={() => onSelect(slot)}
            className={`slot-btn ${isSelected ? "selected" : ""}`}
          >
            {slot.start_time}
          </button>
        );
      })}
    </div>
  );
}
