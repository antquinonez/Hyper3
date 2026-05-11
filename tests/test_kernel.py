import time

import numpy as np
import pytest

from hyper3 import (
    AbstractionLayer,
    EquivalenceEngine,
    EventLog,
    GraphMaintenanceEngine,
    Hyperedge,
    Hypergraph,
    Hypernode,
    LazyCache,
    Metadata,
    Modality,
    ObserverSlice,
    TraversalEngine,
)
from hyper3.memory import HypergraphMemory
from hyper3.multiway import MultiwayEngine, MultiwayGraph, MultiwayState
from hyper3.multiway_causal import StateConvergenceEngine
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.rules import TransitiveRule


class TestAbstractionLayerEnum:
    def test_three_members(self):
        members = list(AbstractionLayer)
        assert len(members) == 3

    def test_member_values(self):
        assert AbstractionLayer.DETAIL.value == "detail"
        assert AbstractionLayer.INTERMEDIATE.value == "intermediate"
        assert AbstractionLayer.SUMMARY.value == "summary"

    def test_lookup_by_value(self):
        assert AbstractionLayer("detail") is AbstractionLayer.DETAIL
        assert AbstractionLayer("summary") is AbstractionLayer.SUMMARY

    def test_ordering_from_detail_to_summary(self):
        names = [m.value for m in AbstractionLayer]
        assert names.index("detail") < names.index("intermediate") < names.index("summary")


class TestModalityEnum:
    def test_six_members(self):
        members = list(Modality)
        assert len(members) == 6

    def test_member_values_are_strings(self):
        assert {m.value for m in Modality} == {"textual", "conceptual", "temporal", "convergence", "sensory", "abstract"}

    def test_lookup_by_value(self):
        assert Modality("textual") is Modality.TEXTUAL
        assert Modality("convergence") is Modality.CAUSAL


class TestHypernode:
    def test_default_creation(self):
        node = Hypernode()
        assert len(node.id) == 32
        assert node.label == ""
        assert node.data is None
        assert node.access_count == 0
        assert node.weight == 1.0

    def test_custom_creation(self):
        meta = Metadata(
            modality_tags={Modality.CONCEPTUAL},
            abstraction_layer=AbstractionLayer.DETAIL,
        )
        node = Hypernode(label="test", data={"key": "val"}, metadata=meta)
        assert node.label == "test"
        assert node.data == {"key": "val"}
        assert Modality.CONCEPTUAL in node.metadata.modality_tags

    def test_touch_updates_access(self):
        node = Hypernode()
        now = time.time()
        node.touch(now)
        assert node.access_count == 1
        assert node.last_accessed == now
        node.touch(now + 1)
        assert node.access_count == 2

    def test_is_active(self):
        node = Hypernode()
        assert not node.is_active
        node.touch(time.time())
        assert node.is_active

    def test_matches_identical(self):
        a = Hypernode(data="hello")
        b = Hypernode(data="hello")
        assert a.matches(b) == 1.0

    def test_matches_different(self):
        a = Hypernode(data="hello")
        b = Hypernode(data="world")
        assert a.matches(b) == 0.0

    def test_matches_none_data(self):
        a = Hypernode(data=None)
        b = Hypernode(data="hello")
        assert a.matches(b) == 0.0

    def test_matches_dict_partial(self):
        a = Hypernode(data={"x": 1, "y": 2, "z": 3})
        b = Hypernode(data={"x": 1, "y": 2, "z": 99})
        assert a.matches(b) == pytest.approx(2 / 3)

    def test_matches_dict_no_overlap(self):
        a = Hypernode(data={"a": 1})
        b = Hypernode(data={"b": 1})
        assert a.matches(b) == 0.0


class TestHyperedge:
    def test_default_creation(self):
        edge = Hyperedge()
        assert len(edge.id) == 32
        assert edge.source_ids == frozenset()
        assert edge.target_ids == frozenset()

    def test_node_ids(self):
        edge = Hyperedge(
            source_ids=frozenset({"a", "b"}),
            target_ids=frozenset({"c"}),
        )
        assert edge.node_ids == frozenset({"a", "b", "c"})

    def test_directed_edge(self):
        edge = Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            label="causes",
        )
        assert edge.source_ids == frozenset({"a"})
        assert edge.target_ids == frozenset({"b"})
        assert edge.label == "causes"

    def test_hyperedge_multi_source(self):
        edge = Hyperedge(
            source_ids=frozenset({"a", "b", "c"}),
            target_ids=frozenset({"d"}),
        )
        assert len(edge.source_ids) == 3
        assert len(edge.target_ids) == 1


class TestHypergraph:
    def test_add_node(self):
        g = Hypergraph()
        node = Hypernode(label="x")
        result = g.add_node(node)
        assert result is node
        assert g.node_count == 1

    def test_add_duplicate_node(self):
        g = Hypergraph()
        node = Hypernode(id="abc", label="x")
        g.add_node(node)
        result = g.add_node(node)
        assert result is node
        assert g.node_count == 1

    def test_get_node(self):
        g = Hypergraph()
        node = Hypernode(id="n1")
        g.add_node(node)
        assert g.get_node("n1") is node
        assert g.get_node("missing") is None

    def test_remove_node(self):
        g = Hypergraph()
        node = Hypernode(id="n1")
        g.add_node(node)
        assert g.remove_node("n1") is True
        assert g.node_count == 0
        assert g.remove_node("n1") is False

    def test_remove_node_cascades_edges(self):
        g = Hypergraph()
        a = Hypernode(id="a")
        b = Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}))
        g.add_edge(edge)
        g.remove_node("a")
        assert g.edge_count == 0

    def test_add_edge(self):
        g = Hypergraph()
        a = Hypernode(id="a")
        b = Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}))
        result = g.add_edge(edge)
        assert result is edge
        assert g.edge_count == 1

    def test_add_edge_missing_node_raises(self):
        g = Hypergraph()
        edge = Hyperedge(source_ids=frozenset({"missing"}), target_ids=frozenset())
        with pytest.raises(ValueError, match="not found"):
            g.add_edge(edge)

    def test_remove_edge(self):
        g = Hypergraph()
        a = Hypernode(id="a")
        b = Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        edge = Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}))
        g.add_edge(edge)
        assert g.remove_edge("e1") is True
        assert g.edge_count == 0
        assert g.remove_edge("e1") is False

    def test_edges_for(self):
        g = Hypergraph()
        a = Hypernode(id="a")
        b = Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        e1 = Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}))
        e2 = Hyperedge(id="e2", source_ids=frozenset({"b"}), target_ids=frozenset({"a"}))
        g.add_edge(e1)
        g.add_edge(e2)
        assert len(g.incident_edges("a")) == 2

    def test_neighbors(self):
        g = Hypergraph()
        a = Hypernode(id="a")
        b = Hypernode(id="b")
        c = Hypernode(id="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        neighbors = g.neighbors("a")
        assert set(neighbors) == {"b", "c"}

    def test_query_dimension(self):
        g = Hypergraph()
        n1 = Hypernode(id="n1", metadata=Metadata(modality_tags={Modality.CONCEPTUAL}))
        n2 = Hypernode(id="n2", metadata=Metadata(modality_tags={Modality.TEMPORAL}))
        g.add_node(n1)
        g.add_node(n2)
        result = g.query_dimension(Modality.CONCEPTUAL)
        assert len(result) == 1
        assert result[0].id == "n1"

    def test_merge_node(self):
        g = Hypergraph()
        primary = Hypernode(id="p", label="alpha", data={"x": 1}, access_count=5, weight=1.5)
        secondary = Hypernode(id="s", label="beta", data={"x": 1}, access_count=3, weight=2.0)
        g.add_node(primary)
        g.add_node(secondary)
        result = g.merge_node("p", "s")
        assert result is primary
        assert primary.access_count == 8
        assert primary.weight == 2.0
        assert "beta" in primary.metadata.custom["aliases"]
        assert g.node_count == 1
        assert g.get_node("s") is None

    def test_merge_node_rewires_edges(self):
        g = Hypergraph()
        p = Hypernode(id="p")
        s = Hypernode(id="s")
        target = Hypernode(id="t")
        g.add_node(p)
        g.add_node(s)
        g.add_node(target)
        edge = Hyperedge(
            id="e1",
            source_ids=frozenset({"s"}),
            target_ids=frozenset({"t"}),
        )
        g.add_edge(edge)
        g.merge_node("p", "s")
        assert "p" in edge.source_ids
        assert "s" not in edge.source_ids
        assert g.edge_count == 1
        assert g.get_edge("e1") is not None
        assert "p" in g.get_edge("e1").source_ids

    def test_nodes_and_edges_properties(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        assert len(g.nodes) == 2
        assert len(g.edges) == 1


class TestEventLog:
    def test_record(self):
        log = EventLog()
        entry = log.record("node_created", node_id="abc")
        assert entry["event_type"] == "node_created"
        assert entry["details"]["node_id"] == "abc"
        assert entry["timestamp"] > 0

    def test_query_by_type(self):
        log = EventLog()
        log.record("node_created", node_id="a")
        log.record("edge_created", edge_id="e1")
        log.record("node_created", node_id="b")
        results = log.query(event_type="node_created")
        assert len(results) == 2

    def test_query_since(self):
        log = EventLog()
        log.record("first")
        cutoff = time.time()
        log.record("second")
        results = log.query(since=cutoff)
        assert len(results) == 1
        assert results[0]["event_type"] == "second"

    def test_query_with_limit(self):
        log = EventLog()
        for i in range(10):
            log.record("event", idx=i)
        results = log.query(limit=3)
        assert len(results) == 3

    def test_size(self):
        log = EventLog()
        assert log.size == 0
        log.record("x")
        assert log.size == 1


class TestEquivalenceEngine:
    def _make_graph_with_duplicates(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", data="hello"))
        g.add_node(Hypernode(id="b", data="hello"))
        g.add_node(Hypernode(id="c", data="world"))
        return g

    def test_find_equivalences(self):
        g = self._make_graph_with_duplicates()
        engine = EquivalenceEngine(g, threshold=0.8)
        pairs = engine.find_equivalences()
        assert len(pairs) == 1
        id1, id2, score = pairs[0]
        assert {id1, id2} == {"a", "b"}
        assert score == 1.0

    def test_merge_equivalences(self):
        g = self._make_graph_with_duplicates()
        engine = EquivalenceEngine(g, threshold=0.8)
        merged = engine.merge_equivalences()
        assert len(merged) == 1
        assert g.node_count == 2

    def test_no_false_positives(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", data="cat"))
        g.add_node(Hypernode(id="b", data="dog"))
        engine = EquivalenceEngine(g, threshold=0.8)
        assert engine.find_equivalences() == []


class TestLazyCache:
    def test_put_and_get(self):
        cache = LazyCache()
        cache.put("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing(self):
        cache = LazyCache()
        assert cache.get("missing") is None

    def test_ttl_expiration(self):
        cache = LazyCache(ttl=0.01)
        cache.put("key", "value")
        time.sleep(0.02)
        assert cache.get("key") is None

    def test_max_size_eviction(self):
        cache = LazyCache(max_size=3)
        for i in range(5):
            cache.put(f"key{i}", i)
        assert cache.size == 3
        assert cache.get("key0") is None
        assert cache.get("key4") is not None

    def test_invalidate(self):
        cache = LazyCache()
        cache.put("key", "val")
        assert cache.invalidate("key")
        assert cache.get("key") is None
        assert not cache.invalidate("key")

    def test_clear(self):
        cache = LazyCache()
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size == 0

    def test_evict_expired(self):
        cache = LazyCache(ttl=0.01)
        cache.put("a", 1)
        cache.put("b", 2)
        time.sleep(0.02)
        evicted = cache.evict_expired()
        assert evicted == 2
        assert cache.size == 0

    def test_lru_ordering(self):
        cache = LazyCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3


class TestTraversalEngine:
    def _build_graph(self):
        g = Hypergraph()
        for label in ["root", "a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"root"}), target_ids=frozenset({"a"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"root"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"d"})))
        return g

    def test_bfs(self):
        g = self._build_graph()
        engine = TraversalEngine(g)
        result = engine.traverse_breadth_first("root", max_depth=3)
        labels = {n.label for n in result}
        assert labels == {"root", "a", "b", "c", "d"}

    def test_bfs_max_depth(self):
        g = self._build_graph()
        engine = TraversalEngine(g)
        result = engine.traverse_breadth_first("root", max_depth=1)
        labels = {n.label for n in result}
        assert "root" in labels
        assert "c" not in labels

    def test_bfs_max_nodes(self):
        g = self._build_graph()
        engine = TraversalEngine(g)
        result = engine.traverse_breadth_first("root", max_nodes=3)
        assert len(result) == 3

    def test_dfs(self):
        g = self._build_graph()
        engine = TraversalEngine(g)
        result = engine.traverse_depth_first("root", max_depth=3)
        labels = {n.label for n in result}
        assert labels == {"root", "a", "b", "c", "d"}

    def test_dfs_max_depth(self):
        g = self._build_graph()
        engine = TraversalEngine(g)
        result = engine.traverse_depth_first("root", max_depth=1)
        assert len(result) == 3

    def test_traverse_dimension(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", metadata=Metadata(modality_tags={Modality.CONCEPTUAL})))
        g.add_node(Hypernode(id="b", metadata=Metadata(modality_tags={Modality.TEMPORAL})))
        g.add_node(Hypernode(id="c", metadata=Metadata(modality_tags={Modality.CONCEPTUAL})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"})))
        engine = TraversalEngine(g)
        result = engine.traverse_dimension("a", Modality.CONCEPTUAL, max_depth=3)
        ids = {n.id for n in result}
        assert "a" in ids
        assert "b" not in ids
        assert "c" in ids

    def test_traverse_touches_nodes(self):
        g = self._build_graph()
        engine = TraversalEngine(g)
        engine.traverse_breadth_first("root")
        root = g.get_node("root")
        assert root.access_count == 1


class TestObserverSlice:
    def _build_graph(self):
        g = Hypergraph()
        for label in ["root", "a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label, weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({"root"}), target_ids=frozenset({"a"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"root"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        return g

    def test_narrow(self):
        g = self._build_graph()
        obs = ObserverSlice(g)
        result = obs.narrow("root", max_depth=1, max_nodes=5)
        assert {n.id for n in result} == {"root"}

    def test_broaden(self):
        g = self._build_graph()
        obs = ObserverSlice(g)
        result = obs.broaden("root", max_depth=5, max_nodes=100)
        assert len(result) == 4

    def test_filter_by_modality(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", metadata=Metadata(modality_tags={Modality.CONCEPTUAL})))
        g.add_node(Hypernode(id="b", metadata=Metadata(modality_tags={Modality.TEMPORAL})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        obs = ObserverSlice(g)
        obs.configure(modalities={Modality.CONCEPTUAL})
        result = obs.apply("a")
        ids = {n.id for n in result}
        assert "a" in ids
        assert "b" not in ids

    def test_filter_by_weight(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", weight=1.0))
        g.add_node(Hypernode(id="b", weight=0.01))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        obs = ObserverSlice(g)
        obs.configure(min_weight=0.5)
        result = obs.apply("a")
        ids = {n.id for n in result}
        assert "a" in ids
        assert "b" not in ids


class TestGraphMaintenanceEngine:
    def _build_graph(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", data="x", weight=1.0))
        g.add_node(Hypernode(id="b", data="x", weight=0.8))
        g.add_node(Hypernode(id="c", data="z", weight=0.05, access_count=0))
        g.add_node(Hypernode(id="d", data="w", weight=0.5))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"})))
        return g

    def test_decay_weights(self):
        g = self._build_graph()
        engine = GraphMaintenanceEngine(g, decay_threshold=0.1)
        engine.decay_weights(factor=0.5)
        a = g.get_node("a")
        assert a.weight == pytest.approx(0.5)

    def test_prune_dead_nodes(self):
        g = self._build_graph()
        engine = GraphMaintenanceEngine(g, decay_threshold=0.1)
        g.get_node("c").weight = 0.05
        pruned = engine.prune_dead_nodes()
        assert "c" in pruned
        assert g.node_count == 3

    def test_merge_equivalences(self):
        g = self._build_graph()
        engine = GraphMaintenanceEngine(g, merge_threshold=0.8)
        merged = engine.merge_equivalences()
        assert len(merged) == 1

    def test_reinforce(self):
        g = self._build_graph()
        engine = GraphMaintenanceEngine(g)
        engine.reinforce("a", boost=2.0)
        assert g.get_node("a").weight == 2.0

    def test_evolve(self):
        g = self._build_graph()
        engine = GraphMaintenanceEngine(g, decay_threshold=0.1)
        report = engine.evolve()
        assert report["decayed"] == 0
        assert report["pruned"] == 1
        assert report["merged"] == 1
        assert report["node_count"] == 2

    def test_metrics_accumulate(self):
        g = self._build_graph()
        engine = GraphMaintenanceEngine(g)
        engine.evolve()
        engine.evolve()
        assert engine.metrics.total_refinements == 2




class TestHypernodeMatchesScalar:
    def test_matches_bool_data(self):
        a = Hypernode(data=True)
        b = Hypernode(data=True)
        assert a.matches(b) == 1.0

    def test_matches_int_data(self):
        a = Hypernode(data=42)
        b = Hypernode(data=42)
        assert a.matches(b) == 1.0

    def test_matches_different_scalars(self):
        a = Hypernode(data=42)
        b = Hypernode(data=99)
        assert a.matches(b) == 0.0


class TestBatchMode:
    def test_batch_mode_add_node(self):
        g = Hypergraph()
        g.begin_batch()
        g.add_node(Hypernode(id="a", label="a"))
        assert g._neighbor_cache is None
        assert g._cache_invalidated_in_batch is True
        g.end_batch()
        assert g._batch_mode is False
        assert g._neighbor_cache is None

    def test_batch_mode_no_invalidation(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g._neighbor_cache = {"a": []}
        g.begin_batch()
        assert not g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache == {"a": []}

    def test_batch_mode_add_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.begin_batch()
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        assert g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache is None

    def test_batch_mode_remove_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.begin_batch()
        g.remove_node("a")
        assert g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache is None

    def test_batch_mode_remove_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.begin_batch()
        g.remove_edge("e1")
        assert g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache is None


class TestFindPaths:
    def test_find_paths_missing_source(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="b"))
        assert g.find_paths("missing", "b") == []

    def test_find_paths_missing_target(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        assert g.find_paths("a", "missing") == []

    def test_find_paths_max_depth_exceeded(self):
        g = Hypergraph()
        for lbl in "abcde":
            g.add_node(Hypernode(id=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"d"}), target_ids=frozenset({"e"})))
        paths = g.find_paths("a", "e", max_depth=2)
        assert paths == []

    def test_find_paths_max_paths(self):
        g = Hypergraph()
        for lbl in "abcdef":
            g.add_node(Hypernode(id=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"d"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"})))
        paths = g.find_paths("a", "d", max_paths=1)
        assert len(paths) == 1

    def test_find_paths_with_edge_label(self):
        g = Hypergraph()
        for lbl in "abc":
            g.add_node(Hypernode(id=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="other"))
        paths = g.find_paths("a", "c", edge_label="rel")
        assert paths == []


class TestPatternMatch:
    def test_pattern_match_with_limit(self):
        g = Hypergraph()
        for i in range(20):
            g.add_node(Hypernode(id=f"n{i}", label=f"label{i}"))
            if i > 0:
                g.add_edge(Hyperedge(
                    source_ids=frozenset({f"n{i-1}"}),
                    target_ids=frozenset({f"n{i}"}),
                    label="rel",
                ))
        results = g.pattern_match(edge_label="rel", limit=5)
        assert len(results) == 5

    def test_pattern_match_source_and_target_labels(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="alpha"))
        g.add_node(Hypernode(id="b", label="beta"))
        g.add_edge(Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            label="causes",
        ))
        results = g.pattern_match(edge_label="causes", source_label="alpha", target_label="beta")
        assert len(results) == 1
        assert results[0][1]["source_label"] == "alpha"
        assert results[0][1]["target_label"] == "beta"


class TestLabeledEdges:
    def test_labeled_edges_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="alpha"))
        g.add_node(Hypernode(id="b", label="beta"))
        g.add_edge(Hyperedge(
            id="e1",
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            label="causes",
            weight=2.0,
            data={"key": "val"},
        ))
        edges = g.labeled_edges
        assert len(edges) == 1
        assert edges[0]["id"] == "e1"
        assert edges[0]["label"] == "causes"
        assert edges[0]["source_labels"] == ["alpha"]
        assert edges[0]["target_labels"] == ["beta"]
        assert edges[0]["weight"] == 2.0
        assert edges[0]["data"] == {"key": "val"}

    def test_labeled_edges_empty_graph(self):
        g = Hypergraph()
        assert g.labeled_edges == []


class TestDegreeCentrality:
    def test_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        result = g.degree_centrality()
        assert result == {"a": 1.0}

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.degree_centrality() == {}


class TestBetweennessCentralityEmpty:
    def test_empty_graph(self):
        g = Hypergraph()
        assert g.betweenness_centrality() == {}


class TestHasCycleEmpty:
    def test_empty_graph(self):
        g = Hypergraph()
        assert g.has_cycle() is False


class TestDetectCycles:
    def test_empty_graph(self):
        g = Hypergraph()
        assert g.detect_cycles() == []

    def test_max_cycles_limit(self):
        g = Hypergraph()
        for i in range(6):
            g.add_node(Hypernode(id=f"n{i}"))
            if i > 0:
                g.add_edge(Hyperedge(
                    source_ids=frozenset({f"n{i}"}),
                    target_ids=frozenset({f"n{i-1}"}),
                ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({"n0"}),
            target_ids=frozenset({"n5"}),
        ))
        cycles = g.detect_cycles(max_cycles=1)
        assert len(cycles) == 1


class TestShortestPath:
    def test_missing_nodes(self):
        g = Hypergraph()
        assert g.shortest_path("a", "b") is None

    def test_unweighted(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        path = g.shortest_path("a", "b", weighted=False)
        assert path == ["a", "b"]


class TestMergeNode:
    def test_merge_missing_primary(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="s"))
        assert g.merge_node("missing", "s") is None

    def test_merge_missing_secondary(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="p"))
        assert g.merge_node("p", "missing") is None

    def test_merge_transfers_modality_tags(self):
        g = Hypergraph()
        p = Hypernode(id="p", label="primary", metadata=Metadata(modality_tags={Modality.CONCEPTUAL}))
        s = Hypernode(id="s", label="secondary", metadata=Metadata(modality_tags={Modality.TEMPORAL}))
        g.add_node(p)
        g.add_node(s)
        g.merge_node("p", "s")
        assert Modality.TEMPORAL in p.metadata.modality_tags
        assert Modality.CONCEPTUAL in p.metadata.modality_tags

    def test_merge_same_label_no_alias(self):
        g = Hypergraph()
        p = Hypernode(id="p", label="same")
        s = Hypernode(id="s", label="same")
        g.add_node(p)
        g.add_node(s)
        g.merge_node("p", "s")
        assert "aliases" not in p.metadata.custom


class TestDirectedEdgeAccessors:
    def test_outgoing_edges(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="out"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="in"))
        out = g.outgoing_edges("a")
        assert len(out) == 1
        assert out[0].label == "out"

    def test_incoming_edges(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="out"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="in"))
        inc = g.incoming_edges("a")
        assert len(inc) == 1
        assert inc[0].label == "in"

    def test_out_neighbors(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        nbrs = g.out_neighbors("a")
        assert set(nbrs) == {"b", "c"}

    def test_in_neighbors(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"a"})))
        nbrs = g.in_neighbors("a")
        assert set(nbrs) == {"b", "c"}

    def test_out_neighbors_deduplicates(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="second"))
        nbrs = g.out_neighbors("a")
        assert nbrs == ["b"]

    def test_in_neighbors_deduplicates(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="second"))
        nbrs = g.in_neighbors("b")
        assert nbrs == ["a"]

    def test_out_neighbors_excludes_self(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"})))
        assert g.out_neighbors("a") == []

    def test_in_neighbors_excludes_self(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"})))
        assert g.in_neighbors("a") == []


class TestIncidenceMatrix:
    def test_basic_incidence(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        H, nodes, edges = g.incidence_matrix()
        assert H.shape == (2, 1)
        a_idx = nodes.index("a")
        b_idx = nodes.index("b")
        assert H[a_idx, 0] == 1.0
        assert H[b_idx, 0] == -1.0

    def test_empty_graph_incidence(self):
        g = Hypergraph()
        H, nodes, edges = g.incidence_matrix()
        assert H.shape == (0, 0)
        assert nodes == []
        assert edges == []


class TestHypergraphLaplacian:
    def test_empty_graph(self):
        g = Hypergraph()
        L = g.hypergraph_laplacian()
        assert L.shape == (0, 0)

    def test_single_node_no_edges(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        L = g.hypergraph_laplacian()
        assert L.shape == (1, 1)
        assert L[0, 0] == 0.0

    def test_two_nodes_one_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            weight=2.0,
        ))
        L = g.hypergraph_laplacian()
        assert L.shape == (2, 2)
        assert L[0, 0] == pytest.approx(1.0)
        assert L[1, 1] == pytest.approx(1.0)
        assert L[0, 1] == pytest.approx(-1.0)
        assert L[1, 0] == pytest.approx(-1.0)


class TestGetNodeByLabel:
    def test_unlabeled_node_not_in_index(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label=""))
        assert g.get_node_by_label("anything") is None

    def test_label_overwrites_previous(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="x"))
        g.add_node(Hypernode(id="b", label="x"))
        found = g.get_node_by_label("x")
        assert found.id == "b"


class TestMergeNodeEdgeRewire:
    def test_merge_creates_self_loop_edge(self):
        g = Hypergraph()
        p = Hypernode(id="p", label="p")
        s = Hypernode(id="s", label="s")
        g.add_node(p)
        g.add_node(s)
        edge = Hyperedge(
            id="e1",
            source_ids=frozenset({"s"}),
            target_ids=frozenset({"p"}),
        )
        g.add_edge(edge)
        g.merge_node("p", "s")
        assert "p" in edge.source_ids
        assert "p" in edge.target_ids


class TestNodeDegree:
    def test_node_degree(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        assert g.node_degree("a") == 2
        assert g.node_degree("b") == 1
        assert g.node_degree("c") == 1

    def test_degree_distribution(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        dist = g.degree_distribution()
        assert dist[2] == 1
        assert dist[1] == 2


"""Tests for hypergraph-native algorithms and n-ary edge support."""





def _make_graph_with_edges():
    g = Hypergraph()
    a = Hypernode(label="A")
    b = Hypernode(label="B")
    c = Hypernode(label="C")
    d = Hypernode(label="D")
    for n in [a, b, c, d]:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=2.0))
    g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="rel", weight=3.0))
    g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({d.id}), label="rel", weight=1.0))
    return g, a, b, c, d


def _make_hyperedge_graph():
    g = Hypergraph()
    a = Hypernode(label="A")
    b = Hypernode(label="B")
    c = Hypernode(label="C")
    d = Hypernode(label="D")
    e = Hypernode(label="E")
    for n in [a, b, c, d, e]:
        g.add_node(n)
    g.add_edge(Hyperedge(
        source_ids=frozenset({a.id, b.id}),
        target_ids=frozenset({c.id, d.id}),
        label="joint_produces",
        weight=2.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({c.id}),
        target_ids=frozenset({e.id}),
        label="leads_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({d.id, e.id}),
        target_ids=frozenset({a.id}),
        label="feeds_back",
        weight=1.5,
    ))
    return g, a, b, c, d, e


class TestNaryEdgeCreation:
    def test_create_and_query_hyperedge(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        hyperedges = [edge for edge in g.edges if len(edge.source_ids) > 1 or len(edge.target_ids) > 1]
        assert len(hyperedges) == 2
        joint = next(e for e in hyperedges if e.label == "joint_produces")
        assert joint.source_ids == frozenset({a.id, b.id})
        assert joint.target_ids == frozenset({c.id, d.id})

    def test_link_hyper_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("gene_a")
        mem.add("gene_b")
        mem.add("protein_complex")
        mem.add("pathway")
        edge = mem.link_hyper(
            {"gene_a", "gene_b"},
            {"protein_complex", "pathway"},
            label="jointly_encodes",
            weight=5.0,
        )
        assert edge.weight == 5.0
        assert len(edge.source_ids) == 2
        assert len(edge.target_ids) == 2
        assert edge.label == "jointly_encodes"

    def test_query_hyperedges_by_cardinality(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.add("z")
        mem.link("x", "y", label="pair")
        mem.link_hyper({"x", "y"}, {"z"}, label="nary")

        pairwise = mem.query_hyperedges(min_source_cardinality=1, min_target_cardinality=1)
        assert len(pairwise) == 2

        nary_only = mem.query_hyperedges(min_source_cardinality=2)
        assert len(nary_only) == 1
        assert nary_only[0].label == "nary"

    def test_query_hyperedges_by_containing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link_hyper({"a", "b"}, {"c"}, label="abc")
        mem.link("a", "b", label="ab")

        edges_with_a = mem.query_hyperedges(containing="a")
        assert len(edges_with_a) == 2

        edges_with_c = mem.query_hyperedges(containing="c")
        assert len(edges_with_c) == 1
        assert edges_with_c[0].label == "abc"

    def test_hyperedge_neighbors(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        nbrs = g.hyperedge_neighbors(a.id)
        assert b.id in nbrs
        assert c.id in nbrs
        assert d.id in nbrs
        assert len(nbrs[b.id]) == 1
        assert len(nbrs[c.id]) == 1

    def test_hyperedge_neighbors_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link_hyper({"a", "b"}, {"c"}, label="joint")
        nbrs = mem.hyperedge_neighbors("a")
        assert "b" in nbrs
        assert "c" in nbrs


class TestStar:
    def test_star_returns_incident_edges(self):
        g, a, b, c, d = _make_graph_with_edges()
        edges = g.star(b.id)
        assert len(edges) == 2
        labels = {e.label for e in edges}
        assert labels == {"rel"}

    def test_star_empty_for_unknown(self):
        g = Hypergraph()
        assert g.star("nonexistent") == []


class TestHyperedgeCocoverage:
    def test_cocoverage_counts(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        cov = g.hyperedge_cocoverage(a.id)
        assert cov[b.id] == 1
        assert cov[c.id] == 1
        assert cov[d.id] == 2
        assert cov[e.id] == 1


class TestConnectedComponents:
    def test_pairwise_components(self):
        g, a, b, c, d = _make_graph_with_edges()
        comps = g.connected_components()
        assert len(comps) == 1
        assert {a.id, b.id, c.id, d.id} == comps[0]

    def test_disconnected_components(self):
        g = Hypergraph()
        a, b, c, d = Hypernode(label="A"), Hypernode(label="B"), Hypernode(label="C"), Hypernode(label="D")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        comps = g.connected_components()
        assert len(comps) == 3
        sizes = sorted(len(c) for c in comps)
        assert sizes == [1, 1, 2]

    def test_hyperedge_connects_all_members(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        comps = g.connected_components()
        assert len(comps) == 1
        assert {a.id, b.id, c.id, d.id, e.id} == comps[0]

    def test_s_components_high_s_splits(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        comps_s1 = g.connected_components(s=1)
        assert len(comps_s1) == 1
        comps_s3 = g.connected_components(s=3)
        assert len(comps_s3) == 3


class TestShortestPathHypergraph:
    def test_pairwise_shortest_path(self):
        g, a, b, c, d = _make_graph_with_edges()
        path = g.shortest_path(a.id, d.id, weighted=False)
        assert path is not None
        assert path[0] == a.id
        assert path[-1] == d.id
        assert len(path) == 4

    def test_no_path(self):
        g = Hypergraph()
        a, b = Hypernode(label="A"), Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        assert g.shortest_path(a.id, b.id) is None

    def test_weighted_shortest_path(self):
        g, a, b, c, d = _make_graph_with_edges()
        path = g.shortest_path(a.id, d.id, weighted=True)
        assert path is not None
        assert path[0] == a.id
        assert path[-1] == d.id

    def test_hyperedge_shortest_path(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        path = g.shortest_path(a.id, e.id, weighted=False)
        assert path is not None
        assert path[0] == a.id
        assert path[-1] == e.id

    def test_same_node(self):
        g, a, *_ = _make_graph_with_edges()
        path = g.shortest_path(a.id, a.id)
        assert path == [a.id]

    def test_dijkstra_stale_heap_entry(self):
        g = Hypergraph()
        n0 = Hypernode(label="n0")
        n1 = Hypernode(label="n1")
        n2 = Hypernode(label="n2")
        n3 = Hypernode(label="n3")
        for n in [n0, n1, n2, n3]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n0.id}), target_ids=frozenset({n1.id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({n0.id}), target_ids=frozenset({n2.id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({n1.id}), target_ids=frozenset({n3.id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({n2.id}), target_ids=frozenset({n3.id}), weight=100.0))
        path = g.shortest_path(n0.id, n3.id, weighted=True)
        assert path is not None
        assert path == [n0.id, n2.id, n3.id]


class TestCycleDetection:
    def test_no_cycle(self):
        g, a, b, c, d = _make_graph_with_edges()
        assert g.has_cycle() is False

    def test_detect_cycle(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="A"), Hypernode(label="B"), Hypernode(label="C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({a.id})))
        assert g.has_cycle() is True

    def test_detect_cycles_returns_list(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="A"), Hypernode(label="B"), Hypernode(label="C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({a.id})))
        cycles = g.detect_cycles()
        assert len(cycles) == 1

    def test_hyperedge_cycle(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        assert g.has_cycle() is True


class TestBetweennessCentrality:
    def test_basic_centrality(self):
        g, a, b, c, d = _make_graph_with_edges()
        bc = g.betweenness_centrality()
        assert len(bc) == 4
        assert all(0.0 <= v <= 1.0 for v in bc.values())
        assert bc[b.id] > 0 or bc[c.id] > 0

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.betweenness_centrality() == {}

    def test_approximate_with_sampling(self):
        g, a, b, c, d = _make_graph_with_edges()
        bc = g.betweenness_centrality(max_samples=5)
        assert len(bc) == 4


class TestPageRank:
    def test_basic_pagerank(self):
        g, a, b, c, d = _make_graph_with_edges()
        pr = g.pagerank()
        assert len(pr) == 4
        total = sum(pr.values())
        assert abs(total - 1.0) < 0.01

    def test_pagerank_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="rel")
        mem.link("B", "C", label="rel")
        pr = mem.analyze.centrality("pagerank")
        assert len(pr) == 3
        total = sum(pr.values())
        assert abs(total - 1.0) < 0.01

    def test_empty_graph(self):
        g = Hypergraph()
        pr = g.pagerank()
        assert pr == {}

    def test_no_edges(self):
        g = Hypergraph()
        a, b = Hypernode(label="A"), Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        pr = g.pagerank()
        assert len(pr) == 2
        assert abs(pr[a.id] - pr[b.id]) < 0.01


class TestSPersistence:
    def test_basic_filtration(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        filt = g.s_persistence()
        assert len(filt.levels) == 2
        assert filt.levels[0].s == 1
        assert filt.levels[0].num_components == 1
        assert filt.levels[1].num_components >= filt.levels[0].num_components

    def test_no_edges(self):
        g = Hypergraph()
        filt = g.s_persistence()
        assert len(filt.levels) == 0
        g2 = Hypergraph()
        a = Hypernode(label="A")
        g2.add_node(a)
        filt2 = g2.s_persistence()
        assert len(filt2.levels) == 1
        assert filt2.levels[0].num_components == 1

    def test_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link_hyper({"a", "b"}, {"c"}, label="abc")
        filt = mem.s_persistence()
        assert len(filt.levels) == 1
        assert filt.levels[0].num_components == 1


class TestHyperedgeSimilarity:
    def test_jaccard_similarity(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        e1 = edges[0]
        result = g.hyperedge_similarity(e1.id, metric="jaccard")
        assert len(result.similar_edges) == 2
        assert all(0.0 <= score <= 1.0 for _, score in result.similar_edges)

    def test_sorensen_dice(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        e1 = edges[0]
        result = g.hyperedge_similarity(e1.id, metric="sorensen_dice")
        assert len(result.similar_edges) == 2

    def test_top_k(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        result = g.hyperedge_similarity(edges[0].id, top_k=1)
        assert len(result.similar_edges) == 1


class TestSpectralEmbedding:
    def test_basic_embedding(self):
        g, a, b, c, d = _make_graph_with_edges()
        se = g.spectral_embedding(dimensions=2)
        assert len(se.node_ids) == 4
        assert se.embeddings.shape[0] == 4
        assert se.embeddings.shape[1] <= 2

    def test_empty_graph(self):
        g = Hypergraph()
        se = g.spectral_embedding()
        assert len(se.node_ids) == 0

    def test_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="r")
        mem.link("B", "C", label="r")
        result = mem.spectral_embedding(dimensions=2)
        assert "A" in result
        assert "B" in result
        assert "C" in result
        assert len(result["A"]) <= 2


class TestSpreadHyperedge:
    def test_linear_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="r")
        mem.link("B", "C", label="r")
        results = mem.spread_hyperedge("A", energy=1.0, mode="linear", iterations=3)
        labels = {r.label for r in results}
        assert "B" in labels

    def test_and_mode_requires_all_sources(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link_hyper({"A", "B"}, {"C"}, label="joint")
        results = mem.spread_hyperedge("A", energy=1.0, mode="and", iterations=3)
        labels = {r.label for r in results}
        assert "C" not in labels

    def test_and_mode_succeeds_with_all_sources(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link_hyper({"A", "B"}, {"C"}, label="joint")
        if mem._activation is None:
            mem._activation = SpreadingActivation(mem._graph)
        mem._activation.clear()
        a_node = mem._find_node("A")
        b_node = mem._find_node("B")
        mem._activation.stimulate(a_node.id, 1.0)
        mem._activation.stimulate(b_node.id, 1.0)
        mem._activation.spread_hyperedge(mode="and", iterations=3)
        activated = mem._activation.get_activated()
        labels = {r.label for r in activated}
        assert "C" in labels

    def test_or_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link_hyper({"A", "B"}, {"C"}, label="joint")
        results = mem.spread_hyperedge("A", energy=1.0, mode="or", iterations=3)
        labels = {r.label for r in results}
        assert "C" in labels


class TestIncidenceMatrixUnsigned:
    def test_unsigned_incidence(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        H, node_ids, edge_ids = g.incidence_matrix_unsigned()
        assert H.shape[0] == 5
        assert H.shape[1] == 3
        for val in H.flat:
            assert val in (0.0, 1.0)
        assert np.sum(H) == 9.0


class TestGraphLevelMethods:
    def test_s_connected_components(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        comps = g.s_connected_components(s=1)
        assert len(comps) == 1
        comps_high = g.s_connected_components(s=10)
        assert len(comps_high) == 3

    def test_incidence_matrix_with_nary(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        H, node_ids, edge_ids = g.incidence_matrix()
        assert H.shape[0] == 5
        assert H.shape[1] == 3
        positive = np.sum(H > 0)
        negative = np.sum(H < 0)
        assert positive == 5
        assert negative == 4

    def test_laplacian_with_nary(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        L = g.hypergraph_laplacian()
        assert L.shape == (5, 5)
        assert np.allclose(L, L.T, atol=1e-10)





class TestLabelIndex:
    def test_get_node_by_label_found(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x1", label="alpha"))
        g.add_node(Hypernode(id="x2", label="beta"))
        node = g.get_node_by_label("alpha")
        assert node is not None
        assert node.id == "x1"

    def test_get_node_by_label_not_found(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x1", label="alpha"))
        assert g.get_node_by_label("gamma") is None

    def test_get_node_by_label_empty_graph(self):
        g = Hypergraph()
        assert g.get_node_by_label("anything") is None

    def test_label_index_updated_on_remove(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x1", label="alpha"))
        assert g.get_node_by_label("alpha") is not None
        g.remove_node("x1")
        assert g.get_node_by_label("alpha") is None

    def test_label_index_on_merge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x1", label="alpha"))
        g.add_node(Hypernode(id="x2", label="beta"))
        g.add_edge(Hyperedge(source_ids=frozenset({"x1"}), target_ids=frozenset({"x2"}), label="rel"))
        g.merge_node("x1", "x2")
        assert g.get_node_by_label("alpha") is not None
        assert g.get_node_by_label("beta") is None

    def test_label_index_unlabeled_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x1"))
        assert g.get_node_by_label("") is None

    def test_label_index_overwrite(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x1", label="alpha"))
        g.add_node(Hypernode(id="x2", label="alpha"))
        node = g.get_node_by_label("alpha")
        assert node is not None
        assert node.id in ("x1", "x2")


class TestNeighborCache:
    def test_neighbors_cached(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        nbrs1 = g.neighbors("a")
        nbrs2 = g.neighbors("b")
        assert "b" in nbrs1
        assert "a" in nbrs2

    def test_neighbor_cache_invalidated_on_add_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        g.add_node(Hypernode(id="c", label="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        assert g.neighbors("a") == ["b"]
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        nbrs = g.neighbors("a")
        assert set(nbrs) == {"b", "c"}

    def test_neighbor_cache_invalidated_on_remove_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        e = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel")
        g.add_edge(e)
        assert "b" in g.neighbors("a")
        g.remove_edge(e.id)
        assert g.neighbors("a") == []

    def test_neighbor_cache_invalidated_on_remove_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        assert "b" in g.neighbors("a")
        g.remove_node("b")
        assert g.neighbors("a") == []


class TestLeavesCache:
    def test_leaves_cached(self):
        mg = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"r"}))
        mg.add_state(root)
        s1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a"}), depth=1)
        mg.add_state(s1)
        leaves1 = mg.get_leaves()
        leaves2 = mg.get_leaves()
        assert leaves1 is leaves2
        assert len(leaves1) == 1

    def test_leaves_cache_invalidated(self):
        mg = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"r"}))
        mg.add_state(root)
        mg.get_leaves()
        s1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a"}), depth=1)
        mg.add_state(s1)
        leaves = mg.get_leaves()
        assert len(leaves) == 1
        assert leaves[0].id == s1.id


class TestVectorizedInvariants:
    def test_vectorized_matches_original(self):
        g = Hypergraph()
        for i in range(20):
            g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
        mg = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset(f"n{i}" for i in range(5)))
        mg.add_state(root)
        for i in range(10):
            nodes = frozenset(f"n{i+j}" for j in range(5))
            s = MultiwayState(parent_id=root.id, active_node_ids=nodes, depth=1)
            mg.add_state(s)

        engine = StateConvergenceEngine(g, mg, threshold=0.5)
        pairs = engine.find_invariants()
        for _a_id, _b_id, sim in pairs:
            assert 0.0 <= sim <= 1.0

    def test_vectorized_no_false_positives(self):
        g = Hypergraph()
        for i in range(10):
            g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
        mg = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"n0"}))
        mg.add_state(root)
        s1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"n1", "n2"}), depth=1)
        s2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"n3", "n4"}), depth=1)
        mg.add_state(s1)
        mg.add_state(s2)
        engine = StateConvergenceEngine(g, mg, threshold=0.7)
        pairs = engine.find_invariants()
        assert len(pairs) == 0


class TestTransitiveRuleOptimization:
    def test_edge_set_avoids_duplicates(self):
        g = Hypergraph()
        for i in range(5):
            g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
        g.add_edge(Hyperedge(source_ids=frozenset({"n0"}), target_ids=frozenset({"n1"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"n1"}), target_ids=frozenset({"n2"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"n0"}), target_ids=frozenset({"n2"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        active = frozenset(f"n{i}" for i in range(3))
        matches = rule.find_matches(g, active)
        assert len(matches) == 0

    def test_edge_set_finds_new_transitive(self):
        g = Hypergraph()
        for i in range(4):
            g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
        g.add_edge(Hyperedge(source_ids=frozenset({"n0"}), target_ids=frozenset({"n1"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"n1"}), target_ids=frozenset({"n2"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"n2"}), target_ids=frozenset({"n3"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        active = frozenset(f"n{i}" for i in range(4))
        matches = rule.find_matches(g, active)
        assert len(matches) == 2


class TestBatchMutation:
    def test_batch_mode_defers_cache_invalidation(self):
        g, nodes = _make_chain_graph()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[0].id}),
                target_ids=frozenset({nodes[1].id}),
                label="e",
            )
        )
        _ = g.neighbors(nodes[0].id)
        assert g._neighbor_cache is not None
        g.begin_batch()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[1].id}),
                target_ids=frozenset({nodes[2].id}),
                label="e",
            )
        )
        assert g._neighbor_cache is not None
        assert g._cache_invalidated_in_batch is True
        g.end_batch()
        assert g._neighbor_cache is None
        assert g._batch_mode is False

    def test_batch_mode_restores_functionality(self):
        g, nodes = _make_chain_graph()
        g.begin_batch()
        for i in range(4):
            g.add_edge(
                Hyperedge(
                    source_ids=frozenset({nodes[i].id}),
                    target_ids=frozenset({nodes[i + 1].id}),
                    label="next",
                )
            )
        g.end_batch()
        nbrs = g.neighbors(nodes[0].id)
        assert len(nbrs) == 1

    def test_non_batch_mode_invalidates_immediately(self):
        g, nodes = _make_chain_graph()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[0].id}),
                target_ids=frozenset({nodes[1].id}),
                label="e",
            )
        )
        _ = g.neighbors(nodes[0].id)
        assert g._neighbor_cache is not None
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[1].id}),
                target_ids=frozenset({nodes[2].id}),
                label="e",
            )
        )
        assert g._neighbor_cache is None


class TestPathQueries:
    def test_find_paths_basic(self):
        g, a, b, c, d = _make_path_graph()
        paths = g.find_paths(a.id, d.id)
        assert len(paths) == 2
        for path in paths:
            assert path[0] == a.id
            assert path[-1] == d.id

    def test_find_paths_with_label(self):
        g, a, b, c, d = _make_path_graph()
        paths = g.find_paths(a.id, d.id, edge_label="next")
        assert len(paths) == 1
        assert any(len(p) == 4 for p in paths)

    def test_find_paths_no_path(self):
        g = Hypergraph()
        x, y = Hypernode(label="x"), Hypernode(label="y")
        g.add_node(x)
        g.add_node(y)
        paths = g.find_paths(x.id, y.id)
        assert paths == []

    def test_find_paths_max_paths(self):
        g, a, b, c, d = _make_path_graph()
        paths = g.find_paths(a.id, d.id, max_paths=1)
        assert len(paths) == 1

    def test_pattern_match_by_label(self):
        g, a, b, c, d = _make_path_graph()
        matches = g.pattern_match(edge_label="skip")
        assert len(matches) == 1
        edge, bindings = matches[0]
        assert edge.label == "skip"

    def test_pattern_match_by_source_target(self):
        g, a, b, c, d = _make_path_graph()
        matches = g.pattern_match(source_label="a", target_label="d")
        assert len(matches) == 1


class TestEquivalenceBlocking:
    def test_blocking_reduces_comparisons(self):
        g = Hypergraph()
        for i in range(10):
            g.add_node(Hypernode(label=f"dict_{i}", data={"type": "a", "val": i}))
            g.add_node(Hypernode(label=f"str_{i}", data="same_string"))
            g.add_node(Hypernode(label=f"none_{i}"))
        engine = EquivalenceEngine(g, threshold=0.5)
        pairs = engine.find_equivalences()
        assert len(pairs) == 90
        for _a_id, _b_id, score in pairs:
            assert score >= 0.5

    def test_blocking_key_groups(self):
        g = Hypergraph()
        for i in range(5):
            g.add_node(Hypernode(label=f"d{i}", data={"x": 1, "y": 2}))
            g.add_node(Hypernode(label=f"s{i}", data="hello"))
            g.add_node(Hypernode(label=f"n{i}"))
        engine = EquivalenceEngine(g, threshold=0.5)
        pairs = engine.find_equivalences()
        assert len(pairs) == 20


class TestSubgraphExtraction:
    def test_subgraph_includes_only_specified_nodes(self):
        g, nodes = _make_graph_wave2()
        sg = g.subgraph({nodes[0].id, nodes[1].id, nodes[2].id})
        assert sg.node_count == 3
        assert sg.edge_count == 2

    def test_subgraph_excludes_external_edges(self):
        g, nodes = _make_graph_wave2()
        sg = g.subgraph({nodes[0].id, nodes[1].id})
        assert sg.node_count == 2
        assert sg.edge_count == 1

    def test_subgraph_empty_set(self):
        g, nodes = _make_graph_wave2()
        sg = g.subgraph(set())
        assert sg.node_count == 0

    def test_subgraph_preserves_labels(self):
        g, nodes = _make_graph_wave2()
        sg = g.subgraph({nodes[0].id, nodes[1].id})
        assert sg.get_node_by_label("n0") is not None
        assert sg.get_node_by_label("n1") is not None


class TestGraphAnalytics:
    def test_degree_centrality(self):
        g, nodes = _make_graph_wave2()
        dc = g.degree_centrality()
        assert nodes[1].id in dc
        assert dc[nodes[1].id] > dc[nodes[5].id]

    def test_betweenness_centrality(self):
        g, nodes = _make_graph_wave2()
        bc = g.betweenness_centrality()
        assert len(bc) == 6

    def test_connected_components(self):
        g, nodes = _make_graph_wave2()
        components = g.connected_components()
        assert len(components) == 3

    def test_has_cycle_false(self):
        g, nodes = _make_graph_wave2()
        assert g.has_cycle() is False

    def test_has_cycle_true(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="e"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({a.id}), label="e"))
        assert g.has_cycle() is True

    def test_detect_cycles(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="e"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({a.id}), label="e"))
        cycles = g.detect_cycles()
        assert len(cycles) == 1

    def test_shortest_path(self):
        g, nodes = _make_graph_wave2()
        path = g.shortest_path(nodes[0].id, nodes[2].id, weighted=False)
        assert path is not None
        assert len(path) == 3
        assert path[0] == nodes[0].id
        assert path[-1] == nodes[2].id

    def test_shortest_path_no_path(self):
        g, nodes = _make_graph_wave2()
        path = g.shortest_path(nodes[0].id, nodes[5].id, weighted=False)
        assert path is None

    def test_degree_distribution(self):
        g, nodes = _make_graph_wave2()
        dist = g.degree_distribution()
        assert sum(dist.values()) == 6

    def test_node_degree(self):
        g, nodes = _make_graph_wave2()
        assert g.node_degree(nodes[1].id) == 2
        assert g.node_degree(nodes[5].id) == 0



def _make_chain_graph():
    g = Hypergraph()
    nodes = []
    for i in range(5):
        n = Hypernode(label=f"n{i}")
        g.add_node(n)
        nodes.append(n)
    return g, nodes



def _make_path_graph():
    g = Hypergraph()
    a, b, c, d = (
        Hypernode(label="a"),
        Hypernode(label="b"),
        Hypernode(label="c"),
        Hypernode(label="d"),
    )
    g.add_node(a)
    g.add_node(b)
    g.add_node(c)
    g.add_node(d)
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({c.id}), target_ids=frozenset({d.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), label="skip"
        )
    )
    return g, a, b, c, d



def _make_graph_wave2():
    g = Hypergraph()
    nodes = [Hypernode(label=f"n{i}") for i in range(6)]
    for n in nodes:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), label="e"))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), label="e"))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[4].id}), label="e"))
    return g, nodes


class TestIdempotentEdgeAdd:
    def test_add_same_edge_returns_existing(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({a.id}), label="loop")
        result1 = g.add_edge(e1)
        result2 = g.add_edge(e1)
        assert result1 is result2
        assert g.edge_count == 1


class TestToNetworkx:
    def test_to_networkx_preserves_attributes(self):
        g = Hypergraph()
        a = Hypernode(label="alpha", weight=2.5, data={"kind": "test"})
        b = Hypernode(label="beta", weight=1.0)
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=3.0))
        G = g.to_networkx()
        assert G.nodes[a.id]["label"] == "alpha"
        assert G.nodes[a.id]["weight"] == 2.5
        assert G.nodes[a.id]["data"]["kind"] == "test"
        assert G.edges[a.id, b.id]["label"] == "rel"
        assert G.edges[a.id, b.id]["weight"] == 3.0

    def test_inverted_weights(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), weight=4.0))
        G = g._to_networkx_inverted_weights()
        cost = G.edges[a.id, b.id]["cost"]
        assert cost == pytest.approx(0.25)


class TestBetweennessSampling:
    def test_sampling_with_many_nodes(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(10)]
        for n in nodes:
            g.add_node(n)
        for i in range(9):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        bc = g.betweenness_centrality(max_samples=5)
        assert len(bc) == 10
        assert all(v >= 0.0 for v in bc.values())


class TestSConnectedComponentsNoEdges:
    def test_nodes_no_edges_all_singletons(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        for n in [a, b, c]:
            g.add_node(n)
        comps = g.s_connected_components(s=1)
        assert len(comps) == 3
        assert all(len(comp) == 1 for comp in comps)
        union = set()
        for comp in comps:
            union.update(comp)
        assert union == {a.id, b.id, c.id}


class TestCycleDetectionMaxCycles:
    def test_max_cycles_stops_early(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(6)]
        for n in nodes:
            g.add_node(n)
        for i in range(5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[5].id}), target_ids=frozenset({nodes[2].id})))
        all_cycles = g.detect_cycles()
        assert len(all_cycles) >= 2
        limited = g.detect_cycles(max_cycles=1)
        assert len(limited) < len(all_cycles)


class TestShortestPathRevisit:
    def test_weighted_prefers_high_weight_path(self):
        g = Hypergraph()
        a, b, c, d = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c"), Hypernode(label="d")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({d.id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), weight=10.0))
        path = g.shortest_path(a.id, d.id, weighted=True)
        assert path is not None
        assert len(path) == 2
        assert path[0] == a.id
        assert path[-1] == d.id


class TestSpectralEmbeddingSingle:
    def test_single_node_returns_default(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="only"))
        se = g.spectral_embedding(dimensions=2)
        assert len(se.node_ids) == 1
        assert se.embeddings.shape == (1, 1)
        assert se.embeddings[0, 0] == 0.0

    def test_single_node_self_loop_k_zero(self):
        g = Hypergraph()
        n = Hypernode(label="only")
        g.add_node(n)
        g.add_edge(Hyperedge(
            source_ids=frozenset({n.id}),
            target_ids=frozenset({n.id}),
        ))
        se = g.spectral_embedding(dimensions=2)
        assert len(se.node_ids) == 1
        assert se.embeddings.shape == (1, 1)
        assert se.embeddings[0, 0] == 0.0

    def test_eigsh_exception_returns_zeros(self):
        from unittest.mock import patch
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(
                source_ids=frozenset({nodes[i].id}),
                target_ids=frozenset({nodes[i + 1].id}),
            ))
            g.add_edge(Hyperedge(
                source_ids=frozenset({nodes[i + 1].id}),
                target_ids=frozenset({nodes[i].id}),
            ))
        with patch("scipy.sparse.linalg.eigsh", side_effect=RuntimeError("boom")):
            se = g.spectral_embedding(dimensions=2)
        assert np.all(se.eigenvalues == 0.0)
        assert se.embeddings.shape == (4, 2)
        assert np.all(se.embeddings == 0.0)


class TestHyperedgeSimilarityEdgeCases:
    def test_missing_edge_id_returns_empty(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        result = g.hyperedge_similarity("nonexistent_id")
        assert len(result.similar_edges) == 0

    def test_overlap_coefficient_metric(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        result = g.hyperedge_similarity(edges[0].id, metric="overlap_coefficient")
        assert len(result.similar_edges) == 2

    def test_unknown_metric_defaults_to_jaccard(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        result_jaccard = g.hyperedge_similarity(edges[0].id, metric="jaccard")
        result_unknown = g.hyperedge_similarity(edges[0].id, metric="nonexistent")
        assert len(result_jaccard.similar_edges) == len(result_unknown.similar_edges)
        for (eid_j, score_j), (eid_u, score_u) in zip(
            result_jaccard.similar_edges, result_unknown.similar_edges, strict=True
        ):
            assert eid_j == eid_u
            assert score_j == pytest.approx(score_u)


class TestPageRankNoEdges:
    def test_single_node_no_edges_uniform(self):
        g = Hypergraph()
        n = Hypernode(label="solo")
        g.add_node(n)
        pr = g.pagerank()
        assert pr[n.id] == pytest.approx(1.0)


class TestMergeNodeRewireEdgeRemoved:
    def test_merge_when_edge_already_removed(self):
        g = Hypergraph()
        a = Hypernode(label="a", data="same")
        b = Hypernode(label="b", data="same")
        c = Hypernode(label="c")
        for n in [a, b, c]:
            g.add_node(n)
        e1 = Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="e")
        g.add_edge(e1)
        g.remove_edge(e1.id)
        g.merge_node(a.id, b.id)
        assert g.node_count == 2
        assert g.get_node_by_label("a") is not None


class TestSemanticFindPaths:
    def test_hyperedge_respects_direction(self):
        g = Hypergraph()
        a, b, c, d = [Hypernode(label=l) for l in "abcd"]
        for n in [a, b, c, d]:
            g.add_node(n)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id, c.id}), label="e")
        e2 = Hyperedge(source_ids=frozenset({d.id}), target_ids=frozenset({a.id}), label="f")
        g.add_edge(e1)
        g.add_edge(e2)
        assert g.find_paths(a.id, b.id) == [[a.id, b.id]]
        assert g.find_paths(a.id, c.id) == [[a.id, c.id]]
        assert g.find_paths(d.id, a.id) == [[d.id, a.id]]
        assert g.find_paths(b.id, a.id) == []
        assert g.find_paths(b.id, c.id) == []
        assert g.find_paths(a.id, d.id) == []

    def test_path_edges_are_valid(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcd"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["c"].id}), target_ids=frozenset({nodes["d"].id}), label="x"))
        paths = g.find_paths(nodes["a"].id, nodes["d"].id)
        assert len(paths) == 1
        for path in paths:
            assert path[0] == nodes["a"].id
            assert path[-1] == nodes["d"].id
            for i in range(len(path) - 1):
                outgoing = g.outgoing_edges(path[i])
                assert any(path[i + 1] in e.target_ids for e in outgoing)


class TestSemanticConnectedComponents:
    def test_partition_property(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcdef"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["d"].id}), target_ids=frozenset({nodes["e"].id}), label="y"))
        all_ids = {n.id for n in nodes.values()}
        comps = g.connected_components()
        union = set()
        for comp in comps:
            union.update(comp)
        assert union == all_ids
        for i in range(len(comps)):
            for j in range(i + 1, len(comps)):
                assert comps[i].isdisjoint(comps[j])

    def test_s1_agrees_with_basic(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcde"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["d"].id}), target_ids=frozenset({nodes["e"].id}), label="y"))
        basic = {frozenset(c) for c in g.connected_components()}
        s1 = {frozenset(c) for c in g.s_connected_components(s=1)}
        assert basic == s1

    def test_s_monotonicity(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcde"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id, nodes["c"].id}), label="e1"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id, nodes["d"].id}), target_ids=frozenset({nodes["e"].id}), label="e2"))
        prev = None
        for s in range(1, 5):
            comps = g.s_connected_components(s=s)
            if prev is not None:
                for comp in comps:
                    assert any(comp <= pc for pc in prev)
            prev = comps


class TestSemanticPageRank:
    def test_sums_to_one(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcde"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["c"].id}), target_ids=frozenset({nodes["d"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["d"].id}), target_ids=frozenset({nodes["a"].id}), label="x"))
        pr = g.pagerank()
        assert sum(pr.values()) == pytest.approx(1.0)
        assert all(v >= 0 for v in pr.values())
        assert set(pr.keys()) == {n.id for n in nodes.values()}

    def test_dangling_node_gets_score(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abc"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        pr = g.pagerank()
        assert pr[nodes["c"].id] > 0
        assert sum(pr.values()) == pytest.approx(1.0)


class TestSemanticBetweenness:
    def test_bridge_node_highest(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcde"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["c"].id}), target_ids=frozenset({nodes["d"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["d"].id}), target_ids=frozenset({nodes["e"].id}), label="x"))
        bc = g.betweenness_centrality()
        assert bc[nodes["c"].id] == max(bc.values())

    def test_all_nodes_present(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abc"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        bc = g.betweenness_centrality()
        assert set(bc.keys()) == {n.id for n in nodes.values()}
        assert all(v >= 0 for v in bc.values())


class TestSemanticShortestPath:
    def test_path_edges_are_valid(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcd"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x", weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x", weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["c"].id}), target_ids=frozenset({nodes["d"].id}), label="x", weight=1.0))
        path = g.shortest_path(nodes["a"].id, nodes["d"].id)
        assert path is not None
        assert path[0] == nodes["a"].id
        assert path[-1] == nodes["d"].id
        for i in range(len(path) - 1):
            outgoing = g.outgoing_edges(path[i])
            assert any(path[i + 1] in e.target_ids for e in outgoing)

    def test_dangling_source_returns_none(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x"))
        assert g.shortest_path(b.id, a.id) is None


class TestSemanticCycles:
    def test_cycle_edges_are_valid(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abc"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["c"].id}), target_ids=frozenset({nodes["a"].id}), label="x"))
        cycles = g.detect_cycles()
        assert len(cycles) == 1
        for cycle in cycles:
            assert cycle[0] == cycle[-1]
            for i in range(len(cycle) - 1):
                outgoing = g.outgoing_edges(cycle[i])
                assert any(cycle[i + 1] in e.target_ids for e in outgoing)

    def test_no_false_positives(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abc"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        assert g.detect_cycles() == []
        assert g.has_cycle() is False


class TestSemanticEvolution:
    def test_decay_is_monotonic(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l, weight=w) for l, w in [("a", 1.0), ("b", 0.5), ("c", 0.05)]}
        for n in nodes.values():
            g.add_node(n)
        eng = GraphMaintenanceEngine(g, decay_threshold=0.1)
        old_weights = {l: g.get_node(n.id).weight for l, n in nodes.items()}
        eng.decay_weights(factor=0.5)
        new_weights = {l: g.get_node(n.id).weight for l, n in nodes.items()}
        for label in nodes:
            assert new_weights[label] <= old_weights[label] + 1e-12

    def test_prune_removes_connected_edges(self):
        g = Hypergraph()
        a = Hypernode(label="a", weight=0.01)
        b = Hypernode(label="b", weight=1.0)
        c = Hypernode(label="c", weight=1.0)
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x"))
        eng = GraphMaintenanceEngine(g, decay_threshold=0.1, prune_access_count=0)
        eng.prune_dead_nodes()
        assert g.edge_count == 0
        assert g.node_count == 2
        assert g.get_node(a.id) is None

    def test_prune_preserves_accessed_nodes(self):
        g = Hypergraph()
        a = Hypernode(label="a", weight=0.01, access_count=1)
        g.add_node(a)
        eng = GraphMaintenanceEngine(g, decay_threshold=0.1, prune_access_count=0)
        pruned = eng.prune_dead_nodes()
        assert len(pruned) == 0
        assert g.get_node(a.id) is not None

    def test_reinforce_caps_at_100(self):
        g = Hypergraph()
        h = Hypernode(label="h", weight=99.0)
        g.add_node(h)
        eng = GraphMaintenanceEngine(g)
        eng.reinforce(h.id, boost=2.0)
        assert g.get_node(h.id).weight == 100.0

    def test_reinforce_missing_node_is_noop(self):
        g = Hypergraph()
        eng = GraphMaintenanceEngine(g)
        result = eng.reinforce("nonexistent", boost=2.0)
        assert result is None
        assert g.node_count == 0

    def test_merge_rewires_edges(self):
        g = Hypergraph()
        p = Hypernode(label="p", data="same")
        s = Hypernode(label="s", data="same")
        t = Hypernode(label="t")
        for n in [p, s, t]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({s.id}), target_ids=frozenset({t.id}), label="x"))
        eng = GraphMaintenanceEngine(g, merge_threshold=0.5)
        eng.merge_equivalences()
        outgoing = g.outgoing_edges(p.id)
        assert any(t.id in e.target_ids for e in outgoing)
        assert g.get_node(s.id) is None

    def test_self_merge_is_noop(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        result = g.merge_node(a.id, a.id)
        assert result is None
        assert g.node_count == 1

    def test_cascading_merge_prevents_stale_scores(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l, data={"type": "same"}) for l in "abc"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["a"].id}), target_ids=frozenset({nodes["b"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["b"].id}), target_ids=frozenset({nodes["c"].id}), label="x"))
        from hyper3.equivalence import EquivalenceEngine
        eng = EquivalenceEngine(g, threshold=0.1)
        merged = eng.merge_equivalences()
        surviving = {g.get_node(nid).label for nid in g._nodes}
        assert len(surviving) + len(merged) == 3
        assert len(merged) == 1


class TestAdjacencyMatrix:
    def test_shape(self):
        g = Hypergraph()
        for l in "abcd":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcd"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        mat, node_ids = g.adjacency_matrix()
        assert mat.shape == (4, 4)
        assert len(node_ids) == 4

    def test_empty_graph(self):
        g = Hypergraph()
        mat, node_ids = g.adjacency_matrix()
        assert mat.shape == (0, 0)
        assert node_ids == []


class TestNormalizedLaplacian:
    def test_shape_and_eigenvalues(self):
        g = Hypergraph()
        for l in "abcd":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcd"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[2]}), target_ids=frozenset({ids[3]})))
        L, node_ids = g.normalized_laplacian()
        assert L.shape == (4, 4)
        eigenvalues = np.sort(np.linalg.eigvalsh(L))
        assert eigenvalues[0] >= -1e-10

    def test_empty_graph(self):
        g = Hypergraph()
        L, node_ids = g.normalized_laplacian()
        assert L.shape == (0, 0)
        assert node_ids == []


class TestShortestPathLengths:
    def test_all_pairs(self):
        g = Hypergraph()
        for l in "abcd":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcd"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        dists = g.shortest_path_lengths(weighted=False)
        assert dists[ids[0]][ids[2]] == 2.0
        assert dists[ids[0]][ids[0]] == 0.0

    def test_unreachable_omitted(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        dists = g.shortest_path_lengths(weighted=False)
        assert ids[2] not in dists[ids[0]]

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.shortest_path_lengths() == {}


class TestConnectivityHelpers:
    def test_is_connected(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        assert g.is_connected()

    def test_not_connected(self):
        g = Hypergraph()
        for l in "abcd":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcd"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        assert not g.is_connected()

    def test_largest_cc(self):
        g = Hypergraph()
        for l in "abcde":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcde"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        lcc = g.largest_connected_component()
        assert len(lcc) == 3

    def test_component_of(self):
        g = Hypergraph()
        for l in "abcd":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcd"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        comp = g.component_of(ids[0])
        assert ids[0] in comp
        assert ids[1] in comp
        assert ids[2] not in comp

    def test_component_of_missing(self):
        g = Hypergraph()
        assert g.component_of("missing") == set()


class TestGraphStatistics:
    def test_density(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        assert g.density() == pytest.approx(1 / 6)

    def test_density_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.density() == 0.0

    def test_unique_edge_sizes(self):
        g = Hypergraph()
        for l in "abcd":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcd"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0], ids[1]}), target_ids=frozenset({ids[2], ids[3]})))
        assert g.unique_edge_sizes() == [2, 4]

    def test_max_edge_order(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        assert g.max_edge_order() == 1

    def test_max_edge_order_empty(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.max_edge_order() == 0


class TestDistanceMetrics:
    def _make_path(self, n: int) -> tuple[Hypergraph, list[str]]:
        g = Hypergraph()
        ids = []
        for i in range(n):
            node = Hypernode(label=f"n{i}")
            g.add_node(node)
            ids.append(node.id)
        for i in range(n - 1):
            g.add_edge(Hyperedge(source_ids=frozenset({ids[i]}), target_ids=frozenset({ids[i + 1]})))
            g.add_edge(Hyperedge(source_ids=frozenset({ids[i + 1]}), target_ids=frozenset({ids[i]})))
        return g, ids

    def test_eccentricity_single_node(self):
        g = Hypergraph()
        n = Hypernode(label="a")
        g.add_node(n)
        assert g.eccentricity(n.id) == 0

    def test_eccentricity_pair(self):
        g, ids = self._make_path(2)
        assert g.eccentricity(ids[0]) == 1
        assert g.eccentricity(ids[1]) == 1

    def test_eccentricity_path(self):
        g, ids = self._make_path(5)
        ecc = g.eccentricity()
        assert ecc[ids[0]] == 4
        assert ecc[ids[2]] == 2
        assert ecc[ids[4]] == 4

    def test_eccentricity_missing_node(self):
        g = Hypergraph()
        assert g.eccentricity("missing") == 0

    def test_diameter_path(self):
        g, _ = self._make_path(5)
        assert g.diameter() == 4

    def test_diameter_empty(self):
        g = Hypergraph()
        assert g.diameter() == 0

    def test_diameter_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.diameter() == 0

    def test_radius_path(self):
        g, ids = self._make_path(5)
        assert g.radius() == 2

    def test_radius_empty(self):
        g = Hypergraph()
        assert g.radius() == 0

    def test_periphery_path(self):
        g, ids = self._make_path(5)
        p = g.periphery()
        assert set(p) == {ids[0], ids[4]}

    def test_periphery_empty(self):
        g = Hypergraph()
        assert g.periphery() == []

    def test_center_path(self):
        g, ids = self._make_path(5)
        c = g.center()
        assert c == [ids[2]]

    def test_center_path_even(self):
        g, ids = self._make_path(4)
        c = g.center()
        assert set(c) == {ids[1], ids[2]}

    def test_center_empty(self):
        g = Hypergraph()
        assert g.center() == []

    def test_diameter_triangle(self):
        g = Hypergraph()
        ids = []
        for l in "abc":
            n = Hypernode(label=l)
            g.add_node(n)
            ids.append(n.id)
        for i in range(3):
            j = (i + 1) % 3
            g.add_edge(Hyperedge(source_ids=frozenset({ids[i]}), target_ids=frozenset({ids[j]})))
            g.add_edge(Hyperedge(source_ids=frozenset({ids[j]}), target_ids=frozenset({ids[i]})))
        assert g.diameter() == 1
        assert g.radius() == 1


class TestDegreeAssortativity:
    def test_empty(self):
        g = Hypergraph()
        assert g.degree_assortativity() == 0.0

    def test_single_edge(self):
        g = Hypergraph()
        ids = []
        for l in "ab":
            n = Hypernode(label=l)
            g.add_node(n)
            ids.append(n.id)
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[0]})))
        assert g.degree_assortativity() == pytest.approx(0.0, abs=1e-10)

    def test_returns_float(self):
        g = Hypergraph()
        for l in "abcd":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcd"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[0]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[2]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[2]}), target_ids=frozenset({ids[3]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[3]}), target_ids=frozenset({ids[2]})))
        r = g.degree_assortativity()
        assert -1.0 <= r <= 1.0


class TestHEigenvectorCentrality:
    def _make_hypergraph(self):
        g = Hypergraph()
        ids = []
        for l in "abcd":
            g.add_node(Hypernode(label=l))
            ids.append(g.get_node_by_label(l).id)
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0], ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1], ids[2]}), target_ids=frozenset({ids[3]})))
        return g, ids

    def test_returns_dict(self):
        g, _ = self._make_hypergraph()
        hc = g.h_eigenvector_centrality()
        assert isinstance(hc, dict)
        assert len(hc) == 4

    def test_all_positive(self):
        g, _ = self._make_hypergraph()
        hc = g.h_eigenvector_centrality()
        assert all(v >= 0 for v in hc.values())

    def test_sums_to_one(self):
        g, _ = self._make_hypergraph()
        hc = g.h_eigenvector_centrality()
        assert abs(sum(hc.values()) - 1.0) < 1e-6

    def test_empty(self):
        g = Hypergraph()
        assert g.h_eigenvector_centrality() == {}

    def test_no_edges(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        hc = g.h_eigenvector_centrality()
        assert len(hc) == 3


class TestZEigenvectorCentrality:
    def _make_hypergraph(self):
        g = Hypergraph()
        ids = []
        for l in "abcd":
            g.add_node(Hypernode(label=l))
            ids.append(g.get_node_by_label(l).id)
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0], ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1], ids[2]}), target_ids=frozenset({ids[3]})))
        return g, ids

    def test_returns_dict(self):
        g, _ = self._make_hypergraph()
        zc = g.z_eigenvector_centrality()
        assert isinstance(zc, dict)
        assert len(zc) == 4

    def test_all_positive(self):
        g, _ = self._make_hypergraph()
        zc = g.z_eigenvector_centrality()
        assert all(v >= 0 for v in zc.values())

    def test_sums_to_one(self):
        g, _ = self._make_hypergraph()
        zc = g.z_eigenvector_centrality()
        assert abs(sum(zc.values()) - 1.0) < 1e-6

    def test_empty(self):
        g = Hypergraph()
        assert g.z_eigenvector_centrality() == {}


class TestCEigenvectorCentrality:
    def test_matches_eigenvector(self):
        g = Hypergraph()
        ids = []
        for l in "abcd":
            g.add_node(Hypernode(label=l))
            ids.append(g.get_node_by_label(l).id)
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[2]}), target_ids=frozenset({ids[3]})))
        cc = g.c_eigenvector_centrality()
        ec = g.eigenvector_centrality()
        for nid in cc:
            assert abs(cc[nid] - ec[nid]) < 1e-6


class TestNodeEdgeCentrality:
    def test_returns_tuple(self):
        g = Hypergraph()
        ids = []
        for l in "abc":
            g.add_node(Hypernode(label=l))
            ids.append(g.get_node_by_label(l).id)
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0], ids[1]}), target_ids=frozenset({ids[2]})))
        nc, ec = g.node_edge_centrality()
        assert isinstance(nc, dict)
        assert isinstance(ec, dict)
        assert len(nc) == 3
        assert len(ec) == 1

    def test_all_positive(self):
        g = Hypergraph()
        ids = []
        for l in "abc":
            g.add_node(Hypernode(label=l))
            ids.append(g.get_node_by_label(l).id)
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0], ids[1]}), target_ids=frozenset({ids[2]})))
        nc, ec = g.node_edge_centrality()
        assert all(v >= 0 for v in nc.values())
        assert all(v >= 0 for v in ec.values())

    def test_empty(self):
        g = Hypergraph()
        nc, ec = g.node_edge_centrality()
        assert nc == {}
        assert ec == {}

    def test_no_edges(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        nc, ec = g.node_edge_centrality()
        assert len(nc) == 3
        assert ec == {}


class TestSWalkCentralities:
    def _make_hypergraph(self):
        g = Hypergraph()
        ids = []
        for l in "abcd":
            g.add_node(Hypernode(label=l))
            ids.append(g.get_node_by_label(l).id)
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0], ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1], ids[2]}), target_ids=frozenset({ids[3]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[3]})))
        return g, ids

    def test_s_walk_betweenness_edges(self):
        g, _ = self._make_hypergraph()
        bc = g.s_walk_betweenness(s=1, kind="edges")
        assert isinstance(bc, dict)
        assert len(bc) == 3

    def test_s_walk_betweenness_nodes(self):
        g, _ = self._make_hypergraph()
        bc = g.s_walk_betweenness(s=1, kind="nodes")
        assert isinstance(bc, dict)
        assert len(bc) == 4

    def test_s_walk_closeness_edges(self):
        g, _ = self._make_hypergraph()
        cc = g.s_walk_closeness(s=1, kind="edges")
        assert isinstance(cc, dict)
        assert len(cc) == 3
        assert all(0 <= v <= 1 for v in cc.values())

    def test_s_walk_closeness_nodes(self):
        g, _ = self._make_hypergraph()
        cc = g.s_walk_closeness(s=1, kind="nodes")
        assert isinstance(cc, dict)
        assert len(cc) == 4

    def test_s_walk_empty(self):
        g = Hypergraph()
        assert g.s_walk_betweenness(s=1, kind="edges") == {}
        assert g.s_walk_betweenness(s=1, kind="nodes") == {}
        assert g.s_walk_closeness(s=1, kind="edges") == {}
        assert g.s_walk_closeness(s=1, kind="nodes") == {}

    def test_s_walk_betweenness_s2(self):
        g, _ = self._make_hypergraph()
        bc = g.s_walk_betweenness(s=2, kind="edges")
        assert isinstance(bc, dict)


class TestClusteringCoefficient:
    def test_triangle(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[2]}), target_ids=frozenset({ids[0]})))
        cc = g.clustering_coefficient(ids[0])
        assert cc == 1.0

    def test_single_neighbor_zero(self):
        g = Hypergraph()
        for l in "ab":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "ab"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        assert g.clustering_coefficient(ids[0]) == 0.0

    def test_average_clustering_triangle(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[2]}), target_ids=frozenset({ids[0]})))
        assert g.average_clustering_coefficient() == 1.0


class TestKatzCentrality:
    def test_returns_dict(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        kc = g.katz_centrality()
        assert len(kc) == 3
        assert all(isinstance(v, float) for v in kc.values())
        assert all(v > 0 for v in kc.values())

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.katz_centrality() == {}


class TestSpectralClustering:
    def test_two_clusters(self):
        g = Hypergraph()
        for l in "abcdef":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abcdef"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[3]}), target_ids=frozenset({ids[4]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[4]}), target_ids=frozenset({ids[5]})))
        clusters = g.spectral_clustering(k=2)
        assert len(clusters) == 2
        assert sum(len(c) for c in clusters) == 6

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.spectral_clustering(k=2) == []


class TestDualAndTransformations:
    def test_to_dual(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0], ids[1]}), target_ids=frozenset({ids[2]})))
        dual = g.to_dual()
        assert dual.node_count == 1
        assert dual.edge_count == 3

    def test_to_dual_empty(self):
        g = Hypergraph()
        dual = g.to_dual()
        assert dual.node_count == 0
        assert dual.edge_count == 0

    def test_to_line_graph(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "abc"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        g.add_edge(Hyperedge(source_ids=frozenset({ids[1]}), target_ids=frozenset({ids[2]})))
        lg = g.to_line_graph()
        assert lg.number_of_nodes() == 2
        assert lg.number_of_edges() == 1

    def test_to_bipartite_graph(self):
        g = Hypergraph()
        for l in "ab":
            g.add_node(Hypernode(label=l))
        ids = [g.get_node_by_label(l).id for l in "ab"]
        g.add_edge(Hyperedge(source_ids=frozenset({ids[0]}), target_ids=frozenset({ids[1]})))
        bg = g.to_bipartite_graph()
        assert bg.number_of_nodes() == 3
        assert bg.number_of_edges() == 2


class TestShortestPathLengthsWeighted:
    def test_weighted_distances_chain(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=2.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=2.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), weight=2.0))
        lengths = g.shortest_path_lengths(weighted=True)
        cost = 1.0 / 2.0
        assert abs(lengths[nodes[0].id][nodes[3].id] - 3 * cost) < 1e-9
        assert abs(lengths[nodes[0].id][nodes[1].id] - cost) < 1e-9

    def test_weighted_distances_prefer_high_weight(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=10.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=10.0))
        lengths = g.shortest_path_lengths(weighted=True)
        cheap_path_cost = 1.0 / 10.0 + 1.0 / 10.0
        assert abs(lengths[nodes[0].id][nodes[2].id] - cheap_path_cost) < 1e-9

    def test_single_source_weighted(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=5.0))
        dists = g.single_source_shortest_path_lengths(nodes[0].id, weighted=True)
        assert abs(dists[nodes[2].id] - 2 * (1.0 / 5.0)) < 1e-9

    def test_single_source_missing_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.single_source_shortest_path_lengths("nonexistent", weighted=True) == {}

    def test_dijkstra_duplicate_heap_entries(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=10.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=10.0))
        dists = g.single_source_shortest_path_lengths(nodes[0].id, weighted=True)
        indirect_cost = 1.0 / 10.0 + 1.0 / 10.0
        assert abs(dists[nodes[2].id] - indirect_cost) < 1e-9


class TestClusteringEdgeCases:
    def test_average_clustering_empty_graph(self):
        g = Hypergraph()
        assert g.average_clustering_coefficient() == 0.0

    def test_average_clustering_isolated_nodes(self):
        g = Hypergraph()
        for i in range(3):
            g.add_node(Hypernode(label=f"n{i}"))
        assert g.average_clustering_coefficient() == 0.0

    def test_average_clustering_chain(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        result = g.average_clustering_coefficient()
        assert 0.0 <= result <= 1.0

    def test_clustering_coefficient_three_neighbors(self):
        g = Hypergraph()
        center = Hypernode(label="center")
        g.add_node(center)
        nbrs = [Hypernode(label=f"nbr{i}") for i in range(3)]
        for n in nbrs:
            g.add_node(n)
            g.add_edge(Hyperedge(source_ids=frozenset({center.id}), target_ids=frozenset({n.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nbrs[0].id}), target_ids=frozenset({nbrs[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nbrs[1].id}), target_ids=frozenset({nbrs[2].id})))
        cc = g.clustering_coefficient(center.id)
        assert 0.0 < cc < 1.0
        expected = 2.0 * 2 / (3 * 2)
        assert abs(cc - expected) < 1e-9

    def test_spectral_clustering_k1(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        clusters = g.spectral_clustering(k=1)
        assert len(clusters) == 1
        assert len(clusters[0]) == 4


class TestSimilarityEdgeCases:
    def test_zero_intersection_not_returned(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        e1 = Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), label="group_a")
        e2 = Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), label="group_b")
        g.add_edge(e1)
        g.add_edge(e2)
        result = g.hyperedge_similarity(e1.id, metric="jaccard")
        assert len(result.similar_edges) == 0

    def test_sorensen_dice_metric(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        e1 = Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset({nodes[2].id}))
        e2 = Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}))
        g.add_edge(e1)
        g.add_edge(e2)
        result = g.hyperedge_similarity(e1.id, metric="sorensen_dice")
        assert len(result.similar_edges) == 1
        score = result.similar_edges[0][1]
        intersection = 2
        assert abs(score - 2.0 * intersection / (3 + 2)) < 1e-9

    def test_overlap_coefficient_metric(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        e1 = Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset({nodes[2].id}))
        e2 = Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}))
        g.add_edge(e1)
        g.add_edge(e2)
        result = g.hyperedge_similarity(e1.id, metric="overlap_coefficient")
        assert len(result.similar_edges) == 1
        score = result.similar_edges[0][1]
        assert abs(score - 2.0 / 2.0) < 1e-9


class TestSpectralClusteringEdgeCases:
    def test_spectral_clustering_k_equals_n(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        clusters = g.spectral_clustering(k=3)
        assert len(clusters) == 3
        assert sum(len(c) for c in clusters) == 3

    def test_spectral_clustering_k_zero(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        clusters = g.spectral_clustering(k=0)
        assert clusters == []


class TestDualWithIsolatedNodes:
    def test_dual_skips_isolated_nodes(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        iso = Hypernode(label="isolated")
        g.add_node(a)
        g.add_node(b)
        g.add_node(iso)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        dual = g.to_dual()
        assert dual.node_count == 1
        assert dual.edge_count == 2
        dual_labels = {n.label for n in dual.nodes}
        assert "e0" in dual_labels


class TestAlgebraicConnectivity:
    def test_connected_graph_positive(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        ac = g.algebraic_connectivity()
        assert ac > 0.0

    def test_disconnected_graph_zero(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        assert g.algebraic_connectivity() == 0.0

    def test_single_node_zero(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.algebraic_connectivity() == 0.0

    def test_empty_graph_zero(self):
        g = Hypergraph()
        assert g.algebraic_connectivity() == 0.0


class TestFiedlerVector:
    def test_returns_node_ids_and_values(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        ids, vec = g.fiedler_vector()
        assert len(ids) == 4
        assert len(vec) == 4

    def test_single_node_empty(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        ids, vec = g.fiedler_vector()
        assert ids == []
        assert vec == []

    def test_connected_graph_nonzero(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        _, vec = g.fiedler_vector()
        assert any(abs(v) > 1e-10 for v in vec)


class TestSpectralBisection:
    def test_produces_two_partitions(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(6)]
        for n in nodes:
            g.add_node(n)
        for i in range(5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        parts = g.spectral_bisection()
        assert len(parts) == 2
        all_nodes = parts[0] | parts[1]
        assert len(all_nodes) == 6

    def test_partitions_disjoint(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        parts = g.spectral_bisection()
        assert len(parts[0] & parts[1]) == 0

    def test_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        parts = g.spectral_bisection()
        assert len(parts) == 1


class TestSpectralBipartivity:
    def test_complete_graph_low(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
        bp = g.spectral_bipartivity()
        assert 0.0 < bp <= 1.0

    def test_empty_graph_one(self):
        g = Hypergraph()
        assert g.spectral_bipartivity() == 1.0

    def test_path_graph(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        bp = g.spectral_bipartivity()
        assert 0.0 < bp <= 1.0


class TestBetheHessian:
    def test_shape(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        H, ids = g.bethe_hessian_matrix()
        import numpy as np
        H_arr = np.asarray(H)
        assert H_arr.shape == (4, 4)
        assert len(ids) == 4

    def test_symmetric(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        H, _ = g.bethe_hessian_matrix()
        import numpy as np
        H_arr = np.asarray(H)
        assert np.allclose(H_arr, H_arr.T, atol=1e-10)

    def test_custom_r(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        H, _ = g.bethe_hessian_matrix(r=2.5)
        import numpy as np
        H_arr = np.asarray(H)
        assert H_arr.shape == (3, 3)

    def test_empty_graph(self):
        g = Hypergraph()
        H, ids = g.bethe_hessian_matrix()
        import numpy as np
        assert np.asarray(H).shape == (0, 0)
        assert ids == []


class TestGirth:
    def test_cycle_length(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[0].id})))
        assert g.girth() == 4

    def test_triangle(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        assert g.girth() == 3

    def test_no_cycles_zero(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        assert g.girth() == 0

    def test_empty_graph_zero(self):
        g = Hypergraph()
        assert g.girth() == 0


class TestClosenessCentrality:
    def test_star_graph_center(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(1, 5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[i].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[0].id})))
        cc = g.closeness_centrality()
        center = cc[nodes[0].id]
        for i in range(1, 5):
            assert center >= cc[nodes[i].id]

    def test_sum_values_positive(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        cc = g.closeness_centrality()
        assert all(v > 0 for v in cc.values())

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.closeness_centrality() == {}


class TestEigenvectorCentrality:
    def test_star_center_highest(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(1, 5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[i].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[0].id})))
        ec = g.eigenvector_centrality()
        center = ec[nodes[0].id]
        for i in range(1, 5):
            assert center >= ec[nodes[i].id]

    def test_normalized(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        ec = g.eigenvector_centrality()
        norm = np.linalg.norm(list(ec.values()))
        assert abs(norm - 1.0) < 1e-6

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.eigenvector_centrality() == {}


class TestTransitivity:
    def test_complete_graph_one(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        assert abs(g.transitivity() - 1.0) < 1e-10

    def test_no_triangles_zero(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[1].id})))
        t = g.transitivity()
        assert t >= 0.0
        assert t <= 1.0

    def test_small_graph_zero(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        g.add_node(Hypernode(label="b"))
        assert g.transitivity() == 0.0


class TestStronglyConnectedComponents:
    def test_single_scc_in_cycle(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 3].id})))
        sccs = g.strongly_connected_components()
        assert len(sccs) == 1
        assert len(sccs[0]) == 3

    def test_two_isolated_cycles(self):
        g = Hypergraph()
        nodes_a = [Hypernode(label=f"a{i}") for i in range(3)]
        nodes_b = [Hypernode(label=f"b{i}") for i in range(3)]
        for n in nodes_a + nodes_b:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes_a[i].id}), target_ids=frozenset({nodes_a[(i + 1) % 3].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes_b[i].id}), target_ids=frozenset({nodes_b[(i + 1) % 3].id})))
        sccs = g.strongly_connected_components()
        assert len(sccs) == 2

    def test_dag_each_node_own_scc(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        sccs = g.strongly_connected_components()
        assert len(sccs) == 4

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.strongly_connected_components() == []


class TestBiconnectedComponents:
    def test_simple_triangle(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            for j in range(3):
                if i != j:
                    g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
        bccs = g.biconnected_components()
        assert len(bccs) >= 1
        all_nodes = set()
        for comp in bccs:
            all_nodes |= comp
        assert len(all_nodes) == 3

    def test_bridge_splits(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[2].id})))
        bccs = g.biconnected_components()
        assert len(bccs) >= 1

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.biconnected_components() == []


class TestArticulationPoints:
    def test_path_has_internal_articulation(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        aps = g.articulation_points()
        assert nodes[1].id in aps
        assert nodes[2].id in aps

    def test_cycle_no_articulation(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 4].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[(i + 1) % 4].id}), target_ids=frozenset({nodes[i].id})))
        aps = g.articulation_points()
        assert len(aps) == 0

    def test_star_center_is_articulation(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(1, 5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[i].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[0].id})))
        aps = g.articulation_points()
        assert nodes[0].id in aps


class TestCliqueProjection:
    def test_pairwise_graph_unchanged(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        proj = g.clique_projection()
        assert proj.node_count == 3
        assert proj.edge_count == 2

    def test_hyperedge_expands_to_clique(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(
            source_ids=frozenset({nodes[0].id, nodes[1].id}),
            target_ids=frozenset({nodes[2].id, nodes[3].id}),
        ))
        proj = g.clique_projection()
        assert proj.node_count == 4
        assert proj.edge_count == 6

    def test_preserves_labels(self):
        g = Hypergraph()
        a = Hypernode(label="alpha")
        b = Hypernode(label="beta")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        proj = g.clique_projection()
        labels = {n.label for n in proj.nodes}
        assert "alpha" in labels
        assert "beta" in labels


class TestHashHypergraph:
    def test_deterministic(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        assert g.hash() == g.hash()

    def test_different_graphs_different_hashes(self):
        g1 = Hypergraph()
        g2 = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        c = Hypernode(label="c")
        g1.add_node(a)
        g1.add_node(b)
        g1.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        g2.add_node(a)
        g2.add_node(c)
        g2.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id})))
        assert g1.hash() != g2.hash()

    def test_empty_graph(self):
        g = Hypergraph()
        assert isinstance(g.hash(), str)
        assert len(g.hash()) == 64


class TestTransitionMatrix:
    def test_shape(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        P, ids = g.transition_matrix()
        P_arr = np.asarray(P.todense())
        assert P_arr.shape == (4, 4)
        assert len(ids) == 4

    def test_rows_sum_to_one(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        P, _ = g.transition_matrix()
        P_arr = np.asarray(P.todense())
        for i in range(4):
            row_sum = P_arr[i].sum()
            if row_sum > 0:
                assert abs(row_sum - 1.0) < 1e-10

    def test_empty_graph(self):
        g = Hypergraph()
        P, ids = g.transition_matrix()
        assert len(ids) == 0


class TestIncidenceMatrixByOrder:
    def test_pairwise_edges_order_1(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        H, node_ids, edge_ids = g.incidence_matrix_by_order(order=1)
        H_arr = np.asarray(H)
        assert H_arr.shape[1] == 3

    def test_hyperedge_order_2(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(
            source_ids=frozenset({nodes[0].id, nodes[1].id}),
            target_ids=frozenset({nodes[2].id, nodes[3].id}),
        ))
        H, _, _ = g.incidence_matrix_by_order(order=1)
        H_arr = np.asarray(H)
        assert H_arr.shape[1] == 1

    def test_no_matching_order(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        H, _, edge_ids = g.incidence_matrix_by_order(order=3)
        assert len(edge_ids) == 0


class TestDegreeCorrelation:
    def test_positive_for_assortative(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(6)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            for j in range(i + 1, 3):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        for i in range(3, 5):
            for j in range(i + 1, 6):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[0].id})))
        corr = g.degree_correlation()
        assert -1.0 <= corr <= 1.0

    def test_empty_graph_zero(self):
        g = Hypergraph()
        assert g.degree_correlation() == 0.0

    def test_no_edges_zero(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.degree_correlation() == 0.0


class TestGreedyModularityCommunities:
    def test_two_clusters(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(6)]
        for n in nodes:
            g.add_node(n)
        for i in range(2):
            for j in range(i + 1, 3):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        for i in range(3, 5):
            for j in range(i + 1, 6):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        comms = g.greedy_modularity_communities()
        assert len(comms) >= 1
        all_nodes = set()
        for c in comms:
            all_nodes |= c
        assert len(all_nodes) == 6

    def test_single_node(self):
        g = Hypergraph()
        node = Hypernode(label="a")
        g.add_node(node)
        comms = g.greedy_modularity_communities()
        assert len(comms) == 1
        assert node.id in comms[0]

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.greedy_modularity_communities() == []


class TestSubhypergraphCentrality:
    def test_positive_values(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        sc = g.subhypergraph_centrality()
        assert all(v > 0 for v in sc.values())

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.subhypergraph_centrality() == {}

    def test_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        sc = g.subhypergraph_centrality()
        assert sc is not None


class TestCorePeriphery:
    def test_hub_is_core(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(1, 5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[i].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[0].id})))
        cp = g.core_periphery()
        hub_score = cp[nodes[0].id]
        for i in range(1, 5):
            assert hub_score >= cp[nodes[i].id]

    def test_scores_bounded(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        cp = g.core_periphery()
        assert all(0.0 <= v <= 1.0 for v in cp.values())

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.core_periphery() == {}


class TestMultiorderLaplacian:
    def test_shape(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(
            source_ids=frozenset({nodes[0].id, nodes[1].id}),
            target_ids=frozenset({nodes[2].id, nodes[3].id}),
        ))
        L = g.multiorder_laplacian({1: 1.0, 2: 0.5})
        L_arr = np.asarray(L)
        assert L_arr.shape == (4, 4)

    def test_symmetric(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        L = g.multiorder_laplacian({1: 1.0})
        L_arr = np.asarray(L)
        assert np.allclose(L_arr, L_arr.T, atol=1e-10)

    def test_eigenvalues(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        eigs = g.multiorder_laplacian_eigenvalues({1: 1.0})
        assert len(eigs) == 4

    def test_empty_graph(self):
        import numpy as np
        g = Hypergraph()
        L = g.multiorder_laplacian({1: 1.0})
        assert L.shape == (0, 0)


class TestDualRandomWalkAdjacency:
    def test_shape(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        A, edge_ids, _ = g.dual_random_walk_adjacency()
        assert len(edge_ids) == 2

    def test_zero_diagonal(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        A, _, _ = g.dual_random_walk_adjacency()
        A_arr = np.asarray(A)
        assert np.all(np.diag(A_arr) == 0)

    def test_no_edges_returns_empty(self):
        g = Hypergraph()
        for l in "ab":
            g.add_node(Hypernode(label=l))
        A, edge_ids, _ = g.dual_random_walk_adjacency()
        A_arr = np.asarray(A)
        assert A_arr.shape == (0, 0)
        assert edge_ids == []


class TestRandomWalk:
    def test_starts_at_source(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        path = g.random_walk(nodes[0].id, steps=5)
        assert path[0] == nodes[0].id

    def test_visits_valid_nodes(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        path = g.random_walk(nodes[0].id, steps=10)
        valid = {n.id for n in nodes}
        assert all(nid in valid for nid in path)

    def test_missing_source_returns_empty(self):
        g = Hypergraph()
        assert g.random_walk("nonexistent") == []

    def test_sink_node_stops_walk(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        path = g.random_walk(nodes[2].id, steps=100)
        assert len(path) == 1
        assert path[0] == nodes[2].id


class TestRandomWalkDensity:
    def test_preserves_sum(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        rho = [0.5, 0.3, 0.1, 0.1]
        result = g.random_walk_density(rho, steps=5)
        assert abs(sum(result) - sum(rho)) < 1e-6

    def test_empty_graph(self):
        import numpy as np
        g = Hypergraph()
        result = g.random_walk_density([], steps=5)
        assert len(result) == 0

    def test_length_mismatch_returns_input(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        result = g.random_walk_density([1.0, 0.0], steps=5)
        assert list(result) == [1.0, 0.0]


class TestStationaryState:
    def test_sums_to_one(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        ids, pi = g.stationary_state()
        assert len(pi) == 4
        assert abs(sum(pi) - 1.0) < 1e-6

    def test_non_negative(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        _, pi = g.stationary_state()
        assert all(p >= -1e-10 for p in pi)

    def test_empty_graph(self):
        ids, pi = Hypergraph().stationary_state()
        assert ids == []
        assert pi == []


class TestEigenvectorCentralityNumpy:
    def test_matches_power_iteration(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        ec_pi = g.eigenvector_centrality()
        ec_np = g.eigenvector_centrality_numpy()
        pi_vals = np.array([ec_pi[n.id] for n in nodes])
        np_vals = np.array([ec_np[n.id] for n in nodes])
        assert np.corrcoef(np.abs(pi_vals), np.abs(np_vals))[0, 1] > 0.95

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.eigenvector_centrality_numpy() == {}


class TestKatzCentralitySolve:
    def test_agrees_with_iteration(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        kc_iter = g.katz_centrality(alpha=0.1)
        kc_solve = g.katz_centrality_solve(alpha=0.1)
        iter_vals = [kc_iter[n.id] for n in nodes]
        solve_vals = [kc_solve[n.id] for n in nodes]
        assert np.allclose(np.abs(iter_vals), np.abs(solve_vals), atol=0.05)

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.katz_centrality_solve() == {}


class TestSquareClustering:
    def test_complete_graph_one(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        for n in nodes:
            assert abs(g.square_clustering(n.id) - 1.0) < 1e-10

    def test_single_node_zero(self):
        g = Hypergraph()
        n = Hypernode(label="a")
        g.add_node(n)
        assert g.square_clustering(n.id) == 0.0


class TestTriangles:
    def test_complete_graph_count(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        assert g.triangles(nodes[0].id) == 3

    def test_no_triangles(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        assert g.triangles(nodes[0].id) == 0


class TestChordlessCycles:
    def test_triangle_is_chordless(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 3].id})))
        result = g.chordless_cycles()
        assert len(result) >= 1

    def test_chorded_cycle_filtered(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 4].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        result = g.chordless_cycles()
        unique_sizes = {len(set(c)) for c in result}
        assert all(s <= 3 for s in unique_sizes)

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.chordless_cycles() == []


class TestSComponentsBySize:
    def test_filters_by_min_size(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        d = Hypernode(label="d")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({d.id})))
        result = g.s_components_by_size(min_size=3)
        assert all(len(comp) >= 3 for comp in result)

    def test_default_returns_all(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        result = g.s_components_by_size()
        total_nodes = sum(len(c) for c in result)
        assert total_nodes == 3


class TestSimplicialComplex:
    def test_includes_all_faces(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id, b.id}), target_ids=frozenset({c.id})))
        sc = g.simplicial_complex()
        sizes = [len(s) for s in sc]
        assert sizes.count(1) == 3
        assert sizes.count(2) == 3
        assert sizes.count(3) == 1

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.simplicial_complex() == []


class TestBipartiteProjectedGraph:
    def test_shared_hyperedge_creates_edge(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id, b.id}), target_ids=frozenset({c.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        proj = g.bipartite_projected_graph(onto=0)
        assert proj.has_edge(a.id, b.id)
        assert proj.has_edge(a.id, c.id)
        assert proj.has_edge(b.id, c.id)

    def test_no_shared_hyperedge_no_edge(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        for n in [a, b]:
            g.add_node(n)
        proj = g.bipartite_projected_graph(onto=0)
        assert proj.number_of_edges() == 0


class TestBipartiteWeightedProjection:
    def test_jaccard_scores(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id, b.id, c.id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id, b.id}), target_ids=frozenset()))
        proj = g.bipartite_weighted_projection(onto=0)
        ab_key = (min(a.id, b.id), max(a.id, b.id))
        assert abs(proj[ab_key] - 1.0) < 1e-10

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.bipartite_weighted_projection() == {}


class TestAdjacencyTensor:
    def _make_uniform_3(self):
        g = Hypergraph()
        a, b, c, d = (Hypernode(label=l) for l in "abcd")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id, c.id}),
            weight=2.0,
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id, d.id}),
            weight=1.0,
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({c.id}),
            target_ids=frozenset({a.id, d.id}),
            weight=3.0,
        ))
        return g, a, b, c, d

    def test_uniform_3_tensor(self):
        g, a, b, c, d = self._make_uniform_3()
        result = g.adjacency_tensor()
        assert result.order == 2
        assert result.n_nodes == 4
        assert result.n_nonzero == 3
        assert result.coords is not None
        assert result.coords.shape[1] == 3
        assert result.dense_tensor is None

    def test_dense_tensor(self):
        g, a, b, c, d = self._make_uniform_3()
        result = g.adjacency_tensor(dense=True)
        assert result.dense_tensor is not None
        assert result.dense_tensor.shape == (4, 4, 4)
        node_ids = result.node_ids
        a_i = node_ids.index(a.id)
        b_i = node_ids.index(b.id)
        c_i = node_ids.index(c.id)
        d_i = node_ids.index(d.id)
        assert result.dense_tensor[a_i, b_i, c_i] == pytest.approx(2.0)
        assert result.dense_tensor[a_i, b_i, d_i] == pytest.approx(1.0)
        assert result.dense_tensor[a_i, c_i, d_i] == pytest.approx(3.0)

    def test_empty_graph(self):
        g = Hypergraph()
        result = g.adjacency_tensor()
        assert result.n_nodes == 0
        assert result.n_nonzero == 0
        assert result.coords is None

    def test_nodes_no_edges(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        result = g.adjacency_tensor()
        assert result.n_nodes == 2
        assert result.n_nonzero == 0

    def test_order_param_mixed_graph(self):
        g = Hypergraph()
        a, b, c, d = (Hypernode(label=l) for l in "abcd")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id, c.id}),
        ))
        result = g.adjacency_tensor(order=1)
        assert result.order == 1
        assert result.n_nonzero == 1

        result_2 = g.adjacency_tensor(order=2)
        assert result_2.order == 2
        assert result_2.n_nonzero == 1

    def test_auto_order_picks_most_common(self):
        g = Hypergraph()
        a, b, c, d = (Hypernode(label=l) for l in "abcd")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({c.id}),
            target_ids=frozenset({d.id}),
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id, c.id}),
        ))
        result = g.adjacency_tensor()
        assert result.order == 1

    def test_weight_accumulation(self):
        g = Hypergraph()
        a, b, c = (Hypernode(label=l) for l in "abc")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id, c.id}),
            weight=2.0,
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id, c.id}),
            weight=3.0,
        ))
        result = g.adjacency_tensor(order=2)
        assert result.n_nonzero == 1
        assert result.values[0] == pytest.approx(5.0)

    def test_pairwise_consistent_with_unweighted(self):
        g = Hypergraph()
        a, b, c = (Hypernode(label=l) for l in "abc")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
        ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({b.id}),
            target_ids=frozenset({c.id}),
        ))
        result = g.adjacency_tensor(order=1, dense=True)
        node_ids = result.node_ids
        a_i = node_ids.index(a.id)
        b_i = node_ids.index(b.id)
        c_i = node_ids.index(c.id)
        assert result.dense_tensor[a_i, b_i] == pytest.approx(1.0)
        assert result.dense_tensor[b_i, c_i] == pytest.approx(1.0)
        assert result.dense_tensor[a_i, c_i] == pytest.approx(0.0)

    def test_no_edges_of_target_order(self):
        g, a, b, c, d = self._make_uniform_3()
        result = g.adjacency_tensor(order=5)
        assert result.n_nonzero == 0
        assert result.n_nodes == 4

    def test_result_dict_access(self):
        g, a, b, c, d = self._make_uniform_3()
        result = g.adjacency_tensor()
        assert "order" in result
        assert result["order"] == 2
        assert result["n_nodes"] == 4

    def test_ghost_node_skipped_in_tensor(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        ghost_id = "ghost_id"
        edge = Hyperedge(
            source_ids=frozenset({a.id, ghost_id}),
            target_ids=frozenset({b.id}),
        )
        g._edges[edge.id] = edge
        result = g.adjacency_tensor(order=2)
        assert result.n_nonzero == 0


class TestIsDag:
    def _make_dag(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d", "e"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[4].id})))
        return g, nodes

    def _make_cycle(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        return g, nodes

    def test_dag_is_dag(self):
        g, _ = self._make_dag()
        assert g.is_dag() is True

    def test_cycle_is_not_dag(self):
        g, _ = self._make_cycle()
        assert g.is_dag() is False

    def test_empty_is_dag(self):
        g = Hypergraph()
        assert g.is_dag() is True

    def test_single_node_is_dag(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.is_dag() is True


class TestTopologicalSort:
    def test_dag_order(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        order = g.topological_sort()
        assert order is not None
        assert len(order) == 4
        assert order.index(nodes[0].id) < order.index(nodes[1].id)
        assert order.index(nodes[0].id) < order.index(nodes[2].id)
        assert order.index(nodes[1].id) < order.index(nodes[3].id)
        assert order.index(nodes[2].id) < order.index(nodes[3].id)

    def test_cycle_returns_none(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        assert g.topological_sort() is None

    def test_empty_returns_empty(self):
        g = Hypergraph()
        assert g.topological_sort() == []


class TestTransitiveClosure:
    def test_chain(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        closure = g.transitive_closure()
        assert (nodes[0].id, nodes[1].id) in closure
        assert (nodes[1].id, nodes[2].id) in closure
        assert (nodes[0].id, nodes[2].id) in closure
        assert len(closure) == 3

    def test_diamond(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        closure = g.transitive_closure()
        assert (nodes[0].id, nodes[3].id) in closure
        assert len(closure) == 5

    def test_empty(self):
        g = Hypergraph()
        assert g.transitive_closure() == set()


class TestTransitiveReduction:
    def test_chain_is_identity(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        red = g.transitive_reduction()
        assert (nodes[0].id, nodes[1].id) in red
        assert (nodes[1].id, nodes[2].id) in red
        assert len(red) == 2

    def test_removes_redundant(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        red = g.transitive_reduction()
        assert (nodes[0].id, nodes[1].id) in red
        assert (nodes[1].id, nodes[2].id) in red
        assert (nodes[0].id, nodes[2].id) not in red
        assert len(red) == 2

    def test_empty(self):
        g = Hypergraph()
        assert g.transitive_reduction() == set()


class TestDagLongestPath:
    def test_chain(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        path = g.dag_longest_path()
        assert len(path) == 4
        assert path[0] == nodes[0].id
        assert path[-1] == nodes[3].id

    def test_diamond(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        path = g.dag_longest_path()
        assert len(path) == 3

    def test_cycle_returns_empty(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        assert g.dag_longest_path() == []

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.dag_longest_path() == []

    def test_nodes_no_edges(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(label=label))
        path = g.dag_longest_path()
        assert len(path) == 1


class TestDagLongestPathLength:
    def test_chain(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        assert g.dag_longest_path_length() == 3

    def test_cycle_returns_minus_one(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[0].id})))
        assert g.dag_longest_path_length() == -1

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.dag_longest_path_length() == 0


class TestIsTree:
    def test_simple_tree(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[3].id})))
        assert g.is_tree() is True

    def test_cycle_not_tree(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        assert g.is_tree() is False

    def test_empty_not_tree(self):
        g = Hypergraph()
        assert g.is_tree() is False

    def test_single_node_is_tree(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.is_tree() is True

    def test_disconnected_not_tree(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        assert g.is_tree() is False


class TestIsForest:
    def test_single_tree_is_forest(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        assert g.is_forest() is True

    def test_two_disconnected_trees(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        assert g.is_forest() is True

    def test_cycle_not_forest(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        assert g.is_forest() is False

    def test_empty_is_forest(self):
        g = Hypergraph()
        assert g.is_forest() is True

    def test_isolated_nodes_are_forest(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(label=label))
        assert g.is_forest() is True

    def test_cycle_component_plus_isolated_pair(self):
        g = Hypergraph()
        t0 = Hypernode(label="t0")
        t1 = Hypernode(label="t1")
        t2 = Hypernode(label="t2")
        p0 = Hypernode(label="p0")
        p1 = Hypernode(label="p1")
        for n in [t0, t1, t2, p0, p1]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({t0.id}), target_ids=frozenset({t1.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({t1.id}), target_ids=frozenset({t2.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({t2.id}), target_ids=frozenset({t0.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({p0.id}), target_ids=frozenset({p1.id})))
        assert g.is_forest() is False


class TestMinimumSpanningEdges:
    def test_simple(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=3.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), weight=2.0))
        mst = g.minimum_spanning_edges()
        assert len(mst) == 3

    def test_empty(self):
        g = Hypergraph()
        assert g.minimum_spanning_edges() == []

    def test_hyperedge_no_duplicate_ids(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), weight=3.0))
        mst = g.minimum_spanning_edges()
        assert len(mst) == len(set(mst))

    def test_skip_degenerate_edge(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset(), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), weight=3.0))
        assert len(g.minimum_spanning_edges()) == 1


class TestMinimumSpanningTree:
    def test_returns_pairs(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=3.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}), weight=1.0))
        mst = g.minimum_spanning_tree()
        assert len(mst) == 2
        for u, v in mst:
            assert u != v


class TestSpanningTreeCount:
    def test_complete_graph_4(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(Hyperedge(
                    source_ids=frozenset({nodes[i].id}),
                    target_ids=frozenset({nodes[j].id}),
                ))
        assert g.spanning_tree_count() == 16

    def test_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.spanning_tree_count() == 1

    def test_empty(self):
        g = Hypergraph()
        assert g.spanning_tree_count() == 0


class TestTreeCenter:
    def test_even_length_path(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        center = g.tree_center()
        assert len(center) == 2
        assert set(center) == {nodes[1].id, nodes[2].id}

    def test_odd_length_path(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        center = g.tree_center()
        assert center == [nodes[1].id]

    def test_non_tree_returns_empty(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        assert g.tree_center() == []

    def test_empty_returns_empty(self):
        g = Hypergraph()
        assert g.tree_center() == []


class TestMaxFlow:
    def _make_flow_graph(self):
        g = Hypergraph()
        nodes = []
        for label in ["s", "a", "b", "c", "t"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        s, a, b, c, t = nodes
        g.add_edge(Hyperedge(source_ids=frozenset({s.id}), target_ids=frozenset({a.id}), weight=10.0))
        g.add_edge(Hyperedge(source_ids=frozenset({s.id}), target_ids=frozenset({b.id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), weight=15.0))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({t.id}), weight=10.0))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), weight=10.0))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({t.id}), weight=10.0))
        return g, nodes

    def test_max_flow_value(self):
        g, nodes = self._make_flow_graph()
        s, _a, _b, _c, t = nodes
        flow_val, _ = g.max_flow(s.id, t.id)
        assert flow_val == pytest.approx(15.0)

    def test_max_flow_flow_dict(self):
        g, nodes = self._make_flow_graph()
        s, _a, _b, _c, t = nodes
        _, flow_dict = g.max_flow(s.id, t.id)
        assert len(flow_dict) > 0
        for f in flow_dict.values():
            assert f > 0

    def test_max_flow_no_path(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        flow_val, flow_dict = g.max_flow(a.id, b.id)
        assert flow_val == 0.0
        assert flow_dict == {}

    def test_max_flow_same_node(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        flow_val, _ = g.max_flow(a.id, a.id)
        assert flow_val == 0.0

    def test_max_flow_self_loop_skipped(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({a.id}), weight=99.0))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), weight=5.0))
        flow_val, flow_dict = g.max_flow(a.id, b.id)
        assert flow_val == pytest.approx(5.0)
        assert (a.id, b.id) in flow_dict
        assert flow_dict[(a.id, b.id)] == pytest.approx(5.0)

    def test_max_flow_missing_node(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        flow_val, flow_dict = g.max_flow(a.id, "nonexistent")
        assert flow_val == 0.0
        assert flow_dict == {}


class TestMinCutSt:
    def test_min_cut_equals_max_flow(self):
        g = Hypergraph()
        nodes = []
        for label in ["s", "a", "t"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=3.0))
        cut_val, (left, right) = g.min_cut_st(nodes[0].id, nodes[2].id)
        assert cut_val == pytest.approx(3.0)
        assert nodes[0].id in left
        assert nodes[2].id in right


class TestMinCutGlobal:
    def test_simple(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=3.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), weight=3.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}), weight=2.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id}), weight=2.0))
        cut_val, (left, right) = g.min_cut_global()
        assert cut_val == pytest.approx(5.0)
        assert len(left) + len(right) == 4
        assert len(left) > 0 and len(right) > 0

    def test_single_node(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        cut_val, (left, right) = g.min_cut_global()
        assert cut_val == 0.0


class TestMaxWeightMatching:
    def test_simple(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=3.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), weight=4.0))
        matching = g.max_weight_matching()
        assert len(matching) == 2
        covered = set()
        for pair in matching:
            covered.update(pair)
        assert len(covered) == 4

    def test_empty(self):
        g = Hypergraph()
        assert g.max_weight_matching() == set()

    def test_prefers_heavier(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=10.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=1.0))
        matching = g.max_weight_matching()
        assert frozenset({nodes[0].id, nodes[1].id}) in matching


class TestBipartiteMaximumMatching:
    def test_simple(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        left = {nodes[0].id, nodes[1].id}
        right = {nodes[2].id, nodes[3].id}
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        matching = g.bipartite_maximum_matching(left, right)
        assert len(matching) == 2

    def test_no_edges(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        matching = g.bipartite_maximum_matching({nodes[0].id}, {nodes[1].id})
        assert matching == set()

    def test_reverse_direction(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        left = {nodes[0].id, nodes[1].id}
        right = {nodes[2].id, nodes[3].id}
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[1].id})))
        matching = g.bipartite_maximum_matching(left, right)
        assert len(matching) == 2


class TestBipartiteMaxWeightMatching:
    def test_prefers_heavier(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        left = {nodes[0].id, nodes[1].id}
        right = {nodes[2].id, nodes[3].id}
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}), weight=10.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[3].id}), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id}), weight=5.0))
        matching = g.bipartite_max_weight_matching(left, right)
        assert len(matching) == 2


class TestMinEdgeCover:
    def test_simple(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), weight=3.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), weight=4.0))
        cover = g.min_edge_cover()
        covered = set()
        for pair in cover:
            covered.update(pair)
        assert len(covered) == 4

    def test_empty(self):
        g = Hypergraph()
        assert g.min_edge_cover() == set()

    def test_uncovered_node(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        c = Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), weight=5.0))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), weight=3.0))
        cover = g.min_edge_cover()
        covered = set()
        for pair in cover:
            covered.update(pair)
        assert len(cover) == 2
        assert covered == {a.id, b.id, c.id}


class TestMinimumCycleBasis:
    def test_triangle(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        basis = g.minimum_cycle_basis()
        assert len(basis) == 1
        assert len(basis[0]) == 3
        assert set(basis[0]) == {nodes[0].id, nodes[1].id, nodes[2].id}

    def test_two_triangles(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c", "d"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[0].id})))
        basis = g.minimum_cycle_basis()
        assert len(basis) == 2
        for cycle in basis:
            assert len(cycle) == 3

    def test_no_cycles(self):
        g = Hypergraph()
        nodes = []
        for label in ["a", "b", "c"]:
            n = Hypernode(label=label)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        assert g.minimum_cycle_basis() == []

    def test_empty(self):
        g = Hypergraph()
        assert g.minimum_cycle_basis() == []


class TestEncapsulationDag:
    def test_nested_edges(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        e1 = Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset())
        e2 = Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset())
        g.add_edge(e1)
        g.add_edge(e2)
        dag = g.encapsulation_dag()
        assert len(dag) == 1
        assert dag[0] == (e1.id, e2.id)

    def test_no_containment(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abcd"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        assert g.encapsulation_dag() == []

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.encapsulation_dag() == []

    def test_single_edge(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "ab"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        assert g.encapsulation_dag() == []


class TestSimpliciality:
    def test_simplicial_complex(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        assert g.simpliciality() == 1.0

    def test_no_containment_pairs(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abcd"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        assert g.simpliciality() == 1.0

    def test_empty_and_single(self):
        g = Hypergraph()
        assert g.simpliciality() == 1.0
        n = Hypernode(label="a")
        g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id}), target_ids=frozenset()))
        assert g.simpliciality() == 1.0


class TestFaceEnumeration:
    def test_triangle_face_enum(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id for n in nodes}), target_ids=frozenset()))
        tri = frozenset({n.id for n in nodes})
        result = g.face_enumeration(tri)
        assert len(result["faces"]) == 6
        assert len(result["cofaces"]) == 0

    def test_edge_cofaces(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        edge = frozenset({nodes[0].id, nodes[1].id})
        result = g.face_enumeration(edge)
        assert len(result["faces"]) == 2
        assert frozenset({nodes[0].id}) in result["faces"]
        assert frozenset({nodes[1].id}) in result["faces"]
        assert len(result["cofaces"]) == 1
        assert frozenset({nodes[0].id, nodes[1].id, nodes[2].id}) in result["cofaces"]

    def test_vertex_faces(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id for n in nodes}), target_ids=frozenset()))
        result = g.face_enumeration(frozenset({nodes[0].id}))
        assert result["faces"] == []
        assert len(result["cofaces"]) == 3


class TestBoundaryOperator:
    def test_triangle_boundary(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id for n in nodes}), target_ids=frozenset()))
        bd = g.boundary_operator(2)
        tri = frozenset({n.id for n in nodes})
        assert tri in bd
        assert len(bd[tri]) == 3
        signs = {face: sign for face, sign in bd[tri]}
        assert set(signs.values()) == {1, -1}

    def test_edge_boundary(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        bd = g.boundary_operator(1)
        edge = frozenset({nodes[0].id, nodes[1].id})
        assert edge in bd
        assert len(bd[edge]) == 2
        faces = [f for f, _ in bd[edge]]
        assert frozenset({nodes[0].id}) in faces
        assert frozenset({nodes[1].id}) in faces

    def test_zero_dim_empty(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "ab"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        assert g.boundary_operator(0) == {}


class TestHodgeMatrix:
    def test_triangle_hodge_1(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id for n in nodes}), target_ids=frozenset()))
        B, k_simplices, km1_simplices = g.hodge_matrix(2)
        assert B.shape == (3, 1)
        assert len(k_simplices) == 1
        assert len(km1_simplices) == 3

    def test_empty(self):
        g = Hypergraph()
        B, rows, cols = g.hodge_matrix(1)
        assert B.shape == (0, 0)
        assert rows == []
        assert cols == []


class TestHodgeLaplacian:
    def test_zero_laplacian_connected(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "ab"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        L = g.hodge_laplacian(0)
        assert L.shape == (2, 2)
        import numpy as np
        eigenvalues = np.linalg.eigvalsh(L)
        near_zero = sum(1 for ev in eigenvalues if abs(ev) < 1e-10)
        assert near_zero == 1

    def test_disconnected_two_components(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abcd"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        L = g.hodge_laplacian(0)
        import numpy as np
        eigenvalues = np.linalg.eigvalsh(L)
        near_zero = sum(1 for ev in eigenvalues if abs(ev) < 1e-10)
        assert near_zero == 2

    def test_empty(self):
        g = Hypergraph()
        import numpy as np
        L = g.hodge_laplacian(0)
        assert L.shape == (0, 0)


class TestBettiCurve:
    def test_triangle(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id for n in nodes}), target_ids=frozenset()))
        betti = g.betti_curve()
        assert len(betti) >= 1
        assert betti[0] == 1

    def test_disconnected(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abcd"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        betti = g.betti_curve()
        assert betti[0] == 2

    def test_max_dim(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id for n in nodes}), target_ids=frozenset()))
        betti = g.betti_curve(max_dim=0)
        assert len(betti) == 1

    def test_empty(self):
        g = Hypergraph()
        assert g.betti_curve() == []


class TestPersistenceDiagram:
    def test_single_edge(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "ab"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset(), weight=1.0))
        pd = g.persistence_diagram()
        births_dim0 = [b for d, b, _ in pd if d == 0]
        deaths_dim0 = [de for d, b, de in pd if d == 0 and de is not None]
        assert len(births_dim0) == 2
        assert len(deaths_dim0) == 1
        assert deaths_dim0[0] == 1.0

    def test_two_edges_merge(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset(), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset(), weight=2.0))
        pd = g.persistence_diagram()
        deaths_dim0 = [de for d, b, de in pd if d == 0 and de is not None]
        assert len(deaths_dim0) == 2
        assert sorted(deaths_dim0) == [1.0, 2.0]

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.persistence_diagram() == []

    def test_no_edges(self):
        g = Hypergraph()
        for l in "ab":
            g.add_node(Hypernode(label=l))
        assert g.persistence_diagram() == []

    def test_betti1_birth_triangle(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset(), weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset(), weight=2.0))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset(), weight=3.0))
        pd = g.persistence_diagram()
        dim1_births = [b for d, b, _ in pd if d == 1]
        assert len(dim1_births) > 0


class TestDetectMotifs:
    def test_triangle_motifs(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset()))
        result = g.detect_motifs(order=3, runs_config_model=5, seed=42)
        assert "motif_2_2_2" in result.observed
        assert result.observed["motif_2_2_2"] == 1

    def test_path_motifs(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abcd"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        result = g.detect_motifs(order=3, runs_config_model=5, seed=42)
        assert sum(result.observed.values()) > 0
        assert "motif_1_1_2" in result.observed

    def test_empty(self):
        g = Hypergraph()
        result = g.detect_motifs()
        assert result.observed == {}

    def test_z_scores(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(10)]
        for n in nodes:
            g.add_node(n)
        for i in range(9):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id, nodes[i + 1].id}), target_ids=frozenset()))
        result = g.detect_motifs(order=3, runs_config_model=10, seed=42)
        assert len(result.z_scores) > 0


class TestSimplicialContagion:
    def test_basic_spread(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abcde"]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id, nodes[i + 1].id}), target_ids=frozenset()))
        result = g.simplicial_contagion(
            {nodes[0].id}, beta=0.8, mu=0.1, timesteps=50, seed=42,
        )
        assert len(result.infected_fraction) == 51
        assert result.infected_fraction[0] == pytest.approx(0.2, abs=0.01)
        assert result.infected_fraction[-1] > result.infected_fraction[0]

    def test_zero_beta(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        result = g.simplicial_contagion(
            {nodes[0].id}, beta=0.0, mu=0.0, timesteps=10, seed=42,
        )
        assert all(f == pytest.approx(1 / 3, abs=0.01) for f in result.infected_fraction[1:])

    def test_full_recovery(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        result = g.simplicial_contagion(
            {nodes[0].id}, beta=0.0, mu=1.0, timesteps=5, seed=42,
        )
        assert result.infected_fraction[-1] == pytest.approx(0.0, abs=0.01)

    def test_empty(self):
        g = Hypergraph()
        result = g.simplicial_contagion(set(), timesteps=10)
        assert result.timesteps == 10


class TestSimulateKuramoto:
    def test_basic(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        result = g.simulate_kuramoto(k2=1.0, k3=0.0, timesteps=100, dt=0.01, seed=42)
        assert result.theta_time.shape == (101, 3)
        assert len(result.order_parameter) == 101
        assert all(0 <= r <= 1 for r in result.order_parameter)

    def test_sync_with_coupling(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abc"]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset()))
        import numpy as np
        omega = np.zeros(3)
        result = g.simulate_kuramoto(k2=5.0, k3=0.0, omega=omega, timesteps=1000, dt=0.01, seed=42)
        assert result.order_parameter[-1] > 0.8

    def test_empty(self):
        g = Hypergraph()
        result = g.simulate_kuramoto(timesteps=10)
        assert result.theta_time is None


class TestMSF:
    def test_basic_structure(self):
        g = Hypergraph()
        nodes = [Hypernode(label=l) for l in "abcde"]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id, nodes[i + 1].id}), target_ids=frozenset()))

        import numpy as np

        def F(x, p):
            return np.array([-x[1], x[0]])

        def JF(x, p):
            return np.array([[0, -1], [1, 0]])

        def JH(x, p):
            return np.array([[0, 0], [0, 0]])

        result = g.master_stability_function(F, JF, JH, integration_time=10.0, integration_step=0.01)
        assert len(result.alpha_values) > 0
        assert len(result.lambda_max) == len(result.alpha_values)

    def test_empty(self):
        g = Hypergraph()
        result = g.master_stability_function(lambda x, p: x, lambda x, p: x, lambda x, p: x)
        assert result.alpha_values == []


class TestGreedyColor:
    def test_path_graph_two_colors(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        colors = g.greedy_color()
        assert max(colors.values()) + 1 == 2

    def test_triangle_three_colors(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 3].id})))
        colors = g.greedy_color()
        assert max(colors.values()) + 1 == 3

    def test_empty_graph(self):
        g = Hypergraph()
        colors = g.greedy_color()
        assert colors == {}

    def test_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        colors = g.greedy_color()
        assert len(colors) == 1
        assert colors[list(colors.keys())[0]] == 0

    def test_no_adjacent_same_color(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(6)]
        for n in nodes:
            g.add_node(n)
        pairs = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5), (1, 4)]
        for i, j in pairs:
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
        colors = g.greedy_color()
        for i, j in pairs:
            assert colors[nodes[i].id] != colors[nodes[j].id]

    def test_hyperedge_projects_to_pairwise(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id, nodes[2].id, nodes[3].id})))
        colors = g.greedy_color()
        for i in range(4):
            for j in range(i + 1, 4):
                assert colors[nodes[i].id] != colors[nodes[j].id]

    def test_all_strategies(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        for strategy in ["largest_first", "smallest_last", "random_sequential",
                         "connected_sequential_bfs", "connected_sequential_dfs",
                         "saturation_largest_first"]:
            colors = g.greedy_color(strategy=strategy)
            assert len(colors) == 5
            assert max(colors.values()) + 1 <= 3

    def test_interchange(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        colors = g.greedy_color(interchange=True)
        assert max(colors.values()) + 1 == 2


class TestChromaticNumber:
    def test_path(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        assert g.chromatic_number() == 2

    def test_empty(self):
        g = Hypergraph()
        assert g.chromatic_number() == 0

    def test_complete_graph(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            for j in range(i + 1, 4):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
        assert g.chromatic_number() == 4


class TestEquitableColor:
    def test_balanced_color_classes(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(6)]
        for n in nodes:
            g.add_node(n)
        for i in range(5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        colors = g.equitable_color(3)
        class_sizes = {}
        for c in colors.values():
            class_sizes[c] = class_sizes.get(c, 0) + 1
        sizes = list(class_sizes.values())
        assert max(sizes) - min(sizes) <= 1

    def test_empty(self):
        g = Hypergraph()
        colors = g.equitable_color(1)
        assert colors == {}

    def test_no_adjacent_same_color(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        colors = g.equitable_color(3)
        for i in range(3):
            assert colors[nodes[i].id] != colors[nodes[i + 1].id]


class TestDirectedMotifs:
    def test_chain(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        result = g.detect_directed_motifs(order=3, runs_config_model=5, seed=42)
        assert len(result.observed) > 0
        assert "z_scores" in result

    def test_empty(self):
        g = Hypergraph()
        result = g.detect_directed_motifs()
        assert result.observed == {}

    def test_two_nodes_too_few(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(2)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        result = g.detect_directed_motifs(order=3)
        assert result.observed == {}

    def test_three_node_cycle(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 3].id})))
        result = g.detect_directed_motifs(order=3, runs_config_model=0, seed=42)
        assert len(result.observed) > 0
        assert sum(result.observed.values()) == 1

    def test_result_type(self):
        from hyper3.kernel_dynamics import DirectedMotifResult
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        result = g.detect_directed_motifs(order=3, runs_config_model=2, seed=0)
        assert isinstance(result, DirectedMotifResult)
        assert "observed" in result
        assert result["z_scores"] is not None


class TestSubhypergraphByOrder:
    def test_filter_pairwise(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id, nodes[2].id})))
        sub = g.subhypergraph_by_order({1})
        assert sub.edge_count == 1
        assert sub.node_count == 4

    def test_filter_higher_order(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id, nodes[2].id})))
        sub = g.subhypergraph_by_order({2})
        assert sub.edge_count == 1
        assert sub.node_count == 4

    def test_multiple_orders(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id, nodes[2].id})))
        sub = g.subhypergraph_by_order({1, 2})
        assert sub.edge_count == 2

    def test_empty_result(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        sub = g.subhypergraph_by_order({5})
        assert sub.edge_count == 0
        assert sub.node_count == 3

    def test_preserves_all_nodes(self):
        from hyper3.generators import random_hypergraph
        g = random_hypergraph(8, {0: 0.5, 1: 0.3}, seed=42)
        sub = g.subhypergraph_by_order({1})
        assert sub.node_count == g.node_count


class TestAttributeAssortativity:
    def test_perfect_assortative(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}", data={"group": "a"}) for i in range(3)]
        for i in range(3):
            nodes[i].data = {"group": "a" if i < 2 else "b"}
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        r = g.attribute_assortativity("group")
        assert -1.0 <= r <= 1.0

    def test_no_attribute(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        r = g.attribute_assortativity("missing")
        assert r == 0.0

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.attribute_assortativity("x") == 0.0


class TestAverageNeighborDegree:
    def test_path_graph(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        result = g.average_neighbor_degree()
        assert len(result) == 4

    def test_empty_graph(self):
        g = Hypergraph()
        result = g.average_neighbor_degree()
        assert result == {}

    def test_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        result = g.average_neighbor_degree()
        assert len(result) == 1


class TestAverageDegreeConnectivity:
    def test_path_graph(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        result = g.average_degree_connectivity()
        assert 1 in result
        assert 2 in result

    def test_empty_graph(self):
        g = Hypergraph()
        result = g.average_degree_connectivity()
        assert result == {}


class TestDirectedLineGraph:
    def test_chain(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        dlg = g.to_directed_line_graph()
        assert dlg.number_of_nodes() == 3
        assert dlg.number_of_edges() == 2

    def test_empty(self):
        g = Hypergraph()
        dlg = g.to_directed_line_graph()
        assert dlg.number_of_nodes() == 0

    def test_no_directed_adjacency(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        dlg = g.to_directed_line_graph()
        assert dlg.number_of_edges() == 0

    def test_cycle(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 3].id})))
        dlg = g.to_directed_line_graph()
        assert dlg.number_of_nodes() == 3
        assert dlg.number_of_edges() == 3


class TestSWalkPaths:
    def test_path_exists(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        edges = list(g._edges.keys())
        path = g.s_walk_shortest_path(edges[0], edges[2], s=1)
        assert path is not None
        assert path[0] == edges[0]
        assert path[-1] == edges[2]

    def test_path_length(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        edges = list(g._edges.keys())
        length = g.s_walk_shortest_path_length(edges[0], edges[2], s=1)
        assert length == 2.0

    def test_no_path(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        edges = list(g._edges.keys())
        path = g.s_walk_shortest_path(edges[0], edges[1], s=1)
        assert path is None
        assert g.s_walk_shortest_path_length(edges[0], edges[1], s=1) == float("inf")

    def test_nonexistent_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        assert g.s_walk_shortest_path("fake1", "fake2", s=1) is None
        assert g.s_walk_shortest_path_length("fake1", "fake2", s=1) == float("inf")

    def test_distance_matrix(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
        dm = g.s_walk_distance_matrix(s=1)
        edges = list(g._edges.keys())
        assert len(dm) == 3
        assert dm[edges[0]][edges[0]] == 0.0
        assert dm[edges[0]][edges[2]] == 2.0

    def test_self_distance_zero(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        edges = list(g._edges.keys())
        assert g.s_walk_shortest_path_length(edges[0], edges[0], s=1) == 0.0


class TestTransitivityStarGraph:
    def test_star_no_triads(self):
        g = Hypergraph()
        center = Hypernode(label="center")
        g.add_node(center)
        leaves = [Hypernode(label=f"leaf{i}") for i in range(4)]
        for lf in leaves:
            g.add_node(lf)
            g.add_edge(Hyperedge(source_ids=frozenset({center.id}), target_ids=frozenset({lf.id})))
        assert g.transitivity() == 0.0

    def test_chain_no_triads(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i + 1].id}), target_ids=frozenset({nodes[i].id})))
        assert g.transitivity() == 0.0


class TestSquareClusteringTwoHop:
    def test_square_two_hop_contribution(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[4].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[4].id}), target_ids=frozenset({nodes[3].id})))
        sc = g.square_clustering(nodes[4].id)
        assert 0.0 <= sc <= 1.0


class TestSpectralClusteringDegenerate:
    def test_isolated_nodes_exception_fallback(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        clusters = g.spectral_clustering(k=2)
        assert len(clusters) >= 1
        total = sum(len(c) for c in clusters)
        assert total == 4

    def test_single_node_no_exception(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="only"))
        clusters = g.spectral_clustering(k=2)
        assert len(clusters) == 1
        assert len(clusters[0]) == 1


class TestSpectralClusteringConvergence:
    def test_kmeans_converges(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(8)]
        for n in nodes:
            g.add_node(n)
        for i in range(3):
            for j in range(i + 1, 4):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        for i in range(4, 7):
            for j in range(i + 1, 8):
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))
                g.add_edge(Hyperedge(source_ids=frozenset({nodes[j].id}), target_ids=frozenset({nodes[i].id})))
        clusters = g.spectral_clustering(k=2)
        assert len(clusters) == 2
        assert sum(len(c) for c in clusters) == 8


class TestCanonicalDirectedMotifEmpty:
    def test_three_isolated_nodes_empty_motif(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        result = g.detect_directed_motifs(order=3, runs_config_model=2, seed=42)
        assert len(result.observed) > 0
        assert any("empty" in k for k in result.observed)

    def test_mixed_empty_and_nonempty_motifs(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        result = g.detect_directed_motifs(order=3, runs_config_model=2, seed=42)
        assert len(result.observed) > 0


class TestMotifZScoresZeroStd:
    def test_z_score_zero_when_null_constant(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        result = g.detect_motifs(order=3, runs_config_model=0, seed=42)
        for v in result.z_scores.values():
            assert v == 0.0


class TestRandomizePairwiseSingleEdge:
    def test_single_edge_skips_swaps(self):
        from hyper3.kernel_dynamics import DynamicsMixin
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        result = g.detect_motifs(order=3, runs_config_model=5, seed=42)
        assert len(result.observed) > 0

    def test_randomize_empty_adjacency(self):
        import random

        from hyper3.kernel_dynamics import DynamicsMixin
        adj = {"a": set(), "b": set(), "c": set()}
        result = DynamicsMixin._randomize_pairwise(adj, ["a", "b", "c"], random.Random(42))
        for v in result.values():
            assert v == set()


class TestSimplicialContagionBetaDelta:
    def test_beta_delta_with_multi_infected_edge(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        result = g.simplicial_contagion(
            {nodes[0].id, nodes[1].id},
            beta=0.1, beta_delta=0.9,
            mu=0.0, timesteps=20, seed=42,
        )
        assert len(result.infected_fraction) == 21
        assert result.infected_fraction[-1] >= result.infected_fraction[0]


class TestKuramotoTripleCoupling:
    def test_hyperedge_triple_coupling(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        omega = np.zeros(4)
        theta0 = np.array([0.0, 0.5, 1.0, 1.5])
        result = g.simulate_kuramoto(k2=1.0, k3=0.5, omega=omega, theta0=theta0, timesteps=100, dt=0.01, seed=42)
        assert result.theta_time.shape == (101, 4)
        assert len(result.order_parameter) == 101

    def test_hyperedge_four_members_produces_triples(self):
        import numpy as np
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        omega = np.zeros(4)
        theta0 = np.array([0.0, 0.3, 0.6, 0.9])
        result = g.simulate_kuramoto(k2=0.0, k3=2.0, omega=omega, theta0=theta0, timesteps=500, dt=0.01, seed=42)
        assert result.theta_time.shape == (501, 4)
        assert result.order_parameter[-1] > 0.3


class TestMSFLambdaZero:
    def test_zero_integration_steps_returns_zero(self):
        import numpy as np

        from hyper3.kernel_dynamics import DynamicsMixin

        def F(x, p):
            return np.array([-x[1], x[0]])

        def JF(x, p):
            return np.array([[0, -1], [1, 0]])

        def JH(x, p):
            return np.array([[0, 0], [0, 0]])

        lam = DynamicsMixin._compute_msf_lambda(F, JF, JH, 0.5, {}, 0.001, 0.01, None)
        assert lam == 0.0

    def test_small_integration_hits_transient(self):
        import numpy as np

        from hyper3.kernel_dynamics import DynamicsMixin

        def F(x, p):
            return np.array([-x[1], x[0]])

        def JF(x, p):
            return np.array([[0, -1], [1, 0]])

        def JH(x, p):
            return np.array([[0, 0], [0, 0]])

        lam = DynamicsMixin._compute_msf_lambda(F, JF, JH, 0.5, {}, 0.05, 0.01, 42)
        assert isinstance(lam, float)


class TestRandomizeDirectedEdgeCases:
    def test_empty_directed_edges(self):
        import random

        from hyper3.kernel_dynamics import DynamicsMixin
        adj = {"a": set(), "b": set(), "c": set()}
        result = DynamicsMixin._randomize_directed(adj, ["a", "b", "c"], random.Random(42))
        for v in result.values():
            assert v == set()

    def test_single_directed_edge_no_swap(self):
        import random

        from hyper3.kernel_dynamics import DynamicsMixin
        adj = {"a": {"b"}, "b": set(), "c": set()}
        result = DynamicsMixin._randomize_directed(adj, ["a", "b", "c"], random.Random(42))
        total_edges = sum(len(v) for v in result.values())
        assert total_edges == 1


class TestTransitionMatrixDelegation:
    def test_dynamics_transition_matrix_delegates(self):
        import numpy as np

        from hyper3.kernel_dynamics import DynamicsMixin
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        P, ids = DynamicsMixin.transition_matrix(g)
        P_arr = np.asarray(P.todense())
        assert P_arr.shape == (3, 3)
        assert len(ids) == 3


class TestHyperedgeSimilarityEmptyNodes:
    def test_query_edge_empty_nodes(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        empty_edge = Hyperedge(source_ids=frozenset(), target_ids=frozenset())
        g.add_edge(empty_edge)
        result = g.hyperedge_similarity(empty_edge.id)
        assert len(result.similar_edges) == 0

    def test_candidate_edge_empty_nodes(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        c = Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        query = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}))
        empty_candidate = Hyperedge(source_ids=frozenset(), target_ids=frozenset())
        g.add_edge(query)
        g.add_edge(empty_candidate)
        result = g.hyperedge_similarity(query.id)
        assert len(result.similar_edges) == 0


class TestChordlessCyclesMaxCycles:
    def test_max_cycles_limits_chordless(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(5):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 5].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[3].id})))
        all_chordless = g.chordless_cycles(max_cycles=50)
        limited = g.chordless_cycles(max_cycles=1)
        assert len(limited) <= 1
        assert len(limited) <= len(all_chordless)

    def test_four_cycle_is_chordless(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 4].id})))
        result = g.chordless_cycles()
        assert len(result) >= 1
        for cycle in result:
            unique = cycle[:-1]
            assert len(unique) == 4


class TestDetectCyclesDFSMaxCycles:
    def test_multiple_cycles_same_root_hit_limit(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(6)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[4].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[4].id}), target_ids=frozenset({nodes[0].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[5].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[5].id}), target_ids=frozenset({nodes[0].id})))
        all_cycles = g.detect_cycles(max_cycles=10)
        assert len(all_cycles) >= 3
        limited = g.detect_cycles(max_cycles=1)
        assert len(limited) == 1


class TestEdgeLabelIndex:
    def _make_graph(self):
        g = Hypergraph()
        a = Hypernode(id="a")
        b = Hypernode(id="b")
        c = Hypernode(id="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        return g

    def test_edges_by_label_returns_matching_edges(self):
        g = self._make_graph()
        e1 = Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes")
        e2 = Hyperedge(id="e2", source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="causes")
        e3 = Hyperedge(id="e3", source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="enables")
        g.add_edge(e1)
        g.add_edge(e2)
        g.add_edge(e3)
        causes = g.edges_by_label("causes")
        assert len(causes) == 2
        assert {e.id for e in causes} == {"e1", "e2"}

    def test_edges_by_label_unknown_returns_empty(self):
        g = self._make_graph()
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes"))
        assert g.edges_by_label("unknown") == []

    def test_empty_label_edges_not_indexed(self):
        g = self._make_graph()
        g.add_edge(Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label=""))
        g.add_edge(Hyperedge(id="e2", source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="causes"))
        assert g.edges_by_label("") == []
        assert len(g.edges_by_label("causes")) == 1

    def test_remove_edge_updates_label_index(self):
        g = self._make_graph()
        e1 = Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes")
        e2 = Hyperedge(id="e2", source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="causes")
        g.add_edge(e1)
        g.add_edge(e2)
        assert len(g.edges_by_label("causes")) == 2
        g.remove_edge("e1")
        assert len(g.edges_by_label("causes")) == 1
        assert g.edges_by_label("causes")[0].id == "e2"

    def test_remove_last_edge_for_label_cleans_up_key(self):
        g = self._make_graph()
        e1 = Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes")
        g.add_edge(e1)
        assert len(g.edges_by_label("causes")) == 1
        g.remove_edge("e1")
        assert g.edges_by_label("causes") == []
        assert "causes" not in g._edge_label_index

    def test_remove_node_cleans_up_label_index(self):
        g = self._make_graph()
        e1 = Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes")
        g.add_edge(e1)
        g.remove_node("b")
        assert g.edges_by_label("causes") == []
        assert "causes" not in g._edge_label_index

    def test_label_index_after_batch_operations(self):
        g = self._make_graph()
        g.begin_batch()
        g.add_edge(Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes"))
        g.add_edge(Hyperedge(id="e2", source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="causes"))
        g.end_batch()
        assert len(g.edges_by_label("causes")) == 2

    def test_multiple_labels_independent(self):
        g = self._make_graph()
        g.add_edge(Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes"))
        g.add_edge(Hyperedge(id="e2", source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="enables"))
        g.add_edge(Hyperedge(id="e3", source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="causes"))
        assert len(g.edges_by_label("causes")) == 2
        assert len(g.edges_by_label("enables")) == 1
        g.remove_edge("e1")
        assert len(g.edges_by_label("causes")) == 1
        assert len(g.edges_by_label("enables")) == 1

