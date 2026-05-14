import time

import pytest

from hyper3.consistency import ConsistencyVerifier, InvariantConfig, VerificationResult, Violation
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


class TestCleanGraph:
    def test_clean_graph_no_violations(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=1.0))
        verifier = ConsistencyVerifier(g)
        result = verifier.verify()
        assert result.violations == []
        assert result.invariant_count == 6
        assert result.passed == 6
        assert result.repaired_count == 0

    def test_empty_graph_no_violations(self):
        g = Hypergraph()
        verifier = ConsistencyVerifier(g)
        result = verifier.verify()
        assert result.violations == []
        assert result.invariant_count == 6
        assert result.passed == 6


class TestPositiveWeights:
    def test_detects_negative_weight(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=-1.0)
        g.add_edge(edge)
        verifier = ConsistencyVerifier(g)
        violations = verifier.verify_invariant("check_positive_weights")
        assert len(violations) == 1
        assert violations[0].severity == "error"
        assert violations[0].edge_id == edge.id
        assert violations[0].repairable is True

    def test_detects_zero_weight(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=0.0)
        g.add_edge(edge)
        verifier = ConsistencyVerifier(g)
        violations = verifier.verify_invariant("check_positive_weights")
        assert len(violations) == 1

    def test_repair_sets_weight_to_one(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=-2.0)
        g.add_edge(edge)
        config = InvariantConfig(repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        assert result.repaired_count == 1
        assert edge.weight == 1.0
        assert result.violations[0].repaired is True


class TestNoOrphans:
    def test_detects_orphan_node(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel"))
        orphan = g.add_node(Hypernode(label="orphan"))
        verifier = ConsistencyVerifier(g)
        violations = verifier.verify_invariant("check_no_orphans")
        assert len(violations) == 1
        assert violations[0].node_id == orphan.id
        assert violations[0].severity == "warning"
        assert violations[0].repairable is False

    def test_orphan_not_repaired(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="orphan"))
        config = InvariantConfig(repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        orphan_violations = [v for v in result.violations if v.invariant == "check_no_orphans"]
        assert len(orphan_violations) == 1
        assert orphan_violations[0].repaired is False


class TestNoSelfLoops:
    def test_detects_self_loop(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({a.id}), label="self")
        g.add_edge(edge)
        verifier = ConsistencyVerifier(g)
        violations = verifier.verify_invariant("check_no_self_loops")
        assert len(violations) == 1
        assert violations[0].edge_id == edge.id
        assert violations[0].severity == "warning"
        assert violations[0].repairable is True

    def test_repair_removes_self_loop(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({a.id}), label="self")
        g.add_edge(edge)
        config = InvariantConfig(repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        assert result.repaired_count >= 1
        assert g.get_edge(edge.id) is None


class TestLabelIndex:
    def test_detects_stale_entry(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        g._label_index["phantom"] = "dead_node_id"
        verifier = ConsistencyVerifier(g)
        violations = verifier.verify_invariant("check_label_index")
        assert len(violations) >= 1
        assert any("phantom" in v.description for v in violations)

    def test_repair_rebuilds_index(self):
        g = Hypergraph()
        node = g.add_node(Hypernode(label="a"))
        g._label_index["stale"] = "nonexistent"
        g._label_index.pop("a", None)
        config = InvariantConfig(repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        verifier.verify()
        assert g._label_index == {"a": node.id}
        assert "stale" not in g._label_index


class TestEdgeIntegrity:
    def test_detects_dangling_edge(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        phantom_id = "node_does_not_exist"
        edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({phantom_id}), label="rel")
        g._edges[edge.id] = edge
        verifier = ConsistencyVerifier(g)
        violations = verifier.verify_invariant("check_edge_integrity")
        assert len(violations) == 1
        assert violations[0].edge_id == edge.id
        assert violations[0].severity == "error"

    def test_repair_removes_dangling_edge(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        phantom_id = "node_does_not_exist"
        edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({phantom_id}), label="rel")
        g._edges[edge.id] = edge
        config = InvariantConfig(repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        assert g.get_edge(edge.id) is None
        assert result.repaired_count >= 1


class TestNoDuplicateEdges:
    def test_detects_duplicates(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        src = frozenset({a.id})
        tgt = frozenset({b.id})
        e1 = Hyperedge(source_ids=src, target_ids=tgt, label="rel", weight=2.0)
        e2 = Hyperedge(source_ids=src, target_ids=tgt, label="rel", weight=1.0)
        g.add_edge(e1)
        g.add_edge(e2)
        verifier = ConsistencyVerifier(g)
        violations = verifier.verify_invariant("check_no_duplicate_edges")
        assert len(violations) == 2

    def test_repair_keeps_higher_weight(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        src = frozenset({a.id})
        tgt = frozenset({b.id})
        e1 = Hyperedge(source_ids=src, target_ids=tgt, label="rel", weight=5.0)
        e2 = Hyperedge(source_ids=src, target_ids=tgt, label="rel", weight=2.0)
        g.add_edge(e1)
        g.add_edge(e2)
        config = InvariantConfig(repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        verifier.verify()
        assert g.get_edge(e1.id) is not None
        assert g.get_edge(e2.id) is None
        assert e1.weight == 5.0


class TestCacheConsistency:
    def test_detects_stale_cache(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel"))
        g._neighbor_cache = {a.id: [b.id], b.id: [a.id], "phantom": ["x"]}
        config = InvariantConfig(check_cache_consistency=True, repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        cache_violations = [v for v in result.violations if v.invariant == "check_cache_consistency"]
        assert len(cache_violations) >= 1
        assert g._neighbor_cache is None

    def test_clean_cache_no_violation(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel"))
        g.neighbors(a.id)
        assert g._neighbor_cache is not None
        config = InvariantConfig(check_cache_consistency=True)
        verifier = ConsistencyVerifier(g, config=config)
        violations = verifier.verify_invariant("check_cache_consistency")
        assert violations == []


class TestVerifyIntegration:
    def test_repair_true_auto_fixes(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        bad_edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=-1.0)
        g.add_edge(bad_edge)
        config = InvariantConfig(repair=True)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        assert bad_edge.weight == 1.0
        assert result.repaired_count >= 1

    def test_repair_false_only_reports(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        bad_edge = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=-1.0)
        g.add_edge(bad_edge)
        config = InvariantConfig(repair=False)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        assert bad_edge.weight == -1.0
        assert result.repaired_count == 0
        assert len(result.violations) >= 1

    def test_config_disables_checks(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=-1.0))
        g.add_node(Hypernode(label="orphan"))
        config = InvariantConfig(check_positive_weights=False, check_no_orphans=False)
        verifier = ConsistencyVerifier(g, config=config)
        result = verifier.verify()
        assert all(v.invariant not in ("check_positive_weights", "check_no_orphans") for v in result.violations)
        assert result.invariant_count == 4

    def test_unknown_invariant_raises(self):
        g = Hypergraph()
        verifier = ConsistencyVerifier(g)
        with pytest.raises(ValueError, match="Unknown invariant"):
            verifier.verify_invariant("check_nonexistent")


class TestVerificationResult:
    def test_passed_count_correct(self):
        g = Hypergraph()
        a = g.add_node(Hypernode(label="a"))
        b = g.add_node(Hypernode(label="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=-1.0))
        verifier = ConsistencyVerifier(g)
        result = verifier.verify()
        assert result.invariant_count == 6
        assert result.passed == 5
        assert len(result.violations) == 1

    def test_elapsed_ms_recorded(self):
        g = Hypergraph()
        for i in range(100):
            g.add_node(Hypernode(label=f"n{i}"))
        verifier = ConsistencyVerifier(g)
        result = verifier.verify()
        assert result.elapsed_ms >= 0.0


class TestMonitorIntegration:
    def test_system_monitor_verify_invariants(self):
        from hyper3.memory import HypergraphMemory

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="rel")
        result = mem.monitor.verify_invariants()
        assert isinstance(result, VerificationResult)
        assert result.violations == []

    def test_system_monitor_verify_with_repair(self):
        from hyper3.memory import HypergraphMemory

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        edge = Hyperedge(
            source_ids=frozenset({mem.graph.get_node_by_label("a").id}),
            target_ids=frozenset({mem.graph.get_node_by_label("b").id}),
            label="rel",
            weight=-1.0,
        )
        mem.graph.add_edge(edge)
        result = mem.monitor.verify_invariants(repair=True)
        assert edge.weight == 1.0
        assert result.repaired_count >= 1


class TestPerformance:
    def test_1000_node_graph_under_500ms(self):
        g = Hypergraph()
        nodes = []
        for i in range(1000):
            n = g.add_node(Hypernode(label=f"n{i}"))
            nodes.append(n)
        for i in range(len(nodes) - 1):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id}), label="rel"))
        verifier = ConsistencyVerifier(g)
        start = time.perf_counter()
        result = verifier.verify()
        elapsed = (time.perf_counter() - start) * 1000.0
        assert result.violations == []
        assert elapsed < 500.0
