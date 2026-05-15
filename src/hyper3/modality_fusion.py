"""ModalityFusion: multi-modality knowledge fusion."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel_types import Modality
from hyper3.results import _SimpleResultBase


@dataclass
class ModalityProfile(_SimpleResultBase):
    """Per-concept modality coverage: scores, coverage counts, fused score, dominant modality, and gaps."""

    node_id: str = ""
    per_modality_score: dict[str, float] = field(default_factory=dict)
    modality_coverage: dict[str, int] = field(default_factory=dict)
    fused_score: float = 0.0
    dominant_modality: str = ""
    gap_modalities: list[str] = field(default_factory=list)


@dataclass
class ModalityGap(_SimpleResultBase):
    """A modality gap for a concept: which modalities are rich vs. missing, and the coverage ratio."""

    concept: str = ""
    rich_modalities: list[str] = field(default_factory=list)
    gap_modalities: list[str] = field(default_factory=list)
    coverage_ratio: float = 0.0


@dataclass
class FusionResult(_SimpleResultBase):
    """Result of cross-modality fusion: ranked concepts, weights, cross-modality edge count, and detected gaps."""

    query_modalities: list[str] = field(default_factory=list)
    modality_weights: dict[str, float] = field(default_factory=dict)
    ranked_concepts: list[ModalityProfile] = field(default_factory=list)
    cross_modality_edges: int = 0
    gaps: list[ModalityGap] = field(default_factory=list)
    total_candidates: int = 0


_ALL_MODALITIES = list(Modality)


def _node_modalities(graph: Any, node_id: str) -> set[Modality]:
    """Return the modality tags for a node, defaulting to CONCEPTUAL."""
    node = graph.get_node(node_id)
    if node is None:
        return {Modality.CONCEPTUAL}
    tags = node.metadata.modality_tags
    return tags if tags else {Modality.CONCEPTUAL}


class ModalityFusionEngine:
    """Cross-modality fusion engine: queries the graph across multiple modalities, weights results
    by modality relevance, detects modality gaps, and produces fused relevance rankings via RRF."""

    def __init__(self, graph: Any) -> None:
        """Initialize with a reference to the underlying Hypergraph.

        Args:
            graph: A ``Hypergraph`` instance.
        """
        self._graph = graph

    def fuse(
        self,
        seed_id: str,
        *,
        modalities: set[Modality] | None = None,
        weights: dict[str, float] | None = None,
        max_depth: int = 3,
        max_concepts: int = 50,
        rrf_k: int = 60,
    ) -> FusionResult:
        """Query across multiple modalities with per-modality RRF fusion.

        Args:
            seed_id: Internal node ID to start BFS from.
            modalities: Set of modalities to query. Defaults to all six.
            weights: Per-modality weights (keyed by modality value string).
                Defaults to uniform 1.0.
            max_depth: BFS depth from seed.
            max_concepts: Maximum ranked concepts to return.
            rrf_k: RRF smoothing constant.

        Returns:
            FusionResult with ranked concepts, weights, and cross-modality edge count.
        """
        if self._graph.get_node(seed_id) is None:
            return FusionResult()

        mod_set = modalities if modalities is not None else set(_ALL_MODALITIES)
        mod_list = sorted(mod_set, key=lambda m: m.value)
        mod_names = [m.value for m in mod_list]

        w: dict[str, float] = {}
        if weights:
            for m in mod_list:
                w[m.value] = weights.get(m.value, 1.0)
        else:
            for name in mod_names:
                w[name] = 1.0

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(seed_id, 0)])
        visited.add(seed_id)
        candidate_ids: list[str] = [seed_id]

        while queue:
            nid, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self._graph.incident_edges(nid):
                for participant in edge.node_ids:
                    if participant not in visited:
                        visited.add(participant)
                        candidate_ids.append(participant)
                        queue.append((participant, depth + 1))

        per_modality_scores: dict[str, dict[str, float]] = {name: {} for name in mod_names}

        for nid in candidate_ids:
            node = self._graph.get_node(nid)
            if node is None:
                continue
            for edge in self._graph.incident_edges(nid):
                edge_mods: set[Modality] = set()
                if edge.metadata.modality_tags:
                    edge_mods.update(edge.metadata.modality_tags)
                for pid in edge.node_ids:
                    pnode = self._graph.get_node(pid)
                    if pnode and pnode.metadata.modality_tags:
                        edge_mods.update(pnode.metadata.modality_tags)
                if not edge_mods:
                    edge_mods = {Modality.CONCEPTUAL}
                for em in edge_mods:
                    if em in mod_set:
                        per_modality_scores[em.value][nid] = per_modality_scores[em.value].get(nid, 0.0) + edge.weight

        per_modality_ranked: dict[str, list[tuple[str, float]]] = {}
        for name in mod_names:
            scored = sorted(per_modality_scores[name].items(), key=lambda x: -x[1])
            per_modality_ranked[name] = scored

        rrf_scores: dict[str, float] = {}
        for nid in candidate_ids:
            rrf_scores[nid] = 0.0
        for name in mod_names:
            for rank, (nid, _score) in enumerate(per_modality_ranked[name]):
                contribution = w[name] / (rrf_k + rank + 1)
                rrf_scores[nid] = rrf_scores.get(nid, 0.0) + contribution

        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: -x[1])
        top_candidates = sorted_candidates[:max_concepts]

        profiles: list[ModalityProfile] = []
        for nid, fused in top_candidates:
            per_mod: dict[str, float] = {}
            coverage: dict[str, int] = {}
            for name in mod_names:
                score = per_modality_scores[name].get(nid, 0.0)
                per_mod[name] = score
                coverage[name] = 1 if score > 0 else 0
            dominant = max(per_mod, key=lambda k: per_mod[k]) if any(v > 0 for v in per_mod.values()) else mod_names[0]
            gap_mods = [name for name in mod_names if coverage.get(name, 0) == 0]
            profiles.append(ModalityProfile(
                node_id=nid,
                per_modality_score=per_mod,
                modality_coverage=coverage,
                fused_score=fused,
                dominant_modality=dominant,
                gap_modalities=gap_mods,
            ))

        cross_edges = self._count_cross_modality_edges(candidate_ids)

        return FusionResult(
            query_modalities=mod_names,
            modality_weights=w,
            ranked_concepts=profiles,
            cross_modality_edges=cross_edges,
            gaps=[],
            total_candidates=len(candidate_ids),
        )

    def detect_gaps(
        self,
        concept_ids: list[str],
        *,
        expected_modalities: set[Modality] | None = None,
    ) -> list[ModalityGap]:
        """Detect modality gaps for a list of concepts.

        Args:
            concept_ids: Internal node IDs to analyze.
            expected_modalities: Modalities to check for. Defaults to all.

        Returns:
            List of ModalityGap for concepts with incomplete coverage.
        """
        mod_set = expected_modalities if expected_modalities is not None else set(_ALL_MODALITIES)
        mod_names = sorted(m.value for m in mod_set)
        total = len(mod_names)

        gaps: list[ModalityGap] = []
        for cid in concept_ids:
            node = self._graph.get_node(cid)
            if node is None:
                continue
            concept_label = node.label
            rich: list[str] = []
            missing: list[str] = []
            present: set[str] = set()

            for edge in self._graph.incident_edges(cid):
                edge_mods: set[Modality] = set()
                if edge.metadata.modality_tags:
                    edge_mods.update(edge.metadata.modality_tags)
                for pid in edge.node_ids:
                    pn = self._graph.get_node(pid)
                    if pn and pn.metadata.modality_tags:
                        edge_mods.update(pn.metadata.modality_tags)
                if not edge_mods:
                    edge_mods = {Modality.CONCEPTUAL}
                for em in edge_mods:
                    if em in mod_set:
                        present.add(em.value)

            for name in mod_names:
                if name in present:
                    rich.append(name)
                else:
                    missing.append(name)

            ratio = len(rich) / total if total > 0 else 0.0
            gaps.append(ModalityGap(
                concept=concept_label,
                rich_modalities=rich,
                gap_modalities=missing,
                coverage_ratio=ratio,
            ))

        return gaps

    def modality_coverage(self, concept_id: str) -> ModalityProfile:
        """Compute per-modality coverage for a single concept.

        Args:
            concept_id: Internal node ID.

        Returns:
            ModalityProfile with per-modality scores and coverage.
        """
        node = self._graph.get_node(concept_id)
        if node is None:
            return ModalityProfile(node_id=concept_id)

        per_mod: dict[str, float] = {}
        coverage: dict[str, int] = {}

        for edge in self._graph.incident_edges(concept_id):
            edge_mods: set[Modality] = set()
            if edge.metadata.modality_tags:
                edge_mods.update(edge.metadata.modality_tags)
            for pid in edge.node_ids:
                pn = self._graph.get_node(pid)
                if pn and pn.metadata.modality_tags:
                    edge_mods.update(pn.metadata.modality_tags)
            if not edge_mods:
                edge_mods = {Modality.CONCEPTUAL}
            for em in edge_mods:
                name = em.value
                per_mod[name] = per_mod.get(name, 0.0) + edge.weight
                coverage[name] = coverage.get(name, 0) + 1

        dominant = max(per_mod, key=lambda k: per_mod[k]) if per_mod else ""
        gap = [m.value for m in _ALL_MODALITIES if m.value not in per_mod]

        return ModalityProfile(
            node_id=concept_id,
            per_modality_score=per_mod,
            modality_coverage=coverage,
            fused_score=0.0,
            dominant_modality=dominant,
            gap_modalities=gap,
        )

    def cross_modality_edges(self, concept_id: str) -> int:
        """Count edges where the concept connects to nodes with non-overlapping modality tags.

        Args:
            concept_id: Internal node ID.

        Returns:
            Count of cross-modality edges.
        """
        node = self._graph.get_node(concept_id)
        if node is None:
            return 0

        seed_mods = _node_modalities(self._graph, concept_id)
        seed_mod_values = {m.value for m in seed_mods}
        count = 0

        for edge in self._graph.incident_edges(concept_id):
            other_mods: set[str] = set()
            for pid in edge.node_ids:
                if pid == concept_id:
                    continue
                for m in _node_modalities(self._graph, pid):
                    other_mods.add(m.value)
            if other_mods and not other_mods.intersection(seed_mod_values):
                count += 1

        return count

    def to_dict(self) -> dict[str, Any]:
        """Serialize engine state to a dict.

        Returns:
            Dict with graph node/edge counts for verification.
        """
        return {
            "node_count": self._graph.node_count,
            "edge_count": self._graph.edge_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Any) -> ModalityFusionEngine:
        """Reconstruct an engine from serialized state and a live graph.

        Args:
            data: Dict previously returned by ``to_dict()``.
            graph: A live ``Hypergraph`` instance.

        Returns:
            A new ModalityFusionEngine bound to the graph.
        """
        engine = cls(graph)
        return engine

    def _count_cross_modality_edges(self, node_ids: list[str]) -> int:
        """Count edges within a subgraph where source and target have non-overlapping modality tags."""
        counted_edges: set[str] = set()
        count = 0

        for nid in node_ids:
            for edge in self._graph.incident_edges(nid):
                if edge.id in counted_edges:
                    continue
                counted_edges.add(edge.id)
                all_source_mods: set[str] = set()
                all_target_mods: set[str] = set()
                for sid in edge.source_ids:
                    for m in _node_modalities(self._graph, sid):
                        all_source_mods.add(m.value)
                for tid in edge.target_ids:
                    for m in _node_modalities(self._graph, tid):
                        all_target_mods.add(m.value)
                if all_source_mods and all_target_mods and not all_source_mods.intersection(all_target_mods):
                    count += 1

        return count
