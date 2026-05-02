import time

import pytest

from hyper3 import (
    BeliefLayer,
    BeliefState,
    ConvergenceRecord,
    Hyperedge,
    Hypergraph,
    HypergraphMemory,
    Hypernode,
    InverseRule,
    Modality,
    MultiwayEngine,
    MultiwayGraph,
    MultiwayState,
    NodeNotFoundError,
    Outcome,
    StateConvergenceEngine,
    TransitiveRule,
)


class TestStateConvergenceEngine:
    def _build_multiway(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = MultiwayEngine(g)
        engine.expand({"a", "b", "c", "d"}, [TransitiveRule(edge_label="rel")], max_depth=2)
        return g, engine

    def test_state_similarity_identical(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        states = mw.states
        ci = StateConvergenceEngine(g, mw)
        sim = ci.compute_state_similarity(states[0], states[0])
        assert sim == 1.0

    def test_state_similarity_different(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw)
        root = mw.get_root()
        leaves = mw.get_leaves()
        assert root is not None
        assert len(leaves) >= 1
        sim = ci.compute_state_similarity(root, leaves[0])
        assert 0.0 <= sim <= 1.0
        assert sim < 1.0

    def test_find_invariants(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        invariants = ci.find_invariants()
        assert isinstance(invariants, list)
        leaves = mw.get_leaves()
        if len(leaves) < 2:
            assert len(invariants) == 0
        for pair in invariants:
            assert isinstance(pair, tuple)
            assert len(pair) == 3
            assert isinstance(pair[0], str)
            assert isinstance(pair[1], str)
            assert isinstance(pair[2], float)

    def test_merge_invariant_states(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        merged = ci.merge_invariant_states()
        assert isinstance(merged, list)
        state_ids = {s.id for s in mw.states}
        for inv in merged:
            assert isinstance(inv, ConvergenceRecord)
            assert inv.merged_into in state_ids

    def test_enforce(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        report = ci.enforce()
        assert report.states_before >= report.states_after
        assert report.merges_performed == report.states_before - report.states_after


class TestBeliefState:
    def test_create(self):
        qs = BeliefState()
        assert not qs.resolved
        assert qs.outcome_count == 0

    def test_add_outcome(self):
        qs = BeliefState()
        qs.add_outcome("a", 0.7)
        qs.add_outcome("b", 0.3)
        assert qs.outcome_count == 2

    def test_normalize(self):
        qs = BeliefState()
        qs.add_outcome("a", 3.0)
        qs.add_outcome("b", 4.0)
        qs.normalize()
        total_prob = sum(i.probability for i in qs.outcomes)
        assert abs(total_prob - 1.0) < 0.01

    def test_sample(self):
        qs = BeliefState()
        qs.add_outcome("a", 0.9)
        qs.add_outcome("b", 0.1)
        selected = qs.sample()
        assert selected is not None
        assert selected.node_id in {"a", "b"}
        assert qs.resolved
        assert qs.resolved_to in {"a", "b"}

    def test_sample_with_context(self):
        qs = BeliefState()
        qs.add_outcome("a", 0.5)
        qs.add_outcome("b", 0.5)
        counts = {"a": 0, "b": 0}
        for _ in range(200):
            qs2 = BeliefState()
            qs2.add_outcome("a", 0.5)
            qs2.add_outcome("b", 0.5)
            result = qs2.sample(context_weights={"b": 10.0})
            counts[result.node_id] += 1
        assert counts["b"] > counts["a"]

    def test_sample_empty(self):
        qs = BeliefState()
        assert qs.sample() is None

    def test_probability(self):
        qs = BeliefState()
        qs.add_outcome("a", 0.6)
        qs.add_outcome("b", 0.8)
        qs.normalize()
        total = sum(i.probability for i in qs.outcomes)
        assert abs(total - 1.0) < 0.01


class TestBeliefLayer:
    def test_create_distribution(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b"])
        assert qs.outcome_count == 2

    def test_create_from_labels(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="concept_x"))
        g.add_node(Hypernode(id="y", label="concept_y"))
        ql = BeliefLayer(g)
        qs = ql.create_from_labels(["concept_x", "concept_y"])
        assert qs.outcome_count == 2

    def test_sample_state(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b"])
        result = ql.sample(qs.id)
        assert result is not None
        assert result.node_id in {"a", "b"}
        assert qs.resolved

    def test_evolve_amplitudes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b"])
        ql.evolve_amplitudes(qs.id, {"a": 5.0, "b": 0.1})
        a_amp = None
        b_amp = None
        for outcome in qs.outcomes:
            if outcome.node_id == "a":
                a_amp = outcome.amplitude
            if outcome.node_id == "b":
                b_amp = outcome.amplitude
        assert a_amp is not None and b_amp is not None
        assert a_amp > b_amp
        assert a_amp > 0.9

    def test_active_and_resolved(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = BeliefLayer(g)
        qs1 = ql.create_distribution(["a"])
        ql.create_distribution(["a"])
        assert len(ql.active_distributions) == 2
        ql.sample(qs1.id)
        assert len(ql.active_distributions) == 1
        assert len(ql.resolved_states) == 1

    def test_get_state(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        assert ql.get_state("nonexistent") is None


class TestHypergraphMemoryIntegration:
    def test_reason_with_rules(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="rel")
        mem.relate("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        result = mem.reason({"a", "b", "c"})
        assert "expansion" in result
        assert result["expansion"]["rules_applied"] == 1

    def test_reason_no_rules(self):
        mem = HypergraphMemory()
        mem.store("a")
        result = mem.reason({"a"})
        assert "error" in result

    def test_reason_no_seed(self):
        mem = HypergraphMemory()
        mem.add_rules(TransitiveRule())
        result = mem.reason({"nonexistent"})
        assert "error" in result

    def test_create_distribution_and_sample(self):
        mem = HypergraphMemory()
        mem.store("cat")
        mem.store("bank_river")
        mem.store("bank_finance")
        qs = mem.create_distribution(["cat", "bank_river", "bank_finance"])
        assert qs.outcome_count == 3
        result = mem.sample(qs, context={"bank_finance": 5.0})
        assert result is not None
        assert result.label in {"cat", "bank_river", "bank_finance"}
        assert qs.resolved

    def test_create_distribution_empty(self):
        mem = HypergraphMemory()
        with pytest.raises(NodeNotFoundError):
            mem.create_distribution(["nonexistent"])

    def test_lateral_insights(self):
        mem = HypergraphMemory()
        for label in ["a", "b", "c"]:
            mem.store(label)
        mem.relate("a", "b", label="rel")
        mem.relate("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"), InverseRule(edge_label="rel", inverse_label="inv"))
        mem.reason({"a", "b", "c"}, max_depth=2)
        insights = mem.lateral_insights("a")
        assert isinstance(insights, list)
        for insight in insights:
            assert isinstance(insight["branchial_distance"], float)
            assert 0.0 <= insight["branchial_distance"] <= 2.0
            assert "complementary_nodes" in insight
            assert "transferable_patterns" in insight
            assert "novel_in_source" in insight
            assert "novel_in_lateral" in insight

    def test_lateral_insights_no_multiway(self):
        mem = HypergraphMemory()
        assert mem.lateral_insights("x") == []

    def test_stats_includes_new_fields(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        stats = mem.stats()
        assert isinstance(stats["multiway_states"], int)
        assert stats["multiway_states"] == 0
        assert isinstance(stats["belief_active"], int)
        assert stats["belief_active"] == 0
        assert isinstance(stats["belief_resolved"], int)
        assert stats["belief_resolved"] == 0

    def test_multiway_property(self):
        mem = HypergraphMemory()
        assert mem.multiway is None
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        mem.reason({"a", "b"})
        assert mem.multiway is not None
        assert len(mem.multiway.multiway.states) >= 1

    def test_belief_property(self):
        mem = HypergraphMemory()
        assert isinstance(mem.belief, BeliefLayer)

    def test_full_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["rain", "clouds", "wet_ground", "flooding", "umbrella"]:
            mem.store(label, modalities={Modality.CONCEPTUAL})
        mem.relate("rain", "wet_ground", label="causes")
        mem.relate("wet_ground", "flooding", label="causes")
        mem.relate("clouds", "rain", label="leads_to")
        mem.relate("umbrella", "rain", label="protects_from")
        mem.add_rules(
            TransitiveRule(edge_label="causes"),
            InverseRule(edge_label="causes", inverse_label="caused_by"),
        )
        result = mem.reason({"rain", "clouds", "wet_ground", "flooding", "umbrella"}, max_depth=3)
        assert result["expansion"]["rules_applied"] == 3
        qs = mem.create_distribution(["rain", "clouds", "umbrella"])
        assert qs.outcome_count == 3
        selected = mem.sample(qs)
        assert selected is not None
        assert selected.label in {"rain", "clouds", "umbrella"}
        mem.evolve()
        stats = mem.stats()
        assert stats["nodes"] == 5
        assert stats["multiway_states"] == 4



class TestCausalInvarianceDeep:
    def test_state_similarity_both_empty(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        mw.expand(set(), [], max_depth=1)
        s1 = MultiwayState(active_node_ids=frozenset())
        s2 = MultiwayState(active_node_ids=frozenset())
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.compute_state_similarity(s1, s2) == 1.0

    def test_state_similarity_one_empty(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [], max_depth=1)
        s1 = MultiwayState(active_node_ids=frozenset({"a"}))
        s2 = MultiwayState(active_node_ids=frozenset())
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.compute_state_similarity(s1, s2) == 0.0

    def test_no_duplicate_merges_on_repeated_enforce(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        mw = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        mw.expand({"a"}, [rule], max_depth=2, max_total_states=20)
        ci = StateConvergenceEngine(g, mw.multiway, threshold=0.3)
        ci.enforce()
        r2 = ci.enforce()
        assert r2["merges_performed"] == 0

    def test_invariants_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [], max_depth=1)
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.invariants == []

    def test_enforce_reports_reduction(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        mw = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        mw.expand({"a"}, [rule], max_depth=2, max_total_states=20)
        ci = StateConvergenceEngine(g, mw.multiway, threshold=0.3)
        report = ci.enforce()
        assert "reduction" in report
        assert isinstance(report["reduction"], int)
        assert report["reduction"] == report["states_before"] - report["states_after"]


class TestGraphIsomorphismCoverage:
    def test_edge_count_mismatch_returns_zero(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        e1 = g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        e2 = g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
        e3 = g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        mw = MultiwayEngine(g)
        s1 = MultiwayState(active_node_ids=frozenset({"a", "b", "c", "d"}), produced_edge_ids=[e1.id, e2.id])
        s2 = MultiwayState(active_node_ids=frozenset({"a", "b", "c", "d"}), produced_edge_ids=[e1.id, e2.id, e3.id])
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.check_graph_isomorphism(s1, s2) == 0.0

    def test_node_match_returns_false_for_missing_nodes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="shared", data={"k": "v"}))
        g.add_node(Hypernode(id="b", label="shared", data={"k": "v"}))
        e1 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"miss1"}), label="rel")
        e2 = Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"miss2"}), label="rel")
        g._edges[e1.id] = e1
        g._edges[e2.id] = e2
        mw = MultiwayEngine(g)
        s1 = MultiwayState(active_node_ids=frozenset({"a", "miss1"}), produced_edge_ids=[e1.id])
        s2 = MultiwayState(active_node_ids=frozenset({"b", "miss2"}), produced_edge_ids=[e2.id])
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.check_graph_isomorphism(s1, s2) == 0.0

    def test_large_graphs_use_approximate_isomorphism(self):
        g = Hypergraph()
        n = 55
        for i in range(n):
            g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
        edge_ids = []
        for i in range(n - 1):
            e = g.add_edge(Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i + 1}"}), label="rel"))
            edge_ids.append(e.id)
        mw = MultiwayEngine(g)
        shared = frozenset({f"n{i}" for i in range(n)})
        s1 = MultiwayState(active_node_ids=shared, produced_edge_ids=edge_ids)
        s2 = MultiwayState(active_node_ids=shared, produced_edge_ids=edge_ids)
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.check_graph_isomorphism(s1, s2) == 0.8

    def test_approximate_empty_graphs(self):
        import networkx as nx

        g = Hypergraph()
        mw = MultiwayEngine(g)
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci._approximate_isomorphism(nx.DiGraph(), nx.DiGraph()) == 1.0

    def test_approximate_degree_mismatch(self):
        import networkx as nx

        g = Hypergraph()
        mw = MultiwayEngine(g)
        ci = StateConvergenceEngine(g, mw.multiway)
        ga = nx.DiGraph([(0, 1), (1, 2)])
        gb = nx.DiGraph([(0, 1), (0, 2), (1, 2)])
        assert ci._approximate_isomorphism(ga, gb) == 0.0

    def test_approximate_in_degree_mismatch(self):
        import networkx as nx

        g = Hypergraph()
        mw = MultiwayEngine(g)
        ci = StateConvergenceEngine(g, mw.multiway)
        ga = nx.DiGraph([(0, 1), (0, 2)])
        gb = nx.DiGraph([(0, 1), (2, 1)])
        assert ci._approximate_isomorphism(ga, gb) == 0.0

    def test_approximate_triangle_mismatch(self):
        import networkx as nx

        g = Hypergraph()
        mw = MultiwayEngine(g)
        ci = StateConvergenceEngine(g, mw.multiway)
        ga = nx.DiGraph([(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])
        gb = nx.DiGraph([(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)])
        assert ci._approximate_isomorphism(ga, gb) == 0.0

    def test_approximate_all_match(self):
        import networkx as nx

        g = Hypergraph()
        mw = MultiwayEngine(g)
        ci = StateConvergenceEngine(g, mw.multiway)
        ga = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
        gb = nx.DiGraph([(0, 2), (2, 1), (1, 0)])
        assert ci._approximate_isomorphism(ga, gb) == 0.8
