from __future__ import annotations

import json
from pathlib import Path

import pytest

from hyper3 import BulkResult, GraphDescription, HypergraphMemory, NodeInfo, NodeNotFoundError, top_k
from hyper3.memory_persistence import _json_fallback


class TestHasNode:
    def test_returns_true_for_existing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("alpha")
        assert mem.has("alpha") is True

    def test_returns_false_for_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.has("nope") is False

    def test_contains_operator(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("beta")
        assert "beta" in mem
        assert "gamma" not in mem

    def test_contains_rejects_non_string(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert 42 not in mem

    def test_after_save_load(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("persist")
        path = tmp_path / "test.json"
        mem.save(str(path))
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(path))
        assert mem2.has("persist")


class TestEnsure:
    def test_creates_when_absent(self):
        mem = HypergraphMemory(evolve_interval=0)
        node = mem.ensure("concept", data={"type": "test"})
        assert node.label == "concept"
        assert node.data == {"type": "test"}

    def test_returns_existing_without_mutation(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"type": "original"})
        node = mem.ensure("x", data={"type": "new"})
        assert node.data["type"] == "original"

    def test_update_merges_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"type": "original", "extra": 1})
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
        edge = mem.link("src", "tgt", label="connects")
        assert edge.label == "connects"

    def test_update_with_non_dict_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data="string_data")
        node = mem.ensure("x", data={"type": "new"}, update=True)
        assert node.data == "string_data"


class TestRelateWeight:
    def test_default_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        edge = mem.link("a", "b", label="x")
        assert edge.weight == 1.0

    def test_custom_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        edge = mem.link("a", "b", label="x", weight=5.5)
        assert edge.weight == 5.5

    def test_bidirectional_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        edge = mem.link("a", "b", label="x", weight=3.0, bidirectional=True)
        assert edge.weight == 3.0
        rev = mem.neighbors("b", edge_label="x", direction="out")
        assert "a" in rev

    def test_zero_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        with pytest.raises(ValueError, match="positive"):
            mem.link("a", "b", label="x", weight=0.0)


class TestNeighbors:
    def test_outgoing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="knows")
        mem.link("a", "c", label="knows")
        assert set(mem.neighbors("a", direction="out")) == {"b", "c"}

    def test_incoming(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="knows")
        assert mem.neighbors("b", direction="in") == ["a"]

    def test_filter_by_edge_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="friend")
        mem.link("a", "c", label="enemy")
        assert mem.neighbors("a", edge_label="friend", direction="out") == ["b"]

    def test_any_direction(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="x")
        mem.link("c", "a", label="y")
        result = set(mem.neighbors("a", direction="any"))
        assert result == {"b", "c"}

    def test_missing_concept_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.neighbors("ghost") == []

    def test_no_edges_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("loner")
        assert mem.neighbors("loner") == []

    def test_excludes_self(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="x")
        result = mem.neighbors("a", direction="out")
        assert "a" not in result


class TestQueryNodes:
    def test_filter_by_type(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("m1", data={"type": "movie"})
        mem.add("m2", data={"type": "movie"})
        mem.add("g1", data={"type": "genre"})
        result = mem.query_nodes(type="movie")
        assert set(result) == {"m1", "m2"}

    def test_filter_by_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"type": "pkg", "eco": "pypi"})
        mem.add("y", data={"type": "pkg", "eco": "npm"})
        mem.add("z", data={"type": "pkg"})
        result = mem.query_nodes(data={"eco": "pypi"})
        assert result == ["x"]

    def test_combined_type_and_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a", data={"type": "t", "v": 1})
        mem.add("b", data={"type": "t", "v": 2})
        result = mem.query_nodes(type="t", data={"v": 1})
        assert result == ["a"]

    def test_filter_by_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"type": "a"})
        mem.add("y", data={"type": "b"})
        mem.add("z", data={"type": "c"})
        result = mem.query_nodes(labels={"x", "z"})
        assert set(result) == {"x", "z"}

    def test_limit(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"n{i}", data={"type": "t"})
        result = mem.query_nodes(type="t", limit=3)
        assert len(result) == 3

    def test_empty_result(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.query_nodes(type="nonexistent") == []

    def test_nodes_without_data_excluded(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("no_data")
        mem.add("has_data", data={"type": "x"})
        result = mem.query_nodes(type="x")
        assert result == ["has_data"]


class TestDescribe:
    def test_basic_counts(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="knows")
        desc = mem.describe()
        assert desc.node_count == 2
        assert desc.edge_count == 1

    def test_node_types(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("m1", data={"type": "movie"})
        mem.add("m2", data={"type": "movie"})
        mem.add("g", data={"type": "genre"})
        desc = mem.describe()
        assert desc.node_types == {"movie": 2, "genre": 1}

    def test_node_types_kind_fallback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("p", data={"kind": "paper"})
        desc = mem.describe()
        assert desc.node_types == {"paper": 1}

    def test_untyped_nodes(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("bare")
        desc = mem.describe()
        assert desc.node_types == {"(untyped)": 1}

    def test_edge_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="friend")
        mem.link("b", "c", label="friend")
        mem.link("a", "c", label="enemy")
        desc = mem.describe()
        assert desc.edge_labels == {"friend": 2, "enemy": 1}

    def test_unlabeled_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b")
        desc = mem.describe()
        assert desc.edge_labels == {"(unlabeled)": 1}

    def test_degree_stats(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="x")
        mem.link("a", "c", label="x")
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
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="x")
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
        mem.add("hub")
        mem.add("a")
        mem.add("b")
        mem.link("hub", "a", label="x")
        mem.link("hub", "b", label="x")
        mem.link("a", "hub", label="y")
        pr = mem.pagerank()
        assert len(pr) == 3
        assert all(0 <= v <= 1 for v in pr.values())
        assert pr["hub"] > pr["b"]
        assert sum(pr.values()) == pytest.approx(1.0)

    def test_top_k(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"n{i}")
        for i in range(1, 10):
            mem.link("n0", f"n{i}", label="x")
        pr = mem.pagerank(top_k=3)
        assert len(pr) == 3

    def test_single_node(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("solo")
        pr = mem.pagerank()
        assert pr["solo"] == pytest.approx(1.0)

    def test_empty_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        pr = mem.pagerank()
        assert pr == {}

    def test_unweighted(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="x", weight=5.0)
        mem.link("a", "c", label="x", weight=1.0)
        pr_w = mem.pagerank(weighted=True)
        pr_u = mem.pagerank(weighted=False)
        assert pr_w != pr_u
        assert len(pr_w) == 3


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
            mem.add(f"n{i}")
        mem.link("n0", "n1", label="x")
        mem.link("n1", "n2", label="x")
        bc = mem.betweenness_centrality(top_k=2)
        assert len(bc) == 2
        assert max(bc, key=bc.get) == "n1"

    def test_degree_top_k(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"n{i}")
        for i in range(1, 10):
            mem.link("n0", f"n{i}", label="x")
        dc = mem.degree_centrality(top_k=3)
        assert len(dc) == 3
        assert "n0" in dc

    def test_top_k_none_returns_all(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="x")
        bc = mem.betweenness_centrality(top_k=None)
        assert len(bc) == 2


class TestGet:
    def test_missing_concept_returns_default(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.get("missing") is None

    def test_missing_concept_custom_default(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.get("missing", default="fallback") == "fallback"

    def test_no_key_returns_label_and_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"type": "t", "val": 42})
        result = mem.get("x")
        assert result == {"label": "x", "type": "t", "val": 42}

    def test_no_key_non_dict_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data="plain_string")
        result = mem.get("x")
        assert result == {"label": "x"}

    def test_key_returns_value(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"color": "red"})
        assert mem.get("x", "color") == "red"

    def test_key_missing_returns_default(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"color": "red"})
        assert mem.get("x", "size") is None
        assert mem.get("x", "size", default=0) == 0

    def test_key_non_dict_data_returns_default(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data=42)
        assert mem.get("x", "anything") is None
        assert mem.get("x", "anything", default="nope") == "nope"


class TestSet:
    def test_missing_concept_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        with pytest.raises(NodeNotFoundError, match="ghost"):
            mem.set("ghost", x=1)

    def test_none_data_initialized_to_dict(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.set("x", color="blue", size=10)
        assert mem.get("x", "color") == "blue"
        assert mem.get("x", "size") == 10

    def test_updates_existing_dict(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"color": "red"})
        mem.set("x", color="green", shape="circle")
        assert mem.get("x", "color") == "green"
        assert mem.get("x", "shape") == "circle"


class TestInfo:
    def test_missing_returns_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.info("ghost") is None

    def test_returns_nodeinfo(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"type": "t"})
        result = mem.info("x")
        assert isinstance(result, NodeInfo)
        assert result.label == "x"
        assert result.data == {"type": "t"}
        assert result.weight == 1.0
        assert result.access_count >= 1

    def test_non_dict_data_returns_empty_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data="string_data")
        result = mem.info("x")
        assert isinstance(result, NodeInfo)
        assert result.data == {}


class TestLinkHyper:
    def test_creates_hyperedge(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        edge = mem.link_hyper({"a", "b"}, {"c"}, label="joint", weight=2.5)
        assert edge.label == "joint"
        assert edge.weight == 2.5

    def test_edge_data_forwarded(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        edge = mem.link_hyper({"a"}, {"b"}, label="x", extra="val")
        assert edge.data == {"extra": "val"}


class TestAddAll:
    def test_nodes_only(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.add_all(nodes={"a": {}, "b": {"type": "t"}})
        assert result.nodes_added == 2
        assert result.nodes_skipped == 0
        assert result.edges_added == 0
        assert result.edges_skipped == 0
        assert mem.has("a")
        assert mem.has("b")

    def test_nodes_existing_skipped(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a", data={"v": 1})
        result = mem.add_all(nodes={"a": {"v": 2}, "b": {}})
        assert result.nodes_added == 1
        assert result.nodes_skipped == 1
        assert mem.get("a", "v") == 2

    def test_edges_only_dict_spec(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        result = mem.add_all(edges=[{"source": "a", "target": "b", "label": "x", "weight": 3.0}])
        assert result.edges_added == 1
        assert result.nodes_added == 0

    def test_edges_only_tuple_spec(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        result = mem.add_all(edges=[("a", "b", "y")])
        assert result.edges_added == 1

    def test_tuple_spec_with_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        result = mem.add_all(edges=[("a", "b", "z", 5.0)])
        assert result.edges_added == 1

    def test_tuple_spec_short(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        result = mem.add_all(edges=[("a", "b")])
        assert result.edges_added == 1
        edges = list(mem._graph.edges)
        assert any(e.label == "" for e in edges)

    def test_edges_missing_nodes_skipped(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.add_all(edges=[("a", "b", "x")])
        assert result.edges_added == 0
        assert result.edges_skipped == 1

    def test_both_nodes_and_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.add_all(
            nodes={"a": {}, "b": {}},
            edges=[("a", "b", "connects")],
        )
        assert isinstance(result, BulkResult)
        assert result.nodes_added == 2
        assert result.edges_added == 1

    def test_empty_call(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.add_all()
        assert result.nodes_added == 0
        assert result.edges_added == 0


class TestMaybeEvolveWithFeedback:
    def test_evolve_with_feedback_triggered(self):
        mem = HypergraphMemory(evolve_interval=2)
        mem.add("a")
        mem.add("b")
        assert hasattr(mem, "_feedback")
        assert mem._feedback is not None
        stats_after = mem.stats()
        assert stats_after.nodes == 2


class TestLoadRecordsEdgeWithoutEndpoints:
    def test_edge_missing_source_skipped(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        result = mem.load_records([], [{"target": "b", "label": "x"}])
        assert result.edges == 0

    def test_edge_missing_target_skipped(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        result = mem.load_records([], [{"source": "a", "label": "x"}])
        assert result.edges == 0

    def test_edge_empty_source_skipped(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        result = mem.load_records([], [{"source": "", "target": "a", "label": "x"}])
        assert result.edges == 0


class TestLoadBareSnapshot:
    def test_load_state_file_via_load(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("alpha")
        mem.add("beta")
        mem.link("alpha", "beta", label="knows")
        path = str(tmp_path / "state.json")
        mem.save_state(path)
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)
        assert mem2.stats().nodes == 0


class TestLoadFallbackPaths:
    def test_load_with_rules_after_snapshot_failure(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="links")
        path = str(tmp_path / "mixed.json")
        mem.save(path, include_rules=True)
        p = Path(path)
        data = json.loads(p.read_text())
        data["snapshot"] = {"cache_items": None}
        p.write_text(json.dumps(data))
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)
        assert mem2.has("x")
        assert mem2.has("y")

    def test_load_plain_after_rules_corruption(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("p")
        mem.add("q")
        mem.link("p", "q", label="rel")
        path = str(tmp_path / "corrupt_rules.json")
        mem.save(path, include_rules=False)
        p = Path(path)
        data = json.loads(p.read_text())
        data["rules"] = None
        p.write_text(json.dumps(data))
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)
        assert mem2.has("p")
        assert mem2.has("q")
        assert mem2.rules == []


class TestTryLoadBareSnapshot:
    def test_invalid_json_returns_none(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        p = tmp_path / "bad.txt"
        p.write_text("not valid json {{{")
        assert mem._try_load_bare_snapshot(str(p)) is None

    def test_has_graph_key_returns_none(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        p = tmp_path / "graph.json"
        p.write_text(json.dumps({"graph": {"nodes": [], "edges": []}}))
        assert mem._try_load_bare_snapshot(str(p)) is None

    def test_no_version_no_saved_at_returns_none(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        p = tmp_path / "no_meta.json"
        p.write_text(json.dumps({"data": [1, 2, 3]}))
        assert mem._try_load_bare_snapshot(str(p)) is None

    def test_valid_bare_snapshot_returned(self, tmp_path):
        from hyper3.snapshot import SystemSnapshot

        mem = HypergraphMemory(evolve_interval=0)
        p = tmp_path / "bare.json"
        p.write_text(json.dumps({"version": 1, "saved_at": 1234567890.0}))
        result = mem._try_load_bare_snapshot(str(p))
        assert isinstance(result, SystemSnapshot)
        assert result.version == 1
        assert result.saved_at == 1234567890.0


class TestJsonFallback:
    def test_set_sorted(self):
        assert _json_fallback({3, 1, 2}) == [1, 2, 3]

    def test_frozenset_sorted(self):
        assert _json_fallback(frozenset([3, 1, 2])) == [1, 2, 3]

    def test_tuple_to_list(self):
        assert _json_fallback((1, 2, 3)) == [1, 2, 3]

    def test_str_fallback(self):
        assert _json_fallback(42) == "42"

    def test_object_str_fallback(self):
        class Widget:
            def __str__(self):
                return "widget"

        assert _json_fallback(Widget()) == "widget"
