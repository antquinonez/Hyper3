"""
Self-Evolving Cognition: Feedback, Validation, and Meta-Awareness (Plain Python)
================================================================================

Reimplements examples/advanced/13_self_evolving_cognition.py using only
networkx, numpy, and standard libraries. No Hyper3 imports.

Implements five capabilities from scratch:
  1. Feedback-driven evolution — manual decay/prune/reinforce with trend tracking
  2. Metamorphosis validation — snapshot/rollback with fitness comparison
  3. Cross-operation feedback — multi-signal aggregation and correlation
  4. Computational bias profile — rule effectiveness tracking and style analysis
  5. Causal merge insight preservation — set-difference merge provenance

Run with:
    .venv/bin/python examples/comparison/13_self_evolving_cognition.py
"""

from __future__ import annotations

import copy
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import networkx as nx


@dataclass
class FeedbackSignal:
    signal_type: str
    node_id: str
    outcome: bool
    confidence: float = 0.0
    context: dict = field(default_factory=dict)
    timestamp: float = 0.0


class OperationFeedback:
    def __init__(self):
        self._signals: list[FeedbackSignal] = []
        self._collapse_stats: dict[str, dict[str, int]] = {}
        self._retrieval_stats: dict[str, dict[str, int]] = {}
        self._inference_stats: dict[str, dict[str, int]] = {}
        self._evolution_fitness_history: list[float] = []

    def record_collapse_outcome(self, qs_id: str, selected_node_id: str, correct: bool | None = None):
        stats = self._collapse_stats.setdefault(qs_id, {"correct": 0, "incorrect": 0, "unknown": 0})
        if correct is True:
            stats["correct"] += 1
        elif correct is False:
            stats["incorrect"] += 1
        else:
            stats["unknown"] += 1
        self._signals.append(FeedbackSignal("collapse", selected_node_id, correct is True, 1.0 if correct is not None else 0.5))

    def record_retrieval_outcome(self, query: str, relevant_ids: set[str], irrelevant_ids: set[str]):
        stats = self._retrieval_stats.setdefault(query, {"relevant": 0, "irrelevant": 0})
        stats["relevant"] += len(relevant_ids)
        stats["irrelevant"] += len(irrelevant_ids)
        for nid in relevant_ids:
            self._signals.append(FeedbackSignal("retrieval_relevant", nid, True))
        for nid in irrelevant_ids:
            self._signals.append(FeedbackSignal("retrieval_irrelevant", nid, False))

    def record_inference_outcome(self, edge_id: str, accepted: bool):
        stats = self._inference_stats.setdefault(edge_id, {"accepted": 0, "rejected": 0})
        if accepted:
            stats["accepted"] += 1
        else:
            stats["rejected"] += 1
        self._signals.append(FeedbackSignal("inference", edge_id, accepted))

    def record_evolution_outcome(self, fitness: float):
        self._evolution_fitness_history.append(fitness)
        self._signals.append(FeedbackSignal("evolution", "", fitness > 0.5, fitness))

    def get_reinforced_nodes(self, min_signals: int = 2) -> set[str]:
        node_outcomes: dict[str, list[bool]] = {}
        for s in self._signals:
            if s.signal_type in ("retrieval_relevant", "collapse"):
                node_outcomes.setdefault(s.node_id, []).append(s.outcome)
        return {
            nid for nid, outcomes in node_outcomes.items()
            if len(outcomes) >= min_signals and sum(outcomes) / len(outcomes) > 0.5
        }

    def get_suppressed_nodes(self, min_signals: int = 2) -> set[str]:
        node_outcomes: dict[str, list[bool]] = {}
        for s in self._signals:
            if s.signal_type == "retrieval_irrelevant":
                node_outcomes.setdefault(s.node_id, []).append(True)
        return {nid for nid, outcomes in node_outcomes.items() if len(outcomes) >= min_signals}

    def get_fitness_trend(self) -> str:
        if len(self._evolution_fitness_history) < 2:
            return "insufficient_data"
        recent = self._evolution_fitness_history[-5:]
        slope = (recent[-1] - recent[0]) / len(recent)
        if slope > 0.02:
            return "improving"
        if slope < -0.02:
            return "declining"
        return "stable"

    def collapse_accuracy(self) -> float:
        tc = sum(s.get("correct", 0) for s in self._collapse_stats.values())
        ti = sum(s.get("incorrect", 0) for s in self._collapse_stats.values())
        total = tc + ti
        return tc / total if total else 0.5

    def retrieval_precision(self) -> float:
        tr = sum(s.get("relevant", 0) for s in self._retrieval_stats.values())
        ti = sum(s.get("irrelevant", 0) for s in self._retrieval_stats.values())
        total = tr + ti
        return tr / total if total else 0.5

    def inference_acceptance_rate(self) -> float:
        ta = sum(s.get("accepted", 0) for s in self._inference_stats.values())
        tr = sum(s.get("rejected", 0) for s in self._inference_stats.values())
        total = ta + tr
        return ta / total if total else 0.5

    def cross_operation_summary(self) -> dict:
        collapse_acc = self.collapse_accuracy()
        retrieval_prec = self.retrieval_precision()
        inference_acc = self.inference_acceptance_rate()
        trend = self.get_fitness_trend()
        health = (collapse_acc + retrieval_prec + inference_acc) / 3.0

        type_counts: dict[str, int] = {}
        for s in self._signals:
            base_type = s.signal_type.split("_")[0]
            type_counts[base_type] = type_counts.get(base_type, 0) + 1

        positive_by_node: dict[str, int] = {}
        total_by_node: dict[str, int] = {}
        for s in self._signals:
            if s.node_id:
                total_by_node[s.node_id] = total_by_node.get(s.node_id, 0) + 1
                if s.outcome:
                    positive_by_node[s.node_id] = positive_by_node.get(s.node_id, 0) + 1

        correlated_nodes: dict[str, dict] = {}
        for nid, count in total_by_node.items():
            if count >= 3:
                pos = positive_by_node.get(nid, 0)
                correlated_nodes[nid] = {
                    "positive_rate": pos / count,
                    "signal_count": count,
                    "signal_types": list({
                        s.signal_type.split("_")[0]
                        for s in self._signals if s.node_id == nid
                    }),
                }

        return {
            "collapse_accuracy": collapse_acc,
            "retrieval_precision": retrieval_prec,
            "inference_acceptance_rate": inference_acc,
            "fitness_trend": trend,
            "overall_health": health,
            "signal_type_distribution": type_counts,
            "total_signals": len(self._signals),
            "correlated_nodes": correlated_nodes,
        }


class GraphSnapshot:
    def __init__(self, G: nx.DiGraph, version_id: str):
        self.version_id = version_id
        self.nodes = set(G.nodes())
        self.edges = [(u, v, dict(d)) for u, v, d in G.edges(data=True)]
        self.node_data = {n: dict(G.nodes[n]) for n in G.nodes()}


class GraphDiffer:
    def __init__(self, G: nx.DiGraph):
        self._G = G
        self._versions: dict[str, GraphSnapshot] = {}
        self._counter = 0

    def capture(self) -> GraphSnapshot:
        self._counter += 1
        vid = f"v{self._counter}"
        snap = GraphSnapshot(self._G, vid)
        self._versions[vid] = snap
        return snap

    def rollback_to_version(self, version_id: str):
        snap = self._versions[version_id]
        self._G.clear()
        for n in snap.nodes:
            self._G.add_node(n, **snap.node_data.get(n, {}))
        for u, v, data in snap.edges:
            self._G.add_edge(u, v, **data)


class RuleEffectivenessTracker:
    def __init__(self):
        self._outcomes: dict[str, dict[str, int]] = {}

    def record_outcome(self, rule_name: str, success: bool):
        stats = self._outcomes.setdefault(rule_name, {"success": 0, "failure": 0})
        if success:
            stats["success"] += 1
        else:
            stats["failure"] += 1

    def get_effectiveness(self) -> dict[str, dict]:
        result = {}
        for name, stats in self._outcomes.items():
            total = stats["success"] + stats["failure"]
            result[name] = {
                "effectiveness": stats["success"] / total if total else 0.0,
                "applications": total,
            }
        return result

    def compute_bias_profile(self, position_history: list[float] | None = None) -> dict:
        effectiveness = self.get_effectiveness()
        if not effectiveness:
            return {
                "dominant_rules": [],
                "underused_rules": [],
                "reasoning_style": "unknown",
                "position_trajectory": "no_data",
                "bias_score": 0.0,
            }

        sorted_by_eff = sorted(effectiveness.items(), key=lambda x: x[1]["effectiveness"], reverse=True)
        total_apps = sum(e["applications"] for _, e in sorted_by_eff)
        avg_eff = sum(e["effectiveness"] for _, e in sorted_by_eff) / len(sorted_by_eff)

        dominant = [name for name, stats in sorted_by_eff[:3] if stats["effectiveness"] > avg_eff]
        underused = [
            name for name, stats in sorted_by_eff
            if stats["effectiveness"] > avg_eff and stats["applications"] < (total_apps / len(sorted_by_eff))
        ]

        if dominant:
            style = "focused"
        elif len(sorted_by_eff) > 5:
            style = "exploratory"
        else:
            style = "balanced"

        trajectory = "stable"
        if position_history and len(position_history) >= 3:
            recent = position_history[-3:]
            if recent[-1] > recent[0] + 0.1:
                trajectory = "expanding"
            elif recent[-1] < recent[0] - 0.1:
                trajectory = "contracting"

        max_share = max(e["applications"] / max(total_apps, 1) for _, e in sorted_by_eff)

        return {
            "dominant_rules": dominant,
            "underused_rules": underused,
            "reasoning_style": style,
            "position_trajectory": trajectory,
            "bias_score": max_share,
            "average_effectiveness": avg_eff,
            "rule_count": len(sorted_by_eff),
        }


@dataclass
class MergeInsight:
    state_id: str
    unique_nodes: list[str]
    unique_edges: list[str]
    rule_applied: str
    node_count: int
    edge_count: int


@dataclass
class ConvergenceRecord:
    state_a_id: str
    state_b_id: str
    similarity: float
    merged_into: str
    insights: list[MergeInsight]


@dataclass
class MwState:
    id: str
    active_node_ids: frozenset[str]
    rule_applied: str | None
    depth: int
    produced_node_ids: list[str]
    produced_edge_ids: list[str]


class CausalMergeEngine:
    def __init__(self, threshold: float = 0.5):
        self._states: dict[str, MwState] = {}
        self._threshold = threshold
        self._counter = 0

    def add_state(self, active_node_ids: frozenset[str], rule_applied: str | None, depth: int, produced_node_ids: list[str], produced_edge_ids: list[str]) -> MwState:
        self._counter += 1
        sid = f"state_{self._counter}"
        state = MwState(sid, active_node_ids, rule_applied, depth, produced_node_ids, produced_edge_ids)
        self._states[sid] = state
        return state

    def _compute_similarity(self, a: MwState, b: MwState) -> float:
        node_sim = len(a.active_node_ids & b.active_node_ids) / max(len(a.active_node_ids | b.active_node_ids), 1)
        ea = set(a.produced_edge_ids)
        eb = set(b.produced_edge_ids)
        edge_sim = len(ea & eb) / max(len(ea | eb), 1) if (ea or eb) else 1.0
        return 0.7 * node_sim + 0.3 * edge_sim

    def _extract_insight(self, state: MwState, other_node_ids: frozenset[str], other_edge_ids: set[str]) -> MergeInsight:
        return MergeInsight(
            state_id=state.id,
            unique_nodes=[nid for nid in state.active_node_ids if nid not in other_node_ids],
            unique_edges=[eid for eid in state.produced_edge_ids if eid not in other_edge_ids],
            rule_applied=state.rule_applied or "",
            node_count=len(state.active_node_ids),
            edge_count=len(state.produced_edge_ids),
        )

    def merge_invariant_states(self) -> list[ConvergenceRecord]:
        merged: list[ConvergenceRecord] = []
        consumed: set[str] = set()
        state_ids = list(self._states.keys())
        for i, sa_id in enumerate(state_ids):
            for sb_id in state_ids[i + 1:]:
                if sa_id in consumed or sb_id in consumed:
                    continue
                sa = self._states[sa_id]
                sb = self._states[sb_id]
                sim = self._compute_similarity(sa, sb)
                if sim >= self._threshold:
                    consumed.add(sa_id)
                    consumed.add(sb_id)
                    insight_a = self._extract_insight(sa, sb.active_node_ids, set(sb.produced_edge_ids))
                    insight_b = self._extract_insight(sb, sa.active_node_ids, set(sa.produced_edge_ids))
                    merged_nodes = sa.active_node_ids | sb.active_node_ids
                    merged_edges = list(set(sa.produced_edge_ids + sb.produced_edge_ids))
                    rules = []
                    if sa.rule_applied:
                        rules.append(sa.rule_applied)
                    if sb.rule_applied and sb.rule_applied not in rules:
                        rules.append(sb.rule_applied)
                    ms = self.add_state(
                        merged_nodes, " + ".join(rules) if rules else None,
                        min(sa.depth, sb.depth),
                        list(set(sa.produced_node_ids + sb.produced_node_ids)),
                        merged_edges,
                    )
                    merged.append(ConvergenceRecord(sa_id, sb_id, sim, ms.id, [insight_a, insight_b]))
        return merged


def evolve_graph(
    G: nx.DiGraph,
    *,
    fitness_trend: str = "stable",
    reinforced_nodes: set[str] | None = None,
    suppressed_nodes: set[str] | None = None,
    decay_factor: float = 0.95,
    boost: float = 1.1,
) -> dict:
    actual_decay = decay_factor
    if fitness_trend == "declining":
        actual_decay = min(decay_factor + 0.03, 0.99)

    decayed = 0
    for u, v, data in G.edges(data=True):
        if "weight" in data:
            data["weight"] *= actual_decay
            decayed += 1

    pruned = []
    for node in list(G.nodes()):
        if G.degree(node) == 0 and not G.nodes[node].get("data"):
            pruned.append(node)
            G.remove_node(node)

    reinforced_count = 0
    if reinforced_nodes:
        for nid in reinforced_nodes:
            if G.has_node(nid):
                for _, _, data in G.edges(nid, data=True):
                    data["weight"] = data.get("weight", 1.0) * boost
                reinforced_count += 1

    suppressed_count = 0
    if suppressed_nodes:
        for nid in suppressed_nodes:
            if G.has_node(nid):
                G.remove_node(nid)
                suppressed_count += 1

    return {
        "decayed": decayed,
        "pruned": len(pruned),
        "merged": 0,
        "reinforced": reinforced_count,
        "suppressed": suppressed_count,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
    }


def compute_fitness(G: nx.DiGraph, total_nodes: int) -> float:
    if total_nodes == 0:
        return 1.0
    prunes = total_nodes - G.number_of_nodes()
    return 1.0 - (prunes / (total_nodes + 1)) * 0.1


def transitive_inference(G: nx.DiGraph, edge_label: str) -> list[tuple[str, str]]:
    new_edges = []
    edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("label") == edge_label]
    edge_set = set(edges)
    for s1, t1 in edges:
        for s2, t2 in edges:
            if t1 == s2 and (s1, t2) not in edge_set:
                new_edges.append((s1, t2))
    return new_edges


def main():
    G = nx.DiGraph()
    total_nodes_created = 0
    feedback = OperationFeedback()
    rule_tracker = RuleEffectivenessTracker()

    print("=" * 70)
    print("SECTION 1: Feedback-Driven Evolution")
    print("=" * 70)

    for concept in ["alpha", "beta", "gamma", "delta", "epsilon"]:
        G.add_node(concept)
        total_nodes_created += 1
    G.add_edge("alpha", "beta", label="connects", weight=1.0)
    G.add_edge("beta", "gamma", label="connects", weight=1.0)
    G.add_edge("gamma", "delta", label="connects", weight=1.0)
    G.add_edge("delta", "epsilon", label="connects", weight=1.0)

    feedback.record_evolution_outcome(0.8)
    feedback.record_evolution_outcome(0.7)
    feedback.record_evolution_outcome(0.6)

    print(f"  Fitness trend: {feedback.get_fitness_trend()}")
    print(f"  Evolution before feedback-driven cycle:")
    result = evolve_graph(G, fitness_trend=feedback.get_fitness_trend())
    print(f"    decayed={result['decayed']}, pruned={result['pruned']}, "
          f"reinforced={result['reinforced']}, suppressed={result['suppressed']}")

    print()
    print("  Adding more concepts and recording positive feedback:")
    for concept in ["zeta", "eta", "theta"]:
        G.add_node(concept)
        total_nodes_created += 1
    G.add_edge("epsilon", "zeta", label="connects", weight=1.0)

    feedback.record_inference_outcome("edge_1", accepted=True)
    feedback.record_inference_outcome("edge_2", accepted=True)
    feedback.record_inference_outcome("edge_3", accepted=False)

    print(f"  Inference acceptance rate: {feedback.inference_acceptance_rate():.2f}")
    print(f"  Reinforced nodes: {len(feedback.get_reinforced_nodes())}")

    print()
    print("=" * 70)
    print("SECTION 2: Cross-Operation Feedback Summary")
    print("=" * 70)

    feedback.record_retrieval_outcome("connects", {"alpha"}, {"epsilon"})
    feedback.record_retrieval_outcome("connects", {"beta"}, set())

    summary = feedback.cross_operation_summary()
    print(f"  Overall health: {summary['overall_health']:.2f}")
    print(f"  Fitness trend: {summary['fitness_trend']}")
    print(f"  Signal distribution: {summary['signal_type_distribution']}")
    print(f"  Collapse accuracy: {summary['collapse_accuracy']:.2f}")
    print(f"  Retrieval precision: {summary['retrieval_precision']:.2f}")
    print(f"  Inference acceptance: {summary['inference_acceptance_rate']:.2f}")
    print(f"  Total signals recorded: {summary['total_signals']}")

    correlated = summary["correlated_nodes"]
    if correlated:
        print(f"  Nodes appearing across multiple operations: {len(correlated)}")
        for nid, info in list(correlated.items())[:3]:
            print(f"    {nid[:8]}: positive_rate={info['positive_rate']:.2f}, "
                  f"types={info['signal_types']}")

    print()
    print("=" * 70)
    print("SECTION 3: Metamorphosis with Validation and Rollback")
    print("=" * 70)

    for concept in ["a", "b", "c", "d", "e", "f", "g", "h"]:
        G.add_node(concept)
        total_nodes_created += 1
    G.add_edge("a", "b", label="causes", weight=1.0)
    G.add_edge("b", "c", label="causes", weight=1.0)
    G.add_edge("d", "e", label="prevents", weight=1.0)
    G.add_edge("e", "f", label="prevents", weight=1.0)

    differ = GraphDiffer(G)
    fitness_before = compute_fitness(G, total_nodes_created)

    pre_snap = differ.capture()
    new_edges = transitive_inference(G, "causes")
    for s, t in new_edges:
        G.add_edge(s, t, label="causes", weight=0.5)
    for s, t in [("d", "f",)]:
        pass

    fitness_after = compute_fitness(G, total_nodes_created)
    improvement = fitness_after - fitness_before
    rolled_back = False

    if improvement < 0:
        differ.rollback_to_version(pre_snap.version_id)
        rolled_back = True
        fitness_after = compute_fitness(G, total_nodes_created)

    print(f"  Validated execution:")
    print(f"    rolled_back={rolled_back}")
    print(f"    fitness_before={fitness_before:.3f}")
    print(f"    fitness_after={fitness_after:.3f}")
    print(f"    improvement={fitness_after - fitness_before:.3f}")

    print()
    print("  Simulating degraded fitness (force rollback):")
    pre_snap2 = differ.capture()
    nodes_to_remove = list(G.nodes())[:3]
    for n in nodes_to_remove:
        G.remove_node(n)
    fitness_after_degrade = compute_fitness(G, total_nodes_created)
    improvement2 = fitness_after_degrade - fitness_before

    if fitness_after_degrade < fitness_before:
        differ.rollback_to_version(pre_snap2.version_id)
        rolled_back2 = True
        fitness_after_degrade = compute_fitness(G, total_nodes_created)
    else:
        rolled_back2 = False

    print(f"    rolled_back={rolled_back2}")
    print(f"    fitness_before={compute_fitness(G, total_nodes_created):.3f}")
    print(f"    fitness_after_rollback={fitness_after_degrade:.3f}")

    print()
    print("=" * 70)
    print("SECTION 4: Computational Bias Profile")
    print("=" * 70)

    for concept in ["x", "y", "z"]:
        if not G.has_node(concept):
            G.add_node(concept)
            total_nodes_created += 1
    G.add_edge("x", "y", label="link", weight=1.0)
    G.add_edge("y", "z", label="link", weight=1.0)

    rule_tracker.record_outcome("transitive", success=True)
    rule_tracker.record_outcome("transitive", success=True)
    rule_tracker.record_outcome("transitive", success=False)
    rule_tracker.record_outcome("inverse", success=True)

    profile = rule_tracker.compute_bias_profile()
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
    print("SECTION 5: Causal Merge Insight Preservation")
    print("=" * 70)

    causal = CausalMergeEngine(threshold=0.5)
    shared_nodes = frozenset({"node_a", "node_b"})
    causal.add_state(shared_nodes | frozenset({"node_c"}), "transitive", 1, ["node_c"], ["edge_ac"])
    causal.add_state(shared_nodes | frozenset({"node_d"}), "inverse", 1, ["node_d"], ["edge_bd"])

    invariants = causal.merge_invariant_states()
    print(f"  Invariants found: {len(invariants)}")
    for inv in invariants:
        print(f"  Merge: {inv.state_a_id} + {inv.state_b_id} "
              f"(similarity={inv.similarity:.3f})")
        for insight in inv.insights:
            print(f"    State {insight.state_id}: "
                  f"rule={insight.rule_applied}, "
                  f"unique_nodes={len(insight.unique_nodes)}, "
                  f"unique_edges={len(insight.unique_edges)}")

    print()
    print("=" * 70)
    print("COMPLETE")


if __name__ == "__main__":
    main()
