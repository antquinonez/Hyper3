from __future__ import annotations

from dataclasses import dataclass

from hyper3.results import (
    CommitResult,
    CorrelatedNodeInfo,
    DerivationInfo,
    DiscoverResult,
    DiscoveryAnalysis,
    DiscoveryHealthInfo,
    EvolutionHealthInfo,
    EvolutionStats,
    GraphHealthInfo,
    HyperedgeSimilarityResult,
    HypergraphCutResult,
    ImportResult,
    PerspectiveAnalysis,
    RollbackResult,
    SPersistenceLevel,
    SPersistenceResult,
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

    def test_get_returns_actual_zero_not_default(self):
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


class TestCorrelatedNodeInfo:
    def test_defaults(self):
        r = CorrelatedNodeInfo()
        assert r.positive_rate == 0.0
        assert r.signal_count == 0
        assert r.signal_types == []

    def test_with_values(self):
        r = CorrelatedNodeInfo(positive_rate=0.8, signal_count=5, signal_types=["sampling", "retrieval"])
        assert r.positive_rate == 0.8
        assert r.signal_count == 5
        assert r.signal_types == ["sampling", "retrieval"]

    def test_bracket_access(self):
        r = CorrelatedNodeInfo(positive_rate=0.6, signal_count=3)
        assert r["positive_rate"] == 0.6
        assert r["signal_count"] == 3

    def test_contains(self):
        r = CorrelatedNodeInfo(positive_rate=0.5, signal_count=2)
        assert "positive_rate" in r
        assert "signal_count" in r

    def test_keys(self):
        r = CorrelatedNodeInfo()
        assert set(r.keys()) == {"positive_rate", "signal_count", "signal_types"}


class TestDerivationInfo:
    def test_defaults(self):
        d = DerivationInfo()
        assert d.rule == ""
        assert d.bindings == {}
        assert d.context == {}

    def test_with_values(self):
        d = DerivationInfo(rule="transitive", bindings={"A": "x", "B": "y"}, context={"depth": 2})
        assert d.rule == "transitive"
        assert d.bindings == {"A": "x", "B": "y"}
        assert d.context == {"depth": 2}

    def test_bracket_access(self):
        d = DerivationInfo(rule="inverse", bindings={"X": "a"})
        assert d["rule"] == "inverse"
        assert d["bindings"] == {"X": "a"}

    def test_keys(self):
        d = DerivationInfo()
        assert set(d.keys()) == {"rule", "bindings", "context"}


class TestDiscoverResult:
    def test_defaults(self):
        r = DiscoverResult()
        assert r.total_patterns == 0
        assert r.new_rules_added == 0
        assert r.analysis is None

    def test_with_values(self):
        analysis = DiscoveryAnalysis(total_patterns=10, new_patterns=3, active_rules=5)
        r = DiscoverResult(total_patterns=10, new_rules_added=2, analysis=analysis)
        assert r.total_patterns == 10
        assert r.new_rules_added == 2
        assert r.analysis.total_patterns == 10

    def test_bracket_access(self):
        r = DiscoverResult(total_patterns=7, new_rules_added=1)
        assert r["total_patterns"] == 7
        assert r["new_rules_added"] == 1

    def test_contains_with_none_analysis(self):
        r = DiscoverResult(total_patterns=5)
        assert "total_patterns" in r
        assert "analysis" not in r


class TestEvolutionHealthInfo:
    def test_defaults(self):
        r = EvolutionHealthInfo()
        assert r.merges == 0
        assert r.prunes == 0
        assert r.refinements == 0

    def test_with_values(self):
        r = EvolutionHealthInfo(merges=10, prunes=5, refinements=3)
        assert r.merges == 10
        assert r.prunes == 5
        assert r.refinements == 3

    def test_keys_match_evolution_stats(self):
        e = EvolutionHealthInfo()
        assert set(e.keys()) == {"merges", "prunes", "refinements"}
        s = EvolutionStats()
        assert set(s.keys()) == {"merges", "prunes", "refinements"}


class TestEvolutionStats:
    def test_defaults(self):
        r = EvolutionStats()
        assert r.merges == 0
        assert r.prunes == 0
        assert r.refinements == 0

    def test_with_values(self):
        r = EvolutionStats(merges=8, prunes=15, refinements=4)
        assert r.merges == 8
        assert r.prunes == 15
        assert r.refinements == 4

    def test_bracket_access(self):
        r = EvolutionStats(merges=3, prunes=7)
        assert r["merges"] == 3
        assert r["prunes"] == 7


class TestGraphHealthInfo:
    def test_defaults(self):
        r = GraphHealthInfo()
        assert r.nodes == 0
        assert r.edges == 0
        assert r.avg_degree == 0.0

    def test_with_values(self):
        r = GraphHealthInfo(nodes=100, edges=250, avg_degree=5.0)
        assert r.nodes == 100
        assert r.edges == 250
        assert r.avg_degree == 5.0

    def test_bracket_access(self):
        r = GraphHealthInfo(nodes=50, edges=75, avg_degree=3.0)
        assert r["nodes"] == 50
        assert r["avg_degree"] == 3.0

    def test_keys(self):
        r = GraphHealthInfo()
        assert set(r.keys()) == {"nodes", "edges", "avg_degree"}


class TestPerspectiveAnalysis:
    def test_defaults(self):
        r = PerspectiveAnalysis()
        assert r.available_frames == []
        assert r.transformations_computed == 0
        assert r.frame_effectiveness == {}

    def test_with_values(self):
        r = PerspectiveAnalysis(
            available_frames=["classical", "quantum"],
            transformations_computed=6,
            frame_effectiveness={"classical": 0.8, "quantum": 0.6},
        )
        assert r.available_frames == ["classical", "quantum"]
        assert r.transformations_computed == 6
        assert r.frame_effectiveness["classical"] == 0.8

    def test_bracket_access(self):
        r = PerspectiveAnalysis(available_frames=["hypergraph"])
        assert r["available_frames"] == ["hypergraph"]

    def test_keys(self):
        r = PerspectiveAnalysis()
        assert set(r.keys()) == {"available_frames", "transformations_computed", "frame_effectiveness"}


class TestSPersistenceResult:
    def test_defaults(self):
        r = SPersistenceResult()
        assert r.levels == []
        assert r.max_s == 1
        assert r.total_edges == 0

    def test_with_levels(self):
        level = SPersistenceLevel(s=1, components=[frozenset({"a", "b"})], num_components=1, largest_component_size=2)
        r = SPersistenceResult(levels=[level], max_s=3, total_edges=5)
        assert len(r.levels) == 1
        assert r.levels[0].s == 1
        assert r.max_s == 3
        assert r.total_edges == 5

    def test_bracket_access(self):
        r = SPersistenceResult(max_s=5, total_edges=10)
        assert r["max_s"] == 5
        assert r["total_edges"] == 10


class TestHyperedgeSimilarityResult:
    def test_defaults(self):
        r = HyperedgeSimilarityResult()
        assert r.query_edge_id == ""
        assert r.similar_edges == []
        assert r.metric == "jaccard"

    def test_with_values(self):
        r = HyperedgeSimilarityResult(
            query_edge_id="e1",
            similar_edges=[("e2", 0.8), ("e3", 0.5)],
            metric="sorensen_dice",
        )
        assert r.query_edge_id == "e1"
        assert len(r.similar_edges) == 2
        assert r.similar_edges[0] == ("e2", 0.8)
        assert r.metric == "sorensen_dice"

    def test_bracket_access(self):
        r = HyperedgeSimilarityResult(query_edge_id="abc")
        assert r["query_edge_id"] == "abc"

    def test_keys(self):
        r = HyperedgeSimilarityResult()
        assert set(r.keys()) == {"query_edge_id", "similar_edges", "metric"}


class TestHypergraphCutResult:
    def test_defaults(self):
        r = HypergraphCutResult()
        assert r.partitions == []
        assert r.cut_value == 0.0
        assert r.normalized_cut_value == 0.0

    def test_with_values(self):
        r = HypergraphCutResult(
            partitions=[frozenset({"a", "b"}), frozenset({"c", "d"})],
            cut_value=2.0,
            normalized_cut_value=0.35,
        )
        assert len(r.partitions) == 2
        assert frozenset({"a", "b"}) in r.partitions
        assert r.cut_value == 2.0
        assert r.normalized_cut_value == 0.35

    def test_bracket_access(self):
        r = HypergraphCutResult(cut_value=1.5)
        assert r["cut_value"] == 1.5

    def test_keys(self):
        r = HypergraphCutResult()
        assert set(r.keys()) == {"partitions", "cut_value", "normalized_cut_value"}
