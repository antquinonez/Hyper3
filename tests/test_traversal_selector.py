from __future__ import annotations

import pytest

from hyper3.adaptive_slice import SliceContext
from hyper3.kernel import Hypergraph
from hyper3.traversal_selector import (
    StrategyRecommendation,
    StrategyReport,
    TraversalStrategy,
    TraversalStrategySelector,
)


def _ctx(**kw: float | int) -> SliceContext:
    defaults = dict(
        concept_id="test",
        degree_ratio=0.5,
        label_diversity=0.5,
        modality_count=0,
        weight_spread=0.5,
        connectivity=0.5,
        neighbor_count=10,
    )
    defaults.update(kw)
    return SliceContext(**defaults)


class TestTraversalSelectorConstruction:
    def test_default_construction(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        report = selector.get_report()
        assert report.total_outcomes == 0

    def test_custom_parameters(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, exploration_rate=0.5, context_bins=3)
        assert selector._exploration_rate == 0.5


class TestTraversalSelectorRecommend:
    def test_recommend_returns_strategy(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, exploration_rate=0.0)
        rec = selector.recommend(_ctx())
        assert isinstance(rec.strategy, TraversalStrategy)
        assert isinstance(rec.confidence, float)

    def test_recommend_with_zero_exploration_uses_thompson(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, exploration_rate=0.0)
        selector._alpha[("dr2_ld2_mc0_nc0", TraversalStrategy.DFS)] = 100.0
        selector._beta[("dr2_ld2_mc0_nc0", TraversalStrategy.DFS)] = 1.0
        rec = selector.recommend(_ctx(degree_ratio=0.5, label_diversity=0.5, neighbor_count=5))
        assert rec.strategy == TraversalStrategy.DFS

    def test_recommend_with_full_exploration_can_return_any(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, exploration_rate=1.0)
        strategies_seen: set[TraversalStrategy] = set()
        for _ in range(200):
            rec = selector.recommend(_ctx())
            strategies_seen.add(rec.strategy)
        assert len(strategies_seen) > 1

    def test_recommend_confidence_from_beta(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, exploration_rate=0.0)
        rec = selector.recommend(_ctx())
        assert 0.0 <= rec.confidence <= 1.0


class TestTraversalSelectorOutcome:
    def test_record_outcome_updates_thompson(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        from hyper3.traversal_selector import StrategyOutcome

        outcome = StrategyOutcome(
            strategy=TraversalStrategy.BFS,
            result_size=10,
            relevance_score=0.8,
            context_key="dr2_ld2_mc0_nc0",
        )
        selector.record_outcome(outcome)
        key = ("dr2_ld2_mc0_nc0", TraversalStrategy.BFS)
        assert selector._alpha.get(key, 1.0) == 2.0

    def test_record_failure_increments_beta(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        from hyper3.traversal_selector import StrategyOutcome

        outcome = StrategyOutcome(
            strategy=TraversalStrategy.DFS,
            result_size=0,
            relevance_score=0.0,
            context_key="dr2_ld2_mc0_nc0",
        )
        selector.record_outcome(outcome)
        key = ("dr2_ld2_mc0_nc0", TraversalStrategy.DFS)
        assert selector._beta.get(key, 1.0) == 2.0

    def test_multiple_outcomes_accumulate(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        from hyper3.traversal_selector import StrategyOutcome

        for _ in range(5):
            selector.record_outcome(
                StrategyOutcome(
                    strategy=TraversalStrategy.WEIGHT_PRIORITY,
                    result_size=5,
                    relevance_score=0.9,
                    context_key="dr2_ld2_mc0_nc0",
                )
            )
        key = ("dr2_ld2_mc0_nc0", TraversalStrategy.WEIGHT_PRIORITY)
        assert selector._alpha.get(key, 1.0) == 6.0


class TestTraversalSelectorReport:
    def test_empty_report(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        report = selector.get_report()
        assert report.total_outcomes == 0
        assert report.strategy_distribution == {}

    def test_report_with_outcomes(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        from hyper3.traversal_selector import StrategyOutcome

        selector.record_outcome(
            StrategyOutcome(
                strategy=TraversalStrategy.BFS,
                result_size=5,
                relevance_score=0.8,
                context_key="ctx1",
            )
        )
        selector.record_outcome(
            StrategyOutcome(
                strategy=TraversalStrategy.DFS,
                result_size=3,
                relevance_score=0.6,
                context_key="ctx1",
            )
        )
        report = selector.get_report()
        assert report.total_outcomes == 2
        assert report.strategy_distribution.get("bfs") == 1
        assert report.strategy_distribution.get("dfs") == 1


class TestTraversalSelectorDiscretize:
    def test_same_context_same_bin(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        ctx1 = _ctx(degree_ratio=0.5, label_diversity=0.5, neighbor_count=10)
        ctx2 = _ctx(degree_ratio=0.5, label_diversity=0.5, neighbor_count=10)
        assert selector._discretize(ctx1) == selector._discretize(ctx2)

    def test_different_contexts_different_bins(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, context_bins=2)
        ctx_low = _ctx(degree_ratio=0.1, neighbor_count=3)
        ctx_high = _ctx(degree_ratio=0.9, neighbor_count=50)
        assert selector._discretize(ctx_low) != selector._discretize(ctx_high)


class TestTraversalSelectorSerialization:
    def test_to_dict_round_trip(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, exploration_rate=0.3)
        from hyper3.traversal_selector import StrategyOutcome

        selector.record_outcome(
            StrategyOutcome(
                strategy=TraversalStrategy.BFS,
                result_size=10,
                relevance_score=0.8,
                context_key="ctx1",
            )
        )
        data = selector.to_dict()
        restored = TraversalStrategySelector.from_dict(data, g)
        assert restored._exploration_rate == 0.3
        assert len(restored._alpha) > 0

    def test_from_dict_defaults(self):
        g = Hypergraph()
        restored = TraversalStrategySelector.from_dict({}, g)
        assert restored._exploration_rate == 0.1


class TestTraversalSelectorEdgeCases:
    def test_cold_start_uses_thompson_with_uniform_priors(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g, exploration_rate=0.0)
        rec = selector.recommend(_ctx())
        assert isinstance(rec.strategy, TraversalStrategy)

    def test_empty_graph_recommendation(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        rec = selector.recommend(SliceContext())
        assert isinstance(rec.strategy, TraversalStrategy)

    def test_heuristic_high_degree_prefers_dfs(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        strategy = selector._heuristic_recommend(_ctx(degree_ratio=0.9))
        assert strategy == TraversalStrategy.DFS

    def test_heuristic_high_modality_prefers_dimension(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        strategy = selector._heuristic_recommend(_ctx(modality_count=4))
        assert strategy == TraversalStrategy.DIMENSION

    def test_heuristic_low_neighbors_prefers_bfs(self):
        g = Hypergraph()
        selector = TraversalStrategySelector(g)
        strategy = selector._heuristic_recommend(_ctx(neighbor_count=2, degree_ratio=0.3, connectivity=0.2))
        assert strategy == TraversalStrategy.BFS
