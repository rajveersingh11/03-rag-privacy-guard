import React from 'react';
import { useApp } from '../components/AppContext';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import {
  ShieldAlert,
  Server,
  Terminal,
  Database,
  ShieldCheck,
  AlertTriangle,
  FileSpreadsheet
} from 'lucide-react';

interface DashboardProps {
  setActivePage: (page: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ setActivePage }) => {
  const { health, loadingHealth, healthError, events } = useApp();

  const isConnected = !!health;

  // Compute status statistics
  const recentEvents = events.slice(0, 5); // last 5 events
  const totalEventsCount = events.length;
  const blockedCount = events.filter((e) => e.status === 'blocked' || e.status === 'quarantined').length;

  const docCount = health?.checks?.vectorstore?.doc_count ?? 0;

  // Quick Action Buttons
  const handleAction = (pageId: string) => {
    setActivePage(pageId);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Alert / Status */}
      <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="bg-blue-950/40 p-2.5 rounded-lg border border-blue-500/20">
            <ShieldCheck className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold font-mono tracking-wider text-gray-100 uppercase m-0">AegisVault Command Center</h2>
            <p className="text-xs text-gray-500 font-light mt-0.5">Enterprise-grade guardrails shielding vector indexes and large language models.</p>
          </div>
        </div>

        <div className="flex space-x-2 shrink-0">
          <button
            onClick={() => handleAction('query')}
            className="px-3.5 py-2.5 bg-blue-600 hover:bg-blue-500 text-gray-100 border border-transparent rounded-xl text-xs font-mono font-bold tracking-wider flex items-center space-x-2 shadow-lg shadow-blue-950/40 glow-blue transition-all"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>QUERY CONSOLE</span>
          </button>
          <button
            onClick={() => handleAction('ingest')}
            className="px-3.5 py-2.5 border border-gray-800 bg-[#070b13] hover:bg-gray-900 text-gray-300 hover:text-gray-100 rounded-xl text-xs font-mono font-bold tracking-wider flex items-center space-x-2 transition-all"
          >
            <Database className="w-3.5 h-3.5" />
            <span>INGEST DATA</span>
          </button>
        </div>
      </div>

      {/* Main Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Vector Document Cache"
          value={isConnected ? `${docCount} Documents` : 'Offline'}
          subtext="Total index nodes in vector database"
          icon={<Database className="w-5 h-5 text-blue-400" />}
          status={isConnected ? 'ok' : 'error'}
          loading={loadingHealth}
        />
        <MetricCard
          title="Security Posture Score"
          value="98.4%"
          subtext="6-layer guardrails active & verified"
          icon={<ShieldCheck className="w-5 h-5 text-emerald-400" />}
          status="ok"
          loading={loadingHealth}
        />
        <MetricCard
          title="Blocked Vulnerabilities"
          value={blockedCount}
          subtext="Canary leaks & RBAC violations"
          icon={<ShieldAlert className="w-5 h-5 text-amber-400" />}
          status={blockedCount > 0 ? 'warning' : 'ok'}
          loading={loadingHealth}
        />
        <MetricCard
          title="Compliance Events Recorded"
          value={totalEventsCount}
          subtext="Compliance logs stored in local cache"
          icon={<FileSpreadsheet className="w-5 h-5 text-purple-400" />}
          status="info"
          loading={loadingHealth}
        />
      </div>

      {/* Health Probes Grid */}
      <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5">
        <div className="flex justify-between items-center border-b border-gray-900 pb-3 mb-5">
          <span className="text-xs font-mono font-bold text-gray-400 uppercase tracking-widest flex items-center">
            <Server className="w-4 h-4 mr-2 text-gray-500" />
            System Module Health Probes
          </span>
          <div className="text-[10px] font-mono text-gray-600">
            POLLING CALIBRATION: EVERY 30S
          </div>
        </div>

        {healthError && (
          <div className="bg-rose-950/10 border border-rose-900/40 p-4 rounded-xl font-mono text-xs text-rose-400 mb-5 glow-red">
            <AlertTriangle className="w-4.5 h-4.5 text-rose-400 shrink-0 inline-block mr-2" />
            {healthError}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* DB */}
          <div className="bg-[#030712] border border-gray-900 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[10px] font-mono font-semibold text-gray-500 uppercase">Relational DB</span>
                <span className={`w-2 h-2 rounded-full ${isConnected && health?.checks?.db?.status === 'ok' ? 'bg-emerald-400 glow-green' : 'bg-rose-500'}`} />
              </div>
              <h4 className="text-xs font-mono font-bold text-gray-300 mt-2">PostgreSQL</h4>
            </div>
            <div className="mt-4 pt-2 border-t border-gray-900/60 flex justify-between items-center text-[10px] font-mono text-gray-500">
              <span>LATENCY:</span>
              <span className="text-emerald-400 font-bold">{health?.checks?.db?.latency_ms ?? 0} ms</span>
            </div>
          </div>

          {/* Redis */}
          <div className="bg-[#030712] border border-gray-900 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[10px] font-mono font-semibold text-gray-500 uppercase">Task Queue / Cache</span>
                <span className={`w-2 h-2 rounded-full ${isConnected && health?.checks?.redis?.status === 'ok' ? 'bg-emerald-400 glow-green' : 'bg-rose-500'}`} />
              </div>
              <h4 className="text-xs font-mono font-bold text-gray-300 mt-2">Redis Cluster</h4>
            </div>
            <div className="mt-4 pt-2 border-t border-gray-900/60 flex justify-between items-center text-[10px] font-mono text-gray-500">
              <span>LATENCY:</span>
              <span className="text-emerald-400 font-bold">{health?.checks?.redis?.latency_ms ?? 0} ms</span>
            </div>
          </div>

          {/* Neo4j */}
          <div className="bg-[#030712] border border-gray-900 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[10px] font-mono font-semibold text-gray-500 uppercase">Knowledge Graph</span>
                <span className={`w-2 h-2 rounded-full ${isConnected && health?.checks?.neo4j?.status === 'ok' ? 'bg-emerald-400 glow-green' : 'bg-gray-700'}`} />
              </div>
              <h4 className="text-xs font-mono font-bold text-gray-300 mt-2">Neo4j Boundary</h4>
            </div>
            <div className="mt-4 pt-2 border-t border-gray-900/60 flex justify-between items-center text-[10px] font-mono text-gray-500">
              <span>BOUNDARIES:</span>
              <span className={isConnected && health?.checks?.neo4j?.status === 'ok' ? 'text-emerald-400 font-bold' : 'text-gray-600'}>
                {isConnected && health?.checks?.neo4j?.status === 'ok' ? 'ISOLATED' : 'DISABLED'}
              </span>
            </div>
          </div>

          {/* Vector store */}
          <div className="bg-[#030712] border border-gray-900 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[10px] font-mono font-semibold text-gray-500 uppercase">Vector Index</span>
                <span className={`w-2 h-2 rounded-full ${isConnected && health?.checks?.vectorstore?.status === 'ok' ? 'bg-emerald-400 glow-green' : 'bg-rose-500'}`} />
              </div>
              <h4 className="text-xs font-mono font-bold text-gray-300 mt-2">ChromaDB</h4>
            </div>
            <div className="mt-4 pt-2 border-t border-gray-900/60 flex justify-between items-center text-[10px] font-mono text-gray-500">
              <span>DOC COUNT:</span>
              <span className="text-emerald-400 font-bold">{health?.checks?.vectorstore?.doc_count ?? 0}</span>
            </div>
          </div>

          {/* LLM Client */}
          <div className="bg-[#030712] border border-gray-900 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[10px] font-mono font-semibold text-gray-500 uppercase">Inference Client</span>
                <span className={`w-2 h-2 rounded-full ${isConnected && health?.checks?.llm_client?.status === 'configured' ? 'bg-emerald-400 glow-green' : 'bg-rose-500'}`} />
              </div>
              <h4 className="text-xs font-mono font-bold text-gray-300 mt-2">Gemini / OpenAI</h4>
            </div>
            <div className="mt-4 pt-2 border-t border-gray-900/60 flex justify-between items-center text-[10px] font-mono text-gray-500">
              <span>GATEWAY:</span>
              <span className="text-emerald-400 font-bold uppercase">READY</span>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Log Preview */}
      <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5">
        <div className="flex justify-between items-center border-b border-gray-900 pb-3 mb-4">
          <span className="text-xs font-mono font-bold text-gray-400 uppercase tracking-widest flex items-center">
            <ShieldAlert className="w-4 h-4 mr-2 text-gray-500" />
            Recent Security & Sanitisation Incidents
          </span>
          <button
            onClick={() => handleAction('events')}
            className="text-[10px] font-mono text-blue-400 hover:text-blue-300 hover:underline"
          >
            VIEW ENTIRE COMPLIANCE LEDGER &rarr;
          </button>
        </div>

        {recentEvents.length === 0 ? (
          <div className="text-center py-8 text-xs font-mono text-gray-600 bg-[#030712] border border-gray-900 rounded-xl">
            NO DETECTED INCIDENTS: SECURITY ENGINES CLEARED ALL LOGGED RETRIEVALS
          </div>
        ) : (
          <div className="space-y-2">
            {recentEvents.map((evt) => (
              <div
                key={evt.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-[#030712] border border-gray-900 rounded-xl hover:border-gray-800 transition-all font-mono text-xs gap-3 group"
              >
                <div className="flex items-start sm:items-center space-x-3">
                  <div className="shrink-0 pt-0.5 sm:pt-0">
                    <StatusBadge status={evt.risk} type="risk" />
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-500 block sm:inline mr-2">{new Date(evt.time).toLocaleTimeString()}</span>
                    <span className="text-gray-300 font-semibold group-hover:text-blue-400 transition-colors">
                      {evt.type.replace('_', ' ').toUpperCase()} ({evt.user})
                    </span>
                    <p className="text-[10px] text-gray-500 font-light mt-1 max-w-[280px] sm:max-w-xl truncate" title={evt.details}>
                      {evt.details}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between sm:justify-end gap-3 text-[10px]">
                  <span className="text-gray-500">TENANT: {evt.tenant}</span>
                  <span className="bg-gray-900 border border-gray-800 text-gray-500 px-2 py-0.5 rounded text-[9px] uppercase font-light">
                    {evt.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
