import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useApp } from './AppContext';
import { X, CheckCircle2, XCircle, AlertTriangle, Info } from 'lucide-react';

interface AppShellProps {
  activePage: string;
  setActivePage: (page: string) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  activePage,
  setActivePage,
  children,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { toasts, removeToast } = useApp();

  const getToastIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'info':
      default:
        return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  const getToastClasses = (type: string) => {
    switch (type) {
      case 'success':
        return 'border-emerald-500/20 bg-emerald-950/20 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.06)]';
      case 'error':
        return 'border-rose-500/20 bg-rose-950/20 text-rose-300 shadow-[0_0_10px_rgba(239,68,68,0.06)]';
      case 'warning':
        return 'border-amber-500/20 bg-amber-950/20 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.06)]';
      case 'info':
      default:
        return 'border-blue-500/20 bg-blue-950/20 text-blue-300 shadow-[0_0_10px_rgba(59,130,246,0.06)]';
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#030712] text-gray-100 font-sans">
      {/* Sidebar navigation */}
      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
        isOpen={sidebarOpen}
        setIsOpen={setSidebarOpen}
      />

      {/* Main content pane */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Header bar */}
        <TopBar
          activePage={activePage}
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
        />

        {/* Scrollable page body */}
        <main className="flex-1 overflow-y-auto bg-[#040814] p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>

      {/* Toast Notification Deck */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col space-y-2.5 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-start p-3.5 border rounded-xl pointer-events-auto backdrop-blur-md transition-all duration-300 animate-[slide-in_0.2s_ease-out] ${getToastClasses(
              toast.type
            )}`}
          >
            <div className="shrink-0 mt-0.5 mr-3">{getToastIcon(toast.type)}</div>
            <div className="flex-1 text-xs font-mono tracking-tight leading-relaxed">
              {toast.message}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 ml-3.5 text-gray-500 hover:text-gray-300 p-0.5 rounded transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
