"""
Discovering Hidden Patterns in Infrastructure Monitoring Data
==============================================================

This example shows how Hyper3's rule system discovers non-obvious
relationships in operational data: multi-hop dependency chains,
co-occurrence causal patterns, service abstractions from similar
profiles, and structural analogies via embedding arithmetic.

The graph models a production microservices deployment with 125 nodes
(services, hosts, metrics, alerts, deployments, external dependencies,
correlations) and 229 edges across 10 relationship types. Manually
placed correlation patterns are embedded for the rule engine to
recover automatically.

Run with:
    .venv/bin/python examples/showcase/reasoning/advanced_rules/advanced_rules.py
"""

from __future__ import annotations

from collections import Counter

from hyper3 import (
    GeneralizationRule,
    HashEmbeddingProvider,
    HubInferenceRule,
    HypergraphMemory,
    InverseRule,
    StructuralProjectionRule,
    TransitiveRule,
)


def _label(mem: HypergraphMemory, nid: str) -> str:
    node = mem.engine.graph.get_node(nid)
    return node.label if node else nid[:8]


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Infrastructure Graph Construction
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Infrastructure Graph Construction")
    print("=" * 70)

    services = {
        "svc-auth": {"response_time_p95": 45, "error_rate": 0.02, "throughput": 8000, "team": "platform", "tier": "critical"},
        "svc-user": {"response_time_p95": 50, "error_rate": 0.02, "throughput": 8000, "team": "platform", "tier": "critical"},
        "svc-audit": {"response_time_p95": 35, "error_rate": 0.02, "throughput": 8000, "team": "platform", "tier": "critical"},
        "svc-order": {"response_time_p95": 120, "error_rate": 0.05, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-payment": {"response_time_p95": 100, "error_rate": 0.05, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-checkout": {"response_time_p95": 150, "error_rate": 0.05, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-email": {"response_time_p95": 200, "error_rate": 0.01, "throughput": 10000, "team": "messaging", "tier": "standard"},
        "svc-sms": {"response_time_p95": 180, "error_rate": 0.01, "throughput": 10000, "team": "messaging", "tier": "standard"},
        "svc-push": {"response_time_p95": 150, "error_rate": 0.01, "throughput": 10000, "team": "messaging", "tier": "standard"},
        "svc-queue": {"response_time_p95": 10, "error_rate": 0.001, "throughput": 50000, "team": "infra", "tier": "critical"},
        "svc-cache": {"response_time_p95": 5, "error_rate": 0.001, "throughput": 50000, "team": "infra", "tier": "critical"},
        "svc-scheduler": {"response_time_p95": 15, "error_rate": 0.001, "throughput": 50000, "team": "infra", "tier": "critical"},
        "svc-analytics": {"response_time_p95": 300, "error_rate": 0.03, "throughput": 2000, "team": "data", "tier": "standard"},
        "svc-recommendation": {"response_time_p95": 250, "error_rate": 0.03, "throughput": 2000, "team": "data", "tier": "standard"},
        "svc-search": {"response_time_p95": 80, "error_rate": 0.03, "throughput": 2000, "team": "data", "tier": "standard"},
        "svc-api-gateway": {"response_time_p95": 25, "error_rate": 0.01, "throughput": 15000, "team": "platform", "tier": "critical"},
        "svc-notification": {"response_time_p95": 100, "error_rate": 0.02, "throughput": 5000, "team": "messaging", "tier": "standard"},
        "svc-shipping": {"response_time_p95": 200, "error_rate": 0.03, "throughput": 1000, "team": "commerce", "tier": "standard"},
        "svc-review": {"response_time_p95": 80, "error_rate": 0.01, "throughput": 4000, "team": "commerce", "tier": "standard"},
        "svc-catalog": {"response_time_p95": 60, "error_rate": 0.02, "throughput": 6000, "team": "commerce", "tier": "critical"},
        "svc-pricing": {"response_time_p95": 30, "error_rate": 0.01, "throughput": 7000, "team": "commerce", "tier": "critical"},
        "svc-promo": {"response_time_p95": 90, "error_rate": 0.04, "throughput": 2000, "team": "marketing", "tier": "standard"},
        "svc-loyalty": {"response_time_p95": 110, "error_rate": 0.03, "throughput": 1500, "team": "marketing", "tier": "standard"},
        "svc-support": {"response_time_p95": 250, "error_rate": 0.05, "throughput": 800, "team": "operations", "tier": "standard"},
        "svc-config": {"response_time_p95": 20, "error_rate": 0.001, "throughput": 12000, "team": "infra", "tier": "critical"},
        "svc-feature-flag": {"response_time_p95": 15, "error_rate": 0.001, "throughput": 10000, "team": "infra", "tier": "critical"},
        "svc-billing": {"response_time_p95": 80, "error_rate": 0.04, "throughput": 2500, "team": "commerce", "tier": "critical"},
        "svc-invoice": {"response_time_p95": 90, "error_rate": 0.03, "throughput": 2000, "team": "commerce", "tier": "standard"},
        "svc-subscription": {"response_time_p95": 70, "error_rate": 0.02, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-content": {"response_time_p95": 100, "error_rate": 0.02, "throughput": 4500, "team": "media", "tier": "standard"},
        "svc-media": {"response_time_p95": 150, "error_rate": 0.03, "throughput": 3000, "team": "media", "tier": "standard"},
        "svc-webhook": {"response_time_p95": 40, "error_rate": 0.01, "throughput": 8000, "team": "infra", "tier": "standard"},
        "svc-docs": {"response_time_p95": 120, "error_rate": 0.01, "throughput": 1000, "team": "platform", "tier": "standard"},
        "svc-cart": {"response_time_p95": 80, "error_rate": 0.04, "throughput": 3500, "team": "commerce", "tier": "critical"},
        "svc-inventory": {"response_time_p95": 60, "error_rate": 0.02, "throughput": 5000, "team": "commerce", "tier": "critical"},
    }
    for name, data in services.items():
        mem.add(name, data=data)

    for i in range(1, 21):
        mem.add(
            f"host-prod-{i:02d}",
            data={"cpu_avg": 40 + i, "memory_avg": 55 + i, "disk_usage": 25 + i * 2, "os": "linux" if i % 3 != 0 else "ubuntu"},
        )

    for name, data in {
        "metric-latency-spike-api": {"severity": "high", "pattern_type": "spike"},
        "metric-latency-spike-auth": {"severity": "medium", "pattern_type": "spike"},
        "metric-error-burst-order": {"severity": "high", "pattern_type": "burst"},
        "metric-error-burst-payment": {"severity": "critical", "pattern_type": "burst"},
        "metric-cpu-spike-prod-01": {"severity": "high", "pattern_type": "threshold"},
        "metric-cpu-spike-prod-02": {"severity": "medium", "pattern_type": "threshold"},
        "metric-memory-pressure-prod-03": {"severity": "high", "pattern_type": "gradual"},
        "metric-disk-threshold-prod-04": {"severity": "medium", "pattern_type": "threshold"},
        "metric-throughput-drop-search": {"severity": "high", "pattern_type": "drop"},
        "metric-timeout-gateway": {"severity": "critical", "pattern_type": "spike"},
        "metric-connection-pool-exhaust": {"severity": "high", "pattern_type": "gradual"},
        "metric-queue-backlog": {"severity": "medium", "pattern_type": "gradual"},
        "metric-cache-miss-rate": {"severity": "low", "pattern_type": "gradual"},
        "metric-deployment-failure": {"severity": "critical", "pattern_type": "spike"},
        "metric-external-api-slow": {"severity": "medium", "pattern_type": "degradation"},
    }.items():
        mem.add(name, data=data)

    for name, data in {
        "alert-high-latency-api": {"priority": "P1", "category": "performance", "acknowledged": True},
        "alert-auth-failures": {"priority": "P1", "category": "security", "acknowledged": True},
        "alert-order-errors": {"priority": "P2", "category": "errors", "acknowledged": False},
        "alert-payment-declines": {"priority": "P1", "category": "revenue", "acknowledged": True},
        "alert-cpu-critical": {"priority": "P2", "category": "infrastructure", "acknowledged": False},
        "alert-memory-warning": {"priority": "P3", "category": "infrastructure", "acknowledged": True},
        "alert-disk-full": {"priority": "P2", "category": "infrastructure", "acknowledged": False},
        "alert-search-degraded": {"priority": "P2", "category": "performance", "acknowledged": True},
        "alert-gateway-timeout": {"priority": "P1", "category": "availability", "acknowledged": False},
        "alert-connection-leak": {"priority": "P2", "category": "infrastructure", "acknowledged": True},
        "alert-queue-overflow": {"priority": "P2", "category": "performance", "acknowledged": False},
        "alert-cache-cold": {"priority": "P3", "category": "performance", "acknowledged": True},
        "alert-deploy-rollback": {"priority": "P1", "category": "deployment", "acknowledged": True},
        "alert-external-degradation": {"priority": "P2", "category": "third_party", "acknowledged": False},
        "alert-cascading-failure": {"priority": "P0", "category": "incident", "acknowledged": False},
    }.items():
        mem.add(name, data=data)

    for name, data in {
        "deploy-v2.3.1": {"version": "2.3.1", "changelist_size": 12, "rollback": False},
        "deploy-v2.3.2": {"version": "2.3.2", "changelist_size": 8, "rollback": False},
        "deploy-v2.3.3": {"version": "2.3.3", "changelist_size": 3, "rollback": False},
        "deploy-v2.4.0": {"version": "2.4.0", "changelist_size": 45, "rollback": True},
        "deploy-v2.4.1": {"version": "2.4.1", "changelist_size": 5, "rollback": False},
        "deploy-v2.5.0": {"version": "2.5.0", "changelist_size": 30, "rollback": False},
        "deploy-v2.5.1": {"version": "2.5.1", "changelist_size": 7, "rollback": False},
        "deploy-v2.6.0": {"version": "2.6.0", "changelist_size": 22, "rollback": True},
        "deploy-v3.0.0": {"version": "3.0.0", "changelist_size": 80, "rollback": False},
        "deploy-v3.0.1": {"version": "3.0.1", "changelist_size": 4, "rollback": False},
        "deploy-v3.1.0": {"version": "3.1.0", "changelist_size": 35, "rollback": False},
        "deploy-v3.1.1": {"version": "3.1.1", "changelist_size": 6, "rollback": False},
        "deploy-v3.2.0": {"version": "3.2.0", "changelist_size": 18, "rollback": False},
        "deploy-hotfix-001": {"version": "hotfix-001", "changelist_size": 2, "rollback": False},
        "deploy-hotfix-002": {"version": "hotfix-002", "changelist_size": 3, "rollback": False},
    }.items():
        mem.add(name, data=data)

    for name, data in {
        "ext-stripe": {"availability": 99.9, "latency": 150},
        "ext-sendgrid": {"availability": 99.5, "latency": 200},
        "ext-aws-s3": {"availability": 99.99, "latency": 50},
        "ext-twilio": {"availability": 99.8, "latency": 180},
        "ext-datadog": {"availability": 99.9, "latency": 100},
        "ext-github": {"availability": 99.5, "latency": 300},
        "ext-slack": {"availability": 99.0, "latency": 250},
        "ext-pagerduty": {"availability": 99.99, "latency": 80},
        "ext-cloudflare": {"availability": 99.99, "latency": 20},
        "ext-elasticsearch": {"availability": 99.8, "latency": 120},
    }.items():
        mem.add(name, data=data)

    for name, data in {
        "corr-api-auth-latency": {"discovery_type": "manual", "confidence": 0.92},
        "corr-order-payment-error": {"discovery_type": "manual", "confidence": 0.88},
        "corr-checkout-cart-fail": {"discovery_type": "manual", "confidence": 0.85},
        "corr-search-index-delay": {"discovery_type": "manual", "confidence": 0.80},
        "corr-cache-queue-backlog": {"discovery_type": "manual", "confidence": 0.90},
        "corr-deploy-cpu-spike": {"discovery_type": "manual", "confidence": 0.87},
        "corr-external-gateway-timeout": {"discovery_type": "manual", "confidence": 0.93},
        "corr-memory-connection-leak": {"discovery_type": "manual", "confidence": 0.82},
        "corr-disk-deploy-failure": {"discovery_type": "manual", "confidence": 0.75},
        "corr-subscription-billing": {"discovery_type": "manual", "confidence": 0.78},
        "corr-media-content-delivery": {"discovery_type": "manual", "confidence": 0.70},
        "corr-notification-push-fail": {"discovery_type": "manual", "confidence": 0.73},
        "corr-analytics-recommendation-drift": {"discovery_type": "manual", "confidence": 0.68},
        "corr-loyalty-promo-abuse": {"discovery_type": "manual", "confidence": 0.65},
        "corr-audit-compliance-gap": {"discovery_type": "manual", "confidence": 0.72},
    }.items():
        mem.add(name, data=data)

    for src, tgt in [
        ("svc-api-gateway", "svc-auth"), ("svc-api-gateway", "svc-catalog"),
        ("svc-api-gateway", "svc-search"), ("svc-api-gateway", "svc-config"),
        ("svc-auth", "svc-user"), ("svc-auth", "svc-audit"), ("svc-auth", "svc-config"),
        ("svc-catalog", "svc-inventory"), ("svc-catalog", "svc-pricing"),
        ("svc-catalog", "svc-review"),
        ("svc-order", "svc-inventory"), ("svc-order", "svc-payment"),
        ("svc-order", "svc-notification"), ("svc-order", "svc-shipping"),
        ("svc-payment", "svc-billing"), ("svc-payment", "ext-stripe"),
        ("svc-checkout", "svc-cart"), ("svc-checkout", "svc-payment"),
        ("svc-checkout", "svc-shipping"), ("svc-checkout", "svc-notification"),
        ("svc-cart", "svc-inventory"), ("svc-cart", "svc-pricing"),
        ("svc-shipping", "svc-notification"), ("svc-shipping", "ext-twilio"),
        ("svc-search", "svc-catalog"), ("svc-search", "ext-elasticsearch"),
        ("svc-analytics", "svc-recommendation"), ("svc-analytics", "svc-user"),
        ("svc-analytics", "svc-order"),
        ("svc-recommendation", "svc-catalog"), ("svc-recommendation", "svc-user"),
        ("svc-recommendation", "svc-order"),
        ("svc-notification", "svc-email"), ("svc-notification", "svc-sms"),
        ("svc-notification", "svc-push"),
        ("svc-billing", "svc-invoice"), ("svc-billing", "svc-subscription"),
        ("svc-billing", "ext-stripe"),
        ("svc-invoice", "svc-subscription"),
        ("svc-email", "ext-sendgrid"), ("svc-sms", "ext-twilio"),
        ("svc-push", "ext-datadog"),
        ("svc-media", "svc-content"), ("svc-media", "ext-aws-s3"),
        ("svc-content", "svc-catalog"),
        ("svc-support", "svc-user"), ("svc-support", "svc-order"),
        ("svc-loyalty", "svc-promo"), ("svc-promo", "svc-pricing"),
        ("svc-docs", "svc-catalog"),
    ]:
        mem.link(src, tgt, label="depends_on")

    for svc, hnum in [
        ("svc-api-gateway", 1), ("svc-auth", 1), ("svc-user", 2),
        ("svc-order", 2), ("svc-payment", 3), ("svc-inventory", 3),
        ("svc-notification", 4), ("svc-search", 4), ("svc-analytics", 5),
        ("svc-recommendation", 5), ("svc-cart", 6), ("svc-checkout", 6),
        ("svc-shipping", 7), ("svc-review", 7), ("svc-catalog", 8),
        ("svc-pricing", 8), ("svc-promo", 9), ("svc-loyalty", 9),
        ("svc-support", 10), ("svc-config", 10), ("svc-feature-flag", 10),
        ("svc-audit", 11), ("svc-billing", 11), ("svc-invoice", 12),
        ("svc-subscription", 12), ("svc-content", 13), ("svc-media", 13),
        ("svc-email", 14), ("svc-sms", 14), ("svc-push", 14),
        ("svc-scheduler", 15), ("svc-webhook", 15), ("svc-queue", 16),
        ("svc-cache", 16), ("svc-docs", 17),
    ]:
        mem.link(svc, f"host-prod-{hnum:02d}", label="deployed_to")

    for src, tgt in [
        ("metric-latency-spike-api", "alert-high-latency-api"),
        ("metric-latency-spike-api", "alert-cascading-failure"),
        ("metric-latency-spike-auth", "alert-auth-failures"),
        ("metric-error-burst-order", "alert-order-errors"),
        ("metric-error-burst-order", "alert-cascading-failure"),
        ("metric-error-burst-payment", "alert-payment-declines"),
        ("metric-error-burst-payment", "alert-cascading-failure"),
        ("metric-cpu-spike-prod-01", "alert-cpu-critical"),
        ("metric-cpu-spike-prod-02", "alert-cpu-critical"),
        ("metric-memory-pressure-prod-03", "alert-memory-warning"),
        ("metric-disk-threshold-prod-04", "alert-disk-full"),
        ("metric-throughput-drop-search", "alert-search-degraded"),
        ("metric-timeout-gateway", "alert-gateway-timeout"),
        ("metric-timeout-gateway", "alert-cascading-failure"),
        ("metric-connection-pool-exhaust", "alert-connection-leak"),
        ("metric-queue-backlog", "alert-queue-overflow"),
        ("metric-cache-miss-rate", "alert-cache-cold"),
        ("metric-deployment-failure", "alert-deploy-rollback"),
        ("metric-external-api-slow", "alert-external-degradation"),
        ("metric-external-api-slow", "alert-cascading-failure"),
    ]:
        mem.link(src, tgt, label="triggers")

    for src, tgt in [
        ("deploy-v2.3.1", "metric-latency-spike-api"),
        ("deploy-v2.3.2", "metric-latency-spike-auth"),
        ("deploy-v2.3.3", "metric-error-burst-order"),
        ("deploy-v2.4.0", "metric-error-burst-payment"),
        ("deploy-v2.4.0", "metric-deployment-failure"),
        ("deploy-v2.4.1", "metric-cpu-spike-prod-01"),
        ("deploy-v2.5.0", "metric-throughput-drop-search"),
        ("deploy-v2.5.1", "metric-timeout-gateway"),
        ("deploy-v2.6.0", "metric-connection-pool-exhaust"),
        ("deploy-v2.6.0", "metric-deployment-failure"),
        ("deploy-v3.0.0", "metric-cpu-spike-prod-02"),
        ("deploy-v3.0.0", "metric-memory-pressure-prod-03"),
        ("deploy-v3.1.0", "metric-cache-miss-rate"),
        ("deploy-v3.1.1", "metric-queue-backlog"),
        ("deploy-v3.2.0", "metric-external-api-slow"),
    ]:
        mem.link(src, tgt, label="causes")

    for src, tgt in [
        ("alert-high-latency-api", "alert-cascading-failure"),
        ("alert-auth-failures", "alert-cascading-failure"),
        ("alert-order-errors", "alert-cascading-failure"),
        ("alert-payment-declines", "alert-cascading-failure"),
        ("alert-cpu-critical", "alert-cascading-failure"),
        ("alert-gateway-timeout", "alert-cascading-failure"),
        ("alert-external-degradation", "alert-cascading-failure"),
        ("metric-latency-spike-auth", "metric-latency-spike-api"),
        ("metric-error-burst-payment", "metric-error-burst-order"),
        ("metric-cpu-spike-prod-02", "metric-cpu-spike-prod-01"),
        ("metric-memory-pressure-prod-03", "metric-cpu-spike-prod-01"),
        ("deploy-v2.3.2", "deploy-v2.3.1"),
        ("deploy-v2.3.3", "deploy-v2.3.2"),
        ("deploy-hotfix-001", "deploy-v2.3.3"),
        ("deploy-hotfix-002", "deploy-hotfix-001"),
    ]:
        mem.link(src, tgt, label="follows")

    for src, tgt in [
        ("alert-cascading-failure", "alert-high-latency-api"),
        ("alert-cascading-failure", "alert-auth-failures"),
        ("alert-cascading-failure", "alert-order-errors"),
        ("alert-cascading-failure", "alert-payment-declines"),
        ("deploy-hotfix-001", "alert-high-latency-api"),
        ("deploy-hotfix-001", "alert-cascading-failure"),
        ("deploy-hotfix-002", "alert-auth-failures"),
        ("deploy-hotfix-002", "alert-deploy-rollback"),
        ("deploy-v3.0.0", "alert-cpu-critical"),
        ("deploy-v3.0.0", "alert-memory-warning"),
        ("deploy-v3.1.0", "alert-search-degraded"),
        ("deploy-v3.1.0", "alert-cache-cold"),
        ("deploy-v3.2.0", "alert-external-degradation"),
        ("deploy-v3.2.0", "alert-connection-leak"),
        ("deploy-v3.0.1", "alert-queue-overflow"),
    ]:
        mem.link(src, tgt, label="mitigates")

    for src, tgt in [
        ("host-prod-01", "metric-latency-spike-api"),
        ("host-prod-01", "metric-cpu-spike-prod-01"),
        ("host-prod-02", "metric-error-burst-order"),
        ("host-prod-03", "metric-error-burst-payment"),
        ("host-prod-03", "metric-cpu-spike-prod-02"),
        ("host-prod-04", "metric-throughput-drop-search"),
        ("host-prod-05", "metric-connection-pool-exhaust"),
        ("host-prod-16", "metric-queue-backlog"),
        ("host-prod-16", "metric-cache-miss-rate"),
        ("host-prod-06", "metric-timeout-gateway"),
    ]:
        mem.link(src, tgt, label="monitors")

    for src, tgt in [
        ("svc-api-gateway", "metric-latency-spike-api"),
        ("svc-api-gateway", "metric-timeout-gateway"),
        ("svc-api-gateway", "metric-external-api-slow"),
        ("svc-auth", "metric-latency-spike-auth"),
        ("svc-order", "metric-error-burst-order"),
        ("svc-payment", "metric-error-burst-payment"),
        ("svc-search", "metric-throughput-drop-search"),
        ("svc-checkout", "metric-timeout-gateway"),
        ("svc-queue", "metric-queue-backlog"),
        ("svc-cache", "metric-cache-miss-rate"),
        ("svc-webhook", "metric-deployment-failure"),
        ("svc-queue", "metric-connection-pool-exhaust"),
        ("svc-inventory", "metric-external-api-slow"),
        ("svc-shipping", "metric-external-api-slow"),
        ("host-prod-01", "metric-memory-pressure-prod-03"),
    ]:
        mem.link(src, tgt, label="affects")

    for corr, alert, metric in [
        ("corr-api-auth-latency", "alert-high-latency-api", "metric-latency-spike-auth"),
        ("corr-order-payment-error", "alert-order-errors", "metric-error-burst-order"),
        ("corr-checkout-cart-fail", "alert-cascading-failure", "metric-error-burst-payment"),
        ("corr-search-index-delay", "alert-search-degraded", "metric-throughput-drop-search"),
        ("corr-cache-queue-backlog", "alert-queue-overflow", "metric-cache-miss-rate"),
        ("corr-deploy-cpu-spike", "alert-cpu-critical", "metric-cpu-spike-prod-01"),
        ("corr-external-gateway-timeout", "alert-gateway-timeout", "metric-timeout-gateway"),
        ("corr-memory-connection-leak", "alert-connection-leak", "metric-connection-pool-exhaust"),
    ]:
        mem.link(corr, alert, label="triggers")
        mem.link(corr, alert, label="correlates_with")
        mem.link(corr, alert, label="follows")
        mem.link(corr, metric, label="causes")

    for corr, alert, metric in [
        ("corr-disk-deploy-failure", "alert-deploy-rollback", "metric-deployment-failure"),
        ("corr-subscription-billing", "alert-payment-declines", "metric-error-burst-payment"),
        ("corr-media-content-delivery", "alert-cascading-failure", "metric-throughput-drop-search"),
        ("corr-notification-push-fail", "alert-external-degradation", "metric-external-api-slow"),
        ("corr-analytics-recommendation-drift", "alert-search-degraded", "metric-throughput-drop-search"),
        ("corr-loyalty-promo-abuse", "alert-order-errors", "metric-error-burst-order"),
        ("corr-audit-compliance-gap", "alert-auth-failures", "metric-latency-spike-auth"),
    ]:
        mem.link(corr, alert, label="correlates_with")
        mem.link(corr, metric, label="correlates_with")

    for src, tgt in [
        ("metric-latency-spike-api", "corr-api-auth-latency"),
        ("metric-error-burst-order", "corr-order-payment-error"),
        ("metric-error-burst-payment", "corr-checkout-cart-fail"),
        ("metric-throughput-drop-search", "corr-search-index-delay"),
        ("metric-cache-miss-rate", "corr-cache-queue-backlog"),
        ("metric-cpu-spike-prod-01", "corr-deploy-cpu-spike"),
        ("metric-timeout-gateway", "corr-external-gateway-timeout"),
        ("metric-connection-pool-exhaust", "corr-memory-connection-leak"),
    ]:
        mem.link(src, tgt, label="indicates")

    initial_nodes = mem.size[0]
    initial_edges = mem.size[1]
    print(f"  Nodes: {initial_nodes}, Edges: {initial_edges}")
    print("    35 services | 20 hosts | 15 metrics | 15 alerts")
    print("    15 deployments | 10 external deps | 15 correlations")
    edge_counter: Counter[str] = Counter()
    for edge in mem.engine.graph.edges:
        if edge.label:
            edge_counter[edge.label] += 1
    print(f"  Edge types: {dict(edge_counter)}")
    print()

    # =====================================================================
    # SECTION 2: Auto-Discovery of Structural Patterns
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Auto-Discovery of Structural Patterns")
    print("=" * 70)

    discovery_result = mem.auto_discover_and_apply()
    print(f"  Total patterns discovered: {discovery_result.total_patterns}")
    print(f"  New rules added to active set: {discovery_result.new_rules_added}")

    discovered = mem.discovery.get_discovered_rules()
    type_counts = Counter(dr.pattern_type for dr in discovered)
    print(f"  Pattern breakdown: {dict(type_counts)}")
    print()

    for dr in discovered:
        if dr.pattern_type == "transitive":
            label = dr.pattern.get("edge_label", "?")
            chains = dr.pattern.get("chain_count", 0)
            print(f"  [transitive] edge_label='{label}' — {chains} two-hop chains found")
        elif dr.pattern_type == "inverse":
            fwd = dr.pattern.get("forward", "?")
            rev = dr.pattern.get("reverse", "?")
            pairs = dr.pattern.get("pair_count", 0)
            print(f"  [inverse]    '{fwd}' <-> '{rev}' — {pairs} mutual pairs")
        elif dr.pattern_type == "hub":
            hub = dr.pattern.get("hub_node", "?")
            lbl = dr.pattern.get("edge_label", "?")
            fan = dr.pattern.get("fan_out", 0)
            print(f"  [hub]        '{hub}' fans out {fan}x via '{lbl}'")
    print()

    # =====================================================================
    # SECTION 3: TransitiveRule — Multi-Hop Dependency Chains
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: TransitiveRule — Multi-Hop Dependency Chains")
    print("=" * 70)

    transitive = TransitiveRule(edge_label="depends_on", new_label="inferred_depends_on")
    all_ids = frozenset(n.id for n in mem.engine.graph.nodes)
    t_matches = transitive.find_matches(mem.engine.graph, all_ids)

    print(f"  Found {len(t_matches)} transitive dependency chains")
    print("  (A depends_on B depends_on C => A inferred_depends_on C)")
    print()

    seen_targets: Counter[str] = Counter()
    for m in t_matches:
        seen_targets[_label(mem, m.bindings["C"])] += 1
    top_targets = seen_targets.most_common(8)
    print("  Top transitive targets (most reached via chains):")
    for tgt, count in top_targets:
        print(f"    {tgt}: reached by {count} chain(s)")

    print()
    print("  Sample chains (showing A -> B -> C):")
    for m in t_matches[:12]:
        a = _label(mem, m.bindings["A"])
        b = _label(mem, m.bindings["B"])
        c = _label(mem, m.bindings["C"])
        print(f"    {a} -> {b} -> {c}")
    print()

    # =====================================================================
    # SECTION 4: HubInferenceRule — Co-Occurrence Patterns
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: HubInferenceRule — Co-Occurrence Patterns")
    print("=" * 70)

    min_support = 2
    confidence_threshold = 0.6
    causal = HubInferenceRule(min_support=min_support, confidence_threshold=confidence_threshold, causes_label="causes")
    c_matches = causal.find_matches(mem.engine.graph, all_ids)

    print(f"  Found {len(c_matches)} causal relationships")
    print(f"  (min_support={min_support}, confidence_threshold={confidence_threshold})")
    print()

    for m in c_matches:
        cause = _label(mem, m.bindings["cause"])
        effect = _label(mem, m.bindings["effect"])
        support = m.context["support"]
        conf = m.context["confidence"]
        print(f"  {cause}")
        print(f"    -> {effect}  (support={support}, confidence={conf:.2f})")
    print()

    # =====================================================================
    # SECTION 5: GeneralizationRule — Abstract Service Categories
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: GeneralizationRule — Abstract Service Categories")
    print("=" * 70)

    gen = GeneralizationRule(similarity_threshold=0.8, label_prefix="category_")
    g_matches = gen.find_matches(mem.engine.graph, all_ids)

    print(f"  Found {len(g_matches)} service abstraction pairs (similarity >= 0.8)")
    print()

    team_groups: dict[str, list[tuple[str, str, float]]] = {}
    for m in g_matches:
        la = m.context["label_a"]
        lb = m.context["label_b"]
        sim = m.context["similarity"]
        node_a = mem.engine.graph.get_node_by_label(la)
        team = node_a.data.get("team", "unknown") if node_a and node_a.data else "unknown"
        team_groups.setdefault(team, []).append((la, lb, sim))

    for team, pairs in sorted(team_groups.items()):
        print(f"  Team '{team}' — {len(pairs)} similar pair(s):")
        for la, lb, sim in pairs:
            print(f"    {la} ~ {lb}  (similarity={sim:.2f})")

    print()
    print("  Applying generalization to create abstract category nodes...")
    for m in g_matches[:5]:
        gen.apply(mem.engine.graph, m)
    print(f"  Created {min(5, len(g_matches))} category nodes")
    print(f"  Graph now: {mem.size[0]} nodes, {mem.size[1]} edges")
    print()

    # =====================================================================
    # SECTION 6: StructuralProjectionRule — Structural Analogies
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: StructuralProjectionRule — Structural Analogies")
    print("=" * 70)

    mem.set_embedding_provider(HashEmbeddingProvider(dim=32))
    analogical = StructuralProjectionRule(similarity_threshold=0.7)
    assert mem.embedding_engine is not None
    analogical.set_embedding_engine(mem.embedding_engine)

    a_matches = analogical.find_matches(mem.engine.graph, all_ids)

    print(f"  Found {len(a_matches)} structural analogies (A:B :: C:D)")
    print()

    if a_matches:
        print("  Top analogies by score:")
        scored = sorted(a_matches, key=lambda m: m.context.get("analogy_score", 0), reverse=True)
        for m in scored[:10]:
            a = _label(mem, m.bindings["A"])
            b = _label(mem, m.bindings["B"])
            c = _label(mem, m.bindings["C"])
            d = _label(mem, m.bindings["D"])
            score = m.context.get("analogy_score", 0)
            print(f"    {a}:{b} :: {c}:{d}  (score={score:.3f})")
    else:
        print("  No analogies above threshold 0.7 with hash embeddings.")
        print("  In production, use sentence-transformer providers for")
        print("  semantically meaningful analogies.")
    print()

    # =====================================================================
    # SECTION 7: Full Reasoning with All Rules Combined
    # =====================================================================

    print("=" * 70)
    print("SECTION 7: Full Reasoning with All Rules Combined")
    print("=" * 70)

    mem.add_rules(
        transitive,
        causal,
        gen,
        analogical,
        InverseRule(edge_label="mitigates", inverse_label="resolved_by"),
    )

    seeds = {
        "svc-api-gateway", "svc-auth", "svc-user",
        "svc-order", "svc-payment", "svc-billing", "svc-checkout",
    }
    pre_nodes = mem.size[0]
    pre_edges = mem.size[1]

    result = mem.reason(
        seeds=seeds,
        depth=3,
        max_states=50,
    )

    expansion = result.expansion
    overlay = result.overlay or {}

    print(f"  Seeds: {sorted(seeds)}")
    print("  (chosen to form depends_on chains for transitive inference)")
    print(f"  States created:     {expansion.states_created if expansion else 0}")
    print(f"  Rules applied:      {expansion.rules_applied if expansion else 0}")
    print(f"  Max depth reached:  {expansion.max_depth if expansion else 0}")
    if overlay:
        print(f"  Overlay committed:  {overlay.get('node_count', 0)} nodes, {overlay.get('edge_count', 0)} edges")

    post_nodes = mem.size[0]
    post_edges = mem.size[1]
    print()
    print("  Graph growth:")
    print(f"    Before reasoning: {pre_nodes} nodes, {pre_edges} edges")
    print(f"    After reasoning:  {post_nodes} nodes, {post_edges} edges")
    print(f"    Delta:            +{post_nodes - pre_nodes} nodes, +{post_edges - pre_edges} edges")

    new_edge_labels: Counter[str] = Counter()
    inferred_edges = 0
    for edge in mem.engine.graph.edges:
        if edge.metadata.custom.get("inferred"):
            inferred_edges += 1
            if edge.label:
                new_edge_labels[edge.label] += 1
    print()
    print(f"  Total inferred edges in graph: {inferred_edges}")
    if new_edge_labels:
        print(f"  Inferred edge types: {dict(new_edge_labels)}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Infrastructure:  {initial_nodes} nodes, {initial_edges} edges")
    print(f"  Auto-discovery:  {discovery_result.total_patterns} patterns")
    for ptype, count in sorted(type_counts.items()):
        print(f"    {ptype}: {count}")
    print(f"  Transitive chains:  {len(t_matches)} hidden dependency paths")
    print(f"  Causal links:       {len(c_matches)} co-occurrence patterns")
    print(f"  Abstractions:       {len(g_matches)} similar-service pairs")
    print(f"  Analogies:          {len(a_matches)} structural (A:B::C:D)")
    print(f"  Final graph:        {mem.size[0]} nodes, {mem.size[1]} edges")
    print()
    print("  Key takeaway: rule-based reasoning transforms raw telemetry")
    print("  edges into actionable knowledge — hidden dependencies, causal")
    print("  chains, and service abstractions — without manual rule writing")
    print("  for every possible pattern.")
    print()


if __name__ == "__main__":
    main()
