"""Automatic abstraction engine for identifying and executing graph collapse/expansion."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from hyper3.abstraction import AbstractionNavigator
from hyper3.community import CommunityDetector
from hyper3.kernel import (
    AbstractionLayer,
    Hypergraph,
)
from hyper3.results import _SimpleResultBase


@dataclass
class AbstractionCandidate(_SimpleResultBase):
    """A node recommended for promotion or demotion between abstraction layers.

    Attributes:
        node_id: Internal ID of the candidate node.
        node_label: Human-readable label of the candidate node.
        current_layer: The node's current abstraction layer.
        recommended_layer: The proposed target abstraction layer.
        reason: Categorization of why the transition is recommended.
        score: Confidence score for the recommendation in [0, 1].
        group_members: Labels of other nodes in the same promotion group.
    """
    node_id: str = ""
    node_label: str = ""
    current_layer: str = "intermediate"
    recommended_layer: str = "intermediate"
    reason: str = ""
    score: float = 0.0
    group_members: list[str] = field(default_factory=list)


@dataclass
class AbstractionAction(_SimpleResultBase):
    """Records a single promotion or demotion action that was executed.

    Attributes:
        action: Either ``"promote"`` or ``"demote"``.
        node_label: Label of the node that was acted upon.
        summary_label: Label of the summary node created or removed.
        layer: Target abstraction layer after the action.
        members_collapsed: Number of nodes collapsed into the summary.
        members_expanded: Number of nodes restored from the summary.
    """
    action: str = ""
    node_label: str = ""
    summary_label: str = ""
    layer: str = "summary"
    members_collapsed: int = 0
    members_expanded: int = 0


@dataclass
class AbstractionResult(_SimpleResultBase):
    """Summary of an assessment-and-execution cycle.

    Attributes:
        assessed_nodes: Total number of nodes in the graph at assessment time.
        promotions: Number of promotion actions executed.
        demotions: Number of demotion actions executed.
        actions: Ordered list of actions that were performed.
        candidates: All candidates identified during assessment.
    """
    assessed_nodes: int = 0
    promotions: int = 0
    demotions: int = 0
    actions: list[AbstractionAction] = field(default_factory=list)
    candidates: list[AbstractionCandidate] = field(default_factory=list)


class AutoAbstractionEngine:
    """Monitor node access patterns and structural roles to recommend or
    auto-execute abstraction layer transitions.

    Integrates with :class:`AbstractionNavigator` for collapse/expand
    operations and :class:`CommunityDetector` for group discovery.

    Args:
        graph: The hypergraph being monitored.
        promote_threshold: Score threshold above which a group is recommended
            for promotion (default 0.6, range [0, 1]).
        demote_threshold: Access count below which a summary node is
            recommended for demotion (default 2).
        min_cluster_size: Minimum number of members in a promotion candidate
            group (default 3).
        max_cluster_density: Internal edge density ceiling for candidate
            groups (default 0.7).
        auto_execute: Whether to automatically execute promotions and
            demotions during ``assess_and_execute()``. Default ``False``.
    """

    def __init__(
        self,
        graph: Hypergraph,
        *,
        promote_threshold: float = 0.6,
        demote_threshold: float = 2.0,
        min_cluster_size: int = 3,
        max_cluster_density: float = 0.7,
        auto_execute: bool = False,
    ) -> None:
        """Initialize the auto-abstraction engine.

        Args:
            graph: The hypergraph to monitor and operate on.
            promote_threshold: Minimum composite score for a promotion
                recommendation. Defaults to 0.6.
            demote_threshold: Access count below which a summary node is
                a demotion candidate. Defaults to 2.0.
            min_cluster_size: Minimum members in a promotion candidate group.
                Defaults to 3.
            max_cluster_density: Internal edge density ceiling for candidate
                groups. Defaults to 0.7.
            auto_execute: Whether ``assess_and_execute()`` automatically
                applies transitions. Defaults to False.
        """
        self._graph = graph
        self._promote_threshold = promote_threshold
        self._demote_threshold = demote_threshold
        self._min_cluster_size = min_cluster_size
        self._max_cluster_density = max_cluster_density
        self._auto_execute = auto_execute
        self._navigator = AbstractionNavigator(graph)
        self._detector = CommunityDetector(graph)
        self._assessment_history: list[dict[str, list[str]]] = []

    def assess(self) -> list[AbstractionCandidate]:
        """Identify promotion and demotion candidates based on current
        graph structure and access patterns.

        Returns:
            List of AbstractionCandidate describing recommended transitions.
        """
        candidates: list[AbstractionCandidate] = []
        g = self._graph

        if g.node_count == 0:
            return candidates

        candidates.extend(self._find_promotion_candidates())
        candidates.extend(self._find_demotion_candidates())

        self._record_assessment(candidates)
        return candidates

    def execute(self, candidates: list[AbstractionCandidate]) -> AbstractionResult:
        """Execute promotion and demotion actions for the given candidates.

        Args:
            candidates: Candidates returned by :meth:`assess`.

        Returns:
            AbstractionResult summarising actions taken.
        """
        actions: list[AbstractionAction] = []
        promotions = 0
        demotions = 0

        promotion_groups = self._group_promotion_candidates(candidates)
        for group_key in promotion_groups:
            labels = set(group_key.split("|"))
            if len(labels) < self._min_cluster_size:
                continue
            summary_label = "+".join(sorted(labels)[:3])
            result = self._navigator.collapse_subgraph(
                labels, summary_label=summary_label,
            )
            if result is not None:
                promotions += 1
                actions.append(
                    AbstractionAction(
                        action="promote",
                        node_label=summary_label,
                        summary_label=summary_label,
                        layer="summary",
                        members_collapsed=len(labels),
                    )
                )

        for cand in candidates:
            if cand.recommended_layer != "detail":
                continue
            expand_result = self._navigator.expand_node(cand.node_label)
            if expand_result is not None and expand_result.summary_removed:
                demotions += 1
                actions.append(
                    AbstractionAction(
                        action="demote",
                        node_label=cand.node_label,
                        summary_label=cand.node_label,
                        layer="detail",
                        members_expanded=len(expand_result.expanded_nodes),
                    )
                )

        return AbstractionResult(
            assessed_nodes=self._graph.node_count,
            promotions=promotions,
            demotions=demotions,
            actions=actions,
            candidates=candidates,
        )

    def assess_and_execute(self) -> AbstractionResult:
        """Run assessment and execute all recommended transitions.

        Returns:
            AbstractionResult summarising actions taken.
        """
        candidates = self.assess()
        return self.execute(candidates)

    def get_candidates_for(self, concept: str) -> list[AbstractionCandidate]:
        """Return candidates that reference a specific concept label.

        Args:
            concept: The node label to filter by.

        Returns:
            Matching candidates from the most recent assessment.
        """
        if not self._assessment_history:
            return []
        node = self._graph.get_node_by_label(concept)
        if not node:
            return []
        candidates = self.assess()
        return [cand for cand in candidates if cand.node_label == concept or concept in cand.group_members]

    def to_dict(self) -> dict[str, Any]:
        """Serialize engine configuration to a plain dict."""
        return {
            "promote_threshold": self._promote_threshold,
            "demote_threshold": self._demote_threshold,
            "min_cluster_size": self._min_cluster_size,
            "max_cluster_density": self._max_cluster_density,
            "auto_execute": self._auto_execute,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> AutoAbstractionEngine:
        """Restore an engine from a serialized config dict."""
        return cls(
            graph,
            promote_threshold=float(data.get("promote_threshold", 0.6)),
            demote_threshold=float(data.get("demote_threshold", 2.0)),
            min_cluster_size=int(data.get("min_cluster_size", 3)),
            max_cluster_density=float(data.get("max_cluster_density", 0.7)),
            auto_execute=bool(data.get("auto_execute", False)),
        )

    def _find_promotion_candidates(self) -> list[AbstractionCandidate]:
        """Identify node groups suitable for promotion to the summary layer.

        Uses community detection to find clusters, then scores them on
        internal density, access density, and label homogeneity. Also
        delegates to :meth:`_find_hub_promotion_candidates` for hub-based
        discovery.

        Returns:
            Candidates whose composite score meets the promote threshold.
        """
        g = self._graph
        candidates: list[AbstractionCandidate] = []

        if g.node_count < self._min_cluster_size:
            return candidates

        communities = self._detector.detect_label_propagation(seed=42)
        for community in communities.communities:
            if community.size < self._min_cluster_size:
                continue

            member_labels = community.member_labels
            layers = self._get_member_layers(member_labels)
            if any(l == "summary" for l in layers.values()):
                continue

            density = self._compute_internal_density(member_labels)
            if density < 0.3:
                continue

            access_density = self._compute_access_density(member_labels)
            label_homo = self._compute_label_homogeneity(member_labels)
            score = (access_density * 0.4) + (density * 0.3) + (label_homo * 0.3)

            if score >= self._promote_threshold:
                representative = member_labels[0] if member_labels else ""
                candidates.append(
                    AbstractionCandidate(
                        node_id=self._label_to_id(representative) or "",
                        node_label=representative,
                        current_layer=layers.get(representative, "intermediate"),
                        recommended_layer="summary",
                        reason="high_density_high_access",
                        score=score,
                        group_members=member_labels,
                    )
                )

        hub_candidates = self._find_hub_promotion_candidates()
        candidates.extend(hub_candidates)

        return candidates

    def _find_hub_promotion_candidates(self) -> list[AbstractionCandidate]:
        """Find high-degree nodes whose neighborhoods form promotion groups.

        A node whose degree centrality exceeds twice the average is treated
        as a hub. Its neighborhood is scored the same way as community-based
        candidates.

        Returns:
            Candidates derived from hub neighborhoods.
        """
        g = self._graph
        candidates: list[AbstractionCandidate] = []
        if g.node_count < self._min_cluster_size:
            return candidates

        centrality = g.degree_centrality()
        if not centrality:
            return candidates

        avg_degree = sum(centrality.values()) / len(centrality)
        hub_threshold = 2.0 * avg_degree

        for node in g.nodes:
            node_centrality = centrality.get(node.id, 0.0)
            if node_centrality <= hub_threshold:
                continue

            layer = node.metadata.abstraction_layer
            if layer == AbstractionLayer.SUMMARY:
                continue

            neighbors = g.neighbors(node.label)
            if len(neighbors) < self._min_cluster_size - 1:
                continue

            group = [node.label] + [n for n in neighbors if n != node.label]
            if len(group) < self._min_cluster_size:
                continue

            access_density = self._compute_access_density(group)
            density = self._compute_internal_density(group)
            label_homo = self._compute_label_homogeneity(group)
            score = (access_density * 0.4) + (density * 0.3) + (label_homo * 0.3)

            if score >= self._promote_threshold:
                candidates.append(
                    AbstractionCandidate(
                        node_id=node.id,
                        node_label=node.label,
                        current_layer=layer.value,
                        recommended_layer="summary",
                        reason="hub_neighborhood",
                        score=score,
                        group_members=group,
                    )
                )

        return candidates

    def _find_demotion_candidates(self) -> list[AbstractionCandidate]:
        """Identify summary-layer nodes with low access for demotion.

        A summary node is a demotion candidate when its access count is
        below ``demote_threshold`` and its relative access (compared to the
        busiest summary node) exceeds 0.8, indicating it is rarely used
        relative to peers.

        Returns:
            Candidates recommended for demotion to the detail layer.
        """
        candidates: list[AbstractionCandidate] = []
        summary_nodes = self._navigator.nodes_at_layer(AbstractionLayer.SUMMARY)

        if not summary_nodes:
            return candidates

        max_access = max((n.access_count for n in summary_nodes), default=1) or 1

        for node in summary_nodes:
            mapping = self._navigator.get_summary_for(node.label)
            if mapping is None:
                continue

            if node.access_count >= self._demote_threshold:
                continue

            relative_access = 1.0 - (node.access_count / max_access)
            if relative_access > 0.8:
                candidates.append(
                    AbstractionCandidate(
                        node_id=node.id,
                        node_label=node.label,
                        current_layer="summary",
                        recommended_layer="detail",
                        reason="low_access_summary",
                        score=relative_access,
                    )
                )

        return candidates

    def _compute_internal_density(self, labels: list[str]) -> float:
        """Compute the ratio of internal edges to the maximum possible.

        An edge is internal when both its source and target node sets are
        fully contained within the group identified by *labels*.

        Args:
            labels: Node labels defining the group.

        Returns:
            Density value in [0, 1]. Returns 0.0 for groups smaller than 2.
        """
        if len(labels) < 2:
            return 0.0

        node_ids = set()
        for lbl in labels:
            node = self._graph.get_node_by_label(lbl)
            if node:
                node_ids.add(node.id)

        if len(node_ids) < 2:
            return 0.0

        internal_edges = 0
        for edge in self._graph.edges:
            if edge.source_ids <= node_ids and edge.target_ids <= node_ids:
                internal_edges += 1

        n = len(node_ids)
        max_edges = n * (n - 1)
        return internal_edges / max_edges if max_edges > 0 else 0.0

    def _compute_access_density(self, labels: list[str]) -> float:
        """Compute the average-to-max ratio of access counts for a group.

        Args:
            labels: Node labels defining the group.

        Returns:
            Ratio in [0, 1]. Returns 0.0 when the group is empty or all
            access counts are zero.
        """
        if not labels:
            return 0.0

        access_counts: list[int] = []
        for lbl in labels:
            node = self._graph.get_node_by_label(lbl)
            if node:
                access_counts.append(node.access_count)
            else:
                access_counts.append(0)

        total = sum(access_counts)
        max_count = max(access_counts) if access_counts else 0
        if max_count == 0:
            return 0.0

        avg = total / len(access_counts)
        return min(avg / max_count, 1.0)

    def _compute_label_homogeneity(self, labels: list[str]) -> float:
        """Compute Jaccard similarity of outgoing edge labels across a group.

        Args:
            labels: Node labels defining the group.

        Returns:
            ``|intersection| / |union|`` of outgoing edge label sets.
            Returns 1.0 for groups smaller than 2 or when all label sets
            are empty.
        """
        if len(labels) < 2:
            return 1.0

        all_labels: list[set[str]] = []
        for lbl in labels:
            node = self._graph.get_node_by_label(lbl)
            if not node:
                all_labels.append(set())
                continue
            outgoing = self._graph.outgoing_edges(node.id)
            edge_labels = {e.label for e in outgoing}
            all_labels.append(edge_labels)

        if not all_labels:
            return 0.0

        non_empty = [s for s in all_labels if s]
        if not non_empty:
            return 1.0

        intersection = set.intersection(*non_empty)
        union = set.union(*non_empty)
        return len(intersection) / len(union) if union else 0.0

    def _get_member_layers(self, labels: list[str]) -> dict[str, str]:
        """Resolve the abstraction layer for each label in the group.

        Args:
            labels: Node labels to look up.

        Returns:
            Dict mapping each resolved label to its abstraction layer value.
            Labels that do not resolve to a node are omitted.
        """
        result: dict[str, str] = {}
        for lbl in labels:
            node = self._graph.get_node_by_label(lbl)
            if node:
                result[lbl] = node.metadata.abstraction_layer.value
        return result

    def _label_to_id(self, label: str) -> str | None:
        """Resolve a concept label to its internal node ID.

        Args:
            label: The concept label to resolve.

        Returns:
            The node ID, or ``None`` if the label does not exist.
        """
        node = self._graph.get_node_by_label(label)
        return node.id if node else None

    def _group_promotion_candidates(
        self, candidates: list[AbstractionCandidate],
    ) -> dict[str, list[AbstractionCandidate]]:
        """Group promotion candidates by their member set.

        Candidates targeting the summary layer are keyed by the sorted,
        pipe-delimited membership labels so that overlapping candidates
        for the same group are co-located.

        Args:
            candidates: All candidates from an assessment run.

        Returns:
            Dict mapping group key to the candidates that share that group.
        """
        groups: dict[str, list[AbstractionCandidate]] = defaultdict(list)
        for cand in candidates:
            if cand.recommended_layer != "summary":
                continue
            key = "|".join(sorted(cand.group_members))
            groups[key].append(cand)
        return groups

    def _record_assessment(self, candidates: list[AbstractionCandidate]) -> None:
        """Append the current assessment to the rolling history.

        Keeps up to 20 historical entries. Only promotion candidates
        (those targeting the summary layer) are recorded.

        Args:
            candidates: The candidates produced by the current assessment.
        """
        promoted_labels: list[str] = []
        for cand in candidates:
            if cand.recommended_layer == "summary":
                promoted_labels.extend(cand.group_members)
        self._assessment_history.append({"promoted": promoted_labels})
        if len(self._assessment_history) > 20:
            self._assessment_history = self._assessment_history[-20:]
