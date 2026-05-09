from __future__ import annotations

import pytest

from hyper3.boundary_reasoning import (
    BoundaryAwareReasonConfig,
    BoundaryNavigationReport,
    BoundaryReasoningEngine,
    DecidabilityAssessment,
)
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def _add_node(g: Hypergraph, label: str, data: dict | None = None) -> str:
    n = Hypernode(label=label, data=data)
    g.add_node(n)
    return n.id


def _add_edge(
    g: Hypergraph,
    source_id: str,
    target_id: str,
    label: str = "related",
    weight: float = 1.0,
) -> Hyperedge:
    e = Hyperedge(
        source_ids=frozenset({source_id}),
        target_ids=frozenset({target_id}),
        label=label,
        weight=weight,
    )
    return g.add_edge(e)


class TestSelfReference:
    def test_direct_self_loop(self):
        g = Hypergraph()
        nid = _add_node(g, "A")
        _add_edge(g, nid, nid, "defines")
        engine = BoundaryReasoningEngine(g)
        score = engine._detect_self_reference(nid)
        assert score == 0.9

    def test_two_hop_self_reference(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "defines")
        _add_edge(g, b, a, "states")
        engine = BoundaryReasoningEngine(g)
        score = engine._detect_self_reference(a)
        assert score == 0.7

    def test_semantic_self_reference(self):
        g = Hypergraph()
        a = _add_node(g, "recursion")
        b = _add_node(g, "recursion")
        _add_edge(g, a, b, "related")
        engine = BoundaryReasoningEngine(g)
        score = engine._detect_self_reference(a)
        assert score == 0.4

    def test_no_self_reference(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "causes")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_self_reference(a) == 0.0


class TestUniversalQuantification:
    def test_explicit_scope_all(self):
        g = Hypergraph()
        nid = _add_node(g, "universal_claim", data={"scope": "all"})
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_universal(nid) == 0.8

    def test_explicit_quantifier(self):
        g = Hypergraph()
        nid = _add_node(g, "claim", data={"quantifier": "universal"})
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_universal(nid) == 0.8

    def test_edge_label_forall(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "forall")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_universal(a) == 0.4

    def test_no_universal(self):
        g = Hypergraph()
        nid = _add_node(g, "A", data={"scope": "specific"})
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_universal(nid) == 0.0


class TestNegationCycle:
    def test_direct_negation_cycle(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "supports")
        _add_edge(g, b, a, "opposes")
        engine = BoundaryReasoningEngine(g)
        cycles = engine.detect_negation_cycles(a)
        assert len(cycles) >= 1
        score = engine._detect_negation_score(a)
        assert score >= 0.7

    def test_causes_prevents_cycle(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "causes")
        _add_edge(g, b, a, "prevents")
        engine = BoundaryReasoningEngine(g)
        cycles = engine.detect_negation_cycles(a)
        assert len(cycles) >= 1

    def test_no_negation_cycle(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "causes")
        _add_edge(g, b, a, "supports")
        engine = BoundaryReasoningEngine(g)
        cycles = engine.detect_negation_cycles(a)
        assert len(cycles) == 0

    def test_custom_negation_pairs(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "yes")
        _add_edge(g, b, a, "no")
        engine = BoundaryReasoningEngine(g, negation_pairs={"yes": "no"})
        cycles = engine.detect_negation_cycles(a)
        assert len(cycles) >= 1


class TestInfiniteRegress:
    def test_chain_of_four(self):
        g = Hypergraph()
        nodes = [_add_node(g, f"N{i}") for i in range(5)]
        for i in range(4):
            _add_edge(g, nodes[i], nodes[i + 1], "depends_on")
        engine = BoundaryReasoningEngine(g)
        chains = engine.detect_infinite_regress(nodes[0])
        assert len(chains) >= 1
        assert any(len(c) >= 4 for c in chains)

    def test_chain_of_six(self):
        g = Hypergraph()
        nodes = [_add_node(g, f"N{i}") for i in range(7)]
        for i in range(6):
            _add_edge(g, nodes[i], nodes[i + 1], "requires")
        engine = BoundaryReasoningEngine(g)
        score = engine._detect_regress_score(nodes[0])
        assert score == 0.8

    def test_no_regress(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "causes")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_regress_score(a) == 0.0


class TestFixedPoint:
    def test_bidirectional_defines(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "defines")
        _add_edge(g, b, a, "defines")
        engine = BoundaryReasoningEngine(g)
        score = engine._detect_fixed_point(a)
        assert score == 0.7

    def test_no_fixed_point(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "defines")
        _add_edge(g, b, a, "causes")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_fixed_point(a) == 0.0


class TestUndecidableSimilarity:
    def test_halting_keyword(self):
        g = Hypergraph()
        nid = _add_node(g, "halting problem")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_undecidable_sim(nid) == 0.5

    def test_turing_keyword(self):
        g = Hypergraph()
        nid = _add_node(g, "Turing machine completeness")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_undecidable_sim(nid) == 0.5

    def test_no_match(self):
        g = Hypergraph()
        nid = _add_node(g, "simple concept")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_undecidable_sim(nid) == 0.0


class TestAssessment:
    def test_clean_graph_decidable(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "causes")
        engine = BoundaryReasoningEngine(g)
        assessment = engine.assess(a)
        assert assessment.decidability_score < 0.25
        assert assessment.boundary_zone == "decidable"
        assert assessment.recommended_strategy == "standard"

    def test_self_referential_boundary(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        _add_edge(g, a, a, "defines")
        engine = BoundaryReasoningEngine(g)
        assessment = engine.assess(a)
        assert assessment.decidability_score > 0.15
        assert assessment.indicators["self_reference"] == 0.9

    def test_near_boundary_classification(self):
        g = Hypergraph()
        a = _add_node(g, "A", data={"scope": "all"})
        b = _add_node(g, "B")
        _add_edge(g, a, b, "related")
        engine = BoundaryReasoningEngine(g)
        assessment = engine.assess(a)
        assert assessment.indicators["universal_quantification"] == 0.8
        assert assessment.boundary_zone in ("decidable", "near_boundary")

    def test_beyond_boundary(self):
        g = Hypergraph()
        a = _add_node(g, "halting problem self-reference")
        _add_edge(g, a, a, "defines")
        _add_edge(g, a, a, "proves")
        engine = BoundaryReasoningEngine(g)
        assessment = engine.assess(a)
        assert assessment.boundary_zone in ("boundary", "beyond_boundary")
        assert assessment.recommended_strategy in ("partial", "reformulate")

    def test_assess_batch(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "halting problem")
        _add_edge(g, a, b, "causes")
        engine = BoundaryReasoningEngine(g)
        results = engine.assess_set({a, b})
        assert len(results) == 2
        scores = {r.concept_id: r.decidability_score for r in results}
        assert scores[b] > scores[a]

    def test_confidence_modifier(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        _add_edge(g, a, a, "defines")
        engine = BoundaryReasoningEngine(g)
        assessment = engine.assess(a)
        assert 0.0 < assessment.confidence_modifier < 1.0


class TestConfigureReasoning:
    def test_decidable_config(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        assessment = DecidabilityAssessment(boundary_zone="decidable")
        config = engine.configure_reasoning(assessment)
        assert config.strategy == "standard"
        assert config.max_reasoning_depth == 999
        assert config.confidence_cap == 1.0
        assert config.require_convergence is False

    def test_conservative_config(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        assessment = DecidabilityAssessment(boundary_zone="near_boundary")
        config = engine.configure_reasoning(assessment)
        assert config.strategy == "conservative"
        assert config.max_reasoning_depth == 3
        assert config.confidence_cap == 0.8
        assert config.require_convergence is True

    def test_partial_config(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        assessment = DecidabilityAssessment(boundary_zone="boundary")
        config = engine.configure_reasoning(assessment)
        assert config.strategy == "partial"
        assert config.max_reasoning_depth == 2
        assert config.confidence_cap == 0.5
        assert config.generate_alternatives is True

    def test_reformulate_config(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        assessment = DecidabilityAssessment(boundary_zone="beyond_boundary")
        config = engine.configure_reasoning(assessment)
        assert config.strategy == "reformulate"
        assert config.max_reasoning_depth == 1
        assert config.confidence_cap == 0.3
        assert config.generate_alternatives is True


class TestNavigate:
    def test_navigation_report_full(self):
        g = Hypergraph()
        a = _add_node(g, "halting problem")
        _add_edge(g, a, a, "defines")
        engine = BoundaryReasoningEngine(g)
        report = engine.navigate(a)
        assert isinstance(report, BoundaryNavigationReport)
        assert report.concept == "halting problem"
        assert isinstance(report.assessment, DecidabilityAssessment)
        assert isinstance(report.reasoning_config, BoundaryAwareReasonConfig)
        assert len(report.warnings) > 0

    def test_navigation_decidable_no_warnings(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, a, b, "causes")
        engine = BoundaryReasoningEngine(g)
        report = engine.navigate(a)
        assert len(report.warnings) == 0


class TestAlternatives:
    def test_alternatives_for_self_reference(self):
        g = Hypergraph()
        a = _add_node(g, "claim")
        _add_edge(g, a, a, "defines")
        engine = BoundaryReasoningEngine(g)
        assessment = DecidabilityAssessment(
            concept="claim",
            concept_id=a,
            indicators={"self_reference": 0.9},
        )
        alts = engine.generate_alternatives(a, assessment)
        assert any("Stratified" in alt for alt in alts)

    def test_alternatives_for_negation_cycle(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        assessment = DecidabilityAssessment(
            concept="A",
            concept_id=a,
            indicators={"negation_cycle": 0.9},
        )
        engine = BoundaryReasoningEngine(g)
        alts = engine.generate_alternatives(a, assessment)
        assert any("Consistent fragment" in alt for alt in alts)

    def test_alternatives_for_infinite_regress(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        assessment = DecidabilityAssessment(
            concept="A",
            concept_id=a,
            indicators={"infinite_regress": 0.8},
        )
        engine = BoundaryReasoningEngine(g)
        alts = engine.generate_alternatives(a, assessment)
        assert any("Base case" in alt for alt in alts)

    def test_always_includes_constrained(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        engine = BoundaryReasoningEngine(g)
        assessment = DecidabilityAssessment(concept="A", concept_id=a, indicators={})
        alts = engine.generate_alternatives(a, assessment)
        assert any("Constrained" in alt for alt in alts)

    def test_missing_node_returns_empty(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        assessment = DecidabilityAssessment(indicators={"self_reference": 0.9})
        assert engine.generate_alternatives("nonexistent", assessment) == []


class TestEdgeCases:
    def test_empty_graph(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        a = _add_node(g, "A")
        assessment = engine.assess(a)
        assert assessment.decidability_score == 0.0
        assert assessment.boundary_zone == "decidable"

    def test_isolated_node(self):
        g = Hypergraph()
        nid = _add_node(g, "isolated")
        engine = BoundaryReasoningEngine(g)
        assessment = engine.assess(nid)
        assert assessment.decidability_score == 0.0
        assert assessment.confidence_modifier == 1.0

    def test_no_data_node(self):
        g = Hypergraph()
        nid = _add_node(g, "A")
        b = _add_node(g, "B")
        _add_edge(g, nid, b, "causes")
        engine = BoundaryReasoningEngine(g)
        assert engine._detect_universal(nid) == 0.0

    def test_describe_patterns_no_indicators(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        patterns = engine._describe_patterns({})
        assert patterns == []

    def test_describe_patterns_all_indicators(self):
        g = Hypergraph()
        engine = BoundaryReasoningEngine(g)
        indicators = {
            "self_reference": 0.9,
            "universal_quantification": 0.8,
            "negation_cycle": 0.9,
            "infinite_regress": 0.8,
            "fixed_point": 0.7,
            "undecidable_similarity": 0.5,
        }
        patterns = engine._describe_patterns(indicators)
        assert len(patterns) == 6


class TestResultTypes:
    def test_assessment_is_simple_result_base(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        engine = BoundaryReasoningEngine(g)
        assessment = engine.assess(a)
        assert "decidability_score" in assessment
        assert assessment["decidability_score"] == assessment.decidability_score

    def test_config_is_simple_result_base(self):
        config = BoundaryAwareReasonConfig()
        assert "strategy" in config
        assert config["strategy"] == "standard"

    def test_report_is_simple_result_base(self):
        g = Hypergraph()
        a = _add_node(g, "A")
        engine = BoundaryReasoningEngine(g)
        report = engine.navigate(a)
        assert "warnings" in report


class TestIntegration:
    def test_assess_boundary_via_facade(self):
        from hyper3.memory import HypergraphMemory
        from hyper3.rules import TransitiveRule

        mem = HypergraphMemory(rules=[TransitiveRule(edge_label="causes")])
        mem.add("A")
        result = mem.assess_boundary("A")
        assert result is not None
        assert isinstance(result, DecidabilityAssessment)
        assert result.concept == "A"
        assert result.boundary_zone == "decidable"

    def test_assess_boundary_missing_concept(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory()
        assert mem.assess_boundary("nonexistent") is None

    def test_navigate_boundary_via_facade(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory()
        mem.add("halting problem")
        result = mem.navigate_boundary("halting problem")
        assert result is not None
        assert isinstance(result, BoundaryNavigationReport)
        assert result.concept == "halting problem"

    def test_navigate_boundary_missing_concept(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory()
        assert mem.navigate_boundary("nonexistent") is None

    def test_reason_boundary_aware_decidable_proceeds_normally(self):
        from hyper3.memory import HypergraphMemory
        from hyper3.rules import TransitiveRule

        mem = HypergraphMemory(rules=[TransitiveRule(edge_label="causes")])
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="causes")
        mem.link("B", "C", label="causes")
        result = mem.reason_boundary_aware({"A", "B"}, max_depth=2)
        assert result.error is None

    def test_reason_boundary_aware_boundary_limits_depth(self):
        from hyper3.memory import HypergraphMemory
        from hyper3.rules import TransitiveRule

        mem = HypergraphMemory(rules=[TransitiveRule(edge_label="causes")])
        mem.add("halting problem self-reference")
        mem.link("halting problem self-reference", "halting problem self-reference", label="defines")
        mem.add("B")
        mem.link("halting problem self-reference", "B", label="causes")
        result = mem.reason_boundary_aware({"halting problem self-reference"}, max_depth=5)
        assert result.error is None

    def test_assess_boundary_self_loop(self):
        from hyper3.memory import HypergraphMemory

        mem = HypergraphMemory()
        mem.add("self_ref")
        mem.link("self_ref", "self_ref", label="defines")
        result = mem.assess_boundary("self_ref")
        assert result is not None
        assert result.indicators["self_reference"] == 0.9
        assert result.boundary_zone != "decidable"

    def test_reason_boundary_aware_empty_seeds(self):
        from hyper3.memory import HypergraphMemory
        from hyper3.rules import TransitiveRule

        mem = HypergraphMemory(rules=[TransitiveRule(edge_label="causes")])
        result = mem.reason_boundary_aware({"nonexistent"})
        assert result.error is not None
