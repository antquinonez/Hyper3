from __future__ import annotations

import pytest

from hyper3.invariant_detector import InvariantDetector, InvariantReport, PropertyInvariant
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def _make_engine(**kw) -> tuple[Hypergraph, InvariantDetector]:
    g = Hypergraph()
    d = InvariantDetector(g, **kw)
    return g, d


class TestConstruction:
    def test_default_frames(self):
        _, d = _make_engine()
        assert d._frame_names == ["classical", "quantum", "hypergraph", "probabilistic"]

    def test_custom_frames(self):
        _, d = _make_engine(frame_names=["a", "b"])
        assert d._frame_names == ["a", "b"]


class TestDetect:
    def test_node_not_found(self):
        g, d = _make_engine()
        report = d.detect("nonexistent")
        assert report.concept_id == "nonexistent"
        assert report.concept == ""
        assert report.total_properties == 0

    def test_single_node_no_edges(self):
        g, d = _make_engine()
        n = Hypernode(label="x")
        g.add_node(n)
        report = d.detect(n.id)
        assert report.concept == "x"
        assert report.total_properties == 4
        assert report.robustness_score == 1.0

    def test_hub_node(self):
        g, d = _make_engine(frame_names=["classical"])
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(5):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({n.id}),
                label="connects",
            ))
        report = d.detect(hub.id)
        degree_inv = next(p for p in report.property_invariants if p.property_name == "degree_rank")
        assert degree_inv.values["classical"] == "high"
        hub_inv = next(p for p in report.property_invariants if p.property_name == "is_hub")
        assert hub_inv.values["classical"] is True

    def test_leaf_node(self):
        g, d = _make_engine(frame_names=["classical"])
        hub = Hypernode(label="hub")
        leaf = Hypernode(label="leaf")
        g.add_node(hub)
        g.add_node(leaf)
        for i in range(3):
            n = Hypernode(label=f"filler{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({n.id}),
                label="connects",
            ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({hub.id}),
            target_ids=frozenset({leaf.id}),
            label="connects",
        ))
        report = d.detect(leaf.id)
        leaf_inv = next(p for p in report.property_invariants if p.property_name == "is_leaf")
        assert leaf_inv.values["classical"] is True

    def test_robustness_score(self):
        g, d = _make_engine(frame_names=["classical"])
        n = Hypernode(label="x")
        g.add_node(n)
        report = d.detect(n.id)
        assert report.robustness_score == 1.0
        assert report.invariant_count == report.total_properties

    def test_all_invariant_trivially(self):
        g, d = _make_engine(frame_names=["a", "b", "c"])
        n = Hypernode(label="x")
        g.add_node(n)
        report = d.detect(n.id)
        for p in report.property_invariants:
            assert p.is_invariant
            assert p.variance == 0.0


class TestDetectBatch:
    def test_multiple_concepts(self):
        g, d = _make_engine(frame_names=["classical"])
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        reports = d.detect_batch([n1.id, n2.id])
        assert len(reports) == 2


class TestBracketAccess:
    def test_property_invariant(self):
        p = PropertyInvariant(property_name="deg", is_invariant=True, values={"a": "high"}, variance=0.0)
        assert p["property_name"] == "deg"

    def test_invariant_report(self):
        r = InvariantReport(concept="x", concept_id="id", robustness_score=1.0)
        assert r["concept"] == "x"
        assert r["robustness_score"] == 1.0


class TestFrameSpecificDegree:
    def test_quantum_frame_excludes_low_weight_edges(self):
        g, d = _make_engine()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(5):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({n.id}),
                label="e",
                weight=0.3 + i * 0.2,
            ))
        deg_classical, _ = d._frame_degree(hub.id, "classical")
        deg_quantum, _ = d._frame_degree(hub.id, "quantum")
        assert deg_classical == 5.0
        assert deg_quantum == 4.0

    def test_hypergraph_frame_excludes_binary_edges(self):
        g, d = _make_engine()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(
            source_ids=frozenset({hub.id}),
            target_ids=frozenset({a.id}),
            label="binary",
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({hub.id, a.id}),
            target_ids=frozenset({b.id}),
            label="hyper",
        ))
        deg_h, _ = d._frame_degree(hub.id, "hypergraph")
        assert deg_h == 1.0

    def test_probabilistic_frame_returns_weighted_degree(self):
        g, d = _make_engine()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for w in [0.5, 1.0, 2.0]:
            n = Hypernode(label=f"n_{w}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({n.id}),
                label="e",
                weight=w,
            ))
        deg_p, _ = d._frame_degree(hub.id, "probabilistic")
        assert deg_p == 3.5

    def test_different_frames_can_disagree_on_hub_status(self):
        g, d = _make_engine()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(4):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({n.id}),
                label="e",
                weight=0.1,
            ))
        report = d.detect(hub.id)
        hub_inv = next(p for p in report.property_invariants if p.property_name == "is_hub")
        assert hub_inv.values["classical"] is True
        assert hub_inv.values["quantum"] is False


class TestBucketBoundaries:
    def test_low_boundary(self):
        from hyper3.invariant_detector import _bucket
        assert _bucket(0.0) == "low"
        assert _bucket(0.29) == "low"

    def test_medium_boundary(self):
        from hyper3.invariant_detector import _bucket
        assert _bucket(0.30) == "medium"
        assert _bucket(0.70) == "medium"

    def test_high_boundary(self):
        from hyper3.invariant_detector import _bucket
        assert _bucket(0.71) == "high"


class TestCheckInvariantVariance:
    def test_non_invariant_computes_variance(self):
        g, d = _make_engine(frame_names=["frame_a", "frame_b"])
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(4):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({n.id}),
                label="e",
                weight=0.1,
            ))
        report = d.detect(hub.id)
        hub_inv = next(p for p in report.property_invariants if p.property_name == "is_hub")
        if not hub_inv.is_invariant:
            assert 0.0 < hub_inv.variance <= 1.0
        else:
            assert hub_inv.variance == 0.0
