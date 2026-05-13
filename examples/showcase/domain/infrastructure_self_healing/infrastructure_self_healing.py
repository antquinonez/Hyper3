"""
Self-Healing Infrastructure Monitoring with Feedback-Driven Evolution
=====================================================================

Models a production infrastructure with 47 nodes (servers, services, databases,
load balancers, caches, monitoring) and demonstrates the full self-evolving feedback
loop:

  Round 1 (healthy system):
    - Build graph, run reasoning, retrieval, collapse operations
    - Record positive feedback - system stays healthy

  Round 2 (degradation):
    - Add noisy/stale nodes with low reliability
    - Run operations - feedback records poor outcomes
    - Fitness trends decline

  Round 3 (feedback-driven recovery):
    - evolve_with_feedback() intensifies decay and pruning
    - Reinforced nodes get weight boosts
    - Suppressed nodes get force-pruned
    - Bias profile shows which rules are effective
    - Metamorphosis validation rolls back a bad plan

  Round 4 (multiway merge with insight tracking):
    - Multiway reasoning produces convergent states
    - Causal merge preserves unique contributions

Run with:
    .venv/bin/python examples/showcase/domain/infrastructure_self_healing/infrastructure_self_healing.py
"""

from __future__ import annotations

from hyper3 import (
    HypergraphMemory,
    InverseRule,
    MultiwayEngine,
    StateConvergenceEngine,
    TransitiveRule,
)

SERVERS = {
    "web-fe-01": {"category": "server", "service": "web_frontend", "zone": "us-east-1", "health": 0.98},
    "web-fe-02": {"category": "server", "service": "web_frontend", "zone": "us-east-1", "health": 0.95},
    "web-fe-03": {"category": "server", "service": "web_frontend", "zone": "us-west-2", "health": 0.97},
    "api-gw-01": {"category": "server", "service": "api_gateway", "zone": "us-east-1", "health": 0.99},
    "api-gw-02": {"category": "server", "service": "api_gateway", "zone": "us-west-2", "health": 0.96},
    "auth-svc-01": {"category": "server", "service": "auth_service", "zone": "us-east-1", "health": 0.97},
    "auth-svc-02": {"category": "server", "service": "auth_service", "zone": "eu-west-1", "health": 0.94},
    "user-svc-01": {"category": "server", "service": "user_service", "zone": "us-east-1", "health": 0.98},
    "user-svc-02": {"category": "server", "service": "user_service", "zone": "us-west-2", "health": 0.96},
    "order-svc-01": {"category": "server", "service": "order_service", "zone": "us-east-1", "health": 0.99},
    "order-svc-02": {"category": "server", "service": "order_service", "zone": "eu-west-1", "health": 0.93},
    "payment-svc-01": {"category": "server", "service": "payment_service", "zone": "us-east-1", "health": 0.99},
    "payment-svc-02": {"category": "server", "service": "payment_service", "zone": "us-west-2", "health": 0.97},
    "inventory-svc-01": {"category": "server", "service": "inventory_service", "zone": "us-east-1", "health": 0.95},
    "inventory-svc-02": {"category": "server", "service": "inventory_service", "zone": "ap-south-1", "health": 0.91},
    "notification-svc-01": {"category": "server", "service": "notification_service", "zone": "us-east-1", "health": 0.96},
    "search-svc-01": {"category": "server", "service": "search_service", "zone": "us-west-2", "health": 0.94},
    "analytics-svc-01": {"category": "server", "service": "analytics_service", "zone": "us-east-1", "health": 0.92},
    "cache-redis-01": {"category": "server", "service": "cache", "zone": "us-east-1", "health": 0.99},
    "cache-redis-02": {"category": "server", "service": "cache", "zone": "us-west-2", "health": 0.98},
    "db-pg-primary": {"category": "server", "service": "database", "zone": "us-east-1", "health": 0.99},
    "db-pg-replica-01": {"category": "server", "service": "database", "zone": "us-west-2", "health": 0.97},
    "db-pg-replica-02": {"category": "server", "service": "database", "zone": "eu-west-1", "health": 0.96},
    "db-mongo-01": {"category": "server", "service": "document_store", "zone": "us-east-1", "health": 0.98},
    "queue-rmq-01": {"category": "server", "service": "message_queue", "zone": "us-east-1", "health": 0.97},
    "queue-rmq-02": {"category": "server", "service": "message_queue", "zone": "us-west-2", "health": 0.95},
    "cdn-edge-01": {"category": "server", "service": "cdn", "zone": "global", "health": 0.99},
    "cdn-edge-02": {"category": "server", "service": "cdn", "zone": "global", "health": 0.98},
    "lb-ha-01": {"category": "server", "service": "load_balancer", "zone": "us-east-1", "health": 0.99},
    "lb-ha-02": {"category": "server", "service": "load_balancer", "zone": "us-west-2", "health": 0.98},
    "monitor-prom-01": {"category": "server", "service": "monitoring", "zone": "us-east-1", "health": 0.97},
    "log-elastic-01": {"category": "server", "service": "logging", "zone": "us-east-1", "health": 0.96},
}

DEPENDENCIES: list[tuple[str, str, str]] = [
    ("web-fe-01", "lb-ha-01", "routes_to"),
    ("web-fe-02", "lb-ha-01", "routes_to"),
    ("web-fe-03", "lb-ha-02", "routes_to"),
    ("lb-ha-01", "api-gw-01", "routes_to"),
    ("lb-ha-02", "api-gw-02", "routes_to"),
    ("api-gw-01", "auth-svc-01", "calls"),
    ("api-gw-01", "user-svc-01", "calls"),
    ("api-gw-01", "order-svc-01", "calls"),
    ("api-gw-01", "search-svc-01", "calls"),
    ("api-gw-02", "auth-svc-02", "calls"),
    ("api-gw-02", "user-svc-02", "calls"),
    ("api-gw-02", "order-svc-02", "calls"),
    ("auth-svc-01", "cache-redis-01", "reads_from"),
    ("auth-svc-01", "db-pg-primary", "reads_from"),
    ("auth-svc-02", "cache-redis-02", "reads_from"),
    ("auth-svc-02", "db-pg-replica-02", "reads_from"),
    ("user-svc-01", "db-pg-primary", "reads_from"),
    ("user-svc-01", "cache-redis-01", "reads_from"),
    ("user-svc-02", "db-pg-replica-01", "reads_from"),
    ("order-svc-01", "db-pg-primary", "reads_from"),
    ("order-svc-01", "payment-svc-01", "calls"),
    ("order-svc-01", "inventory-svc-01", "calls"),
    ("order-svc-01", "queue-rmq-01", "publishes_to"),
    ("order-svc-02", "db-pg-replica-02", "reads_from"),
    ("order-svc-02", "payment-svc-02", "calls"),
    ("order-svc-02", "inventory-svc-02", "calls"),
    ("payment-svc-01", "db-pg-primary", "reads_from"),
    ("payment-svc-01", "queue-rmq-01", "publishes_to"),
    ("payment-svc-02", "db-pg-replica-01", "reads_from"),
    ("payment-svc-02", "queue-rmq-02", "publishes_to"),
    ("inventory-svc-01", "db-mongo-01", "reads_from"),
    ("inventory-svc-01", "cache-redis-01", "reads_from"),
    ("inventory-svc-02", "db-mongo-01", "reads_from"),
    ("notification-svc-01", "queue-rmq-01", "consumes_from"),
    ("search-svc-01", "db-mongo-01", "reads_from"),
    ("search-svc-01", "cache-redis-02", "reads_from"),
    ("analytics-svc-01", "db-pg-replica-01", "reads_from"),
    ("analytics-svc-01", "queue-rmq-01", "consumes_from"),
    ("cdn-edge-01", "web-fe-01", "routes_to"),
    ("cdn-edge-01", "web-fe-02", "routes_to"),
    ("cdn-edge-02", "web-fe-03", "routes_to"),
    ("monitor-prom-01", "api-gw-01", "monitors"),
    ("monitor-prom-01", "api-gw-02", "monitors"),
    ("monitor-prom-01", "db-pg-primary", "monitors"),
    ("monitor-prom-01", "cache-redis-01", "monitors"),
    ("monitor-prom-01", "queue-rmq-01", "monitors"),
    ("log-elastic-01", "api-gw-01", "receives_logs_from"),
    ("log-elastic-01", "order-svc-01", "receives_logs_from"),
    ("log-elastic-01", "payment-svc-01", "receives_logs_from"),
    ("log-elastic-01", "auth-svc-01", "receives_logs_from"),
    ("payment-svc-01", "auth-svc-01", "calls"),
    ("payment-svc-02", "auth-svc-02", "calls"),
    ("notification-svc-01", "user-svc-01", "calls"),
]

FAILURE_MODES: list[tuple[str, str, str]] = [
    ("db-pg-primary", "order-svc-01", "blocks"),
    ("db-pg-primary", "user-svc-01", "blocks"),
    ("db-pg-primary", "payment-svc-01", "blocks"),
    ("cache-redis-01", "auth-svc-01", "degrades"),
    ("cache-redis-01", "user-svc-01", "degrades"),
    ("cache-redis-01", "inventory-svc-01", "degrades"),
    ("queue-rmq-01", "notification-svc-01", "blocks"),
    ("queue-rmq-01", "analytics-svc-01", "blocks"),
    ("lb-ha-01", "web-fe-01", "blocks"),
    ("lb-ha-01", "web-fe-02", "blocks"),
    ("api-gw-01", "auth-svc-01", "blocks"),
    ("api-gw-01", "order-svc-01", "blocks"),
    ("auth-svc-01", "payment-svc-01", "blocks"),
]

NOISY_NODES = {
    "stale-metric-aggregator-01": {"category": "server", "service": "deprecated", "zone": "us-east-1", "health": 0.12, "stale": True},
    "stale-metric-aggregator-02": {"category": "server", "service": "deprecated", "zone": "us-west-2", "health": 0.08, "stale": True},
    "deprecated-test-runner-01": {"category": "server", "service": "deprecated", "zone": "us-east-1", "health": 0.05, "stale": True},
    "deprecated-test-runner-02": {"category": "server", "service": "deprecated", "zone": "eu-west-1", "health": 0.03, "stale": True},
    "orphan-debug-endpoint": {"category": "server", "service": "deprecated", "zone": "us-east-1", "health": 0.01, "stale": True},
    "legacy-xml-api-01": {"category": "server", "service": "deprecated", "zone": "us-east-1", "health": 0.15, "stale": True},
    "legacy-xml-api-02": {"category": "server", "service": "deprecated", "zone": "us-west-2", "health": 0.10, "stale": True},
    "unused-data-pipeline-01": {"category": "server", "service": "deprecated", "zone": "ap-south-1", "health": 0.07, "stale": True},
    "unused-data-pipeline-02": {"category": "server", "service": "deprecated", "zone": "us-east-1", "health": 0.04, "stale": True},
    "abandoned-ml-experiment-01": {"category": "server", "service": "deprecated", "zone": "us-west-2", "health": 0.02, "stale": True},
    "zombie-cron-worker-01": {"category": "server", "service": "deprecated", "zone": "us-east-1", "health": 0.06, "stale": True},
    "zombie-cron-worker-02": {"category": "server", "service": "deprecated", "zone": "eu-west-1", "health": 0.09, "stale": True},
    "ghost-replica-set-01": {"category": "server", "service": "deprecated", "zone": "ap-south-1", "health": 0.01, "stale": True},
    "ghost-replica-set-02": {"category": "server", "service": "deprecated", "zone": "us-east-1", "health": 0.02, "stale": True},
    "forgotten-proxy-01": {"category": "server", "service": "deprecated", "zone": "us-west-2", "health": 0.11, "stale": True},
}


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)
    mem.add_rules(TransitiveRule(edge_label="calls"))
    mem.add_rules(TransitiveRule(edge_label="routes_to"))
    mem.add_rules(TransitiveRule(edge_label="blocks"))
    mem.add_rules(InverseRule(edge_label="blocks", inverse_label="blocked_by"))

    def _id(label: str) -> str:
        n = mem.engine.graph.get_node_by_label(label)
        return n.id if n else label

    print("=" * 70)
    print("SECTION 1: Building Healthy Infrastructure Graph")
    print("=" * 70)

    for name, data in SERVERS.items():
        mem.add(name, data=data)

    for src, tgt, label in DEPENDENCIES:
        mem.link(src, tgt, label=label)

    for src, tgt, label in FAILURE_MODES:
        mem.link(src, tgt, label=label)

    stats = mem.stats()
    print(f"  Servers: {len(SERVERS)}")
    print(f"  Dependencies: {len(DEPENDENCIES)}")
    print(f"  Failure modes: {len(FAILURE_MODES)}")
    print(f"  Total nodes: {stats.nodes}, edges: {stats.edges}")
    print()

    print("=" * 70)
    print("SECTION 2: Round 1 - Healthy System Operations")
    print("=" * 70)

    paths = mem.find_paths("cdn-edge-01", "db-pg-primary", max_depth=6)
    print(f"  Paths CDN->DB: {len(paths)}")

    for path in paths[:3]:
        print(f"    {' -> '.join(path)}")

    mem.operation_feedback.record_collapse_outcome("qs_auth", _id("auth-svc-01"), correct=True)
    mem.operation_feedback.record_collapse_outcome("qs_payment", _id("payment-svc-01"), correct=True)
    mem.operation_feedback.record_collapse_outcome("qs_order", _id("order-svc-01"), correct=True)

    mem.operation_feedback.record_retrieval_outcome("database", {_id("db-pg-primary"), _id("db-pg-replica-01")}, set())
    mem.operation_feedback.record_retrieval_outcome("cache", {_id("cache-redis-01"), _id("cache-redis-02")}, {_id("cache-redis-02")})

    mem.operation_feedback.record_inference_outcome("inf_call_chain_1", accepted=True)
    mem.operation_feedback.record_inference_outcome("inf_call_chain_2", accepted=True)

    result1 = mem.evolve()
    print(f"\n  Round 1 evolve: decayed={result1.decayed}, pruned={result1.pruned}, "
          f"merged={result1.merged}")
    print(f"  Fitness trend after Round 1: {mem.operation_feedback.get_fitness_trend()}")
    print(f"  Nodes: {mem.size[0]}, Edges: {mem.size[1]}")
    print()

    print("=" * 70)
    print("SECTION 3: Round 2 - Degradation (Noisy/Stale Nodes)")
    print("=" * 70)

    for name, data in NOISY_NODES.items():
        node = mem.add(name, data=data)
        node.weight = data["health"]

    mem.link("stale-metric-aggregator-01", "db-pg-primary", label="reads_from")
    mem.link("legacy-xml-api-01", "lb-ha-01", label="routes_to")
    mem.link("zombie-cron-worker-01", "queue-rmq-01", label="publishes_to")

    print(f"  Added {len(NOISY_NODES)} noisy/stale nodes with low weights")
    print(f"  Total nodes: {mem.size[0]}")

    for i in range(5):
        evo = mem.evolve()
        print(f"  Evolution cycle {i + 1}: decayed={evo.decayed}, pruned={evo.pruned}")

    stale_ids = {}
    for stale_name in ["stale-metric-aggregator-01", "deprecated-test-runner-01",
                       "orphan-debug-endpoint", "legacy-xml-api-01",
                       "unused-data-pipeline-01", "ghost-replica-set-01",
                       "abandoned-ml-experiment-01", "zombie-cron-worker-01"]:
        n = mem.engine.graph.get_node_by_label(stale_name)
        sid = n.id if n else stale_name
        stale_ids[stale_name] = sid
        for _ in range(3):
            mem.operation_feedback.record_retrieval_outcome(
                "infrastructure_search", set(), {sid},
            )

    mem.operation_feedback.record_collapse_outcome("qs_stale", stale_ids.get("stale-metric-aggregator-01", "x"), correct=False)
    mem.operation_feedback.record_collapse_outcome("qs_stale_2", stale_ids.get("deprecated-test-runner-01", "x"), correct=False)
    mem.operation_feedback.record_collapse_outcome("qs_stale_3", stale_ids.get("legacy-xml-api-01", "x"), correct=False)

    for healthy_name in ["api-gw-01", "order-svc-01", "payment-svc-01", "db-pg-primary", "cache-redis-01"]:
        n = mem.engine.graph.get_node_by_label(healthy_name)
        hid = n.id if n else healthy_name
        mem.operation_feedback.record_collapse_outcome(f"qs_{healthy_name}", hid, correct=True)
        for _ in range(3):
            mem.operation_feedback.record_retrieval_outcome(
                "infrastructure_search", {hid}, set(),
            )

    mem.operation_feedback.record_inference_outcome("inf_stale_1", accepted=False)
    mem.operation_feedback.record_inference_outcome("inf_stale_2", accepted=False)
    mem.operation_feedback.record_inference_outcome("inf_stale_3", accepted=False)
    mem.operation_feedback.record_inference_outcome("inf_good_1", accepted=True)

    trend = mem.operation_feedback.get_fitness_trend()
    summary_before = mem.feedback_summary()
    print(f"\n  Fitness trend after degradation: {trend}")
    print(f"  Overall health: {summary_before['overall_health']:.2f}")
    print(f"  Collapse accuracy: {summary_before['collapse_accuracy']:.2f}")
    print(f"  Retrieval precision: {summary_before['retrieval_precision']:.2f}")
    print(f"  Inference acceptance: {summary_before['inference_acceptance_rate']:.2f}")
    print(f"  Reinforced nodes: {len(mem.operation_feedback.get_reinforced_nodes())}")
    print(f"  Suppressed nodes: {len(mem.operation_feedback.get_suppressed_nodes())}")
    print()

    print("=" * 70)
    print("SECTION 4: Round 3 - Feedback-Driven Recovery")
    print("=" * 70)

    recovery = mem.evolve_with_feedback()
    print(f"  Feedback-driven evolution:")
    print(f"    decayed={recovery.decayed}, pruned={recovery.pruned}, "
          f"reinforced={recovery.reinforced}, suppressed={recovery.suppressed}")
    print(f"    Nodes: {recovery.node_count}, Edges: {recovery.edge_count}")

    for i in range(3):
        evo = mem.evolve_with_feedback()
        print(f"  Recovery cycle {i + 1}: pruned={evo.pruned}, "
              f"reinforced={evo.reinforced}, suppressed={evo.suppressed}")

    summary_after = mem.feedback_summary()
    print(f"\n  Post-recovery health: {summary_after['overall_health']:.2f}")
    print(f"  Post-recovery trend: {summary_after['fitness_trend']}")
    print(f"  Nodes remaining: {mem.size[0]}")
    print()

    remaining_stale = 0
    remaining_healthy = 0
    for node in mem.engine.graph.nodes:
        if node.data and node.data.get("stale"):
            remaining_stale += 1
        elif node.data and node.data.get("category") == "server":
            remaining_healthy += 1
    print(f"  Healthy servers remaining: {remaining_healthy}")
    print(f"  Stale nodes remaining: {remaining_stale}")
    print()

    print("=" * 70)
    print("SECTION 5: Cross-Operation Correlation")
    print("=" * 70)

    correlated = summary_after["correlated_nodes"]
    print(f"  Nodes appearing across multiple operation types: {len(correlated)}")
    for nid, info in sorted(correlated.items(), key=lambda x: x[1]["signal_count"], reverse=True)[:8]:
        n = mem.engine.graph.get_node(nid)
        label = n.label if n else f"[removed:{nid[:12]}]"
        print(f"    {label:<30} signals={info['signal_count']}, "
              f"positive_rate={info['positive_rate']:.2f}, "
              f"types={info['signal_types']}")
    print()

    print("=" * 70)
    print("SECTION 6: Computational Bias Profile")
    print("=" * 70)

    mem.reason({"api-gw-01", "order-svc-01", "payment-svc-01"}, max_depth=3, max_total_states=15)
    mem.reason({"cdn-edge-01", "lb-ha-01", "web-fe-01"}, max_depth=3, max_total_states=10)

    profile = mem.compute_bias_profile()
    print(f"  Reasoning style: {profile['reasoning_style']}")
    print(f"  Bias score: {profile['bias_score']:.3f}")
    print(f"  Rule count: {profile['rule_count']}")
    print(f"  Average effectiveness: {profile.get('average_effectiveness', 0):.3f}")
    print(f"  Position trajectory: {profile['position_trajectory']}")
    if profile["dominant_rules"]:
        print(f"  Dominant rules: {profile['dominant_rules']}")
    if profile["underused_rules"]:
        print(f"  Underused rules: {profile['underused_rules']}")
    print()

    print("=" * 70)
    print("SECTION 7: Metamorphosis with Validation")
    print("=" * 70)

    v0 = mem.capture_version()
    print(f"  Captured baseline version: {v0['version_id']}")

    triggers = mem.check_metamorphosis()
    if triggers:
        print(f"  Metamorphosis triggers: {len(triggers)}")
        for t in triggers:
            print(f"    {t.trigger_type}: {t.description} (urgency={t.urgency:.2f})")

        plan = mem.propose_tuning(triggers)
        if plan:
            print(f"  Plan: {len(plan.actions)} actions, "
                  f"expected improvement={plan.expected_improvement:.2f}, "
                  f"risk={plan.risk_level:.2f}")

            result = mem.execute_tuning_validated(plan)
            print(f"  Validated execution:")
            print(f"    rolled_back={result.rolled_back}")
            print(f"    fitness_before={result.fitness_before:.4f}")
            print(f"    fitness_after={result.fitness_after:.4f}")
            print(f"    improvement={result.improvement:.6f}")
    else:
        print("  No metamorphosis triggers (system recovered)")

        delta = mem.diff_from_version(v0["version_id"])
        if delta:
            print(f"  Graph diff from baseline:")
            print(f"    Nodes added: {len(delta.nodes_added)}")
            print(f"    Nodes removed: {len(delta.nodes_removed)}")
            print(f"    Edges added: {len(delta.edges_added)}")
            print(f"    Edges removed: {len(delta.edges_removed)}")
            print(f"    Total changes: {delta.total_changes}")
    print()

    print("=" * 70)
    print("SECTION 8: Multiway Reasoning with Merge Insights")
    print("=" * 70)
    print()
    print("  Now we use the multiway engine directly to explore how different")
    print("  reasoning branches converge on the same conclusions. This shows")
    print("  whether multiple rule applications lead to equivalent states.")
    print()

    mw = MultiwayEngine(mem.engine.graph)
    rules = [
        TransitiveRule(edge_label="calls"),
        TransitiveRule(edge_label="routes_to"),
        TransitiveRule(edge_label="blocks"),
        InverseRule(edge_label="blocks", inverse_label="blocked_by"),
    ]
    mw_result = mw.expand_from_labels(
        {"api-gw-01", "order-svc-01", "payment-svc-01", "db-pg-primary"},
        rules,
        max_total_states=12,
    )
    print(f"  Multiway expansion: {mw_result.states_created} states, "
          f"{mw_result.edges_produced} edges produced, "
          f"{mw_result.rules_applied} rules applied")

    mw_graph = mw.multiway
    causal = StateConvergenceEngine(mem.engine.graph, mw_graph, threshold=0.4)
    invariants = causal.merge_invariant_states()
    print(f"  Causal invariants found: {len(invariants)}")
    for inv in invariants[:5]:
        print(f"    Merge: similarity={inv.similarity:.3f}")
        for insight in inv.insights:
            print(f"      state={insight.state_id[:16]}: rule={insight.rule_applied}, "
                  f"unique_nodes={len(insight.unique_nodes)}, "
                  f"unique_edges={len(insight.unique_edges)}")
    if len(invariants) > 5:
        print(f"    ... and {len(invariants) - 5} more merges")
    if not invariants:
        print("  No convergent states found -- after cleanup, the graph has")
        print("  too few same-label chains for the rules to produce merges.")
    print()

    print("=" * 70)
    print("SECTION 9: Temporal Incident Timeline")
    print("=" * 70)

    print()
    print("  Modeling the degradation incident as temporal events with")
    print("  Allen interval relations and causal chain detection.")
    print()

    temporal_events = [
        ("healthy_baseline", 0.0, 10.0, {"phase": "normal"}),
        ("stale_config_pushed", 10.0, 10.5, {"phase": "degradation", "component": "config-svc-01"}),
        ("db_pool_growth_begins", 11.0, 14.0, {"phase": "degradation", "component": "db-pg-primary"}),
        ("api_latency_spike", 12.0, 16.0, {"phase": "impact", "component": "api-gw-01"}),
        ("customer_timeouts", 13.0, 17.0, {"phase": "impact", "component": "api-gw-01"}),
        ("pager_alert_fired", 14.0, 14.2, {"phase": "detection"}),
        ("feedback_recovery", 16.0, 20.0, {"phase": "recovery"}),
        ("service_restored", 19.0, 25.0, {"phase": "normal"}),
    ]

    for name, start, end, meta in temporal_events:
        mem.add_temporal_event(name, start=start, end=end, **meta)

    events = mem.list_temporal_events()
    print(f"  Temporal events registered: {len(events)}")
    for ev in events:
        dur = ev.interval.end - ev.interval.start
        print(f"    {ev.label:30s} [{ev.interval.start:5.1f} - {ev.interval.end:5.1f}] ({dur:4.1f}m) {ev.metadata.get('phase', '')}")

    print()
    print("  Allen interval relations between key event pairs:")
    pairs = [
        ("stale_config_pushed", "db_pool_growth_begins"),
        ("db_pool_growth_begins", "api_latency_spike"),
        ("api_latency_spike", "customer_timeouts"),
        ("feedback_recovery", "service_restored"),
        ("healthy_baseline", "stale_config_pushed"),
        ("pager_alert_fired", "feedback_recovery"),
    ]
    for src, tgt in pairs:
        relation = mem.allen_relation(src, tgt)
        if relation:
            print(f"    {src:30s} -> {tgt:30s} : {relation.value}")

    print()
    print("  Auto-detected causal chains:")
    chains = mem.detect_temporal_causal_chains(min_chain_length=3)
    if chains:
        for i, chain in enumerate(chains[:5]):
            print(f"    Chain {i+1}: {' -> '.join(chain)}")
    else:
        print("    No causal chains detected (requires graph edges between temporal events)")

    print()
    print("  Temporal constraint consistency:")
    constraints = mem.infer_temporal_constraints()
    print(f"    Inferred constraints: {len(constraints)}")
    issues = mem.check_temporal_constraint_consistency()
    if issues:
        print(f"    Consistency issues: {len(issues)}")
        for issue in issues[:3]:
            print(f"      {issue}")
    else:
        print("    No consistency issues found")

    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    final_stats = mem.stats()
    print(f"  Final graph: {final_stats.nodes} nodes, {final_stats.edges} edges")
    print(f"  Stale nodes cleaned: {len(NOISY_NODES) - remaining_stale}/{len(NOISY_NODES)}")
    print(f"  Healthy nodes preserved: {remaining_healthy}")
    print(f"  Fitness journey: declining -> {summary_after['fitness_trend']}")
    print(f"  Cross-operation correlations: {len(correlated)} nodes tracked")
    print(f"  Multiway states explored: {mw_result.states_created}")
    print(f"  Causal merges: {len(invariants)}")
    print(f"  Temporal events: {len(events)}")
    print(f"  Allen relations computed: {len(pairs)} pairs")
    print()
    print("  Key insight: The feedback loop automatically identifies and removes")
    print("  degraded infrastructure while preserving healthy nodes. Reinforced")
    print("  nodes (frequently accessed) gain weight; suppressed nodes (poor")
    print("  retrieval outcomes) are pruned. The system self-tunes without manual")
    print("  intervention.")
    print()


if __name__ == "__main__":
    main()
