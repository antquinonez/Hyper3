"""
Self-Tuning Knowledge Graph for Operational Intelligence
=========================================================

Demonstrates how Hyper3 adapts its behavior over time through Thompson
sampling and system monitor feedback in an IT operations context.

Covers rule effectiveness learning, measurement basis learning, frame
effectiveness learning, and system monitor self-assessment.

Run with:
    .venv/bin/python examples/showcase/belief/adaptive_learning/adaptive_learning.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory, Modality, TransitiveRule, InverseRule


SERVERS = [
    "web-frontend-01", "web-frontend-02", "web-frontend-03",
    "api-gateway-01", "api-gateway-02",
    "auth-service-01", "auth-service-02",
    "user-service-01", "user-service-02",
    "order-service-01", "order-service-02", "order-service-03",
    "payment-service-01", "payment-service-02",
    "inventory-service-01", "inventory-service-02",
    "notification-service-01", "notification-service-02",
    "search-service-01", "search-service-02",
    "analytics-service-01",
    "cache-redis-01", "cache-redis-02",
    "db-postgres-primary", "db-postgres-replica-01", "db-postgres-replica-02",
    "db-mongo-primary", "db-mongo-replica-01",
    "queue-rabbitmq-01", "queue-rabbitmq-02",
    "cdn-edge-01", "cdn-edge-02", "cdn-edge-03",
    "lb-haproxy-01", "lb-haproxy-02",
    "monitor-prometheus-01", "monitor-grafana-01",
    "log-elastic-01", "log-elastic-02", "log-kibana-01",
    "ci-runner-01", "ci-runner-02", "ci-runner-03",
    "storage-s3-proxy-01",
    "dns-resolver-01", "dns-resolver-02",
    "vpn-gateway-01",
    "mail-relay-01",
    "backup-controller-01",
    "config-consul-01", "config-consul-02",
    "scheduler-airflow-01",
    "ml-inference-01", "ml-inference-02",
    "ml-training-01",
]

SERVICES = [
    "web-frontend", "api-gateway", "auth-service", "user-service",
    "order-service", "payment-service", "inventory-service",
    "notification-service", "search-service", "analytics-service",
    "cache-layer", "database-layer", "message-queue", "cdn-layer",
    "load-balancer", "monitoring-stack", "logging-stack",
    "ci-cd-pipeline", "storage-layer", "dns-service", "vpn-service",
    "mail-service", "backup-service", "config-management",
    "scheduler-service", "ml-platform",
]

REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]
ENVIRONMENTS = ["production", "staging"]

ALERT_TYPES = [
    "high-latency", "cpu-spike", "memory-pressure", "disk-full",
    "connection-pool-exhaustion", "error-rate-surge", "timeout-cascade",
    "replication-lag", "certificate-expiry", "dns-resolution-failure",
]

INCIDENT_TYPES = [
    "degraded-performance", "partial-outage", "full-outage",
    "data-corruption", "security-breach", "capacity-exhaustion",
]

PLAYBOOKS = [
    "restart-service", "scale-horizontally", "failover-replica",
    "clear-cache", "rotate-credentials", "rollback-deployment",
    "throttle-traffic", "increase-pool-size", "migrate-region",
]


def _build_graph(mem: HypergraphMemory) -> None:
    for srv in SERVERS:
        mem.add(srv, data={"type": "server", "region": REGIONS[hash(srv) % len(REGIONS)]})

    for svc in SERVICES:
        mem.add(svc, data={"type": "service"})

    for alt in ALERT_TYPES:
        mem.add(alt, data={"type": "alert"})

    for inc in INCIDENT_TYPES:
        mem.add(inc, data={"type": "incident"})

    for pb in PLAYBOOKS:
        mem.add(pb, data={"type": "playbook"})

    for env in ENVIRONMENTS:
        mem.add(env, data={"type": "environment"})

    for region in REGIONS:
        mem.add(region, data={"type": "region"})

    _link_servers_to_services(mem)
    _link_service_dependencies(mem)
    _link_alerts_to_services(mem)
    _link_incidents_to_alerts(mem)
    _link_playbooks_to_incidents(mem)
    _link_infrastructure(mem)


def _link_servers_to_services(mem: HypergraphMemory) -> None:
    service_servers: dict[str, list[str]] = {
        "web-frontend": [s for s in SERVERS if s.startswith("web-frontend")],
        "api-gateway": [s for s in SERVERS if s.startswith("api-gateway")],
        "auth-service": [s for s in SERVERS if s.startswith("auth-service")],
        "user-service": [s for s in SERVERS if s.startswith("user-service")],
        "order-service": [s for s in SERVERS if s.startswith("order-service")],
        "payment-service": [s for s in SERVERS if s.startswith("payment-service")],
        "inventory-service": [s for s in SERVERS if s.startswith("inventory-service")],
        "notification-service": [s for s in SERVERS if s.startswith("notification-service")],
        "search-service": [s for s in SERVERS if s.startswith("search-service")],
        "analytics-service": [s for s in SERVERS if s.startswith("analytics-service")],
        "cache-layer": [s for s in SERVERS if s.startswith("cache-redis")],
        "database-layer": [s for s in SERVERS if s.startswith("db-")],
        "message-queue": [s for s in SERVERS if s.startswith("queue-")],
        "cdn-layer": [s for s in SERVERS if s.startswith("cdn-")],
        "load-balancer": [s for s in SERVERS if s.startswith("lb-")],
        "monitoring-stack": [s for s in SERVERS if s.startswith("monitor-") or s.startswith("log-")],
        "logging-stack": [s for s in SERVERS if s.startswith("log-")],
        "ci-cd-pipeline": [s for s in SERVERS if s.startswith("ci-")],
        "storage-layer": [s for s in SERVERS if s.startswith("storage-")],
        "dns-service": [s for s in SERVERS if s.startswith("dns-")],
        "vpn-service": [s for s in SERVERS if s.startswith("vpn-")],
        "mail-service": [s for s in SERVERS if s.startswith("mail-")],
        "backup-service": [s for s in SERVERS if s.startswith("backup-")],
        "config-management": [s for s in SERVERS if s.startswith("config-")],
        "scheduler-service": [s for s in SERVERS if s.startswith("scheduler-")],
        "ml-platform": [s for s in SERVERS if s.startswith("ml-")],
    }
    for svc, servers in service_servers.items():
        for srv in servers:
            mem.link(srv, svc, label="hosts")


def _link_service_dependencies(mem: HypergraphMemory) -> None:
    deps = [
        ("web-frontend", "cdn-layer"), ("web-frontend", "load-balancer"),
        ("web-frontend", "api-gateway"),
        ("api-gateway", "auth-service"), ("api-gateway", "user-service"),
        ("api-gateway", "order-service"), ("api-gateway", "search-service"),
        ("auth-service", "database-layer"), ("auth-service", "cache-layer"),
        ("user-service", "database-layer"), ("user-service", "cache-layer"),
        ("order-service", "payment-service"), ("order-service", "inventory-service"),
        ("order-service", "notification-service"), ("order-service", "database-layer"),
        ("payment-service", "database-layer"), ("payment-service", "message-queue"),
        ("inventory-service", "database-layer"), ("inventory-service", "cache-layer"),
        ("notification-service", "message-queue"), ("notification-service", "mail-service"),
        ("search-service", "database-layer"), ("search-service", "cache-layer"),
        ("analytics-service", "database-layer"), ("analytics-service", "message-queue"),
        ("analytics-service", "ml-platform"),
        ("cache-layer", "database-layer"),
        ("database-layer", "storage-layer"), ("database-layer", "backup-service"),
        ("load-balancer", "dns-service"),
        ("monitoring-stack", "logging-stack"), ("monitoring-stack", "notification-service"),
        ("ci-cd-pipeline", "storage-layer"), ("ci-cd-pipeline", "config-management"),
        ("ml-platform", "database-layer"), ("ml-platform", "storage-layer"),
        ("scheduler-service", "database-layer"), ("scheduler-service", "message-queue"),
        ("vpn-gateway-01", "dns-service"), ("vpn-gateway-01", "auth-service"),
    ]
    for src, tgt in deps:
        mem.link(src, tgt, label="depends_on")


def _link_alerts_to_services(mem: HypergraphMemory) -> None:
    links = [
        ("high-latency", "api-gateway"), ("high-latency", "web-frontend"),
        ("high-latency", "load-balancer"),
        ("cpu-spike", "order-service"), ("cpu-spike", "analytics-service"),
        ("cpu-spike", "ml-platform"),
        ("memory-pressure", "cache-layer"), ("memory-pressure", "search-service"),
        ("memory-pressure", "ml-platform"),
        ("disk-full", "database-layer"), ("disk-full", "logging-stack"),
        ("disk-full", "storage-layer"),
        ("connection-pool-exhaustion", "database-layer"),
        ("connection-pool-exhaustion", "api-gateway"),
        ("error-rate-surge", "payment-service"), ("error-rate-surge", "order-service"),
        ("error-rate-surge", "api-gateway"),
        ("timeout-cascade", "api-gateway"), ("timeout-cascade", "order-service"),
        ("timeout-cascade", "payment-service"),
        ("replication-lag", "database-layer"), ("replication-lag", "cache-layer"),
        ("certificate-expiry", "load-balancer"), ("certificate-expiry", "auth-service"),
        ("certificate-expiry", "vpn-service"),
        ("dns-resolution-failure", "dns-service"), ("dns-resolution-failure", "cdn-layer"),
    ]
    for alt, svc in links:
        mem.link(alt, svc, label="triggers_on")


def _link_incidents_to_alerts(mem: HypergraphMemory) -> None:
    links = [
        ("high-latency", "degraded-performance"),
        ("cpu-spike", "degraded-performance"),
        ("memory-pressure", "degraded-performance"),
        ("connection-pool-exhaustion", "partial-outage"),
        ("error-rate-surge", "partial-outage"),
        ("error-rate-surge", "data-corruption"),
        ("timeout-cascade", "full-outage"),
        ("dns-resolution-failure", "full-outage"),
        ("disk-full", "capacity-exhaustion"),
        ("certificate-expiry", "security-breach"),
    ]
    for alt, inc in links:
        mem.link(alt, inc, label="escalates_to")


def _link_playbooks_to_incidents(mem: HypergraphMemory) -> None:
    links = [
        ("restart-service", "degraded-performance"),
        ("scale-horizontally", "capacity-exhaustion"),
        ("scale-horizontally", "degraded-performance"),
        ("failover-replica", "full-outage"), ("failover-replica", "partial-outage"),
        ("clear-cache", "degraded-performance"),
        ("rotate-credentials", "security-breach"),
        ("rollback-deployment", "data-corruption"),
        ("throttle-traffic", "capacity-exhaustion"),
        ("increase-pool-size", "connection-pool-exhaustion"),
        ("migrate-region", "full-outage"),
    ]
    for pb, inc in links:
        mem.link(pb, inc, label="remediates")


def _link_infrastructure(mem: HypergraphMemory) -> None:
    for srv in SERVERS:
        data = mem.node_data(srv)
        if data:
            region = data.get("region", "us-east-1")
            mem.link(srv, region, label="located_in")
            mem.link(srv, "production", label="deployed_in")
    for svc in SERVICES:
        mem.link(svc, "production", label="deployed_in")


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building IT Operations Knowledge Graph")
    print("=" * 70)

    _build_graph(mem)
    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")
    print()

    print("=" * 70)
    print("SECTION 2: Rule Effectiveness Learning (Rule Analytics)")
    print("=" * 70)

    rule_analytics = mem.rule_analytics

    rule_outcomes = [
        ("TransitiveRule", "useful"), ("TransitiveRule", "useful"),
        ("TransitiveRule", "pruned"), ("TransitiveRule", "useful"),
        ("TransitiveRule", "reinforced"), ("TransitiveRule", "useful"),
        ("TransitiveRule", "useful"), ("TransitiveRule", "reinforced"),
        ("InverseRule", "useful"), ("InverseRule", "pruned"),
        ("InverseRule", "useful"), ("InverseRule", "pruned"),
        ("InverseRule", "pruned"), ("InverseRule", "useful"),
        ("HubInferenceRule", "useful"), ("HubInferenceRule", "useful"),
        ("HubInferenceRule", "reinforced"), ("HubInferenceRule", "useful"),
        ("HubInferenceRule", "useful"), ("HubInferenceRule", "reinforced"),
        ("HubInferenceRule", "useful"), ("HubInferenceRule", "reinforced"),
        ("AnalogicalRule", "pruned"), ("AnalogicalRule", "pruned"),
        ("AnalogicalRule", "useful"), ("AnalogicalRule", "pruned"),
        ("GeneralizationRule", "useful"), ("GeneralizationRule", "useful"),
        ("GeneralizationRule", "reinforced"),
        ("AbductiveRule", "useful"), ("AbductiveRule", "useful"),
        ("AbductiveRule", "reinforced"), ("AbductiveRule", "useful"),
    ]
    for rule_name, outcome in rule_outcomes:
        rule_analytics.record_rule_outcome(rule_name, outcome)

    effectiveness = rule_analytics.get_rule_effectiveness()
    print("  Rule effectiveness rankings:")
    sorted_rules = sorted(effectiveness.items(), key=lambda x: x[1]["effectiveness"], reverse=True)
    for rank, (rule_name, stats) in enumerate(sorted_rules, 1):
        eff = stats["effectiveness"]
        ret = stats["retention_rate"]
        reinf = stats["reinforcement_rate"]
        apps = int(stats["applications"])
        print(f"    {rank}. {rule_name:25s}  eff={eff:.2f}  retention={ret:.2f}  "
              f"reinforcement={reinf:.2f}  apps={apps}")

    best = rule_analytics.get_best_rules(3)
    print(f"\n  Top 3 rules by effectiveness:")
    for name, score in best:
        print(f"    {name}: {score:.2f}")
    print()

    print("=" * 70)
    print("SECTION 3: Measurement Basis Learning (Thompson Sampling)")
    print("=" * 70)

    quantum = mem.engine.belief

    training_outcomes = [
        ("pragmatic", True), ("pragmatic", True), ("pragmatic", True),
        ("pragmatic", False), ("pragmatic", True), ("pragmatic", True),
        ("linguistic", True), ("linguistic", True), ("linguistic", False),
        ("linguistic", False), ("linguistic", False),
        ("temporal", True), ("temporal", True), ("temporal", True),
        ("temporal", True), ("temporal", True),
        ("emotional", False), ("emotional", False), ("emotional", True),
        ("emotional", False), ("emotional", False),
    ]
    for basis, success in training_outcomes:
        quantum.record_basis_outcome(basis, success)

    print("  Basis effectiveness:")
    for basis, rate in quantum.basis_effectiveness.items():
        print(f"    {basis:15s}  success_rate={rate:.2f}")

    selections: dict[str, int] = {}
    for _ in range(200):
        chosen = quantum.get_effective_basis()
        selections[chosen] = selections.get(chosen, 0) + 1

    print(f"\n  Thompson sampling selections over 200 trials:")
    for basis in sorted(selections, key=selections.get, reverse=True):
        count = selections[basis]
        bar = "#" * (count // 2)
        print(f"    {basis:15s}  {count:3d}  {bar}")

    problem_sets = [
        (["api-gateway-01", "api-gateway-02", "load-balancer"], "infrastructure-triage"),
        (["high-latency", "timeout-cascade", "error-rate-surge"], "alert-correlation"),
        (["payment-service-01", "payment-service-02", "database-layer"], "dependency-trace"),
    ]

    print(f"\n  Sample results by basis for different problem types:")
    for concepts, problem_type in problem_sets:
        qs = mem.belief.create(concepts)
        if qs is None:
            continue
        print(f"\n    Problem: {problem_type}")
        for basis_name in ["pragmatic", "temporal", "linguistic"]:
            qs_fresh = mem.belief.create(concepts)
            if qs_fresh is None:
                continue
            result = mem.sample_with_profile(qs_fresh, basis_name)
            if result:
                label = mem.node_label(result.node_id) or result.node_id
                print(f"      {basis_name:12s} -> {label}")
            else:
                print(f"      {basis_name:12s} -> no sample")
    print()

    print("=" * 70)
    print("SECTION 4: Frame Effectiveness Learning")
    print("=" * 70)

    analyzer = mem.perspective

    frame_training = [
        ("classical", True), ("classical", True), ("classical", False),
        ("classical", True), ("classical", True), ("classical", False),
        ("quantum", True), ("quantum", True), ("quantum", True),
        ("quantum", True), ("quantum", True), ("quantum", True),
        ("hypergraph", False), ("hypergraph", True), ("hypergraph", False),
        ("hypergraph", False), ("hypergraph", False),
        ("probabilistic", True), ("probabilistic", True), ("probabilistic", True),
        ("probabilistic", False), ("probabilistic", True),
    ]
    for frame, success in frame_training:
        analyzer.record_frame_outcome(frame, success)

    print("  Frame effectiveness:")
    for frame, eff in sorted(analyzer.get_frame_effectiveness().items(), key=lambda x: x[1], reverse=True):
        print(f"    {frame:15s}  effectiveness={eff:.2f}")

    test_concepts = [
        "api-gateway", "high-latency", "order-service",
        "timeout-cascade", "database-layer", "payment-service",
    ]

    print(f"\n  Frame selection comparison:")
    print(f"    {'Concept':30s}  {'Complexity-based':>16s}  {'Learned (TS)':>16s}")
    print("    " + "-" * 70)
    for concept in test_concepts:
        name_complexity, analysis_c = analyzer.select_optimal_frame(concept)
        name_learned, analysis_l = analyzer.select_optimal_frame_learned(concept)
        print(f"    {concept:30s}  {name_complexity:>16s}  {name_learned:>16s}")

    frame_selections: dict[str, int] = {}
    for concept in test_concepts:
        for _ in range(50):
            name, _ = analyzer.select_optimal_frame_learned(concept)
            frame_selections[name] = frame_selections.get(name, 0) + 1

    print(f"\n  Learned frame selections over {len(test_concepts) * 50} trials:")
    for frame in sorted(frame_selections, key=frame_selections.get, reverse=True):
        count = frame_selections[frame]
        bar = "#" * (count // 3)
        print(f"    {frame:15s}  {count:3d}  {bar}")
    print()

    print("=" * 70)
    print("SECTION 5: Meta-Cognitive Self-Assessment")
    print("=" * 70)

    report = mem.introspect()
    system_health = report.system_health
    graph_health = report.graph_health
    evolution_health = report.evolution_health
    discovery_health = report.discovery_health
    anti_patterns = report.anti_patterns
    recommendations = report.recommendations

    print("  Cognitive State:")
    print(f"    Fitness:            {system_health.fitness:.3f}")
    print(f"    Reasoning mode:     {system_health.mode or 'unknown'}")
    print(f"    Meta-computational:  level {system_health.meta_level}")
    print(f"    Rule analytics insight count: {system_health.rule_analytics_insight_count}")

    print("\n  Graph Health:")
    print(f"    Nodes:      {graph_health.nodes}")
    print(f"    Edges:      {graph_health.edges}")
    print(f"    Avg degree: {graph_health.avg_degree:.2f}")

    print("\n  Evolution Health:")
    print(f"    Merges:      {evolution_health.merges}")
    print(f"    Prunes:      {evolution_health.prunes}")
    print(f"    Refinements: {evolution_health.refinements}")

    print("\n  Discovery Health:")
    print(f"    Patterns:     {discovery_health.patterns}")
    print(f"    Active rules: {discovery_health.active_rules}")

    if anti_patterns:
        print(f"\n  Anti-patterns detected ({len(anti_patterns)}):")
        for ap in anti_patterns:
            print(f"    - {ap}")
    else:
        print("\n  No anti-patterns detected")

    if recommendations:
        print(f"\n  Recommendations ({len(recommendations)}):")
        for rec in recommendations:
            print(f"    -> {rec}")
    else:
        print("\n  No specific recommendations")

    triggers = mem.check_metamorphosis()
    print(f"\n  Metamorphosis triggers: {len(triggers)}")
    for trigger in triggers:
        print(f"    [{trigger.trigger_type}] {trigger.description} "
              f"(urgency={trigger.urgency:.2f})")

    if triggers:
        plan = mem.propose_tuning(triggers)
        if plan:
            print(f"\n  Proposed metamorphosis plan:")
            print(f"    Actions: {plan.actions}")
            print(f"    Expected improvement: {plan.expected_improvement:.2f}")
            print(f"    Risk level: {plan.risk_level:.2f}")
    else:
        print("\n  No metamorphosis needed - system is healthy")
    print()

    print("=" * 70)
    print("SECTION 6: Adaptive Learning Summary")
    print("=" * 70)

    print(f"  Graph: {mem.size[0]} nodes, {mem.size[1]} edges")

    print(f"\n  Rule effectiveness rankings (top 5):")
    best = rule_analytics.get_best_rules(5)
    for rank, (name, score) in enumerate(best, 1):
        print(f"    {rank}. {name:25s}  {score:.2f}")
    if effectiveness:
        worst_rule = min(effectiveness, key=lambda k: effectiveness[k]["effectiveness"])
        print(f"    Deprioritized: {worst_rule} "
              f"(eff={effectiveness[worst_rule]['effectiveness']:.2f})")

    if quantum.basis_effectiveness:
        best_basis = max(quantum.basis_effectiveness, key=quantum.basis_effectiveness.get)
        worst_basis = min(quantum.basis_effectiveness, key=quantum.basis_effectiveness.get)
        print(f"\n  Best measurement basis: {best_basis} "
              f"(rate={quantum.basis_effectiveness[best_basis]:.2f})")
        print(f"  Worst measurement basis: {worst_basis} "
              f"(rate={quantum.basis_effectiveness[worst_basis]:.2f})")

    frame_eff = analyzer.get_frame_effectiveness()
    if frame_eff:
        best_frame = max(frame_eff, key=frame_eff.get)
        print(f"\n  Optimal frame: {best_frame} "
              f"(effectiveness={frame_eff[best_frame]:.2f})")

    print(f"\n  System fitness: {system_health.fitness:.3f}")
    if triggers:
        print(f"  Self-repair: {len(triggers)} trigger(s) detected, actions recommended")
    else:
        print(f"  Self-repair: no actions needed")
    print()


if __name__ == "__main__":
    main()
