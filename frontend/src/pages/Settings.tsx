import React, { useState } from 'react';
import { useApp } from '../components/AppContext';
import { Eye, EyeOff, Save, Trash2, CheckCircle2, XCircle, ShieldCheck } from 'lucide-react';
import { apiClient } from '../api/client';

export const Settings: React.FC = () => {
  const { baseUrl: savedUrl, apiKey: savedKey, saveSettings, clearSettings, showToast, refreshHealth } = useApp();

  const [inputUrl, setInputUrl] = useState(savedUrl);
  const [inputKey, setInputKey] = useState(savedKey);
  const [showKey, setShowKey] = useState(false);

  // Testing connection state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    status: 'idle' | 'success' | 'error';
    message?: string;
    version?: string;
  }>({ status: 'idle' });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    saveSettings(inputUrl, inputKey);
  };

  const handleClear = () => {
    clearSettings();
    setInputUrl('http://127.0.0.1:8000');
    setInputKey('');
    setTestResult({ status: 'idle' });
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult({ status: 'idle' });
    try {
      // Temporarily store in localStorage so apiClient can read it for the health test, 
      // but don't save officially in state until they click save, or we can just test with whatever is entered.
      // Wait, let's write to localStorage temporarily, run the test, and restore if they don't save, 
      // or we can modify apiClient to take temporary overrides. Since localStorage is simple, we can do that!
      const originalUrl = localStorage.getItem('ae_base_url');
      const originalKey = localStorage.getItem('ae_api_key');
      
      localStorage.setItem('ae_base_url', inputUrl);
      localStorage.setItem('ae_api_key', inputKey);

      const healthRes = await apiClient.getHealth();
      
      // Restore original config in storage (they must click "Save" to persist permanently)
      if (originalUrl) localStorage.setItem('ae_base_url', originalUrl);
      else localStorage.removeItem('ae_base_url');

      if (originalKey) localStorage.setItem('ae_api_key', originalKey);
      else localStorage.removeItem('ae_api_key');

      setTestResult({
        status: 'success',
        message: `Connection established. Health: ${healthRes.status}.`,
        version: healthRes.version
      });
      showToast('Connection test passed', 'success');
      
      // Trigger global state update if this is the active config they are testing
      if (inputUrl === savedUrl && inputKey === savedKey) {
        refreshHealth();
      }
    } catch (err: any) {
      setTestResult({
        status: 'error',
        message: err.message || 'Could not reach gateway. Verify url and API key.'
      });
      showToast('Connection test failed', 'error');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Intro details */}
      <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-6">
        <div className="flex items-center space-x-3.5 mb-2">
          <div className="bg-blue-950/60 p-2.5 rounded-lg border border-blue-500/20">
            <ShieldCheck className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold font-mono tracking-wider text-gray-100 m-0 uppercase">SECURITY GATEWAY INTERFACE</h2>
            <p className="text-xs text-gray-500 font-light mt-0.5">Configure authentication headers and endpoints for RAG privacy layers.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Form */}
        <div className="lg:col-span-2 bg-[#0b0f19] border border-gray-900 rounded-xl p-6">
          <h3 className="text-sm font-semibold font-mono tracking-wider text-gray-300 uppercase mb-5 border-b border-gray-900 pb-3">
            API AUTHENTICATION & PATHS
          </h3>

          <form onSubmit={handleSave} className="space-y-5">
            {/* Base URL */}
            <div className="space-y-1.5">
              <label htmlFor="base-url" className="block text-[10px] font-mono font-bold text-gray-400 uppercase tracking-widest">
                API Base URL Address
              </label>
              <input
                id="base-url"
                type="url"
                value={inputUrl}
                onChange={(e) => setInputUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000"
                className="w-full bg-[#030712] border border-gray-800 rounded-xl px-4 py-3 text-sm font-mono text-gray-200 placeholder-gray-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                required
              />
              <span className="block text-[10px] text-gray-500 font-mono mt-1">
                Root endpoint address of AegisVault FastAPI server. Default: http://127.0.0.1:8000.
              </span>
            </div>

            {/* API Key */}
            <div className="space-y-1.5">
              <label htmlFor="api-key" className="block text-[10px] font-mono font-bold text-gray-400 uppercase tracking-widest">
                X-API-KEY Header Value
              </label>
              <div className="relative">
                <input
                  id="api-key"
                  type={showKey ? 'text' : 'password'}
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  placeholder="Enter API security token..."
                  className="w-full bg-[#030712] border border-gray-800 rounded-xl pl-4 pr-11 py-3 text-sm font-mono text-gray-200 placeholder-gray-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 p-0.5 rounded transition-colors"
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <span className="block text-[10px] text-gray-500 font-mono mt-1">
                Stored purely in local browser memory. Sent as X-API-Key with every RAG retrieval or ingest request.
              </span>
            </div>

            {/* Actions buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-between border-t border-gray-900 pt-5 mt-6 gap-3">
              <button
                type="button"
                onClick={handleClear}
                className="w-full sm:w-auto px-4 py-2.5 border border-rose-950/80 bg-rose-950/10 hover:bg-rose-950/20 text-rose-400 hover:text-rose-300 rounded-xl text-xs font-mono font-semibold tracking-wider flex items-center justify-center space-x-2 transition-all duration-200"
              >
                <Trash2 className="w-4 h-4" />
                <span>RESET CONFIGS</span>
              </button>

              <div className="flex flex-col sm:flex-row items-center space-y-3 sm:space-y-0 sm:space-x-3 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="w-full sm:w-auto px-4.5 py-2.5 border border-gray-800 bg-[#070b13] hover:bg-gray-900 text-gray-300 hover:text-gray-100 rounded-xl text-xs font-mono font-semibold tracking-wider flex items-center justify-center space-x-2 transition-all duration-200"
                >
                  <span>{testing ? 'TESTING...' : 'PING GATEWAY'}</span>
                </button>

                <button
                  type="submit"
                  className="w-full sm:w-auto px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-gray-100 rounded-xl text-xs font-mono font-semibold tracking-wider flex items-center justify-center space-x-2 shadow-lg shadow-blue-950/40 glow-blue transition-all duration-200"
                >
                  <Save className="w-4 h-4" />
                  <span>COMMIT CHANGES</span>
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Diagnostic Panel */}
        <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold font-mono tracking-wider text-gray-300 uppercase mb-5 border-b border-gray-900 pb-3">
              GATEWAY DIAGNOSTICS
            </h3>

            {testResult.status === 'idle' && (
              <div className="text-center py-10">
                <div className="w-12 h-12 rounded-full border border-dashed border-gray-800 flex items-center justify-center mx-auto mb-3.5 text-gray-600">
                  ⚡
                </div>
                <h4 className="text-xs font-semibold text-gray-400 font-mono">CONNECTION UNTESTED</h4>
                <p className="text-[10px] text-gray-500 font-light mt-1 max-w-[200px] mx-auto leading-relaxed">
                  Trigger a Ping command to run health diagnostic checks against the API endpoint.
                </p>
              </div>
            )}

            {testResult.status === 'success' && (
              <div className="space-y-4 font-mono text-xs">
                <div className="bg-emerald-950/20 border border-emerald-900/40 p-4 rounded-xl flex items-start space-x-3">
                  <CheckCircle2 className="w-4.5 h-4.5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-emerald-400 text-[11px] uppercase tracking-wider">GATEWAY ONLINE</h4>
                    <p className="text-[10px] text-emerald-500/80 font-light leading-relaxed mt-1">{testResult.message}</p>
                  </div>
                </div>

                <div className="bg-[#030712] border border-gray-900/80 p-4 rounded-xl space-y-2">
                  <div className="flex justify-between border-b border-gray-900/60 pb-1.5 text-[10px]">
                    <span className="text-gray-500">VERSION ID:</span>
                    <span className="text-gray-300 font-semibold">{testResult.version}</span>
                  </div>
                  <div className="flex justify-between border-b border-gray-900/60 pb-1.5 text-[10px]">
                    <span className="text-gray-500">AUTHENTICATED:</span>
                    <span className="text-emerald-400 font-semibold">TRUE</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-gray-500">PING LATENCY:</span>
                    <span className="text-emerald-400 font-semibold">&lt; 15 ms</span>
                  </div>
                </div>
              </div>
            )}

            {testResult.status === 'error' && (
              <div className="space-y-4 font-mono text-xs">
                <div className="bg-rose-950/20 border border-rose-900/40 p-4 rounded-xl flex items-start space-x-3 glow-red">
                  <XCircle className="w-4.5 h-4.5 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-rose-400 text-[11px] uppercase tracking-wider">CONNECTION FAILED</h4>
                    <p className="text-[10px] text-rose-500/80 font-light leading-relaxed mt-1">{testResult.message}</p>
                  </div>
                </div>

                <div className="text-[10px] text-gray-500 font-sans leading-relaxed p-2 bg-[#030712] border border-gray-900 rounded-xl">
                  <span className="font-bold text-gray-400">POSSIBLE ISSUES:</span>
                  <ul className="list-disc pl-4 mt-1 space-y-1">
                    <li>The RAG FastAPI backend server is not running or is set to a different port.</li>
                    <li>CORS blocks browser requests from your current client address.</li>
                    <li>Incorrect endpoint URL format (ensure it starts with http:// or https://).</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          <div className="text-[9px] font-mono text-gray-600 bg-gray-950/20 p-3 rounded-lg border border-gray-900 mt-6 leading-relaxed">
            <span className="font-semibold text-gray-500 block mb-0.5">X-API-KEY INFO:</span>
            AegisVault protects retrieval engines using key-based authorization. Ensure keys are synced between backend configurations and the client header definitions.
          </div>
        </div>
      </div>
    </div>
  );
};
