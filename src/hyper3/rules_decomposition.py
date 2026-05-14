"""Decomposition rule for discovering sub-concept groups within high-degree hub nodes."""

from __future__ import annotations

from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata
from hyper3.rules import Rule, RuleMatch


class DecompositionRule(Rule):
    """Identify high-degree hub nodes and decompose them into sub-concept groups.

    For each active node whose degree meets ``min_degree``, the rule groups
    its neighbors by the edge label connecting them to the hub.  When two or
    more groups each have at least ``min_group_size`` members, the rule
    produces a match.  Applying the match creates a summary node per group
    with ``decomposes_into`` edges from the hub and ``contains`` edges from
    each summary to its group members.
    """

    def __init__(
        self,
        *,
        min_degree: int = 5,
        min_group_size: int = 2,
        edge_label: str = "decomposes_into",
        max_hubs: int = 10,
    ) -> None:
        """Initialize the decomposition rule.

        Args:
            min_degree: Minimum incident-edge count for a node to be
                considered a decomposition candidate.
            min_group_size: Minimum neighbors in a sub-group to qualify
                as a decomposition component.
            edge_label: Label applied to created decomposition edges.
            max_hubs: Maximum number of hub candidates returned per
                ``find_matches`` call.
        """
        self._min_degree = min_degree
        self._min_group_size = min_group_size
        self._edge_label = edge_label
        self._max_hubs = max_hubs

    @property
    def name(self) -> str:
        """Return ``"decomposition"``."""
        return "decomposition"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find hub nodes whose neighbors partition into coherent sub-groups.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{hub}`` and context keys
            ``hub_label``, ``groups``, and ``group_count``.
        """
        matches: list[RuleMatch] = []
        for nid in active_nodes:
            if len(matches) >= self._max_hubs:
                break
            degree = len(graph.incident_edges(nid))
            if degree < self._min_degree:
                continue
            groups = self._group_neighbors(graph, nid)
            qualifying = {
                label: members
                for label, members in groups.items()
                if len(members) >= self._min_group_size
            }
            if len(qualifying) < 2:
                continue
            if self._decomposition_exists(graph, nid):
                continue
            hub_node = graph.get_node(nid)
            hub_label = hub_node.label if hub_node else nid
            matches.append(
                RuleMatch(
                    rule_name=self.name,
                    bindings={"hub": nid},
                    context={
                        "hub_label": hub_label,
                        "groups": {label: sorted(members) for label, members in qualifying.items()},
                        "group_count": len(qualifying),
                    },
                )
            )
        return matches

    def _group_neighbors(self, graph: Hypergraph, hub_id: str) -> dict[str, set[str]]:
        """Group neighbor IDs by the edge label connecting them to the hub."""
        groups: dict[str, set[str]] = {}
        for edge in graph.incident_edges(hub_id):
            if hub_id in edge.source_ids:
                neighbors = edge.target_ids
            elif hub_id in edge.target_ids:
                neighbors = edge.source_ids
            else:
                continue
            label = edge.label or ""
            for neighbor in neighbors:
                if neighbor == hub_id:
                    continue
                groups.setdefault(label, set()).add(neighbor)
        return groups

    def _decomposition_exists(self, graph: Hypergraph, hub_id: str) -> bool:
        """Check whether a ``decomposes_into`` edge already originates from the hub."""
        return any(edge.label == self._edge_label for edge in graph.outgoing_edges(hub_id))

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create summary nodes and decomposition edges for each group.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``hub`` binding and ``groups`` context.

        Returns:
            A tuple of ``(summary_node_ids, edge_ids)`` where *edge_ids*
            includes both ``decomposes_into`` and ``contains`` edges.
        """
        hub_id = match.bindings["hub"]
        hub_label = match.context["hub_label"]
        groups: dict[str, list[str]] = match.context["groups"]

        new_node_ids: list[str] = []
        new_edge_ids: list[str] = []

        for group_label, member_ids in groups.items():
            summary_node = Hypernode(
                label=f"{hub_label}_{group_label}",
                data={"type": "component", "parent": hub_label, "group_label": group_label},
                metadata=Metadata(custom={"rule": self.name, "inferred": True}),
            )
            graph.add_node(summary_node)
            new_node_ids.append(summary_node.id)

            decomp_edge = Hyperedge(
                source_ids=frozenset({hub_id}),
                target_ids=frozenset({summary_node.id}),
                label=self._edge_label,
                metadata=Metadata(
                    custom={
                        "rule": self.name,
                        "inferred": True,
                        "component_count": len(member_ids),
                        "confidence": 0.7,
                    }
                ),
            )
            graph.add_edge(decomp_edge)
            new_edge_ids.append(decomp_edge.id)

            contains_edge = Hyperedge(
                source_ids=frozenset({summary_node.id}),
                target_ids=frozenset(member_ids),
                label="contains",
                metadata=Metadata(custom={"rule": self.name, "inferred": True}),
            )
            graph.add_edge(contains_edge)
            new_edge_ids.append(contains_edge.id)

        return new_node_ids, new_edge_ids

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score a decomposition match by group count relative to an estimated maximum.

        Args:
            match: The match to score.
            graph: The hypergraph (unused but required by the ABC signature).

        Returns:
            ``group_count / estimated_max_groups`` clamped to ``[0, 1]``.
        """
        group_count = match.context.get("group_count", 1)
        estimated_max = 10
        return min(group_count / estimated_max, 1.0)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the decomposition rule configuration."""
        return {
            "rule_type": "DecompositionRule",
            "min_degree": self._min_degree,
            "min_group_size": self._min_group_size,
            "edge_label": self._edge_label,
            "max_hubs": self._max_hubs,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> DecompositionRule:
        """Reconstruct a ``DecompositionRule`` from serialized data."""
        return cls(
            min_degree=data.get("min_degree", 5),
            min_group_size=data.get("min_group_size", 2),
            edge_label=data.get("edge_label", "decomposes_into"),
            max_hubs=data.get("max_hubs", 10),
        )
