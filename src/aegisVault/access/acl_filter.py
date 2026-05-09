"""
ACL Filter — Chunk-Level Enforcement
--------------------------------------
Wraps ChromaDB retrieval to apply RBAC filtering
BEFORE chunks reach the inference pipeline.

Separates retrieval (vectorstore.similarity_search)
from access control (RBACPolicy.filter_chunks) cleanly.
"""

from typing import List, Dict, Any, Tuple, Optional

from src.aegisVault.access.rbac import RBACPolicy
from src.aegisVault.utils.common import get_logger

logger = get_logger(__name__)


class ACLFilter:
    """
    Wraps a vectorstore and applies RBAC filtering on results.
    Returns only chunks the requesting user is authorized to see.
    """

    def __init__(self, vectorstore, rbac: Optional[RBACPolicy] = None):
        self.vectorstore = vectorstore
        self.rbac = rbac or RBACPolicy(on_violation="drop")

    def retrieve(
        self,
        query:      str,
        user_id:    str,
        user_roles: List[str],
        tenant_id:  str = "default",
        top_k:      int = 5,
        fetch_k:    int = 20,           # fetch more, filter down to top_k
    ) -> Dict[str, Any]:
        """
        Retrieves top_k authorized chunks for the query.

        Steps:
          1. Fetch fetch_k candidates from vectorstore
          2. Apply RBAC filter (tenant + clearance + ACL)
          3. Return top_k of what remains

        Returns:
            {
              "chunks":        list of authorized (doc, score) tuples,
              "blocked_count": int,
              "user_clearance": str,
            }
        """
        # Step 1: Raw vector search (over-fetch to account for filtering)
        raw: List[Tuple] = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=fetch_k
        )

        # Step 2: Convert to dict format for RBAC filter
        raw_dicts = [
            {
                "page_content": doc.page_content,
                "metadata":     doc.metadata,
                "score":        float(score),
            }
            for doc, score in raw
        ]

        # Step 3: Apply RBAC
        rbac_result = self.rbac.filter_chunks(
            chunks=raw_dicts,
            user_id=user_id,
            user_roles=user_roles,
            tenant_id=tenant_id,
        )

        allowed = rbac_result["allowed_chunks"][:top_k]

        logger.info(
            f"ACLFilter: fetched={len(raw)} filtered={len(allowed)} "
            f"blocked={rbac_result['blocked_count']} "
            f"user={user_id} clearance={rbac_result['user_clearance']}"
        )

        return {
            "chunks":          allowed,
            "blocked_count":   rbac_result["blocked_count"],
            "user_clearance":  rbac_result["user_clearance"],
            "violations":      rbac_result["violations"],
        }


# ══════════════════════════════════════════════════════════════════════
# __main__ — Test ACLFilter with a mock vectorstore
#
# Usage:
#   python -m aegisVault.access.acl_filter
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from unittest.mock import MagicMock

    print("\n" + "═" * 55)
    print("  AegisVault — ACL Filter Test")
    print("═" * 55)

    # Mock vectorstore with mixed-sensitivity chunks
    mock_vs = MagicMock()
    from types import SimpleNamespace

    def make_doc(chunk_id, content, sensitivity, tenant="org1", roles=None):
        doc = SimpleNamespace()
        doc.page_content = content
        doc.metadata = {
            "chunk_id":          chunk_id,
            "sensitivity_class": sensitivity,
            "tenant_id":         tenant,
            "acl_roles":         roles or [],
        }
        return doc

    mock_vs.similarity_search_with_relevance_scores.return_value = [
        (make_doc("c1", "Our return policy allows 30-day refunds.",   "PUBLIC"),       0.91),
        (make_doc("c2", "Internal HR policy — grade bands 1-5.",      "INTERNAL"),     0.87),
        (make_doc("c3", "Executive salary review Q3 2026.",           "CONFIDENTIAL"), 0.82),
        (make_doc("c4", "Board M&A discussion — RESTRICTED.",         "RESTRICTED"),   0.79),
        (make_doc("c5", "Other company data.",                        "PUBLIC", "org2"), 0.75),
    ]

    acl = ACLFilter(mock_vs)

    roles_to_test = [
        ("employee",  ["employee"]),
        ("manager",   ["manager"]),
        ("executive", ["executive"]),
    ]

    for label, roles in roles_to_test:
        result = acl.retrieve(
            query="What is our refund policy?",
            user_id="u001", user_roles=roles,
            tenant_id="org1", top_k=5,
        )
        print(f"\n  Role={label:<12} clearance={result['user_clearance']:<14} "
              f"allowed={len(result['chunks'])}  blocked={result['blocked_count']}")
        for c in result["chunks"]:
            sens = c["metadata"]["sensitivity_class"]
            print(f"    ✅  [{sens:<14}] {c['page_content'][:55]}")
        for v in result["violations"]:
            print(f"    ✗   [{v.get('sensitivity','?'):<14}] blocked — {v['reason']}")

    print()