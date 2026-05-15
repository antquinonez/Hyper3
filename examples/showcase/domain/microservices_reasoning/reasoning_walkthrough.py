"""
Reasoning and Inference Walkthrough
===================================

Infers hidden service dependency chains in a microservices architecture.

Real ops teams maintain dependency maps, but the *transitive* blast radius
of an infrastructure failure is rarely obvious.  This script builds a
synthetic 82-node, 236-edge graph, applies TransitiveRule and
InverseRule inference, and produces actionable operational reports:

  - Full blast radius of each database / message queue
  - Single points of failure (betweenness centrality)
  - Longest dependency chains (critical paths)
  - Services most at risk from a given infrastructure outage

Run with:
    .venv/bin/python examples/showcase/domain/microservices_reasoning/reasoning_walkthrough.py
"""

from __future__ import annotations

from collections import defaultdict
from typing import cast

from hyper3 import EfficiencyTracker, HypergraphMemory, InverseRule, Modality, OperationType, TransitiveRule, top_k


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)
    tracker = EfficiencyTracker()

    print("=" * 70)
    print("SECTION 1: Building a Microservices Architecture Graph")
    print("=" * 70)

    domains = {
        "auth": [
            ("svc-auth-gateway", {"port": 8443, "team": "auth", "criticality": 5, "lang": "go", "region": "us-east"}),
            ("svc-auth-token", {"port": 8444, "team": "auth", "criticality": 5, "lang": "go", "region": "us-east"}),
            ("svc-auth-session", {"port": 8445, "team": "auth", "criticality": 4, "lang": "go", "region": "us-east"}),
            ("svc-auth-mfa", {"port": 8446, "team": "auth", "criticality": 4, "lang": "python", "region": "us-east"}),
            ("svc-auth-oauth", {"port": 8447, "team": "auth", "criticality": 3, "lang": "python", "region": "eu-west"}),
            ("svc-auth-rbac", {"port": 8448, "team": "auth", "criticality": 4, "lang": "go", "region": "us-east"}),
        ],
        "payments": [
            ("svc-pay-processor", {"port": 8501, "team": "payments", "criticality": 5, "lang": "java", "region": "us-east"}),
            ("svc-pay-validator", {"port": 8502, "team": "payments", "criticality": 5, "lang": "java", "region": "us-east"}),
            ("svc-pay-refund", {"port": 8503, "team": "payments", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-pay-fraud", {"port": 8504, "team": "payments", "criticality": 5, "lang": "python", "region": "us-east"}),
            ("svc-pay-recon", {"port": 8505, "team": "payments", "criticality": 3, "lang": "java", "region": "eu-west"}),
            ("svc-pay-wallet", {"port": 8506, "team": "payments", "criticality": 4, "lang": "java", "region": "us-east"}),
        ],
        "orders": [
            ("svc-order-api", {"port": 8601, "team": "orders", "criticality": 5, "lang": "java", "region": "us-east"}),
            ("svc-order-fulfill", {"port": 8602, "team": "orders", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-order-history", {"port": 8603, "team": "orders", "criticality": 3, "lang": "java", "region": "eu-west"}),
            ("svc-order-pricing", {"port": 8604, "team": "orders", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-order-invoice", {"port": 8605, "team": "orders", "criticality": 3, "lang": "python", "region": "eu-west"}),
            ("svc-order-cart", {"port": 8606, "team": "orders", "criticality": 4, "lang": "java", "region": "us-east"}),
        ],
        "users": [
            ("svc-user-profile", {"port": 8701, "team": "users", "criticality": 4, "lang": "python", "region": "us-east"}),
            ("svc-user-prefs", {"port": 8702, "team": "users", "criticality": 2, "lang": "python", "region": "us-east"}),
            ("svc-user-activity", {"port": 8703, "team": "users", "criticality": 3, "lang": "python", "region": "eu-west"}),
            ("svc-user-perms", {"port": 8704, "team": "users", "criticality": 4, "lang": "go", "region": "us-east"}),
            ("svc-user-onboarding", {"port": 8705, "team": "users", "criticality": 3, "lang": "python", "region": "us-east"}),
        ],
        "notifications": [
            ("svc-notif-email", {"port": 8801, "team": "notifications", "criticality": 3, "lang": "python", "region": "us-east"}),
            ("svc-notif-sms", {"port": 8802, "team": "notifications", "criticality": 3, "lang": "python", "region": "us-east"}),
            ("svc-notif-push", {"port": 8803, "team": "notifications", "criticality": 2, "lang": "node", "region": "eu-west"}),
            ("svc-notif-templates", {"port": 8804, "team": "notifications", "criticality": 2, "lang": "python", "region": "us-east"}),
            ("svc-notif-preferences", {"port": 8805, "team": "notifications", "criticality": 2, "lang": "python", "region": "us-east"}),
        ],
        "search": [
            ("svc-search-indexer", {"port": 8901, "team": "search", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-search-query", {"port": 8902, "team": "search", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-search-suggest", {"port": 8903, "team": "search", "criticality": 3, "lang": "python", "region": "eu-west"}),
            ("svc-search-autocomplete", {"port": 8904, "team": "search", "criticality": 2, "lang": "node", "region": "us-east"}),
        ],
        "analytics": [
            ("svc-analytics-ingest", {"port": 8401, "team": "analytics", "criticality": 3, "lang": "python", "region": "eu-west"}),
            ("svc-analytics-agg", {"port": 8402, "team": "analytics", "criticality": 3, "lang": "python", "region": "eu-west"}),
            ("svc-analytics-dash", {"port": 8403, "team": "analytics", "criticality": 2, "lang": "node", "region": "us-east"}),
            ("svc-analytics-reports", {"port": 8404, "team": "analytics", "criticality": 2, "lang": "python", "region": "eu-west"}),
        ],
        "inventory": [
            ("svc-inv-tracker", {"port": 9201, "team": "inventory", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-inv-reserve", {"port": 9202, "team": "inventory", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-inv-warehouse", {"port": 9203, "team": "inventory", "criticality": 3, "lang": "python", "region": "eu-west"}),
            ("svc-inv-sync", {"port": 9204, "team": "inventory", "criticality": 3, "lang": "go", "region": "us-east"}),
        ],
        "shipping": [
            ("svc-ship-orch", {"port": 9301, "team": "shipping", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-ship-label", {"port": 9302, "team": "shipping", "criticality": 3, "lang": "python", "region": "us-east"}),
            ("svc-ship-track", {"port": 9303, "team": "shipping", "criticality": 3, "lang": "go", "region": "eu-west"}),
            ("svc-ship-carrier", {"port": 9304, "team": "shipping", "criticality": 3, "lang": "java", "region": "us-east"}),
        ],
        "catalog": [
            ("svc-catalog-api", {"port": 9401, "team": "catalog", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-catalog-enrich", {"port": 9402, "team": "catalog", "criticality": 3, "lang": "python", "region": "us-east"}),
            ("svc-catalog-images", {"port": 9403, "team": "catalog", "criticality": 2, "lang": "node", "region": "eu-west"}),
            ("svc-catalog-reviews", {"port": 9404, "team": "catalog", "criticality": 2, "lang": "python", "region": "us-east"}),
        ],
        "platform": [
            ("svc-gateway-main", {"port": 8000, "team": "platform", "criticality": 5, "lang": "go", "region": "us-east"}),
            ("svc-gateway-admin", {"port": 8001, "team": "platform", "criticality": 4, "lang": "go", "region": "us-east"}),
            ("svc-config-server", {"port": 8888, "team": "platform", "criticality": 4, "lang": "java", "region": "us-east"}),
            ("svc-feature-flags", {"port": 8100, "team": "platform", "criticality": 3, "lang": "go", "region": "us-east"}),
            ("svc-rate-limiter", {"port": 8101, "team": "platform", "criticality": 4, "lang": "go", "region": "us-east"}),
        ],
    }

    infrastructure = {
        "db-pg-orders": {"type": "database", "engine": "postgresql", "version": "15", "team": "dba"},
        "db-pg-users": {"type": "database", "engine": "postgresql", "version": "15", "team": "dba"},
        "db-pg-payments": {"type": "database", "engine": "postgresql", "version": "15", "team": "dba"},
        "db-pg-inventory": {"type": "database", "engine": "postgresql", "version": "15", "team": "dba"},
        "db-mysql-analytics": {"type": "database", "engine": "mysql", "version": "8", "team": "dba"},
        "db-mongo-catalog": {"type": "database", "engine": "mongodb", "version": "7", "team": "dba"},
        "db-mongo-sessions": {"type": "database", "engine": "mongodb", "version": "7", "team": "dba"},
        "cache-redis-auth": {"type": "cache", "engine": "redis", "version": "7", "team": "infra"},
        "cache-redis-cart": {"type": "cache", "engine": "redis", "version": "7", "team": "infra"},
        "cache-redis-general": {"type": "cache", "engine": "redis", "version": "7", "team": "infra"},
        "cache-memcached-search": {"type": "cache", "engine": "memcached", "version": "1.6", "team": "infra"},
        "queue-kafka-orders": {"type": "queue", "engine": "kafka", "version": "3.5", "team": "infra"},
        "queue-kafka-events": {"type": "queue", "engine": "kafka", "version": "3.5", "team": "infra"},
        "queue-rabbitmq-notif": {"type": "queue", "engine": "rabbitmq", "version": "3.12", "team": "infra"},
        "proxy-nginx-ext": {"type": "proxy", "engine": "nginx", "version": "1.25", "team": "platform"},
        "proxy-envoy-mesh": {"type": "proxy", "engine": "envoy", "version": "1.28", "team": "platform"},
        "registry-consul": {"type": "service_discovery", "engine": "consul", "version": "1.17", "team": "platform"},
    }

    external = {
        "ext-stripe": {"type": "payment_gateway", "provider": "stripe"},
        "ext-paypal": {"type": "payment_gateway", "provider": "paypal"},
        "ext-sendgrid": {"type": "email", "provider": "sendgrid"},
        "ext-twilio": {"type": "sms", "provider": "twilio"},
        "ext-fcm": {"type": "push", "provider": "firebase"},
        "ext-cloudfront": {"type": "cdn", "provider": "aws"},
        "ext-s3-assets": {"type": "storage", "provider": "aws"},
        "ext-ups": {"type": "carrier", "provider": "ups"},
        "ext-fedex": {"type": "carrier", "provider": "fedex"},
        "ext-usps": {"type": "carrier", "provider": "usps"},
        "ext-elasticsearch": {"type": "search", "provider": "elastic"},
        "ext-datadog": {"type": "monitoring", "provider": "datadog"},
    }

    for domain_services in domains.values():
        for name, data in domain_services:
            mem.add(name, data={**data, "type": "microservice"}, modalities={Modality.CONCEPTUAL})

    for name, data in infrastructure.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    for name, data in external.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    svc_count = sum(len(v) for v in domains.values())
    print(f"  Microservices:      {svc_count}")
    print(f"  Infrastructure:     {len(infrastructure)}")
    print(f"  External services:  {len(external)}")
    print(f"  Total nodes:        {mem.size[0]}")
    print()

    print("=" * 70)
    print("SECTION 2: Creating Dependency Relationships")
    print("=" * 70)

    svc_to_infra: list[tuple[str, str, str]] = [
        ("svc-auth-gateway", "cache-redis-auth", "depends_on"),
        ("svc-auth-gateway", "db-mongo-sessions", "depends_on"),
        ("svc-auth-gateway", "registry-consul", "depends_on"),
        ("svc-auth-token", "cache-redis-auth", "depends_on"),
        ("svc-auth-token", "db-mongo-sessions", "depends_on"),
        ("svc-auth-session", "cache-redis-auth", "depends_on"),
        ("svc-auth-session", "db-mongo-sessions", "depends_on"),
        ("svc-auth-session", "cache-redis-general", "depends_on"),
        ("svc-auth-mfa", "cache-redis-auth", "depends_on"),
        ("svc-auth-mfa", "db-mongo-sessions", "depends_on"),
        ("svc-auth-oauth", "cache-redis-auth", "depends_on"),
        ("svc-auth-oauth", "db-mongo-sessions", "depends_on"),
        ("svc-auth-rbac", "cache-redis-auth", "depends_on"),
        ("svc-auth-rbac", "db-mongo-sessions", "depends_on"),
        ("svc-pay-processor", "db-pg-payments", "depends_on"),
        ("svc-pay-processor", "cache-redis-general", "depends_on"),
        ("svc-pay-processor", "queue-kafka-events", "depends_on"),
        ("svc-pay-validator", "db-pg-payments", "depends_on"),
        ("svc-pay-validator", "cache-redis-general", "depends_on"),
        ("svc-pay-refund", "db-pg-payments", "depends_on"),
        ("svc-pay-refund", "queue-kafka-events", "depends_on"),
        ("svc-pay-fraud", "db-pg-payments", "depends_on"),
        ("svc-pay-fraud", "cache-redis-general", "depends_on"),
        ("svc-pay-fraud", "queue-kafka-events", "depends_on"),
        ("svc-pay-recon", "db-pg-payments", "depends_on"),
        ("svc-pay-recon", "queue-kafka-events", "depends_on"),
        ("svc-pay-wallet", "db-pg-payments", "depends_on"),
        ("svc-pay-wallet", "cache-redis-general", "depends_on"),
        ("svc-order-api", "db-pg-orders", "depends_on"),
        ("svc-order-api", "cache-redis-cart", "depends_on"),
        ("svc-order-api", "queue-kafka-orders", "depends_on"),
        ("svc-order-api", "registry-consul", "depends_on"),
        ("svc-order-fulfill", "db-pg-orders", "depends_on"),
        ("svc-order-fulfill", "queue-kafka-orders", "depends_on"),
        ("svc-order-fulfill", "queue-kafka-events", "depends_on"),
        ("svc-order-history", "db-pg-orders", "depends_on"),
        ("svc-order-pricing", "db-pg-orders", "depends_on"),
        ("svc-order-pricing", "cache-redis-general", "depends_on"),
        ("svc-order-invoice", "db-pg-orders", "depends_on"),
        ("svc-order-invoice", "queue-kafka-events", "depends_on"),
        ("svc-order-cart", "db-pg-orders", "depends_on"),
        ("svc-order-cart", "cache-redis-cart", "depends_on"),
        ("svc-order-cart", "cache-redis-general", "depends_on"),
        ("svc-user-profile", "db-pg-users", "depends_on"),
        ("svc-user-profile", "cache-redis-general", "depends_on"),
        ("svc-user-profile", "registry-consul", "depends_on"),
        ("svc-user-prefs", "db-pg-users", "depends_on"),
        ("svc-user-prefs", "cache-redis-general", "depends_on"),
        ("svc-user-activity", "db-pg-users", "depends_on"),
        ("svc-user-activity", "queue-kafka-events", "depends_on"),
        ("svc-user-perms", "db-pg-users", "depends_on"),
        ("svc-user-perms", "cache-redis-auth", "depends_on"),
        ("svc-user-onboarding", "db-pg-users", "depends_on"),
        ("svc-user-onboarding", "cache-redis-general", "depends_on"),
        ("svc-notif-email", "queue-rabbitmq-notif", "depends_on"),
        ("svc-notif-email", "cache-redis-general", "depends_on"),
        ("svc-notif-sms", "queue-rabbitmq-notif", "depends_on"),
        ("svc-notif-sms", "cache-redis-general", "depends_on"),
        ("svc-notif-push", "queue-rabbitmq-notif", "depends_on"),
        ("svc-notif-templates", "db-mongo-catalog", "depends_on"),
        ("svc-notif-templates", "cache-redis-general", "depends_on"),
        ("svc-notif-preferences", "db-mongo-catalog", "depends_on"),
        ("svc-notif-preferences", "cache-redis-general", "depends_on"),
        ("svc-search-indexer", "db-mongo-catalog", "depends_on"),
        ("svc-search-indexer", "cache-memcached-search", "depends_on"),
        ("svc-search-query", "ext-elasticsearch", "depends_on"),
        ("svc-search-query", "cache-memcached-search", "depends_on"),
        ("svc-search-suggest", "ext-elasticsearch", "depends_on"),
        ("svc-search-suggest", "cache-memcached-search", "depends_on"),
        ("svc-search-autocomplete", "ext-elasticsearch", "depends_on"),
        ("svc-analytics-ingest", "db-mysql-analytics", "depends_on"),
        ("svc-analytics-ingest", "queue-kafka-events", "depends_on"),
        ("svc-analytics-agg", "db-mysql-analytics", "depends_on"),
        ("svc-analytics-agg", "queue-kafka-events", "depends_on"),
        ("svc-analytics-dash", "db-mysql-analytics", "depends_on"),
        ("svc-analytics-reports", "db-mysql-analytics", "depends_on"),
        ("svc-analytics-reports", "queue-kafka-events", "depends_on"),
        ("svc-inv-tracker", "db-pg-inventory", "depends_on"),
        ("svc-inv-tracker", "db-pg-orders", "depends_on"),
        ("svc-inv-tracker", "cache-redis-general", "depends_on"),
        ("svc-inv-reserve", "db-pg-inventory", "depends_on"),
        ("svc-inv-reserve", "cache-redis-cart", "depends_on"),
        ("svc-inv-reserve", "queue-kafka-orders", "depends_on"),
        ("svc-inv-warehouse", "db-pg-inventory", "depends_on"),
        ("svc-inv-sync", "db-pg-inventory", "depends_on"),
        ("svc-inv-sync", "queue-kafka-events", "depends_on"),
        ("svc-ship-orch", "db-pg-orders", "depends_on"),
        ("svc-ship-orch", "queue-kafka-orders", "depends_on"),
        ("svc-ship-label", "queue-kafka-orders", "depends_on"),
        ("svc-ship-track", "db-pg-orders", "depends_on"),
        ("svc-ship-track", "queue-kafka-events", "depends_on"),
        ("svc-ship-carrier", "queue-kafka-orders", "depends_on"),
        ("svc-catalog-api", "db-mongo-catalog", "depends_on"),
        ("svc-catalog-api", "cache-memcached-search", "depends_on"),
        ("svc-catalog-api", "registry-consul", "depends_on"),
        ("svc-catalog-enrich", "db-mongo-catalog", "depends_on"),
        ("svc-catalog-enrich", "queue-kafka-events", "depends_on"),
        ("svc-catalog-images", "db-mongo-catalog", "depends_on"),
        ("svc-catalog-images", "ext-s3-assets", "depends_on"),
        ("svc-catalog-reviews", "db-mongo-catalog", "depends_on"),
        ("svc-catalog-reviews", "ext-elasticsearch", "depends_on"),
        ("svc-gateway-main", "proxy-nginx-ext", "depends_on"),
        ("svc-gateway-main", "proxy-envoy-mesh", "depends_on"),
        ("svc-gateway-main", "registry-consul", "depends_on"),
        ("svc-gateway-main", "svc-rate-limiter", "depends_on"),
        ("svc-gateway-admin", "svc-auth-gateway", "depends_on"),
        ("svc-gateway-admin", "svc-config-server", "depends_on"),
        ("svc-config-server", "db-pg-orders", "depends_on"),
        ("svc-config-server", "registry-consul", "depends_on"),
        ("svc-feature-flags", "db-pg-orders", "depends_on"),
        ("svc-feature-flags", "cache-redis-general", "depends_on"),
        ("svc-rate-limiter", "cache-redis-general", "depends_on"),
        ("svc-rate-limiter", "registry-consul", "depends_on"),
    ]

    svc_to_svc: list[tuple[str, str, str]] = [
        ("svc-auth-gateway", "svc-auth-token", "depends_on"),
        ("svc-auth-gateway", "svc-auth-session", "depends_on"),
        ("svc-auth-gateway", "svc-auth-oauth", "depends_on"),
        ("svc-auth-mfa", "svc-auth-token", "depends_on"),
        ("svc-auth-rbac", "svc-auth-session", "depends_on"),
        ("svc-auth-rbac", "svc-auth-token", "depends_on"),
        ("svc-order-api", "svc-auth-gateway", "depends_on"),
        ("svc-order-api", "svc-user-profile", "depends_on"),
        ("svc-order-api", "svc-catalog-api", "depends_on"),
        ("svc-order-api", "svc-order-pricing", "depends_on"),
        ("svc-order-api", "svc-inv-reserve", "depends_on"),
        ("svc-order-api", "svc-feature-flags", "depends_on"),
        ("svc-order-fulfill", "svc-ship-orch", "depends_on"),
        ("svc-order-fulfill", "svc-inv-tracker", "depends_on"),
        ("svc-order-fulfill", "svc-notif-email", "depends_on"),
        ("svc-order-history", "svc-order-api", "depends_on"),
        ("svc-order-invoice", "svc-order-api", "depends_on"),
        ("svc-order-invoice", "svc-pay-recon", "depends_on"),
        ("svc-order-pricing", "svc-catalog-api", "depends_on"),
        ("svc-order-cart", "svc-order-api", "depends_on"),
        ("svc-order-cart", "svc-catalog-api", "depends_on"),
        ("svc-pay-processor", "svc-auth-gateway", "depends_on"),
        ("svc-pay-processor", "svc-pay-validator", "depends_on"),
        ("svc-pay-processor", "svc-pay-fraud", "depends_on"),
        ("svc-pay-processor", "svc-notif-email", "depends_on"),
        ("svc-pay-validator", "svc-auth-token", "depends_on"),
        ("svc-pay-refund", "svc-pay-processor", "depends_on"),
        ("svc-pay-refund", "svc-notif-email", "depends_on"),
        ("svc-pay-fraud", "svc-user-activity", "depends_on"),
        ("svc-pay-recon", "svc-pay-processor", "depends_on"),
        ("svc-pay-wallet", "svc-pay-validator", "depends_on"),
        ("svc-pay-wallet", "svc-auth-token", "depends_on"),
        ("svc-user-profile", "svc-auth-session", "depends_on"),
        ("svc-user-perms", "svc-auth-session", "depends_on"),
        ("svc-user-perms", "svc-auth-rbac", "depends_on"),
        ("svc-user-activity", "svc-user-profile", "depends_on"),
        ("svc-user-onboarding", "svc-user-profile", "depends_on"),
        ("svc-user-onboarding", "svc-notif-email", "depends_on"),
        ("svc-notif-email", "svc-notif-templates", "depends_on"),
        ("svc-notif-email", "svc-notif-preferences", "depends_on"),
        ("svc-notif-sms", "svc-notif-templates", "depends_on"),
        ("svc-notif-sms", "svc-notif-preferences", "depends_on"),
        ("svc-notif-push", "svc-notif-templates", "depends_on"),
        ("svc-search-indexer", "svc-catalog-api", "depends_on"),
        ("svc-search-suggest", "svc-search-query", "depends_on"),
        ("svc-search-autocomplete", "svc-search-suggest", "depends_on"),
        ("svc-analytics-ingest", "svc-user-activity", "depends_on"),
        ("svc-analytics-ingest", "svc-order-api", "depends_on"),
        ("svc-analytics-agg", "svc-analytics-ingest", "depends_on"),
        ("svc-analytics-dash", "svc-analytics-agg", "depends_on"),
        ("svc-analytics-reports", "svc-analytics-agg", "depends_on"),
        ("svc-inv-tracker", "svc-inv-warehouse", "depends_on"),
        ("svc-inv-reserve", "svc-inv-tracker", "depends_on"),
        ("svc-inv-sync", "svc-inv-tracker", "depends_on"),
        ("svc-ship-orch", "svc-ship-carrier", "depends_on"),
        ("svc-ship-orch", "svc-ship-label", "depends_on"),
        ("svc-ship-track", "svc-ship-orch", "depends_on"),
        ("svc-catalog-enrich", "svc-catalog-api", "depends_on"),
        ("svc-catalog-images", "svc-catalog-enrich", "depends_on"),
        ("svc-catalog-reviews", "svc-catalog-api", "depends_on"),
    ]

    reads: list[tuple[str, str, str]] = [
        ("svc-auth-token", "cache-redis-auth", "reads_from"),
        ("svc-auth-session", "cache-redis-auth", "reads_from"),
        ("svc-auth-session", "db-mongo-sessions", "reads_from"),
        ("svc-user-profile", "db-pg-users", "reads_from"),
        ("svc-user-profile", "cache-redis-general", "reads_from"),
        ("svc-order-api", "db-pg-orders", "reads_from"),
        ("svc-order-api", "cache-redis-cart", "reads_from"),
        ("svc-search-query", "cache-memcached-search", "reads_from"),
        ("svc-catalog-api", "db-mongo-catalog", "reads_from"),
        ("svc-catalog-api", "cache-memcached-search", "reads_from"),
    ]

    writes: list[tuple[str, str, str]] = [
        ("svc-pay-processor", "db-pg-payments", "writes_to"),
        ("svc-pay-fraud", "db-pg-payments", "writes_to"),
        ("svc-order-api", "db-pg-orders", "writes_to"),
        ("svc-order-fulfill", "db-pg-orders", "writes_to"),
        ("svc-user-activity", "db-pg-users", "writes_to"),
        ("svc-analytics-ingest", "db-mysql-analytics", "writes_to"),
        ("svc-analytics-agg", "db-mysql-analytics", "writes_to"),
        ("svc-search-indexer", "ext-elasticsearch", "writes_to"),
        ("svc-inv-tracker", "db-pg-inventory", "writes_to"),
        ("svc-inv-reserve", "db-pg-inventory", "writes_to"),
    ]

    caching: list[tuple[str, str, str]] = [
        ("cache-redis-cart", "db-pg-orders", "caches_for"),
        ("cache-redis-auth", "db-mongo-sessions", "caches_for"),
        ("cache-redis-general", "db-pg-users", "caches_for"),
        ("cache-memcached-search", "ext-elasticsearch", "caches_for"),
    ]

    publishes: list[tuple[str, str, str]] = [
        ("svc-order-api", "queue-kafka-orders", "publishes_to"),
        ("svc-order-fulfill", "queue-kafka-orders", "publishes_to"),
        ("svc-order-fulfill", "queue-kafka-events", "publishes_to"),
        ("svc-pay-processor", "queue-kafka-events", "publishes_to"),
        ("svc-pay-refund", "queue-kafka-events", "publishes_to"),
        ("svc-user-activity", "queue-kafka-events", "publishes_to"),
        ("svc-inv-sync", "queue-kafka-events", "publishes_to"),
        ("svc-ship-track", "queue-kafka-events", "publishes_to"),
        ("svc-catalog-enrich", "queue-kafka-events", "publishes_to"),
    ]

    subscribes: list[tuple[str, str, str]] = [
        ("svc-order-fulfill", "queue-kafka-orders", "subscribes_to"),
        ("svc-inv-reserve", "queue-kafka-orders", "subscribes_to"),
        ("svc-ship-orch", "queue-kafka-orders", "subscribes_to"),
        ("svc-ship-label", "queue-kafka-orders", "subscribes_to"),
        ("svc-ship-carrier", "queue-kafka-orders", "subscribes_to"),
        ("svc-analytics-ingest", "queue-kafka-events", "subscribes_to"),
        ("svc-notif-email", "queue-rabbitmq-notif", "subscribes_to"),
        ("svc-notif-sms", "queue-rabbitmq-notif", "subscribes_to"),
        ("svc-notif-push", "queue-rabbitmq-notif", "subscribes_to"),
    ]

    routes: list[tuple[str, str, str]] = [
        ("proxy-nginx-ext", "svc-gateway-main", "routes_to"),
        ("proxy-nginx-ext", "svc-order-api", "routes_to"),
        ("proxy-nginx-ext", "svc-catalog-api", "routes_to"),
        ("proxy-nginx-ext", "svc-search-query", "routes_to"),
        ("proxy-nginx-ext", "svc-user-profile", "routes_to"),
        ("proxy-envoy-mesh", "svc-gateway-main", "routes_to"),
        ("proxy-envoy-mesh", "svc-auth-gateway", "routes_to"),
        ("proxy-envoy-mesh", "svc-pay-processor", "routes_to"),
        ("proxy-envoy-mesh", "svc-inv-tracker", "routes_to"),
        ("proxy-envoy-mesh", "svc-ship-orch", "routes_to"),
    ]

    ext_deps: list[tuple[str, str, str]] = [
        ("svc-pay-processor", "ext-stripe", "depends_on"),
        ("svc-pay-processor", "ext-paypal", "depends_on"),
        ("svc-pay-wallet", "ext-stripe", "depends_on"),
        ("svc-notif-email", "ext-sendgrid", "depends_on"),
        ("svc-notif-sms", "ext-twilio", "depends_on"),
        ("svc-notif-push", "ext-fcm", "depends_on"),
        ("svc-catalog-images", "ext-cloudfront", "depends_on"),
        ("svc-catalog-images", "ext-s3-assets", "depends_on"),
        ("svc-ship-carrier", "ext-ups", "depends_on"),
        ("svc-ship-carrier", "ext-fedex", "depends_on"),
        ("svc-ship-carrier", "ext-usps", "depends_on"),
    ]

    all_edges = (
        svc_to_infra + svc_to_svc + reads + writes
        + caching + publishes + subscribes + routes + ext_deps
    )
    for src, tgt, label in all_edges:
        mem.link(src, tgt, label=label)

    print(f"  Total edges created: {mem.size[1]}")
    print()

    print("=" * 70)
    print("SECTION 3: Direct vs Transitive Dependencies -- The Tip of the Iceberg")
    print("=" * 70)

    db_labels = sorted(mem.query_nodes(data={"type": "database"}))
    queue_labels = sorted(mem.query_nodes(data={"type": "queue"}))

    direct_dep_map: dict[str, list[str]] = defaultdict(list)
    for le in mem.engine.graph.labeled_edges:
        if le["label"] == "depends_on" and le["source_labels"] and le["target_labels"]:
            direct_dep_map[le["target_labels"][0]].append(le["source_labels"][0])

    for label in db_labels + queue_labels:
        direct = direct_dep_map.get(label, [])
        print(f"  {label}: {len(direct)} direct dependents")
    print()
    print("  This is only the surface -- transitive chains hide far more.")
    print()

    print("=" * 70)
    print("SECTION 4: Adding Reasoning Rules")
    print("=" * 70)

    mem.reason.add_rules(
        TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on"),
        InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
    )
    print("  TransitiveRule: A depends_on B, B depends_on C => A indirectly_depends_on C")
    print("  InverseRule:    A depends_on B => B depended_on_by A")
    print()

    print("=" * 70)
    print("SECTION 5: Running Reasoning on Critical Infrastructure")
    print("=" * 70)

    all_labels = {n.label for n in mem.engine.graph.nodes}

    with tracker.track(OperationType.REASONING, metadata={"seeds": len(all_labels), "max_depth": 4}):
        result = mem.reason(
            seeds=all_labels,
            max_depth=4,
            max_total_states=300,
        )

    exp = result.expansion
    assert exp is not None
    print(f"  Seeds:             {len(all_labels)} nodes")
    print(f"  States explored:   {exp.states_created}")
    print(f"  Rules applied:     {exp.rules_applied}")
    overlay_edges = result.overlay.get("edge_count", 0) if result.overlay else 0
    print(f"  Edges inferred:    {exp.edges_produced} raw, {overlay_edges} unique (after dedup)")
    print(f"  Graph:             {mem.size[0]} nodes, {mem.size[1]} edges ({236} base + {mem.size[1] - 236} inferred)")
    print()

    print("=" * 70)
    print("SECTION 6: Blast Radius Analysis")
    print("=" * 70)

    indirect_reverse: dict[str, set[str]] = defaultdict(set)
    for le in mem.engine.graph.labeled_edges:
        if le["label"] == "indirectly_depends_on" and le["source_labels"] and le["target_labels"]:
            indirect_reverse[le["target_labels"][0]].add(le["source_labels"][0])

    print("  Full blast radius of each database and queue:")
    print()
    for label in db_labels + queue_labels:
        direct = set(direct_dep_map.get(label, []))
        transitive = indirect_reverse.get(label, set()) - direct
        total = direct | transitive
        print(f"  {label}")
        print(f"    Direct dependents:    {len(direct)}")
        print(f"    Transitive dependents: {len(transitive)} (discovered by inference)")
        print(f"    Total blast radius:   {len(total)}")
        if transitive:
            sample = sorted(transitive)[:6]
            suffix = " ..." if len(transitive) > 6 else ""
            print(f"    Hidden: {sample}{suffix}")
        print()

    print("=" * 70)
    print("SECTION 7: Single Points of Failure -- Betweenness Centrality")
    print("=" * 70)

    with tracker.track(OperationType.TRAVERSAL, metadata={"algorithm": "betweenness_centrality"}):
        bc = cast(dict[str, float], mem.analyze.centrality("betweenness"))
    top_spof = top_k(bc, k=15)

    print(f"  {'Rank':<5} {'Node':<35} {'Betweenness':<12}")
    print(f"  {'----':<5} {'----':<35} {'-----------':<12}")
    for rank, (node, score) in enumerate(top_spof, 1):
        print(f"  {rank:<5} {node:<35} {score:<12.4f}")
    print()
    print("  High betweenness => removing this node fragments the dependency graph.")
    print()

    print("=" * 70)
    print("SECTION 8: Critical Dependency Chains")
    print("=" * 70)

    edge_labels_of_interest = {"depends_on", "indirectly_depends_on"}

    deps_forward: dict[str, list[str]] = defaultdict(list)
    for le in mem.engine.graph.labeled_edges:
        if le["label"] in edge_labels_of_interest and le["source_labels"] and le["target_labels"]:
            deps_forward[le["source_labels"][0]].append(le["target_labels"][0])

    def longest_chain(start: str, visited: frozenset[str] | None = None) -> list[str]:
        if visited is None:
            visited = frozenset()
        if start in visited:
            return [start]
        visited = visited | {start}
        best = [start]
        for nxt in deps_forward.get(start, []):
            chain = [start] + longest_chain(nxt, visited)
            if len(chain) > len(best):
                best = chain
        return best

    chains: list[tuple[int, list[str]]] = []
    for label in mem.query_nodes(data={"type": "microservice"}):
        chain = longest_chain(label)
        if len(chain) > 2:
            chains.append((len(chain), chain))
    chains.sort(reverse=True)

    print("  Longest dependency chains (top 5):")
    for i, (length, chain) in enumerate(chains[:5], 1):
        print(f"  Chain {i} (length {length}):")
        print(f"    {' -> '.join(chain[:8])}")
        if length > 8:
            print(f"    ... ({length - 8} more hops)")
    print()

    print("=" * 70)
    print("SECTION 9: Risk Assessment -- Infrastructure Failure Scenarios")
    print("=" * 70)

    failure_scenarios = [
        ("db-pg-orders", "PostgreSQL orders DB outage"),
        ("queue-kafka-events", "Kafka events bus outage"),
        ("cache-redis-auth", "Redis auth cache outage"),
        ("db-pg-payments", "PostgreSQL payments DB outage"),
    ]

    for infra_label, scenario in failure_scenarios:
        direct = set(direct_dep_map.get(infra_label, []))
        transitive = indirect_reverse.get(infra_label, set()) - direct
        total = direct | transitive

        svc_data_map: dict[str, dict] = {}
        for n in mem.engine.graph.nodes:
            if n.label in total:
                svc_data_map[n.label] = n.data

        critical_count = sum(1 for d in svc_data_map.values() if d.get("criticality", 0) >= 4)
        high_count = sum(1 for d in svc_data_map.values() if d.get("criticality", 0) == 3)
        regions = set(d.get("region", "?") for d in svc_data_map.values())
        teams = set(d.get("team", "?") for d in svc_data_map.values())

        print(f"  Scenario: {scenario}")
        print(f"    Directly impacted:     {len(direct)} services")
        print(f"    Indirectly impacted:   {len(transitive)} services")
        print(f"    Total blast radius:    {len(total)} services")
        print(f"    Critical (4-5):        {critical_count}")
        print(f"    High (3):              {high_count}")
        print(f"    Regions affected:      {', '.join(sorted(regions))}")
        print(f"    Teams to page:         {', '.join(sorted(teams))}")
        if len(total) > len(direct) and direct:
            ratio = len(total) / len(direct)
            print(f"    Blast radius is {ratio:.1f}x larger than direct dependencies")
        print()

    print("=" * 70)
    print("SECTION 10: Operation Efficiency Report")
    print("=" * 70)

    with tracker.track(OperationType.SEARCH, metadata={"operation": "query_nodes"}):
        svc_labels = list(mem.query_nodes(data={"type": "microservice"}))

    with tracker.track(OperationType.ACTIVATION, metadata={"operation": "spreading_activation"}):
        mem.activate(svc_labels[0], iterations=3)

    report = tracker.get_report()
    print(f"  Total operations tracked: {report.total_operations}")
    print(f"  Overall avg duration:     {report.overall_avg_duration_ms:.1f}ms")
    print(f"  Slowest operation:        {report.slowest_operation or 'n/a'}")
    print()
    print(f"  {'Operation':<20} {'Count':>6} {'Avg(ms)':>8} {'P50(ms)':>8} {'P95(ms)':>8} {'Max(ms)':>8}")
    print(f"  {'---------':<20} {'-----':>6} {'-------':>8} {'-------':>8} {'-------':>8} {'-------':>8}")
    for op_name, stats in sorted(report.operation_stats.items()):
        print(f"  {op_name:<20} {stats.count:>6} {stats.avg_duration_ms:>8.1f} {stats.p50_duration_ms:>8.1f} {stats.p95_duration_ms:>8.1f} {stats.max_duration_ms:>8.1f}")
    print()

    cache_eff = report.cache_efficiency
    print(f"  Cache hits:       {cache_eff.hits}")
    print(f"  Cache misses:     {cache_eff.misses}")
    print(f"  Cache hit ratio:  {cache_eff.hit_ratio:.2f}")
    print()

    if report.degradation_detected:
        print("  Degradation alerts:")
        for alert in report.degradation_details:
            print(f"    - {alert}")
    else:
        print("  No performance degradation detected.")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Nodes:            {stats.nodes}")
    print(f"  Edges:            {stats.edges} ({mem.size[1] - 236} unique inferred from {exp.edges_produced} raw)")
    print(f"  Active rules:     {stats.active_rules}")
    print()
    print("  Key insight: transitive rule inference discovers non-obvious")
    print("  dependencies that teams may not be aware of. The blast radius")
    print("  of an infrastructure node is typically 2-3x the direct count.")
    print()


if __name__ == "__main__":
    main()
