from __future__ import annotations

import time
import uuid

import numpy as np
import pytest

from hyper3.retrieval_activation import SpreadingActivation
from hyper3.multiway_branchial import BranchialSpace, MultiScaleAnalysis, ScaleLevel
from hyper3.multiway_causal import StateConvergenceEngine
from hyper3.belief import SamplingProfile, BeliefLayer
from hyper3.cache import LazyCache
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, Modality
from hyper3.memory import HypergraphMemory
from hyper3.multiway import MultiwayEngine, MultiwayGraph, MultiwayState
from hyper3.multi_perspective import MultiPerspectiveAnalyzer
from hyper3.multiway_rulial import RulialSpace
from hyper3.rules import (
    StructuralProjectionRule,
    HubInferenceRule,
    ContextualSubstitutionRule,
    RuleMatch,
)
from hyper3.structural_anomaly import ExplorationReport, StructuralAnomalyDetector


class TestGraphIsomorphismForCausalInvariance:
    def test_isomorphic_structures_detected(self):
        g = Hypergraph()
        a = Hypernode(label="A", data="same")
        b = Hypernode(label="B", data="same")
        c = Hypernode(label="C", data="same")
        d = Hypernode(label="D", data="same")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_node(d)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel")
        e2 = Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({d.id}), label="rel")
        g.add_edge(e1)
        g.add_edge(e2)
        mw = MultiwayGraph()
        s1 = MultiwayState(active_node_ids=frozenset({a.id, b.id}), produced_edge_ids=[e1.id])
        s2 = MultiwayState(active_node_ids=frozenset({c.id, d.id}), produced_edge_ids=[e2.id])
        mw.add_state(s1)
        mw.add_state(s2)
        engine = StateConvergenceEngine(g, mw, threshold=0.0)
        score = engine.check_graph_isomorphism(s1, s2)
        assert score == 1.0

    def test_non_isomorphic_structures(self):
        g = Hypergraph()
        for lbl in "ABCD":
            g.add_node(Hypernode(label=lbl, data=lbl))
        e1 = Hyperedge(source_ids=frozenset({g.get_node_by_label("A").id}), target_ids=frozenset({g.get_node_by_label("B").id}), label="rel")
        g.add_edge(e1)
        e2 = Hyperedge(source_ids=frozenset({g.get_node_by_label("C").id}), target_ids=frozenset({g.get_node_by_label("D").id}), label="rel")
        g.add_edge(e2)
        e3 = Hyperedge(source_ids=frozenset({g.get_node_by_label("D").id}), target_ids=frozenset({g.get_node_by_label("A").id}), label="back")
        g.add_edge(e3)
        mw = MultiwayGraph()
        s1 = MultiwayState(active_node_ids=frozenset({g.get_node_by_label("A").id, g.get_node_by_label("B").id}), produced_edge_ids=[e1.id])
        s2 = MultiwayState(active_node_ids=frozenset({g.get_node_by_label("C").id, g.get_node_by_label("D").id, g.get_node_by_label("A").id}), produced_edge_ids=[e2.id, e3.id])
        mw.add_state(s1)
        mw.add_state(s2)
        engine = StateConvergenceEngine(g, mw, threshold=0.0)
        score = engine.check_graph_isomorphism(s1, s2)
        assert score == 0.0

    def test_empty_states_isomorphic(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        s1 = MultiwayState()
        s2 = MultiwayState()
        mw.add_state(s1)
        mw.add_state(s2)
        engine = StateConvergenceEngine(g, mw)
        score = engine.check_graph_isomorphism(s1, s2)
        assert score == 1.0


class TestStructuralProjectionRule:
    def test_no_embedding_engine_returns_empty(self):
        g = Hypergraph()
        for lbl in "ABCD":
            g.add_node(Hypernode(label=lbl))
        rule = StructuralProjectionRule()
        matches = rule.find_matches(g, frozenset(n.id for n in g.nodes))
        assert matches == []

    def test_with_mock_embedding_engine(self):
        g = Hypergraph()
        nodes = []
        for lbl in "ABCD":
            n = Hypernode(label=lbl)
            g.add_node(n)
            nodes.append(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), label="rel"))

        class MockEngine:
            def get_embedding(self, node_id):
                emb_map = {
                    nodes[0].id: np.array([1.0, 0.0, 0.0]),
                    nodes[1].id: np.array([0.0, 1.0, 0.0]),
                    nodes[2].id: np.array([0.5, 0.0, 0.0]),
                    nodes[3].id: np.array([0.0, 0.5, 0.0]),
                }
                return emb_map.get(node_id)

        rule = StructuralProjectionRule(similarity_threshold=0.5)
        rule.set_embedding_engine(MockEngine())
        matches = rule.find_matches(g, frozenset(n.id for n in nodes))
        assert isinstance(matches, list)

    def test_apply_creates_edge(self):
        g = Hypergraph()
        nodes = []
        for lbl in "ABCD":
            n = Hypernode(label=lbl)
            g.add_node(n)
            nodes.append(n)
        rule = StructuralProjectionRule()
        match = RuleMatch(
            rule_name=rule.name,
            bindings={"A": nodes[0].id, "B": nodes[1].id, "C": nodes[2].id, "D": nodes[3].id},
            context={"analogy_score": 0.8},
        )
        new_n, new_e = rule.apply(g, match)
        assert len(new_e) == 1
        edge = g.get_edge(new_e[0])
        assert edge is not None
        assert nodes[2].id in edge.source_ids
        assert nodes[3].id in edge.target_ids

    def test_serialization(self):
        rule = StructuralProjectionRule(edge_label="rel", similarity_threshold=0.6)
        d = rule.to_dict()
        assert d["rule_type"] == "StructuralProjectionRule"
        restored = StructuralProjectionRule._from_dict(d)
        assert restored._edge_label == "rel"
        assert restored._threshold == 0.6


class TestHubInferenceRule:
    def test_detects_recurring_pattern(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        c = Hypernode(label="C")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        for _ in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="leads_to"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="also"))
        rule = HubInferenceRule(min_support=2, confidence_threshold=0.5)
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        ab_matches = [m for m in matches if m.bindings["cause"] == a.id and m.bindings["effect"] == b.id]
        assert len(ab_matches) == 1
        assert ab_matches[0].context["confidence"] >= 0.5
        assert ab_matches[0].context["support"] >= 2

    def test_skips_below_support(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="once"))
        rule = HubInferenceRule(min_support=5)
        matches = rule.find_matches(g, frozenset({a.id, b.id}))
        assert len(matches) == 0

    def test_apply_creates_causes_edge(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        rule = HubInferenceRule(causes_label="causes")
        match = RuleMatch(rule_name=rule.name, bindings={"cause": a.id, "effect": b.id}, context={"support": 3, "confidence": 0.75})
        new_n, new_e = rule.apply(g, match)
        edge = g.get_edge(new_e[0])
        assert edge.label == "causes"
        assert edge.metadata.custom["confidence"] == 0.75

    def test_serialization(self):
        rule = HubInferenceRule(min_support=3, confidence_threshold=0.7, causes_label="implies")
        d = rule.to_dict()
        restored = HubInferenceRule._from_dict(d)
        assert restored._min_support == 3
        assert restored._confidence_threshold == 0.7
        assert restored._causes_label == "implies"


class TestContextualSubstitutionRule:
    def test_detects_similar_nodes(self):
        g = Hypergraph()
        a = Hypernode(label="cat", data={"type": "feline"})
        b = Hypernode(label="dog", data={"type": "canine"})
        c = Hypernode(label="car", data={"wheels": 4})
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        rule = ContextualSubstitutionRule(similarity_threshold=0.0)
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) >= 1

    def test_creates_bidirectional_edges(self):
        g = Hypergraph()
        a = Hypernode(label="x", data=42)
        b = Hypernode(label="y", data=42)
        g.add_node(a)
        g.add_node(b)
        rule = ContextualSubstitutionRule()
        match = RuleMatch(rule_name=rule.name, bindings={"A": a.id, "B": b.id}, context={"similarity": 1.0})
        new_n, new_e = rule.apply(g, match)
        assert len(new_e) == 2
        e1 = g.get_edge(new_e[0])
        e2 = g.get_edge(new_e[1])
        assert a.id in (e1.source_ids | e2.source_ids)
        assert b.id in (e1.target_ids | e2.target_ids)

    def test_skips_existing_substitution(self):
        g = Hypergraph()
        a = Hypernode(label="x", data=1)
        b = Hypernode(label="y", data=1)
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="substitutes_for"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({a.id}), label="substitutes_for"))
        rule = ContextualSubstitutionRule()
        matches = rule.find_matches(g, frozenset({a.id, b.id}))
        assert len(matches) == 0

    def test_serialization(self):
        rule = ContextualSubstitutionRule(similarity_threshold=0.9, substitution_label="equiv")
        d = rule.to_dict()
        restored = ContextualSubstitutionRule._from_dict(d)
        assert restored._threshold == 0.9
        assert restored._label == "equiv"


class TestPerRuleEffectivenessTracking:
    def test_record_outcomes(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        rs.record_rule_outcome("transitive(A)", "applied")
        rs.record_rule_outcome("transitive(A)", "useful")
        rs.record_rule_outcome("transitive(A)", "reinforced")
        rs.record_rule_outcome("inverse(X)", "applied")
        rs.record_rule_outcome("inverse(X)", "pruned")
        outcomes = rs.rule_outcomes
        assert outcomes["transitive(A)"]["applications"] == 2
        assert outcomes["transitive(A)"]["useful"] == 1
        assert outcomes["transitive(A)"]["reinforced"] == 1
        assert outcomes["inverse(X)"]["pruned"] == 1

    def test_effectiveness_scores(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        for _ in range(5):
            rs.record_rule_outcome("good_rule", "useful")
        for _ in range(5):
            rs.record_rule_outcome("bad_rule", "applied")
        eff = rs.get_rule_effectiveness()
        assert eff["good_rule"]["effectiveness"] == pytest.approx(1.0)
        assert eff["bad_rule"]["effectiveness"] == pytest.approx(0.0)

    def test_best_rules(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        for _ in range(3):
            rs.record_rule_outcome("rule_a", "useful")
        for _ in range(3):
            rs.record_rule_outcome("rule_b", "applied")
        best = rs.get_best_rules(top_k=2)
        assert best[0][0] == "rule_a"
        assert best[0][1] > best[1][1]

    def test_record_rule_application_tracks_outcome(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        rs.record_rule_application("transitive(X)")
        outcomes = rs.rule_outcomes
        assert "transitive(X)" in outcomes
        assert outcomes["transitive(X)"]["applications"] == 1

    def test_analyze_includes_effectiveness(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        rs.record_rule_outcome("test_rule", "useful")
        analysis = rs.analyze()
        assert "rule_effectiveness" in analysis
        assert "test_rule" in analysis["rule_effectiveness"]


class TestSamplingProfileLearning:
    def test_record_profile_outcome(self):
        g = Hypergraph()
        qcl = BeliefLayer(g)
        qcl.record_basis_outcome("linguistic", True)
        qcl.record_basis_outcome("linguistic", True)
        qcl.record_basis_outcome("linguistic", False)
        eff = qcl.basis_effectiveness
        assert eff["linguistic"] == pytest.approx(2.0 / 3.0)

    def test_get_effective_profile_returns_valid(self):
        g = Hypergraph()
        qcl = BeliefLayer(g)
        profile = qcl.get_effective_basis()
        assert profile in qcl.bases

    def test_effective_bias_favors_successful(self):
        g = Hypergraph()
        n1 = Hypernode(label="test1")
        g.add_node(n1)
        qcl = BeliefLayer(g)
        for _ in range(50):
            qcl.record_basis_outcome("temporal", True)
        for _ in range(50):
            qcl.record_basis_outcome("linguistic", False)
        counts: dict[str, int] = {}
        for _ in range(100):
            b = qcl.get_effective_basis()
            counts[b] = counts.get(b, 0) + 1
        assert counts.get("temporal", 0) > counts.get("linguistic", 0)


class TestAdaptiveCoherenceTime:
    def test_adapt_scales_with_interpretations(self):
        from hyper3.belief import BeliefState
        qs = BeliefState(created_at=time.time())
        qs.add_outcome("n1", 0.5)
        qs.add_outcome("n2", 0.5)
        qs.normalize()
        qs.adapt_coherence(2)
        assert qs.coherence_time > qs.base_coherence_time

    def test_urgency_shortens_coherence(self):
        from hyper3.belief import BeliefState
        qs = BeliefState(created_at=time.time())
        qs.adapt_coherence(1, urgency=10.0)
        assert qs.coherence_time < qs.base_coherence_time

    def test_create_distribution_adapts(self):
        g = Hypergraph()
        for lbl in "ABCD":
            g.add_node(Hypernode(label=lbl))
        qcl = BeliefLayer(g)
        ids = [g.get_node_by_label(lbl).id for lbl in "ABCD"]
        qs = qcl.create_distribution(ids)
        assert qs.coherence_time != qs.base_coherence_time


class TestMultiScaleBranchialAnalysis:
    def _build_multiway(self):
        g = Hypergraph()
        for i in range(8):
            g.add_node(Hypernode(label=f"n{i}"))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset(n.id for n in g.nodes[:4]))
        mw.add_state(root)
        for i in range(4):
            child = MultiwayState(
                parent_id=root.id,
                active_node_ids=frozenset(n.id for n in g.nodes[i:i+4]),
                depth=1,
                rule_applied=f"rule_{i}",
            )
            mw.add_state(child)
        return g, mw

    def test_returns_multi_scale_analysis(self):
        g, mw = self._build_multiway()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert isinstance(result, MultiScaleAnalysis)
        assert isinstance(result.macro, ScaleLevel)
        assert isinstance(result.meso, ScaleLevel)
        assert isinstance(result.micro, ScaleLevel)

    def test_macro_has_fewer_clusters(self):
        g, mw = self._build_multiway()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert result.macro.n_clusters <= result.meso.n_clusters

    def test_cross_scale_insights_generated(self):
        g, mw = self._build_multiway()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert len(result.cross_scale_insights) > 0

    def test_insufficient_states(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="only"))
        mw = MultiwayGraph()
        mw.add_state(MultiwayState())
        bs = BranchialSpace(g, mw)
        result = bs.multi_scale_analysis()
        assert result.macro.n_clusters == 0


class TestLazyMultiwayExpansion:
    def test_expand_lazy_yields_states(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        c = Hypernode(label="C")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="rel"))
        from hyper3.rules import TransitiveRule
        engine = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        states = list(engine.expand_lazy(
            {a.id, b.id, c.id}, [rule], max_depth=2, max_total_states=10,
        ))
        assert len(states) >= 1
        assert states[0][1] == 0

    def test_expand_lazy_respects_max_states(self):
        g = Hypergraph()
        nodes = []
        for i in range(5):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            nodes.append(n)
        for i in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i+1].id}), label="e"))
        from hyper3.rules import TransitiveRule
        engine = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="e")
        states = list(engine.expand_lazy(
            frozenset(n.id for n in nodes), [rule], max_depth=3, max_total_states=5,
        ))
        assert len(states) <= 5


class TestTraversalPrefetching:
    def test_enable_prefetch(self):
        cache = LazyCache()
        assert not cache.prefetch_enabled
        cache.enable_prefetch(True)
        assert cache.prefetch_enabled

    def test_record_access_tracks_transitions(self):
        cache = LazyCache()
        cache.enable_prefetch(True)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")
        cache.get("b")
        cache.get("c")
        predicted = cache.predict_next("a")
        assert "b" in predicted

    def test_predict_next_empty_history(self):
        cache = LazyCache()
        assert cache.predict_next("x") == []

    def test_prefetch_neighbors(self):
        cache = LazyCache()
        cache.put("center", "value")
        added = cache.prefetch_neighbors("center", {"n1": "v1", "n2": "v2"})
        assert added == 2
        assert cache.get("n1") == "v1"
        assert cache.get("n2") == "v2"

    def test_prefetch_skips_existing(self):
        cache = LazyCache()
        cache.put("n1", "existing")
        added = cache.prefetch_neighbors("center", {"n1": "new", "n2": "v2"})
        assert added == 1


class TestHypergraphMemoryPrefetchAPI:
    def test_enable_prefetch(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a", data={"x": 1})
        mem.store("b", data={"x": 2})
        mem.relate("a", "b", label="e")
        mem.enable_prefetch(True)
        assert mem.cache.prefetch_enabled

    def test_record_access_and_predict(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a", data={"x": 1})
        mem.store("b", data={"x": 2})
        mem.store("c", data={"x": 3})
        mem.enable_prefetch(True)
        mem.record_access("a")
        mem.record_access("b")
        mem.record_access("c")
        predicted = mem.predict_next_access("a", top_k=3)
        assert "b" in predicted

    def test_prefetch_neighbors(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("center", data={"x": 0})
        mem.store("n1", data={"x": 1})
        mem.store("n2", data={"x": 2})
        mem.relate("center", "n1", label="e")
        mem.relate("center", "n2", label="e")
        preloaded = mem.prefetch_neighbors("center")
        assert preloaded >= 2

    def test_predict_next_unknown_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.predict_next_access("nonexistent") == []

    def test_cache_property(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.cache is not None
        assert mem.cache.size >= 0


class TestFrameEffectivenessLearning:
    def test_record_frame_outcome(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="test"))
        cr = MultiPerspectiveAnalyzer(g)
        cr.record_frame_outcome("classical", True)
        cr.record_frame_outcome("classical", False)
        cr.record_frame_outcome("quantum", True)
        eff = cr.get_frame_effectiveness()
        assert eff["classical"] == pytest.approx(0.5)
        assert eff["quantum"] == pytest.approx(1.0)

    def test_learned_selection_prefers_successful(self):
        g = Hypergraph()
        a = Hypernode(label="test")
        b = Hypernode(label="b")
        c = Hypernode(label="c")
        d = Hypernode(label="d")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_node(d)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="r1"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="r2"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="r3"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), label="r4"))
        cr = MultiPerspectiveAnalyzer(g)
        for _ in range(20):
            cr.record_frame_outcome("quantum", True)
            cr.record_frame_outcome("classical", False)
            cr.record_frame_outcome("hypergraph", False)
            cr.record_frame_outcome("probabilistic", False)
        quantum_count = 0
        for _ in range(50):
            name, _ = cr.select_optimal_frame_learned("test")
            if name == "quantum":
                quantum_count += 1
        assert quantum_count > 5

    def test_analyze_includes_effectiveness(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        cr.record_frame_outcome("classical", True)
        analysis = cr.analyze()
        assert "frame_effectiveness" in analysis


class TestExplorationReportGeneration:
    def test_partial_proof_dataclass(self):
        report = ExplorationReport(
            concept="test",
            expanded_nodes=["a", "b"],
            total_branches_estimated=10,
            branches_explored=3,
            coverage=0.3,
        )
        assert report.coverage_pct == pytest.approx(30.0)
        assert report.bounds == {}

    def test_anomalous_produces_exploration_report(self):
        g = Hypergraph()
        for lbl in "ABCDE":
            g.add_node(Hypernode(label=lbl))
        a = g.get_node_by_label("A")
        for lbl in "BCDE":
            n = g.get_node_by_label(lbl)
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({n.id}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("A", {"cyclic_structure": 0.1, "contradiction": 0.1, "structural_anomaly": 0.1})
        partial_results = result.partial_results
        anomalous_results = [r for r in partial_results if r.get("status") == "anomalous"]
        if not anomalous_results:
            assert result.anomaly_status in ("boundary", "anomalous")
            return
        assert "exploration_report" in anomalous_results[0]
        report = anomalous_results[0]["exploration_report"]
        assert "coverage_pct" in report
        assert "branches_explored" in report

    def test_boundary_aware_distinguishes_conclusions(self):
        g = Hypergraph()
        for lbl in "ABCD":
            g.add_node(Hypernode(label=lbl))
        a = g.get_node_by_label("A")
        for lbl in "BCD":
            n = g.get_node_by_label(lbl)
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({n.id}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("A", {"cyclic_structure": 0.6, "high_centrality": 0.6})
        boundary_results = [r for r in result.partial_results if r.get("status") == "boundary"]
        if not boundary_results:
            assert result.anomaly_status in ("boundary", "anomalous", "low_risk")
            return
        br = boundary_results[0]
        assert "structural_conclusions" in br
        assert "assumption_dependent" in br
        assert isinstance(br["structural_conclusions"], list)
        assert isinstance(br["assumption_dependent"], list)
