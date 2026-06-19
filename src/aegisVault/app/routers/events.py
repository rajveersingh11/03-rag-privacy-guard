"""
GET /events — Retrieve security events and audit logs from the database
----------------------------------------------------------------------
Serves real database security events to the frontend.
"""

import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from aegisVault.app.deps import verify_api_key
from aegisVault.db.session import get_db
from aegisVault.utils.common import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
def get_security_events(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _key: str = Depends(verify_api_key),
) -> List[Dict[str, Any]]:
    events = []

    # 1. Fetch queries from audit_log
    try:
        query_audit = text("""
            SELECT id, timestamp, tenant_id, user_id,
                   route_action, route_category, query, response, chunks_used, rbac_blocked, pii_redacted, canary_leaked
            FROM audit_log
            ORDER BY timestamp DESC LIMIT :limit
        """)
        res_audit = db.execute(query_audit, {"limit": limit}).fetchall()
        for r in res_audit:
            # Determine risk
            risk = "low"
            if r.canary_leaked:
                risk = "critical"
            elif r.route_action == "block" or r.rbac_blocked > 0:
                risk = "high"
            elif r.pii_redacted > 0:
                risk = "medium"

            status = "blocked" if (r.route_action == "block" or r.rbac_blocked > 0) else "success"
            
            # Format stamp
            time_str = r.timestamp.isoformat() if hasattr(r.timestamp, "isoformat") else str(r.timestamp)
            if not time_str.endswith("Z") and "T" in time_str:
                time_str += "Z"

            details = f"Query: {r.query[:120]}... | Chunks: {r.chunks_used} (Blocked: {r.rbac_blocked}) | PII Redacted: {r.pii_redacted}"
            if r.canary_leaked:
                details += " [CANARY LEAK DETECTED]"

            events.append({
                "id": r.id,
                "time": time_str,
                "type": "query",
                "tenant": r.tenant_id,
                "user": r.user_id,
                "status": status,
                "risk": risk,
                "details": details,
                "traceOrDocId": r.id
            })
    except Exception as e:
        logger.error(f"Error querying audit_log for events: {e}")

    # 2. Fetch injection attempts
    try:
        query_inject = text("""
            SELECT id, detected_at, tenant_id, user_id, raw_query, category, confidence
            FROM injection_attempts
            ORDER BY detected_at DESC LIMIT :limit
        """)
        res_inject = db.execute(query_inject, {"limit": limit}).fetchall()
        for r in res_inject:
            time_str = r.detected_at.isoformat() if hasattr(r.detected_at, "isoformat") else str(r.detected_at)
            if not time_str.endswith("Z") and "T" in time_str:
                time_str += "Z"

            events.append({
                "id": r.id,
                "time": time_str,
                "type": "query",
                "tenant": r.tenant_id or "default",
                "user": r.user_id or "unknown",
                "status": "blocked",
                "risk": "high",
                "details": f"Blocked prompt injection/jailbreak attempt (Category: {r.category}, Confidence: {r.confidence:.2f}) Query: {r.raw_query[:100]}...",
                "traceOrDocId": r.id
            })
    except Exception as e:
        logger.error(f"Error querying injection_attempts for events: {e}")

    # 3. Fetch ingestion log
    try:
        query_ingest = text("""
            SELECT id, ingested_at, tenant_id, doc_id, source, status, reason, chunks_stored, sensitivity_class, pii_entities_found, text_modified
            FROM ingestion_log
            ORDER BY ingested_at DESC LIMIT :limit
        """)
        res_ingest = db.execute(query_ingest, {"limit": limit}).fetchall()
        for r in res_ingest:
            t_type = "file_ingest"
            if r.source == "manual_input":
                t_type = "text_ingest"

            risk = "low"
            if r.status == "quarantined":
                risk = "critical"
            elif r.status == "skipped":
                risk = "medium"
            elif r.text_modified:
                risk = "medium"

            status = "success"
            if r.status == "quarantined":
                status = "blocked"
            elif r.status == "skipped":
                status = "warning"

            time_str = r.ingested_at.isoformat() if hasattr(r.ingested_at, "isoformat") else str(r.ingested_at)
            if not time_str.endswith("Z") and "T" in time_str:
                time_str += "Z"

            details = f"Source: {r.source} | Chunks: {r.chunks_stored} | Sensitivity: {r.sensitivity_class} | Status: {r.status}"
            if r.reason:
                details += f" (Reason: {r.reason})"

            events.append({
                "id": r.id,
                "time": time_str,
                "type": t_type,
                "tenant": r.tenant_id,
                "user": "system",
                "status": status,
                "risk": risk,
                "details": details,
                "traceOrDocId": r.doc_id
            })
    except Exception as e:
        logger.error(f"Error querying ingestion_log for events: {e}")

    # Sort combined events by timestamp descending
    events.sort(key=lambda x: x["time"], reverse=True)
    return events[:limit]
