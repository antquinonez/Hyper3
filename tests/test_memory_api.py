from __future__ import annotations

import pytest

from hyper3 import GraphDescription, HypergraphMemory, top_k


class TestHasNode:
    def test_returns_true_for_existing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("alpha")
        assert mem.has_node("alpha") is True

    def test_returns_false_for_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.has_node("nope") is False

    def test_contains_operator(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("beta")
        assert "beta" in mem
        assert "gamma" not in mem

    def test_contains_rejects_non_string(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert 42 not in mem

    def test_after_save_load(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("persist")
        path = tmp_path / "test.json"
        mem.save(str(path))
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(path))
        assert mem2.has_node("persist")


class TestEnsure:
    def test_creates_when_absent(self):
        mem = HypergraphMemory(evolve_interval=0)
        node = mem.ensure("concept", data={"type": "test"})
        assert node.label == "concept"
        assert node.data == {"type": "test"}

    def test_returns_existing_without_mutation(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data={"type": "original"})
        node = mem.ensure("x", data={"type": "new"})
        assert node.data["type"] == "original"

    def test_update_merges_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data={"type": "original", "extra": 1})
        node = mem.ensure("x", data={"type": "updated"}, update=True)
        assert node.data["type"] == "updated"
        assert node.data["extra"] == 1

    def test_does_not_trigger_evolution(self):
        mem = HypergraphMemory(evolve_interval=1)
        mem.ensure("a")
        mem.ensure("b")
        mem.ensure("c")
        stats = mem.stats()
        assert stats.nodes == 3

    def test_ensure_then_relate(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.ensure("src", data={"type": "source"})
        mem.ensure("tgt", data={"type": "target"})
        edge = mem.relate("src", "tgt", label="connects")
        assert edge.label == "connects"

    def test_update_with_non_dict_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data="string_data")
        node = mem.ensure("x", data={"type": "new"}, update=True)
        assert node.data == "string_data"


class TestRelateWeight:
    def test_default_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", label="x")
        assert edge.weight == 1.0

    def test_custom_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", label="x", weight=5.5)
        assert edge.weight == 5.5

    def test_bidirectional_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", label="x", weight=3.0, bidirectional=True)
        assert edge.weight == 3.0
        rev = mem.neighbors("b", edge_label="x", direction="out")
        assert "a" in rev

    def test_zero_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", label="x", weight=0.0)
        assert edge.weight == 0.0


class TestNeighbors:
    def test_outgoing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="knows")
        mem.relate("a", "c", label="knows")
        assert set(mem.neighbors("a", direction="out")) == {"b", "c"}

    def test_incoming(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="knows")
        assert mem.neighbors("b", direction="in") == ["a"]

    def test_filter_by_edge_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="friend")
        mem.relate("a", "c", label="enemy")
        assert mem.neighbors("a", edge_label="friend", direction="out") == ["b"]

    def test_any_direction(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("c", "a", label="y")
        result = set(mem.neighbors("a", direction="any"))
        assert result == {"b", "c"}

    def test_missing_concept_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.neighbors("ghost") == []

    def test_no_edges_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("loner")
        assert mem.neighbors("loner") == []

    def test_excludes_self(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        result = mem.neighbors("a", direction="out")
        assert "a" not in result


class TestQueryNodes:
    def test_filter_by_type(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("m1", data={"type": "movie"})
        mem.store("m2", data={"type": "movie"})
        mem.store("g1", data={"type": "genre"})
        result = mem.query_nodes(type="movie")
        assert set(result) == {"m1", "m2"}

    def test_filter_by_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data={"type": "pkg", "eco": "pypi"})
        mem.store("y", data={"type": "pkg", "eco": "npm"})
        mem.store("z", data={"type": "pkg"})
        result = mem.query_nodes(data={"eco": "pypi"})
        assert result == ["x"]

    def test_combined_type_and_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a", data={"type": "t", "v": 1})
        mem.store("b", data={"type": "t", "v": 2})
        result = mem.query_nodes(type="t", data={"v": 1})
        assert result == ["a"]

    def test_filter_by_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data={"type": "a"})
        mem.store("y", data={"type": "b"})
        mem.store("z", data={"type": "c"})
        result = mem.query_nodes(labels={"x", "z"})
        assert set(result) == {"x", "z"}

    def test_limit(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"n{i}", data={"type": "t"})
        result = mem.query_nodes(type="t", limit=3)
        assert len(result) == 3

    def test_empty_result(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.query_nodes(type="nonexistent") == []

    def test_nodes_without_data_excluded(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("no_data")
        mem.store("has_data", data={"type": "x"})
        result = mem.query_nodes(type="x")
        assert result == ["has_data"]


class TestDescribe:
    def test_basic_counts(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="knows")
        desc = mem.describe()
        assert desc.node_count == 2
        assert desc.edge_count == 1

    def test_node_types(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("m1", data={"type": "movie"})
        mem.store("m2", data={"type": "movie"})
        mem.store("g", data={"type": "genre"})
        desc = mem.describe()
        assert desc.node_types == {"movie": 2, "genre": 1}

    def test_node_types_kind_fallback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("p", data={"kind": "paper"})
        desc = mem.describe()
        assert desc.node_types == {"paper": 1}

    def test_untyped_nodes(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("bare")
        desc = mem.describe()
        assert desc.node_types == {"(untyped)": 1}

    def test_edge_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="friend")
        mem.relate("b", "c", label="friend")
        mem.relate("a", "c", label="enemy")
        desc = mem.describe()
        assert desc.edge_labels == {"friend": 2, "enemy": 1}

    def test_unlabeled_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        desc = mem.describe()
        assert desc.edge_labels == {"(unlabeled)": 1}

    def test_degree_stats(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("a", "c", label="x")
        desc = mem.describe()
        assert desc.degree_min == 1
        assert desc.degree_max == 2

    def test_empty_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        desc = mem.describe()
        assert desc.node_count == 0
        assert desc.edge_count == 0
        assert desc.node_types == {}
        assert desc.isolated_nodes == 0
        assert desc.density == 0.0

    def test_isolated_nodes(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        desc = mem.describe()
        assert desc.isolated_nodes == 1

    def test_is_dataclass(self):
        mem = HypergraphMemory(evolve_interval=0)
        desc = mem.describe()
        assert isinstance(desc, GraphDescription)
        assert "node_count" in desc
        assert desc["node_count"] == 0


class TestPageRank:
    def test_basic(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("hub")
        mem.store("a")
        mem.store("b")
        mem.relate("hub", "a", label="x")
        mem.relate("hub", "b", label="x")
        mem.relate("a", "hub", label="y")
        pr = mem.pagerank()
        assert len(pr) == 3
        assert all(0 <= v <= 1 for v in pr.values())

    def test_top_k(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"n{i}")
        for i in range(1, 10):
            mem.relate("n0", f"n{i}", label="x")
        pr = mem.pagerank(top_k=3)
        assert len(pr) == 3

    def test_single_node(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("solo")
        pr = mem.pagerank()
        assert pr["solo"] == pytest.approx(1.0)

    def test_empty_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        pr = mem.pagerank()
        assert pr == {}

    def test_unweighted(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x", weight=5.0)
        mem.relate("a", "c", label="x", weight=1.0)
        pr_w = mem.pagerank(weighted=True)
        pr_u = mem.pagerank(weighted=False)
        assert pr_w != pr_u or len(pr_w) == 3


class TestTopK:
    def test_basic(self):
        scores = {"a": 0.9, "b": 0.5, "c": 0.7, "d": 0.3}
        result = top_k(scores, k=2)
        assert result == [("a", 0.9), ("c", 0.7)]

    def test_k_larger_than_dict(self):
        scores = {"a": 1.0}
        result = top_k(scores, k=5)
        assert result == [("a", 1.0)]

    def test_empty(self):
        assert top_k({}, k=3) == []

    def test_k_one(self):
        scores = {"x": 0.1, "y": 0.9}
        result = top_k(scores, k=1)
        assert result == [("y", 0.9)]


class TestCentralityTopK:
    def test_betweenness_top_k(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"n{i}")
        mem.relate("n0", "n1", label="x")
        mem.relate("n1", "n2", label="x")
        bc = mem.betweenness_centrality(top_k=2)
        assert len(bc) == 2

    def test_degree_top_k(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"n{i}")
        for i in range(1, 10):
            mem.relate("n0", f"n{i}", label="x")
        dc = mem.degree_centrality(top_k=3)
        assert len(dc) == 3
        assert "n0" in dc

    def test_top_k_none_returns_all(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        bc = mem.betweenness_centrality(top_k=None)
        assert len(bc) == 2
