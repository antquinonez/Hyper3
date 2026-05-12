"""
Structural Anomaly Detection
=============================
Demonstrates detection of structural anomalies in a microservices architecture
service mesh. Identifies circular dependencies, high-centrality bottlenecks,
contradictory routing rules, and unusual connectivity patterns.

Run: .venv/bin/python examples/showcase/core/structural_anomaly_detection/structural_anomaly_detection.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD SERVICE MESH TOPOLOGY")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    services = [
        "api_gateway", "auth_svc", "user_svc", "order_svc",
        "payment_svc", "inventory_svc", "notification_svc",
        "search_svc", "analytics_svc", "config_svc",
        "logging_svc", "cache_svc",
    ]
    databases = ["db_primary", "db_analytics", "db_cache"]
    queues = ["queue_orders", "queue_notifications"]
    infra = ["load_balancer"]

    for s in services:
        mem.add(s, data={"type": "service"})
    for d in databases:
        mem.add(d, data={"type": "database"})
    for q in queues:
        mem.add(q, data={"type": "message_queue"})
    for i in infra:
        mem.add(i, data={"type": "infrastructure"})

    mem.link("load_balancer", "api_gateway", label="routes_to", weight=5.0)
    mem.link("api_gateway", "auth_svc", label="routes_to", weight=4.0)
    mem.link("api_gateway", "user_svc", label="routes_to", weight=4.0)
    mem.link("api_gateway", "order_svc", label="routes_to", weight=3.0)
    mem.link("api_gateway", "search_svc", label="routes_to", weight=3.0)
    mem.link("api_gateway", "payment_svc", label="routes_to", weight=3.0)
    mem.link("api_gateway", "inventory_svc", label="routes_to", weight=2.0)
    mem.link("api_gateway", "notification_svc", label="routes_to", weight=2.0)
    mem.link("api_gateway", "analytics_svc", label="routes_to", weight=1.5)

    mem.link("auth_svc", "user_svc", label="calls", weight=3.0)
    mem.link("user_svc", "order_svc", label="calls", weight=2.0)
    mem.link("order_svc", "auth_svc", label="calls", weight=2.0)

    mem.link("order_svc", "payment_svc", label="calls", weight=3.0)
    mem.link("order_svc", "inventory_svc", label="calls", weight=2.5)
    mem.link("payment_svc", "queue_orders", label="publishes_to", weight=2.0)
    mem.link("notification_svc", "queue_orders", label="subscribes_to", weight=1.5)
    mem.link("payment_svc", "queue_notifications", label="publishes_to", weight=1.0)
    mem.link("notification_svc", "queue_notifications", label="subscribes_to", weight=1.5)

    mem.link("user_svc", "db_primary", label="reads_from", weight=3.0)
    mem.link("order_svc", "db_primary", label="reads_from", weight=3.0)
    mem.link("order_svc", "db_primary", label="writes_to", weight=3.0)
    mem.link("analytics_svc", "db_analytics", label="reads_from", weight=2.0)
    mem.link("logging_svc", "db_primary", label="writes_to", weight=1.0)
    mem.link("logging_svc", "db_analytics", label="writes_to", weight=1.0)
    mem.link("logging_svc", "db_cache", label="writes_to", weight=1.0)
    mem.link("cache_svc", "db_cache", label="reads_from", weight=2.0)
    mem.link("config_svc", "cache_svc", label="calls", weight=1.0)
    mem.link("search_svc", "cache_svc", label="calls", weight=2.0)

    desc = mem.analyze.describe()
    print(f"nodes: {desc.node_count}, edges: {desc.edge_count}")
    print(f"edge labels: {desc.edge_labels}")

    print("\n" + "=" * 70)
    print("SECTION 2: INDIVIDUAL ANOMALY ASSESSMENT")
    print("=" * 70)

    key_services = ["api_gateway", "auth_svc", "user_svc", "order_svc", "logging_svc", "config_svc"]
    for svc in key_services:
        result = mem.analyze.anomalies(svc)
        print(f"\n{svc}:")
        print(f"  status: {result.anomaly_status}")
        print(f"  boundary score: {result.boundary_score:.4f}")
        print(f"  warnings: {result.boundary_warnings}")

    print("\n" + "=" * 70)
    print("SECTION 3: BOUNDARY INDICATOR DEEP DIVE")
    print("=" * 70)

    from hyper3 import StructuralAnomalyDetector

    detector = StructuralAnomalyDetector(mem.engine.graph)

    for svc in ["api_gateway", "auth_svc", "logging_svc", "config_svc"]:
        indicator = detector.assess_anomaly(svc)
        print(f"\n{svc} indicators:")
        print(f"  cyclic_structure: {indicator.cyclic_structure:.4f}")
        print(f"  high_centrality: {indicator.high_centrality:.4f}")
        print(f"  contradiction_risk: {indicator.contradiction_risk:.4f}")
        print(f"  structural_anomaly: {indicator.structural_anomaly_score:.4f}")
        print(f"  boundary_score: {indicator.boundary_score:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 4: BOUNDARY REGION MAPPING")
    print("=" * 70)

    all_concepts = [n.label for n in mem.engine.graph.nodes]
    regions = mem.map_boundaries(all_concepts)

    status_counts = {"low_risk": 0, "boundary": 0, "anomalous": 0}
    for region in regions:
        status_counts[region.status] = status_counts.get(region.status, 0) + 1
    print(f"\nclassification: {status_counts}")

    print("\nanomalous services:")
    for r in regions:
        if r.status == "anomalous":
            print(f"  {r.description}: boundary_score={r.boundary_score:.4f}")

    print("\nboundary services:")
    for r in regions:
        if r.status == "boundary":
            print(f"  {r.description}: boundary_score={r.boundary_score:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: EXPLORATION WITH ASSUMPTIONS")
    print("=" * 70)

    assumptions = detector.suggest_assumptions("config_svc", top_k=3)
    print(f"\nsuggested assumptions for 'config_svc': {len(assumptions)}")
    for asm in assumptions:
        print(f"  {asm.name}: {asm.description} (coverage gain: {asm.coverage_gain:.4f})")

    anomaly_config = mem.analyze.anomalies("config_svc")
    print(f"\nconfig_svc anomaly status: {anomaly_config.anomaly_status}")
    print(f"  boundary score: {anomaly_config.boundary_score:.4f}")
    print(f"  structural insights: {anomaly_config.structural_insights[:3]}")

    print("\n" + "=" * 70)
    print("SECTION 6: CROSS-REFERENCE WITH CENTRALITY")
    print("=" * 70)

    bc = mem.analyze.centrality("betweenness")
    sorted_bc = sorted(bc.items(), key=lambda x: x[1], reverse=True)
    print("\ntop-5 betweenness centrality:")
    for label, score in sorted_bc[:5]:
        anomaly = mem.analyze.anomalies(label)
        print(f"  {label}: centrality={score:.4f}, anomaly_status={anomaly.anomaly_status}")

    analysis = detector.analyze()
    print(f"\nanomaly summary: mapped={analysis.mapped_regions}, low_risk={analysis.low_risk}, boundary={analysis.boundary}, anomalous={analysis.anomalous}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
