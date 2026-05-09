"""
POST /query — Fully guarded RAG query endpoint
------------------------------------------------
Passes every request through all 6 security layers
via InferencePipeline.query().

Auth: X-API-Key header (set API_KEY in .env)
"""

import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────────

class QueryRequest(BaseModel):
    query:      str             = Field(..., min_length=1, max_length=2000,
                                        example="What is our refund policy?")
    user_id:    str             = Field(..., example="u001")
    user_roles: List[str]       = Field(default=["employee"],
                                        example=["employee"])
    tenant_id:  str             = Field(default="default", example="acme_corp")
    top_k:      int             = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    trace_id:       str
    response:       str
    chunks_used:    int
    rbac_blocked:   int
    pii_redacted:   int
    canary_leaked:  bool
    latency_ms:     int


# ── Auth dependency ────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    expected = os.environ.get("API_KEY", "dev-key")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ── Endpoint ───────────────────────────────────────────────────────────

@router.post("", response_model=QueryResponse)
def run_query(
    req: QueryRequest,
    _key: str = Depends(verify_api_key),
):
    """
    Run a fully guarded RAG query through all 6 security layers:

    - Layer 2: Semantic router (injection + jailbreak detection)
    - Layer 3: RBAC retrieval filter (sensitivity class + tenant isolation)
    - Layer 4: Clean context construction
    - Layer 5: Output sanitizer (PII scrub + canary check)
    - Layer 6: Privacy-safe audit log
    """
    from aegisVault.app.main import state

    pipeline = state.get("inference_pipeline")
    if not pipeline:
        raise HTTPException(status_code=503, detail="Inference pipeline not ready")

    result = pipeline.query(
        user_query=req.query,
        user_id=req.user_id,
        user_roles=req.user_roles,
        tenant_id=req.tenant_id,
        top_k=req.top_k,
    )

    return QueryResponse(
        trace_id=result.trace_id,
        response=result.safe_response,
        chunks_used=result.chunks_used,
        rbac_blocked=result.rbac_blocked,
        pii_redacted=result.pii_redacted,
        canary_leaked=result.canary_leaked,
        latency_ms=result.latency_ms,
    )