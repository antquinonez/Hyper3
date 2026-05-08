from __future__ import annotations

import pytest

from hyper3.belief import BeliefState, ConceptCorrelation, Outcome
from hyper3.entanglement import (
    CorrelatedCollapseResult,
    EntanglementEngine,
    EntanglementGroup,
    EntanglementLink,
    EntanglementReport,
)


def _make_qs(outcome_ids: list[str], labels: list[str] | None = None) -> BeliefState:
    qs = BeliefState()
    for i, nid in enumerate(outcome_ids):
        lbl = labels[i] if labels and i < len(labels) else nid
        qs.add_outcome(nid, 1.0, label=lbl)
    qs.normalize()
    return qs


def _make_corr(
    group_a: list[str],
    group_b: list[str],
    matrix: dict[tuple[str, str], float],
) -> ConceptCorrelation:
    return ConceptCorrelation(
        group_a_node_ids=frozenset(group_a),
        group_b_node_ids=frozenset(group_b),
        correlation_matrix=matrix,
        strength=sum(abs(v) for v in matrix.values()) / max(len(matrix), 1),
    )


class TestRegisterLink:
    def test_creates_link(self):
        engine = EntanglementEngine()
        link = engine.register_link("a", "b", "corr1", 0.8)
        assert isinstance(link, EntanglementLink)
        assert link.distribution_a_id == "a"
        assert link.distribution_b_id == "b"
        assert link.strength == 0.8

    def test_creates_group(self):
        engine = EntanglementEngine()
        engine.register_link("a", "b", "corr1", 0.8)
        group = engine.find_group("a")
        assert group is not None
        assert "a" in group.distribution_ids
        assert "b" in group.distribution_ids

    def test_rejects_self_link(self):
        engine = EntanglementEngine()
        engine.register_link("a", "a", "corr1", 0.5)
        group = engine.find_group("a")
        assert group is None


class TestGroupDiscovery:
    def test_two_links_form_one_group(self):
        engine = EntanglementEngine()
        engine.register_link("a", "b", "c1", 0.8)
        engine.register_link("b", "c", "c2", 0.6)
        ga = engine.find_group("a")
        gc = engine.find_group("c")
        assert ga is not None
        assert gc is not None
        assert ga.id == gc.id
        assert ga.distribution_ids == frozenset({"a", "b", "c"})

    def test_separate_links_separate_groups(self):
        engine = EntanglementEngine()
        engine.register_link("a", "b", "c1", 0.8)
        engine.register_link("c", "d", "c2", 0.6)
        ga = engine.find_group("a")
        gc = engine.find_group("c")
        assert ga is not None
        assert gc is not None
        assert ga.id != gc.id

    def test_find_entangled(self):
        engine = EntanglementEngine()
        engine.register_link("a", "b", "c1", 0.8)
        engine.register_link("b", "c", "c2", 0.6)
        entangled = engine.find_entangled("a")
        assert entangled == {"b", "c"}

    def test_find_entangled_none(self):
        engine = EntanglementEngine()
        assert engine.find_entangled("a") == set()


class TestCorrelatedWeights:
    def test_positive_correlation(self):
        engine = EntanglementEngine()
        link = engine.register_link("qs_a", "qs_b", "corr1", 0.8)
        qs_b = _make_qs(["x", "y"])
        corr = _make_corr(["trigger"], ["x", "y"], {("trigger", "x"): 0.8, ("trigger", "y"): -0.6})
        weights = engine.compute_correlated_weights(qs_b, "trigger", {"corr1": corr}, link)
        assert weights["x"] > weights["y"]

    def test_negative_correlation(self):
        engine = EntanglementEngine()
        link = engine.register_link("qs_a", "qs_b", "corr1", 0.8)
        qs_b = _make_qs(["x", "y"])
        corr = _make_corr(["trigger"], ["x", "y"], {("trigger", "x"): -0.9, ("trigger", "y"): 0.8})
        weights = engine.compute_correlated_weights(qs_b, "trigger", {"corr1": corr}, link)
        assert weights["y"] > weights["x"]

    def test_zero_correlation_uniform(self):
        engine = EntanglementEngine()
        link = engine.register_link("qs_a", "qs_b", "corr1", 0.0)
        qs_b = _make_qs(["x", "y"])
        corr = _make_corr(["trigger"], ["x", "y"], {})
        weights = engine.compute_correlated_weights(qs_b, "trigger", {"corr1": corr}, link)
        assert weights["x"] == weights["y"]

    def test_missing_correlation_returns_empty(self):
        engine = EntanglementEngine()
        link = engine.register_link("qs_a", "qs_b", "nonexistent", 0.5)
        qs_b = _make_qs(["x", "y"])
        weights = engine.compute_correlated_weights(qs_b, "trigger", {}, link)
        assert weights == {}


class TestCorrelatedCollapse:
    def test_no_group_returns_none(self):
        engine = EntanglementEngine()
        qs = _make_qs(["a"])
        result = engine.perform_correlated_collapse(
            "nonexistent", {"q1": qs}, {}, lambda qid, w: None
        )
        assert result is None

    def test_two_distribution_collapse(self):
        engine = EntanglementEngine()
        engine.register_link("qs_a", "qs_b", "corr1", 0.8)
        qs_a = _make_qs(["a1", "a2"], ["label_a1", "label_a2"])
        qs_b = _make_qs(["b1", "b2"], ["label_b1", "label_b2"])
        corr = _make_corr(
            ["a1", "a2"], ["b1", "b2"],
            {("a1", "b1"): 0.9, ("a1", "b2"): -0.5, ("a2", "b2"): 0.9, ("a2", "b1"): -0.5},
        )
        states = {"qs_a": qs_a, "qs_b": qs_b}

        def sample_fn(qs_id: str, weights: dict[str, float] | None) -> Outcome | None:
            qs = states[qs_id]
            if weights:
                best = max(qs.outcomes, key=lambda o: weights.get(o.node_id, 1.0))
                qs.resolved = True
                qs.resolved_to = best.node_id
                return best
            return qs.sample()

        result = engine.perform_correlated_collapse(
            "qs_a", states, {"corr1": corr}, sample_fn
        )
        assert result is not None
        assert isinstance(result, CorrelatedCollapseResult)
        assert "qs_a" in result.collapsed_distributions
        assert "qs_b" in result.collapsed_distributions
        assert len(result.collapse_order) == 2

    def test_cascade_three_distributions(self):
        engine = EntanglementEngine()
        engine.register_link("qs_a", "qs_b", "c1", 0.8)
        engine.register_link("qs_b", "qs_c", "c2", 0.6)
        qs_a = _make_qs(["a1"], ["la1"])
        qs_b = _make_qs(["b1"], ["lb1"])
        qs_c = _make_qs(["c1"], ["lc1"])
        corr1 = _make_corr(["a1"], ["b1"], {("a1", "b1"): 0.9})
        corr2 = _make_corr(["b1"], ["c1"], {("b1", "c1"): 0.7})
        states = {"qs_a": qs_a, "qs_b": qs_b, "qs_c": qs_c}

        def sample_fn(qs_id: str, weights: dict[str, float] | None) -> Outcome | None:
            return states[qs_id].sample(weights)

        result = engine.perform_correlated_collapse(
            "qs_a", states, {"c1": corr1, "c2": corr2}, sample_fn
        )
        assert result is not None
        assert len(result.collapsed_distributions) == 3
        assert result.collapse_order[0] == "qs_a"

    def test_trigger_sample_failure_returns_none(self):
        engine = EntanglementEngine()
        engine.register_link("qs_a", "qs_b", "corr1", 0.8)
        qs_a = BeliefState()
        states = {"qs_a": qs_a}

        result = engine.perform_correlated_collapse(
            "qs_a", states, {}, lambda qid, w: None
        )
        assert result is None

    def test_collapse_order_follows_strength(self):
        engine = EntanglementEngine()
        engine.register_link("qs_a", "qs_b", "c1", 0.9)
        engine.register_link("qs_a", "qs_c", "c2", 0.3)
        qs_a = _make_qs(["a1"], ["la1"])
        qs_b = _make_qs(["b1"], ["lb1"])
        qs_c = _make_qs(["c1"], ["lc1"])
        corr1 = _make_corr(["a1"], ["b1"], {("a1", "b1"): 0.9})
        corr2 = _make_corr(["a1"], ["c1"], {("a1", "c1"): 0.3})
        states = {"qs_a": qs_a, "qs_b": qs_b, "qs_c": qs_c}

        def sample_fn(qs_id: str, weights: dict[str, float] | None) -> Outcome | None:
            return states[qs_id].sample(weights)

        result = engine.perform_correlated_collapse(
            "qs_a", states, {"c1": corr1, "c2": corr2}, sample_fn
        )
        assert result is not None
        assert result.collapse_order[0] == "qs_a"
        assert result.collapse_order[1] == "qs_b"
        assert result.collapse_order[2] == "qs_c"

    def test_collapse_includes_all_group_members_on_sample_failure(self):
        engine = EntanglementEngine()
        engine.register_link("qs_a", "qs_b", "c1", 0.8)
        engine.register_link("qs_a", "qs_c", "c2", 0.5)
        qs_a = _make_qs(["a1"], ["la1"])
        qs_b = _make_qs(["b1"], ["lb1"])
        qs_c = _make_qs(["c1"], ["lc1"])
        corr1 = _make_corr(["a1"], ["b1"], {("a1", "b1"): 0.8})
        corr2 = _make_corr(["a1"], ["c1"], {("a1", "c1"): 0.5})
        states = {"qs_a": qs_a, "qs_b": qs_b, "qs_c": qs_c}
        call_count = 0

        def sample_fn(qs_id: str, weights: dict[str, float] | None) -> Outcome | None:
            nonlocal call_count
            call_count += 1
            if qs_id == "qs_c":
                return None
            return states[qs_id].sample(weights)

        result = engine.perform_correlated_collapse(
            "qs_a", states, {"c1": corr1, "c2": corr2}, sample_fn
        )
        assert result is not None
        assert "qs_a" in result.collapsed_distributions
        assert "qs_b" in result.collapsed_distributions
        assert "qs_c" in result.collapsed_distributions
        assert "qs_c" not in result.collapse_order


class TestRemoveLink:
    def test_remove_existing_link(self):
        engine = EntanglementEngine()
        link = engine.register_link("a", "b", "c1", 0.8)
        engine.remove_link(link.id)
        assert engine.report().total_links == 0

    def test_remove_nonexistent_link(self):
        engine = EntanglementEngine()
        engine.remove_link("nonexistent")

    def test_remove_link_updates_groups(self):
        engine = EntanglementEngine()
        link_ab = engine.register_link("a", "b", "c1", 0.8)
        engine.register_link("b", "c", "c2", 0.6)
        assert engine.find_entangled("a") == {"b", "c"}
        engine.remove_link(link_ab.id)
        assert engine.find_entangled("a") == set()
        assert engine.find_entangled("b") == {"c"}

    def test_remove_link_splits_group(self):
        engine = EntanglementEngine()
        link_ab = engine.register_link("a", "b", "c1", 0.8)
        link_bc = engine.register_link("b", "c", "c2", 0.6)
        assert engine.report().total_groups == 1
        engine.remove_link(link_ab.id)
        assert engine.report().total_groups == 1
        assert engine.find_entangled("a") == set()
        assert engine.find_entangled("b") == {"c"}
        engine.remove_link(link_bc.id)
        assert engine.report().total_groups == 0


class TestClear:
    def test_clear_removes_everything(self):
        engine = EntanglementEngine()
        engine.register_link("a", "b", "c1", 0.8)
        engine.register_link("b", "c", "c2", 0.6)
        engine.clear()
        report = engine.report()
        assert report.total_links == 0
        assert report.total_groups == 0
        assert report.total_collapses == 0


class TestReport:
    def test_report_empty(self):
        engine = EntanglementEngine()
        report = engine.report()
        assert isinstance(report, EntanglementReport)
        assert report.total_links == 0
        assert report.total_groups == 0

    def test_report_with_data(self):
        engine = EntanglementEngine()
        engine.register_link("a", "b", "c1", 0.8)
        report = engine.report()
        assert report.total_links == 1
        assert report.total_groups == 1
        assert len(report.active_links) == 1
        assert len(report.active_groups) == 1


class TestSerialization:
    def test_roundtrip(self):
        engine = EntanglementEngine()
        engine.register_link("a", "b", "c1", 0.8)
        engine.register_link("b", "c", "c2", 0.6)
        data = engine.to_dict()
        restored = EntanglementEngine.from_dict(data)
        assert restored.report().total_links == 2
        assert restored.find_group("a") is not None
        assert restored.find_group("c") is not None
        ga = restored.find_group("a")
        gc = restored.find_group("c")
        assert ga is not None and gc is not None
        assert ga.id == gc.id

    def test_roundtrip_preserves_collapse_count(self):
        engine = EntanglementEngine()
        engine._collapse_count = 5
        data = engine.to_dict()
        restored = EntanglementEngine.from_dict(data)
        assert restored.report().total_collapses == 5


class TestResultTypes:
    def test_link_is_simple_result_base(self):
        link = EntanglementLink(id="test", strength=0.5)
        assert "strength" in link
        assert link["strength"] == 0.5

    def test_group_is_simple_result_base(self):
        group = EntanglementGroup(id="g1", collapse_count=3)
        assert "collapse_count" in group

    def test_collapse_result_is_simple_result_base(self):
        result = CorrelatedCollapseResult(trigger_outcome_label="test")
        assert "trigger_outcome_label" in result

    def test_report_is_simple_result_base(self):
        report = EntanglementReport(total_links=5)
        assert "total_links" in report
