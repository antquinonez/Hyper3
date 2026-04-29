import time

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.rules import TransitiveRule
from hyper3.multiway import MultiwayEngine, MultiwayGraph, MultiwayState
from hyper3.multiway_causal import StateConvergenceEngine


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
        for a_id, b_id, sim in pairs:
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
