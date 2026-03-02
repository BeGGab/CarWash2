import React from "react";
import { useNavigate } from "react-router-dom";

type BackButtonProps = {
  onClick?: () => void;
  to?: string;
  className?: string;
};

export default function BackButton({ onClick, to, className = "" }: BackButtonProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (to) {
      navigate(to);
    } else {
      navigate(-1);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`btn-back inline-flex items-center gap-2 font-medium ${className}`}
    >
      <span aria-hidden>←</span>
      <span>Назад</span>
    </button>
  );
}
