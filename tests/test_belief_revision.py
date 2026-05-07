from __future__ import annotations

import time

import pytest

from hyper3 import HypergraphMemory
from hyper3.belief_revision import Contradiction, ContradictionResolver, RevisionResult


class TestBeliefRevisionBasic:
    def test_no_contradictions(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        contradictions = mem.detect_contradictions()
        assert contradictions == []

    def test_direct_contradiction(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        mem.link("A", "B", label="opposes")
        contradictions = mem.detect_contradictions()
        assert len(contradictions) == 1
        assert contradictions[0].contradiction_type == "negation"

    def test_revise_removes_contradiction(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        edge_b = mem.link("A", "B", label="opposes")
        edge_b.weight = 0.5
        result = mem.revise_beliefs(strategy="higher_weight")
        assert result.contradictions_detected == 1
        assert result.edges_removed_count == 1
        assert result.edges_kept_count == 1
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].label == "supports"

    def test_check_consistency(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="causes")
        mem.link("A", "B", label="prevents")
        contradictions = mem.check_consistency("A", "B")
        assert len(contradictions) == 1

    def test_check_consistency_clean(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        contradictions = mem.check_consistency("A", "B")
        assert contradictions == []

    def test_check_consistency_nonexistent(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        contradictions = mem.check_consistency("X", "Y")
        assert contradictions == []


class TestContradictionResolver:
    def test_negation_map(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        nm = engine.negation_map
        assert nm["supports"] == "opposes"
        assert nm["opposes"] == "supports"
        assert nm["causes"] == "prevents"

    def test_custom_negation_map(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        engine = ContradictionResolver(
            mem.graph, mem._provenance,
            custom_negations={"likes": "dislikes", "dislikes": "likes"},
        )
        nm = engine.negation_map
        assert nm["likes"] == "dislikes"

    def test_self_contradiction(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.link("A", "A", label="enables")
        mem.link("A", "A", label="blocks")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        contradictions = engine.detect_contradictions()
        assert len(contradictions) == 1
        assert contradictions[0].contradiction_type == "negation"

    def test_resolution_higher_confidence(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e1 = mem.link("A", "B", label="supports")
        e2 = mem.link("A", "B", label="opposes")
        e1.weight = 5.0
        e2.weight = 0.5
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="higher_confidence")
        assert result.edges_removed_count == 1
        assert result.edges_kept_count == 1
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].id == e1.id

    def test_resolution_observed_over_inferred(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        e2 = mem.link("A", "B", label="opposes")
        mem._provenance.record_inference(
            edge_id=e2.id, rule_name="test", input_edge_ids=[], depth=1,
        )
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="observed_over_inferred")
        assert result.edges_removed_count == 1
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].label == "supports"

    def test_no_contradictions_no_removal(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="connects")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise()
        assert result.contradictions_detected == 0
        assert result.edges_removed_count == 0
        assert result.edges_kept_count == 0
        assert result.edges_revised == 0

    def test_belief_reviser_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.belief_reviser is None
        mem.detect_contradictions()
        assert mem.belief_reviser is not None


class TestBeliefRevisionMultipleContradictions:
    def test_multiple_pairs(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="causes")
        mem.link("A", "B", label="prevents")
        mem.link("B", "C", label="enables")
        mem.link("B", "C", label="blocks")
        contradictions = mem.detect_contradictions()
        negation = [c for c in contradictions if c.contradiction_type == "negation"]
        assert len(negation) == 2

    def test_cascade_retract_with_dependent_edge(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="supports")
        e_opposes = mem.link("A", "B", label="opposes")
        e_dependent = mem.link("B", "C", label="causes")
        mem._provenance.record_inference(
            edge_id=e_dependent.id, rule_name="test",
            input_edge_ids=[e_opposes.id], depth=1,
        )
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="higher_confidence")
        assert result.edges_removed_count == 2
        cascade_actions = [a for a in result.plan.actions if a.action_type == "cascade_retract"]
        assert len(cascade_actions) == 1
        assert cascade_actions[0].edge_id == e_dependent.id
        assert e_dependent.id not in [e.id for e in mem.graph.edges]


class TestBeliefRevisionNewerStrategy:
    def test_newer_edge_survives(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e_old = mem.link("A", "B", label="supports")
        e_new = mem.link("A", "B", label="opposes")
        mem._provenance.record_inference(
            edge_id=e_old.id,
            rule_name="test",
            input_edge_ids=[],
            depth=0,
        )
        time.sleep(0.01)
        mem._provenance.record_inference(
            edge_id=e_new.id,
            rule_name="test",
            input_edge_ids=[],
            depth=0,
        )
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="newer")
        assert result.edges_removed_count == 1
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].id == e_new.id

    def test_newer_with_no_provenance_favors_first(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        mem.link("A", "B", label="opposes")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="newer")
        assert result.edges_removed_count == 1
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].label == "supports"

    def test_newer_strategy_via_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="causes")
        mem.link("A", "B", label="prevents")
        result = mem.revise_beliefs(strategy="newer")
        assert result.contradictions_detected == 1
        assert result.edges_removed_count == 1


class TestResolutionStrategiesCoverage:
    def test_higher_confidence_second_edge_wins(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e1 = mem.link("A", "B", label="supports")
        e2 = mem.link("A", "B", label="opposes")
        mem._provenance.record_inference(
            edge_id=e1.id, rule_name="test", input_edge_ids=[], depth=2,
        )
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="higher_confidence")
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].id == e2.id
        assert result.edges_kept_count == 1

    def test_higher_weight_second_edge_wins(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e1 = mem.link("A", "B", label="supports")
        e2 = mem.link("A", "B", label="opposes")
        e1.weight = 0.5
        e2.weight = 5.0
        engine = ContradictionResolver(mem.graph, mem._provenance)
        engine.revise(strategy="higher_weight")
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].id == e2.id

    def test_observed_over_inferred_first_edge_is_inferred(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e1 = mem.link("A", "B", label="supports")
        mem.link("A", "B", label="opposes")
        mem._provenance.record_inference(
            edge_id=e1.id, rule_name="test", input_edge_ids=[], depth=1,
        )
        engine = ContradictionResolver(mem.graph, mem._provenance)
        engine.revise(strategy="observed_over_inferred")
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].label == "opposes"

    def test_observed_over_inferred_both_same_status_falls_back_to_weight(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e1 = mem.link("A", "B", label="supports")
        e2 = mem.link("A", "B", label="opposes")
        e1.weight = 0.5
        e2.weight = 5.0
        engine = ContradictionResolver(mem.graph, mem._provenance)
        engine.revise(strategy="observed_over_inferred")
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].id == e2.id

    def test_unknown_strategy_defaults_to_first(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e1 = mem.link("A", "B", label="supports")
        mem.link("A", "B", label="opposes")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="nonexistent_strategy")
        assert result.edges_removed_count == 1
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].id == e1.id


class TestSameLabelEdges:
    def test_same_label_edges_between_same_endpoints_not_contradictory(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        mem.link("A", "B", label="supports")
        contradictions = mem.detect_contradictions()
        negation = [c for c in contradictions if c.contradiction_type == "negation"]
        assert len(negation) == 0


class TestSeverity:
    def test_severity_equal_weights(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports", weight=3.0)
        mem.link("A", "B", label="opposes", weight=3.0)
        contradictions = mem.detect_contradictions()
        negation = [c for c in contradictions if c.contradiction_type == "negation"]
        assert len(negation) == 1
        assert abs(negation[0].severity - 1.0) < 1e-6

    def test_severity_unequal_weights(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports", weight=1.0)
        mem.link("A", "B", label="opposes", weight=3.0)
        contradictions = mem.detect_contradictions()
        negation = [c for c in contradictions if c.contradiction_type == "negation"]
        assert len(negation) == 1
        assert abs(negation[0].severity - 0.5) < 1e-6


class TestSemanticCorrectness:
    def test_no_duplicate_contradiction_pairs(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        mem.link("A", "B", label="opposes")
        contradictions = mem.detect_contradictions()
        pairs = [frozenset({c.edge_a_id, c.edge_b_id}) for c in contradictions]
        assert len(pairs) == len(set(pairs))

    def test_all_reported_contradictions_have_contradictory_labels(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="causes")
        mem.link("A", "B", label="prevents")
        mem.link("B", "C", label="enables")
        mem.link("B", "C", label="blocks")
        mem.link("A", "C", label="supports")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        for c in engine.detect_contradictions():
            assert engine._are_contradictory(c.edge_a_label, c.edge_b_label)

    def test_negation_map_is_fully_symmetric(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        nm = engine.negation_map
        for k, v in nm.items():
            assert nm.get(v) == k, f"Asymmetric: {k}->{v} but {v}->{nm.get(v)}"

    def test_custom_negation_must_be_symmetric(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        engine = ContradictionResolver(
            mem.graph, mem._provenance,
            custom_negations={"likes": "dislikes", "dislikes": "likes"},
        )
        nm = engine.negation_map
        for k, v in nm.items():
            assert nm.get(v) == k

    def test_revise_removes_all_contradictions(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="causes")
        mem.link("A", "B", label="prevents")
        mem.link("B", "C", label="enables")
        mem.link("B", "C", label="blocks")
        mem.revise_beliefs(strategy="higher_weight")
        remaining = mem.detect_contradictions()
        assert len(remaining) == 0

    def test_revise_keeps_winner_edge_intact(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        e1 = mem.link("A", "B", label="supports", weight=5.0)
        mem.link("A", "B", label="opposes", weight=0.5)
        mem.revise_beliefs(strategy="higher_weight")
        surviving = mem.graph.get_edge(e1.id)
        assert surviving is not None
        assert surviving.weight == 5.0
        assert surviving.label == "supports"

    def test_severity_is_in_unit_range(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports", weight=0.1)
        mem.link("A", "B", label="opposes", weight=10.0)
        contradictions = mem.detect_contradictions()
        for c in contradictions:
            assert 0.0 <= c.severity <= 1.0

    def test_self_contradiction_detects_cross_direction(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="supports")
        mem.link("C", "A", label="opposes")
        contradictions = mem.detect_contradictions()
        unique_pairs = {frozenset({c.edge_a_id, c.edge_b_id}) for c in contradictions}
        assert len(contradictions) == len(unique_pairs)
        assert len(contradictions) >= 1

    def test_revise_does_nothing_without_contradictions(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="supports")
        mem.link("B", "A", label="causes")
        result = mem.revise_beliefs()
        assert result.edges_removed_count == 0
        assert result.edges_kept_count == 0

    def test_cascade_removes_all_dependents(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.add("D")
        mem.link("A", "B", label="supports")
        e_opp = mem.link("A", "B", label="opposes")
        e_dep1 = mem.link("B", "C", label="causes")
        e_dep2 = mem.link("C", "D", label="implies")
        mem._provenance.record_inference(
            edge_id=e_dep1.id, rule_name="test",
            input_edge_ids=[e_opp.id], depth=1,
        )
        mem._provenance.record_inference(
            edge_id=e_dep2.id, rule_name="test",
            input_edge_ids=[e_dep1.id], depth=2,
        )
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="higher_confidence")
        cascade_ids = {a.edge_id for a in result.plan.actions if a.action_type == "cascade_retract"}
        assert e_dep1.id in cascade_ids and e_dep2.id in cascade_ids

