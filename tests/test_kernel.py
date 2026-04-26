import time
import pytest
from hyper3 import (
    AbstractionLayer,
    EquivalenceEngine,
    EventLog,
    Hyperedge,
    Hypergraph,
    Hypernode,
    LazyCache,
    Metadata,
    Modality,
    ObserverSlice,
    SelfEvolutionEngine,
    TraversalEngine,
)


class TestHypernode:
    def test_default_creation(self):
        node = Hypernode()
        assert node.id
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
        assert edge.id
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
        assert g.remove_node("n1")
        assert g.node_count == 0
        assert not g.remove_node("n1")

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
        assert g.remove_edge("e1")
        assert g.edge_count == 0
        assert not g.remove_edge("e1")

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
        assert len(g.edges_for("a")) == 2

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
        assert len(result) <= 3

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
        assert len(result) < 5

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
        assert root.access_count >= 1


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
        assert len(result) <= 5

    def test_broaden(self):
        g = self._build_graph()
        obs = ObserverSlice(g)
        result = obs.broaden("root", max_depth=5, max_nodes=100)
        assert len(result) >= 1

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


class TestSelfEvolutionEngine:
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
        engine = SelfEvolutionEngine(g, decay_threshold=0.1)
        decayed = engine.decay_weights(factor=0.5)
        a = g.get_node("a")
        assert a.weight == pytest.approx(0.5)

    def test_prune_dead_nodes(self):
        g = self._build_graph()
        engine = SelfEvolutionEngine(g, decay_threshold=0.1)
        g.get_node("c").weight = 0.05
        pruned = engine.prune_dead_nodes()
        assert "c" in pruned
        assert g.node_count == 3

    def test_merge_equivalences(self):
        g = self._build_graph()
        engine = SelfEvolutionEngine(g, merge_threshold=0.8)
        merged = engine.merge_equivalences()
        assert len(merged) >= 1

    def test_reinforce(self):
        g = self._build_graph()
        engine = SelfEvolutionEngine(g)
        engine.reinforce("a", boost=2.0)
        assert g.get_node("a").weight == 2.0

    def test_evolve(self):
        g = self._build_graph()
        engine = SelfEvolutionEngine(g, decay_threshold=0.1)
        report = engine.evolve()
        assert "decayed" in report
        assert "pruned" in report
        assert "merged" in report
        assert "node_count" in report

    def test_metrics_accumulate(self):
        g = self._build_graph()
        engine = SelfEvolutionEngine(g)
        engine.evolve()
        engine.evolve()
        assert engine.metrics.total_refinements == 2
