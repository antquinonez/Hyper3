from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.rules import RuleMatch
from hyper3.rules_causal_sequence import CausalSequenceRule
from hyper3.temporal import AllenRelation, TemporalReasoner


def _make_setup() -> tuple[Hypergraph, TemporalReasoner, CausalSequenceRule]:
    g = Hypergraph()
    t = TemporalReasoner(g)
    rule = CausalSequenceRule(t)
    return g, t, rule


def _add_event(
    g: Hypergraph, t: TemporalReasoner, label: str, start: float, end: float
) -> str:
    n = Hypernode(label=label, data={"start": start, "end": end})
    g.add_node(n)
    t.add_event(label, label, start, end)
    return n.id


class TestConstruction:
    def test_name_default(self):
        _, _, rule = _make_setup()
        assert rule.name == "causal_sequence(temporal_cause)"

    def test_name_custom_label(self):
        _, t, _ = _make_setup()
        rule = CausalSequenceRule(t, edge_label="causes")
        assert rule.name == "causal_sequence(causes)"

    def test_custom_relations(self):
        _, t, _ = _make_setup()
        rule = CausalSequenceRule(t, relations={AllenRelation.OVERLAPS})
        assert rule._relations == {AllenRelation.OVERLAPS}

    def test_default_relations_are_before_and_meets(self):
        _, t, _ = _make_setup()
        rule = CausalSequenceRule(t)
        assert rule._relations == {AllenRelation.BEFORE, AllenRelation.MEETS}


class TestFindMatches:
    def test_no_events(self):
        g, _, rule = _make_setup()
        n = Hypernode(label="a")
        g.add_node(n)
        assert rule.find_matches(g, frozenset({n.id})) == []

    def test_no_active_nodes(self):
        g, _, rule = _make_setup()
        assert rule.find_matches(g, frozenset()) == []

    def test_single_event_no_pairs(self):
        g, t, rule = _make_setup()
        _add_event(g, t, "a", 0.0, 1.0)
        n = g.get_node_by_label("a")
        assert n is not None
        assert rule.find_matches(g, frozenset({n.id})) == []

    def test_before_pair_produces_one_match(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        assert matches[0].bindings["cause"] == a_id
        assert matches[0].bindings["effect"] == b_id
        assert matches[0].context["relation"] == "before"
        assert matches[0].context["gap"] == pytest.approx(1.0)

    def test_meets_pair_confidence_is_one(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 2.0)
        b_id = _add_event(g, t, "b", 2.0, 4.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        assert matches[0].context["relation"] == "meets"
        assert matches[0].context["gap"] == 0.0
        assert matches[0].context["confidence"] == 1.0

    def test_after_pair_only_reverse_matched(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 2.0, 3.0)
        b_id = _add_event(g, t, "b", 0.0, 1.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        assert matches[0].bindings["cause"] == b_id
        assert matches[0].bindings["effect"] == a_id

    def test_overlapping_pair_ignored(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 3.0)
        b_id = _add_event(g, t, "b", 1.0, 4.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 0

    def test_gap_exceeds_max_gap(self):
        g, t, rule = _make_setup()
        rule = CausalSequenceRule(t, max_gap=0.5)
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 3.0, 4.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 0

    def test_gap_within_max_gap(self):
        g, t, rule = _make_setup()
        rule = CausalSequenceRule(t, max_gap=1.0)
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 1.5, 2.5)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1

    def test_existing_edge_skipped(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        g.add_edge(Hyperedge(
            source_ids=frozenset({a_id}),
            target_ids=frozenset({b_id}),
            label="temporal_cause",
        ))
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 0

    def test_min_confidence_filter(self):
        g, t, rule = _make_setup()
        rule = CausalSequenceRule(t, min_confidence=0.9)
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 5.0, 6.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 0

    def test_three_chained_events(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        c_id = _add_event(g, t, "c", 4.0, 5.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id, c_id}))
        assert len(matches) == 3
        causes = {m.bindings["cause"] for m in matches}
        effects = {m.bindings["effect"] for m in matches}
        assert a_id in causes
        assert c_id in effects
        for m in matches:
            assert m.context["relation"] in ("before", "meets")

    def test_node_without_event_ignored(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        n_no_event = Hypernode(label="no_event")
        g.add_node(n_no_event)
        matches = rule.find_matches(g, frozenset({a_id, n_no_event.id}))
        assert len(matches) == 0

    def test_bidirectional_exclusion(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        assert matches[0].bindings["cause"] == a_id
        assert matches[0].bindings["effect"] == b_id
        reverse_match = [m for m in matches if m.bindings["cause"] == b_id]
        assert len(reverse_match) == 0


class TestConfidence:
    def test_before_gap_zero_point_five(self):
        _, _, rule = _make_setup()
        conf = rule._compute_confidence(AllenRelation.BEFORE, 0.5)
        assert conf == pytest.approx(1.0 / 1.5)

    def test_before_gap_one(self):
        _, _, rule = _make_setup()
        conf = rule._compute_confidence(AllenRelation.BEFORE, 1.0)
        assert conf == pytest.approx(0.5)

    def test_before_gap_five(self):
        _, _, rule = _make_setup()
        conf = rule._compute_confidence(AllenRelation.BEFORE, 5.0)
        assert conf == pytest.approx(1.0 / 6.0)

    def test_before_gap_zero(self):
        _, _, rule = _make_setup()
        conf = rule._compute_confidence(AllenRelation.BEFORE, 0.0)
        assert conf == 1.0

    def test_meets_always_one(self):
        _, _, rule = _make_setup()
        assert rule._compute_confidence(AllenRelation.MEETS, 0.0) == 1.0

    def test_confidence_monotonically_decreases_with_gap(self):
        _, _, rule = _make_setup()
        prev = 1.0
        for gap in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            conf = rule._compute_confidence(AllenRelation.BEFORE, gap)
            assert conf < prev
            prev = conf


class TestApply:
    def test_apply_creates_edge(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        new_nodes, new_edges = rule.apply(g, matches[0])
        assert new_nodes == []
        assert len(new_edges) == 1
        edge = g.get_edge(new_edges[0])
        assert edge is not None
        assert edge.label == "temporal_cause"
        assert source_in(edge, a_id)
        assert target_in(edge, b_id)

    def test_apply_metadata(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        _, new_edges = rule.apply(g, matches[0])
        edge = g.get_edge(new_edges[0])
        assert edge.metadata.custom["rule"] == "causal_sequence(temporal_cause)"
        assert edge.metadata.custom["inferred"] is True
        assert edge.metadata.custom["allen_relation"] == "before"
        assert edge.metadata.custom["temporal_gap"] == pytest.approx(1.0)
        assert 0.0 < edge.metadata.custom["confidence"] < 1.0

    def test_apply_custom_label(self):
        g, t, _ = _make_setup()
        rule = CausalSequenceRule(t, edge_label="causes")
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        _, new_edges = rule.apply(g, matches[0])
        edge = g.get_edge(new_edges[0])
        assert edge.label == "causes"

    def test_apply_deduplication_prevents_rematch(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        rule.apply(g, matches[0])
        second_matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(second_matches) == 0


class TestScoreMatch:
    def test_score_returns_confidence(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        score = rule.score_match(matches[0], g)
        assert score == matches[0].context["confidence"]


class TestSerialization:
    def test_to_dict_roundtrip(self):
        _, t, rule = _make_setup()
        d = rule.to_dict()
        assert d["rule_type"] == "CausalSequenceRule"
        assert d["edge_label"] == "temporal_cause"
        assert d["max_gap"] is None
        assert d["min_confidence"] == 0.0
        assert set(d["relations"]) == {"before", "meets"}

    def test_from_dict_raises(self):
        with pytest.raises(NotImplementedError, match="TemporalReasoner"):
            CausalSequenceRule._from_dict({"rule_type": "CausalSequenceRule"})


class TestEdgeCases:
    def test_point_events_at_different_times(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 1.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 2.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        assert matches[0].context["relation"] == "before"

    def test_equal_intervals_produce_no_match(self):
        g, t, rule = _make_setup()
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 0.0, 1.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 0

    def test_large_event_set(self):
        g, t, rule = _make_setup()
        ids = [_add_event(g, t, f"e{i}", float(i), float(i) + 0.5) for i in range(20)]
        active = frozenset(ids)
        matches = rule.find_matches(g, active)
        assert len(matches) == 190
        for m in matches:
            assert m.context["relation"] == "before"

    def test_overlaps_relation_when_configured(self):
        g, t, _ = _make_setup()
        rule = CausalSequenceRule(t, relations={AllenRelation.OVERLAPS})
        a_id = _add_event(g, t, "a", 0.0, 3.0)
        b_id = _add_event(g, t, "b", 1.0, 4.0)
        matches = rule.find_matches(g, frozenset({a_id, b_id}))
        assert len(matches) == 1
        assert matches[0].context["relation"] == "overlaps"


class TestIntegration:
    def test_transitive_extension(self):
        g, t, _ = _make_setup()
        rule = CausalSequenceRule(t, max_gap=2.0)
        a_id = _add_event(g, t, "a", 0.0, 1.0)
        b_id = _add_event(g, t, "b", 2.0, 3.0)
        c_id = _add_event(g, t, "c", 4.0, 5.0)
        from hyper3.rules import TransitiveRule
        tr = TransitiveRule(edge_label="temporal_cause", new_label="temporal_cause")
        active = frozenset({a_id, b_id, c_id})
        causal_matches = rule.find_matches(g, active)
        for m in causal_matches:
            rule.apply(g, m)
        trans_matches = tr.find_matches(g, active)
        assert len(trans_matches) == 1
        assert trans_matches[0].bindings["A"] == a_id
        assert trans_matches[0].bindings["C"] == c_id


def source_in(edge: Hyperedge, node_id: str) -> bool:
    return node_id in edge.source_ids


def target_in(edge: Hyperedge, node_id: str) -> bool:
    return node_id in edge.target_ids
