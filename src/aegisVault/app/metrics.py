import os
from prometheus_client import Counter, Histogram

aegis_queries_total = Counter(
    "aegis_queries_total",
    "Total queries processed",
    ["action", "tenant_id"]
)

aegis_pii_entities_total = Counter(
    "aegis_pii_entities_total",
    "Total PII entities found",
    ["entity_type", "layer"]
)

aegis_rbac_blocked_total = Counter(
    "aegis_rbac_blocked_total",
    "Total chunks blocked by RBAC",
    ["reason", "tenant_id"]
)

aegis_query_latency_seconds = Histogram(
    "aegis_query_latency_seconds",
    "Query processing latency in seconds",
)

aegis_canary_leak_total = Counter(
    "aegis_canary_leak_total",
    "Total canary token leaks detected",
)

aegis_dp_budget_exceeded_total = Counter(
    "aegis_dp_budget_exceeded_total",
    "Total DP budget exceeded events",
)

aegis_llm_circuit_open_total = Counter(
    "aegis_llm_circuit_open_total",
    "Total times the LLM circuit breaker opened",
)