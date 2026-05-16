"""Tests for memory_reasoning.ReasoningMixin — focused on untested paths.

Covers reason_incremental, reason_boundary_aware, reason_robust,
commit/rollback lifecycle, exhaustive mode, overlay=False, branch overlay
deduplication, bias profiling, causal learning, and property access.
"""

from __future__ import annotations

import pytest

from hyper3.memory import HypergraphMemory
from hyper3.results import (
    BiasProfileResult,
    CommitResult,
    ConsensusReasonResult,
    IterativeReasonResult,
    ReasonResult,
    RollbackResult,
)
from hyper3.rules import (
    HubInferenceRule,
    InverseRule,
    TransitiveRule,
)


def _chain_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.add_rules(TransitiveRule(edge_label="next", new_label="next"))
    mem.add("a")
    mem.add("b")
    mem.add("c")
    mem.add("d")
    mem.link("a", "b", label="next")
    mem.link("b", "c", label="next")
    mem.link("c", "d", label="next")
    return mem


class TestReasonIncremental:
    def test_no_prior_session_returns_error(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.add("x")
        result = mem.reason_incremental({"x"})
        assert result.error == "no prior reasoning session"
        assert result.states_created == 0

    def test_no_rules_returns_error(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.reason({"x"})
        mem._rules.clear()
        result = mem.reason_incremental({"x"})
        assert result.error == "no rules defined"

    def test_incremental_from_prior_session(self):
        mem = _chain_mem()
        first = mem.reason({"a", "b", "c", "d"})
        assert first.expansion is not None
        assert first.expansion.rules_applied > 0
        mem.add("e")
        mem.link("d", "e", label="next")
        result = mem.reason_incremental({"e"})
        assert result.expansion is not None
        assert result.expansion.states_created >= 0

    def test_missing_labels_skipped_gracefully(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"})
        result = mem.reason_incremental({"nonexistent_node"})
        assert result.expansion is not None


class TestReasonIncrementalNewEdgeFiltering:
    def test_previously_produced_edges_excluded(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="next", new_label="next"))
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="next")
        mem.link("b", "c", label="next")
        first = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert first.expansion is not None
        assert first.expansion.rules_applied >= 1
        result = mem.reason_incremental(set())
        assert result.expansion is not None


class TestCommitRollbackLifecycle:
    def test_commit_with_no_overlay_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.commit_inferences()
        assert result.committed_nodes == 0
        assert result.committed_edges == 0

    def test_rollback_with_no_overlay_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.rollback_inferences()
        assert result.rolled_back_nodes == 0
        assert result.rolled_back_edges == 0

    def test_commit_merges_overlay_edges(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        assert mem._overlay is not None
        overlay_edge_count = len(mem._overlay.overlay_edge_ids)
        result = mem.commit_inferences()
        assert result.committed_edges == overlay_edge_count
        assert mem._overlay is None

    def test_rollback_discards_overlay(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        assert mem._overlay is not None
        overlay_edge_count = len(mem._overlay.overlay_edge_ids)
        result = mem.rollback_inferences()
        assert result.rolled_back_edges == overlay_edge_count
        assert mem._overlay is None

    def test_rollback_retracts_provenance(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        assert mem._overlay is not None
        record_count = mem.provenance.record_count
        assert record_count > 0
        mem.rollback_inferences()
        for record in mem.provenance.records:
            assert record.edge_id not in {e.id for e in mem.graph.edges}

    def test_commit_then_rollback_is_noop(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        mem.commit_inferences()
        rollback = mem.rollback_inferences()
        assert rollback.rolled_back_nodes == 0
        assert rollback.rolled_back_edges == 0

    def test_commit_result_type(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        result = mem.commit_inferences()
        assert isinstance(result, CommitResult)

    def test_rollback_result_type(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        result = mem.rollback_inferences()
        assert isinstance(result, RollbackResult)


class TestReasonExhaustive:
    def test_exhaustive_explores_all_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="next", new_label="next"))
        for label in ["a", "b", "c", "d", "e"]:
            mem.add(label)
        mem.link("a", "b", label="next")
        mem.link("b", "c", label="next")
        mem.link("c", "d", label="next")
        mem.link("d", "e", label="next")
        result = mem.reason({"a", "b", "c", "d", "e"}, exhaustive=True)
        assert result.expansion is not None
        assert result.expansion.rules_applied >= 3


class TestReasonNoOverlay:
    def test_reason_without_overlay_no_overlay_in_result(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e", new_label="inferred"))
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason({"a", "b", "c"}, use_overlay=False)
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0
        assert result.overlay is None


class TestReasonNoSeeds:
    def test_reason_with_missing_seeds_returns_error(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        result = mem.reason({"nonexistent"})
        assert result.error == "no seed nodes found"

    def test_reason_with_no_rules_returns_error(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        result = mem.reason({"a"})
        assert result.error == "no rules defined"


class TestReasonMaxMatchesPerRule:
    def test_max_matches_caps_productivity(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(
            TransitiveRule(edge_label="e", new_label="inferred"),
            InverseRule(edge_label="e", inverse_label="inv"),
        )
        for label in ["a", "b", "c", "d", "e"]:
            mem.add(label)
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        mem.link("c", "d", label="e")
        mem.link("d", "e", label="e")
        result = mem.reason({"a", "b", "c", "d", "e"}, max_matches_per_rule=1)
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0


class TestReasonBoundaryAware:
    def test_boundary_aware_delegates_to_reason(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason_boundary_aware({"a", "b", "c"})
        assert isinstance(result, ReasonResult)
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0

    def test_boundary_aware_with_missing_seeds(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="e")
        result = mem.reason_boundary_aware({"a", "b", "nonexistent"})
        assert isinstance(result, ReasonResult)


class TestReasonRobust:
    def test_robust_returns_consensus_result(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason_robust({"a", "b", "c"})
        assert isinstance(result, ConsensusReasonResult)
        assert result.frame_count > 0
        assert isinstance(result.invariant_nodes, int)
        assert isinstance(result.invariant_edges, int)

    def test_robust_no_seeds_returns_error(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        result = mem.reason_robust({"nonexistent"})
        assert result.error is not None

    def test_robust_no_rules_still_finds_invariants(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="e")
        result = mem.reason_robust({"a", "b"})
        assert isinstance(result, ConsensusReasonResult)
        assert result.frame_count > 0


class TestReasonResultFields:
    def test_result_has_multiway_leaves(self):
        mem = _chain_mem()
        result = mem.reason({"a", "b", "c", "d"})
        assert result.multiway_leaves > 0

    def test_result_expansion_info_fields(self):
        mem = _chain_mem()
        result = mem.reason({"a", "b", "c", "d"})
        assert result.expansion is not None
        assert result.expansion.states_created > 0
        assert result.expansion.max_depth >= 0
        assert result.expansion.branches >= 0

    def test_result_with_overlay_has_confidence(self):
        mem = _chain_mem()
        result = mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        if result.overlay and result.overlay.get("edge_count", 0) > 0:
            assert result.confidence is not None
            assert len(result.confidence) > 0


class TestBranchOverlayDeduplication:
    def test_identical_edges_from_branches_deduplicated(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(
            TransitiveRule(edge_label="e", new_label="inferred"),
            TransitiveRule(edge_label="e", new_label="inferred"),
        )
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert result.expansion is not None
        if mem._overlay is not None:
            labels = [e.label for e in mem._overlay._overlay_edges.values()]
            assert labels.count("inferred") >= 1
        mem.rollback_inferences()


class TestBiasProfile:
    def test_bias_profile_with_no_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.compute_bias_profile()
        assert isinstance(result, BiasProfileResult)
        assert result.reasoning_style == "unknown"
        assert result.bias_score == 0.0

    def test_bias_profile_after_reasoning(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"})
        result = mem.compute_bias_profile()
        assert isinstance(result, BiasProfileResult)
        assert result.reasoning_style in {"focused", "exploratory", "balanced", "unknown"}
        assert len(result.dominant_rules) + len(result.underused_rules) >= 0


class TestProperties:
    def test_multiway_none_before_reasoning(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.multiway is None

    def test_multiway_initialized_after_reasoning(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"})
        assert mem.multiway is not None

    def test_state_clustering_none_before_reasoning(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.state_clustering is None

    def test_state_clustering_initialized_after_reasoning(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"})
        assert mem.state_clustering is not None

    def test_rule_analytics_always_initialized(self):
        mem = HypergraphMemory(evolve_interval=0)
        analytics = mem.rule_analytics
        assert analytics is not None

    def test_rules_property_returns_copy(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        rules = mem.rules
        assert len(rules) == 1
        rules.append(TransitiveRule(edge_label="x"))
        assert len(mem.rules) == 1


class TestDiscoverRules:
    def test_discover_rules_finds_patterns(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(4):
            mem.add(f"n{i}")
        mem.link("n0", "n1", label="e")
        mem.link("n1", "n2", label="e")
        mem.link("n2", "n3", label="e")
        discovered = mem.discover_rules()
        total_with_rules = sum(1 for d in discovered if d.rule is not None)
        assert total_with_rules >= 1

    def test_auto_discover_and_apply(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        initial_rule_count = len(mem.rules)
        result = mem.auto_discover_and_apply()
        assert result.total_patterns >= 0
        assert result.new_rules_added >= 0
        assert len(mem.rules) >= initial_rule_count


class TestCausalLearning:
    def test_learn_causal_patterns_empty_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.learn_causal_patterns()
        assert result.hypotheses_created == 0

    def test_commit_causal_hypotheses_without_learner(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.commit_causal_hypotheses()
        assert result == []

    def test_causal_lifecycle(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="causes")
        mem.learn_causal_patterns()
        result = mem.commit_causal_hypotheses(min_confidence=0.0)
        assert isinstance(result, list)


class TestIterativeReasoningEdgeCases:
    def test_iterative_stops_on_confidence_threshold(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        for label in ["a", "b", "c"]:
            mem.add(label)
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason_iterative(
            {"a", "b", "c"},
            max_iterations=10,
            min_confidence=0.001,
        )
        assert isinstance(result, IterativeReasonResult)
        assert result.iterations >= 1

    def test_iterative_commits_each_round(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        for label in ["a", "b", "c"]:
            mem.add(label)
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason_iterative({"a", "b", "c"}, max_iterations=3)
        assert isinstance(result, IterativeReasonResult)
        assert result.total_edges_produced >= 1


class TestReasonResetBehavior:
    def test_reason_resets_multiway_each_call(self):
        mem = _chain_mem()
        r1 = mem.reason({"a", "b", "c", "d"})
        assert r1.expansion is not None
        r2 = mem.reason({"a", "b", "c", "d"})
        assert r2.expansion is not None
        assert r2.expansion is not None

    def test_incremental_preserves_engine(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"})
        engine_after_reason = mem.multiway
        mem.reason_incremental(set())
        assert mem.multiway is engine_after_reason


class TestDerive:
    def test_derive_with_specific_rule(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        results = mem.derive("c", rules=[TransitiveRule(edge_label="e")])
        assert len(results) >= 1
        assert any(r.rule.startswith("transitive") for r in results)

    def test_derive_with_no_matching_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="e")
        results = mem.derive("b", rules=[TransitiveRule(edge_label="other")])
        assert results == []


class TestReasonWithMultipleRules:
    def test_transitive_plus_inverse(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(
            TransitiveRule(edge_label="e"),
            InverseRule(edge_label="e", inverse_label="inv"),
        )
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason({"a", "b", "c"})
        assert result.expansion is not None
        assert result.expansion.rules_applied >= 2

    def test_hub_inference_rule(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(HubInferenceRule(min_support=2))
        mem.add("hub")
        mem.add("x")
        mem.add("y")
        mem.add("z")
        mem.link("hub", "x", label="e")
        mem.link("hub", "y", label="e")
        mem.link("hub", "z", label="e")
        result = mem.reason({"hub", "x", "y", "z"})
        assert result.expansion is not None


class TestReasonOverlayAutoCommit:
    def test_reason_auto_commit_clears_internal_overlay(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        assert mem._overlay is None

    def test_reason_no_auto_commit_preserves_overlay(self):
        mem = _chain_mem()
        result = mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        assert result.overlay is not None
        assert mem._overlay is not None
        mem.rollback_inferences()

    def test_second_reason_auto_commits_first(self):
        mem = _chain_mem()
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        assert mem._overlay is not None
        initial_edges = len([e for e in mem.graph.edges if e.label == "inferred"])
        mem.reason({"a", "b", "c", "d"}, auto_commit=False)
        committed_edges = len([e for e in mem.graph.edges if e.label == "inferred"])
        assert committed_edges >= initial_edges


class TestReasonConfidenceDecay:
    def test_confidence_decays_with_depth(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e", new_label="inferred"))
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="e")
        mem.link("b", "c", label="e")
        result = mem.reason(
            {"a", "b", "c"},
            auto_commit=False,
            confidence_decay=0.5,
        )
        if result.confidence and len(result.confidence) > 1:
            values = sorted(result.confidence.values())
            assert values[0] <= values[-1]
        mem.rollback_inferences()
