import React from "react";

export default function Loader() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="w-10 h-10 border-4 border-wash-primary border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-500 mt-3">Загрузка...</p>
    </div>
  );
}
