import type { HealthCheckResponse, QueryRequest, QueryResponse, IngestResponse, SecurityEvent } from '../types';

export interface ApiClientError {
  status?: number;
  message: string;
  type: 'unauthorized' | 'rate_limit' | 'unavailable' | 'validation' | 'generic';
}

function getSettings() {
  const baseUrl = localStorage.getItem('ae_base_url') || 'http://127.0.0.1:8000';
  const apiKey = localStorage.getItem('ae_api_key') || '';
  return { baseUrl: baseUrl.replace(/\/$/, ''), apiKey };
}

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

function getHeaders(method: string, baseHeaders: Record<string, string> = {}): Record<string, string> {
  const { apiKey } = getSettings();
  const headers: Record<string, string> = { ...baseHeaders };
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method.toUpperCase())) {
    const csrfToken = getCookie('aegis_csrf');
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = 'An error occurred';
    let type: ApiClientError['type'] = 'generic';

    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || JSON.stringify(errorData);
    } catch {
      try {
        message = await response.text();
      } catch {
        // Fallback to default message
      }
    }

    if (response.status === 401 || response.status === 403) {
      type = 'unauthorized';
      message = 'Invalid API key or unauthorized request.';
    } else if (response.status === 429) {
      type = 'rate_limit';
      message = 'Rate limit exceeded. Please try again later.';
    } else if (response.status === 503) {
      type = 'unavailable';
      message = 'Service unavailable. The security pipeline or backend system is not ready.';
    } else if (response.status === 422) {
      type = 'validation';
      message = `Input validation error: ${message}`;
    }

    const apiError: ApiClientError = {
      status: response.status,
      message,
      type,
    };
    throw apiError;
  }

  return response.json() as Promise<T>;
}

export interface AuthResponse {
  status: string;
  user_id: string;
  username: string;
  role: string;
  tenant_id: string;
  expires_at: string;
}

export const apiClient = {
  getHealth: async (): Promise<HealthCheckResponse> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('GET');

    const response = await fetch(`${baseUrl}/health`, {
      method: 'GET',
      headers,
      credentials: 'include',
    });
    return handleResponse<HealthCheckResponse>(response);
  },

  query: async (payload: QueryRequest): Promise<QueryResponse> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('POST', {
      'Content-Type': 'application/json',
    });

    const response = await fetch(`${baseUrl}/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      credentials: 'include',
    });
    return handleResponse<QueryResponse>(response);
  },

  ingestFile: async (
    file: File,
    tenantId: string,
    aclRoles: string,
    runAsync: boolean
  ): Promise<IngestResponse> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('POST');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('tenant_id', tenantId);
    formData.append('acl_roles', aclRoles);

    const response = await fetch(`${baseUrl}/ingest/file?async=${runAsync}`, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    });
    return handleResponse<IngestResponse>(response);
  },

  ingestText: async (
    text: string,
    source: string,
    tenantId: string,
    aclRoles: string
  ): Promise<IngestResponse> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('POST');

    const formData = new FormData();
    formData.append('text', text);
    formData.append('source', source);
    formData.append('tenant_id', tenantId);
    formData.append('acl_roles', aclRoles);

    const response = await fetch(`${baseUrl}/ingest/text`, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include',
    });
    return handleResponse<IngestResponse>(response);
  },

  getSecurityEvents: async (limit: number = 50): Promise<SecurityEvent[]> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('GET');

    const response = await fetch(`${baseUrl}/events?limit=${limit}`, {
      method: 'GET',
      headers,
      credentials: 'include',
    });
    return handleResponse<SecurityEvent[]>(response);
  },

  login: async (username: string, password: string): Promise<AuthResponse> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('POST', {
      'Content-Type': 'application/json',
    });
    const response = await fetch(`${baseUrl}/auth/login`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ username, password }),
      credentials: 'include',
    });
    return handleResponse<AuthResponse>(response);
  },

  signup: async (username: string, password: string): Promise<AuthResponse> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('POST', {
      'Content-Type': 'application/json',
    });
    const response = await fetch(`${baseUrl}/auth/signup`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ username, password }),
      credentials: 'include',
    });
    return handleResponse<AuthResponse>(response);
  },

  logout: async (): Promise<void> => {
    const { baseUrl } = getSettings();
    const headers = getHeaders('POST');
    const response = await fetch(`${baseUrl}/auth/logout`, {
      method: 'POST',
      headers,
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error('Logout failed');
    }
  },
};
