import React from 'react';
import { Menu, RefreshCw, Server, ShieldCheck } from 'lucide-react';
import { useApp } from './AppContext';

interface TopBarProps {
  activePage: string;
  onMenuToggle: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ activePage, onMenuToggle }) => {
  const { baseUrl, refreshHealth, loadingHealth, health } = useApp();

  const getPageTitle = (id: string) => {
    switch (id) {
      case 'dashboard':
        return 'Security Operations Command';
      case 'query':
        return 'Guarded Query Console';
      case 'ingest':
        return 'Secure Ingestion Pipeline';
      case 'events':
        return 'Real-Time Audit Trails';
      case 'settings':
        return 'Gateway Configurations';
      default:
        return 'AegisVault Console';
    }
  };

  const handleRefresh = async () => {
    const res = await refreshHealth();
    if (res) {
      // toast is handled in context or page
    }
  };

  return (
    <header className="flex items-center justify-between h-16 px-6 bg-[#070b13] border-b border-gray-900 sticky top-0 z-30">
      <div className="flex items-center space-x-3.5">
        <button
          onClick={onMenuToggle}
          className="p-1.5 text-gray-400 hover:text-gray-200 border border-gray-800 rounded-lg hover:bg-gray-900 md:hidden transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-base font-semibold text-gray-100 font-mono tracking-wide uppercase m-0">
            {getPageTitle(activePage)}
          </h1>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* API Endpoint Indicator */}
        <div className="hidden lg:flex items-center space-x-2 text-[10px] font-mono bg-gray-900/60 border border-gray-800/80 px-3 py-1.5 rounded-lg text-gray-400">
          <Server className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-gray-500">GATEWAY:</span>
          <span className="text-gray-300 tracking-tight">{baseUrl}</span>
        </div>

        {/* Health status badge */}
        <div className="hidden sm:flex items-center space-x-2 text-[10px] font-mono bg-gray-900/60 border border-gray-800/80 px-3 py-1.5 rounded-lg text-gray-400">
          <ShieldCheck className={`w-3.5 h-3.5 ${health ? 'text-emerald-500' : 'text-rose-500'}`} />
          <span className="text-gray-500">SHIELDS:</span>
          <span className={health ? 'text-emerald-400' : 'text-rose-400'}>
            {health ? '6-LAYER ACTIVE' : 'BYPASS ACTIVE'}
          </span>
        </div>

        {/* Refresh health button */}
        <button
          onClick={handleRefresh}
          disabled={loadingHealth}
          className={`p-2 text-gray-400 hover:text-gray-200 border border-gray-800 rounded-lg hover:bg-gray-900 transition-colors disabled:opacity-50 ${
            loadingHealth ? 'animate-pulse' : ''
          }`}
          title="Force System Health Diagnostics"
        >
          <RefreshCw className={`w-4 h-4 ${loadingHealth ? 'animate-spin text-blue-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
