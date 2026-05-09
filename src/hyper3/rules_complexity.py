from __future__ import annotations

from hyper3.kernel import Hypergraph
from hyper3.multi_perspective import MultiPerspectiveAnalyzer
from hyper3.rules import Rule, RuleMatch


class ComplexityComparisonRule(Rule):
    """Rule that runs multi-frame complexity analysis on each concept and stamps the results onto node data."""
    def __init__(self, perspective: MultiPerspectiveAnalyzer, frames: list[str] | None = None) -> None:
        """Initialize with a multi-perspective analyzer and optional frame names for complexity comparisons."""
        self._perspective = perspective
        self._frames = frames or ["classical", "quantum", "hypergraph", "probabilistic"]

    @property
    def name(self) -> str:
        """Return the rule name "complexity_comparison"."""
        return "complexity_comparison"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Match every active node that has not yet been analysed for complexity comparison."""
        matches: list[RuleMatch] = []
        for nid in active_nodes:
            node = graph.get_node(nid)
            if node is None:
                continue
            if node.data and "complexity_comparison" in node.data:
                continue
            matches.append(
                RuleMatch(
                    rule_name=self.name,
                    bindings={"concept": nid},
                    context={"label": node.label},
                )
            )
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Run multi-frame analysis on the matched concept and stamp the per-frame complexities and optimal frame onto the node data."""
        node_id = match.bindings["concept"]
        node = graph.get_node(node_id)
        if node is None:
            return [], []

        label = match.context.get("label", node.label)
        try:
            analysis = self._perspective.multi_frame_analysis(label)
        except Exception:
            return [], []

        complexities: dict[str, float] = {}
        for frame_name, result in analysis.items():
            complexities[frame_name] = result.complexity

        if not complexities:
            return [], []

        optimal = min(complexities, key=lambda k: complexities[k])
        if node.data is None:
            node.data = {}
        node.data["complexity_comparison"] = {"frames": complexities, "optimal": optimal}
        return [], []
