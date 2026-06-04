import React, { useState } from 'react';
import { useApp } from '../components/AppContext';
import { ErrorPanel } from '../components/ErrorPanel';
import { LoadingState } from '../components/LoadingState';
import { apiClient } from '../api/client';
import type { ApiClientError } from '../api/client';
import type { QueryResponse } from '../types';
import {
  Play,
  User,
  Fingerprint,
  Layers,
  Sliders,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity
} from 'lucide-react';

const ROLES = ['anonymous', 'employee', 'manager', 'executive', 'admin'];

export const QueryConsole: React.FC = () => {
  const { addEvent, showToast } = useApp();

  // Inputs
  const [query, setQuery] = useState('');
  const [userId, setUserId] = useState('u001');
  const [tenantId, setTenantId] = useState('default');
  const [selectedRoles, setSelectedRoles] = useState<string[]>(['employee']);
  const [topK, setTopK] = useState(5);
  const [sessionId, setSessionId] = useState('');

  // Call states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);

  const toggleRole = (role: string) => {
    setSelectedRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    );
  };

  const handleQuerySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const responseData = await apiClient.query({
        query: query.trim(),
        user_id: userId.trim(),
        user_roles: selectedRoles,
        tenant_id: tenantId.trim(),
        top_k: topK,
        session_id: sessionId.trim() || undefined,
      });

      setResponse(responseData);
      showToast('Guarded query finished', 'success');

      // Determine risk level based on the result
      let risk: 'low' | 'medium' | 'high' | 'critical' = 'low';
      let status = 'success';
      let eventDetails = `Completed query. Chunks context retrieved: ${responseData.chunks_used}.`;

      if (responseData.canary_leaked) {
        risk = 'critical';
        status = 'warning';
        eventDetails = 'CRITICAL ALERT: RAG output attempted to leak a Canary Token. Leak was blocked.';
      } else if (responseData.rbac_blocked > 0) {
        risk = 'medium';
        status = 'blocked';
        eventDetails = `RBAC Policy applied: Blocked access to ${responseData.rbac_blocked} document chunk(s).`;
      } else if (responseData.pii_redacted > 0) {
        risk = 'low';
        status = 'success';
        eventDetails = `Query successfully returned with ${responseData.pii_redacted} PII entity redaction(s).`;
      }

      // Add to local audit trail
      addEvent({
        type: 'query',
        tenant: tenantId.trim(),
        user: userId.trim(),
        status,
        risk,
        details: `${eventDetails} Query text: "${query.substring(0, 50)}${query.length > 50 ? '...' : ''}"`,
        traceOrDocId: responseData.trace_id,
      });
    } catch (err: any) {
      console.error('Query error:', err);
      setError(err);
      showToast(err.message || 'Query execution failed', 'error');

      // Log failure in audit
      addEvent({
        type: 'query',
        tenant: tenantId.trim(),
        user: userId.trim(),
        status: 'error',
        risk: 'medium',
        details: `Query execution failed: ${err.message || 'Connection error'}`,
        traceOrDocId: 'failed-trace',
      });
    } finally {
      setLoading(false);
    }
  };

  const isCanaryLeaked = response?.canary_leaked;

  return (
    <div className="space-y-6">
      {/* Introduction Banner */}
      <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5 flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="bg-blue-950/40 p-2.5 rounded-lg border border-blue-500/20">
            <Activity className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold font-mono tracking-wider text-gray-100 uppercase m-0">GUARDED PROMPT RETRIEVAL</h2>
            <p className="text-xs text-gray-500 font-light mt-0.5">Real-time analysis spanning RBAC, PII redaction, prompt injection, and canary tracking.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Param settings panel */}
        <form onSubmit={handleQuerySubmit} className="lg:col-span-5 bg-[#0b0f19] border border-gray-900 rounded-xl p-5 space-y-5">
          <h3 className="text-xs font-semibold font-mono tracking-wider text-gray-400 uppercase mb-3 pb-2 border-b border-gray-900">
            CONSOLE PARAMETERS
          </h3>

          {/* User ID & Tenant ID */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider flex items-center">
                <User className="w-3 h-3 mr-1 text-gray-600" /> User Security ID
              </label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="u001"
                pattern="^[a-zA-Z0-9_\-]{1,64}$"
                className="w-full bg-[#030712] border border-gray-800 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider flex items-center">
                <Fingerprint className="w-3 h-3 mr-1 text-gray-600" /> Logical Tenant ID
              </label>
              <input
                type="text"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                placeholder="default"
                pattern="^[a-zA-Z0-9_\-]{1,64}$"
                className="w-full bg-[#030712] border border-gray-800 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
          </div>

          {/* Roles Checkbox Grid */}
          <div className="space-y-2">
            <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider flex items-center">
              <Layers className="w-3 h-3 mr-1 text-gray-600" /> RBAC Clearance Roles
            </label>
            <div className="grid grid-cols-3 gap-2 bg-[#030712] border border-gray-800/60 p-3 rounded-xl">
              {ROLES.map((role) => {
                const checked = selectedRoles.includes(role);
                return (
                  <label
                    key={role}
                    className={`flex items-center space-x-2 p-1.5 rounded-lg border text-[10px] font-mono uppercase cursor-pointer select-none transition-colors ${
                      checked
                        ? 'bg-blue-950/30 border-blue-500/30 text-blue-400 font-semibold'
                        : 'border-transparent text-gray-500 hover:text-gray-400'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleRole(role)}
                      className="hidden"
                    />
                    <span className={`w-1.5 h-1.5 rounded-full ${checked ? 'bg-blue-400' : 'bg-gray-800'}`} />
                    <span>{role}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Top-K Selector & Session ID */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider flex items-center">
                  <Sliders className="w-3 h-3 mr-1 text-gray-600" /> Top-K Retrievals
                </label>
                <span className="text-[10px] font-mono text-blue-400 font-semibold">{topK} Chunks</span>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider">
                Session Memory ID
              </label>
              <input
                type="text"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                placeholder="optional-session"
                className="w-full bg-[#030712] border border-gray-800 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Prompt input */}
          <div className="space-y-2 border-t border-gray-900 pt-4">
            <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider">
              Guarded System Query
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What is our billing and cancellation policy?"
              rows={4}
              className="w-full bg-[#030712] border border-gray-800 rounded-xl p-3.5 text-xs font-mono text-gray-200 placeholder-gray-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 leading-relaxed"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-900 disabled:border-gray-800/80 disabled:text-gray-600 border border-transparent disabled:cursor-not-allowed text-gray-100 rounded-xl text-xs font-mono font-bold tracking-wider flex items-center justify-center space-x-2.5 shadow-lg shadow-blue-950/40 glow-blue transition-all duration-200"
          >
            {loading ? (
              <span>EVALUATING GATEWAY SHIELDS...</span>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>RUN SECURE RETRIEVAL</span>
              </>
            )}
          </button>
        </form>

        {/* Results panel */}
        <div className="lg:col-span-7 space-y-6">
          {error && <ErrorPanel error={error} />}

          {loading && <LoadingState type="console" text="Piping prompt through security layers..." />}

          {!loading && !response && !error && (
            <div className="border border-dashed border-gray-800 rounded-xl p-10 text-center bg-[#0b0f19]/30 min-h-[400px] flex flex-col justify-center items-center">
              <div className="w-12 h-12 bg-gray-900 border border-gray-800/80 rounded-full flex items-center justify-center mb-4 text-gray-600">
                ⚡
              </div>
              <h4 className="text-xs font-semibold text-gray-400 font-mono">RETRIEVAL PIPELINE IDLE</h4>
              <p className="text-[10px] text-gray-500 font-light mt-1 max-w-[280px] mx-auto leading-relaxed">
                Submit a guarded system query using identity details. Retrieval results will display sanitization reports.
              </p>
            </div>
          )}

          {response && (
            <div className="space-y-6 animate-[fade-in_0.3s_ease-out]">
              {/* Risk Banner Alert */}
              {isCanaryLeaked && (
                <div className="bg-rose-950/20 border border-rose-900/40 p-4 rounded-xl flex items-start space-x-3 glow-red">
                  <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5 animate-pulse" />
                  <div>
                    <h4 className="font-semibold text-rose-400 text-[11.5px] uppercase tracking-wider font-mono">CANARY DATA LEAK CONTAINED</h4>
                    <p className="text-[10.5px] text-rose-500/80 font-mono mt-1 leading-relaxed">
                      AegisVault intercepted a canary token leakage in the output stream. The response payload was sanitised.
                    </p>
                  </div>
                </div>
              )}

              {!isCanaryLeaked && response.rbac_blocked > 0 && (
                <div className="bg-amber-950/20 border border-amber-900/40 p-4 rounded-xl flex items-start space-x-3 glow-amber">
                  <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-amber-400 text-[11.5px] uppercase tracking-wider font-mono">CONTEXT LIMITED BY RBAC FILTERS</h4>
                    <p className="text-[10.5px] text-amber-500/80 font-mono mt-1 leading-relaxed">
                      {response.rbac_blocked} context document chunks were matched but denied authorization due to lack of ACL clearances.
                    </p>
                  </div>
                </div>
              )}

              {/* LLM Response Panel */}
              <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5 space-y-4">
                <div className="flex justify-between items-center border-b border-gray-900 pb-3">
                  <span className="text-[10px] font-mono font-bold text-gray-400 uppercase tracking-widest flex items-center">
                    <CheckCircle className={`w-3.5 h-3.5 mr-2 ${isCanaryLeaked ? 'text-rose-500' : 'text-emerald-500'}`} />
                    Sanitized Output Payload
                  </span>
                  <div className="flex space-x-2 text-[9px] font-mono text-gray-500">
                    <span>STATUS:</span>
                    <span className={isCanaryLeaked ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'}>
                      {isCanaryLeaked ? 'SANITIZED' : 'CLEARED'}
                    </span>
                  </div>
                </div>
                <div className="p-4 bg-[#030712] border border-gray-900 rounded-xl font-mono text-xs text-gray-300 leading-relaxed whitespace-pre-wrap select-all selection:bg-blue-900/30">
                  {response.response}
                </div>
              </div>

              {/* Security Metrics Panel */}
              <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5">
                <h3 className="text-xs font-semibold font-mono tracking-wider text-gray-400 uppercase mb-4 pb-2 border-b border-gray-900">
                  SHIELD EVALUATION TRACES
                </h3>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3.5">
                  {/* Trace ID */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">TRACE IDENTIFIER</span>
                    <span className="text-[10px] text-gray-300 block truncate mt-1 select-all font-light" title={response.trace_id}>
                      {response.trace_id}
                    </span>
                  </div>

                  {/* Chunks */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">AUTHORIZED CONTEXT</span>
                    <span className="text-[11px] text-emerald-400 font-bold block mt-1">
                      {response.chunks_used} Chunks
                    </span>
                  </div>

                  {/* RBAC Blocked */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">RBAC ACCESS BLOCKED</span>
                    <span className={`text-[11px] font-bold block mt-1 ${response.rbac_blocked > 0 ? 'text-amber-500 animate-pulse' : 'text-gray-500'}`}>
                      {response.rbac_blocked} Chunks
                    </span>
                  </div>

                  {/* PII Redacted */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">PII ENTITIES SCRUBBED</span>
                    <span className={`text-[11px] font-bold block mt-1 ${response.pii_redacted > 0 ? 'text-blue-400' : 'text-gray-500'}`}>
                      {response.pii_redacted} Values
                    </span>
                  </div>

                  {/* Canary Leaked */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">CANARY ATTACK BLOCKED</span>
                    <span className={`text-[10px] uppercase font-bold block mt-1 ${isCanaryLeaked ? 'text-rose-400 animate-pulse' : 'text-gray-500'}`}>
                      {isCanaryLeaked ? 'CONTAINED' : 'CLEAN'}
                    </span>
                  </div>

                  {/* Latency */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono flex items-center space-x-2">
                    <div className="flex-1">
                      <span className="block text-[8px] text-gray-500 uppercase font-semibold">LATENCY</span>
                      <span className="text-[11px] text-gray-300 font-bold block mt-1">
                        {response.latency_ms} ms
                      </span>
                    </div>
                    <Clock className="w-3.5 h-3.5 text-gray-600 shrink-0" />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
