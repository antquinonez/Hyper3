"""
Self-Tuning Knowledge Graph for Operational Intelligence (Standard Library Reimplementation)
==============================================================================================

Reimplements Hyper3's adaptive learning example using collections.Counter
for rule effectiveness tracking, numpy.random.beta for Thompson sampling,
manual dict for outcome recording, and a simple health check function.

Run with:
    .venv/bin/python examples/comparison/12_adaptive_learning.py
"""

from __future__ import annotations

from collections import Counter, defaultdict

import networkx as nx
import numpy as np


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


def _build_graph(G: nx.DiGraph) -> None:
    for srv in SERVERS:
        G.add_node(srv, type="server", region=REGIONS[hash(srv) % len(REGIONS)])

    for svc in SERVICES:
        G.add_node(svc, type="service")

    for alt in ALERT_TYPES:
        G.add_node(alt, type="alert")

    for inc in INCIDENT_TYPES:
        G.add_node(inc, type="incident")

    for pb in PLAYBOOKS:
        G.add_node(pb, type="playbook")

    for env in ENVIRONMENTS:
        G.add_node(env, type="environment")

    for region in REGIONS:
        G.add_node(region, type="region")

    _link_servers_to_services(G)
    _link_service_dependencies(G)
    _link_alerts_to_services(G)
    _link_incidents_to_alerts(G)
    _link_playbooks_to_incidents(G)
    _link_infrastructure(G)


def _link_servers_to_services(G: nx.DiGraph) -> None:
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
            G.add_edge(srv, svc, label="hosts")


def _link_service_dependencies(G: nx.DiGraph) -> None:
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
        G.add_edge(src, tgt, label="depends_on")


def _link_alerts_to_services(G: nx.DiGraph) -> None:
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
        G.add_edge(alt, svc, label="triggers_on")


def _link_incidents_to_alerts(G: nx.DiGraph) -> None:
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
        G.add_edge(alt, inc, label="escalates_to")


def _link_playbooks_to_incidents(G: nx.DiGraph) -> None:
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
        G.add_edge(pb, inc, label="remediates")


def _link_infrastructure(G: nx.DiGraph) -> None:
    for srv in SERVERS:
        data = G.nodes[srv]
        if data:
            region = data.get("region", "us-east-1")
            G.add_edge(srv, region, label="located_in")
            G.add_edge(srv, "production", label="deployed_in")
    for svc in SERVICES:
        G.add_edge(svc, "production", label="deployed_in")


class RuleEffectivenessTracker:
    def __init__(self):
        self.outcomes: dict[str, Counter] = defaultdict(Counter)
        self.applications: dict[str, int] = Counter()

    def record_outcome(self, rule_name: str, outcome: str):
        self.outcomes[rule_name][outcome] += 1
        self.applications[rule_name] += 1

    def get_effectiveness(self) -> dict[str, dict]:
        result = {}
        for rule, counts in self.outcomes.items():
            total = sum(counts.values())
            useful = counts.get("useful", 0) + counts.get("reinforced", 0)
            reinforced = counts.get("reinforced", 0)
            pruned = counts.get("pruned", 0)
            result[rule] = {
                "effectiveness": useful / total if total else 0.0,
                "retention_rate": (total - pruned) / total if total else 0.0,
                "reinforcement_rate": reinforced / total if total else 0.0,
                "applications": total,
            }
        return result

    def get_best_rules(self, n: int) -> list[tuple[str, float]]:
        eff = self.get_effectiveness()
        ranked = sorted(eff.items(), key=lambda x: x[1]["effectiveness"], reverse=True)
        return [(name, stats["effectiveness"]) for name, stats in ranked[:n]]


class ThompsonSampler:
    def __init__(self):
        self.successes: dict[str, int] = Counter()
        self.failures: dict[str, int] = Counter()
        self.rng = np.random.default_rng(42)

    def record_outcome(self, name: str, success: bool):
        if success:
            self.successes[name] += 1
        else:
            self.failures[name] += 1

    def sample(self, candidates: list[str]) -> str:
        scores = {}
        for name in candidates:
            s = self.successes.get(name, 0)
            f = self.failures.get(name, 0)
            scores[name] = float(self.rng.beta(s + 1, f + 1))
        return max(scores, key=scores.get)

    @property
    def effectiveness(self) -> dict[str, float]:
        result = {}
        all_names = set(self.successes) | set(self.failures)
        for name in all_names:
            s = self.successes.get(name, 0)
            f = self.failures.get(name, 0)
            total = s + f
            result[name] = s / total if total else 0.0
        return result


class FrameSelector:
    def __init__(self):
        self.sampler = ThompsonSampler()

    def record_frame_outcome(self, frame: str, success: bool):
        self.sampler.record_outcome(frame, success)

    def select_frame_learned(self, candidates: list[str] | None = None) -> str:
        if candidates is None:
            candidates = ["classical", "quantum", "hypergraph", "probabilistic"]
        return self.sampler.sample(candidates)

    def select_frame_complexity(self, concept: str) -> str:
        if any(kw in concept for kw in ["latency", "timeout", "cascade"]):
            return "classical"
        elif any(kw in concept for kw in ["payment", "order"]):
            return "quantum"
        elif any(kw in concept for kw in ["database", "db"]):
            return "hypergraph"
        return "probabilistic"

    def get_effectiveness(self) -> dict[str, float]:
        return self.sampler.effectiveness


class WeightedSampler:
    def __init__(self):
        self.rng = np.random.default_rng(42)
        self.amplitudes: dict[str, float] = {}

    def superpose(self, concepts: list[str], amplitudes: list[float] | None = None) -> dict[str, float]:
        if amplitudes is None:
            amplitudes = [1.0] * len(concepts)
        probs = np.array(amplitudes) ** 2
        probs = probs / probs.sum()
        self.amplitudes = {c: p for c, p in zip(concepts, probs)}
        return self.amplitudes

    def collapse(self, concepts: list[str], context_weights: dict[str, float] | None = None) -> str:
        if not self.amplitudes:
            self.superpose(concepts)
        probs = np.array([self.amplitudes.get(c, 0.0) for c in concepts])
        if context_weights:
            weights = np.array([context_weights.get(c, 1.0) for c in concepts])
            probs = probs * weights
        probs = probs / probs.sum()
        return self.rng.choice(concepts, p=probs)

    def collapse_with_basis(self, concepts: list[str], basis: str) -> str | None:
        _ = basis
        self.superpose(concepts)
        return self.collapse(concepts)


def compute_health(G: nx.DiGraph) -> dict:
    n = G.number_of_nodes()
    e = G.number_of_edges()
    avg_degree = 2 * e / n if n else 0.0
    return {
        "fitness": 1.0,
        "mode": "stable",
        "meta_level": 0,
        "nodes": n,
        "edges": e,
        "avg_degree": avg_degree,
    }


def check_triggers(G: nx.DiGraph, health: dict) -> list[dict]:
    triggers = []
    if health["avg_degree"] < 1.5:
        triggers.append({"type": "low_connectivity", "description": "Graph connectivity below threshold",
                         "urgency": 0.7})
    if health["fitness"] < 0.5:
        triggers.append({"type": "low_fitness", "description": "System fitness degraded",
                         "urgency": 0.9})
    return triggers


def main() -> None:
    G = nx.DiGraph()

    # =====================================================================
    # SECTION 1: Building IT Operations Knowledge Graph
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Building IT Operations Knowledge Graph")
    print("=" * 70)

    _build_graph(G)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print()

    # =====================================================================
    # SECTION 2: Rule Effectiveness Learning
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Rule Effectiveness Learning (collections.Counter)")
    print("=" * 70)

    rulial = RuleEffectivenessTracker()

    rule_outcomes = [
        ("TransitiveRule", "useful"), ("TransitiveRule", "useful"),
        ("TransitiveRule", "pruned"), ("TransitiveRule", "useful"),
        ("TransitiveRule", "reinforced"), ("TransitiveRule", "useful"),
        ("TransitiveRule", "useful"), ("TransitiveRule", "reinforced"),
        ("InverseRule", "useful"), ("InverseRule", "pruned"),
        ("InverseRule", "useful"), ("InverseRule", "pruned"),
        ("InverseRule", "pruned"), ("InverseRule", "useful"),
        ("CausalInferenceRule", "useful"), ("CausalInferenceRule", "useful"),
        ("CausalInferenceRule", "reinforced"), ("CausalInferenceRule", "useful"),
        ("CausalInferenceRule", "useful"), ("CausalInferenceRule", "reinforced"),
        ("CausalInferenceRule", "useful"), ("CausalInferenceRule", "reinforced"),
        ("AnalogicalRule", "pruned"), ("AnalogicalRule", "pruned"),
        ("AnalogicalRule", "useful"), ("AnalogicalRule", "pruned"),
        ("GeneralizationRule", "useful"), ("GeneralizationRule", "useful"),
        ("GeneralizationRule", "reinforced"),
        ("AbductiveRule", "useful"), ("AbductiveRule", "useful"),
        ("AbductiveRule", "reinforced"), ("AbductiveRule", "useful"),
    ]
    for rule_name, outcome in rule_outcomes:
        rulial.record_outcome(rule_name, outcome)

    effectiveness = rulial.get_effectiveness()
    print("  Rule effectiveness rankings:")
    sorted_rules = sorted(effectiveness.items(), key=lambda x: x[1]["effectiveness"], reverse=True)
    for rank, (rule_name, stats) in enumerate(sorted_rules, 1):
        eff = stats["effectiveness"]
        ret = stats["retention_rate"]
        reinf = stats["reinforcement_rate"]
        apps = int(stats["applications"])
        print(f"    {rank}. {rule_name:25s}  eff={eff:.2f}  retention={ret:.2f}  "
              f"reinforcement={reinf:.2f}  apps={apps}")

    best = rulial.get_best_rules(3)
    print(f"\n  Top 3 rules by effectiveness:")
    for name, score in best:
        print(f"    {name}: {score:.2f}")
    print()

    # =====================================================================
    # SECTION 3: Measurement Basis Learning (Thompson Sampling)
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Measurement Basis Learning (numpy.random.beta)")
    print("=" * 70)

    basis_sampler = ThompsonSampler()

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
        basis_sampler.record_outcome(basis, success)

    print("  Basis effectiveness:")
    for basis, rate in basis_sampler.effectiveness.items():
        print(f"    {basis:15s}  success_rate={rate:.2f}")

    candidates = ["pragmatic", "linguistic", "temporal", "emotional"]
    selections: dict[str, int] = Counter()
    for _ in range(200):
        chosen = basis_sampler.sample(candidates)
        selections[chosen] += 1

    print(f"\n  Thompson sampling selections over 200 trials:")
    for basis in sorted(selections, key=selections.get, reverse=True):
        count = selections[basis]
        bar = "#" * (count // 2)
        print(f"    {basis:15s}  {count:3d}  {bar}")

    sampler = WeightedSampler()
    problem_sets = [
        (["api-gateway-01", "api-gateway-02", "lb-haproxy-01"], "infrastructure-triage"),
        (["high-latency", "timeout-cascade", "error-rate-surge"], "alert-correlation"),
        (["payment-service-01", "payment-service-02", "database-layer"], "dependency-trace"),
    ]

    print(f"\n  Weighted sampling results for different problem types:")
    for concepts, problem_type in problem_sets:
        present = [c for c in concepts if c in G]
        if not present:
            continue
        print(f"\n    Problem: {problem_type}")
        for basis_name in ["pragmatic", "temporal", "linguistic"]:
            result = sampler.collapse_with_basis(present, basis_name)
            if result:
                print(f"      {basis_name:12s} -> {result}")
    print()

    # =====================================================================
    # SECTION 4: Frame Effectiveness Learning
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: Frame Effectiveness Learning")
    print("=" * 70)

    frame_selector = FrameSelector()

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
        frame_selector.record_frame_outcome(frame, success)

    print("  Frame effectiveness:")
    for frame, eff in sorted(frame_selector.get_effectiveness().items(), key=lambda x: x[1], reverse=True):
        print(f"    {frame:15s}  effectiveness={eff:.2f}")

    test_concepts = [
        "api-gateway", "high-latency", "order-service",
        "timeout-cascade", "database-layer", "payment-service",
    ]

    print(f"\n  Frame selection comparison:")
    print(f"    {'Concept':30s}  {'Complexity-based':>16s}  {'Learned (TS)':>16s}")
    print("    " + "-" * 70)
    for concept in test_concepts:
        name_complexity = frame_selector.select_frame_complexity(concept)
        name_learned = frame_selector.select_frame_learned()
        print(f"    {concept:30s}  {name_complexity:>16s}  {name_learned:>16s}")

    frame_selections: dict[str, int] = Counter()
    for concept in test_concepts:
        for _ in range(50):
            name = frame_selector.select_frame_learned()
            frame_selections[name] += 1

    print(f"\n  Learned frame selections over {len(test_concepts) * 50} trials:")
    for frame in sorted(frame_selections, key=frame_selections.get, reverse=True):
        count = frame_selections[frame]
        bar = "#" * (count // 3)
        print(f"    {frame:15s}  {count:3d}  {bar}")
    print()

    # =====================================================================
    # SECTION 5: Meta-Cognitive Self-Assessment
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: Meta-Cognitive Self-Assessment (Health Check)")
    print("=" * 70)

    health = compute_health(G)

    print("  System Health:")
    print(f"    Fitness:     {health['fitness']:.3f}")
    print(f"    Mode:        {health['mode']}")
    print(f"    Nodes:       {health['nodes']}")
    print(f"    Edges:       {health['edges']}")
    print(f"    Avg degree:  {health['avg_degree']:.2f}")

    triggers = check_triggers(G, health)
    print(f"\n  Metamorphosis triggers: {len(triggers)}")
    for trigger in triggers:
        print(f"    [{trigger['type']}] {trigger['description']} "
              f"(urgency={trigger['urgency']:.2f})")

    if triggers:
        print(f"\n  Proposed actions:")
        for trigger in triggers:
            print(f"    -> Address: {trigger['description']}")
    else:
        print("\n  No actions needed - system is healthy")
    print()

    # =====================================================================
    # SECTION 6: Adaptive Learning Summary
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: Adaptive Learning Summary")
    print("=" * 70)

    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print(f"\n  Rule effectiveness rankings (top 5):")
    best = rulial.get_best_rules(5)
    for rank, (name, score) in enumerate(best, 1):
        print(f"    {rank}. {name:25s}  {score:.2f}")
    if effectiveness:
        worst_rule = min(effectiveness, key=lambda k: effectiveness[k]["effectiveness"])
        print(f"    Deprioritized: {worst_rule} "
              f"(eff={effectiveness[worst_rule]['effectiveness']:.2f})")

    if basis_sampler.effectiveness:
        best_basis = max(basis_sampler.effectiveness, key=basis_sampler.effectiveness.get)
        worst_basis = min(basis_sampler.effectiveness, key=basis_sampler.effectiveness.get)
        print(f"\n  Best measurement basis: {best_basis} "
              f"(rate={basis_sampler.effectiveness[best_basis]:.2f})")
        print(f"  Worst measurement basis: {worst_basis} "
              f"(rate={basis_sampler.effectiveness[worst_basis]:.2f})")

    frame_eff = frame_selector.get_effectiveness()
    if frame_eff:
        best_frame = max(frame_eff, key=frame_eff.get)
        print(f"\n  Optimal frame: {best_frame} "
              f"(effectiveness={frame_eff[best_frame]:.2f})")

    print(f"\n  System fitness: {health['fitness']:.3f}")
    if triggers:
        print(f"  Self-repair: {len(triggers)} trigger(s) detected, actions recommended")
    else:
        print(f"  Self-repair: no actions needed")
    print()
    print("  Implementation note: this uses collections.Counter + numpy.random.beta")
    print("  for Thompson sampling, networkx.DiGraph for the knowledge graph,")
    print("  and simple dict-based tracking for all learning components.")
    print()


if __name__ == "__main__":
    main()
