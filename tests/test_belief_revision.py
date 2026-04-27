from __future__ import annotations

import pytest

from hyper3 import CognitiveMemory
from hyper3.belief_revision import BeliefRevisionEngine, Contradiction


class TestBeliefRevisionBasic:
    def test_no_contradictions(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="supports")
        contradictions = mem.detect_contradictions()
        assert contradictions == []

    def test_direct_contradiction(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="supports")
        mem.relate("A", "B", label="opposes")
        contradictions = mem.detect_contradictions()
        assert len(contradictions) >= 1
        assert contradictions[0]["type"] == "negation"

    def test_revise_removes_contradiction(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="supports")
        edge_b = mem.relate("A", "B", label="opposes")
        edge_b.weight = 0.5
        result = mem.revise_beliefs(strategy="higher_weight")
        assert result.contradictions_detected >= 1
        assert result.edges_removed_count >= 1

    def test_check_consistency(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="causes")
        mem.relate("A", "B", label="prevents")
        contradictions = mem.check_consistency("A", "B")
        assert len(contradictions) >= 1

    def test_check_consistency_clean(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="supports")
        contradictions = mem.check_consistency("A", "B")
        assert contradictions == []

    def test_check_consistency_nonexistent(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        contradictions = mem.check_consistency("X", "Y")
        assert contradictions == []


class TestBeliefRevisionEngine:
    def test_negation_map(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        engine = BeliefRevisionEngine(mem.graph, mem._provenance)
        nm = engine.negation_map
        assert nm["supports"] == "opposes"
        assert nm["opposes"] == "supports"
        assert nm["causes"] == "prevents"

    def test_custom_negation_map(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        engine = BeliefRevisionEngine(
            mem.graph, mem._provenance,
            custom_negations={"likes": "dislikes", "dislikes": "likes"},
        )
        nm = engine.negation_map
        assert nm["likes"] == "dislikes"

    def test_self_contradiction(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.relate("A", "A", label="enables")
        mem.relate("A", "A", label="blocks")
        engine = BeliefRevisionEngine(mem.graph, mem._provenance)
        contradictions = engine.detect_contradictions()
        found_self = any(c.contradiction_type == "self_negation" for c in contradictions)
        assert found_self

    def test_resolution_higher_confidence(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        e1 = mem.relate("A", "B", label="supports")
        e2 = mem.relate("A", "B", label="opposes")
        e1.weight = 5.0
        e2.weight = 0.5
        engine = BeliefRevisionEngine(mem.graph, mem._provenance)
        result = engine.revise(strategy="higher_confidence")
        assert result.edges_removed_count >= 1

    def test_resolution_observed_over_inferred(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        e1 = mem.relate("A", "B", label="supports")
        e2 = mem.relate("A", "B", label="opposes")
        mem._provenance.record_inference(
            edge_id=e2.id, rule_name="test", input_edge_ids=[], depth=1,
        )
        engine = BeliefRevisionEngine(mem.graph, mem._provenance)
        result = engine.revise(strategy="observed_over_inferred")
        assert result.edges_removed_count >= 1

    def test_no_contradictions_no_removal(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="connects")
        engine = BeliefRevisionEngine(mem.graph, mem._provenance)
        result = engine.revise()
        assert result.contradictions_detected == 0
        assert result.edges_removed_count == 0

    def test_belief_reviser_property(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        assert mem.belief_reviser is None
        mem.detect_contradictions()
        assert mem.belief_reviser is not None


class TestBeliefRevisionMultipleContradictions:
    def test_multiple_pairs(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="causes")
        mem.relate("A", "B", label="prevents")
        mem.relate("B", "C", label="enables")
        mem.relate("B", "C", label="blocks")
        contradictions = mem.detect_contradictions()
        assert len(contradictions) >= 2

    def test_cascade_retract(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        e1 = mem.relate("A", "B", label="supports")
        e2 = mem.relate("A", "B", label="opposes")
        mem._provenance.record_inference(
            edge_id=e2.id, rule_name="test", input_edge_ids=[e1.id], depth=1,
        )
        engine = BeliefRevisionEngine(mem.graph, mem._provenance)
        result = engine.revise()
        assert result.edges_removed_count >= 1
