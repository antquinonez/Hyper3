from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.kernel_types import Metadata, Modality
from hyper3.memory import HypergraphMemory
from hyper3.modality_fusion import (
    FusionResult,
    ModalityFusionEngine,
    ModalityGap,
    ModalityProfile,
)


def _make_graph() -> Hypergraph:
    return Hypergraph()


def _add_tagged_node(g: Hypergraph, label: str, *modalities: Modality) -> str:
    node = Hypernode(label=label)
    node.metadata.modality_tags = set(modalities) if modalities else set()
    g.add_node(node)
    return node.id


def _add_edge(g: Hypergraph, src: str, tgt: str, label: str = "", weight: float = 1.0) -> str:
    edge = Hyperedge(
        source_ids=frozenset({src}),
        target_ids=frozenset({tgt}),
        label=label,
        weight=weight,
    )
    g.add_edge(edge)
    return edge.id


class TestModalityFusionEngineConstruction:
    def test_construction(self):
        g = _make_graph()
        engine = ModalityFusionEngine(g)
        assert engine._graph is g

    def test_to_dict(self):
        g = _make_graph()
        _add_tagged_node(g, "a")
        engine = ModalityFusionEngine(g)
        d = engine.to_dict()
        assert d["node_count"] == 1
        assert d["edge_count"] == 0

    def test_from_dict(self):
        g = _make_graph()
        _add_tagged_node(g, "x")
        engine = ModalityFusionEngine(g)
        d = engine.to_dict()
        restored = ModalityFusionEngine.from_dict(d, g)
        assert restored._graph is g
        assert restored.to_dict()["node_count"] == 1


class TestFuse:
    def test_fuse_empty_graph(self):
        g = _make_graph()
        engine = ModalityFusionEngine(g)
        result = engine.fuse("nonexistent")
        assert result.total_candidates == 0
        assert result.ranked_concepts == []

    def test_fuse_no_modality_tags_treats_as_conceptual(self):
        g = _make_graph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        _add_edge(g, a.id, b.id, label="rel")
        engine = ModalityFusionEngine(g)
        result = engine.fuse(a.id)
        assert result.total_candidates == 2
        assert len(result.ranked_concepts) == 2
        assert "conceptual" in result.query_modalities
        for profile in result.ranked_concepts:
            assert profile.per_modality_score.get("conceptual", 0.0) > 0.0

    def test_fuse_single_modality(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="causes")
        engine = ModalityFusionEngine(g)
        result = engine.fuse(a_id, modalities={Modality.CAUSAL})
        assert result.query_modalities == ["convergence"]
        assert len(result.ranked_concepts) == 2

    def test_fuse_multiple_modalities_rrf(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.TEMPORAL)
        c_id = _add_tagged_node(g, "c", Modality.CAUSAL, Modality.TEMPORAL)
        _add_edge(g, a_id, b_id, label="rel", weight=2.0)
        _add_edge(g, b_id, c_id, label="rel", weight=3.0)
        engine = ModalityFusionEngine(g)
        result = engine.fuse(
            a_id,
            modalities={Modality.CAUSAL, Modality.TEMPORAL},
        )
        assert result.total_candidates == 3
        assert len(result.ranked_concepts) == 3
        c_profile = next(p for p in result.ranked_concepts if p.node_id == c_id)
        b_profile = next(p for p in result.ranked_concepts if p.node_id == b_id)
        assert c_profile.fused_score > 0
        assert b_profile.fused_score > 0

    def test_fuse_custom_weights(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL, Modality.TEMPORAL)
        b_id = _add_tagged_node(g, "b", Modality.TEMPORAL)
        c_id = _add_tagged_node(g, "c", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="rel")
        _add_edge(g, a_id, c_id, label="rel")
        engine = ModalityFusionEngine(g)
        result = engine.fuse(
            a_id,
            modalities={Modality.CAUSAL, Modality.TEMPORAL},
            weights={"convergence": 10.0, "temporal": 1.0},
        )
        c_profile = next(p for p in result.ranked_concepts if p.node_id == c_id)
        b_profile = next(p for p in result.ranked_concepts if p.node_id == b_id)
        assert c_profile.per_modality_score.get("convergence", 0.0) > 0
        assert c_profile.fused_score > 0
        assert b_profile.fused_score > 0

    def test_fuse_max_concepts_limit(self):
        g = _make_graph()
        seed = g.add_node(Hypernode(label="seed"))
        ids = [seed.id]
        for i in range(10):
            n = g.add_node(Hypernode(label=f"n{i}"))
            ids.append(n.id)
            _add_edge(g, seed.id, n.id, label="rel")
        engine = ModalityFusionEngine(g)
        result = engine.fuse(seed.id, max_concepts=3)
        assert len(result.ranked_concepts) == 3
        assert result.total_candidates == 11

    def test_fuse_seed_with_no_edges(self):
        g = _make_graph()
        a_id = g.add_node(Hypernode(label="a")).id
        engine = ModalityFusionEngine(g)
        result = engine.fuse(a_id)
        assert result.total_candidates == 1
        assert len(result.ranked_concepts) == 1
        assert result.ranked_concepts[0].node_id == a_id

    def test_fuse_cross_modality_edges_counted(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.TEMPORAL)
        _add_edge(g, a_id, b_id, label="cross")
        engine = ModalityFusionEngine(g)
        result = engine.fuse(a_id)
        assert result.cross_modality_edges == 1

    def test_fuse_no_cross_modality_edges_when_same(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="same")
        engine = ModalityFusionEngine(g)
        result = engine.fuse(a_id)
        assert result.cross_modality_edges == 0

    def test_fuse_rrf_k_parameter(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="rel", weight=5.0)
        engine = ModalityFusionEngine(g)
        r1 = engine.fuse(a_id, rrf_k=1)
        r2 = engine.fuse(a_id, rrf_k=1000)
        s1 = r1.ranked_concepts[0].fused_score
        s2 = r2.ranked_concepts[0].fused_score
        assert s1 != s2


class TestModalityCoverage:
    def test_coverage_node_with_multiple_modalities(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL, Modality.TEMPORAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="rel", weight=2.0)
        engine = ModalityFusionEngine(g)
        profile = engine.modality_coverage(a_id)
        assert profile.node_id == a_id
        assert profile.per_modality_score.get("convergence", 0.0) == 2.0
        assert "convergence" not in profile.gap_modalities

    def test_coverage_node_with_no_edges(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        engine = ModalityFusionEngine(g)
        profile = engine.modality_coverage(a_id)
        assert profile.per_modality_score == {}
        assert len(profile.gap_modalities) > 0

    def test_coverage_no_modality_tags_defaults_conceptual(self):
        g = _make_graph()
        a_id = g.add_node(Hypernode(label="a")).id
        b_id = g.add_node(Hypernode(label="b")).id
        _add_edge(g, a_id, b_id, label="rel")
        engine = ModalityFusionEngine(g)
        profile = engine.modality_coverage(a_id)
        assert profile.per_modality_score.get("conceptual", 0.0) > 0.0

    def test_coverage_missing_node(self):
        g = _make_graph()
        engine = ModalityFusionEngine(g)
        profile = engine.modality_coverage("nonexistent")
        assert profile.node_id == "nonexistent"
        assert profile.per_modality_score == {}


class TestDetectGaps:
    def test_gap_present_in_some_modalities(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="rel")
        engine = ModalityFusionEngine(g)
        gaps = engine.detect_gaps([a_id])
        assert len(gaps) == 1
        gap = gaps[0]
        assert gap.concept == "a"
        assert "convergence" in gap.rich_modalities
        assert "temporal" in gap.gap_modalities
        assert 0.0 < gap.coverage_ratio < 1.0

    def test_gap_all_modalities_present(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="rel")
        engine = ModalityFusionEngine(g)
        gaps = engine.detect_gaps([a_id], expected_modalities={Modality.CAUSAL})
        assert len(gaps) == 1
        assert len(gaps[0].gap_modalities) == 0
        assert gaps[0].coverage_ratio == 1.0

    def test_gap_expected_modalities_filter(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="rel")
        engine = ModalityFusionEngine(g)
        gaps = engine.detect_gaps([a_id], expected_modalities={Modality.CAUSAL, Modality.TEMPORAL})
        assert len(gaps[0].gap_modalities) == 1
        assert gaps[0].gap_modalities == ["temporal"]


class TestCrossModalityEdges:
    def test_cross_edge_between_different_modalities(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.TEMPORAL)
        _add_edge(g, a_id, b_id, label="cross")
        engine = ModalityFusionEngine(g)
        count = engine.cross_modality_edges(a_id)
        assert count == 1

    def test_cross_edge_same_modality_returns_zero(self):
        g = _make_graph()
        a_id = _add_tagged_node(g, "a", Modality.CAUSAL)
        b_id = _add_tagged_node(g, "b", Modality.CAUSAL)
        _add_edge(g, a_id, b_id, label="same")
        engine = ModalityFusionEngine(g)
        assert engine.cross_modality_edges(a_id) == 0

    def test_cross_edge_missing_node(self):
        g = _make_graph()
        engine = ModalityFusionEngine(g)
        assert engine.cross_modality_edges("nonexistent") == 0


class TestIntegration:
    def test_via_analytics_mixin(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="rel")
        g = mem._graph
        a_node = mem._find_node("a")
        assert a_node is not None
        g.get_node(a_node.id).metadata.modality_tags = {Modality.CAUSAL}
        b_node = mem._find_node("b")
        assert b_node is not None
        g.get_node(b_node.id).metadata.modality_tags = {Modality.TEMPORAL}
        result = mem.cross_modality("a")
        assert isinstance(result, FusionResult)
        assert result.total_candidates >= 2

    def test_via_analyze_namespace(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="rel")
        g = mem._graph
        x_node = mem._find_node("x")
        assert x_node is not None
        g.get_node(x_node.id).metadata.modality_tags = {Modality.CAUSAL}
        y_node = mem._find_node("y")
        assert y_node is not None
        g.get_node(y_node.id).metadata.modality_tags = {Modality.CAUSAL}
        result = mem.analyze.cross_modality("x")
        assert isinstance(result, FusionResult)
        assert result.total_candidates >= 2

    def test_rrf_multi_modality_ranks_higher(self):
        g = _make_graph()
        seed_id = _add_tagged_node(g, "seed", Modality.CAUSAL, Modality.TEMPORAL)
        single_id = _add_tagged_node(g, "single", Modality.CAUSAL)
        multi_id = _add_tagged_node(g, "multi", Modality.CAUSAL, Modality.TEMPORAL)
        _add_edge(g, seed_id, single_id, label="rel", weight=1.0)
        _add_edge(g, seed_id, multi_id, label="rel", weight=1.0)
        _add_edge(g, multi_id, seed_id, label="back", weight=1.0)
        engine = ModalityFusionEngine(g)
        result = engine.fuse(seed_id, modalities={Modality.CAUSAL, Modality.TEMPORAL})
        multi_profile = next((p for p in result.ranked_concepts if p.node_id == multi_id), None)
        single_profile = next((p for p in result.ranked_concepts if p.node_id == single_id), None)
        assert multi_profile is not None
        assert single_profile is not None
        assert multi_profile.fused_score >= single_profile.fused_score

    def test_mixed_tagged_and_untagged(self):
        g = _make_graph()
        tagged_id = _add_tagged_node(g, "tagged", Modality.CAUSAL)
        untagged_id = g.add_node(Hypernode(label="untagged")).id
        _add_edge(g, tagged_id, untagged_id, label="rel")
        engine = ModalityFusionEngine(g)
        result = engine.fuse(tagged_id)
        assert result.total_candidates == 2
        untagged_profile = next(p for p in result.ranked_concepts if p.node_id == untagged_id)
        assert untagged_profile.per_modality_score.get("convergence", 0.0) > 0
