from __future__ import annotations

from itertools import combinations

from hyper3.kernel import Hyperedge, Hypergraph, Metadata
from hyper3.multiway import MultiwayGraph
from hyper3.rules import Rule, RuleMatch


class SimultaneityRule(Rule):
    """Rule that creates simultaneous edges between nodes that co-occur in sibling multiway states."""
    def __init__(self, multiway: MultiwayGraph) -> None:
        """Initialize with a reference to the multiway graph for simultaneity detection."""
        self._multiway = multiway

    @property
    def name(self) -> str:
        """Return the rule name "simultaneity"."""
        return "simultaneity"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find pairs of nodes that appear together in sibling multiway leaves (share a parent state) but lack a simultaneous edge."""
        leaves = self._multiway.get_leaves()
        by_parent: dict[str, list] = {}
        for leaf in leaves:
            if leaf.parent_id is not None:
                by_parent.setdefault(leaf.parent_id, []).append(leaf)

        matches: list[RuleMatch] = []
        seen: set[frozenset[str]] = set()
        for siblings in by_parent.values():
            if len(siblings) < 2:
                continue
            all_node_ids: set[str] = set()
            for s in siblings:
                all_node_ids |= s.active_node_ids & active_nodes
            for a, b in combinations(sorted(all_node_ids), 2):
                pair = frozenset({a, b})
                if pair in seen:
                    continue
                seen.add(pair)
                if self._edge_exists(graph, a, b):
                    continue
                matches.append(
                    RuleMatch(
                        rule_name=self.name,
                        bindings={"source": a, "target": b},
                    )
                )
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create a "simultaneous" labeled edge between the matched pair of nodes."""
        s = match.bindings["source"]
        t = match.bindings["target"]
        edge = Hyperedge(
            source_ids=frozenset({s}),
            target_ids=frozenset({t}),
            label="simultaneous",
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.9}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def _edge_exists(self, graph: Hypergraph, a: str, b: str) -> bool:
        """Check whether a simultaneous-labeled edge already exists between two nodes."""
        for e in graph.incident_edges(a):
            if e.label == "simultaneous" and (
                (a in e.source_ids and b in e.target_ids) or (b in e.source_ids and a in e.target_ids)
            ):
                return True
        return False
