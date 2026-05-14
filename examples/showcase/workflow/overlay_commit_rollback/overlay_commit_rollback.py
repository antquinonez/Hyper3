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
    .venv/bin/python examples/showcase/workflow/overlay_commit_rollback/overlay_commit_rollback.py
"""

from __future__ import annotations

from collections import deque

from hyper3 import (
    HypergraphMemory,
    TransitiveRule,
    Modality,
)

SERVICES: dict[str, dict] = {
    "api_gateway": {"type": "service", "team": "platform", "criticality": 9},
    "auth_service": {"type": "service", "team": "identity", "criticality": 10},
    "user_service": {"type": "service", "team": "identity", "criticality": 8},
    "payment_service": {"type": "service", "team": "commerce", "criticality": 10},
    "search_service": {"type": "service", "team": "catalog", "criticality": 6},
    "reporting_service": {"type": "service", "team": "data", "criticality": 5},
    "order_service": {"type": "service", "team": "commerce", "criticality": 9},
    "catalog_service": {"type": "service", "team": "catalog", "criticality": 8},
    "web_frontend": {"type": "service", "team": "platform", "criticality": 8},
    "mobile_bff": {"type": "service", "team": "platform", "criticality": 7},
    "notification_service": {"type": "service", "team": "platform", "criticality": 4},
    "email_service": {"type": "service", "team": "platform", "criticality": 4},
}

INFRASTRUCTURE: dict[str, dict] = {
    "redis_cache_auth": {"type": "cache", "team": "platform", "criticality": 9},
    "postgres_users": {"type": "database", "team": "data", "criticality": 9},
    "postgres_payments": {"type": "database", "team": "data", "criticality": 10},
    "elastic_search_idx": {"type": "database", "team": "data", "criticality": 7},
    "mongo_analytics": {"type": "database", "team": "data", "criticality": 7},
    "redis_sessions": {"type": "cache", "team": "platform", "criticality": 8},
}

QUEUES: dict[str, dict] = {
    "kafka_ingestion": {"type": "queue", "team": "platform", "criticality": 8},
    "kafka_analytics": {"type": "queue", "team": "data", "criticality": 7},
    "kafka_events": {"type": "queue", "team": "platform", "criticality": 7},
}

NETWORK: dict[str, dict] = {
    "network_segment_dmz": {"type": "network", "team": "network", "criticality": 9},
    "lb_web": {"type": "load_balancer", "team": "infra", "criticality": 9},
    "lb_api": {"type": "load_balancer", "team": "infra", "criticality": 9},
    "dns_primary": {"type": "network", "team": "network", "criticality": 10},
    "firewall_core": {"type": "network", "team": "network", "criticality": 10},
    "cdn_edge": {"type": "network", "team": "network", "criticality": 7},
    "vpn_gateway": {"type": "network", "team": "network", "criticality": 8},
    "lb_internal": {"type": "load_balancer", "team": "infra", "criticality": 8},
}

DEPENDS_ON: list[tuple[str, str]] = [
    ("api_gateway", "auth_service"),
    ("api_gateway", "user_service"),
    ("api_gateway", "order_service"),
    ("api_gateway", "search_service"),
    ("api_gateway", "payment_service"),
    ("auth_service", "redis_cache_auth"),
    ("auth_service", "postgres_users"),
    ("user_service", "postgres_users"),
    ("user_service", "auth_service"),
    ("user_service", "redis_cache_auth"),
    ("payment_service", "postgres_payments"),
    ("payment_service", "redis_cache_auth"),
    ("order_service", "payment_service"),
    ("order_service", "user_service"),
    ("web_frontend", "api_gateway"),
    ("mobile_bff", "api_gateway"),
    ("search_service", "elastic_search_idx"),
    ("catalog_service", "search_service"),
    ("reporting_service", "mongo_analytics"),
    ("notification_service", "email_service"),
]

CONNECTS_TO: list[tuple[str, str]] = [
    ("network_segment_dmz", "lb_web"),
    ("network_segment_dmz", "lb_api"),
    ("network_segment_dmz", "vpn_gateway"),
    ("network_segment_dmz", "firewall_core"),
    ("firewall_core", "cdn_edge"),
    ("vpn_gateway", "lb_internal"),
    ("lb_internal", "dns_primary"),
    ("lb_web", "cdn_edge"),
    ("lb_api", "cdn_edge"),
]

ROUTES_TO: list[tuple[str, str]] = [
    ("lb_web", "web_frontend"),
    ("lb_api", "api_gateway"),
    ("lb_internal", "order_service"),
    ("lb_api", "mobile_bff"),
]

PUBLISHES_TO: list[tuple[str, str]] = [
    ("kafka_ingestion", "kafka_analytics"),
    ("kafka_ingestion", "kafka_events"),
    ("kafka_analytics", "reporting_service"),
    ("kafka_events", "search_service"),
    ("kafka_events", "mongo_analytics"),
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
    all_nodes.update(INFRASTRUCTURE)
    all_nodes.update(QUEUES)
    all_nodes.update(NETWORK)

    for label, data in all_nodes.items():
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})

    edge_groups: list[tuple[list[tuple[str, str]], str]] = [
        (DEPENDS_ON, "depends_on"),
        (CONNECTS_TO, "connects_to"),
        (ROUTES_TO, "routes_to"),
        (PUBLISHES_TO, "publishes_to"),
    ]
    for edges, label in edge_groups:
        for src, tgt in edges:
            mem.link(src, tgt, label=label)


def analyze_hypothesis(
    mem: HypergraphMemory,
    seeds: set[str],
    symptom_ids: set[str],
) -> dict:
    result = mem.reason(
        seeds=seeds,
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
            _src = mem.engine.graph.get_node(next(iter(edge.source_ids)))
            _tgt = mem.engine.graph.get_node(next(iter(edge.target_ids)))
            src_label = _src.label if _src else ""
            tgt_label = _tgt.label if _tgt else ""
            conf = overlay.get_confidence(eid)
            overlay_details.append({
                "source": src_label,
                "target": tgt_label,
                "label": edge.label,
                "confidence": conf,
            })

        seed_ids: set[str] = set()
        for s in seeds:
            n = mem.engine.graph.get_node_by_label(s)
            if n:
                seed_ids.add(n.id)
        adj: dict[str, set[str]] = {}
        for eid in overlay.overlay_edge_ids:
            edge = overlay.get_edge(eid)
            if edge:
                for src in edge.source_ids:
                    adj.setdefault(src, set()).update(edge.target_ids)

        visited = set(seed_ids)
        queue = deque(seed_ids)
        while queue:
            node = queue.popleft()
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        for nid in visited:
            if nid in symptom_ids:
                node = mem.engine.graph.get_node(nid)
                if node:
                    blast_radius.add(node.label)

    confidence_map = result.confidence or {}
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

    print(f"  Hypothesis: {name}")
    print(f"  Description: {description}")
    print(f"  Seeds: {', '.join(sorted(seeds))}")
    print(f"  Expansion: {exp.states_created} states, "
          f"{exp.rules_applied} rules applied, "
          f"{exp.edges_produced} edges produced")
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
    print("SECTION 1: Building Infrastructure Graph")
    print("=" * 70)

    build_infrastructure(mem)

    print(f"  Nodes:        {mem.size[0]:>3}")
    print(f"  Edges:        {mem.size[1]:>3}")
    print()
    print("  Edge types:")
    print(f"    depends_on:    {len(DEPENDS_ON):>3}")
    print(f"    connects_to:   {len(CONNECTS_TO):>3}")
    print(f"    routes_to:     {len(ROUTES_TO):>3}")
    print(f"    publishes_to:  {len(PUBLISHES_TO):>3}")
    print()

    print("=" * 70)
    print("SECTION 2: Recording Observed Symptoms")
    print("=" * 70)

    print("  On-call has identified the following production errors:")
    print()
    for label, desc in SYMPTOMS:
        print(f"    {label:<25} {desc}")
    print()

    symptom_ids: set[str] = set()
    for label, _ in SYMPTOMS:
        node = mem.engine.graph.get_node_by_label(label)
        if node:
            symptom_ids.add(node.id)
    print(f"  {len(symptom_ids)} symptom services require explanation")
    print()

    base_edge_count = mem.size[1]

    for lbl in ["depends_on", "connects_to", "publishes_to", "routes_to"]:
        mem.add_rules(TransitiveRule(edge_label=lbl, new_label=f"indirectly_{lbl}"))

    print("=" * 70)
    print("SECTION 3: Hypothesis A - Redis Cache Auth Failure (CORRECT)")
    print("=" * 70)

    seeds_a = {"redis_cache_auth", "auth_service", "user_service", "api_gateway", "payment_service"}
    analysis_a = analyze_hypothesis(mem, seeds_a, symptom_ids)
    print_hypothesis_report(
        "A", "Redis cache auth failure", seeds_a, analysis_a
    )

    print("  Verdict: STRONG MATCH - blast radius covers most symptoms")
    print("  Action: Rollback for now, will re-test and commit after comparing")
    rb = mem.rollback_inferences()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {mem.size[1]} edges (unchanged)")
    print()

    print("=" * 70)
    print("SECTION 4: Hypothesis B - Network Segment DMZ (INCORRECT)")
    print("=" * 70)

    seeds_b = {"network_segment_dmz", "lb_web", "lb_api", "dns_primary", "vpn_gateway"}
    analysis_b = analyze_hypothesis(mem, seeds_b, symptom_ids)
    print_hypothesis_report(
        "B", "DMZ network segment partition or misconfiguration", seeds_b, analysis_b
    )

    print("  Verdict: NO MATCH - inferred edges do not reach any symptom services")
    print("  Action: Rollback - hypothesis does not explain observed failures")
    rb = mem.rollback_inferences()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {mem.size[1]} edges (unchanged)")
    print()

    print("=" * 70)
    print("SECTION 5: Hypothesis C - Kafka Ingestion (PARTIAL)")
    print("=" * 70)

    seeds_c = {"kafka_ingestion", "kafka_analytics", "kafka_events"}
    analysis_c = analyze_hypothesis(mem, seeds_c, symptom_ids)
    print_hypothesis_report(
        "C", "Kafka cluster degradation or partition", seeds_c, analysis_c
    )

    print("  Verdict: PARTIAL MATCH - explains some symptoms but not critical ones")
    print("  Action: Rollback - incomplete explanation for auth/payment failures")
    rb = mem.rollback_inferences()
    print(f"  Rolled back: {rb['rolled_back_edges']} edges")
    print(f"  Base graph intact: {mem.size[1]} edges (unchanged)")
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
    print(f"  Base graph edges after:  {mem.size[1]}")
    print(f"  Inference edges added:   {mem.size[1] - base_edge_count}")
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
