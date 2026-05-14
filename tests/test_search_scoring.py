import math
import time

import numpy as np
import pytest

from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hypernode
from hyper3.search_index import AttributeIndex, SearchFilter
from hyper3.search_planner import QueryPlanner, SearchPlan
from hyper3.search_query import FieldBoost, SearchQuery
from hyper3.search_scoring import ScoringPipeline


def _make_node(label: str, data: dict | None = None) -> Hypernode:
    return Hypernode(label=label, data=data or {})


def _build_catalog(graph):
    graph.add_node(_make_node("a", {"type": "movie", "genre": "action", "year": 2020}))
    graph.add_node(_make_node("b", {"type": "movie", "genre": "comedy", "year": 2021}))
    graph.add_node(_make_node("c", {"type": "book", "genre": "scifi", "year": 2019}))
    graph.add_node(_make_node("d", {"type": "movie", "genre": "action", "year": 2022}))


class TestScoringPipeline:
    def setup_method(self):
        self.graph = Hypergraph()
        _build_catalog(self.graph)
        self.index = AttributeIndex()
        self.index.build(self.graph)
        self.planner = QueryPlanner(self.graph, index=self.index)
        self.pipeline = ScoringPipeline(self.graph)

    def test_score_browse_candidates(self):
        q = SearchQuery(filters=[SearchFilter("type", "movie")])
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        assert len(results) == 3
        assert all(r.strategy == plan.strategy for r in results)
        labels = {r.label for r in results}
        assert labels == {"a", "b", "d"}

    def test_score_sorted_descending(self):
        q = SearchQuery(filters=[SearchFilter("type", "movie")])
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_score_with_field_boost(self):
        q = SearchQuery(
            filters=[SearchFilter("type", "movie")],
            boosts=[FieldBoost(field="genre", factor=2.0, value="action")],
        )
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        action_results = [r for r in results if r.data.get("genre") == "action"]
        non_action = [r for r in results if r.data.get("genre") != "action"]
        if action_results and non_action:
            assert action_results[0].boost_multiplier > non_action[0].boost_multiplier

    def test_score_with_min_score(self):
        q = SearchQuery(min_score=999.0)
        plan = self.planner.plan(q)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert len(results) == 0

    def test_score_empty_candidates(self):
        q = SearchQuery()
        plan = self.planner.plan(q)
        results = self.pipeline.score(set(), q, plan)
        assert results == []

    def test_score_preserves_data(self):
        q = SearchQuery(filters=[SearchFilter("type", "movie")])
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        for r in results:
            assert isinstance(r.data, dict)
            assert "type" in r.data


class TestScoringPipelineActivation:
    """Tests covering _collect_activation (lines 70-77)."""

    def setup_method(self):
        self.graph = Hypergraph()
        _build_catalog(self.graph)
        from hyper3.retrieval_activation import SpreadingActivation

        self.activation = SpreadingActivation(self.graph)
        self.pipeline = ScoringPipeline(self.graph, activation=self.activation)

    def test_activation_scoring_with_text_match(self):
        q = SearchQuery(text="a")
        plan = SearchPlan(use_activation=True, activation_iterations=2)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert len(results) > 0
        assert any(r.activation_score > 0.0 for r in results)

    def test_activation_text_not_found_returns_empty_scores(self):
        q = SearchQuery(text="nonexistent")
        plan = SearchPlan(use_activation=True)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert all(r.activation_score == 0.0 for r in results)

    def test_activation_skipped_without_plan_flag(self):
        q = SearchQuery(text="a")
        plan = SearchPlan(use_activation=False)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert all(r.activation_score == 0.0 for r in results)


class TestScoringPipelineEmbedding:
    """Tests covering _collect_similarity (lines 84-93)."""

    def setup_method(self):
        self.graph = Hypergraph()
        _build_catalog(self.graph)
        from hyper3.embedding import EmbeddingEngine, HashEmbeddingProvider

        provider = HashEmbeddingProvider(dim=16)
        self.engine = EmbeddingEngine(self.graph, provider=provider, similarity_threshold=0.0)
        self.engine.precompute_all()
        self.pipeline = ScoringPipeline(self.graph, embedding=self.engine)

    def test_similarity_scoring_with_text_match(self):
        q = SearchQuery(text="a")
        plan = SearchPlan(use_embedding=True, embedding_top_k=4)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert len(results) > 0
        assert any(r.similarity_score > 0.0 for r in results)

    def test_similarity_text_not_found_returns_zero(self):
        q = SearchQuery(text="nonexistent")
        plan = SearchPlan(use_embedding=True)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert all(r.similarity_score == 0.0 for r in results)

    def test_similarity_skipped_without_plan_flag(self):
        q = SearchQuery(text="a")
        plan = SearchPlan(use_embedding=False)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert all(r.similarity_score == 0.0 for r in results)


class TestScoringBoostFunctions:
    """Tests covering _compute_boost recency, popularity, and field-presence (lines 115-128)."""

    def test_recency_boost_decays_with_age(self):
        node = _make_node("fresh", {"type": "doc"})
        boost = FieldBoost(field="type", factor=3.0, function="recency")
        score = ScoringPipeline._compute_boost(node, node.data, boost)
        assert 0.0 < score <= 3.0
        assert score > 0.0

    def test_popularity_boost_increases_with_access_count(self):
        low = _make_node("low", {"type": "doc"})
        high = _make_node("high", {"type": "doc"})
        high.access_count = 100
        boost = FieldBoost(field="type", factor=2.0, function="popularity")
        score_low = ScoringPipeline._compute_boost(low, low.data, boost)
        score_high = ScoringPipeline._compute_boost(high, high.data, boost)
        assert score_high > score_low

    def test_popularity_boost_scales_with_logarithm(self):
        node = _make_node("popular", {"type": "doc"})
        node.access_count = 10000
        boost = FieldBoost(field="type", factor=2.0, function="popularity")
        score = ScoringPipeline._compute_boost(node, node.data, boost)
        assert score > 2.0

    def test_field_value_mismatch_returns_one(self):
        node = _make_node("x", {"genre": "comedy"})
        boost = FieldBoost(field="genre", factor=2.0, value="action")
        score = ScoringPipeline._compute_boost(node, node.data, boost)
        assert score == 1.0

    def test_field_presence_boost_without_value(self):
        node = _make_node("x", {"genre": "action"})
        boost = FieldBoost(field="genre", factor=2.5)
        score = ScoringPipeline._compute_boost(node, node.data, boost)
        assert score == 2.5

    def test_field_absence_returns_one(self):
        node = _make_node("x", {"type": "doc"})
        boost = FieldBoost(field="missing_field", factor=3.0)
        score = ScoringPipeline._compute_boost(node, node.data, boost)
        assert score == 1.0


class TestScoringCombineWeights:
    """Tests covering _combine weight calculation (lines 96-103)."""

    def test_combine_index_only(self):
        plan = SearchPlan(use_index=True, use_activation=False, use_embedding=False)
        score = ScoringPipeline._combine(0.5, 0.3, plan)
        assert score == pytest.approx(1.0)

    def test_combine_all_enabled(self):
        plan = SearchPlan(use_index=True, use_activation=True, use_embedding=True)
        score = ScoringPipeline._combine(0.8, 0.6, plan)
        expected = (0.8 * 0.4 + 0.6 * 0.6 + 1.0) / (0.4 + 0.6 + 1.0)
        assert score == pytest.approx(expected)

    def test_combine_no_flags_uses_denominator_one(self):
        plan = SearchPlan(use_index=False, use_activation=False, use_embedding=False)
        score = ScoringPipeline._combine(0.0, 0.0, plan)
        assert score == pytest.approx(0.0)


class TestScoringMissingNode:
    """Test covering the node-not-found guard (line 41)."""

    def test_score_skips_nonexistent_candidate_ids(self):
        graph = Hypergraph()
        _build_catalog(graph)
        pipeline = ScoringPipeline(graph)
        q = SearchQuery()
        plan = SearchPlan(use_index=True)
        fake_id = "deadbeef00000000"
        results = pipeline.score({fake_id}, q, plan)
        assert results == []
