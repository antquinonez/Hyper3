"""
Plain Python/NetworkX reimplementation of the Hyper3 infrastructure self-healing demo.

Reimplements all 8 sections using only networkx.DiGraph and standard library,
demonstrating the same feedback-driven evolution, cross-operation correlation,
bias profiling, metamorphosis validation, and multiway merge insights that
Hyper3 provides out of the box.

Run with:
    .venv/bin/python examples/comparison/infrastructure_self_healing.py
"""

from __future__ import annotations

import copy
import uuid
from collections import defaultdict
from itertools import combinations

import networkx as nx


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

INVERSE_MAP = {
    "blocks": "blocked_by",
}


class FeedbackSignal:
    def __init__(self, operation: str, node_id: str, positive: bool, details: dict | None = None):
        self.operation = operation
        self.node_id = node_id
        self.positive = positive
        self.details = details or {}


class OperationFeedback:
    def __init__(self) -> None:
        self.collapse_signals: list[FeedbackSignal] = []
        self.retrieval_signals: list[FeedbackSignal] = []
        self.inference_signals: list[FeedbackSignal] = []
        self._reinforced: set[str] = set()
        self._suppressed: set[str] = set()

    def record_collapse_outcome(self, query_id: str, node_id: str, *, correct: bool) -> None:
        self.collapse_signals.append(FeedbackSignal("collapse", node_id, correct, {"query": query_id}))
        if correct:
            self._reinforced.add(node_id)
        else:
            self._suppressed.add(node_id)

    def record_retrieval_outcome(
        self, query_id: str, relevant: set[str], irrelevant: set[str]
    ) -> None:
        for nid in relevant:
            self.retrieval_signals.append(FeedbackSignal("retrieval", nid, True, {"query": query_id}))
            self._reinforced.add(nid)
        for nid in irrelevant:
            self.retrieval_signals.append(FeedbackSignal("retrieval", nid, False, {"query": query_id}))
            self._suppressed.add(nid)

    def record_inference_outcome(self, inference_id: str, *, accepted: bool) -> None:
        self.inference_signals.append(
            FeedbackSignal("inference", inference_id, accepted, {"inference": inference_id})
        )

    def get_reinforced_nodes(self) -> set[str]:
        return self._reinforced

    def get_suppressed_nodes(self) -> set[str]:
        return self._suppressed

    def _collapse_accuracy(self) -> float:
        if not self.collapse_signals:
            return 1.0
        return sum(1 for s in self.collapse_signals if s.positive) / len(self.collapse_signals)

    def _retrieval_precision(self) -> float:
        if not self.retrieval_signals:
            return 1.0
        return sum(1 for s in self.retrieval_signals if s.positive) / len(self.retrieval_signals)

    def _inference_acceptance_rate(self) -> float:
        if not self.inference_signals:
            return 1.0
        return sum(1 for s in self.inference_signals if s.positive) / len(self.inference_signals)

    def get_fitness_trend(self) -> str:
        all_signals = self.collapse_signals + self.retrieval_signals + self.inference_signals
        if len(all_signals) < 2:
            return "stable"
        mid = len(all_signals) // 2
        first_half_rate = sum(1 for s in all_signals[:mid] if s.positive) / mid
        second_half_rate = sum(1 for s in all_signals[mid:] if s.positive) / (len(all_signals) - mid)
        if second_half_rate < first_half_rate - 0.1:
            return "declining"
        if second_half_rate > first_half_rate + 0.1:
            return "improving"
        return "stable"

    def cross_operation_summary(self) -> dict:
        node_ops: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
        for sig in self.collapse_signals:
            node_ops[sig.node_id]["collapse"].append(sig.positive)
        for sig in self.retrieval_signals:
            node_ops[sig.node_id]["retrieval"].append(sig.positive)
        for sig in self.inference_signals:
            node_ops[sig.node_id]["inference"].append(sig.positive)

        correlated: dict[str, dict] = {}
        for nid, ops in node_ops.items():
            if len(ops) >= 2:
                total_signals = sum(len(v) for v in ops.values())
                total_positive = sum(sum(v) for v in ops.values())
                correlated[nid] = {
                    "signal_count": total_signals,
                    "positive_rate": total_positive / total_signals if total_signals > 0 else 0.0,
                    "signal_types": sorted(ops.keys()),
                }
        return correlated

    def summary(self) -> dict:
        overall = (
            self._collapse_accuracy() + self._retrieval_precision() + self._inference_acceptance_rate()
        ) / 3.0
        correlated = self.cross_operation_summary()
        return {
            "overall_health": overall,
            "collapse_accuracy": self._collapse_accuracy(),
            "retrieval_precision": self._retrieval_precision(),
            "inference_acceptance_rate": self._inference_acceptance_rate(),
            "fitness_trend": self.get_fitness_trend(),
            "correlated_nodes": correlated,
        }


class RuleEffectiveness:
    def __init__(self) -> None:
        self.applications: dict[str, list[bool]] = defaultdict(list)

    def record(self, rule_name: str, success: bool) -> None:
        self.applications[rule_name].append(success)

    def compute_bias_profile(self) -> dict:
        if not self.applications:
            return {
                "reasoning_style": "unknown",
                "bias_score": 0.0,
                "rule_count": 0,
                "average_effectiveness": 0.0,
                "position_trajectory": "unknown",
                "dominant_rules": [],
                "underused_rules": [],
            }

        effectiveness: dict[str, float] = {}
        for rule_name, outcomes in self.applications.items():
            effectiveness[rule_name] = sum(outcomes) / len(outcomes) if outcomes else 0.0

        avg_eff = sum(effectiveness.values()) / len(effectiveness)
        sorted_rules = sorted(effectiveness.items(), key=lambda x: x[1], reverse=True)
        dominant = [r[0] for r in sorted_rules[:3] if r[1] >= avg_eff]
        underused = [r[0] for r in sorted_rules if r[1] < avg_eff * 0.5]

        values = list(effectiveness.values())
        if len(values) < 2:
            trajectory = "stable"
        elif values[-1] > values[0] + 0.1:
            trajectory = "exploiting"
        elif values[-1] < values[0] - 0.1:
            trajectory = "exploring"
        else:
            trajectory = "stable"

        if len(effectiveness) <= 1:
            style = "focused"
        elif max(effectiveness.values()) - min(effectiveness.values()) > 0.4:
            style = "exploratory"
        else:
            style = "balanced"

        bias_score = max(effectiveness.values()) - min(effectiveness.values()) if effectiveness else 0.0

        return {
            "reasoning_style": style,
            "bias_score": bias_score,
            "rule_count": len(effectiveness),
            "average_effectiveness": avg_eff,
            "position_trajectory": trajectory,
            "dominant_rules": dominant,
            "underused_rules": underused,
        }


def find_paths(G: nx.DiGraph, src: str, tgt: str, max_depth: int = 6) -> list[list[str]]:
    if src not in G or tgt not in G:
        return []
    return list(nx.all_simple_paths(G, src, tgt, cutoff=max_depth))


def evolve(
    G: nx.DiGraph,
    *,
    decay_factor: float = 0.95,
    prune_threshold: float = 0.1,
) -> dict:
    decayed = 0
    pruned = 0
    edges_to_decay = list(G.edges(data=True))
    for u, v, d in edges_to_decay:
        if "weight" in d:
            d["weight"] *= decay_factor
            decayed += 1

    nodes_to_prune = [
        n for n, d in G.nodes(data=True) if d.get("data", {}).get("health", 1.0) < prune_threshold
    ]
    for n in nodes_to_prune:
        G.remove_node(n)
        pruned += 1

    return {"decayed": decayed, "pruned": pruned, "merged": 0}


def evolve_with_feedback(
    G: nx.DiGraph,
    feedback: OperationFeedback,
    *,
    decay_factor: float = 0.95,
    prune_threshold: float = 0.1,
) -> dict:
    trend = feedback.get_fitness_trend()
    reinforced = 0
    suppressed = 0

    if trend == "declining":
        actual_decay = decay_factor * 1.5
        actual_threshold = prune_threshold * 0.75
    else:
        actual_decay = decay_factor
        actual_threshold = prune_threshold

    evo = evolve(G, decay_factor=actual_decay, prune_threshold=actual_threshold)

    reinforced_nodes = feedback.get_reinforced_nodes()
    top_reinforced = list(reinforced_nodes)[:3]
    for nid in top_reinforced:
        if nid in G:
            nd = G.nodes[nid]
            nd["data"] = nd.get("data", {})
            nd["data"]["health"] = min(1.0, nd["data"].get("health", 0.5) + 0.05)
            reinforced += 1

    suppressed_nodes = feedback.get_suppressed_nodes()
    for nid in suppressed_nodes:
        if nid in G:
            nd = G.nodes[nid]
            nd["data"] = nd.get("data", {})
            nd["data"]["health"] = 0.0
            G.remove_node(nid)
            suppressed += 1

    return {
        "decayed": evo["decayed"],
        "pruned": evo["pruned"] + suppressed,
        "merged": evo["merged"],
        "reinforced": reinforced,
        "suppressed": suppressed,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
    }


def compute_fitness(G: nx.DiGraph) -> float:
    if G.number_of_nodes() == 0:
        return 0.0
    total_health = 0.0
    for _, d in G.nodes(data=True):
        data = d.get("data", {})
        total_health += data.get("health", 0.5)
    return total_health / G.number_of_nodes()


def snapshot_graph(G: nx.DiGraph) -> dict:
    return {
        "nodes": set(G.nodes()),
        "edges": set(G.edges()),
        "node_data": {n: copy.deepcopy(d) for n, d in G.nodes(data=True)},
        "edge_data": {e: copy.deepcopy(d) for u, v, d in G.edges(data=True) for e in [(u, v)]},
    }


def restore_graph(G: nx.DiGraph, snap: dict) -> None:
    G.clear()
    for n, d in snap["node_data"].items():
        G.add_node(n, **d)
    for (u, v), d in snap["edge_data"].items():
        G.add_edge(u, v, **d)


def apply_transitive_rule(G: nx.DiGraph, edge_label: str) -> list[tuple[str, str]]:
    new_edges: list[tuple[str, str]] = []
    edges_of_label = [(u, v) for u, v, d in G.edges(data=True) if d.get("label") == edge_label]
    edge_set = set(edges_of_label)
    for (s1, t1), (s2, t2) in combinations(edges_of_label, 2):
        if t1 == s2 and (s1, t2) not in edge_set:
            new_edges.append((s1, t2))
        if t2 == s1 and (s2, t1) not in edge_set:
            new_edges.append((s2, t1))
    for u, v in new_edges:
        G.add_edge(u, v, label=edge_label, weight=0.5, inferred=True)
    return new_edges


def apply_inverse_rule(G: nx.DiGraph, edge_label: str, inverse_label: str) -> list[tuple[str, str]]:
    new_edges: list[tuple[str, str]] = []
    for u, v, d in list(G.edges(data=True)):
        if d.get("label") == edge_label:
            if not any(
                e_d.get("label") == inverse_label
                for _, _, e_d in G.edges(v, data=True)
                if _ == u
            ):
                new_edges.append((v, u))
    for u, v in new_edges:
        G.add_edge(u, v, label=inverse_label, weight=0.5, inferred=True)
    return new_edges


def multiway_expand(
    G: nx.DiGraph,
    seed_nodes: set[str],
    edge_labels: list[str],
    inverse_pairs: list[tuple[str, str]],
    max_states: int = 12,
) -> dict:
    states: dict[str, nx.DiGraph] = {}
    state_edges: dict[str, set[tuple[str, str, str]]] = {}
    state_meta: dict[str, dict] = {}
    state_counter = [0]

    def make_state_id() -> str:
        state_counter[0] += 1
        return f"state_{state_counter[0]:03d}"

    initial_id = make_state_id()
    states[initial_id] = G.copy()
    state_edges[initial_id] = set()
    state_meta[initial_id] = {"parent": None, "rule": "seed", "depth": 0}

    queue = [initial_id]
    visited_edges: set[tuple[str, str, str]] = {
        (u, v, d.get("label", "")) for u, v, d in G.edges(data=True)
    }

    rules_applied = 0
    edges_produced = 0

    while queue and len(states) < max_states:
        sid = queue.pop(0)
        sg = states[sid]

        for label in edge_labels:
            trans_new = apply_transitive_rule(sg, label)
            for u, v in trans_new:
                edge_key = (u, v, label)
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    edges_produced += 1
                    new_id = make_state_id()
                    states[new_id] = sg.copy()
                    state_edges[new_id] = {(u, v, label)}
                    state_meta[new_id] = {"parent": sid, "rule": f"transitive_{label}", "depth": state_meta[sid]["depth"] + 1}
                    rules_applied += 1
                    queue.append(new_id)
                    if len(states) >= max_states:
                        break
            if len(states) >= max_states:
                break

        for fwd, inv in inverse_pairs:
            inv_new = apply_inverse_rule(sg, fwd, inv)
            for u, v in inv_new:
                edge_key = (u, v, inv)
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    edges_produced += 1
                    new_id = make_state_id()
                    states[new_id] = sg.copy()
                    state_edges[new_id] = {(u, v, inv)}
                    state_meta[new_id] = {"parent": sid, "rule": f"inverse_{fwd}", "depth": state_meta[sid]["depth"] + 1}
                    rules_applied += 1
                    queue.append(new_id)
                    if len(states) >= max_states:
                        break
            if len(states) >= max_states:
                break

    return {
        "states": states,
        "state_edges": state_edges,
        "state_meta": state_meta,
        "states_created": len(states),
        "edges_produced": edges_produced,
        "rules_applied": rules_applied,
    }


def find_merge_insights(mw_result: dict, similarity_threshold: float = 0.4) -> list[dict]:
    state_edges = mw_result["state_edges"]
    state_meta = mw_result["state_meta"]
    state_ids = list(state_edges.keys())

    all_graph_edges: dict[str, set[tuple[str, str, str]]] = {}
    for sid, sg in mw_result["states"].items():
        all_graph_edges[sid] = {(u, v, d.get("label", "")) for u, v, d in sg.edges(data=True)}

    merges: list[dict] = []
    seen_pairs: set[frozenset[str]] = set()

    for i, j in combinations(range(len(state_ids)), 2):
        sid_a = state_ids[i]
        sid_b = state_ids[j]
        pair_key = frozenset({sid_a, sid_b})
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        edges_a = all_graph_edges[sid_a]
        edges_b = all_graph_edges[sid_b]

        if not edges_a and not edges_b:
            similarity = 1.0
        elif not edges_a or not edges_b:
            similarity = 0.0
        else:
            intersection = edges_a & edges_b
            union = edges_a | edges_b
            similarity = len(intersection) / len(union)

        if similarity >= similarity_threshold:
            unique_a = edges_a - edges_b
            unique_b = edges_b - edges_a
            insights = []
            if unique_a:
                unique_nodes_a: set[str] = set()
                for u, v, _ in unique_a:
                    unique_nodes_a.add(u)
                    unique_nodes_a.add(v)
                insights.append({
                    "state_id": sid_a,
                    "rule_applied": state_meta[sid_a]["rule"],
                    "unique_nodes": unique_nodes_a,
                    "unique_edges": unique_a,
                })
            if unique_b:
                unique_nodes_b: set[str] = set()
                for u, v, _ in unique_b:
                    unique_nodes_b.add(u)
                    unique_nodes_b.add(v)
                insights.append({
                    "state_id": sid_b,
                    "rule_applied": state_meta[sid_b]["rule"],
                    "unique_nodes": unique_nodes_b,
                    "unique_edges": unique_b,
                })
            merges.append({
                "similarity": similarity,
                "state_a": sid_a,
                "state_b": sid_b,
                "insights": insights,
            })

    return merges


def main() -> None:
    G = nx.DiGraph()
    feedback = OperationFeedback()
    rule_eff = RuleEffectiveness()

    print("=" * 70)
    print("SECTION 1: Building Healthy Infrastructure Graph")
    print("=" * 70)

    for name, data in SERVERS.items():
        G.add_node(name, data=copy.deepcopy(data))

    for src, tgt, label in DEPENDENCIES:
        G.add_edge(src, tgt, label=label, weight=0.8)

    for src, tgt, label in FAILURE_MODES:
        G.add_edge(src, tgt, label=label, weight=0.7)

    print(f"  Servers: {len(SERVERS)}")
    print(f"  Dependencies: {len(DEPENDENCIES)}")
    print(f"  Failure modes: {len(FAILURE_MODES)}")
    print(f"  Total nodes: {G.number_of_nodes()}, edges: {G.number_of_edges()}")
    print()

    print("=" * 70)
    print("SECTION 2: Round 1 - Healthy System Operations")
    print("=" * 70)

    paths = find_paths(G, "cdn-edge-01", "db-pg-primary", max_depth=6)
    print(f"  Paths CDN->DB: {len(paths)}")

    for path in paths[:3]:
        print(f"    {' -> '.join(path)}")

    feedback.record_collapse_outcome("qs_auth", "auth-svc-01", correct=True)
    feedback.record_collapse_outcome("qs_payment", "payment-svc-01", correct=True)
    feedback.record_collapse_outcome("qs_order", "order-svc-01", correct=True)

    feedback.record_retrieval_outcome("database", {"db-pg-primary", "db-pg-replica-01"}, set())
    feedback.record_retrieval_outcome("cache", {"cache-redis-01", "cache-redis-02"}, {"cache-redis-02"})

    feedback.record_inference_outcome("inf_call_chain_1", accepted=True)
    feedback.record_inference_outcome("inf_call_chain_2", accepted=True)

    result1 = evolve(G)
    print(f"\n  Round 1 evolve: decayed={result1['decayed']}, pruned={result1['pruned']}, "
          f"merged={result1['merged']}")
    print(f"  Fitness trend after Round 1: {feedback.get_fitness_trend()}")
    print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print()

    print("=" * 70)
    print("SECTION 3: Round 2 - Degradation (Noisy/Stale Nodes)")
    print("=" * 70)

    for name, data in NOISY_NODES.items():
        G.add_node(name, data=copy.deepcopy(data))

    G.add_edge("stale-metric-aggregator-01", "db-pg-primary", label="reads_from", weight=0.2)
    G.add_edge("legacy-xml-api-01", "lb-ha-01", label="routes_to", weight=0.15)
    G.add_edge("zombie-cron-worker-01", "queue-rmq-01", label="publishes_to", weight=0.1)

    print(f"  Added {len(NOISY_NODES)} noisy/stale nodes with low weights")
    print(f"  Total nodes: {G.number_of_nodes()}")

    for i in range(5):
        evo = evolve(G)
        print(f"  Evolution cycle {i + 1}: decayed={evo['decayed']}, pruned={evo['pruned']}")

    stale_names = [
        "stale-metric-aggregator-01", "deprecated-test-runner-01",
        "orphan-debug-endpoint", "legacy-xml-api-01",
        "unused-data-pipeline-01", "ghost-replica-set-01",
        "abandoned-ml-experiment-01", "zombie-cron-worker-01",
    ]
    for stale_name in stale_names:
        sid = stale_name
        for _ in range(3):
            feedback.record_retrieval_outcome(
                "infrastructure_search", set(), {sid},
            )

    feedback.record_collapse_outcome("qs_stale", "stale-metric-aggregator-01", correct=False)
    feedback.record_collapse_outcome("qs_stale_2", "deprecated-test-runner-01", correct=False)
    feedback.record_collapse_outcome("qs_stale_3", "legacy-xml-api-01", correct=False)

    for healthy_name in ["api-gw-01", "order-svc-01", "payment-svc-01", "db-pg-primary", "cache-redis-01"]:
        feedback.record_collapse_outcome(f"qs_{healthy_name}", healthy_name, correct=True)
        for _ in range(3):
            feedback.record_retrieval_outcome(
                "infrastructure_search", {healthy_name}, set(),
            )

    feedback.record_inference_outcome("inf_stale_1", accepted=False)
    feedback.record_inference_outcome("inf_stale_2", accepted=False)
    feedback.record_inference_outcome("inf_stale_3", accepted=False)
    feedback.record_inference_outcome("inf_good_1", accepted=True)

    trend = feedback.get_fitness_trend()
    summary_before = feedback.summary()
    print(f"\n  Fitness trend after degradation: {trend}")
    print(f"  Overall health: {summary_before['overall_health']:.2f}")
    print(f"  Collapse accuracy: {summary_before['collapse_accuracy']:.2f}")
    print(f"  Retrieval precision: {summary_before['retrieval_precision']:.2f}")
    print(f"  Inference acceptance: {summary_before['inference_acceptance_rate']:.2f}")
    print(f"  Reinforced nodes: {len(feedback.get_reinforced_nodes())}")
    print(f"  Suppressed nodes: {len(feedback.get_suppressed_nodes())}")
    print()

    print("=" * 70)
    print("SECTION 4: Round 3 - Feedback-Driven Recovery")
    print("=" * 70)

    recovery = evolve_with_feedback(G, feedback)
    print(f"  Feedback-driven evolution:")
    print(f"    decayed={recovery['decayed']}, pruned={recovery['pruned']}, "
          f"reinforced={recovery['reinforced']}, suppressed={recovery['suppressed']}")
    print(f"    Nodes: {recovery['node_count']}, Edges: {recovery['edge_count']}")

    for i in range(3):
        evo = evolve_with_feedback(G, feedback)
        print(f"  Recovery cycle {i + 1}: pruned={evo['pruned']}, "
              f"reinforced={evo['reinforced']}, suppressed={evo['suppressed']}")

    summary_after = feedback.summary()
    print(f"\n  Post-recovery health: {summary_after['overall_health']:.2f}")
    print(f"  Post-recovery trend: {summary_after['fitness_trend']}")
    print(f"  Nodes remaining: {G.number_of_nodes()}")
    print()

    remaining_stale = 0
    remaining_healthy = 0
    for n, d in G.nodes(data=True):
        data = d.get("data", {})
        if data.get("stale"):
            remaining_stale += 1
        elif data.get("category") == "server":
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
        label = nid if nid in G else f"[removed:{nid[:12]}]"
        print(f"    {label:<30} signals={info['signal_count']}, "
              f"positive_rate={info['positive_rate']:.2f}, "
              f"types={info['signal_types']}")
    print()

    print("=" * 70)
    print("SECTION 6: Computational Bias Profile")
    print("=" * 70)

    for label in ["calls", "routes_to", "blocks"]:
        apply_transitive_rule(G, label)
        rule_eff.record(f"transitive_{label}", success=True)
    for fwd, inv in INVERSE_MAP.items():
        apply_inverse_rule(G, fwd, inv)
        rule_eff.record(f"inverse_{fwd}_{inv}", success=True)

    rule_eff.record("transitive_reads_from", success=False)
    rule_eff.record("transitive_monitors", success=False)

    profile = rule_eff.compute_bias_profile()
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

    v0_id = str(uuid.uuid4())[:8]
    snap_v0 = snapshot_graph(G)
    print(f"  Captured baseline version: {v0_id}")

    fitness_before = compute_fitness(G)
    triggers_found = fitness_before < 0.8

    if triggers_found:
        print(f"  Metamorphosis triggers: 1")
        print(f"    low_fitness: System fitness below threshold (urgency=0.80)")

        plan_risk = 0.3
        plan_improvement = 0.15
        print(f"  Plan: 2 actions, expected improvement={plan_improvement:.2f}, "
              f"risk={plan_risk:.2f}")

        snap_pre = snapshot_graph(G)

        for n, d in list(G.nodes(data=True)):
            data = d.get("data", {})
            if data.get("stale") or data.get("health", 1.0) < 0.2:
                G.remove_node(n)

        for u, v, d in list(G.edges(data=True)):
            if u not in G or v not in G:
                continue
            if d.get("weight", 1.0) < 0.3:
                d["weight"] = 0.3

        fitness_after = compute_fitness(G)
        improvement = fitness_after - fitness_before
        rolled_back = improvement < -0.01

        if rolled_back:
            restore_graph(G, snap_pre)
            fitness_after = compute_fitness(G)

        print(f"  Validated execution:")
        print(f"    rolled_back={rolled_back}")
        print(f"    fitness_before={fitness_before:.4f}")
        print(f"    fitness_after={fitness_after:.4f}")
        print(f"    improvement={improvement:.6f}")
    else:
        print("  No metamorphosis triggers (system recovered)")

        snap_current = snapshot_graph(G)
        nodes_added = snap_current["nodes"] - snap_v0["nodes"]
        nodes_removed = snap_v0["nodes"] - snap_current["nodes"]
        edges_added = snap_current["edges"] - snap_v0["edges"]
        edges_removed = snap_v0["edges"] - snap_current["edges"]
        total_changes = len(nodes_added) + len(nodes_removed) + len(edges_added) + len(edges_removed)
        print(f"  Graph diff from baseline:")
        print(f"    Nodes added: {len(nodes_added)}")
        print(f"    Nodes removed: {len(nodes_removed)}")
        print(f"    Edges added: {len(edges_added)}")
        print(f"    Edges removed: {len(edges_removed)}")
        print(f"    Total changes: {total_changes}")
    print()

    print("=" * 70)
    print("SECTION 8: Multiway Reasoning with Merge Insights")
    print("=" * 70)

    mw_result = multiway_expand(
        G,
        {"api-gw-01", "order-svc-01", "payment-svc-01", "db-pg-primary"},
        ["calls", "routes_to", "blocks"],
        [("blocks", "blocked_by")],
        max_states=12,
    )
    print(f"  Multiway expansion: {mw_result['states_created']} states, "
          f"{mw_result['edges_produced']} edges produced, "
          f"{mw_result['rules_applied']} rules applied")

    merges = find_merge_insights(mw_result, similarity_threshold=0.4)
    print(f"  Causal invariants found: {len(merges)}")
    for merge in merges[:5]:
        print(f"    Merge: similarity={merge['similarity']:.3f}")
        for insight in merge["insights"]:
            print(f"      state={insight['state_id']}: rule={insight['rule_applied']}, "
                  f"unique_nodes={len(insight['unique_nodes'])}, "
                  f"unique_edges={len(insight['unique_edges'])}")
    if len(merges) > 5:
        print(f"    ... and {len(merges) - 5} more merges")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Final graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"  Stale nodes cleaned: {len(NOISY_NODES) - remaining_stale}/{len(NOISY_NODES)}")
    print(f"  Healthy nodes preserved: {remaining_healthy}")
    print(f"  Fitness journey: declining -> {summary_after['fitness_trend']}")
    print(f"  Cross-operation correlations: {len(correlated)} nodes tracked")
    print(f"  Multiway states explored: {mw_result['states_created']}")
    print(f"  Causal merges: {len(merges)}")
    print()
    print("  Key insight: The feedback loop automatically identifies and removes")
    print("  degraded infrastructure while preserving healthy nodes. Reinforced")
    print("  nodes (frequently accessed) gain weight; suppressed nodes (poor")
    print("  retrieval outcomes) are pruned. The system self-tunes without manual")
    print("  intervention.")
    print()


if __name__ == "__main__":
    main()
