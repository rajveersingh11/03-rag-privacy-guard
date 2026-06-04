import React, { useState, useEffect } from 'react';
import { useApp } from '../components/AppContext';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { ShieldAlert, Trash2, Filter, Download, Calendar, Search } from 'lucide-react';
import type { SecurityEvent } from '../types';

export const SecurityEvents: React.FC = () => {
  const { events, clearEvents, addEvent } = useApp();
  const [filterType, setFilterType] = useState<string>('all');
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Prepopulate with a few demo records if localStorage is completely empty
  useEffect(() => {
    if (events.length === 0) {
      const demoEvents: Omit<SecurityEvent, 'id' | 'time'>[] = [
        {
          type: 'query',
          tenant: 'finance_corp',
          user: 'u948',
          status: 'success',
          risk: 'low',
          details: 'Retrieved general billing info. Standard clearance matching.',
          traceOrDocId: 'tr-8fb3d10c-99a3-4122'
        },
        {
          type: 'query',
          tenant: 'health_sys',
          user: 'anon_user',
          status: 'blocked',
          risk: 'high',
          details: 'Query contained unauthorized SSN prompt request. Blocked by Layer 3 RBAC policy.',
          traceOrDocId: 'tr-3ec9e419-74d1-4475'
        },
        {
          type: 'file_ingest',
          tenant: 'default',
          user: 'admin_sys',
          status: 'warning',
          risk: 'medium',
          details: 'Ingested raw CSV. Sanitized 4 phone numbers and quarantined 1 password hash.',
          traceOrDocId: 'doc_user_metrics_v2.csv'
        },
        {
          type: 'query',
          tenant: 'default',
          user: 'u102',
          status: 'warning',
          risk: 'critical',
          details: 'Canary token "AEGIS-CANARY-D93FB" leaked by LLM response. Logged and scrubbed.',
          traceOrDocId: 'tr-cf2984ab-2051-4099'
        }
      ];

      // Add them with some delays to spacing time stamps
      demoEvents.forEach((de, index) => {
        setTimeout(() => {
          addEvent(de);
        }, index * 100);
      });
    }
  }, [events.length, addEvent]);

  // Filter events
  const filteredEvents = events.filter((evt) => {
    const matchesType = filterType === 'all' || evt.type === filterType;
    const matchesRisk = filterRisk === 'all' || evt.risk === filterRisk;
    
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = 
      evt.user.toLowerCase().includes(searchLower) ||
      evt.tenant.toLowerCase().includes(searchLower) ||
      evt.traceOrDocId.toLowerCase().includes(searchLower) ||
      evt.details.toLowerCase().includes(searchLower);

    return matchesType && matchesRisk && matchesSearch;
  });

  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(events, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href",     dataStr);
    downloadAnchor.setAttribute("download", `aegisvault_audit_export_${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6">
      {/* Filters & Actions Panel */}
      <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <div className="bg-red-950/40 p-2 rounded-lg border border-red-500/20">
              <ShieldAlert className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold font-mono tracking-wider text-gray-100 uppercase m-0">SECURITY AUDIT ENGINE</h2>
              <p className="text-xs text-gray-500 font-light mt-0.5">Cryptographic traces, compliance blocks, and canary exposure logs.</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2.5 items-center">
            {events.length > 0 && (
              <>
                <button
                  onClick={handleExport}
                  className="px-3.5 py-2 border border-gray-800 bg-[#070b13] hover:bg-gray-900 text-gray-300 hover:text-gray-100 rounded-lg text-xs font-mono font-semibold tracking-wider flex items-center space-x-1.5 transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>EXPORT LOGS</span>
                </button>
                <button
                  onClick={clearEvents}
                  className="px-3.5 py-2 border border-rose-950/80 bg-rose-950/10 hover:bg-rose-950/20 text-rose-400 hover:text-rose-300 rounded-lg text-xs font-mono font-semibold tracking-wider flex items-center space-x-1.5 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>CLEAR COMPLIANCE</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Filter controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 mt-5 border-t border-gray-900 pt-4">
          {/* Search bar */}
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600">
              <Search className="w-3.5 h-3.5" />
            </span>
            <input
              type="text"
              placeholder="Search user, tenant, ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-[#030712] border border-gray-800 rounded-xl pl-9 pr-4 py-2 text-xs font-mono text-gray-300 placeholder-gray-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
            />
          </div>

          {/* Type Filter */}
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600">
              <Filter className="w-3.5 h-3.5" />
            </span>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full bg-[#030712] border border-gray-800 rounded-xl pl-9 pr-4 py-2 text-xs font-mono text-gray-400 focus:outline-none focus:border-blue-500 focus:text-gray-200"
            >
              <option value="all">ALL EVENT TYPES</option>
              <option value="query">QUERIES</option>
              <option value="file_ingest">FILE INGESTS</option>
              <option value="text_ingest">TEXT INGESTS</option>
            </select>
          </div>

          {/* Risk Filter */}
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600">
              <ShieldAlert className="w-3.5 h-3.5" />
            </span>
            <select
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value)}
              className="w-full bg-[#030712] border border-gray-800 rounded-xl pl-9 pr-4 py-2 text-xs font-mono text-gray-400 focus:outline-none focus:border-blue-500 focus:text-gray-200"
            >
              <option value="all">ALL RISK LEVELS</option>
              <option value="low">LOW</option>
              <option value="medium">MEDIUM</option>
              <option value="high">HIGH</option>
              <option value="critical">CRITICAL</option>
            </select>
          </div>

          <div className="flex items-center justify-end text-[10px] font-mono text-gray-500 pr-2">
            Showing {filteredEvents.length} of {events.length} audit logs
          </div>
        </div>
      </div>

      {/* Events Log List */}
      {filteredEvents.length === 0 ? (
        <EmptyState
          title="NO COMPLIANCE AUDITS FOUND"
          description="We searched logs but found no events matching those filter parameters. Ingest documents or query the console to trigger audit logs."
          icon={<ShieldAlert className="w-8 h-8 text-gray-700" />}
        />
      ) : (
        <div className="bg-[#0b0f19] border border-gray-900 rounded-xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-900 bg-[#05080f]/60 text-[9px] font-mono text-gray-500 uppercase tracking-widest">
                  <th className="py-4 px-6 font-semibold">TIME STAMP</th>
                  <th className="py-4 px-4 font-semibold">EVENT TYPE</th>
                  <th className="py-4 px-4 font-semibold">TENANT</th>
                  <th className="py-4 px-4 font-semibold">IDENTITY</th>
                  <th className="py-4 px-4 font-semibold">RISK LEVEL</th>
                  <th className="py-4 px-4 font-semibold">TRACE / DOC ID</th>
                  <th className="py-4 px-6 font-semibold">AUDIT DECRYPT DETAILS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-900/60 font-mono text-xs text-gray-300">
                {filteredEvents.map((evt) => (
                  <tr key={evt.id} className="hover:bg-[#121826]/30 transition-colors group">
                    <td className="py-4 px-6 text-[10px] text-gray-500 font-light flex items-center space-x-1.5 whitespace-nowrap">
                      <Calendar className="w-3 h-3 text-gray-600" />
                      <span>{new Date(evt.time).toLocaleString()}</span>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      <StatusBadge status={evt.type} type="event" />
                    </td>
                    <td className="py-4 px-4 text-[11px] text-gray-400 font-medium whitespace-nowrap">
                      {evt.tenant}
                    </td>
                    <td className="py-4 px-4 text-[11px] text-gray-400 whitespace-nowrap">
                      {evt.user}
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      <StatusBadge status={evt.risk} type="risk" />
                    </td>
                    <td className="py-4 px-4 text-[10px] text-gray-500 select-all font-light break-all max-w-[120px] truncate" title={evt.traceOrDocId}>
                      {evt.traceOrDocId}
                    </td>
                    <td className="py-4 px-6 text-[11px] text-gray-400 leading-normal max-w-sm">
                      <p className="line-clamp-2 text-gray-400 group-hover:text-gray-200 transition-colors">
                        {evt.details}
                      </p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
