from __future__ import annotations

from hyper3.adaptive_slice import (
    AdaptiveSliceEngine,
    AdaptiveSliceReport,
    RecommendedSlice,
    SliceContext,
    SliceOutcomeRecord,
)
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.kernel_types import Modality
from hyper3.results import _SimpleResultBase


def _make_dense_graph() -> tuple[Hypergraph, str]:
    g = Hypergraph()
    center = g.add_node(Hypernode(label="center"))
    for i in range(20):
        n = g.add_node(Hypernode(label=f"n{i}"))
        g.add_edge(Hyperedge(
            source_ids=frozenset({center.id}),
            target_ids=frozenset({n.id}),
            label=f"e{i % 3}",
        ))
    for i in range(10):
        na = g.get_node_by_label(f"n{i}")
        nb = g.get_node_by_label(f"n{i + 10}")
        g.add_edge(Hyperedge(
            source_ids=frozenset({na.id}),
            target_ids=frozenset({nb.id}),
            label=f"c{i % 2}",
            weight=1.0 + i * 0.1,
        ))
    return g, center.id


def _make_sparse_graph() -> tuple[Hypergraph, str]:
    g = Hypergraph()
    center = g.add_node(Hypernode(label="center"))
    n1 = g.add_node(Hypernode(label="n1"))
    g.add_edge(Hyperedge(
        source_ids=frozenset({center.id}),
        target_ids=frozenset({n1.id}),
        label="e0",
    ))
    return g, center.id


class TestExtractContext:
    def test_dense_neighborhood(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(center_id)
        assert ctx.degree_ratio > 0.0
        assert ctx.neighbor_count == 20
        assert ctx.label_diversity > 0.0

    def test_sparse_neighborhood(self):
        g, center_id = _make_sparse_graph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(center_id)
        assert ctx.neighbor_count == 1
        assert ctx.degree_ratio <= 0.5

    def test_no_node(self):
        g = Hypergraph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context("nonexistent")
        assert ctx.concept_id == "nonexistent"
        assert ctx.degree_ratio == 0.0

    def test_context_vector_length(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(center_id)
        vec = ctx.to_vector()
        assert len(vec) == 6
        assert all(isinstance(v, float) for v in vec)

    def test_context_vector_bounded(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(center_id)
        for v in ctx.to_vector():
            assert 0.0 <= v <= 1.0

    def test_connectivity_in_dense_graph(self):
        g, center_id = _make_dense_graph()
        n0 = g.get_node_by_label("n0")
        n1 = g.get_node_by_label("n1")
        g.add_edge(Hyperedge(
            source_ids=frozenset({n0.id}),
            target_ids=frozenset({n1.id}),
            label="cross",
        ))
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(n0.id)
        assert ctx.neighbor_count >= 1


class TestHeuristicRecommend:
    def test_dense_gets_narrow_slice(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(center_id)
        rec = engine._heuristic_recommend(ctx)
        assert rec.max_depth <= 3
        assert rec.max_nodes <= 50
        assert rec.strategy == "heuristic"

    def test_sparse_gets_wide_slice(self):
        g, center_id = _make_sparse_graph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(center_id)
        rec = engine._heuristic_recommend(ctx)
        assert rec.max_depth >= 3
        assert rec.max_nodes >= 50

    def test_heuristic_confidence_low(self):
        g, center_id = _make_sparse_graph()
        engine = AdaptiveSliceEngine(g)
        ctx = engine.extract_context(center_id)
        rec = engine._heuristic_recommend(ctx)
        assert rec.confidence < 0.5


class TestThompsonRecommend:
    def test_no_history_falls_back_to_heuristic(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        rec = engine.recommend(center_id)
        assert rec.strategy == "heuristic"

    def test_with_history_uses_thompson(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        for _ in range(10):
            engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        rec = engine.recommend(center_id)
        assert rec.strategy == "thompson"
        assert rec.max_depth in [1, 2, 3, 5, 7]
        assert rec.max_nodes in [10, 25, 50, 100, 200]

    def test_recommended_params_within_grid(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        for _ in range(5):
            engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        rec = engine.recommend(center_id)
        assert rec.max_depth in [1, 2, 3, 5, 7]
        assert rec.max_nodes in [10, 25, 50, 100, 200]
        assert rec.min_weight in [0.0, 0.1, 0.3, 0.5]


class TestRecordOutcome:
    def test_appends_to_history(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        assert len(engine._outcome_history) == 1

    def test_respects_max_history(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g, max_history=5)
        for i in range(10):
            engine.record_outcome(center_id, 3, 50, 0.0, success=i % 2 == 0)
        assert len(engine._outcome_history) == 5

    def test_record_captures_context(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        record = engine._outcome_history[0]
        assert len(record.context_vector) == 6
        assert record.concept_id == center_id
        assert record.success is True


class TestReport:
    def test_empty_report(self):
        g = Hypergraph()
        engine = AdaptiveSliceEngine(g)
        report = engine.report()
        assert report.total_outcomes == 0
        assert report.successful_outcomes == 0
        assert report.overall_success_rate == 0.0

    def test_report_with_data(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        engine.record_outcome(center_id, 5, 100, 0.0, success=False)
        engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        report = engine.report()
        assert report.total_outcomes == 3
        assert report.successful_outcomes == 2
        assert abs(report.overall_success_rate - 2 / 3) < 1e-9
        assert report.grid_coverage > 0.0

    def test_report_most_used_params(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        for _ in range(5):
            engine.record_outcome(center_id, 5, 100, 0.0, success=True)
        engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        report = engine.report()
        assert report.most_used_depth == 5
        assert report.most_used_nodes == 100


class TestSerialization:
    def test_roundtrip(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g)
        engine.record_outcome(center_id, 3, 50, 0.0, success=True)
        engine.record_outcome(center_id, 5, 100, 0.1, success=False)
        data = engine.to_dict()
        restored = AdaptiveSliceEngine.from_dict(data, g)
        assert len(restored._outcome_history) == 2
        assert restored._outcome_history[0].success is True
        assert restored._outcome_history[1].max_depth == 5

    def test_roundtrip_preserves_history(self):
        g, center_id = _make_dense_graph()
        engine = AdaptiveSliceEngine(g, max_history=10)
        for i in range(10):
            engine.record_outcome(center_id, 3, 50, 0.0, success=i % 2 == 0)
        data = engine.to_dict()
        restored = AdaptiveSliceEngine.from_dict(data, g)
        assert restored._max_history == 10
        assert len(restored._outcome_history) == 10


class TestResultTypes:
    def test_slice_context_is_simple_result_base(self):
        ctx = SliceContext(degree_ratio=0.5)
        assert isinstance(ctx, _SimpleResultBase)
        assert "degree_ratio" in ctx
        assert ctx["degree_ratio"] == 0.5

    def test_recommended_slice_is_simple_result_base(self):
        rec = RecommendedSlice(max_depth=5)
        assert isinstance(rec, _SimpleResultBase)
        assert rec["max_depth"] == 5

    def test_report_is_simple_result_base(self):
        report = AdaptiveSliceReport(total_outcomes=10)
        assert isinstance(report, _SimpleResultBase)
        assert report["total_outcomes"] == 10

    def test_outcome_record_is_simple_result_base(self):
        rec = SliceOutcomeRecord(max_depth=3, success=True)
        assert isinstance(rec, _SimpleResultBase)
        assert rec["success"] is True
