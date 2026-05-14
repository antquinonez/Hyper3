from __future__ import annotations

from collections import defaultdict
from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata
from hyper3.rules import Rule, RuleMatch


class InductiveGeneralizationRule(Rule):
    """Detect repeated edge patterns and create abstract category nodes.

    When three or more active nodes share an edge with the same label
    pointing to the same target (convergence) or originating from the
    same source (divergence), this rule creates a category node with a
    ``"generalizes"`` hyperedge linking it to all pattern members, plus
    a representative edge preserving the shared relational pattern.

    This is complementary to :class:`GeneralizationRule`, which creates
    abstractions from data similarity rather than relational structure.
    """

    def __init__(
        self,
        *,
        min_group_size: int = 3,
        edge_label: str | None = None,
        label_prefix: str = "category_",
        max_groups: int = 10,
    ) -> None:
        """Initialize the inductive generalization rule.

        Args:
            min_group_size: Minimum number of nodes in a convergence or
                divergence group to trigger generalization.  Default 3
                prevents trivial two-node groups that
                :class:`GeneralizationRule` already handles.
            edge_label: If set, only consider edges with this label.
                ``None`` considers all labels.
            label_prefix: Prefix for generated category node labels.
            max_groups: Maximum number of groups returned per
                ``find_matches`` call.
        """
        self._min_group_size = min_group_size
        self._edge_label = edge_label
        self._label_prefix = label_prefix
        self._max_groups = max_groups

    @property
    def name(self) -> str:
        """Return ``"inductive_generalization"``."""
        return "inductive_generalization"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find convergence and divergence patterns among active nodes.

        A **convergence** pattern occurs when ``min_group_size`` or more
        active nodes have edges with the same label pointing to the same
        target.  A **divergence** pattern occurs when the same number of
        active nodes are targets of edges from the same source with the
        same label.

        Groups already covered by an existing ``"generalizes"`` edge are
        skipped.  Results are ranked by group size (largest first) and
        capped at ``max_groups``.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate in matches.

        Returns:
            A list of :class:`RuleMatch` objects, each with bindings
            ``pattern_type``, ``members``, ``shared_id``, and
            ``edge_label``, plus context with ``group_size``,
            ``pattern_type``, ``edge_label``, and ``shared_label``.
        """
        convergence = self._find_convergence_groups(graph, active_nodes)
        divergence = self._find_divergence_groups(graph, active_nodes)
        all_groups = convergence + divergence
        all_groups.sort(key=lambda m: m.context.get("group_size", 0), reverse=True)
        return all_groups[: self._max_groups]

    def _find_convergence_groups(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find groups of active nodes converging on the same target via the same label."""
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for edge in graph.edges:
            if self._edge_label and edge.label != self._edge_label:
                continue
            if not edge.label:
                continue
            for src in edge.source_ids:
                if src not in active_nodes:
                    continue
                for tgt in edge.target_ids:
                    groups[(edge.label, tgt)].append(src)

        matches: list[RuleMatch] = []
        for (label, tgt_id), sources in groups.items():
            unique_sources = list(dict.fromkeys(sources))
            if len(unique_sources) < self._min_group_size:
                continue
            if self._group_already_generalized(graph, unique_sources):
                continue
            tgt_node = graph.get_node(tgt_id)
            shared_label = tgt_node.label if tgt_node else tgt_id
            matches.append(
                RuleMatch(
                    rule_name=self.name,
                    bindings={
                        "pattern_type": "convergence",
                        "members": ",".join(sorted(unique_sources)),
                        "shared_id": tgt_id,
                        "edge_label": label,
                    },
                    context={
                        "group_size": len(unique_sources),
                        "pattern_type": "convergence",
                        "edge_label": label,
                        "shared_label": shared_label,
                    },
                )
            )
        return matches

    def _find_divergence_groups(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find groups of active nodes diverging from the same source via the same label."""
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for edge in graph.edges:
            if self._edge_label and edge.label != self._edge_label:
                continue
            if not edge.label:
                continue
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    if tgt not in active_nodes:
                        continue
                    groups[(edge.label, src)].append(tgt)

        matches: list[RuleMatch] = []
        for (label, src_id), targets in groups.items():
            unique_targets = list(dict.fromkeys(targets))
            if len(unique_targets) < self._min_group_size:
                continue
            if self._group_already_generalized(graph, unique_targets):
                continue
            src_node = graph.get_node(src_id)
            shared_label = src_node.label if src_node else src_id
            matches.append(
                RuleMatch(
                    rule_name=self.name,
                    bindings={
                        "pattern_type": "divergence",
                        "members": ",".join(sorted(unique_targets)),
                        "shared_id": src_id,
                        "edge_label": label,
                    },
                    context={
                        "group_size": len(unique_targets),
                        "pattern_type": "divergence",
                        "edge_label": label,
                        "shared_label": shared_label,
                    },
                )
            )
        return matches

    def _group_already_generalized(self, graph: Hypergraph, member_ids: list[str]) -> bool:
        """Check whether an existing ``"generalizes"`` edge covers all members."""
        member_set = set(member_ids)
        for edge in graph.edges:
            if edge.label != "generalizes":
                continue
            if member_set.issubset(edge.target_ids):
                return True
        return False

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create a category node, a generalizes edge, and a representative edge.

        The category node receives label
        ``{label_prefix}{edge_label}_{shared_label}`` and data
        ``{"type": "category", "pattern": pattern_type, "edge_label": edge_label}``.

        For convergence patterns a representative edge is created from
        the category node to the shared target.  For divergence patterns
        a representative edge is created from the shared source to the
        category node.

        Args:
            graph: The hypergraph to modify.
            match: A match produced by :meth:`find_matches`.

        Returns:
            A tuple of ``([category_node_id], [generalizes_edge_id, representative_edge_id])``.
        """
        pattern_type = match.bindings["pattern_type"]
        member_ids = match.bindings["members"].split(",")
        shared_id = match.bindings["shared_id"]
        edge_label = match.bindings["edge_label"]
        shared_node = graph.get_node(shared_id)
        shared_label = shared_node.label if shared_node else shared_id

        category_node = Hypernode(
            label=f"{self._label_prefix}{edge_label}_{shared_label}",
            data={"type": "category", "pattern": pattern_type, "edge_label": edge_label},
            metadata=Metadata(custom={"rule": self.name, "inferred": True}),
        )
        graph.add_node(category_node)

        gen_edge = Hyperedge(
            source_ids=frozenset({category_node.id}),
            target_ids=frozenset(member_ids),
            label="generalizes",
            metadata=Metadata(
                custom={
                    "rule": self.name,
                    "inferred": True,
                    "confidence": 0.7,
                    "pattern_type": pattern_type,
                },
            ),
        )
        graph.add_edge(gen_edge)

        if pattern_type == "convergence":
            rep_edge = Hyperedge(
                source_ids=frozenset({category_node.id}),
                target_ids=frozenset({shared_id}),
                label=edge_label,
                metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.7}),
            )
        else:
            rep_edge = Hyperedge(
                source_ids=frozenset({shared_id}),
                target_ids=frozenset({category_node.id}),
                label=edge_label,
                metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.7}),
            )
        graph.add_edge(rep_edge)

        return [category_node.id], [gen_edge.id, rep_edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Return a normalized score based on group size.

        The score is ``group_size / 100``, clamped to ``[0.0, 1.0]``.
        Larger groups receive higher confidence.

        Args:
            match: The match to score.
            graph: The hypergraph (unused but required by the ABC).

        Returns:
            A float in ``[0.0, 1.0]``.
        """
        group_size = match.context.get("group_size", 0)
        return min(group_size / 100.0, 1.0)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the inductive generalization rule configuration."""
        return {
            "rule_type": "InductiveGeneralizationRule",
            "min_group_size": self._min_group_size,
            "edge_label": self._edge_label,
            "label_prefix": self._label_prefix,
            "max_groups": self._max_groups,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> InductiveGeneralizationRule:
        """Reconstruct an :class:`InductiveGeneralizationRule` from serialized data."""
        return cls(
            min_group_size=data.get("min_group_size", 3),
            edge_label=data.get("edge_label"),
            label_prefix=data.get("label_prefix", "category_"),
            max_groups=data.get("max_groups", 10),
        )
