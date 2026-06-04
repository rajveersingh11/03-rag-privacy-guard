import React from 'react';

interface StatusBadgeProps {
  status: string;
  type?: 'health' | 'risk' | 'sensitivity' | 'event' | 'generic';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'generic' }) => {
  const normStatus = status.toLowerCase().trim();

  // Determine theme styling classes
  let classes = 'bg-gray-800 text-gray-300 border-gray-700';

  if (type === 'health') {
    if (normStatus === 'ok' || normStatus === 'configured') {
      classes = 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30';
    } else if (normStatus === 'degraded' || normStatus === 'warning') {
      classes = 'bg-amber-950/40 text-amber-400 border-amber-500/30';
    } else if (normStatus === 'unavailable' || normStatus === 'error' || normStatus === 'unconfigured') {
      classes = 'bg-rose-950/40 text-rose-400 border-rose-500/30';
    }
  } else if (type === 'risk') {
    if (normStatus === 'low') {
      classes = 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30';
    } else if (normStatus === 'medium') {
      classes = 'bg-blue-950/40 text-blue-400 border-blue-500/30';
    } else if (normStatus === 'high') {
      classes = 'bg-amber-950/40 text-amber-400 border-amber-500/30';
    } else if (normStatus === 'critical') {
      classes = 'bg-rose-950/60 text-rose-300 border-rose-500 font-semibold animate-pulse';
    }
  } else if (type === 'sensitivity') {
    if (normStatus === 'public') {
      classes = 'bg-emerald-950/30 text-emerald-400 border-emerald-500/20';
    } else if (normStatus === 'internal') {
      classes = 'bg-blue-950/30 text-blue-400 border-blue-500/20';
    } else if (normStatus === 'restricted') {
      classes = 'bg-amber-950/30 text-amber-400 border-amber-500/20';
    } else if (normStatus === 'confidential') {
      classes = 'bg-orange-950/40 text-orange-400 border-orange-500/30';
    } else if (normStatus === 'secret' || normStatus === 'top secret') {
      classes = 'bg-rose-950/40 text-rose-400 border-rose-500/30 font-semibold';
    }
  } else if (type === 'event') {
    if (normStatus === 'query') {
      classes = 'bg-purple-950/40 text-purple-400 border-purple-500/30';
    } else if (normStatus === 'file_ingest') {
      classes = 'bg-teal-950/40 text-teal-400 border-teal-500/30';
    } else if (normStatus === 'text_ingest') {
      classes = 'bg-indigo-950/40 text-indigo-400 border-indigo-500/30';
    }
  } else {
    // Generic
    if (['success', 'ingested', 'ok'].includes(normStatus)) {
      classes = 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30';
    } else if (['pending', 'queued', 'processing'].includes(normStatus)) {
      classes = 'bg-blue-950/40 text-blue-400 border-blue-500/30';
    } else if (['blocked', 'quarantined', 'failed', 'rejected'].includes(normStatus)) {
      classes = 'bg-rose-950/40 text-rose-400 border-rose-500/30';
    }
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono border uppercase tracking-wider ${classes}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current inline-block" />
      {status}
    </span>
  );
};
