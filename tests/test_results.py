from __future__ import annotations

from dataclasses import dataclass

from hyper3.results import (
    CommitResult,
    DiscoveryHealthInfo,
    ImportResult,
    RollbackResult,
    SubgraphEdge,
    SubgraphNode,
    _SimpleResultBase,
    top_k,
)


class TestSimpleResultBase:
    def test_bracket_access(self):
        r = CommitResult(committed_nodes=5, committed_edges=3)
        assert r["committed_nodes"] == 5
        assert r["committed_edges"] == 3

    def test_contains_with_set_field(self):
        r = CommitResult(committed_nodes=1, committed_edges=0)
        assert "committed_nodes" in r
        assert "committed_edges" in r

    def test_contains_false_for_none_field(self):
        r = CommitResult(committed_nodes=0, committed_edges=0)
        assert "committed_nodes" in r

    def test_contains_false_for_private_attr(self):
        r = CommitResult()
        assert "_foo" not in r

    def test_contains_false_for_missing_attr(self):
        r = CommitResult()
        assert "nonexistent" not in r

    def test_get_returns_value(self):
        r = CommitResult(committed_nodes=7)
        assert r.get("committed_nodes", 0) == 7

    def test_get_returns_default_for_none(self):
        r = RollbackResult(rolled_back_nodes=0, rolled_back_edges=0)
        assert r.get("rolled_back_nodes", -1) == 0

    def test_get_returns_default_for_missing(self):
        r = CommitResult()
        assert r.get("nope", "fallback") == "fallback"

    def test_keys_returns_field_names(self):
        r = CommitResult(committed_nodes=1, committed_edges=2)
        assert r.keys() == ["committed_nodes", "committed_edges"]

    def test_items_returns_pairs(self):
        r = CommitResult(committed_nodes=3, committed_edges=1)
        assert r.items() == [("committed_nodes", 3), ("committed_edges", 1)]

    def test_get_with_none_field_returns_default(self):
        @dataclass
        class DummyResult(_SimpleResultBase):
            value: str | None = None

        r = DummyResult()
        assert r.get("value", "fallback") == "fallback"

    def test_contains_with_zero_int_is_true(self):
        r = CommitResult(committed_nodes=0)
        assert "committed_nodes" in r

    def test_contains_with_false_bool_is_true(self):
        @dataclass
        class BoolResult(_SimpleResultBase):
            flag: bool = False

        r = BoolResult()
        assert "flag" in r


class TestCommitResult:
    def test_defaults(self):
        r = CommitResult()
        assert r.committed_nodes == 0
        assert r.committed_edges == 0

    def test_with_values(self):
        r = CommitResult(committed_nodes=10, committed_edges=5)
        assert r.committed_nodes == 10
        assert r.committed_edges == 5

    def test_bracket_access(self):
        r = CommitResult(committed_nodes=3, committed_edges=2)
        assert r["committed_nodes"] == 3
        assert r["committed_edges"] == 2

    def test_keys(self):
        r = CommitResult()
        keys = r.keys()
        assert "committed_nodes" in keys
        assert "committed_edges" in keys
        assert len(keys) == 2


class TestRollbackResult:
    def test_defaults(self):
        r = RollbackResult()
        assert r.rolled_back_nodes == 0
        assert r.rolled_back_edges == 0

    def test_with_values(self):
        r = RollbackResult(rolled_back_nodes=4, rolled_back_edges=7)
        assert r.rolled_back_nodes == 4
        assert r.rolled_back_edges == 7

    def test_bracket_access(self):
        r = RollbackResult(rolled_back_nodes=1, rolled_back_edges=2)
        assert r["rolled_back_nodes"] == 1
        assert r["rolled_back_edges"] == 2


class TestImportResult:
    def test_defaults(self):
        r = ImportResult()
        assert r.nodes == 0
        assert r.edges == 0

    def test_with_values(self):
        r = ImportResult(nodes=100, edges=250)
        assert r.nodes == 100
        assert r.edges == 250

    def test_bracket_access(self):
        r = ImportResult(nodes=50, edges=75)
        assert r["nodes"] == 50
        assert r["edges"] == 75

    def test_keys(self):
        r = ImportResult()
        assert r.keys() == ["nodes", "edges"]


class TestDiscoveryHealthInfo:
    def test_defaults(self):
        r = DiscoveryHealthInfo()
        assert r.patterns == 0
        assert r.active_rules == 0

    def test_with_values(self):
        r = DiscoveryHealthInfo(patterns=12, active_rules=3)
        assert r.patterns == 12
        assert r.active_rules == 3

    def test_bracket_access(self):
        r = DiscoveryHealthInfo(patterns=5, active_rules=2)
        assert r["patterns"] == 5
        assert r["active_rules"] == 2

    def test_items(self):
        r = DiscoveryHealthInfo(patterns=8, active_rules=4)
        items = r.items()
        assert ("patterns", 8) in items
        assert ("active_rules", 4) in items


class TestSubgraphNode:
    def test_defaults(self):
        n = SubgraphNode()
        assert n.id == ""
        assert n.label == ""

    def test_with_values(self):
        n = SubgraphNode(id="abc", label="concept_x")
        assert n.id == "abc"
        assert n.label == "concept_x"

    def test_bracket_access(self):
        n = SubgraphNode(id="xyz", label="test")
        assert n["id"] == "xyz"
        assert n["label"] == "test"

    def test_keys(self):
        n = SubgraphNode()
        assert n.keys() == ["id", "label"]


class TestSubgraphEdge:
    def test_defaults(self):
        e = SubgraphEdge()
        assert e.id == ""
        assert e.label == ""
        assert e.source_labels == []
        assert e.target_labels == []
        assert e.weight == 1.0

    def test_with_values(self):
        e = SubgraphEdge(
            id="e1",
            label="causes",
            source_labels=["a", "b"],
            target_labels=["c"],
            weight=2.5,
        )
        assert e.id == "e1"
        assert e.label == "causes"
        assert e.source_labels == ["a", "b"]
        assert e.target_labels == ["c"]
        assert e.weight == 2.5

    def test_bracket_access(self):
        e = SubgraphEdge(id="e2", weight=3.0)
        assert e["id"] == "e2"
        assert e["weight"] == 3.0

    def test_keys(self):
        e = SubgraphEdge()
        assert set(e.keys()) == {"id", "label", "source_labels", "target_labels", "weight"}


class TestTopK:
    def test_returns_top_k_sorted(self):
        scores = {"a": 3.0, "b": 1.0, "c": 5.0, "d": 2.0}
        result = top_k(scores, k=2)
        assert result == [("c", 5.0), ("a", 3.0)]

    def test_default_k_is_10(self):
        scores = {f"n{i}": float(i) for i in range(20)}
        result = top_k(scores)
        assert len(result) == 10

    def test_k_exceeds_input(self):
        scores = {"a": 1.0, "b": 2.0}
        result = top_k(scores, k=10)
        assert len(result) == 2
        assert result[0] == ("b", 2.0)

    def test_empty_input(self):
        result = top_k({}, k=5)
        assert result == []
