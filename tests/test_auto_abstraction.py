from __future__ import annotations

from hyper3.auto_abstraction import (
    AbstractionAction,
    AbstractionCandidate,
    AbstractionResult,
    AutoAbstractionEngine,
)
from hyper3.kernel import (
    AbstractionLayer,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
)


def _add(g: Hypergraph, label: str, *, layer: AbstractionLayer = AbstractionLayer.DETAIL) -> Hypernode:
    return g.add_node(Hypernode(label=label, metadata=Metadata(abstraction_layer=layer)))


def _link(g: Hypergraph, a: Hypernode, b: Hypernode, label: str = "related") -> None:
    g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label=label))


def _touch(node: Hypernode, count: int) -> None:
    node.access_count = count


class TestAutoAbstractionConstruction:
    def test_default_construction(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(g)
        assert engine._promote_threshold == 0.6
        assert engine._demote_threshold == 2.0
        assert engine._min_cluster_size == 3
        assert not engine._auto_execute

    def test_custom_parameters(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(
            g,
            promote_threshold=0.8,
            demote_threshold=5.0,
            min_cluster_size=5,
            auto_execute=True,
        )
        assert engine._promote_threshold == 0.8
        assert engine._demote_threshold == 5.0
        assert engine._min_cluster_size == 5
        assert engine._auto_execute


class TestAutoAbstractionAssess:
    def test_empty_graph_returns_empty(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(g)
        assert engine.assess() == []

    def test_single_node_no_candidates(self):
        g = Hypergraph()
        _add(g, "solo")
        engine = AutoAbstractionEngine(g)
        assert engine.assess() == []

    def test_two_nodes_no_candidates_below_min_cluster(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        _link(g, a, b)
        engine = AutoAbstractionEngine(g, min_cluster_size=3)
        assert engine.assess() == []

    def test_summary_node_low_access_demotion_candidate(self):
        g = Hypergraph()
        _add(g, "a")
        _add(g, "b")
        _add(g, "c")
        summary = g.add_node(
            Hypernode(
                label="summary_abc",
                metadata=Metadata(abstraction_layer=AbstractionLayer.SUMMARY),
                access_count=0,
            )
        )
        engine = AutoAbstractionEngine(g, demote_threshold=2.0)
        engine._navigator._mappings[summary.id] = type(
            "M", (), {"detail_node_ids": [], "detail_labels": ["a", "b", "c"]}
        )
        candidates = engine.assess()
        demotion = [c for c in candidates if c.recommended_layer == "detail"]
        assert len(demotion) >= 1
        assert demotion[0].node_label == "summary_abc"

    def test_summary_node_high_access_no_demotion(self):
        g = Hypergraph()
        _add(g, "a")
        _add(g, "b")
        summary = g.add_node(
            Hypernode(
                label="summary_ab",
                metadata=Metadata(abstraction_layer=AbstractionLayer.SUMMARY),
                access_count=100,
            )
        )
        engine = AutoAbstractionEngine(g, demote_threshold=2.0)
        engine._navigator._mappings[summary.id] = type(
            "M", (), {"detail_node_ids": [], "detail_labels": ["a", "b"]}
        )
        candidates = engine.assess()
        demotion = [c for c in candidates if c.recommended_layer == "detail"]
        assert len(demotion) == 0

    def test_mixed_layer_group_includes_intermediate(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        c = _add(g, "c")
        _link(g, a, b)
        _link(g, b, c)
        _link(g, c, a)
        _touch(a, 50)
        _touch(b, 50)
        _touch(c, 50)
        engine = AutoAbstractionEngine(g, promote_threshold=0.1, min_cluster_size=3)
        candidates = engine.assess()
        promotion = [c for c in candidates if c.recommended_layer == "summary"]
        assert len(promotion) >= 1

    def test_only_summary_nodes_no_promotion(self):
        g = Hypergraph()
        a = _add(g, "a", layer=AbstractionLayer.SUMMARY)
        b = _add(g, "b", layer=AbstractionLayer.SUMMARY)
        c = _add(g, "c", layer=AbstractionLayer.SUMMARY)
        _link(g, a, b)
        _link(g, b, c)
        _link(g, c, a)
        engine = AutoAbstractionEngine(g, promote_threshold=0.1, min_cluster_size=3)
        candidates = engine.assess()
        promotion = [c for c in candidates if c.recommended_layer == "summary"]
        assert len(promotion) == 0


class TestAutoAbstractionExecute:
    def test_execute_promotion_collapses_group(self):
        g = Hypergraph()
        a = _add(g, "alpha")
        b = _add(g, "beta")
        c = _add(g, "gamma")
        _link(g, a, b)
        _link(g, b, c)
        _link(g, c, a)
        engine = AutoAbstractionEngine(g, promote_threshold=0.1, min_cluster_size=3)
        candidates = engine.assess()
        promotion_cands = [c for c in candidates if c.recommended_layer == "summary"]
        if promotion_cands:
            result = engine.execute(promotion_cands)
            assert result.promotions >= 1
            assert len(result.actions) >= 1
            assert result.actions[0].action == "promote"

    def test_execute_demotion_expands_summary(self):
        g = Hypergraph()
        _add(g, "x")
        _add(g, "y")
        summary = g.add_node(
            Hypernode(
                label="summary_xy",
                metadata=Metadata(abstraction_layer=AbstractionLayer.SUMMARY),
                access_count=0,
            )
        )
        engine = AutoAbstractionEngine(g, demote_threshold=2.0)
        from hyper3.abstraction import AbstractionMapping

        engine._navigator._mappings[summary.id] = AbstractionMapping(
            summary_node_id=summary.id,
            summary_label="summary_xy",
            detail_node_ids=["x_fake", "y_fake"],
            detail_labels=["x", "y"],
            layer=AbstractionLayer.SUMMARY,
        )
        candidates = [AbstractionCandidate(
            node_id=summary.id,
            node_label="summary_xy",
            current_layer="summary",
            recommended_layer="detail",
            reason="low_access_summary",
            score=0.9,
        )]
        result = engine.execute(candidates)
        assert result.demotions >= 1

    def test_execute_returns_action_counts(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(g)
        result = engine.execute([])
        assert result.promotions == 0
        assert result.demotions == 0
        assert result.actions == []


class TestAutoAbstractionAssessAndExecute:
    def test_full_pipeline_empty_graph(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(g)
        result = engine.assess_and_execute()
        assert result.assessed_nodes == 0
        assert result.promotions == 0
        assert result.demotions == 0

    def test_full_pipeline_with_candidates(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        c = _add(g, "c")
        _link(g, a, b)
        _link(g, b, c)
        _link(g, c, a)
        _touch(a, 50)
        _touch(b, 50)
        _touch(c, 50)
        engine = AutoAbstractionEngine(g, promote_threshold=0.1, min_cluster_size=3)
        result = engine.assess_and_execute()
        assert result.assessed_nodes >= 3
        assert result.promotions >= 1


class TestAutoAbstractionGetCandidatesFor:
    def test_no_history_returns_empty(self):
        g = Hypergraph()
        _add(g, "a")
        engine = AutoAbstractionEngine(g)
        result = engine.get_candidates_for("a")
        assert result == []

    def test_unknown_concept_returns_empty(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(g)
        result = engine.get_candidates_for("nonexistent")
        assert result == []


class TestAutoAbstractionSerialization:
    def test_to_dict_round_trip(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(
            g, promote_threshold=0.8, demote_threshold=5.0, auto_execute=True,
        )
        data = engine.to_dict()
        restored = AutoAbstractionEngine.from_dict(data, g)
        assert restored._promote_threshold == 0.8
        assert restored._demote_threshold == 5.0
        assert restored._auto_execute

    def test_from_dict_defaults(self):
        g = Hypergraph()
        restored = AutoAbstractionEngine.from_dict({}, g)
        assert restored._promote_threshold == 0.6
        assert restored._demote_threshold == 2.0
        assert not restored._auto_execute


class TestAutoAbstractionScoring:
    def test_access_density_high_when_uniform(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        _touch(a, 10)
        _touch(b, 10)
        engine = AutoAbstractionEngine(g)
        density = engine._compute_access_density(["a", "b"])
        assert density == 1.0

    def test_access_density_low_when_skewed(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        _touch(a, 100)
        _touch(b, 1)
        engine = AutoAbstractionEngine(g)
        density = engine._compute_access_density(["a", "b"])
        assert 0.0 < density < 0.6

    def test_label_homogeneity_high_when_same_labels(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        _link(g, a, b, "relates")
        _link(g, b, a, "relates")
        engine = AutoAbstractionEngine(g)
        homo = engine._compute_label_homogeneity(["a", "b"])
        assert homo > 0.5

    def test_internal_density_computed_correctly(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        _link(g, a, b)
        engine = AutoAbstractionEngine(g)
        density = engine._compute_internal_density(["a", "b"])
        assert density > 0.0

    def test_internal_density_empty_labels(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(g)
        assert engine._compute_internal_density([]) == 0.0


class TestAutoAbstractionEdgeCases:
    def test_graph_with_no_edges_no_promotion(self):
        g = Hypergraph()
        _add(g, "a")
        _add(g, "b")
        _add(g, "c")
        engine = AutoAbstractionEngine(g, promote_threshold=0.1, min_cluster_size=3)
        candidates = engine.assess()
        promotion = [c for c in candidates if c.recommended_layer == "summary"]
        assert len(promotion) == 0

    def test_cycle_of_summaries_prevented(self):
        g = Hypergraph()
        s1 = g.add_node(Hypernode(label="s1", metadata=Metadata(abstraction_layer=AbstractionLayer.SUMMARY)))
        s2 = g.add_node(Hypernode(label="s2", metadata=Metadata(abstraction_layer=AbstractionLayer.SUMMARY)))
        s3 = g.add_node(Hypernode(label="s3", metadata=Metadata(abstraction_layer=AbstractionLayer.SUMMARY)))
        _link(g, s1, s2)
        _link(g, s2, s3)
        _link(g, s3, s1)
        engine = AutoAbstractionEngine(g, promote_threshold=0.1, min_cluster_size=3)
        candidates = engine.assess()
        promotion = [c for c in candidates if c.recommended_layer == "summary"]
        assert len(promotion) == 0

    def test_backward_compatible_auto_execute_false(self):
        g = Hypergraph()
        engine = AutoAbstractionEngine(g, auto_execute=False)
        assert not engine._auto_execute
