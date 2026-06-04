import React from 'react';

interface LoadingStateProps {
  type?: 'spinner' | 'skeleton' | 'console';
  rows?: number;
  text?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  type = 'spinner',
  rows = 3,
  text = 'Processing secure transaction...',
}) => {
  if (type === 'spinner') {
    return (
      <div className="flex flex-col items-center justify-center py-10 space-y-4">
        <div className="relative w-12 h-12">
          {/* Inner ring */}
          <div className="absolute inset-0 rounded-full border-2 border-gray-800"></div>
          {/* Active indicator */}
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin"></div>
          {/* Glowing scanner line */}
          <div className="absolute inset-x-1 top-1/2 h-0.5 bg-blue-400 opacity-50 blur-[2px] animate-pulse"></div>
        </div>
        {text && <p className="text-gray-400 text-sm font-mono tracking-wider animate-pulse">{text}</p>}
      </div>
    );
  }

  if (type === 'console') {
    return (
      <div className="bg-[#0b0f19] border border-gray-800 rounded-xl p-5 font-mono text-xs text-blue-400 space-y-2">
        <div className="flex items-center space-x-2 animate-pulse">
          <span className="text-blue-500">▶</span>
          <span>INITIALIZING PRIVACY GATEWAY...</span>
        </div>
        <div className="text-gray-600">SHIELD STATUS: 6-LAYER RAG PRIVACY GUARD ACTIVE</div>
        <div className="text-gray-600">PARSING METADATA CHUNKS...</div>
        <div className="flex items-center space-x-2 text-emerald-500 animate-pulse delay-100">
          <span>✓</span>
          <span>PII SANITIZER MODULE ENABLED [200 OK]</span>
        </div>
        <div className="flex items-center space-x-2 text-purple-500 animate-pulse delay-300">
          <span>⚙</span>
          <span>COMPUTING DIFFERENTIAL PRIVACY VECTORS...</span>
        </div>
        <div className="w-full bg-gray-900 h-1.5 rounded-full overflow-hidden">
          <div className="bg-blue-500 h-full rounded-full animate-[loading-bar_2s_infinite_linear]" style={{ width: '60%' }}></div>
        </div>
      </div>
    );
  }

  // Skeleton rows
  return (
    <div className="space-y-4 w-full py-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-4 animate-pulse">
          <div className="rounded-full bg-gray-800 h-10 w-10"></div>
          <div className="flex-1 space-y-2 py-1">
            <div className="h-4 bg-gray-800 rounded w-3/4"></div>
            <div className="space-y-2">
              <div className="h-3 bg-gray-800 rounded"></div>
              <div className="h-3 bg-gray-800 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
