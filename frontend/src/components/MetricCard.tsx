import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  subtext?: string;
  trend?: {
    value: string;
    type: 'positive' | 'negative' | 'neutral';
  };
  status?: 'ok' | 'warning' | 'error' | 'info';
  loading?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon,
  subtext,
  trend,
  status = 'info',
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="bg-[#0b0f19] border border-gray-800 rounded-xl p-5 animate-pulse">
        <div className="flex justify-between items-start mb-4">
          <div className="h-4 bg-gray-800 rounded w-1/3"></div>
          <div className="h-8 bg-gray-800 rounded-full w-8"></div>
        </div>
        <div className="h-8 bg-gray-800 rounded w-1/2 mb-2"></div>
        <div className="h-3 bg-gray-800 rounded w-2/3"></div>
      </div>
    );
  }

  // Border and glow mapping
  let borderClass = 'border-gray-800 hover:border-gray-700';
  let glowClass = '';

  if (status === 'ok') {
    borderClass = 'border-emerald-950/60 hover:border-emerald-500/40';
    glowClass = 'hover:shadow-[0_0_15px_rgba(16,185,129,0.08)]';
  } else if (status === 'warning') {
    borderClass = 'border-amber-950/60 hover:border-amber-500/40';
    glowClass = 'hover:shadow-[0_0_15px_rgba(245,158,11,0.08)]';
  } else if (status === 'error') {
    borderClass = 'border-rose-950/60 hover:border-rose-500/40';
    glowClass = 'hover:shadow-[0_0_15px_rgba(239,68,68,0.08)]';
  }

  return (
    <div className={`bg-[#0b0f19] border rounded-xl p-5 transition-all duration-300 ${borderClass} ${glowClass}`}>
      <div className="flex justify-between items-start mb-2">
        <span className="text-gray-400 text-sm font-medium tracking-wide uppercase">{title}</span>
        {icon && <div className="text-gray-500 bg-[#121826] p-2 rounded-lg border border-gray-800/60">{icon}</div>}
      </div>
      <div className="flex items-baseline space-x-2">
        <span className="text-2xl font-semibold text-gray-100 font-mono tracking-tight">{value}</span>
        {trend && (
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              trend.type === 'positive'
                ? 'bg-emerald-950/40 text-emerald-400'
                : trend.type === 'negative'
                ? 'bg-rose-950/40 text-rose-400'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            {trend.value}
          </span>
        )}
      </div>
      {subtext && <p className="text-xs text-gray-500 mt-2 font-light">{subtext}</p>}
    </div>
  );
};
