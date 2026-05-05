"""
Speculative Incident Investigation with Overlay
================================================

An SRE team investigates why their application is down. They build a
microservices infrastructure graph, identify 6 services reporting errors,
and use the overlay system to explore 3 competing root-cause hypotheses
without contaminating the base knowledge graph.

The overlay acts as a scratchpad: each hypothesis is tested in isolation,
reviewed against observed symptoms, and either committed (correct) or
rolled back (wrong).  Only the winning hypothesis persists.

Run with:
    .venv/bin/python examples/showcase/overlay_commit_rollback/08_overlay_commit_rollback.py
"""

from __future__ import annotations

from hyper3 import (
    HypergraphMemory,
    TransitiveRule,
    InverseRule,
    Modality,
)

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


def build_infrastructure(mem: HypergraphMemory) -> None:
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
        mem.store(label, data=data, modalities={Modality.CONCEPTUAL})

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
            mem.relate(src, tgt, label=label)


def analyze_hypothesis(
    mem: HypergraphMemory,
    seeds: set[str],
    symptom_ids: set[str],
) -> dict:
    result = mem.reason(
        seed_concepts=seeds,
        max_depth=3,
        max_total_states=30,
        auto_commit=False,
        confidence_decay=0.9,
    )

    overlay = mem.overlay
    blast_radius: set[str] = set()
    overlay_details: list[dict] = []

    if overlay:
        for eid in sorted(overlay.overlay_edge_ids):
            edge = overlay.get_edge(eid)
            if not edge:
                continue
            _src = mem.graph.get_node(next(iter(edge.source_ids)))
            _tgt = mem.graph.get_node(next(iter(edge.target_ids)))
            src_label = _src.label if _src else ""
            tgt_label = _tgt.label if _tgt else ""
            conf = overlay.get_confidence(eid)
            overlay_details.append({
                "source": src_label,
                "target": tgt_label,
                "label": edge.label,
                "confidence": conf,
            })
            for nid in edge.source_ids | edge.target_ids:
                if nid in symptom_ids:
                    node = mem.graph.get_node(nid)
                    if node:
                        blast_radius.add(node.label)

    confidence_map = result.get("confidence", {})
    avg_conf = (
        sum(confidence_map.values()) / len(confidence_map)
        if confidence_map
        else 0.0
    )

    return {
        "result": result,
        "overlay_details": overlay_details,
        "blast_radius": sorted(blast_radius),
        "match_count": len(blast_radius),
        "match_score": len(blast_radius) / len(symptom_ids) if symptom_ids else 0.0,
        "avg_confidence": avg_conf,
    }


def print_hypothesis_report(
    name: str,
    description: str,
    seeds: set[str],
    analysis: dict,
) -> None:
    exp = analysis["result"].expansion
    overlay_info = analysis["result"].get("overlay", {})

    print(f"  Hypothesis: {name}")
    print(f"  Description: {description}")
    print(f"  Seeds: {', '.join(sorted(seeds))}")
    print(f"  Expansion: {exp.states_created} states, "
          f"{exp.rules_applied} rules applied, "
          f"{exp.edges_produced} edges produced")
    print(f"  Overlay: {overlay_info.get('edge_count', 0)} edges, "
          f"{overlay_info.get('node_count', 0)} new nodes")
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
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building Microservices Infrastructure Graph")
    print("=" * 70)

    build_infrastructure(mem)

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
    print(f"  Total edges:    {mem.graph.edge_count:>3}")
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

    symptom_ids: set[str] = set()
    for label, _ in SYMPTOMS:
        node = mem.graph.get_node_by_label(label)
        if node:
            symptom_ids.add(node.id)
    print(f"  {len(symptom_ids)} symptom services require explanation")
    print()

    base_edge_count = mem.graph.edge_count

    mem.add_rules(
        TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on"),
        InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
    )

    print("=" * 70)
    print("SECTION 3: Hypothesis A - Redis Cache Auth Failure (CORRECT)")
    print("=" * 70)

    seeds_a = {"redis_cache_auth", "auth_service", "user_service", "api_gateway", "payment_service"}
    analysis_a = analyze_hypothesis(mem, seeds_a, symptom_ids)
    print_hypothesis_report(
        "A", "redis_cache_auth authentication cache failure", seeds_a, analysis_a
    )

    print("  Verdict: STRONG MATCH - blast radius covers most symptoms")
    print("  Action: Rollback for now, will re-test and commit after comparing")
    rb = mem.rollback_inferences()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {mem.graph.edge_count} edges (unchanged)")
    print()

    print("=" * 70)
    print("SECTION 4: Hypothesis B - Network Segment DMZ Issue (INCORRECT)")
    print("=" * 70)

    seeds_b = {"network_segment_dmz", "lb_web", "lb_api", "dns_primary"}
    analysis_b = analyze_hypothesis(mem, seeds_b, symptom_ids)
    print_hypothesis_report(
        "B", "DMZ network segment partition or misconfiguration", seeds_b, analysis_b
    )

    print("  Verdict: NO MATCH - inferred edges do not reach any symptom services")
    print("  Action: Rollback - hypothesis does not explain observed failures")
    rb = mem.rollback_inferences()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {mem.graph.edge_count} edges (unchanged)")
    print()

    print("=" * 70)
    print("SECTION 5: Hypothesis C - Kafka Inestion Cluster Issue (PARTIAL)")
    print("=" * 70)

    seeds_c = {"kafka_ingestion", "kafka_analytics", "kafka_events",
               "analytics_service", "reporting_service", "search_service"}
    analysis_c = analyze_hypothesis(mem, seeds_c, symptom_ids)
    print_hypothesis_report(
        "C", "Kafka ingestion cluster degradation or partition", seeds_c, analysis_c
    )

    print("  Verdict: PARTIAL MATCH - explains some symptoms but not critical ones")
    print("  Action: Rollback - incomplete explanation for auth/payment failures")
    rb = mem.rollback_inferences()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {mem.graph.edge_count} edges (unchanged)")
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
    analysis_final = analyze_hypothesis(mem, seeds_a, symptom_ids)

    if mem.overlay:
        print(f"  Overlay contains {len(mem.overlay.overlay_edge_ids)} inference edges")
        print()

        print("  Committing overlay to base graph...")
        committed = mem.commit_inferences()
        print(f"  Committed: {committed['committed_nodes']} nodes, "
              f"{committed['committed_edges']} edges")
    else:
        print("  No overlay to commit.")
    print()

    print("=" * 70)
    print("SECTION 8: Before / After Comparison")
    print("=" * 70)

    print(f"  Base graph edges before: {base_edge_count}")
    print(f"  Base graph edges after:  {mem.graph.edge_count}")
    print(f"  Inference edges added:   {mem.graph.edge_count - base_edge_count}")
    print()
    print(f"  Overlay active: {mem.overlay is not None}")
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


if __name__ == "__main__":
    main()
