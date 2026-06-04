export interface HealthCheckDetail {
  status: 'ok' | 'error' | 'configured' | 'unconfigured' | string;
  latency_ms?: number;
  doc_count?: number;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  checks: {
    db: HealthCheckDetail;
    redis: HealthCheckDetail;
    neo4j: HealthCheckDetail;
    vectorstore: HealthCheckDetail;
    llm_client: HealthCheckDetail;
  };
}

export interface QueryRequest {
  query: string;
  user_id: string;
  user_roles: string[];
  tenant_id: string;
  top_k: number;
  session_id?: string;
}

export interface QueryResponse {
  trace_id: string;
  response: string;
  chunks_used: number;
  rbac_blocked: number;
  pii_redacted: number;
  canary_leaked: boolean;
  latency_ms: number;
}

export interface IngestResponse {
  doc_id: string;
  status: string;
  reason: string | null;
  chunks_stored: number;
  sensitivity_class: string;
  pii_entities_found: string[];
  text_modified: boolean;
  async_task_id: string | null;
}

export interface SecurityEvent {
  id: string;
  time: string;
  type: 'query' | 'file_ingest' | 'text_ingest';
  tenant: string;
  user: string;
  status: 'success' | 'blocked' | 'error' | 'warning' | string;
  risk: 'low' | 'medium' | 'high' | 'critical';
  details: string;
  traceOrDocId: string;
}
