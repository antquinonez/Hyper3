import pytest
from hyper3 import (
    BoundaryNavigator,
    ConstraintCheck,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
    NoSelfLoopConstraint,
    ProvenanceDepthConstraint,
    WeightInflationConstraint,
    HypergraphMemory,
)


def _make_edge(src_label, tgt_label, weight=1.0, custom=None):
    g = Hypergraph()
    g.add_node(Hypernode(id=src_label, label=src_label))
    g.add_node(Hypernode(id=tgt_label, label=tgt_label))
    meta = Metadata(custom=custom or {})
    return Hyperedge(
        source_ids=frozenset({src_label}),
        target_ids=frozenset({tgt_label}),
        weight=weight,
        metadata=meta,
    ), g


class TestNoSelfLoopConstraint:
    def test_rejects_self_loop(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"}))
        c = NoSelfLoopConstraint()
        assert not c.is_valid(edge, g)

    def test_accepts_normal_edge(self):
        edge, g = _make_edge("a", "b")
        c = NoSelfLoopConstraint()
        assert c.is_valid(edge, g)

    def test_check_returns_reason(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"}))
        c = NoSelfLoopConstraint()
        reason = c.check(edge, g)
        assert reason is not None
        assert "self-loop" in reason

    def test_check_returns_none_for_valid(self):
        edge, g = _make_edge("a", "b")
        c = NoSelfLoopConstraint()
        assert c.check(edge, g) is None


class TestWeightInflationConstraint:
    def test_rejects_heavy_edge(self):
        edge, g = _make_edge("a", "b", weight=200.0)
        c = WeightInflationConstraint(max_weight=100.0)
        assert not c.is_valid(edge, g)

    def test_accepts_normal_weight(self):
        edge, g = _make_edge("a", "b", weight=50.0)
        c = WeightInflationConstraint(max_weight=100.0)
        assert c.is_valid(edge, g)

    def test_rejects_outlier_weight(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        existing = Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            weight=1.0,
        )
        g.add_edge(existing)
        inflated = Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            weight=50.0,
        )
        c = WeightInflationConstraint(max_weight=100.0, growth_factor=3.0)
        assert not c.is_valid(inflated, g)


class TestProvenanceDepthConstraint:
    def test_rejects_deep_edge(self):
        edge, g = _make_edge("a", "b", custom={"provenance_depth": 15})
        c = ProvenanceDepthConstraint(max_depth=10)
        assert not c.is_valid(edge, g)

    def test_accepts_shallow_edge(self):
        edge, g = _make_edge("a", "b", custom={"provenance_depth": 5})
        c = ProvenanceDepthConstraint(max_depth=10)
        assert c.is_valid(edge, g)


class TestBoundaryNavigator:
    def test_check_edge_passes(self):
        edge, g = _make_edge("a", "b")
        nav = BoundaryNavigator()
        assert nav.check_edge(edge, g)

    def test_check_edge_fails_self_loop(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"}))
        nav = BoundaryNavigator()
        assert not nav.check_edge(edge, g)

    def test_add_constraint(self):
        nav = BoundaryNavigator()
        initial = len(nav.constraints)
        nav.add_constraint(WeightInflationConstraint(max_weight=50.0))
        assert len(nav.constraints) == initial + 1

    def test_remove_constraint(self):
        nav = BoundaryNavigator()
        nav.remove_constraint(NoSelfLoopConstraint)
        types = [type(c) for c in nav.constraints]
        assert NoSelfLoopConstraint not in types

    def test_check_edges_filters(self):
        edge_ok, g = _make_edge("a", "b")
        g.add_node(Hypernode(id="c", label="c"))
        edge_loop = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"}))
        nav = BoundaryNavigator()
        result = nav.check_edges([edge_ok, edge_loop], g)
        assert len(result) == 1
        assert result[0] is edge_ok

    def test_validate_edge_returns_violations(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"}))
        nav = BoundaryNavigator()
        violations = nav.validate_edge(edge, g)
        assert len(violations) > 0
        assert any("self-loop" in v for v in violations)

    def test_validate_and_filter(self):
        edge_ok, g = _make_edge("a", "b")
        g.add_node(Hypernode(id="c", label="c"))
        edge_loop = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"}))
        nav = BoundaryNavigator()
        valid, rejected = nav.validate_and_filter([edge_ok, edge_loop], g)
        assert len(valid) == 1
        assert len(rejected) == 1


class TestBoundaryNavigatorIntegration:
    def test_relate_respects_constraints(self):
        mem = HypergraphMemory(evolve_interval=0)
        from hyper3.constraints import BoundaryNavigator
        from hyper3.exceptions import ConstraintViolationError
        mem._boundary_navigator = BoundaryNavigator()
        mem.store("a")
        with pytest.raises(ConstraintViolationError):
            mem.relate("a", "a")

    def test_relate_allows_valid_edge(self):
        mem = HypergraphMemory(evolve_interval=0)
        from hyper3.constraints import BoundaryNavigator
        mem._boundary_navigator = BoundaryNavigator()
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b")
        assert edge is not None
