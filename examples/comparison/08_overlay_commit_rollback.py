"""
Speculative Incident Investigation with Overlay (networkx reimplementation)
============================================================================

Reimplements examples/advanced/08_overlay_commit_rollback.py using only
networkx. Simulates overlay transactions via G.copy() + manual diff tracking.
This demonstrates how much boilerplate is needed to replicate Hyper3's
overlay feature with plain networkx.

Run with:
    .venv/bin/python examples/comparison/08_overlay_commit_rollback.py
"""

from __future__ import annotations

from collections import Counter, defaultdict

import networkx as nx


SERVICES: dict[str, dict] = {
    "web_frontend": {"type": "service", "team": "platform", "criticality": 8},
    "mobile_bff": {"type": "service", "team": "platform", "criticality": 7},
    "api_gateway": {"type": "service", "team": "platform", "criticality": 9},
    "auth_service": {"type": "service", "team": "identity", "criticality": 10},
    "user_service": {"type": "service", "team": "identity", "criticality": 8},
    "order_service": {"type": "service", "team": "commerce", "criticality": 9},
    "payment_service": {"type": "service", "team": "commerce", "criticality": 10},
    "inventory_service": {"type": "service", "team": "commerce", "criticality": 7},
    "notification_service": {"type": "service", "team": "platform", "criticality": 4},
    "search_service": {"type": "service", "team": "catalog", "criticality": 6},
    "analytics_service": {"type": "service", "team": "data", "criticality": 6},
    "reporting_service": {"type": "service", "team": "data", "criticality": 5},
    "recommendation_engine": {"type": "service", "team": "catalog", "criticality": 5},
    "pricing_service": {"type": "service", "team": "commerce", "criticality": 7},
    "shipping_service": {"type": "service", "team": "commerce", "criticality": 6},
    "email_service": {"type": "service", "team": "platform", "criticality": 4},
    "sms_service": {"type": "service", "team": "platform", "criticality": 3},
    "file_service": {"type": "service", "team": "platform", "criticality": 5},
    "config_service": {"type": "service", "team": "platform", "criticality": 8},
    "scheduler_service": {"type": "service", "team": "platform", "criticality": 4},
    "graphql_gateway": {"type": "service", "team": "platform", "criticality": 7},
    "catalog_service": {"type": "service", "team": "catalog", "criticality": 8},
    "cart_service": {"type": "service", "team": "commerce", "criticality": 7},
    "review_service": {"type": "service", "team": "catalog", "criticality": 5},
    "coupon_service": {"type": "service", "team": "commerce", "criticality": 4},
}

DATABASES: dict[str, dict] = {
    "postgres_users": {"type": "database", "team": "data", "criticality": 9},
    "postgres_orders": {"type": "database", "team": "data", "criticality": 9},
    "postgres_payments": {"type": "database", "team": "data", "criticality": 10},
    "postgres_inventory": {"type": "database", "team": "data", "criticality": 8},
    "postgres_products": {"type": "database", "team": "data", "criticality": 8},
    "mongo_analytics": {"type": "database", "team": "data", "criticality": 7},
    "elastic_search_idx": {"type": "database", "team": "data", "criticality": 7},
    "cassandra_events": {"type": "database", "team": "data", "criticality": 8},
    "timescale_metrics": {"type": "database", "team": "sre", "criticality": 7},
    "redis_sessions": {"type": "database", "team": "platform", "criticality": 8},
    "postgres_configs": {"type": "database", "team": "platform", "criticality": 8},
    "postgres_reviews": {"type": "database", "team": "data", "criticality": 6},
}

CACHES: dict[str, dict] = {
    "redis_cache_auth": {"type": "cache", "team": "platform", "criticality": 9},
    "redis_cache_products": {"type": "cache", "team": "platform", "criticality": 7},
    "redis_cache_search": {"type": "cache", "team": "platform", "criticality": 7},
    "memcached_sessions": {"type": "cache", "team": "platform", "criticality": 6},
    "redis_cache_recommendations": {"type": "cache", "team": "platform", "criticality": 5},
    "redis_cache_cart": {"type": "cache", "team": "platform", "criticality": 6},
}

QUEUES: dict[str, dict] = {
    "kafka_ingestion": {"type": "queue", "team": "platform", "criticality": 8},
    "kafka_analytics": {"type": "queue", "team": "data", "criticality": 7},
    "rabbitmq_notifications": {"type": "queue", "team": "platform", "criticality": 6},
    "rabbitmq_orders": {"type": "queue", "team": "commerce", "criticality": 8},
    "sqs_payments": {"type": "queue", "team": "commerce", "criticality": 8},
    "kafka_events": {"type": "queue", "team": "platform", "criticality": 7},
}

LOAD_BALANCERS: dict[str, dict] = {
    "lb_web": {"type": "load_balancer", "team": "infra", "criticality": 9},
    "lb_api": {"type": "load_balancer", "team": "infra", "criticality": 9},
    "lb_internal": {"type": "load_balancer", "team": "infra", "criticality": 8},
    "lb_analytics": {"type": "load_balancer", "team": "infra", "criticality": 6},
    "lb_search": {"type": "load_balancer", "team": "infra", "criticality": 6},
}

MONITORING: dict[str, dict] = {
    "prometheus": {"type": "monitoring", "team": "sre", "criticality": 7},
    "grafana": {"type": "monitoring", "team": "sre", "criticality": 6},
    "pagerduty": {"type": "monitoring", "team": "sre", "criticality": 8},
    "datadog": {"type": "monitoring", "team": "sre", "criticality": 7},
    "sentry": {"type": "monitoring", "team": "sre", "criticality": 6},
}

NETWORK: dict[str, dict] = {
    "network_segment_dmz": {"type": "network", "team": "network", "criticality": 9},
    "network_segment_internal": {"type": "network", "team": "network", "criticality": 9},
    "network_segment_database": {"type": "network", "team": "network", "criticality": 10},
    "network_segment_cache": {"type": "network", "team": "network", "criticality": 9},
    "vpn_gateway": {"type": "network", "team": "network", "criticality": 8},
    "firewall_core": {"type": "network", "team": "network", "criticality": 10},
    "cdn_edge": {"type": "network", "team": "network", "criticality": 7},
    "dns_primary": {"type": "network", "team": "network", "criticality": 10},
}

INFRASTRUCTURE: dict[str, dict] = {
    "k8s_cluster_prod": {"type": "infrastructure", "team": "platform", "criticality": 10},
    "k8s_cluster_staging": {"type": "infrastructure", "team": "platform", "criticality": 5},
    "docker_registry": {"type": "infrastructure", "team": "platform", "criticality": 8},
    "ci_runner": {"type": "infrastructure", "team": "platform", "criticality": 6},
    "artifact_storage": {"type": "infrastructure", "team": "platform", "criticality": 7},
    "consul_service_mesh": {"type": "infrastructure", "team": "platform", "criticality": 8},
    "istio_sidecar": {"type": "infrastructure", "team": "platform", "criticality": 7},
    "cert_manager": {"type": "infrastructure", "team": "platform", "criticality": 8},
    "vault_secrets": {"type": "infrastructure", "team": "security", "criticality": 10},
    "log_aggregator": {"type": "infrastructure", "team": "sre", "criticality": 7},
    "tracing_jaeger": {"type": "infrastructure", "team": "sre", "criticality": 6},
    "backup_storage": {"type": "infrastructure", "team": "data", "criticality": 9},
    "storage_s3": {"type": "infrastructure", "team": "platform", "criticality": 8},
    "storage_nfs": {"type": "infrastructure", "team": "platform", "criticality": 6},
    "service_discovery": {"type": "infrastructure", "team": "platform", "criticality": 8},
}

DEPENDS_ON: list[tuple[str, str]] = [
    ("web_frontend", "api_gateway"),
    ("mobile_bff", "api_gateway"),
    ("api_gateway", "auth_service"),
    ("api_gateway", "user_service"),
    ("api_gateway", "order_service"),
    ("api_gateway", "search_service"),
    ("api_gateway", "catalog_service"),
    ("api_gateway", "cart_service"),
    ("api_gateway", "review_service"),
    ("api_gateway", "payment_service"),
    ("auth_service", "redis_cache_auth"),
    ("auth_service", "postgres_users"),
    ("auth_service", "redis_sessions"),
    ("auth_service", "vault_secrets"),
    ("user_service", "postgres_users"),
    ("user_service", "auth_service"),
    ("user_service", "redis_cache_auth"),
    ("order_service", "postgres_orders"),
    ("order_service", "inventory_service"),
    ("order_service", "payment_service"),
    ("order_service", "rabbitmq_orders"),
    ("order_service", "user_service"),
    ("payment_service", "postgres_payments"),
    ("payment_service", "sqs_payments"),
    ("payment_service", "redis_cache_auth"),
    ("payment_service", "vault_secrets"),
    ("inventory_service", "postgres_inventory"),
    ("inventory_service", "postgres_products"),
    ("notification_service", "rabbitmq_notifications"),
    ("notification_service", "email_service"),
    ("notification_service", "sms_service"),
    ("search_service", "elastic_search_idx"),
    ("search_service", "redis_cache_search"),
    ("search_service", "catalog_service"),
    ("search_service", "kafka_events"),
    ("analytics_service", "mongo_analytics"),
    ("analytics_service", "kafka_analytics"),
    ("analytics_service", "cassandra_events"),
    ("reporting_service", "postgres_orders"),
    ("reporting_service", "analytics_service"),
    ("recommendation_engine", "redis_cache_recommendations"),
    ("recommendation_engine", "cassandra_events"),
    ("recommendation_engine", "user_service"),
    ("pricing_service", "postgres_products"),
    ("pricing_service", "redis_cache_products"),
    ("shipping_service", "postgres_orders"),
    ("shipping_service", "inventory_service"),
    ("email_service", "file_service"),
    ("sms_service", "config_service"),
    ("cart_service", "redis_cache_cart"),
    ("cart_service", "catalog_service"),
    ("cart_service", "pricing_service"),
    ("review_service", "postgres_reviews"),
    ("review_service", "user_service"),
    ("coupon_service", "postgres_products"),
    ("coupon_service", "cart_service"),
    ("scheduler_service", "config_service"),
    ("scheduler_service", "rabbitmq_notifications"),
    ("graphql_gateway", "api_gateway"),
    ("graphql_gateway", "analytics_service"),
    ("catalog_service", "postgres_products"),
    ("catalog_service", "redis_cache_products"),
    ("catalog_service", "search_service"),
    ("file_service", "storage_s3"),
    ("file_service", "storage_nfs"),
    ("lb_web", "dns_primary"),
    ("lb_api", "dns_primary"),
    ("k8s_cluster_prod", "docker_registry"),
    ("k8s_cluster_prod", "consul_service_mesh"),
    ("k8s_cluster_prod", "cert_manager"),
    ("k8s_cluster_prod", "vault_secrets"),
    ("k8s_cluster_prod", "istio_sidecar"),
    ("k8s_cluster_prod", "service_discovery"),
    ("k8s_cluster_staging", "docker_registry"),
    ("ci_runner", "docker_registry"),
    ("ci_runner", "artifact_storage"),
    ("log_aggregator", "tracing_jaeger"),
    ("tracing_jaeger", "elastic_search_idx"),
    ("config_service", "vault_secrets"),
    ("config_service", "postgres_configs"),
]

ROUTES_TO: list[tuple[str, str]] = [
    ("lb_web", "web_frontend"),
    ("lb_web", "cdn_edge"),
    ("lb_api", "api_gateway"),
    ("lb_api", "graphql_gateway"),
    ("lb_internal", "auth_service"),
    ("lb_internal", "user_service"),
    ("lb_internal", "order_service"),
    ("lb_internal", "payment_service"),
    ("lb_internal", "inventory_service"),
    ("lb_analytics", "analytics_service"),
    ("lb_analytics", "reporting_service"),
    ("lb_search", "search_service"),
    ("lb_search", "elastic_search_idx"),
    ("cdn_edge", "web_frontend"),
    ("vpn_gateway", "lb_internal"),
    ("dns_primary", "lb_web"),
]

CONNECTS_TO: list[tuple[str, str]] = [
    ("network_segment_dmz", "lb_web"),
    ("network_segment_dmz", "lb_api"),
    ("network_segment_dmz", "vpn_gateway"),
    ("network_segment_dmz", "firewall_core"),
    ("network_segment_internal", "lb_internal"),
    ("network_segment_internal", "network_segment_dmz"),
    ("network_segment_internal", "k8s_cluster_prod"),
    ("network_segment_database", "postgres_users"),
    ("network_segment_database", "postgres_orders"),
    ("network_segment_database", "postgres_payments"),
    ("network_segment_database", "postgres_inventory"),
    ("network_segment_database", "postgres_products"),
    ("network_segment_database", "mongo_analytics"),
    ("network_segment_database", "cassandra_events"),
    ("network_segment_database", "elastic_search_idx"),
    ("network_segment_database", "timescale_metrics"),
    ("network_segment_database", "postgres_configs"),
    ("network_segment_database", "postgres_reviews"),
    ("network_segment_cache", "redis_cache_auth"),
    ("network_segment_cache", "redis_cache_products"),
    ("network_segment_cache", "redis_cache_search"),
    ("network_segment_cache", "redis_cache_recommendations"),
    ("network_segment_cache", "memcached_sessions"),
    ("network_segment_cache", "redis_cache_cart"),
    ("network_segment_cache", "redis_sessions"),
    ("firewall_core", "network_segment_internal"),
]

MONITORS_EDGES: list[tuple[str, str]] = [
    ("prometheus", "api_gateway"),
    ("prometheus", "auth_service"),
    ("prometheus", "user_service"),
    ("prometheus", "order_service"),
    ("prometheus", "payment_service"),
    ("prometheus", "search_service"),
    ("grafana", "prometheus"),
    ("datadog", "k8s_cluster_prod"),
    ("datadog", "network_segment_internal"),
    ("sentry", "api_gateway"),
    ("sentry", "auth_service"),
    ("sentry", "user_service"),
    ("pagerduty", "prometheus"),
    ("log_aggregator", "k8s_cluster_prod"),
]

CACHES_FOR: list[tuple[str, str]] = [
    ("redis_cache_auth", "postgres_users"),
    ("redis_cache_auth", "auth_service"),
    ("redis_cache_products", "postgres_products"),
    ("redis_cache_search", "elastic_search_idx"),
    ("redis_cache_recommendations", "cassandra_events"),
    ("memcached_sessions", "redis_sessions"),
    ("redis_cache_cart", "postgres_orders"),
]

REPLICATES_TO: list[tuple[str, str]] = [
    ("postgres_users", "backup_storage"),
    ("postgres_orders", "backup_storage"),
    ("postgres_payments", "backup_storage"),
    ("postgres_inventory", "backup_storage"),
    ("redis_cache_auth", "redis_cache_search"),
    ("redis_cache_products", "redis_cache_search"),
    ("cassandra_events", "backup_storage"),
]

PUBLISHES_TO: list[tuple[str, str]] = [
    ("kafka_ingestion", "kafka_analytics"),
    ("kafka_ingestion", "kafka_events"),
    ("kafka_events", "analytics_service"),
    ("rabbitmq_orders", "shipping_service"),
    ("rabbitmq_orders", "notification_service"),
    ("sqs_payments", "notification_service"),
    ("kafka_analytics", "reporting_service"),
    ("scheduler_service", "kafka_events"),
]

SYMPTOMS: list[tuple[str, str]] = [
    ("auth_service", "authentication timeout errors"),
    ("user_service", "slow profile lookup responses"),
    ("api_gateway", "502 bad gateway responses"),
    ("search_service", "degraded query performance"),
    ("payment_service", "transaction processing failures"),
    ("reporting_service", "stale dashboard data"),
]


class OverlayTransaction:
    """Manual overlay simulation on top of a networkx DiGraph.

    Tracks nodes/edges added during a transactional exploration.
    commit() applies changes to the base graph.
    rollback() discards the overlay copy entirely.
    """

    def __init__(self, base: nx.DiGraph):
        self.base = base
        self.overlay = base.copy()
        self.added_nodes: list[str] = []
        self.added_edges: list[tuple[str, str, dict]] = []
        self.confidence: dict[tuple[str, str, str], float] = {}

    def add_node(self, label: str, **kwargs) -> None:
        if label not in self.overlay:
            self.added_nodes.append(label)
        self.overlay.add_node(label, **kwargs)

    def add_edge(self, src: str, tgt: str, label: str, confidence: float = 0.8) -> None:
        self.added_edges.append((src, tgt, {"label": label, "confidence": confidence}))
        self.confidence[(src, tgt, label)] = confidence
        self.overlay.add_edge(src, tgt, label=label, confidence=confidence)

    def commit(self) -> dict:
        committed_nodes = 0
        committed_edges = 0
        for node in self.added_nodes:
            if node not in self.base:
                self.base.add_node(node, **self.overlay.nodes[node])
                committed_nodes += 1
        for src, tgt, data in self.added_edges:
            if not self.base.has_edge(src, tgt):
                self.base.add_edge(src, tgt, **data)
                committed_edges += 1
            elif self.base[src][tgt].get("label") != data.get("label"):
                self.base.add_edge(src, tgt, **data)
                committed_edges += 1
        return {"committed_nodes": committed_nodes, "committed_edges": committed_edges}

    def rollback(self) -> dict:
        count = len(self.added_edges)
        self.overlay = None
        self.added_nodes = []
        self.added_edges = []
        self.confidence = {}
        return {"rolled_back_edges": count}

    def get_edge_details(self) -> list[dict]:
        details = []
        for src, tgt, data in self.added_edges:
            label = data.get("label", "")
            conf = data.get("confidence", 0.0)
            details.append({"source": src, "target": tgt, "label": label, "confidence": conf})
        return details


def build_infrastructure(G: nx.DiGraph) -> None:
    all_nodes: dict[str, dict] = {}
    all_nodes.update(SERVICES)
    all_nodes.update(DATABASES)
    all_nodes.update(CACHES)
    all_nodes.update(QUEUES)
    all_nodes.update(LOAD_BALANCERS)
    all_nodes.update(MONITORING)
    all_nodes.update(NETWORK)
    all_nodes.update(INFRASTRUCTURE)

    for label, data in all_nodes.items():
        G.add_node(label, **data)

    edge_groups: list[tuple[list[tuple[str, str]], str]] = [
        (DEPENDS_ON, "depends_on"),
        (ROUTES_TO, "routes_to"),
        (CONNECTS_TO, "connects_to"),
        (MONITORS_EDGES, "monitors"),
        (CACHES_FOR, "caches_for"),
        (REPLICATES_TO, "replicates_to"),
        (PUBLISHES_TO, "publishes_to"),
    ]
    for edges, label in edge_groups:
        for src, tgt in edges:
            G.add_edge(src, tgt, label=label)


def find_transitive_chains(G: nx.DiGraph, edge_label: str, new_label: str) -> list[tuple[str, str, str]]:
    edges_of_label = {(u, v) for u, v, d in G.edges(data=True) if d.get("label") == edge_label}
    chains = []
    for a, b in edges_of_label:
        for b2, c in edges_of_label:
            if b == b2 and a != c:
                chains.append((a, b, c))
    return chains


def find_inverse_edges(G: nx.DiGraph, edge_label: str) -> list[tuple[str, str]]:
    edges_of_label = {(u, v) for u, v, d in G.edges(data=True) if d.get("label") == edge_label}
    pairs = []
    for u, v in edges_of_label:
        if (v, u) in edges_of_label:
            pairs.append((u, v))
    return pairs


def expand_hypothesis(
    G: nx.DiGraph,
    seeds: set[str],
    symptom_labels: set[str],
    max_depth: int = 3,
    decay: float = 0.9,
) -> dict:
    overlay = OverlayTransaction(G)

    visited: set[str] = set()
    frontier: set[str] = set(seeds)
    rules_applied = 0
    states_created = 0

    for depth in range(max_depth):
        next_frontier: set[str] = set()
        for node in frontier:
            if node in visited:
                continue
            visited.add(node)
            states_created += 1

            for _, tgt, data in G.out_edges(node, data=True):
                label = data.get("label", "")
                if label == "depends_on":
                    conf = decay ** (depth + 1)
                    overlay.add_edge(node, tgt, "indirectly_depends_on", confidence=conf)
                    rules_applied += 1
                    if tgt not in visited:
                        next_frontier.add(tgt)

            for pred, _, data in G.in_edges(node, data=True):
                label = data.get("label", "")
                if label == "depends_on":
                    conf = decay ** (depth + 1)
                    overlay.add_edge(pred, node, "depended_on_by", confidence=conf)
                    rules_applied += 1

        frontier = next_frontier
        if not frontier:
            break

    blast_radius: set[str] = set()
    for src, tgt, data in overlay.added_edges:
        if src in symptom_labels:
            blast_radius.add(src)
        if tgt in symptom_labels:
            blast_radius.add(tgt)

    overlay_details = overlay.get_edge_details()
    confidences = [d["confidence"] for d in overlay_details]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    matched_labels = sorted(blast_radius)

    return {
        "overlay": overlay,
        "overlay_details": overlay_details,
        "blast_radius": matched_labels,
        "match_count": len(blast_radius),
        "match_score": len(blast_radius) / len(symptom_labels) if symptom_labels else 0.0,
        "avg_confidence": avg_conf,
        "states_created": states_created,
        "rules_applied": rules_applied,
        "edges_produced": len(overlay_details),
    }


def print_hypothesis_report(
    name: str,
    description: str,
    seeds: set[str],
    analysis: dict,
) -> None:
    print(f"  Hypothesis: {name}")
    print(f"  Description: {description}")
    print(f"  Seeds: {', '.join(sorted(seeds))}")
    print(f"  Expansion: {analysis['states_created']} states, "
          f"{analysis['rules_applied']} rules applied, "
          f"{analysis['edges_produced']} edges produced")
    print(f"  Overlay: {len(analysis['overlay_details'])} edges, "
          f"{len(analysis['overlay'].added_nodes)} new nodes")
    print()

    if analysis["overlay_details"]:
        print("  Inferred edges:")
        for d in analysis["overlay_details"]:
            print(f"    {d['source']} --[{d['label']}]--> {d['target']}"
                  f"  (confidence={d['confidence']:.2f})")
    else:
        print("  No inference edges produced.")
    print()

    if analysis["blast_radius"]:
        print(f"  Blast radius matches: {', '.join(analysis['blast_radius'])}")
    else:
        print("  Blast radius: no symptom services matched")
    print(f"  Match score: {analysis['match_count']}/{len(SYMPTOMS)} "
          f"symptoms ({analysis['match_score']:.0%})")
    print(f"  Average confidence: {analysis['avg_confidence']:.2f}")
    print()


def main() -> None:
    G = nx.DiGraph()

    print("=" * 70)
    print("SECTION 1: Building Microservices Infrastructure Graph")
    print("=" * 70)

    build_infrastructure(G)

    service_count = len(SERVICES)
    db_count = len(DATABASES)
    cache_count = len(CACHES)
    queue_count = len(QUEUES)
    lb_count = len(LOAD_BALANCERS)
    mon_count = len(MONITORING)
    net_count = len(NETWORK)
    infra_count = len(INFRASTRUCTURE)
    total_nodes = (service_count + db_count + cache_count + queue_count
                   + lb_count + mon_count + net_count + infra_count)

    print(f"  Services:       {service_count:>3}")
    print(f"  Databases:      {db_count:>3}")
    print(f"  Caches:         {cache_count:>3}")
    print(f"  Queues:         {queue_count:>3}")
    print(f"  Load balancers: {lb_count:>3}")
    print(f"  Monitoring:     {mon_count:>3}")
    print(f"  Network:        {net_count:>3}")
    print(f"  Infrastructure: {infra_count:>3}")
    print(f"  -------------------")
    print(f"  Total nodes:    {total_nodes:>3}")
    print(f"  Total edges:    {G.number_of_edges():>3}")
    print()

    print("  Edge types:")
    print(f"    depends_on:    {len(DEPENDS_ON):>3}")
    print(f"    routes_to:     {len(ROUTES_TO):>3}")
    print(f"    connects_to:   {len(CONNECTS_TO):>3}")
    print(f"    monitors:      {len(MONITORS_EDGES):>3}")
    print(f"    caches_for:    {len(CACHES_FOR):>3}")
    print(f"    replicates_to: {len(REPLICATES_TO):>3}")
    print(f"    publishes_to:  {len(PUBLISHES_TO):>3}")
    print()

    print("=" * 70)
    print("SECTION 2: Observed Symptoms")
    print("=" * 70)

    print("  On-call has identified the following production errors:")
    print()
    for label, desc in SYMPTOMS:
        print(f"    {label:<25} {desc}")
    print()

    symptom_labels: set[str] = set()
    for label, _ in SYMPTOMS:
        if label in G:
            symptom_labels.add(label)
    print(f"  {len(symptom_labels)} symptom services require explanation")
    print()

    base_edge_count = G.number_of_edges()

    print("=" * 70)
    print("SECTION 3: Hypothesis A - Redis Cache Auth Failure (CORRECT)")
    print("=" * 70)

    seeds_a = {"redis_cache_auth", "auth_service", "user_service", "api_gateway", "payment_service"}
    analysis_a = expand_hypothesis(G, seeds_a, symptom_labels)
    print_hypothesis_report(
        "A", "redis_cache_auth authentication cache failure", seeds_a, analysis_a
    )

    print("  Verdict: STRONG MATCH - blast radius covers most symptoms")
    print("  Action: Rollback for now, will re-test and commit after comparing")
    rb = analysis_a["overlay"].rollback()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {G.number_of_edges()} edges (unchanged)")
    print()

    print("=" * 70)
    print("SECTION 4: Hypothesis B - Network Segment DMZ Issue (INCORRECT)")
    print("=" * 70)

    seeds_b = {"network_segment_dmz", "lb_web", "lb_api", "dns_primary"}
    analysis_b = expand_hypothesis(G, seeds_b, symptom_labels)
    print_hypothesis_report(
        "B", "DMZ network segment partition or misconfiguration", seeds_b, analysis_b
    )

    print("  Verdict: NO MATCH - inferred edges do not reach any symptom services")
    print("  Action: Rollback - hypothesis does not explain observed failures")
    rb = analysis_b["overlay"].rollback()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {G.number_of_edges()} edges (unchanged)")
    print()

    print("=" * 70)
    print("SECTION 5: Hypothesis C - Kafka Ingestion Cluster Issue (PARTIAL)")
    print("=" * 70)

    seeds_c = {"kafka_ingestion", "kafka_analytics", "kafka_events",
               "analytics_service", "reporting_service", "search_service"}
    analysis_c = expand_hypothesis(G, seeds_c, symptom_labels)
    print_hypothesis_report(
        "C", "Kafka ingestion cluster degradation or partition", seeds_c, analysis_c
    )

    print("  Verdict: PARTIAL MATCH - explains some symptoms but not critical ones")
    print("  Action: Rollback - incomplete explanation for auth/payment failures")
    rb = analysis_c["overlay"].rollback()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {G.number_of_edges()} edges (unchanged)")
    print()

    print("=" * 70)
    print("SECTION 6: Comparative Analysis")
    print("=" * 70)

    print(f"  {'Metric':<30} {'Hyp A':>8} {'Hyp B':>8} {'Hyp C':>8}")
    print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8}")
    print(f"  {'Overlay edges':<30} "
          f"{len(analysis_a['overlay_details']):>8} "
          f"{len(analysis_b['overlay_details']):>8} "
          f"{len(analysis_c['overlay_details']):>8}")
    print(f"  {'Symptoms matched':<30} "
          f"{analysis_a['match_count']:>8} "
          f"{analysis_b['match_count']:>8} "
          f"{analysis_c['match_count']:>8}")
    print(f"  {'Match score':<30} "
          f"{analysis_a['match_score']:>7.0%} "
          f"{analysis_b['match_score']:>7.0%} "
          f"{analysis_c['match_score']:>7.0%}")
    print(f"  {'Avg confidence':<30} "
          f"{analysis_a['avg_confidence']:>8.2f} "
          f"{analysis_b['avg_confidence']:>8.2f} "
          f"{analysis_c['avg_confidence']:>8.2f}")
    print()
    print("  Conclusion: Hypothesis A (redis_cache_auth) is the root cause.")
    print("  It explains the most symptoms with high confidence.")
    print()

    print("=" * 70)
    print("SECTION 7: Committing Correct Hypothesis")
    print("=" * 70)

    print("  Re-running hypothesis A reasoning...")
    analysis_final = expand_hypothesis(G, seeds_a, symptom_labels)

    if analysis_final["overlay"].added_edges:
        print(f"  Overlay contains {len(analysis_final['overlay'].added_edges)} inference edges")
        print()

        print("  Committing overlay to base graph...")
        committed = analysis_final["overlay"].commit()
        print(f"  Committed: {committed['committed_nodes']} nodes, "
              f"{committed['committed_edges']} edges")
    else:
        print("  No overlay to commit.")
    print()

    print("=" * 70)
    print("SECTION 8: Before / After Comparison")
    print("=" * 70)

    print(f"  Base graph edges before: {base_edge_count}")
    print(f"  Base graph edges after:  {G.number_of_edges()}")
    print(f"  Inference edges added:   {G.number_of_edges() - base_edge_count}")
    print()
    print(f"  Overlay active: {analysis_final['overlay'].overlay is not None}")
    print()

    print("  Committed inferences now in the base graph:")
    for d in analysis_final["overlay_details"]:
        print(f"    {d['source']} --[{d['label']}]--> {d['target']}")
    print()

    print("=" * 70)
    print("SECTION 9: Why Overlay Matters")
    print("=" * 70)

    wrong_edges = (len(analysis_b["overlay_details"])
                   + len(analysis_c["overlay_details"]))
    print(f"  Without overlay, investigating hypotheses B and C would have")
    print(f"  injected {wrong_edges} incorrect inference edges into the graph.")
    print()
    print("  With overlay:")
    print("    - Each hypothesis explored in isolation (scratchpad)")
    print("    - Wrong hypotheses rolled back cleanly (no pollution)")
    print("    - Correct hypothesis committed with full provenance")
    print("    - Base graph only contains verified inferences")
    print()
    print("  This is critical for incident investigation where multiple")
    print("  team members propose competing theories simultaneously.")
    print()

    print("=" * 70)
    print("SECTION 10: Boilerplate Comparison")
    print("=" * 70)
    print()
    print("  What Hyper3 gives you for free (that we had to build manually):")
    print()
    print("  1. OverlayTransaction class (~50 lines)")
    print("     - G.copy() for snapshot")
    print("     - Manual tracking of added_nodes, added_edges, confidence")
    print("     - commit() iterates and adds to base graph")
    print("     - rollback() nulls the overlay reference")
    print()
    print("  2. Transitive chain discovery (~15 lines)")
    print("     - Must build edge sets manually")
    print("     - Nested loop over all same-label edge pairs")
    print()
    print("  3. Inverse edge discovery (~10 lines)")
    print("     - Must build edge sets, check reverse membership")
    print()
    print("  4. Hypothesis expansion (~40 lines)")
    print("     - Manual BFS with confidence decay tracking")
    print("     - Manual blast radius calculation")
    print("     - No rule engine, no multiway expansion")
    print()
    print("  Total boilerplate: ~115 lines to replicate what Hyper3 does")
    print("  with mem.reason() + mem.commit_inferences().")
    print()


if __name__ == "__main__":
    main()
