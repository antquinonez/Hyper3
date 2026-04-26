from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import networkx as nx
import numpy as np

from hyper3.kernel import Hypergraph
from hyper3.multiway import MultiwayGraph, MultiwayState
from hyper3.quantum import (
    BUILTIN_BASES,
    CollapseTrigger,
    InterferencePattern,
    Interpretation,
    MeasurementBasis,
    QuantumCognitiveLayer,
    QuantumEntanglement,
    QuantumState,
)


@dataclass
class CausalInvariant:
    state_a_id: str
    state_b_id: str
    similarity: float
    merged_into: str


class CausalInvarianceEngine:
    def __init__(self, graph: Hypergraph, multiway: MultiwayGraph, *, threshold: float = 0.7) -> None:
        self._graph = graph
        self._multiway = multiway
        self._threshold = threshold
        self._invariants: list[CausalInvariant] = []
        self._consumed_states: set[str] = set()

    @property
    def invariants(self) -> list[CausalInvariant]:
        return list(self._invariants)

    def compute_state_similarity(self, state_a: MultiwayState, state_b: MultiwayState) -> float:
        nodes_a = state_a.active_node_ids
        nodes_b = state_b.active_node_ids
        if not nodes_a and not nodes_b:
            return 1.0
        if not nodes_a or not nodes_b:
            return 0.0
        overlap = len(nodes_a & nodes_b)
        total = len(nodes_a | nodes_b)
        jaccard = overlap / total

        produced_a = set(state_a.produced_edge_ids)
        produced_b = set(state_b.produced_edge_ids)
        edge_overlap = 0.0
        if not produced_a and not produced_b:
            edge_overlap = 1.0
        elif produced_a or produced_b:
            edge_overlap = len(produced_a & produced_b) / max(len(produced_a | produced_b), 1)

        return 0.7 * jaccard + 0.3 * edge_overlap

    def check_graph_isomorphism(self, state_a: MultiwayState, state_b: MultiwayState) -> float:
        g_a = nx.DiGraph()
        g_b = nx.DiGraph()
        for eid in state_a.produced_edge_ids:
            edge = self._graph.get_edge(eid)
            if edge:
                for src in edge.source_ids:
                    g_a.add_node(src, nid=src)
                    for tgt in edge.target_ids:
                        g_a.add_node(tgt, nid=tgt)
                        g_a.add_edge(src, tgt)
        for eid in state_b.produced_edge_ids:
            edge = self._graph.get_edge(eid)
            if edge:
                for src in edge.source_ids:
                    g_b.add_node(src, nid=src)
                    for tgt in edge.target_ids:
                        g_b.add_node(tgt, nid=tgt)
                        g_b.add_edge(src, tgt)
        if g_a.number_of_nodes() + g_b.number_of_nodes() > 50:
            return 0.0

        def _node_match(a: dict, b: dict) -> bool:
            na = self._graph.get_node(a.get("nid", ""))
            nb = self._graph.get_node(b.get("nid", ""))
            if na and nb:
                return na.matches(nb) > 0.5
            return False

        return 1.0 if nx.is_isomorphic(g_a, g_b, node_match=_node_match) else 0.0

    def find_invariants(self) -> list[tuple[str, str, float]]:
        leaves = self._multiway.get_leaves()
        if len(leaves) < 2:
            return []
        all_node_ids = sorted(set().union(*(s.active_node_ids for s in leaves)))
        if not all_node_ids:
            return []
        nid_idx = {nid: i for i, nid in enumerate(all_node_ids)}
        matrix = np.zeros((len(leaves), len(all_node_ids)))
        for i, leaf in enumerate(leaves):
            for nid in leaf.active_node_ids:
                matrix[i, nid_idx[nid]] = 1.0
        intersection = matrix @ matrix.T
        row_sums = matrix.sum(axis=1)
        union = row_sums[:, None] + row_sums[None, :] - intersection
        jaccard = np.where(union > 0, intersection / union, 0.0)

        all_edge_ids = sorted(set().union(*(set(s.produced_edge_ids) for s in leaves)))
        if all_edge_ids:
            eid_idx = {eid: i for i, eid in enumerate(all_edge_ids)}
            ematrix = np.zeros((len(leaves), len(all_edge_ids)))
            for i, leaf in enumerate(leaves):
                for eid in leaf.produced_edge_ids:
                    if eid in eid_idx:
                        ematrix[i, eid_idx[eid]] = 1.0
            e_intersection = ematrix @ ematrix.T
            e_sums = ematrix.sum(axis=1)
            e_union = e_sums[:, None] + e_sums[None, :] - e_intersection
            edge_sim = np.where(e_union > 0, e_intersection / e_union, 1.0)
        else:
            edge_sim = np.ones((len(leaves), len(leaves)))

        similarity = 0.7 * jaccard + 0.3 * edge_sim

        pairs: list[tuple[str, str, float]] = []
        for i in range(len(leaves)):
            if leaves[i].id in self._consumed_states:
                continue
            for j in range(i + 1, len(leaves)):
                if leaves[j].id in self._consumed_states:
                    continue
                if leaves[i].parent_id is not None and leaves[i].parent_id == leaves[j].parent_id:
                    continue
                sim = float(similarity[i, j])
                if sim >= self._threshold:
                    pairs.append((leaves[i].id, leaves[j].id, sim))
        pairs.sort(key=lambda p: p[2], reverse=True)
        return pairs

    def merge_invariant_states(self) -> list[CausalInvariant]:
        merged: list[CausalInvariant] = []
        consumed: set[str] = set()
        for state_a_id, state_b_id, similarity in self.find_invariants():
            if state_a_id in consumed or state_b_id in consumed:
                continue
            state_a = self._multiway.get_state(state_a_id)
            state_b = self._multiway.get_state(state_b_id)
            if not state_a or not state_b:
                continue
            merged_nodes = state_a.active_node_ids | state_b.active_node_ids
            merged_edges = list(set(state_a.produced_edge_ids + state_b.produced_edge_ids))
            rules_used: list[str] = []
            if state_a.rule_applied:
                rules_used.append(state_a.rule_applied)
            if state_b.rule_applied and state_b.rule_applied not in rules_used:
                rules_used.append(state_b.rule_applied)
            merged_state = MultiwayState(
                parent_id=state_a.parent_id,
                active_node_ids=merged_nodes,
                rule_applied=" + ".join(rules_used) if rules_used else None,
                depth=min(state_a.depth, state_b.depth),
                produced_node_ids=list(
                    set(state_a.produced_node_ids + state_b.produced_node_ids)
                ),
                produced_edge_ids=merged_edges,
                timestamp=time.time(),
            )
            self._multiway.add_state(merged_state)
            invariant = CausalInvariant(
                state_a_id=state_a_id,
                state_b_id=state_b_id,
                similarity=similarity,
                merged_into=merged_state.id,
            )
            self._invariants.append(invariant)
            self._consumed_states.add(state_a_id)
            self._consumed_states.add(state_b_id)
            consumed.add(state_a_id)
            consumed.add(state_b_id)
            merged.append(invariant)
        return merged

    def enforce(self) -> dict[str, Any]:
        before = self._multiway.state_count
        invariants = self.merge_invariant_states()
        after = self._multiway.state_count
        return {
            "invariants_found": len(invariants),
            "states_before": before,
            "states_after": after,
            "reduction": len(invariants),
        }
