from __future__ import annotations

from itertools import combinations
from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Metadata
from hyper3.rules import Rule, RuleMatch


class AnalogicalReasoningRule(Rule):
    """Detect structural analogies between concept pairs via outgoing-label isomorphism.

    Two nodes A and C are considered structurally analogous when they share a
    sufficient number of outgoing edge labels (the *label overlap*) and, for
    each shared label, the targets reachable via that label also exhibit
    similar outgoing structure.  The resulting ``analogous_to`` edge enables
    cross-domain knowledge transfer in downstream reasoning.
    """

    def __init__(
        self,
        *,
        edge_label: str = "analogous_to",
        similarity_threshold: float = 0.6,
        min_outgoing_labels: int = 2,
        max_candidates: int = 50,
    ) -> None:
        """Initialize the analogical reasoning rule.

        Args:
            edge_label: Label applied to created analogy edges.
            similarity_threshold: Minimum combined similarity for a match.
            min_outgoing_labels: Nodes with fewer distinct outgoing edge labels
                are skipped to prevent trivial matches.
            max_candidates: Cap on total candidate pairs evaluated per call.
        """
        self._edge_label = edge_label
        self._similarity_threshold = similarity_threshold
        self._min_outgoing_labels = min_outgoing_labels
        self._max_candidates = max_candidates

    @property
    def name(self) -> str:
        """Return ``"analogy"``."""
        return "analogy"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find structurally analogous node pairs among active nodes.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate in matches.

        Returns:
            A list of ``RuleMatch`` objects with bindings ``{A, C}`` and
            context keys ``similarity``, ``shared_labels``, and
            ``label_overlap``.
        """
        candidate_info = self._build_candidate_info(graph, active_nodes)
        if len(candidate_info) < 2:
            return []
        label_to_nodes = self._build_label_index(candidate_info)
        matches: list[RuleMatch] = []
        seen_pairs: set[frozenset[str]] = set()
        evaluated = 0
        for node_ids in label_to_nodes.values():
            sorted_ids = sorted(node_ids)
            for a_id, c_id in combinations(sorted_ids, 2):
                pair = frozenset({a_id, c_id})
                if pair in seen_pairs:
                    continue
                if evaluated >= self._max_candidates:
                    return matches
                seen_pairs.add(pair)
                evaluated += 1
                match = self._evaluate_pair(graph, a_id, c_id, candidate_info)
                if match is not None:
                    matches.append(match)
        return matches

    def _build_candidate_info(self, graph: Hypergraph, active_nodes: frozenset[str]) -> dict[str, set[str]]:
        """Build mapping from node ID to its set of distinct outgoing edge labels."""
        info: dict[str, set[str]] = {}
        for nid in active_nodes:
            labels: set[str] = set()
            for edge in graph.incident_edges(nid):
                if nid in edge.source_ids and edge.label:
                    labels.add(edge.label)
            if len(labels) >= self._min_outgoing_labels:
                info[nid] = labels
        return info

    def _build_label_index(self, candidate_info: dict[str, set[str]]) -> dict[str, set[str]]:
        """Build inverted index from each outgoing label to nodes that carry it."""
        index: dict[str, set[str]] = {}
        for nid, labels in candidate_info.items():
            for label in labels:
                index.setdefault(label, set()).add(nid)
        return index

    def _evaluate_pair(self, graph: Hypergraph, a_id: str, c_id: str, candidate_info: dict[str, set[str]]) -> RuleMatch | None:
        """Evaluate whether two nodes are structurally analogous."""
        if a_id == c_id:
            return None
        if self._analogy_edge_exists(graph, a_id, c_id):
            return None
        labels_a = candidate_info[a_id]
        labels_c = candidate_info[c_id]
        shared = labels_a & labels_c
        if not shared:
            return None
        union = labels_a | labels_c
        label_overlap = len(shared) / len(union)
        target_sim = self._compute_target_similarity(graph, a_id, c_id, shared)
        similarity = label_overlap * 0.5 + target_sim * 0.5
        if similarity < self._similarity_threshold:
            return None
        return RuleMatch(
            rule_name=self.name,
            bindings={"A": a_id, "C": c_id},
            context={
                "similarity": similarity,
                "shared_labels": sorted(shared),
                "label_overlap": label_overlap,
            },
        )

    def _compute_target_similarity(self, graph: Hypergraph, a_id: str, c_id: str, shared_labels: set[str]) -> float:
        """Compute average outgoing-label overlap between targets of A and targets of C."""
        similarities: list[float] = []
        for label in shared_labels:
            targets_a = self._get_targets_by_label(graph, a_id, label)
            targets_c = self._get_targets_by_label(graph, c_id, label)
            pair_sims: list[float] = []
            for b_id in targets_a:
                out_b = self._outgoing_label_set(graph, b_id)
                for d_id in targets_c:
                    out_d = self._outgoing_label_set(graph, d_id)
                    if not out_b and not out_d:
                        pair_sims.append(1.0)
                    elif not out_b or not out_d:
                        pair_sims.append(0.0)
                    else:
                        overlap = len(out_b & out_d) / len(out_b | out_d)
                        pair_sims.append(overlap)
            if pair_sims:
                similarities.append(sum(pair_sims) / len(pair_sims))
        return sum(similarities) / len(similarities) if similarities else 0.0

    def _get_targets_by_label(self, graph: Hypergraph, node_id: str, label: str) -> set[str]:
        """Return all target node IDs reachable from node_id via edges with the given label."""
        targets: set[str] = set()
        for edge in graph.incident_edges(node_id):
            if node_id in edge.source_ids and edge.label == label:
                targets.update(edge.target_ids)
        return targets

    def _outgoing_label_set(self, graph: Hypergraph, node_id: str) -> set[str]:
        """Return the set of distinct outgoing edge labels for a node."""
        labels: set[str] = set()
        for edge in graph.incident_edges(node_id):
            if node_id in edge.source_ids and edge.label:
                labels.add(edge.label)
        return labels

    def _analogy_edge_exists(self, graph: Hypergraph, a_id: str, c_id: str) -> bool:
        """Check whether an analogy edge already exists between two nodes in either direction."""
        for edge in graph.incident_edges(a_id):
            if edge.label != self._edge_label:
                continue
            if a_id in edge.source_ids and c_id in edge.target_ids:
                return True
            if c_id in edge.source_ids and a_id in edge.target_ids:
                return True
        return False

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create a directed analogy edge from A to C.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``A`` and ``C`` bindings.

        Returns:
            ``( [], [new_edge_id] )``.
        """
        a_id = match.bindings["A"]
        c_id = match.bindings["C"]
        edge = Hyperedge(
            source_ids=frozenset({a_id}),
            target_ids=frozenset({c_id}),
            label=self._edge_label,
            metadata=Metadata(
                custom={
                    "rule": self.name,
                    "inferred": True,
                    "similarity": match.context["similarity"],
                    "shared_labels": match.context["shared_labels"],
                }
            ),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score an analogy match by the similarity stored in context.

        Args:
            match: The match to score.
            graph: The hypergraph (unused, present for interface consistency).

        Returns:
            The similarity value from the match context.
        """
        return match.context.get("similarity", 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the analogical reasoning rule configuration.

        Returns:
            A JSON-compatible dictionary with all constructor parameters.
        """
        return {
            "rule_type": "AnalogicalReasoningRule",
            "edge_label": self._edge_label,
            "similarity_threshold": self._similarity_threshold,
            "min_outgoing_labels": self._min_outgoing_labels,
            "max_candidates": self._max_candidates,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AnalogicalReasoningRule:
        """Reconstruct an ``AnalogicalReasoningRule`` from serialized data.

        Args:
            data: Dictionary produced by ``to_dict``.

        Returns:
            The reconstructed rule instance.
        """
        return cls(
            edge_label=data.get("edge_label", "analogous_to"),
            similarity_threshold=data.get("similarity_threshold", 0.6),
            min_outgoing_labels=data.get("min_outgoing_labels", 2),
            max_candidates=data.get("max_candidates", 50),
        )
