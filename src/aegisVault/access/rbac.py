"""
RBAC — Role-Based Access Control
----------------------------------
Resolves a user's clearance level from their roles and enforces
sensitivity-class-based document access at retrieval time.

Used by:
  - InferencePipeline  (filters chunks before LLM sees them)
  - acl_filter.py      (per-chunk enforcement)
  - app/routers/query  (passes user_roles into pipeline)
"""

from typing import List, Dict, Any

from src.aegisVault.constants import SENSITIVITY_LEVELS, ROLE_CLEARANCE
from src.aegisVault.utils.common import get_logger, sensitivity_index

logger = get_logger(__name__)


class RBACPolicy:
    """
    Resolves clearance and enforces access rules.

    Sensitivity order (low → high):
      PUBLIC → INTERNAL → CONFIDENTIAL → RESTRICTED → TOP_SECRET

    A user with clearance CONFIDENTIAL can access:
      PUBLIC, INTERNAL, CONFIDENTIAL  — but NOT RESTRICTED or TOP_SECRET.
    """

    def __init__(self, on_violation: str = "drop"):
        """
        Args:
            on_violation: "drop" | "redact" | "audit_only"
                drop       — silently remove the chunk (default, most secure)
                redact     — replace content with [REDACTED] placeholder
                audit_only — allow but log the violation
        """
        self.on_violation = on_violation

    # ── Public API ─────────────────────────────────────────────────────

    def resolve_clearance(self, roles: List[str]) -> str:
        """Return the highest sensitivity level the user's roles permit."""
        levels = [
            SENSITIVITY_LEVELS.index(ROLE_CLEARANCE.get(r, "PUBLIC"))
            for r in roles
            if r in ROLE_CLEARANCE
        ]
        if not levels:
            return "PUBLIC"
        return SENSITIVITY_LEVELS[max(levels)]

    def can_access(
        self,
        user_roles:        List[str],
        chunk_sensitivity: str,
        chunk_acl_roles:   List[str] = None,
        user_id:           str = None,
        chunk_acl_users:   List[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns access decision for a single chunk.

        Returns:
            {
              "allowed":   bool,
              "reason":    str,
              "clearance": str,
            }
        """
        clearance     = self.resolve_clearance(user_roles)
        user_level    = sensitivity_index(clearance)
        chunk_level   = sensitivity_index(chunk_sensitivity or "PUBLIC")

        # ── Clearance check ─────────────────────────────────────────
        if chunk_level > user_level:
            return {
                "allowed":   False,
                "reason":    f"clearance_insufficient: {clearance} < {chunk_sensitivity}",
                "clearance": clearance,
            }

        # ── Explicit ACL role check ──────────────────────────────────
        if chunk_acl_roles:
            if not any(r in chunk_acl_roles for r in user_roles):
                return {
                    "allowed":   False,
                    "reason":    "acl_role_mismatch",
                    "clearance": clearance,
                }

        # ── Explicit ACL user check ──────────────────────────────────
        if chunk_acl_users and user_id:
            if user_id not in chunk_acl_users:
                return {
                    "allowed":   False,
                    "reason":    "acl_user_mismatch",
                    "clearance": clearance,
                }

        return {"allowed": True, "reason": "ok", "clearance": clearance}

    def filter_chunks(
        self,
        chunks:     List[Dict[str, Any]],
        user_id:    str,
        user_roles: List[str],
        tenant_id:  str = "default",
    ) -> Dict[str, Any]:
        """
        Filter a list of retrieved chunks by RBAC policy.
        Each chunk dict must have a 'metadata' key.

        Returns:
            {
              "allowed_chunks":  list of permitted chunks,
              "blocked_count":   int,
              "user_clearance":  str,
              "violations":      list of blocked chunk details,
            }
        """
        clearance  = self.resolve_clearance(user_roles)
        allowed    = []
        blocked    = []
        violations = []

        for chunk in chunks:
            meta = chunk.get("metadata", {})

            # Tenant boundary — hard reject cross-tenant
            if meta.get("tenant_id", "default") != tenant_id:
                blocked.append(chunk)
                violations.append({
                    "chunk_id": meta.get("chunk_id", "unknown"),
                    "reason":   "tenant_boundary",
                })
                continue

            decision = self.can_access(
                user_roles=user_roles,
                chunk_sensitivity=meta.get("sensitivity_class", "PUBLIC"),
                chunk_acl_roles=meta.get("acl_roles", []),
                user_id=user_id,
                chunk_acl_users=meta.get("acl_users", []),
            )

            if decision["allowed"]:
                allowed.append(chunk)
            else:
                if self.on_violation == "redact":
                    redacted = dict(chunk)
                    redacted["page_content"] = "[REDACTED — INSUFFICIENT CLEARANCE]"
                    allowed.append(redacted)
                elif self.on_violation == "audit_only":
                    allowed.append(chunk)

                blocked.append(chunk)
                violations.append({
                    "chunk_id": meta.get("chunk_id", "unknown"),
                    "reason":   decision["reason"],
                    "sensitivity": meta.get("sensitivity_class"),
                })
                logger.debug(
                    f"RBAC blocked chunk '{meta.get('chunk_id')}' "
                    f"— {decision['reason']}"
                )

        if violations:
            logger.info(
                f"RBAC: {len(allowed)} allowed, {len(blocked)} blocked "
                f"| user={user_id} clearance={clearance}"
            )

        return {
            "allowed_chunks":  allowed,
            "blocked_count":   len(blocked),
            "user_clearance":  clearance,
            "violations":      violations,
        }


# ══════════════════════════════════════════════════════════════════════
# __main__ — Test RBAC policy locally
#
# Usage:
#   python -m aegisVault.access.rbac
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═" * 55)
    print("  AegisVault — RBAC Policy Test")
    print("═" * 55)

    policy = RBACPolicy(on_violation="drop")

    # Test matrix: user roles vs chunk sensitivity
    test_cases = [
        # (user_roles,        chunk_sensitivity, expected)
        (["employee"],        "PUBLIC",          True),
        (["employee"],        "INTERNAL",        True),
        (["employee"],        "CONFIDENTIAL",    False),
        (["employee"],        "RESTRICTED",      False),
        (["manager"],         "CONFIDENTIAL",    True),
        (["manager"],         "RESTRICTED",      False),
        (["executive"],       "RESTRICTED",      True),
        (["executive"],       "TOP_SECRET",      False),
        (["admin"],           "TOP_SECRET",      True),
        (["anonymous"],       "INTERNAL",        False),
    ]

    print(f"\n  {'Roles':<20} {'Chunk Class':<16} {'Expected':<10} {'Got':<10} {'Pass'}")
    print(f"  {'─'*20} {'─'*16} {'─'*10} {'─'*10} {'─'*5}")

    all_pass = True
    for roles, chunk_class, expected in test_cases:
        decision = policy.can_access(roles, chunk_class)
        got      = decision["allowed"]
        passed   = got == expected
        icon     = "✅" if passed else "❌"
        if not passed:
            all_pass = False
        print(f"  {str(roles):<20} {chunk_class:<16} {str(expected):<10} {str(got):<10} {icon}")

    print(f"\n  {'✅ All tests passed' if all_pass else '❌ Some tests FAILED'}")

    # Test filter_chunks
    print(f"\n{'─'*55}")
    print("  filter_chunks() demo — employee filtering 4 chunks")
    print(f"{'─'*55}")

    chunks = [
        {"page_content": "Public FAQ content",
         "metadata": {"chunk_id": "c1", "sensitivity_class": "PUBLIC",
                      "tenant_id": "org1", "acl_roles": []}},
        {"page_content": "Internal policy doc",
         "metadata": {"chunk_id": "c2", "sensitivity_class": "INTERNAL",
                      "tenant_id": "org1", "acl_roles": []}},
        {"page_content": "Confidential salary data",
         "metadata": {"chunk_id": "c3", "sensitivity_class": "CONFIDENTIAL",
                      "tenant_id": "org1", "acl_roles": []}},
        {"page_content": "Other tenant doc",
         "metadata": {"chunk_id": "c4", "sensitivity_class": "PUBLIC",
                      "tenant_id": "org2", "acl_roles": []}},  # cross-tenant
    ]

    result = policy.filter_chunks(
        chunks=chunks, user_id="u001",
        user_roles=["employee"], tenant_id="org1",
    )
    print(f"\n  Clearance  : {result['user_clearance']}")
    print(f"  Allowed    : {len(result['allowed_chunks'])} chunks")
    print(f"  Blocked    : {result['blocked_count']} chunks")
    for v in result["violations"]:
        print(f"  ✗ {v['chunk_id']} — {v['reason']}")
    print()