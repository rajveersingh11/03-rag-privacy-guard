"""
POST /ingest — Document ingestion endpoint
-------------------------------------------
Accepts a raw text file or JSON payload, queues it as a
Celery task for async processing through the full ingestion
pipeline (PII scrub → DP embed → ChromaDB + Neo4j).

For synchronous ingestion (dev/test), set ?async=false.
Auth: X-API-Key header
"""

import os
import secrets
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Header, UploadFile, Query, Request
from pydantic import BaseModel

router = APIRouter()

MAX_INGEST_BYTES = int(os.environ.get("MAX_INGEST_BYTES", str(5 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.environ.get("ALLOWED_INGEST_EXTENSIONS", ".txt,.md,.csv").split(",")
    if ext.strip()
}
ALLOWED_CONTENT_TYPES = {
    ct.strip().lower()
    for ct in os.environ.get(
        "ALLOWED_INGEST_CONTENT_TYPES",
        "text/plain,text/markdown,text/csv,application/octet-stream",
    ).split(",")
    if ct.strip()
}


# ── Response schema ────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    doc_id:             str
    status:             str       # ingested | quarantined | rejected | queued
    reason:             Optional[str] = None
    chunks_stored:      int
    sensitivity_class:  str
    pii_entities_found: List[str]
    text_modified:      bool
    async_task_id:      Optional[str] = None


# ── Auth ───────────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    expected = os.environ.get("API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API key is not configured")
    if not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


async def _read_limited_text_file(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    content_type = (file.content_type or "application/octet-stream").lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")

    content_bytes = await file.read(MAX_INGEST_BYTES + 1)
    if len(content_bytes) > MAX_INGEST_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {MAX_INGEST_BYTES} bytes.",
        )
    if not content_bytes.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return content_bytes.decode("utf-8", errors="replace")


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/file", response_model=IngestResponse)
async def ingest_file(
    request:    Request,
    file:       UploadFile = File(..., description="Plain text file (.txt, .md, .csv)"),
    tenant_id:  str        = Form(default="default"),
    acl_roles:  str        = Form(default="employee",
                                  description="Comma-separated roles, e.g. employee,manager"),
    run_async:  bool       = Query(default=True, alias="async",
                                   description="Queue via Celery (true) or run synchronously (false)"),
    _key:       str        = Depends(verify_api_key),
):
    """
    Ingest a plain-text file through the full privacy pipeline.

    Async (default): queues a Celery task → returns immediately with task_id.
    Sync (?async=false): runs pipeline inline → returns full result.
    """
    content = await _read_limited_text_file(file)
    metadata = {
        "source":   file.filename,
        "filename": file.filename,
        "content_type": file.content_type or "text/plain",
    }
    roles = [r.strip() for r in acl_roles.split(",") if r.strip()] or ["employee"]

    if run_async:
        # Queue via Celery worker
        try:
            from aegisVault.worker import ingest_document_task
            task = ingest_document_task.delay(content, metadata, tenant_id, roles)
            return IngestResponse(
                doc_id=metadata.get("source", "unknown"),
                status="queued",
                chunks_stored=0,
                sensitivity_class="UNKNOWN",
                pii_entities_found=[],
                text_modified=False,
                async_task_id=task.id,
            )
        except Exception:
            # Celery unavailable — fall through to sync
            pass

    # Synchronous ingestion
    pipeline = getattr(request.app.state, "ingestion_pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Ingestion pipeline not ready")

    result = pipeline.ingest(
        text=content,
        metadata=metadata,
        tenant_id=tenant_id,
        acl_roles=roles,
    )

    return IngestResponse(
        doc_id=result.doc_id,
        status=result.status,
        reason=result.reason,
        chunks_stored=result.chunks_stored,
        sensitivity_class=result.sensitivity_class,
        pii_entities_found=result.pii_entities_found,
        text_modified=result.text_modified,
    )


@router.post("/text", response_model=IngestResponse)
async def ingest_text(
    request:    Request,
    text:       str   = Form(..., description="Raw document text"),
    source:     str   = Form(default="manual_input"),
    tenant_id:  str   = Form(default="default"),
    acl_roles:  str   = Form(default="employee"),
    _key:       str   = Depends(verify_api_key),
):
    """Ingest raw text directly (no file upload needed)."""
    pipeline = getattr(request.app.state, "ingestion_pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Ingestion pipeline not ready")

    result = pipeline.ingest(
        text=text,
        metadata={"source": source},
        tenant_id=tenant_id,
        acl_roles=[r.strip() for r in acl_roles.split(",") if r.strip()] or ["employee"],
    )

    return IngestResponse(
        doc_id=result.doc_id,
        status=result.status,
        reason=result.reason,
        chunks_stored=result.chunks_stored,
        sensitivity_class=result.sensitivity_class,
        pii_entities_found=result.pii_entities_found,
        text_modified=result.text_modified,
    )
