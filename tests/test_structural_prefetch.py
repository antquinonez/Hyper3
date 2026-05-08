from __future__ import annotations

import pytest

from hyper3.cache import LazyCache
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.structural_prefetch import PrefetchConfig, PrefetchStats, StructuralPrefetchEngine


def _make_engine(**config_kw) -> tuple[Hypergraph, LazyCache, StructuralPrefetchEngine]:
    g = Hypergraph()
    c = LazyCache()
    cfg = PrefetchConfig(**config_kw) if config_kw else None
    e = StructuralPrefetchEngine(g, c, cfg)
    return g, c, e


class TestConstruction:
    def test_default_config(self):
        _, _, e = _make_engine()
        assert e._config.enabled is True

    def test_stats_initial(self):
        _, _, e = _make_engine()
        s = e.stats()
        assert s.prefetches_attempted == 0


class TestOnAccess:
    def test_no_edges(self):
        g, _, e = _make_engine()
        n = Hypernode(label="x")
        g.add_node(n)
        assert e.on_access(n.id) == 0

    def test_prefetches_neighbors(self):
        g, c, e = _make_engine()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="e",
            weight=1.0,
        ))
        added = e.on_access(a.id)
        assert added == 1
        assert c.get(f"node:{b.id}") is not None

    def test_respects_max_neighbors(self):
        g, c, e = _make_engine(max_neighbors=2)
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(5):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({n.id}),
                label="e",
                weight=1.0,
            ))
        added = e.on_access(hub.id)
        assert added <= 2

    def test_respects_min_weight(self):
        g, c, e = _make_engine(min_weight=0.5)
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="e",
            weight=0.2,
        ))
        assert e.on_access(a.id) == 0

    def test_already_cached_is_hit(self):
        g, c, e = _make_engine()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="e",
            weight=1.0,
        ))
        c.put(f"node:{b.id}", b.id)
        added = e.on_access(a.id)
        assert added == 0
        assert e.stats().prefetches_hit == 1

    def test_disabled(self):
        g, c, e = _make_engine(enabled=False)
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="e",
            weight=1.0,
        ))
        assert e.on_access(a.id) == 0

    def test_node_not_in_graph(self):
        g, _, e = _make_engine()
        assert e.on_access("nonexistent") == 0


class TestStats:
    def test_counters_after_multiple(self):
        g, c, e = _make_engine()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        d = Hypernode(label="d")
        g.add_node(a)
        g.add_node(b)
        g.add_node(d)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="e",
            weight=1.0,
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({d.id}),
            label="e",
            weight=1.0,
        ))
        e.on_access(a.id)
        s = e.stats()
        assert s.nodes_scanned == 1
        assert s.prefetches_added == 2

    def test_reset_stats(self):
        g, c, e = _make_engine()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="e",
            weight=1.0,
        ))
        e.on_access(a.id)
        e.reset_stats()
        s = e.stats()
        assert s.prefetches_attempted == 0
        assert s.prefetches_hit == 0
        assert s.prefetches_added == 0
        assert s.nodes_scanned == 0


class TestBracketAccess:
    def test_prefetch_config(self):
        cfg = PrefetchConfig(max_neighbors=5)
        assert cfg["max_neighbors"] == 5

    def test_prefetch_stats(self):
        s = PrefetchStats(prefetches_added=10)
        assert s["prefetches_added"] == 10
