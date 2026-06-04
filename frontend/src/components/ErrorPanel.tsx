import React from 'react';
import { ShieldAlert, AlertTriangle, Cpu, HelpCircle } from 'lucide-react';
import type { ApiClientError } from '../api/client';

interface ErrorPanelProps {
  error: ApiClientError | string | null;
  onRetry?: () => void;
}

export const ErrorPanel: React.FC<ErrorPanelProps> = ({ error, onRetry }) => {
  if (!error) return null;

  // Convert string error to standard ApiClientError format
  const apiError: ApiClientError = typeof error === 'string' 
    ? { message: error, type: 'generic' } 
    : error;

  let title = 'Operation Failed';
  let message = apiError.message;
  let icon = <AlertTriangle className="w-8 h-8 text-rose-500" />;
  let suggestion = 'An unexpected error occurred. Please verify your inputs and try again.';

  if (apiError.type === 'unauthorized') {
    title = 'API Key Denied [401/403]';
    icon = <ShieldAlert className="w-8 h-8 text-rose-500" />;
    suggestion = 'Please navigate to Settings to verify your API Key and CORS configuration. Ensure the header matches X-API-Key.';
  } else if (apiError.type === 'rate_limit') {
    title = 'Rate Limit Exceeded [429]';
    icon = <AlertTriangle className="w-8 h-8 text-amber-500 animate-bounce" />;
    suggestion = 'The backend rate limiter is throttling requests (60 queries/min, 10 ingests/min). Please wait a few seconds before retrying.';
  } else if (apiError.type === 'unavailable') {
    title = 'Security Engine Offline [503]';
    icon = <Cpu className="w-8 h-8 text-rose-500" />;
    suggestion = 'The FastAPI service or one of its dependencies (ChromaDB, Redis, LLM API client) is currently unreachable. Make sure the server is running on http://127.0.0.1:8000.';
  } else if (apiError.type === 'validation') {
    title = 'Payload Validation Error [422]';
    icon = <HelpCircle className="w-8 h-8 text-cyan-500" />;
    suggestion = 'The request payload failed schema validation (e.g. invalid symbols in User/Tenant IDs or query text out of bounds).';
  }

  return (
    <div className="bg-[#0f0b11] border border-rose-900/40 rounded-xl p-5 glow-red flex flex-col md:flex-row items-start md:items-center space-y-4 md:space-y-0 md:space-x-5 my-4">
      <div className="bg-rose-950/30 p-3 rounded-lg border border-rose-800/40 shrink-0">
        {icon}
      </div>
      <div className="flex-1">
        <h4 className="text-sm font-semibold text-rose-400 font-mono tracking-wider uppercase">
          {title}
        </h4>
        <p className="text-xs text-gray-400 mt-1 font-mono break-all font-light leading-relaxed">
          {message}
        </p>
        <div className="mt-2 text-[10px] text-gray-500 border-t border-gray-900 pt-2 font-sans">
          <span className="font-semibold text-gray-400">RECOMMENDATION:</span> {suggestion}
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3.5 py-1.5 bg-rose-950/60 hover:bg-rose-900/50 text-rose-300 border border-rose-800/60 hover:border-rose-700 rounded-lg text-xs font-mono font-medium transition-all duration-200"
        >
          RETRY
        </button>
      )}
    </div>
  );
};
