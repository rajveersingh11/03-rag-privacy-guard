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
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, Request
from pydantic import BaseModel

from aegisVault.app.deps import verify_api_key, limiter
from aegisVault.utils.common import get_logger

logger = get_logger(__name__)

router = APIRouter()

MAX_INGEST_BYTES = int(os.environ.get("MAX_INGEST_BYTES", str(5 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.environ.get("ALLOWED_INGEST_EXTENSIONS", ".txt,.md,.csv,.pdf").split(",")
    if ext.strip()
}
ALLOWED_CONTENT_TYPES = {
    ct.strip().lower()
    for ct in os.environ.get(
        "ALLOWED_INGEST_CONTENT_TYPES",
        "text/plain,text/markdown,text/csv,application/pdf,application/octet-stream",
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


# ── Hooks ──────────────────────────────────────────────────────────────

def scan_file(path: str) -> bool:
    """Stub for virus/malware scanning (e.g. ClamAV)."""
    logger.warning("No virus scanner configured for file uploads. Skipping scan.")
    return True


async def _read_limited_text_file(file: UploadFile) -> str:
    filename = Path(file.filename or "unknown").name
    suffix = Path(filename).suffix.lower()
    content_type = (file.content_type or "application/octet-stream").lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")

    scan_file(filename)

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
@limiter.limit("10/minute")
async def ingest_file(
    request:    Request,
    file:       UploadFile = File(..., description="Plain text file (.txt, .md, .csv, .pdf)"),
    tenant_id:  str        = Form(default="default", pattern=r"^[a-zA-Z0-9_\-]{1,64}$"),
    acl_roles:  str        = Form(default="employee",
                                  description="Comma-separated roles, e.g. employee,manager"),
    run_async:  bool       = Query(default=True, alias="async",
                                   description="Queue via Celery (true) or run synchronously (false)"),
    _key:       str        = Depends(verify_api_key),
):
    """
    Ingest a file through the full privacy pipeline.
    Async (default): queues a Celery task → returns immediately with task_id.
    Sync (?async=false): runs pipeline inline → returns full result.
    """
    content = await _read_limited_text_file(file)
    safe_filename = Path(file.filename or "unknown").name
    metadata = {
        "source":   safe_filename,
        "filename": safe_filename,
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

    import asyncio
    result = await asyncio.to_thread(
        pipeline.ingest,
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
@limiter.limit("10/minute")
async def ingest_text(
    request:    Request,
    text:       str   = Form(..., description="Raw document text", min_length=3),
    source:     str   = Form(default="manual_input"),
    tenant_id:  str   = Form(default="default", pattern=r"^[a-zA-Z0-9_\-]{1,64}$"),
    acl_roles:  str   = Form(default="employee"),
    _key:       str   = Depends(verify_api_key),
):
    """Ingest raw text directly (no file upload needed)."""
    pipeline = getattr(request.app.state, "ingestion_pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Ingestion pipeline not ready")

    import asyncio
    result = await asyncio.to_thread(
        pipeline.ingest,
        text=text,
        metadata={"source": Path(source).name},
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
