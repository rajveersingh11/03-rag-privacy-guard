import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { SecurityEvent, HealthCheckResponse } from '../types';
import { apiClient } from '../api/client';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface AppContextType {
  // Settings
  baseUrl: string;
  apiKey: string;
  saveSettings: (baseUrl: string, apiKey: string) => void;
  clearSettings: () => void;
  
  // Toasts
  toasts: Toast[];
  showToast: (message: string, type: ToastType) => void;
  removeToast: (id: string) => void;

  // Local Security Audit Events
  events: SecurityEvent[];
  addEvent: (event: Omit<SecurityEvent, 'id' | 'time'>) => void;
  clearEvents: () => void;

  // System Health
  health: HealthCheckResponse | null;
  loadingHealth: boolean;
  healthError: string | null;
  refreshHealth: () => Promise<HealthCheckResponse | null>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 1. Settings state
  const [baseUrl, setBaseUrl] = useState(() => {
    return localStorage.getItem('ae_base_url') || 'http://127.0.0.1:8000';
  });
  const [apiKey, setApiKey] = useState(() => {
    return localStorage.getItem('ae_api_key') || '';
  });

  const saveSettings = (newUrl: string, newKey: string) => {
    localStorage.setItem('ae_base_url', newUrl);
    localStorage.setItem('ae_api_key', newKey);
    setBaseUrl(newUrl);
    setApiKey(newKey);
    showToast('Settings saved successfully', 'success');
  };

  const clearSettings = () => {
    localStorage.removeItem('ae_base_url');
    localStorage.removeItem('ae_api_key');
    setBaseUrl('http://127.0.0.1:8000');
    setApiKey('');
    showToast('Settings cleared', 'info');
  };

  // 2. Toasts state
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
      removeToast(id);
    }, 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // 3. Events state (local persistence)
  const [events, setEvents] = useState<SecurityEvent[]>(() => {
    const saved = localStorage.getItem('ae_events');
    return saved ? JSON.parse(saved) : [];
  });

  const addEvent = useCallback((eventData: Omit<SecurityEvent, 'id' | 'time'>) => {
    const newEvent: SecurityEvent = {
      ...eventData,
      id: `evt-${Math.random().toString(36).substring(2, 9)}`,
      time: new Date().toISOString(),
    };
    
    setEvents((prev) => {
      const updated = [newEvent, ...prev].slice(0, 100); // limit to last 100 events
      localStorage.setItem('ae_events', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const clearEvents = () => {
    localStorage.removeItem('ae_events');
    setEvents([]);
    showToast('Audit log events cleared', 'info');
  };

  // 4. System Health state
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  const refreshHealth = useCallback(async () => {
    setLoadingHealth(true);
    setHealthError(null);
    try {
      const data = await apiClient.getHealth();
      setHealth(data);
      setLoadingHealth(false);
      return data;
    } catch (err: any) {
      console.error('Health check failed:', err);
      setHealth(null);
      setHealthError(err.message || 'Failed to connect to backend.');
      setLoadingHealth(false);
      return null;
    }
  }, []);

  // Run initial health check on load, and set up polling every 30 seconds
  useEffect(() => {
    refreshHealth();
    const interval = setInterval(() => {
      refreshHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshHealth, baseUrl, apiKey]); // run again if settings change

  return (
    <AppContext.Provider
      value={{
        baseUrl,
        apiKey,
        saveSettings,
        clearSettings,
        toasts,
        showToast,
        removeToast,
        events,
        addEvent,
        clearEvents,
        health,
        loadingHealth,
        healthError,
        refreshHealth,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
