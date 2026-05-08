import pytest

from hyper3.kernel import Hypergraph
from hyper3.memory import HypergraphMemory
from hyper3.temporal import (
    INVERSE_RELATIONS,
    AllenRelation,
    TemporalConstraint,
    TemporalEvent,
    TemporalReasoner,
    TimeInterval,
)


class TestTimeInterval:
    def test_creation(self):
        iv = TimeInterval(1.0, 5.0)
        assert iv.start == 1.0
        assert iv.end == 5.0

    def test_duration(self):
        iv = TimeInterval(2.0, 7.0)
        assert iv.duration == 5.0

    def test_zero_duration(self):
        iv = TimeInterval(3.0, 3.0)
        assert iv.duration == 0.0

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="must be >= start"):
            TimeInterval(5.0, 1.0)

    def test_contains_point_inside(self):
        iv = TimeInterval(1.0, 5.0)
        assert iv.contains_point(3.0) is True

    def test_contains_point_start_boundary(self):
        iv = TimeInterval(1.0, 5.0)
        assert iv.contains_point(1.0) is True

    def test_contains_point_end_boundary(self):
        iv = TimeInterval(1.0, 5.0)
        assert iv.contains_point(5.0) is True

    def test_contains_point_outside(self):
        iv = TimeInterval(1.0, 5.0)
        assert iv.contains_point(6.0) is False

    def test_overlaps_true(self):
        a = TimeInterval(1.0, 4.0)
        b = TimeInterval(3.0, 6.0)
        assert a.overlaps_interval(b) is True
        assert b.overlaps_interval(a) is True

    def test_overlaps_false(self):
        a = TimeInterval(1.0, 3.0)
        b = TimeInterval(4.0, 6.0)
        assert a.overlaps_interval(b) is False
        assert b.overlaps_interval(a) is False

    def test_overlaps_touching_endpoints(self):
        a = TimeInterval(1.0, 3.0)
        b = TimeInterval(3.0, 5.0)
        assert a.overlaps_interval(b) is False
        assert b.overlaps_interval(a) is False


class TestAllenRelationClassification:
    def _rel(self, a_s, a_e, b_s, b_e):
        return TimeInterval(a_s, a_e).relate_to(TimeInterval(b_s, b_e))

    def test_before(self):
        assert self._rel(1, 3, 5, 7) == AllenRelation.BEFORE

    def test_after(self):
        assert self._rel(5, 7, 1, 3) == AllenRelation.AFTER

    def test_meets(self):
        assert self._rel(1, 3, 3, 5) == AllenRelation.MEETS

    def test_met_by(self):
        assert self._rel(3, 5, 1, 3) == AllenRelation.MET_BY

    def test_overlaps(self):
        assert self._rel(1, 4, 3, 6) == AllenRelation.OVERLAPS

    def test_overlapped_by(self):
        assert self._rel(3, 6, 1, 4) == AllenRelation.OVERLAPPED_BY

    def test_contains(self):
        assert self._rel(1, 10, 3, 7) == AllenRelation.CONTAINS

    def test_during(self):
        assert self._rel(3, 7, 1, 10) == AllenRelation.DURING

    def test_starts(self):
        assert self._rel(1, 3, 1, 5) == AllenRelation.STARTS

    def test_started_by(self):
        assert self._rel(1, 5, 1, 3) == AllenRelation.STARTED_BY

    def test_finishes(self):
        assert self._rel(3, 5, 1, 5) == AllenRelation.FINISHES

    def test_finished_by(self):
        assert self._rel(1, 5, 3, 5) == AllenRelation.FINISHED_BY

    def test_equals(self):
        assert self._rel(1, 5, 1, 5) == AllenRelation.EQUALS


class TestInverseRelations:
    def test_all_13_have_inverses(self):
        assert len(INVERSE_RELATIONS) == 13

    def test_inverse_symmetry(self):
        for rel, inv in INVERSE_RELATIONS.items():
            assert INVERSE_RELATIONS[inv] == rel

    def test_specific_inverses(self):
        assert INVERSE_RELATIONS[AllenRelation.BEFORE] == AllenRelation.AFTER
        assert INVERSE_RELATIONS[AllenRelation.MEETS] == AllenRelation.MET_BY
        assert INVERSE_RELATIONS[AllenRelation.OVERLAPS] == AllenRelation.OVERLAPPED_BY
        assert INVERSE_RELATIONS[AllenRelation.CONTAINS] == AllenRelation.DURING
        assert INVERSE_RELATIONS[AllenRelation.STARTS] == AllenRelation.STARTED_BY
        assert INVERSE_RELATIONS[AllenRelation.FINISHES] == AllenRelation.FINISHED_BY
        assert INVERSE_RELATIONS[AllenRelation.EQUALS] == AllenRelation.EQUALS


class TestTemporalConstraint:
    def test_inverse(self):
        c = TemporalConstraint("a", "b", AllenRelation.BEFORE, confidence=0.9)
        inv = c.inverse
        assert inv.event_a_id == "b"
        assert inv.event_b_id == "a"
        assert inv.relation == AllenRelation.AFTER
        assert inv.confidence == 0.9

    def test_inverse_equals(self):
        c = TemporalConstraint("a", "b", AllenRelation.EQUALS)
        inv = c.inverse
        assert inv.relation == AllenRelation.EQUALS


class TestTemporalReasoner:
    def _make_reasoner(self):
        return TemporalReasoner(Hypergraph())

    def test_add_and_get_event(self):
        r = self._make_reasoner()
        ev = r.add_event("e1", "Event 1", 0.0, 5.0)
        assert ev.event_id == "e1"
        assert ev.label == "Event 1"
        assert ev.interval.start == 0.0
        assert ev.interval.end == 5.0
        assert r.get_event("e1") is ev
        assert r.get_event("nonexistent") is None

    def test_events_property(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 1.0)
        r.add_event("e2", "B", 2.0, 3.0)
        assert len(r.events) == 2

    def test_add_constraint(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 1.0)
        r.add_event("e2", "B", 2.0, 3.0)
        c = r.add_constraint("e1", "e2", AllenRelation.BEFORE, confidence=0.8)
        assert c.event_a_id == "e1"
        assert c.event_b_id == "e2"
        assert c.relation == AllenRelation.BEFORE
        assert len(r.constraints) == 1

    def test_infer_constraints(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 2.0)
        r.add_event("e2", "B", 1.0, 3.0)
        r.add_event("e3", "C", 4.0, 6.0)
        inferred = r.infer_constraints()
        assert len(inferred) == 3
        by_pair = {(c.event_a_id, c.event_b_id): c for c in inferred}
        assert by_pair[("e1", "e2")].relation == AllenRelation.OVERLAPS
        assert by_pair[("e1", "e3")].relation == AllenRelation.BEFORE
        assert by_pair[("e2", "e3")].relation == AllenRelation.BEFORE

    def test_find_before(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 2.0)
        r.add_event("e2", "B", 3.0, 5.0)
        r.add_event("e3", "C", 1.0, 4.0)
        before = r.find_before("e2")
        ids = {e.event_id for e in before}
        assert ids == {"e1"}

    def test_find_after(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 2.0)
        r.add_event("e2", "B", 3.0, 5.0)
        r.add_event("e3", "C", 6.0, 8.0)
        after = r.find_after("e1")
        ids = {e.event_id for e in after}
        assert ids == {"e2", "e3"}

    def test_find_overlapping(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 5.0)
        r.add_event("e2", "B", 3.0, 8.0)
        r.add_event("e3", "C", 10.0, 12.0)
        r.add_event("e4", "D", 2.0, 4.0)
        overlapping = r.find_overlapping("e1")
        ids = {e.event_id for e in overlapping}
        assert ids == {"e2", "e4"}

    def test_find_containing(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 10.0)
        r.add_event("e2", "B", 3.0, 7.0)
        containing = r.find_containing("e2")
        ids = {e.event_id for e in containing}
        assert ids == {"e1"}

    def test_causal_order(self):
        r = self._make_reasoner()
        r.add_event("e3", "C", 5.0, 6.0)
        r.add_event("e1", "A", 0.0, 1.0)
        r.add_event("e2", "B", 2.0, 3.0)
        order = r.causal_order(["e3", "e1", "e2"])
        assert order == ["e1", "e2", "e3"]

    def test_causal_order_missing_ids(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 1.0)
        order = r.causal_order(["e1", "missing"])
        assert order == ["e1"]

    def test_detect_causal_chains(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 2.0)
        r.add_event("e2", "B", 2.0, 4.0)
        r.add_event("e3", "C", 4.0, 6.0)
        chains = r.detect_causal_chains(min_chain_length=3)
        assert len(chains) == 1
        assert chains[0] == ["e1", "e2", "e3"]

    def test_detect_causal_chains_before_gap(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 1.0)
        r.add_event("e2", "B", 3.0, 4.0)
        r.add_event("e3", "C", 6.0, 7.0)
        chains = r.detect_causal_chains(min_chain_length=3)
        assert len(chains) == 1
        assert chains[0] == ["e1", "e2", "e3"]

    def test_detect_causal_chains_too_short(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 1.0)
        r.add_event("e2", "B", 3.0, 4.0)
        chains = r.detect_causal_chains(min_chain_length=3)
        assert len(chains) == 0

    def test_temporal_proximity(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 2.0)
        r.add_event("e2", "B", 3.0, 5.0)
        r.add_event("e3", "C", 10.0, 12.0)
        prox = r.temporal_proximity("e1", max_gap=2.0)
        ids = {e.event_id for e, gap in prox}
        assert ids == {"e2"}

    def test_temporal_proximity_gap_values(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 2.0)
        r.add_event("e2", "B", 4.0, 6.0)
        prox = r.temporal_proximity("e1", max_gap=5.0)
        by_id = {e.event_id: gap for e, gap in prox}
        assert by_id["e2"] == 2.0

    def test_temporal_proximity_overlapping_zero_gap(self):
        r = self._make_reasoner()
        r.add_event("e1", "A", 0.0, 5.0)
        r.add_event("e2", "B", 3.0, 8.0)
        prox = r.temporal_proximity("e1", max_gap=1.0)
        by_id = {e.event_id: gap for e, gap in prox}
        assert "e2" in by_id
        assert by_id["e2"] == 0.0

    def test_find_before_nonexistent(self):
        r = self._make_reasoner()
        assert r.find_before("missing") == []

    def test_find_after_nonexistent(self):
        r = self._make_reasoner()
        assert r.find_after("missing") == []

    def test_find_overlapping_nonexistent(self):
        r = self._make_reasoner()
        assert r.find_overlapping("missing") == []

    def test_find_containing_nonexistent(self):
        r = self._make_reasoner()
        assert r.find_containing("missing") == []

    def test_temporal_proximity_nonexistent(self):
        r = self._make_reasoner()
        assert r.temporal_proximity("missing") == []


class TestMemoryIntegration:
    def test_add_temporal_event(self):
        mem = HypergraphMemory(evolve_interval=0)
        ev = mem.add_temporal_event("lunch", 12.0, 13.0)
        assert ev.label == "lunch"
        assert ev.interval.start == 12.0
        assert ev.interval.end == 13.0
        assert mem.has("lunch")

    def test_temporal_query_overlapping(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("meeting", 10.0, 12.0)
        mem.add_temporal_event("lunch", 11.0, 13.0)
        mem.add_temporal_event("dinner", 18.0, 19.0)
        results = mem.temporal_query("meeting", relation="overlapping")
        labels = {r.label for r in results}
        assert labels == {"lunch"}

    def test_temporal_query_before(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("breakfast", 7.0, 8.0)
        mem.add_temporal_event("lunch", 12.0, 13.0)
        mem.add_temporal_event("dinner", 18.0, 19.0)
        results = mem.temporal_query("lunch", relation="before")
        labels = {r.label for r in results}
        assert labels == {"breakfast"}

    def test_temporal_query_after(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("breakfast", 7.0, 8.0)
        mem.add_temporal_event("lunch", 12.0, 13.0)
        mem.add_temporal_event("dinner", 18.0, 19.0)
        results = mem.temporal_query("lunch", relation="after")
        labels = {r.label for r in results}
        assert labels == {"dinner"}

    def test_temporal_query_proximity(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("breakfast", 7.0, 8.0)
        mem.add_temporal_event("lunch", 12.0, 13.0)
        results = mem.temporal_query("breakfast", relation="proximity", max_gap=5.0)
        labels = {r.label for r in results}
        assert labels == {"lunch"}

    def test_temporal_query_nonexistent(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.temporal_query("ghost") == []

    def test_causal_chain(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("dinner", 18.0, 19.0)
        mem.add_temporal_event("breakfast", 7.0, 8.0)
        mem.add_temporal_event("lunch", 12.0, 13.0)
        order = mem.causal_chain(["dinner", "breakfast", "lunch"])
        assert order == ["breakfast", "lunch", "dinner"]

    def test_temporal_property(self):
        mem = HypergraphMemory(evolve_interval=0)
        tr = mem.temporal_engine

        assert isinstance(tr, TemporalReasoner)
        assert mem.temporal_engine is tr

    def test_load_reinitializes_temporal(self):
        import os
        import tempfile
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("event", 1.0, 2.0)
        assert len(mem.temporal_engine.events) == 1
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.save(path)
            mem.load(path)
            assert len(mem.temporal_engine.events) == 0
            assert mem.temporal_engine.get_event("event") is None
        finally:
            os.unlink(path)

    def test_temporal_event_logged(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("work", 9.0, 17.0)
        temporal_entries = mem.log.query("temporal_event")
        assert len(temporal_entries) == 1
        assert temporal_entries[0]["details"]["label"] == "work"
        assert temporal_entries[0]["details"]["start"] == 9.0
        assert temporal_entries[0]["details"]["end"] == 17.0

    def test_temporal_query_containing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("day", 0.0, 24.0)
        mem.add_temporal_event("meeting", 10.0, 11.0)
        results = mem.temporal_query("meeting", relation="containing")
        labels = {r.label for r in results}
        assert labels == {"day"}

    def test_detect_causal_chains_max_chains(self):
        tr = TemporalReasoner(Hypergraph())
        for i in range(20):
            tr.add_event(f"e{i}", f"event_{i}", i * 10.0, i * 10.0 + 5.0)
        chains = tr.detect_causal_chains(min_chain_length=3, max_chains=5)
        assert len(chains) == 5


class TestTemporalConsistency:
    def test_temporal_consistency_check(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="e")
        mem.add_temporal_event("a", 0.0, 5.0)
        mem.add_temporal_event("b", 3.0, 8.0)
        edge = mem.graph.edges[0]
        result = mem.temporal_engine.edge_temporal_consistency(
            edge.id,
            edge.id,
            mem.graph,
        )
        assert result["consistent"] is True
        assert result["relation"] == "equals"


class TestAdditionalCoverage:
    def test_relate_to_nan_rejected(self):
        with pytest.raises(ValueError, match="must be finite"):
            TimeInterval(1.0, float('nan'))

    def test_edge_temporal_consistency_both_edges_missing(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        result = tr.edge_temporal_consistency("missing_a", "missing_b", g)
        assert result == {"consistent": True, "reason": "edge_not_found"}

    def test_edge_temporal_consistency_one_edge_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="e1")
        edge_a_id = mem.graph.edges[0].id
        result = mem.temporal_engine.edge_temporal_consistency(edge_a_id, "missing", mem.graph)
        assert result == {"consistent": True, "reason": "edge_not_found"}

    def test_edge_temporal_consistency_no_temporal_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="e1")
        mem.link("b", "a", label="e2")
        edge_a_id = mem.graph.edges[0].id
        edge_b_id = mem.graph.edges[1].id
        result = mem.temporal_engine.edge_temporal_consistency(edge_a_id, edge_b_id, mem.graph)
        assert result == {"consistent": True, "reason": "no_temporal_data"}

    def test_check_constraint_consistency_single_event(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        tr.add_event("e1", "A", 0.0, 2.0)
        assert tr.check_constraint_consistency() == []

    def test_check_constraint_consistency_no_constraints(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        tr.add_event("e1", "A", 0.0, 2.0)
        tr.add_event("e2", "B", 3.0, 5.0)
        assert tr.check_constraint_consistency() == []

    def test_check_constraint_consistency_matching(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        tr.add_event("e1", "A", 0.0, 2.0)
        tr.add_event("e2", "B", 3.0, 5.0)
        tr.add_constraint("e1", "e2", AllenRelation.BEFORE)
        assert tr.check_constraint_consistency() == []

    def test_check_constraint_consistency_mismatch(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        tr.add_event("e1", "A", 0.0, 2.0)
        tr.add_event("e2", "B", 3.0, 5.0)
        tr.add_constraint("e1", "e2", AllenRelation.AFTER)
        result = tr.check_constraint_consistency()
        assert len(result) == 1
        assert result[0]["event_a"] == "A"
        assert result[0]["event_b"] == "B"
        assert result[0]["actual_relation"] == "before"
        assert result[0]["expected_relation"] == "after"

    def test_check_constraint_consistency_non_matching_target(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        tr.add_event("e1", "A", 0.0, 2.0)
        tr.add_event("e2", "B", 3.0, 5.0)
        tr.add_event("e3", "C", 6.0, 8.0)
        tr.add_constraint("e1", "e3", AllenRelation.BEFORE)
        assert tr.check_constraint_consistency() == []

    def test_check_constraint_consistency_none_interval(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        tr.add_event("e1", "A", 0.0, 2.0)
        e2 = tr.add_event("e2", "B", 3.0, 5.0)
        e2.interval = None
        tr.add_constraint("e1", "e2", AllenRelation.BEFORE)
        assert tr.check_constraint_consistency() == []

    def test_get_event_for_node_found(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("my_event")
        node = mem.graph.get_node_by_label("my_event")
        mem.temporal_engine.add_event("ev1", "my_event", 0.0, 5.0)
        result = mem.temporal_engine.get_event_for_node(node.id, mem.graph)
        assert result is not None
        assert result.event_id == "ev1"
        assert result.label == "my_event"

    def test_get_event_for_node_no_matching_event(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("something")
        node = mem.graph.get_node_by_label("something")
        mem.temporal_engine.add_event("ev1", "other", 0.0, 5.0)
        result = mem.temporal_engine.get_event_for_node(node.id, mem.graph)
        assert result is None

    def test_get_event_for_node_missing_node(self):
        g = Hypergraph()
        tr = TemporalReasoner(g)
        result = tr.get_event_for_node("nonexistent", g)
        assert result is None

