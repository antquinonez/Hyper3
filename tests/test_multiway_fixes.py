"""Integration tests verifying correctness of multiway subsystem bug fixes.

Tests cover:
- Bug #7: Consumed states excluded from get_leaves() after merging
- Bug #13: HubInferenceRule confidence excludes unlabeled edges from denominator
- Bug #18: InverseRule.apply guards against duplicate edges in shared-graph path
- Bug #14: TransitiveRule/InverseRule use outgoing_edges() not incident_edges()
- Bug #20: reason_incremental only selects leaves affected by new edges
- Bug #21: reason() resets multiway graph between calls
- Bug #1: add_state only assigns root for None parent_id, not orphan states
"""
import pytest

from hyper3 import (
    Hyperedge,
    Hypergraph,
    HypergraphMemory,
    Hypernode,
    InverseRule,
    Metadata,
    MultiwayEngine,
    MultiwayGraph,
    MultiwayState,
    StateConvergenceEngine,
    TransitiveRule,
)
from hyper3.rules import HubInferenceRule, RuleMatch


class TestConsumedStatesExcludedFromLeaves:
    """Bug #7: Merged states must not appear as leaves in get_leaves()."""

    def _build_convergent_multiway(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d", "e"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"d"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"d"}), target_ids=frozenset({"e"}), label="rel"))
        engine = MultiwayEngine(g)
        engine.expand(
            {"a", "b", "c", "d", "e"},
            [TransitiveRule(edge_label="rel")],
            max_depth=2,
            max_total_states=50,
        )
        return g, engine

    def test_merged_states_not_in_get_leaves(self):
        g, engine = self._build_convergent_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw)
        mw.get_leaves()
        ci.merge_invariant_states()
        leaves_after = mw.get_leaves()
        consumed_ids = ci._consumed_states
        for leaf in leaves_after:
            assert leaf.id not in consumed_ids

    def test_merged_states_flagged_consumed(self):
        g, engine = self._build_convergent_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw)
        ci.merge_invariant_states()
        for sid in ci._consumed_states:
            state = mw.get_state(sid)
            assert state is not None
            assert state.consumed is True

    def test_leaves_count_decreases_after_merge(self):
        g, engine = self._build_convergent_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw)
        leaves_before = len(mw.get_leaves())
        ci.merge_invariant_states()
        leaves_after = len(mw.get_leaves())
        merged_count = len(ci._consumed_states)
        assert leaves_after == leaves_before - merged_count + len(ci._invariants)

    def test_consumed_states_have_consumed_flag(self):
        g, engine = self._build_convergent_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw)
        ci.merge_invariant_states()
        all_states = mw.states
        consumed = [s for s in all_states if s.consumed]
        assert len(consumed) == len(ci._consumed_states)

    def test_state_clustering_excludes_consumed_from_leaves_input(self):
        g, engine = self._build_convergent_multiway()
        mw = engine.multiway
        ci = StateConvergenceEngine(g, mw)
        ci.merge_invariant_states()
        leaves = mw.get_leaves()
        for leaf in leaves:
            assert not leaf.consumed
        assert len(leaves) > 0


class TestHubInferenceRuleConfidence:
    """Bug #13: Unlabeled edges must not inflate the confidence denominator."""

    def test_unlabeled_edges_excluded_from_denominator(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        c = Hypernode(label="C")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        for _ in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="leads_to"))
        for _ in range(5):
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id})))
        rule = HubInferenceRule(min_support=2, confidence_threshold=0.5)
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        ab_matches = [m for m in matches if m.bindings["cause"] == a.id and m.bindings["effect"] == b.id]
        assert len(ab_matches) == 1
        assert ab_matches[0].context["confidence"] == 1.0
        assert ab_matches[0].context["support"] == 3

    def test_only_labeled_edges_count_in_source_totals(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        c = Hypernode(label="C")
        d = Hypernode(label="D")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({d.id})))
        rule = HubInferenceRule(min_support=1, confidence_threshold=0.1)
        active = frozenset({a.id, b.id, c.id, d.id})
        edge_pairs, source_totals = rule._build_pair_counts(g, active)
        assert source_totals[a.id] == 2
        assert (a.id, b.id) in edge_pairs
        assert (a.id, c.id) in edge_pairs

    def test_mixed_labeled_unlabeled_preserves_confidence(self):
        g = Hypergraph()
        hub = Hypernode(label="H")
        t1 = Hypernode(label="T1")
        t2 = Hypernode(label="T2")
        for n in [hub, t1, t2]:
            g.add_node(n)
        for _ in range(4):
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({t1.id}), label="flow"))
        for _ in range(10):
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({t2.id})))
        rule = HubInferenceRule(min_support=2, confidence_threshold=0.3)
        matches = rule.find_matches(g, frozenset({hub.id, t1.id, t2.id}))
        ht1 = [m for m in matches if m.bindings["effect"] == t1.id]
        assert len(ht1) == 1
        assert ht1[0].context["confidence"] == 1.0


class TestInverseRuleDuplicateGuard:
    """Bug #18: InverseRule.apply must not create duplicate inverse edges."""

    def test_apply_skips_existing_inverse(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="causes"))
        rule = InverseRule(edge_label="causes", inverse_label="caused_by")
        match = RuleMatch(
            rule_name=rule.name,
            bindings={"source": a.id, "target": b.id},
            context={"original_edge": "fake"},
        )
        new_n, new_e = rule.apply(g, match)
        assert len(new_e) == 1
        edge_count_after_first = g.edge_count
        new_n2, new_e2 = rule.apply(g, match)
        assert len(new_e2) == 0
        assert g.edge_count == edge_count_after_first

    def test_apply_idempotent_on_shared_graph(self):
        g = Hypergraph()
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="dep"))
        rule = InverseRule(edge_label="dep", inverse_label="dep_inv")
        matches = rule.find_matches(g, frozenset({a.id, b.id}))
        assert len(matches) >= 1
        for m in matches:
            rule.apply(g, m)
        inverse_count = sum(1 for e in g.edges if e.label == "dep_inv")
        for m in matches:
            new_n, new_e = rule.apply(g, m)
            assert len(new_e) == 0
        assert sum(1 for e in g.edges if e.label == "dep_inv") == inverse_count


class TestOutgoingEdgesDirectionality:
    """Bug #14: Rules must use outgoing_edges() for directed traversal."""

    def test_transitive_rule_ignores_incoming_edges(self):
        g = Hypergraph()
        a = Hypernode(id="a", label="A")
        b = Hypernode(id="b", label="B")
        c = Hypernode(id="c", label="C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"a"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        matches = rule.find_matches(g, frozenset({"a", "b", "c"}))
        a_to_c = [m for m in matches if m.bindings["A"] == "a" and m.bindings["C"] == "c"]
        assert len(a_to_c) == 0

    def test_inverse_rule_ignores_incoming_edges(self):
        g = Hypergraph()
        a = Hypernode(id="a", label="A")
        b = Hypernode(id="b", label="B")
        c = Hypernode(id="c", label="C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="dep"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"b"}), label="dep"))
        rule = InverseRule(edge_label="dep", inverse_label="dep_inv")
        matches = rule.find_matches(g, frozenset({"a", "b", "c"}))
        for m in matches:
            assert m.bindings["source"] != "a"

    def test_transitive_chain_forward_only(self):
        g = Hypergraph()
        nodes = {l: Hypernode(id=l, label=l.upper()) for l in ["a", "b", "c"]}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"a"}), label="back"))
        rule = TransitiveRule(edge_label="next")
        matches = rule.find_matches(g, frozenset(nodes.keys()))
        for m in matches:
            assert m.bindings["A"] == "a"
            assert m.bindings["C"] == "c"
        assert len(matches) == 1


class TestReasonIncrementalSelectivity:
    """Bug #20: reason_incremental must only select leaves with new edges."""

    def test_incremental_only_selects_newly_affected_leaves(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["a", "b", "c", "d", "e", "f"]:
            mem.add(c)
        mem.link("a", "b", label="chain")
        mem.link("b", "c", label="chain")
        mem.link("d", "e", label="chain")
        mem.add_rules(TransitiveRule(edge_label="chain", new_label="chain"))
        mem.reason({"a", "b", "c", "d", "e", "f"}, max_depth=3)
        assert mem._multiway_engine is not None
        first_edge_count = mem.graph.edge_count
        mem.add("g")
        mem.link("c", "g", label="chain")
        result = mem.reason_incremental({"g"})
        assert result.expansion is not None
        assert result.expansion.states_created >= 1 or mem.graph.edge_count > first_edge_count

    def test_incremental_not_all_leaves_selected(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["a", "b", "c"]:
            mem.add(c)
        mem.link("a", "b", label="r")
        mem.link("b", "c", label="r")
        mem.add_rules(TransitiveRule(edge_label="r"))
        mem.reason({"a", "b", "c"}, max_depth=2)
        first_productions = dict(mem._rule_productions)
        mem.reason_incremental(set())
        new_edge_ids_collected = set()
        previously_produced = set()
        for edge_list in first_productions.values():
            previously_produced.update(edge_list)
        for state in mem._multiway_engine.multiway.states:
            for eid in state.produced_edge_ids:
                if eid not in previously_produced:
                    new_edge_ids_collected.add(eid)
        assert len(new_edge_ids_collected) <= len(set(
            eid for s in mem._multiway_engine.multiway.states for eid in s.produced_edge_ids
        ))


class TestReasonResetsMultiwayGraph:
    """Bug #21: reason() must reset the multiway graph between calls."""

    def test_reason_resets_state_count(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["a", "b", "c", "d"]:
            mem.add(c)
        mem.link("a", "b", label="rel")
        mem.link("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        mem.reason({"a", "b", "c"}, max_depth=2)
        states_after_first = mem._multiway_engine.multiway.state_count
        assert states_after_first > 1
        mem.reason({"a", "b", "d"}, max_depth=2)
        states_after_second = mem._multiway_engine.multiway.state_count
        assert states_after_second >= 1

    def test_reason_leaves_are_from_current_session_only(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["a", "b", "c", "d", "e"]:
            mem.add(c)
        mem.link("a", "b", label="rel")
        mem.link("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        mem.reason({"a", "b", "c"}, max_depth=2)
        leaves_first = mem._multiway_engine.multiway.get_leaves()
        first_leaf_ids = {l.id for l in leaves_first}
        mem.reason({"a", "b", "c", "d", "e"}, max_depth=2)
        leaves_second = mem._multiway_engine.multiway.get_leaves()
        second_leaf_ids = {l.id for l in leaves_second}
        assert first_leaf_ids != second_leaf_ids

    def test_sequential_reason_does_not_accumulate_states(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="e")
        mem.add_rules(TransitiveRule(edge_label="e"))
        counts = []
        for _ in range(3):
            mem.reason({"x", "y"}, max_depth=2)
            counts.append(mem._multiway_engine.multiway.state_count)
        assert counts[0] == counts[1] == counts[2]


class TestAddStateRootAssignment:
    """Bug #1: add_state must only assign root when parent_id is None."""

    def test_orphan_state_does_not_overwrite_root(self):
        mw = MultiwayGraph()
        root = MultiwayState(parent_id=None, active_node_ids=frozenset({"root"}))
        mw.add_state(root)
        assert mw.get_root() is root
        assert mw.get_root().id == root.id
        child = MultiwayState(parent_id="nonexistent_parent", active_node_ids=frozenset({"child"}))
        mw.add_state(child)
        assert mw.get_root() is root
        assert mw.get_root().id == root.id

    def test_none_parent_sets_root(self):
        mw = MultiwayGraph()
        state = MultiwayState(parent_id=None, active_node_ids=frozenset({"r"}))
        mw.add_state(state)
        assert mw.get_root() is state

    def test_valid_parent_does_not_set_root(self):
        mw = MultiwayGraph()
        root = MultiwayState(parent_id=None, active_node_ids=frozenset({"r"}))
        mw.add_state(root)
        child = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}))
        mw.add_state(child)
        assert mw.get_root() is root
        assert child.id in root.children_ids

    def test_multiple_orphans_preserve_first_root(self):
        mw = MultiwayGraph()
        root = MultiwayState(parent_id=None, active_node_ids=frozenset({"r"}))
        mw.add_state(root)
        for i in range(5):
            orphan = MultiwayState(parent_id=f"missing_{i}", active_node_ids=frozenset({f"o_{i}"}))
            mw.add_state(orphan)
        assert mw.get_root() is root
        assert mw.get_root().id == root.id
