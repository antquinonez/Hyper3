from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata
from hyper3.memory import HypergraphMemory
from hyper3.provenance import Explanation, ProvenanceRecord, ProvenanceTracker
from hyper3.rules import TransitiveRule


class TestProvenanceTrackerRecord:
    def test_record_inference_stores_record(self):
        tracker = ProvenanceTracker()
        rec = tracker.record_inference("e1", "transitive", input_edge_ids=["ea", "eb"])
        assert rec.edge_id == "e1"
        assert rec.rule_name == "transitive"
        assert rec.input_edge_ids == ["ea", "eb"]
        assert tracker.record_count == 1

    def test_record_inference_with_metadata(self):
        tracker = ProvenanceTracker()
        rec = tracker.record_inference("e1", "inverse", depth=2, confidence=0.9)
        assert rec.depth == 2
        assert rec.metadata.get("confidence") == 0.9

    def test_record_inference_updates_dependents(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "transitive", input_edge_ids=["ea", "eb"])
        assert "e1" in tracker.get_dependents("ea")
        assert "e1" in tracker.get_dependents("eb")


class TestProvenanceTrackerGet:
    def test_get_provenance_returns_record(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "transitive")
        rec = tracker.get_provenance("e1")
        assert rec is not None
        assert rec.edge_id == "e1"

    def test_get_provenance_returns_none_for_unknown(self):
        tracker = ProvenanceTracker()
        assert tracker.get_provenance("nonexistent") is None


class TestProvenanceTrackerIsInferred:
    def test_is_inferred_true(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "transitive")
        assert tracker.is_inferred("e1") is True

    def test_is_inferred_false_for_unknown(self):
        tracker = ProvenanceTracker()
        assert tracker.is_inferred("nonexistent") is False


class TestProvenanceTrackerRetract:
    def test_retract_removes_record(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "transitive")
        retracted = tracker.retract("e1")
        assert "e1" in retracted
        assert tracker.get_provenance("e1") is None
        assert tracker.record_count == 0

    def test_retract_unknown_returns_empty(self):
        tracker = ProvenanceTracker()
        retracted = tracker.retract("nonexistent")
        assert retracted == []

    def test_retract_cascades_to_dependents(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e_ab", "given")
        tracker.record_inference("e_bc", "given")
        tracker.record_inference("e_ac", "transitive", input_edge_ids=["e_ab", "e_bc"])
        tracker.record_inference("e_ad", "transitive", input_edge_ids=["e_ac"])
        retracted = tracker.retract("e_ab")
        assert "e_ab" in retracted
        assert "e_ac" in retracted
        assert "e_ad" in retracted
        assert tracker.record_count == 1

    def test_retract_cascade_three_levels(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "rule1")
        tracker.record_inference("e2", "rule2", input_edge_ids=["e1"])
        tracker.record_inference("e3", "rule3", input_edge_ids=["e2"])
        retracted = tracker.retract("e1")
        assert set(retracted) == {"e1", "e2", "e3"}
        assert tracker.record_count == 0


class TestProvenanceTrackerGetDependents:
    def test_get_dependents_empty(self):
        tracker = ProvenanceTracker()
        assert tracker.get_dependents("e1") == set()

    def test_get_dependents_direct(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e_child", "transitive", input_edge_ids=["e_parent"])
        deps = tracker.get_dependents("e_parent")
        assert deps == {"e_child"}

    def test_get_dependents_transitive(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "rule1")
        tracker.record_inference("e2", "rule2", input_edge_ids=["e1"])
        tracker.record_inference("e3", "rule3", input_edge_ids=["e2"])
        deps = tracker.get_dependents("e1")
        assert deps == {"e2", "e3"}


class TestProvenanceTrackerExplain:
    def _make_graph(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        c = Hypernode(label="C")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        return g, a, b, c

    def test_explain_inferred_edge(self):
        g, a, b, c = self._make_graph()
        e_ab = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="related")
        e_bc = Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="related")
        e_ac = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="inferred")
        g.add_edge(e_ab)
        g.add_edge(e_bc)
        g.add_edge(e_ac)

        tracker = ProvenanceTracker()
        tracker.record_inference(e_ac.id, "transitive", input_edge_ids=[e_ab.id, e_bc.id])

        exp = tracker.explain(e_ac.id, graph=g)
        assert exp is not None
        assert exp.source_label == "A"
        assert exp.target_label == "C"
        assert exp.rule_name == "transitive"
        assert len(exp.input_explanations) == 2

    def test_explain_given_edge(self):
        g, a, b, c = self._make_graph()
        e_ab = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="related")
        g.add_edge(e_ab)

        tracker = ProvenanceTracker()
        exp = tracker.explain(e_ab.id, graph=g)
        assert exp is not None
        assert exp.rule_name == "given"
        assert exp.source_label == "A"
        assert exp.target_label == "B"

    def test_explain_unknown_edge_returns_none(self):
        g = Hypergraph()
        tracker = ProvenanceTracker()
        assert tracker.explain("nonexistent", graph=g) is None

    def test_explain_no_graph(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "transitive")
        exp = tracker.explain("e1", graph=None)
        assert exp is not None
        assert exp.source_label == "?"

    def test_explain_max_depth_zero(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "transitive")
        assert tracker.explain("e1", graph=Hypergraph(), max_depth=0) is None


class TestExplanationRender:
    def test_render_given(self):
        exp = Explanation(
            edge_id="e1",
            source_label="A",
            target_label="B",
            edge_label="related",
            rule_name="given",
            depth=0,
            steps=["A -> B (given)"],
        )
        text = exp.render()
        assert "A -> B (given)" in text

    def test_render_inferred(self):
        inp = Explanation(
            edge_id="e_ab",
            source_label="A",
            target_label="B",
            edge_label="related",
            rule_name="given",
            depth=0,
        )
        exp = Explanation(
            edge_id="e_ac",
            source_label="A",
            target_label="C",
            edge_label="inferred",
            rule_name="transitive",
            depth=1,
            input_explanations=[inp],
        )
        text = exp.render()
        assert "A -> C (inferred) because:" in text
        assert "A -> B (given)" in text
        assert "via transitive" in text

    def test_render_with_indent(self):
        exp = Explanation(
            edge_id="e1",
            source_label="A",
            target_label="B",
            edge_label="",
            rule_name="given",
            depth=0,
        )
        text = exp.render(indent=2)
        assert text.startswith("    A -> B (given)")


class TestProvenanceTrackerClear:
    def test_clear(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "transitive")
        tracker.record_inference("e2", "inverse", input_edge_ids=["e1"])
        tracker.clear()
        assert tracker.record_count == 0
        assert tracker.get_dependents("e1") == set()
        assert tracker.records == []


class TestProvenanceTrackerProperties:
    def test_records_property(self):
        tracker = ProvenanceTracker()
        tracker.record_inference("e1", "r1")
        tracker.record_inference("e2", "r2")
        assert len(tracker.records) == 2
        ids = {r.edge_id for r in tracker.records}
        assert ids == {"e1", "e2"}

    def test_record_count(self):
        tracker = ProvenanceTracker()
        assert tracker.record_count == 0
        tracker.record_inference("e1", "r1")
        assert tracker.record_count == 1


class TestIntegrationHypergraphMemory:
    def test_explain_with_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="related")
        mem.relate("B", "C", label="related")
        rule = TransitiveRule(edge_label="related")
        mem.reason({"A", "B", "C"}, rules=[rule], max_depth=1)
        exp = mem.explain("A", "C")
        assert exp is not None
        assert exp.source_label == "A"
        assert exp.target_label == "C"

    def test_explain_given_edge(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="related")
        exp = mem.explain("A", "B")
        assert exp is not None
        assert exp.rule_name == "given"

    def test_explain_nonexistent_edge(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        assert mem.explain("A", "B") is None

    def test_explain_missing_node(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.explain("A", "B") is None

    def test_retract_inference(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="related")
        mem.relate("B", "C", label="related")
        rule = TransitiveRule(edge_label="related")
        mem.reason({"A", "B", "C"}, rules=[rule], max_depth=1)
        assert mem.explain("A", "C") is not None
        retracted = mem.retract_inference("A", "C")
        assert len(retracted) >= 1
        assert mem.explain("A", "C") is None

    def test_retract_nonexistent(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        assert mem.retract_inference("A", "B") == []

    def test_provenance_property(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert isinstance(mem.provenance, ProvenanceTracker)

    def test_provenance_records_after_reason(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="related")
        mem.relate("B", "C", label="related")
        rule = TransitiveRule(edge_label="related")
        mem.reason({"A", "B", "C"}, rules=[rule], max_depth=1)
        assert mem.provenance.record_count >= 1

    def test_load_resets_provenance(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B")
        path = str(tmp_path / "test.json")
        mem.save(path)
        mem.load(path)
        assert mem.provenance.record_count == 0


class TestCascadeRetraction:
    def test_multi_level_cascade_retraction(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.store("D")
        mem.relate("A", "B", label="rel")
        mem.relate("B", "C", label="rel")
        mem.relate("C", "D", label="rel")
        rule = TransitiveRule(edge_label="rel")
        mem.reason({"A", "B", "C", "D"}, rules=[rule], max_depth=3, max_total_states=50)
        initial_edges = mem.graph.edge_count
        inferred_labels = set()
        for edge in list(mem.graph.edges):
            if edge.label == "inferred":
                inferred_labels.add((edge.source_ids, edge.target_ids, edge.id))
        retracted_any = False
        for src_ids, tgt_ids, eid in inferred_labels:
            if mem.provenance.is_inferred(eid):
                ids = mem.provenance.retract(eid)
                for rid in ids:
                    mem.graph.remove_edge(rid)
                    retracted_any = True
        assert retracted_any
        assert mem.graph.edge_count < initial_edges

    def test_cascade_does_not_remove_given_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        e_ab = mem.relate("A", "B", label="rel")
        e_bc = mem.relate("B", "C", label="rel")
        rule = TransitiveRule(edge_label="rel")
        mem.reason({"A", "B", "C"}, rules=[rule], max_depth=1)
        mem.retract_inference("A", "C")
        assert mem.graph.get_edge(e_ab.id) is not None
        assert mem.graph.get_edge(e_bc.id) is not None

    def test_full_chain_cascade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.store("D")
        mem.relate("A", "B", label="rel")
        mem.relate("B", "C", label="rel")
        mem.relate("C", "D", label="rel")
        rule = TransitiveRule(edge_label="rel")
        mem.reason({"A", "B", "C", "D"}, rules=[rule], max_depth=3, max_total_states=50)
        provenance_count_before = mem.provenance.record_count
        assert provenance_count_before >= 1
        tracker = mem.provenance
        retracted = []
        for edge in list(mem.graph.edges):
            if edge.label == "inferred" and tracker.is_inferred(edge.id):
                ids = tracker.retract(edge.id)
                for eid in ids:
                    mem.graph.remove_edge(eid)
                    retracted.append(eid)
        assert len(retracted) >= 1
        assert tracker.record_count == 0
