import React from 'react';
import { CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react';

interface ConfidenceBadgeProps {
  confidence: number;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

const getConfidenceConfig = (confidence: number) => {
  if (confidence >= 0.75) {
    return {
      label: 'High',
      fullLabel: 'High Confidence',
      icon: CheckCircle2,
      bgClass: 'bg-emerald-50',
      borderClass: 'border-emerald-200',
      textClass: 'text-emerald-700',
      iconClass: 'text-emerald-500',
      barClass: 'bg-emerald-500',
    };
  }
  if (confidence >= 0.55) {
    return {
      label: 'Medium',
      fullLabel: 'Medium Confidence',
      icon: AlertCircle,
      bgClass: 'bg-amber-50',
      borderClass: 'border-amber-200',
      textClass: 'text-amber-700',
      iconClass: 'text-amber-500',
      barClass: 'bg-amber-500',
    };
  }
  return {
    label: 'Low',
    fullLabel: 'Low Confidence',
    icon: HelpCircle,
    bgClass: 'bg-red-50',
    borderClass: 'border-red-200',
    textClass: 'text-red-600',
    iconClass: 'text-red-500',
    barClass: 'bg-red-500',
  };
};

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  showLabel = true,
  size = 'sm',
}) => {
  const config = getConfidenceConfig(confidence);
  const Icon = config.icon;
  const percent = Math.round(confidence * 100);

  const sizeClasses = {
    sm: 'px-2 py-1 text-[10px]',
    md: 'px-2.5 py-1.5 text-xs',
  };

  return (
    <div
      className={`
        inline-flex items-center gap-1.5 rounded-full border font-semibold
        ${config.bgClass} ${config.borderClass} ${config.textClass}
        ${sizeClasses[size]}
      `}
    >
      <Icon size={size === 'sm' ? 12 : 14} className={config.iconClass} />
      {showLabel && <span>{config.label}</span>}
      <span className="opacity-75">({percent}%)</span>
    </div>
  );
};

// Compact inline confidence indicator
export const ConfidenceIndicator: React.FC<{ confidence: number }> = ({ confidence }) => {
  const config = getConfidenceConfig(confidence);
  const percent = Math.round(confidence * 100);

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${config.barClass}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className={`text-[10px] font-semibold ${config.textClass}`}>
        {percent}%
      </span>
    </div>
  );
};

export default ConfidenceBadge;
