import React, { useState, useRef } from 'react';
import { useApp } from '../components/AppContext';
import { ErrorPanel } from '../components/ErrorPanel';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { apiClient } from '../api/client';
import type { ApiClientError } from '../api/client';
import type { IngestResponse } from '../types';
import {
  UploadCloud,
  FileText,
  FileCode,
  Globe,
  Users,
  Zap,
  CheckCircle,
  Database,
  CheckSquare,
  Square,
  Hash,
  AlertTriangle
} from 'lucide-react';

export const Ingestion: React.FC = () => {
  const { addEvent, showToast } = useApp();

  // Navigation tab
  const [activeTab, setActiveTab] = useState<'file' | 'text'>('file');

  // Common Form States
  const [tenantId, setTenantId] = useState('default');
  const [aclRoles, setAclRoles] = useState('employee');
  
  // File Tab States
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [runAsync, setRunAsync] = useState(false); // sync by default so user gets immediate response
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Text Tab States
  const [text, setText] = useState('');
  const [source, setSource] = useState('manual_input');

  // API Call States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [result, setResult] = useState<IngestResponse | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const validExtensions = ['.txt', '.md', '.csv', '.pdf'];
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (validExtensions.includes(ext)) {
        setSelectedFile(file);
        setError(null);
      } else {
        showToast('Invalid file type. Only .txt, .md, .csv, .pdf supported.', 'warning');
      }
    }
  };

  const clearFileSelection = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let response: IngestResponse;

      if (activeTab === 'file') {
        if (!selectedFile) {
          showToast('Please select a file to upload.', 'warning');
          setLoading(false);
          return;
        }
        response = await apiClient.ingestFile(selectedFile, tenantId, aclRoles, runAsync);
      } else {
        if (!text.trim()) {
          showToast('Please enter document content.', 'warning');
          setLoading(false);
          return;
        }
        response = await apiClient.ingestText(text, source, tenantId, aclRoles);
      }

      setResult(response);
      showToast('Document ingested successfully', 'success');

      // Determine risk level based on the result
      let risk: 'low' | 'medium' | 'high' | 'critical' = 'low';
      let status = response.status === 'quarantined' ? 'blocked' : 'success';
      let eventDetails = `Ingested doc "${response.doc_id}". Chunks stored: ${response.chunks_stored}. Sensitivity: ${response.sensitivity_class}.`;

      if (response.status === 'quarantined') {
        risk = 'high';
        eventDetails = `DOCUMENT QUARANTINED: Ingestion blocked. Sensitivity class triggers auto-quarantine rules.`;
      } else if (response.pii_entities_found.length > 0) {
        risk = 'medium';
        eventDetails = `Ingested document "${response.doc_id}" with ${response.pii_entities_found.length} PII scrubbing events.`;
      }

      // Add to audit trail
      addEvent({
        type: activeTab === 'file' ? 'file_ingest' : 'text_ingest',
        tenant: tenantId.trim(),
        user: 'admin_sys', // frontend admin context
        status,
        risk,
        details: eventDetails,
        traceOrDocId: response.doc_id,
      });

    } catch (err: any) {
      console.error('Ingest error:', err);
      setError(err);
      showToast(err.message || 'Ingestion failed', 'error');

      // Log failure in audit
      addEvent({
        type: activeTab === 'file' ? 'file_ingest' : 'text_ingest',
        tenant: tenantId.trim(),
        user: 'admin_sys',
        status: 'error',
        risk: 'medium',
        details: `Ingestion failed: ${err.message || 'Connection error'}`,
        traceOrDocId: activeTab === 'file' && selectedFile ? selectedFile.name : 'manual-input',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Intro details */}
      <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5 flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="bg-blue-950/40 p-2.5 rounded-lg border border-blue-500/20">
            <Database className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold font-mono tracking-wider text-gray-100 uppercase m-0">DOCUMENT INGESTION GATEWAY</h2>
            <p className="text-xs text-gray-500 font-light mt-0.5">Parse, scrub PII, execute differential privacy embeddings, and index into ChromaDB & Neo4j.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Forms input */}
        <div className="lg:col-span-5 bg-[#0b0f19] border border-gray-900 rounded-xl p-5 space-y-5">
          {/* Tab selector */}
          <div className="flex border-b border-gray-900 pb-0.5 gap-2">
            <button
              onClick={() => {
                setActiveTab('file');
                setError(null);
                setResult(null);
              }}
              className={`flex-1 pb-3 text-xs font-mono font-bold tracking-wider uppercase border-b-2 text-center transition-all ${
                activeTab === 'file'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-400'
              }`}
            >
              FILE COMPLIANCE
            </button>
            <button
              onClick={() => {
                setActiveTab('text');
                setError(null);
                setResult(null);
              }}
              className={`flex-1 pb-3 text-xs font-mono font-bold tracking-wider uppercase border-b-2 text-center transition-all ${
                activeTab === 'text'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-400'
              }`}
            >
              RAW CONTENT BLOCK
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Tab Specific Content */}
            {activeTab === 'file' ? (
              <div className="space-y-4">
                {/* Drag and Drop Zone */}
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  className={`border border-dashed rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col justify-center items-center min-h-[140px] ${
                    selectedFile
                      ? 'border-blue-500/40 bg-blue-950/5'
                      : 'border-gray-800 hover:border-gray-700 bg-gray-950/20'
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.md,.csv,.pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  {selectedFile ? (
                    <div className="space-y-2.5">
                      <FileCode className="w-9 h-9 text-blue-400 mx-auto" />
                      <div>
                        <p className="text-xs text-gray-200 font-mono font-semibold max-w-[200px] mx-auto truncate">
                          {selectedFile.name}
                        </p>
                        <p className="text-[10px] text-gray-500 font-mono mt-0.5">
                          {(selectedFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          clearFileSelection();
                        }}
                        className="text-[10px] font-mono text-rose-400 hover:text-rose-300 underline"
                      >
                        REMOVE FILE
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <UploadCloud className="w-9 h-9 text-gray-500 mx-auto" />
                      <p className="text-xs text-gray-400 font-mono">
                        DRAG & DROP OR <span className="text-blue-400 underline">BROWSE</span>
                      </p>
                      <p className="text-[9px] text-gray-600 font-mono uppercase">
                        SUPPORTED: .txt, .md, .csv, .pdf (Max 5MB)
                      </p>
                    </div>
                  )}
                </div>

                {/* Async Sync Toggle */}
                <div className="flex items-center justify-between p-3.5 bg-[#030712] border border-gray-800/80 rounded-xl">
                  <div className="flex items-center space-x-2">
                    <Zap className="w-4 h-4 text-amber-500 shrink-0" />
                    <div>
                      <span className="block text-[10px] font-mono font-bold text-gray-400 uppercase tracking-wide">Celery Async Task Queue</span>
                      <span className="block text-[8px] text-gray-500 font-mono leading-relaxed mt-0.5">Queue upload in background and return immediate Task ID.</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setRunAsync(!runAsync)}
                    className="p-1 hover:text-gray-200 text-gray-400 transition-colors"
                  >
                    {runAsync ? (
                      <CheckSquare className="w-5 h-5 text-blue-500" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-800" />
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Text Block Textarea */}
                <div className="space-y-1.5">
                  <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider">
                    Raw Document text block
                  </label>
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Enter sensitive documents content, tables, or unstructured files to index..."
                    rows={6}
                    className="w-full bg-[#030712] border border-gray-800 rounded-xl p-3 text-xs font-mono text-gray-200 placeholder-gray-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 leading-relaxed"
                    required
                  />
                </div>

                {/* Source Filename Input */}
                <div className="space-y-1.5">
                  <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider flex items-center">
                    <FileText className="w-3.5 h-3.5 mr-1 text-gray-600" /> Source File Identifier
                  </label>
                  <input
                    type="text"
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    placeholder="manual_input"
                    className="w-full bg-[#030712] border border-gray-800 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
              </div>
            )}

            {/* Common Inputs: Tenant, ACL roles */}
            <div className="grid grid-cols-2 gap-4 border-t border-gray-900 pt-4">
              <div className="space-y-1.5">
                <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider flex items-center">
                  <Globe className="w-3.5 h-3.5 mr-1 text-gray-600" /> Tenant Context
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
              <div className="space-y-1.5">
                <label className="block text-[9px] font-mono font-bold text-gray-500 uppercase tracking-wider flex items-center">
                  <Users className="w-3.5 h-3.5 mr-1 text-gray-600" /> ACL Clearance Roles
                </label>
                <input
                  type="text"
                  value={aclRoles}
                  onChange={(e) => setAclRoles(e.target.value)}
                  placeholder="employee,manager"
                  className="w-full bg-[#030712] border border-gray-800 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-blue-500"
                  required
                />
                <span className="block text-[8px] text-gray-500 font-mono mt-0.5 leading-none">Comma-separated permissions.</span>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || (activeTab === 'file' ? !selectedFile : !text.trim())}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-900 disabled:border-gray-800/80 disabled:text-gray-600 border border-transparent disabled:cursor-not-allowed text-gray-100 rounded-xl text-xs font-mono font-bold tracking-wider flex items-center justify-center space-x-2.5 shadow-lg shadow-blue-950/40 glow-blue transition-all duration-200"
            >
              {loading ? (
                <span>INGEST MODULE EXECUTING...</span>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>TRANSMIT COMPLIANCE LOAD</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Dynamic results pane */}
        <div className="lg:col-span-7 space-y-6">
          {error && <ErrorPanel error={error} />}

          {loading && <LoadingState type="console" text="Scrubbing document contents, computing vector coordinates..." />}

          {!loading && !result && !error && (
            <div className="border border-dashed border-gray-800 rounded-xl p-10 text-center bg-[#0b0f19]/30 min-h-[380px] flex flex-col justify-center items-center">
              <div className="w-12 h-12 bg-gray-900 border border-gray-800/80 rounded-full flex items-center justify-center mb-4 text-gray-600">
                🔒
              </div>
              <h4 className="text-xs font-semibold text-gray-400 font-mono">INGEST INSPECTION STAGE IDLE</h4>
              <p className="text-[10px] text-gray-500 font-light mt-1 max-w-[280px] mx-auto leading-relaxed">
                Configure data sources and transmit files. Evaluation reports mapping privacy risk boundaries will render here.
              </p>
            </div>
          )}

          {result && (
            <div className="space-y-6 animate-[fade-in_0.3s_ease-out]">
              {/* Alert Status */}
              {result.status === 'quarantined' ? (
                <div className="bg-rose-950/20 border border-rose-900/40 p-4 rounded-xl flex items-start space-x-3 glow-red">
                  <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5 animate-pulse" />
                  <div>
                    <h4 className="font-semibold text-rose-400 text-[11.5px] uppercase tracking-wider font-mono">DOCUMENT QUARANTINED</h4>
                    <p className="text-[10.5px] text-rose-500/80 font-mono mt-1 leading-relaxed">
                      This document was quarantined under isolation protocols. Reason: {result.reason || 'Contains critical sensitivity elements.'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="bg-emerald-950/20 border border-emerald-900/40 p-4 rounded-xl flex items-start space-x-3 glow-green">
                  <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-emerald-400 text-[11.5px] uppercase tracking-wider font-mono">INGESTION COMPLETE</h4>
                    <p className="text-[10.5px] text-emerald-500/80 font-mono mt-1 leading-relaxed">
                      AegisVault successfully completed ingestion pipeline. Document scrubbed and indexed into storage.
                    </p>
                  </div>
                </div>
              )}

              {/* Core attributes cards */}
              <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5 space-y-4">
                <h3 className="text-xs font-semibold font-mono tracking-wider text-gray-400 uppercase border-b border-gray-900 pb-3">
                  COMPLIANCE AUDIT
                </h3>

                <div className="grid grid-cols-2 gap-4">
                  {/* Status */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">PIPELINE STATUS</span>
                    <div className="mt-1">
                      <StatusBadge status={result.status} />
                    </div>
                  </div>

                  {/* Sensitivity */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">SENSITIVITY CLASS</span>
                    <div className="mt-1">
                      <StatusBadge status={result.sensitivity_class} type="sensitivity" />
                    </div>
                  </div>

                  {/* Chunks */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">CHUNKS INDEXED</span>
                    <span className="text-[11px] text-emerald-400 font-bold block mt-1">
                      {result.chunks_stored} Chunks
                    </span>
                  </div>

                  {/* Text modified */}
                  <div className="bg-[#030712] border border-gray-900 p-3 rounded-lg font-mono">
                    <span className="block text-[8px] text-gray-500 uppercase font-semibold">PII SCRUB MODIFIED</span>
                    <span className={`text-[11px] font-bold block mt-1 uppercase ${result.text_modified ? 'text-blue-400' : 'text-gray-500'}`}>
                      {result.text_modified ? 'YES (PII Redacted)' : 'NO'}
                    </span>
                  </div>
                </div>

                {/* Details list info */}
                <div className="space-y-3 pt-3 border-t border-gray-900">
                  {/* Doc ID */}
                  <div className="flex justify-between items-center text-xs font-mono">
                    <span className="text-gray-500">DOCUMENT SOURCE REF:</span>
                    <span className="text-gray-300 font-semibold select-all font-light" title={result.doc_id}>
                      {result.doc_id}
                    </span>
                  </div>

                  {/* Async ID */}
                  {result.async_task_id && (
                    <div className="flex justify-between items-center text-xs font-mono">
                      <span className="text-gray-500">CELERY TASK ID:</span>
                      <span className="text-blue-400 font-semibold select-all font-light" title={result.async_task_id}>
                        {result.async_task_id}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Redacted entities */}
              <div className="bg-[#0b0f19] border border-gray-900 rounded-xl p-5">
                <h3 className="text-xs font-semibold font-mono tracking-wider text-gray-400 uppercase mb-3 pb-2 border-b border-gray-900 flex justify-between">
                  <span>PII SCRUB DETECTIONS</span>
                  <span className="text-gray-500 text-[10px]">
                    {result.pii_entities_found.length} Entities
                  </span>
                </h3>

                {result.pii_entities_found.length === 0 ? (
                  <div className="text-center py-6 text-[10px] font-mono text-gray-500 bg-[#030712] border border-gray-900 rounded-xl">
                    CLEAN PAYLOAD: NO IDENTIFIABLE PII ENTITIES TRIGGERED SCRUB PATHS
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2 p-3 bg-[#030712] border border-gray-900 rounded-xl font-mono text-xs">
                    {result.pii_entities_found.map((entity, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 bg-blue-950/40 text-blue-400 border border-blue-500/20 rounded-md text-[10px] uppercase font-semibold flex items-center space-x-1.5"
                      >
                        <Hash className="w-3 h-3 text-blue-500" />
                        <span>{entity}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
