# AegisVault: Enterprise RAG Privacy Guard

AegisVault is a high-security Retrieval-Augmented Generation (RAG) backend framework designed to protect sensitive data during document ingestion and LLM inference. It implements a 6-layer defense-in-depth architecture to mitigate prompt injection, cross-tenant data leakage, PII exposure, and embedding inversion risks.

## Features

*   **Layer 1: Ingestion Scrubber & DP Embedder**
    *   Uses Presidio (NER) to detect and redact PII *before* chunking.
    *   Quarantines documents containing critical secrets (API keys, passwords, SSNs).
    *   (Optional) Injects Laplacian noise into embeddings (Differential Privacy) to prevent inversion attacks.
*   **Layer 2: Semantic Router**
    *   Classifies intents and blocks prompt injections, jailbreaks, and data exfiltration attempts before they reach the LLM or vector database.
*   **Layer 3: RBAC & Tenant Isolation**
    *   Enforces sensitivity clearances (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`).
    *   Filters vector search results strictly based on the user's `tenant_id` and assigned `roles`.
    *   Supports hard isolation using an optional Neo4j Knowledge Graph boundary.
*   **Layer 4: Clean Context Builder**
    *   Constructs a sanitized, deterministic prompt structure to minimize hallucination and injection surfaces.
*   **Layer 5: Output Sanitizer & Canary Detection**
    *   Scans the LLM output for generated PII and redacts it.
    *   Monitors for Canary Tokens (fake secrets embedded in the DB) to detect and alert on data leaks.
*   **Layer 6: Privacy-Safe Audit Logging**
    *   Logs query traces, RBAC blocks, PII redactions, and latency to a relational database.
    *   Optionally scrubs PII from the audit logs themselves.

## Architecture Overview

AegisVault separates the heavy ingestion workload from the real-time inference path.

*   **Backend:** FastAPI provides the API surface (`/ingest` and `/query`).
*   **Ingestion (Async):** Celery + Redis orchestrate the document scanning, chunking, and embedding.
*   **Vector Store:** ChromaDB stores the chunks and their metadata.
*   **Graph Store:** Neo4j (optional) maintains tenant-to-document relationships for hard boundaries.
*   **Database:** SQLAlchemy/MySQL stores the audit logs and metrics.
*   **LLM Integration:** LangChain orchestrates calls to OpenAI or Gemini.

## Threat Model & Mitigations

| Threat | AegisVault Mitigation |
| :--- | :--- |
| **Prompt Injection** | Semantic Router intent classification (Fail-closed). |
| **Cross-Tenant Leakage** | Hard filtering on `tenant_id` at the vector search level. |
| **Over-clearance Access** | RBAC filtering on document chunks based on sensitivity class. |
| **Accidental PII Ingestion**| Presidio NER scrubbing at ingestion time. |
| **Embedding Inversion** | Differential Privacy (Laplacian noise) injected into vectors. |
| **LLM Data Exfiltration** | Output Sanitizer + Canary Token monitoring. |

## Setup & Execution

### Prerequisites
*   Python 3.12+
*   `uv` package manager (recommended) or `pip`
*   Docker & Docker Compose (for supporting services)

### Environment Variables
Copy `.env.example` to `.env` and configure:
```text
APP_ENV=development
API_KEY=your_secret_api_key_here
GOOGLE_API_KEY=your_google_ai_key
OPENAI_API_KEY=your_openai_api_key

# Services
DATABASE_URL=sqlite:///./data/aegisdb.sqlite  # Or MySQL/Postgres URL
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Security
QUARANTINE_ENCRYPTION_KEY=your_32_byte_base64_fernet_key
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173
MAX_DP_QUERIES_PER_USER_PER_DAY=100
METRICS_TOKEN=your_metrics_scraping_token
LLAMA_GUARD_ENDPOINT=http://localhost:8010/v1
```

### Installation & Running (Development Mode)

#### 1. Backend Setup
1. Sync python dependencies:
   ```powershell
   uv sync
   $env:PYTHONPATH="src"
   ```
2. Start backing services (Redis, Neo4j, MySQL):
   ```powershell
   docker compose up -d
   ```
3. Start the FastAPI server:
   ```powershell
   uvicorn aegisVault.app.main:app --reload --port 8000
   ```
4. Start the Celery worker (in a separate terminal):
   ```powershell
   celery -A aegisVault.worker worker --loglevel=info --concurrency=4
   ```

#### 2. Frontend Setup
1. Open a new terminal and install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Start Vite's development client server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:5173` in your browser. Since authentication is required, you will see the AegisVault Control Center Authentication screen.
4. **Provision Account:** Switch to "Provision Account", input an admin username and password, and click "Create Account". This automatically creates the schema table in the SQL DB, computes a secure PBKDF2 hash, registers the admin, and logs you in.
5. **Admin Sign In:** For subsequent visits, sign in under "Admin Sign In" with your credentials. On successful login, the gateway retrieves and configures the active `API_KEY` in the frontend session automatically, unlocking access to the operations command dashboard.


---

### Running (Production serving Mode)

FastAPI can directly host and serve the built React static files:
1. Build the production assets inside the frontend directory:
   ```bash
   cd frontend
   npm run build
   ```
2. Run the FastAPI backend in production mode by setting `APP_ENV=production`:
   * On Windows Powershell:
     ```powershell
     $env:APP_ENV="production"
     uvicorn aegisVault.app.main:app --port 8000
     ```
   * On Linux/macOS:
     ```bash
     APP_ENV=production uvicorn aegisVault.app.main:app --port 8000
     ```
3. Open `http://127.0.0.1:8000` in your browser. The backend will directly serve the compiled React bundle from `frontend/dist/`.

## API Examples

### 1. Ingest a Document
```powershell
curl -X POST "http://127.0.0.1:8000/ingest/file?async=false" `
  -H "X-API-Key: $env:API_KEY" `
  -F "file=@confidential_report.pdf" `
  -F "tenant_id=acme_corp" `
  -F "acl_roles=executive,manager"
```

### 2. Guarded Query
```powershell
curl -X POST "http://127.0.0.1:8000/query" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: $env:API_KEY" `
  -d '{
    "query": "What are the Q3 targets?",
    "user_id": "usr_998",
    "user_roles": ["employee"],
    "tenant_id": "acme_corp"
  }'
```

### 3. Retrieve Security Events (Compliance Audit Ledger)
```powershell
curl -X GET "http://127.0.0.1:8000/events?limit=10" `
  -H "X-API-Key: $env:API_KEY"
```

### 4. Admin Account Provision (Signup)
```powershell
curl -X POST "http://127.0.0.1:8000/auth/signup" `
  -H "Content-Type: application/json" `
  -d '{
    "username": "superadmin",
    "password": "supersecurepassword"
  }'
```

### 5. Admin Login
```powershell
curl -X POST "http://127.0.0.1:8000/auth/login" `
  -H "Content-Type: application/json" `
  -d '{
    "username": "superadmin",
    "password": "supersecurepassword"
  }'
```


## Screenshots
*(Add screenshots of the frontend UI here once integrated)*
- Dashboard showing blocked queries vs successful queries
- Quarantine view showing redacted secrets
- RBAC simulator

## Known Limitations
*   **Semantic Router Latency:** Local HuggingFace models for intent classification can add 100-300ms overhead.
*   **DP Noise Degradation:** High epsilon values in Differential Privacy may reduce the accuracy of semantic search.
*   **Local ChromaDB:** Default deployment uses local ChromaDB. For horizontal scaling, migrate to Chroma HTTP Client or Qdrant.

## Production Hardening Checklist
- [ ] Migrate secret management to HashiCorp Vault or AWS Secrets Manager.
- [ ] Implement robust Identity Provider (IdP) integration (OAuth2/OIDC) instead of static API keys.
- [ ] Replace local SQLite/MySQL with managed RDS/Aurora.
- [ ] Enable centralized logging (ELK, Datadog) for the audit stream.
- [ ] Implement key rotation for the `QUARANTINE_ENCRYPTION_KEY`.
- [ ] Tune LLM fallback models for the Semantic Router.

## Development
```powershell
# Run tests
pytest

# Type checking
mypy src
```