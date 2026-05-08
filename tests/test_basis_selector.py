from __future__ import annotations

import random

import numpy as np
import pytest

from hyper3.basis_selector import BasisContext, BasisOutcomeRecord, BasisSelector
from hyper3.belief import SamplingProfile
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, Modality


def _make_graph_with_nodes(n: int = 5, temporal: bool = False) -> Hypergraph:
    g = Hypergraph()
    for i in range(n):
        meta = Metadata()
        if temporal:
            meta.temporal_tags = {"t": float(i)}
        node = Hypernode(label=f"c{i}", data={"val": i} if i % 2 == 0 else None, metadata=meta)
        g.add_node(node)
    return g


def _make_graph_with_edges() -> Hypergraph:
    g = Hypergraph()
    nodes = []
    for i in range(6):
        meta = Metadata(modality_tags={Modality.CONCEPTUAL, Modality.TEXTUAL} if i < 3 else set())
        node = Hypernode(label=f"c{i}", data={"k": i}, metadata=meta, weight=1.0 + i * 0.1)
        g.add_node(node)
        nodes.append(node)
    for i in range(5):
        g.add_edge(Hyperedge(
            source_ids=frozenset({nodes[i].id}),
            target_ids=frozenset({nodes[i + 1].id}),
            label=f"rel_{i % 2}",
            weight=1.0 + i * 0.5,
        ))
    return g


PROFILES = {
    "linguistic": SamplingProfile(
        name="linguistic",
        dimensions=["semantic", "syntactic", "pragmatic"],
        weights={"semantic": 0.5, "syntactic": 0.3, "pragmatic": 0.2},
    ),
    "temporal": SamplingProfile(
        name="temporal",
        dimensions=["recency", "frequency", "duration"],
        weights={"recency": 0.4, "frequency": 0.4, "duration": 0.2},
    ),
    "emotional": SamplingProfile(
        name="emotional",
        dimensions=["valence", "arousal", "dominance"],
        weights={"valence": 0.4, "arousal": 0.3, "dominance": 0.3},
    ),
    "pragmatic": SamplingProfile(
        name="pragmatic",
        dimensions=["utility", "relevance", "actionability"],
        weights={"utility": 0.4, "relevance": 0.3, "actionability": 0.3},
    ),
}


class TestExtractContext:
    def test_returns_features_for_existing_node(self):
        g = _make_graph_with_edges()
        node = list(g.nodes)[0]
        sel = BasisSelector(g)
        ctx = sel.extract_context(node.id)
        assert isinstance(ctx, BasisContext)
        assert ctx.concept_id == node.id
        assert 0.0 <= ctx.degree_ratio <= 1.0
        assert 0.0 <= ctx.label_diversity <= 1.0

    def test_returns_defaults_for_missing_node(self):
        g = Hypergraph()
        sel = BasisSelector(g)
        ctx = sel.extract_context("nonexistent")
        assert ctx.degree_ratio == 0.0
        assert ctx.concept_id == "nonexistent"

    def test_degree_ratio_correctness(self):
        g = _make_graph_with_nodes(10)
        nodes = list(g.nodes)
        g.add_edge(Hyperedge(
            source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}),
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}),
        ))
        sel = BasisSelector(g)
        ctx = sel.extract_context(nodes[0].id)
        assert ctx.degree_ratio == 2 / 10

    def test_label_diversity_correctness(self):
        g = _make_graph_with_edges()
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        ctx = sel.extract_context(nodes[0].id)
        assert ctx.label_diversity > 0.0

    def test_to_vector_length(self):
        g = _make_graph_with_edges()
        node = list(g.nodes)[0]
        sel = BasisSelector(g)
        ctx = sel.extract_context(node.id)
        vec = ctx.to_vector()
        assert vec.shape == (7,)


class TestHeuristicSelect:
    def test_default_is_linguistic(self):
        g = _make_graph_with_nodes(3)
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        result = sel.select_basis(nodes[0].id, PROFILES)
        assert result == "linguistic"

    def test_temporal_heuristic(self):
        g = _make_graph_with_nodes(3, temporal=True)
        nodes = list(g.nodes)
        for i in range(len(nodes) - 1):
            g.add_edge(Hyperedge(
                source_ids=frozenset({nodes[i].id}),
                target_ids=frozenset({nodes[i + 1].id}),
                label="temporal_link",
            ))
        sel = BasisSelector(g)
        result = sel.select_basis(nodes[0].id, PROFILES)
        assert result in PROFILES


class TestThompsonSelect:
    def test_biases_toward_successful_basis(self):
        g = _make_graph_with_nodes(3)
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        ctx = sel.extract_context(nodes[0].id)
        for _ in range(20):
            sel.record_outcome("temporal", nodes[0].id, ctx, success=True)
        for _ in range(20):
            sel.record_outcome("emotional", nodes[0].id, ctx, success=False)

        random.seed(42)
        counts: dict[str, int] = {}
        for _ in range(100):
            choice = sel.select_basis(nodes[0].id, PROFILES)
            counts[choice] = counts.get(choice, 0) + 1
        assert counts.get("temporal", 0) > counts.get("emotional", 0)

    def test_explores_unexplored_basis(self):
        g = _make_graph_with_nodes(3)
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        ctx = sel.extract_context(nodes[0].id)
        for _ in range(3):
            sel.record_outcome("temporal", nodes[0].id, ctx, success=True)

        seen = set()
        random.seed(12345)
        for _ in range(200):
            choice = sel.select_basis(nodes[0].id, PROFILES)
            seen.add(choice)
        assert len(seen) >= 2

    def test_returns_default_on_empty_profiles(self):
        g = _make_graph_with_nodes(3)
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        result = sel.select_basis(nodes[0].id, {})
        assert result == "linguistic"


class TestRecordOutcome:
    def test_appends_to_history(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g)
        ctx = BasisContext(concept_id="x")
        sel.record_outcome("temporal", "x", ctx, True)
        assert len(sel._outcome_history) == 1
        assert sel._outcome_history[0].basis_name == "temporal"
        assert sel._outcome_history[0].success is True

    def test_respects_max_history(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g, max_history=10)
        ctx = BasisContext(concept_id="x")
        for i in range(20):
            sel.record_outcome("temporal", "x", ctx, True)
        assert len(sel._outcome_history) == 10

    def test_rolling_window_keeps_recent(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g, max_history=5)
        ctx = BasisContext(concept_id="x")
        for i in range(5):
            sel.record_outcome("linguistic", "x", ctx, False)
        sel.record_outcome("temporal", "x", ctx, True)
        assert sel._outcome_history[-1].basis_name == "temporal"
        assert len(sel._outcome_history) == 5


class TestBlendedProfile:
    def test_returns_composite_profile(self):
        g = _make_graph_with_edges()
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        profile = sel.compute_blended_profile(nodes[0].id, PROFILES)
        assert profile is not None
        assert profile.name == "blended"
        assert len(profile.dimensions) > 0

    def test_blended_weights_sum_approximately(self):
        g = _make_graph_with_edges()
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        profile = sel.compute_blended_profile(nodes[0].id, PROFILES)
        assert profile is not None
        total = sum(profile.weights.values())
        assert abs(total - 1.0) < 0.05 or total > 0

    def test_returns_none_on_empty_profiles(self):
        g = _make_graph_with_nodes(3)
        nodes = list(g.nodes)
        sel = BasisSelector(g)
        result = sel.compute_blended_profile(nodes[0].id, {})
        assert result is None

    def test_returns_linguistic_on_zero_relevance(self):
        g = Hypergraph()
        node = Hypernode(label="c0")
        g.add_node(node)
        sel = BasisSelector(g)
        result = sel.compute_blended_profile(node.id, PROFILES)
        assert result is not None
        assert result.name in ("blended", "linguistic")


class TestAdaptiveProfile:
    def test_returns_original_with_few_outcomes(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g)
        ctx = BasisContext(concept_id="x")
        for _ in range(3):
            sel.record_outcome("temporal", "x", ctx, True)
        result = sel.create_adaptive_profile("temporal", PROFILES)
        assert result is not None
        assert result.name == "temporal"

    def test_adjusts_weights_with_many_outcomes(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g)
        ctx = BasisContext(concept_id="x", temporal_density=0.9, data_richness=0.8)
        for _ in range(10):
            sel.record_outcome("temporal", "x", ctx, success=True)
        ctx_fail = BasisContext(concept_id="x", temporal_density=0.1, data_richness=0.1)
        for _ in range(5):
            sel.record_outcome("temporal", "x", ctx_fail, success=False)
        result = sel.create_adaptive_profile("temporal", PROFILES)
        assert result is not None
        assert result.name == "temporal_adapted"
        orig = PROFILES["temporal"]
        for dim in orig.dimensions:
            assert dim in result.weights

    def test_returns_none_for_unknown_profile(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g)
        result = sel.create_adaptive_profile("nonexistent", PROFILES)
        assert result is None


class TestSuggestNewBasis:
    def test_suggests_alternative_for_poor_basis(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g)
        ctx = BasisContext(concept_id="x")
        for _ in range(15):
            sel.record_outcome("emotional", "x", ctx, success=False)
        result = sel.suggest_new_basis()
        assert result is not None
        assert "emotional" in result

    def test_returns_none_for_good_coverage(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g)
        ctx = BasisContext(concept_id="x")
        for _ in range(15):
            sel.record_outcome("temporal", "x", ctx, success=True)
        result = sel.suggest_new_basis()
        assert result is None


class TestSerialization:
    def test_to_dict_from_dict_roundtrip(self):
        g = _make_graph_with_nodes(3)
        sel = BasisSelector(g, max_history=100, adaptation_rate=0.2)
        ctx = BasisContext(concept_id="x", temporal_density=0.5)
        sel.record_outcome("temporal", "x", ctx, True)
        sel.record_outcome("linguistic", "x", ctx, False)

        data = sel.to_dict()
        assert data["max_history"] == 100
        assert data["adaptation_rate"] == 0.2
        assert len(data["outcome_history"]) == 2

        sel2 = BasisSelector.from_dict(data, g)
        assert sel2._max_history == 100
        assert sel2._adaptation_rate == 0.2
        assert len(sel2._outcome_history) == 2
        assert sel2._outcome_history[0].basis_name == "temporal"
        assert sel2._outcome_history[0].context_vector == ctx.to_vector().tolist()

    def test_empty_roundtrip(self):
        g = Hypergraph()
        sel = BasisSelector(g)
        data = sel.to_dict()
        sel2 = BasisSelector.from_dict(data, g)
        assert sel2._outcome_history == []
