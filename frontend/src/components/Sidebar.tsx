import React from 'react';
import {
  LayoutDashboard,
  Terminal,
  Database,
  ShieldAlert,
  Settings,
  Shield,
  X
} from 'lucide-react';
import { useApp } from './AppContext';

interface SidebarProps {
  activePage: string;
  setActivePage: (page: string) => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activePage,
  setActivePage,
  isOpen,
  setIsOpen,
}) => {
  const { health, loadingHealth } = useApp();

  const menuItems = [
    { id: 'dashboard', name: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'query', name: 'Query Console', icon: <Terminal className="w-5 h-5" /> },
    { id: 'ingest', name: 'Data Ingestion', icon: <Database className="w-5 h-5" /> },
    { id: 'events', name: 'Security Audits', icon: <ShieldAlert className="w-5 h-5" /> },
    { id: 'settings', name: 'System Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  const handleNav = (pageId: string) => {
    setActivePage(pageId);
    // On mobile, close drawer upon navigation
    setIsOpen(false);
  };

  const isConnected = !!health;

  return (
    <>
      {/* Mobile Drawer Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex flex-col w-64 bg-[#070b13] border-r border-gray-900 transition-transform duration-300 md:translate-x-0 md:static md:h-screen ${
          isOpen ? 'translate-x-0' : '-translate-x-0 -left-64 md:left-0'
        }`}
      >
        {/* Brand header */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-900">
          <div className="flex items-center space-x-2.5">
            <div className="bg-blue-950/80 p-2 rounded-lg border border-blue-500/30 glow-blue">
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <span className="font-mono text-sm font-bold text-gray-100 tracking-wider">AEGISVAULT</span>
              <span className="block text-[8px] font-mono text-gray-500 tracking-widest uppercase">Privacy Guard</span>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 text-gray-400 hover:text-gray-200 md:hidden border border-gray-800 rounded-md hover:bg-gray-900"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {menuItems.map((item) => {
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNav(item.id)}
                className={`flex items-center w-full px-4 py-3 rounded-lg text-sm font-mono transition-all duration-200 group ${
                  isActive
                    ? 'bg-[#121826] text-blue-400 border-l-2 border-blue-500 shadow-md font-medium'
                    : 'text-gray-400 hover:bg-gray-900/60 hover:text-gray-200 border-l-2 border-transparent'
                }`}
              >
                <span className={`mr-3.5 transition-colors ${isActive ? 'text-blue-400' : 'text-gray-500 group-hover:text-gray-300'}`}>
                  {item.icon}
                </span>
                {item.name}
              </button>
            );
          })}
        </nav>

        {/* Connection status footer */}
        <div className="p-4 border-t border-gray-900 bg-[#05080f]/40 font-mono text-[10px] space-y-2">
          <div className="flex items-center justify-between text-gray-500">
            <span>ENGINE STATUS:</span>
            <div className="flex items-center space-x-1.5">
              <span className={`w-2 h-2 rounded-full ${
                loadingHealth 
                  ? 'bg-blue-500 animate-ping'
                  : isConnected 
                  ? 'bg-emerald-500' 
                  : 'bg-rose-500'
              }`} />
              <span className={`text-[10px] font-semibold tracking-wider ${
                isConnected ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {loadingHealth ? 'PROBING...' : isConnected ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>
          </div>
          {health && (
            <div className="flex justify-between text-[9px] text-gray-500 border-t border-gray-900/60 pt-2 font-mono">
              <span>VERSION: {health.version}</span>
              <span>RAG CACHE: {health.checks.vectorstore.doc_count ?? 0} Docs</span>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
