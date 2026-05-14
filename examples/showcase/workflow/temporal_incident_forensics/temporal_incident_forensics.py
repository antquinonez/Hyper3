"""
Temporal Incident Forensics
===========================

First example demonstrating the temporal subsystem. Models a production
deployment incident as a temporal event graph, uses Allen interval relations
to establish causality, and auto-detects causal chains.

Also demonstrates infrastructure graph analysis for impact tracing.

Run with:
    .venv/bin/python examples/showcase/workflow/temporal_incident_forensics/temporal_incident_forensics.py
"""

from __future__ import annotations


def main() -> None:
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Infrastructure Graph Construction")
    print("=" * 70)

    components = {
        "api_gateway": {"tier": "edge", "team": "platform"},
        "auth_service": {"tier": "application", "team": "platform"},
        "order_service": {"tier": "application", "team": "commerce"},
        "payment_service": {"tier": "application", "team": "payments"},
        "connection_pool": {"tier": "infrastructure", "team": "platform"},
        "postgres": {"tier": "data", "team": "platform"},
        "redis": {"tier": "cache", "team": "platform"},
        "load_balancer": {"tier": "edge", "team": "platform"},
        "config_service": {"tier": "infrastructure", "team": "platform"},
    }
    for name, data in components.items():
        mem.add(name, data=data)

    deps = [
        ("api_gateway", "auth_service", "routes_to", 5.0),
        ("api_gateway", "order_service", "routes_to", 5.0),
        ("api_gateway", "payment_service", "routes_to", 5.0),
        ("auth_service", "connection_pool", "uses", 4.0),
        ("order_service", "connection_pool", "uses", 4.0),
        ("order_service", "redis", "uses", 3.0),
        ("payment_service", "postgres", "writes_to", 5.0),
        ("auth_service", "redis", "reads_from", 3.0),
        ("connection_pool", "postgres", "connects_to", 5.0),
        ("load_balancer", "api_gateway", "routes_to", 5.0),
        ("config_service", "connection_pool", "configures", 3.0),
        ("config_service", "api_gateway", "configures", 3.0),
    ]
    for src, tgt, label, weight in deps:
        mem.link(src, tgt, label=label, weight=weight)

    infra_nodes = len(components)
    print(f"  Infrastructure components: {infra_nodes}")
    print(f"  Dependency edges: {mem.size[1]}")
    print()

    print("=" * 70)
    print("SECTION 2: Incident Timeline Registration")
    print("=" * 70)
    print()

    temporal_events = [
        ("routine_deploy_v2_3", 0.0, 0.5, {"deployer": "ci_cd", "artifact": "config-service:v2.3"}),
        ("stale_config_pushed", 0.3, 0.8, {"error": "max_connections=50 instead of 500"}),
        ("db_pool_growth_begins", 2.0, 14.0, {"metric": "active_connections", "threshold": 45}),
        ("api_latency_increase", 4.0, 16.0, {"metric": "p99_ms", "baseline": 50, "peak": 2500}),
        ("customer_timeouts", 5.5, 17.0, {"metric": "timeout_count", "baseline": 0, "peak": 340}),
        ("pager_alert_fired", 6.0, 6.2, {"severity": "critical", "channel": "pagerduty"}),
        ("incident_declared", 7.0, 7.1, {"severity": "SEV1", "commander": "oncall_sre"}),
        ("rollback_initiated", 8.0, 8.3, {"action": "deploy config-service:v2.2"}),
        ("pool_draining", 8.5, 11.0, {"metric": "active_connections", "target": 10}),
        ("service_restored", 10.0, 10.5, {"metric": "availability_pct", "target": 99.9}),
        ("post_mortem_scheduled", 12.0, 12.2, {"action": "schedule_review"}),
    ]

    for name, start, end, meta in temporal_events:
        mem.add_temporal_event(name, start=start, end=end, **meta)

    events = mem.temporal.events
    print(f"  Temporal events registered: {len(events)}")
    for ev in sorted(events, key=lambda e: e.interval.start):
        dur = ev.interval.end - ev.interval.start
        phase = ev.metadata.get("severity", ev.metadata.get("error", ev.metadata.get("action", "")))
        print(f"    T+{ev.interval.start:5.1f}m  {ev.label:30s} ({dur:5.1f}m)  {phase}")
    print()

    print("=" * 70)
    print("SECTION 3: Allen Interval Analysis")
    print("=" * 70)
    print()
    print("  Allen interval algebra defines 13 relations between time intervals.")
    print("  These reveal the temporal structure of the incident.")
    print()

    allen_pairs = [
        ("routine_deploy_v2_3", "stale_config_pushed"),
        ("stale_config_pushed", "db_pool_growth_begins"),
        ("db_pool_growth_begins", "api_latency_increase"),
        ("api_latency_increase", "customer_timeouts"),
        ("rollback_initiated", "service_restored"),
        ("incident_declared", "rollback_initiated"),
        ("pager_alert_fired", "incident_declared"),
    ]

    relation_counts: dict[str, int] = {}
    print("  Key temporal relationships:")
    for src, tgt in allen_pairs:
        relation = mem.allen_relation(src, tgt)
        if relation:
            rel_name = relation.value
            relation_counts[rel_name] = relation_counts.get(rel_name, 0) + 1
            print(f"    {src:30s} -> {tgt:30s} : {rel_name}")

    print(f"\n  Relation frequency: {dict(relation_counts)}")
    print()

    print("=" * 70)
    print("SECTION 4: Automatic Causal Chain Detection")
    print("=" * 70)
    print()
    print("  The temporal subsystem can auto-detect causal chains by")
    print("  analyzing temporal ordering and graph connectivity.")
    print()

    chains = mem.temporal.detect_causal_chains(min_chain_length=3)
    if chains:
        print(f"  Detected {len(chains)} causal chain(s):")
        for i, chain in enumerate(chains[:5]):
            print(f"    Chain {i + 1}: {' -> '.join(chain)}")
    else:
        print("  No causal chains detected (requires edges between temporal events)")
        print("  Temporal events are registered independently from the infrastructure")
        print("  graph. To detect causal chains, we need graph edges connecting them,")
        print("  representing the 'this event caused that event' relationship.")
        print()
        print("  Registering timeline links to enable chain detection...")

        timeline_links = [
            ("routine_deploy_v2_3", "stale_config_pushed"),
            ("stale_config_pushed", "db_pool_growth_begins"),
            ("db_pool_growth_begins", "api_latency_increase"),
            ("api_latency_increase", "customer_timeouts"),
            ("customer_timeouts", "pager_alert_fired"),
            ("pager_alert_fired", "incident_declared"),
            ("incident_declared", "rollback_initiated"),
            ("rollback_initiated", "service_restored"),
        ]
        for src, tgt in timeline_links:
            mem.link(src, tgt, label="timeline_link", weight=3.0)

        chains = mem.temporal.detect_causal_chains(min_chain_length=3)
        if chains:
            print(f"  After adding timeline links, detected {len(chains)} chain(s):")
            for i, chain in enumerate(chains[:5]):
                print(f"    Chain {i + 1}: {' -> '.join(chain)}")
    print()

    print("=" * 70)
    print("SECTION 5: Temporal Constraint Consistency")
    print("=" * 70)

    constraints = mem.temporal.infer_constraints()
    print(f"\n  Inferred temporal constraints: {len(constraints)}")

    issues = mem.temporal.check_constraint_consistency()
    if issues:
        print(f"  Consistency issues: {len(issues)}")
        for issue in issues[:3]:
            print(f"    {issue}")
    else:
        print("  No consistency issues found -- timeline is internally consistent")
        print(f"  ({len(constraints)} Allen relations inferred from {len(events)} events)")
    print()

    print("=" * 70)
    print("SECTION 6: Infrastructure Impact Analysis")
    print("=" * 70)

    path = mem.analyze.shortest_path("config_service", "payment_service", weighted=True)
    if path:
        print(f"\n  Impact propagation path (config -> payment):")
        print(f"    {' -> '.join(path)}")

    path2 = mem.analyze.shortest_path("config_service", "customer_timeouts", weighted=True)
    if path2:
        print(f"\n  Impact propagation path (config -> customer impact):")
        print(f"    {' -> '.join(path2)}")

    centrality = mem.analyze.centrality("betweenness", top_k=5)
    print(f"\n  Betweenness centrality (infrastructure bottlenecks):")
    top_centrality = list(centrality.items())[:1]
    for label, score in list(centrality.items())[:5]:
        print(f"    {label:25s} {score:.4f}")
    if top_centrality:
        print(f"\n  {top_centrality[0][0]} has the highest betweenness centrality,")
        print(f"  confirming it is the primary bottleneck -- any issue routing")
        print(f"  through this node affects all downstream services.")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Infrastructure components: {infra_nodes}")
    print(f"  Temporal events (registered as nodes): {len(events)}")
    print(f"  Total graph nodes: {mem.size[0]} ({infra_nodes} infra + {len(events)} temporal)")
    print(f"  Total graph edges: {mem.size[1]}")
    print(f"  Allen relations: {len(allen_pairs)} pairs analyzed")
    print(f"  Causal chains: {len(chains) if chains else 0}")
    print(f"  Temporal constraints: {len(constraints)}")
    print()
    print("  Key insight: Temporal reasoning adds the WHEN to the WHAT.")
    print("  Graph structure shows which components are connected, but temporal")
    print("  analysis reveals the incident sequence and causal ordering that led")
    print("  from a config error to customer-facing timeouts.")
    print()


if __name__ == "__main__":
    main()
