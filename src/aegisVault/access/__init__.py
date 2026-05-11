"""
AegisVault Access Control
--------------------------
Layer 3 — Role-Based Access Control + ACL chunk filtering.

Usage:
    from aegisVault.access import RBACPolicy, ACLFilter

    policy = RBACPolicy(on_violation="drop")
    acl    = ACLFilter(vectorstore, rbac=policy)
    result = acl.retrieve(query, user_id, user_roles, tenant_id)
"""

from aegisVault.access.rbac       import RBACPolicy
from aegisVault.access.acl_filter import ACLFilter

__all__ = ["RBACPolicy", "ACLFilter"]