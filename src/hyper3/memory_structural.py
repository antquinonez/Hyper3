from __future__ import annotations

from typing import Any

from hyper3.abstraction import AbstractionMapping, AbstractionNavigator, AbstractionSummary, ExpandResult
from hyper3.belief_revision import Contradiction, ContradictionResolver, RevisionResult
from hyper3.community import CommunityDetector, CommunityResult
from hyper3.graph_diff import GraphDelta, GraphDiffer, GraphHistoryResult
from hyper3.memory_base import _MemoryBase
from hyper3.structural_match import (
    PatternEdge,
    PatternNode,
    PatternTemplate,
    StructuralMatchResult,
    StructuralPatternEngine,
)


class StructuralMixin(_MemoryBase):
    def match_structural_pattern(
        self,
        *,
        pattern_name: str = "custom",
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        max_matches: int = 100,
    ) -> StructuralMatchResult:
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)

        p_nodes = [
            PatternNode(
                role=n.get("role", ""),
                data_type=n.get("data_type"),
                label_pattern=n.get("label_pattern"),
                constraints=n.get("constraints", {}),
            )
            for n in (nodes or [])
        ]
        p_edges = [
            PatternEdge(
                source_role=e.get("source_role", ""),
                target_role=e.get("target_role", ""),
                label=e.get("label"),
                min_weight=e.get("min_weight", 0.0),
            )
            for e in (edges or [])
        ]

        template = PatternTemplate(
            name=pattern_name,
            nodes=p_nodes,
            edges=p_edges,
        )
        return self._structural_matcher.match_pattern(template, max_matches=max_matches)

    def match_chains(
        self,
        *,
        edge_label: str | None = None,
        min_length: int = 2,
        max_length: int = 5,
        max_chains: int = 50,
    ) -> list[list[str]]:
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)
        chains = self._structural_matcher.match_chain(
            edge_label=edge_label,
            min_length=min_length,
            max_length=max_length,
            max_chains=max_chains,
        )
        labeled_chains: list[list[str]] = []
        for chain in chains:
            labeled: list[str] = []
            for nid in chain:
                node = self._graph.get_node(nid)
                labeled.append(node.label if node else nid[:8])
            labeled_chains.append(labeled)
        return labeled_chains

    def match_diamonds(
        self,
        *,
        edge_label: str | None = None,
        max_matches: int = 50,
    ) -> list[dict[str, Any]]:
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)
        matches = self._structural_matcher.match_diamond(
            edge_label=edge_label,
            max_matches=max_matches,
        )
        results: list[dict[str, Any]] = []
        for m in matches:
            entry: dict[str, Any] = {"score": m.score}
            for role, nid in m.bindings.items():
                node = self._graph.get_node(nid)
                entry[role] = node.label if node else nid[:8]
            results.append(entry)
        return results

    def match_fan_out(
        self,
        *,
        edge_label: str | None = None,
        min_fan: int = 3,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)
        fans = self._structural_matcher.match_fan_out(
            edge_label=edge_label,
            min_fan=min_fan,
            max_results=max_results,
        )
        results: list[dict[str, Any]] = []
        for nid, target_ids in fans:
            node = self._graph.get_node(nid)
            tgt_labels: list[str] = []
            for tid in target_ids:
                tn = self._graph.get_node(tid)
                tgt_labels.append(tn.label if tn else tid[:8])
            results.append(
                {
                    "node": node.label if node else nid[:8],
                    "fan_out": len(target_ids),
                    "targets": tgt_labels,
                }
            )
        return results

    def detect_communities(
        self,
        *,
        method: str = "label_propagation",
        edge_label: str | None = None,
        seed: int = 42,
    ) -> CommunityResult:
        if self._community_detector is None:
            self._community_detector = CommunityDetector(self._graph)

        if method == "weighted_label_propagation":
            return self._community_detector.detect_weighted_label_propagation(
                seed=seed,
                edge_label=edge_label,
            )
        elif method == "connected_components":
            return self._community_detector.detect_connected_components()
        else:
            return self._community_detector.detect_label_propagation(
                seed=seed,
                edge_label=edge_label,
            )

    def detect_contradictions(self) -> list[Contradiction]:
        if self._belief_revision is None:
            self._belief_revision = ContradictionResolver(self._graph, self._provenance)
        return self._belief_revision.detect_contradictions()

    def revise_beliefs(self, *, strategy: str = "higher_confidence") -> RevisionResult:
        if self._belief_revision is None:
            self._belief_revision = ContradictionResolver(self._graph, self._provenance)
        result = self._belief_revision.revise(strategy=strategy)
        self._log.record(
            "revise_beliefs",
            contradictions=result.contradictions_detected,
            edges_removed=result.edges_removed_count,
        )
        return result

    def check_consistency(
        self,
        source: str,
        target: str,
    ) -> list[Contradiction]:
        if self._belief_revision is None:
            self._belief_revision = ContradictionResolver(self._graph, self._provenance)
        return self._belief_revision.check_consistency(source, target)

    def collapse_subgraph(
        self,
        node_labels: set[str],
        *,
        summary_label: str | None = None,
        summary_data: Any = None,
        layer: str = "summary",
    ) -> AbstractionSummary | None:
        from hyper3.kernel import AbstractionLayer

        if self._abstraction_nav is None:
            self._abstraction_nav = AbstractionNavigator(self._graph)
        layer_enum = AbstractionLayer(layer)
        return self._abstraction_nav.collapse_subgraph(
            node_labels,
            summary_label=summary_label,
            summary_data=summary_data,
            layer=layer_enum,
        )

    def expand_summary(self, summary_label: str) -> ExpandResult | None:
        if self._abstraction_nav is None:
            self._abstraction_nav = AbstractionNavigator(self._graph)
        return self._abstraction_nav.expand_node(summary_label)

    def list_summaries(self) -> list[AbstractionMapping]:
        if self._abstraction_nav is None:
            self._abstraction_nav = AbstractionNavigator(self._graph)
        return self._abstraction_nav.list_summaries()

    def capture_version(self) -> dict[str, int]:
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
            self._meta.set_differ(self._graph_differ)
        version = self._graph_differ.capture()
        return {
            "version_id": version.version_id,
            "node_count": version.node_count,
            "edge_count": version.edge_count,
        }

    def diff_from_version(self, version_id: int) -> GraphDelta | None:
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
        return self._graph_differ.diff_from_version(version_id)

    def diff_between_versions(self, v1: int, v2: int) -> GraphDelta | None:
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
        return self._graph_differ.diff_between_versions(v1, v2)

    def version_history(self) -> GraphHistoryResult:
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
        return self._graph_differ.history

    @property
    def structural_matcher(self) -> StructuralPatternEngine | None:
        return self._structural_matcher

    @property
    def belief_reviser(self) -> ContradictionResolver | None:
        return self._belief_revision

    @property
    def abstraction(self) -> AbstractionNavigator | None:
        return self._abstraction_nav

    @property
    def communities(self) -> CommunityDetector | None:
        return self._community_detector

    @property
    def differ(self) -> GraphDiffer | None:
        return self._graph_differ
