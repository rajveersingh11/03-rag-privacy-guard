import { useState } from 'react';
import { AppProvider } from './components/AppContext';
import { AppShell } from './components/AppShell';
import { Dashboard } from './pages/Dashboard';
import { QueryConsole } from './pages/QueryConsole';
import { Ingestion } from './pages/Ingestion';
import { SecurityEvents } from './pages/SecurityEvents';
import { Settings } from './pages/Settings';

function AppContent() {
  const [activePage, setActivePage] = useState('dashboard');

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard setActivePage={setActivePage} />;
      case 'query':
        return <QueryConsole />;
      case 'ingest':
        return <Ingestion />;
      case 'events':
        return <SecurityEvents />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard setActivePage={setActivePage} />;
    }
  };

  return (
    <AppShell activePage={activePage} setActivePage={setActivePage}>
      {renderPage()}
    </AppShell>
  );
}

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
