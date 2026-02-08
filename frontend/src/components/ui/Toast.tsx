import React, { useEffect, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

type ToastVariant = 'success' | 'error' | 'info' | 'warning';

interface ToastProps {
  message: string;
  variant?: ToastVariant;
  duration?: number;
  onClose: () => void;
}

const variantConfig: Record<ToastVariant, {
  icon: React.FC<{ size?: number; className?: string }>;
  bg: string;
  border: string;
  text: string;
  iconColor: string;
}> = {
  success: {
    icon: CheckCircle2,
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    text: 'text-emerald-800',
    iconColor: 'text-emerald-500',
  },
  error: {
    icon: AlertCircle,
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-800',
    iconColor: 'text-red-500',
  },
  info: {
    icon: Info,
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-800',
    iconColor: 'text-blue-500',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-800',
    iconColor: 'text-amber-500',
  },
};

export const Toast: React.FC<ToastProps> = ({
  message,
  variant = 'info',
  duration = 4000,
  onClose,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const config = variantConfig[variant];
  const Icon = config.icon;

  const handleClose = useCallback(() => {
    setIsVisible(false);
    setTimeout(onClose, 200);
  }, [onClose]);

  useEffect(() => {
    requestAnimationFrame(() => setIsVisible(true));
    const timer = setTimeout(handleClose, duration);
    return () => clearTimeout(timer);
  }, [duration, handleClose]);

  return (
    <div
      role="alert"
      className={`
        fixed bottom-6 right-6 z-[500] max-w-sm
        flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg
        transition-all duration-200
        ${config.bg} ${config.border}
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
      `}
    >
      <Icon size={18} className={`${config.iconColor} shrink-0`} />
      <p className={`text-sm font-medium flex-1 ${config.text}`}>{message}</p>
      <button
        onClick={handleClose}
        aria-label="Dismiss notification"
        className="p-1 rounded-lg hover:bg-black/5 transition-colors shrink-0"
      >
        <X size={14} className="text-slate-400" />
      </button>
    </div>
  );
};

export default Toast;
