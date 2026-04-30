import numpy as np
import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, Modality
from hyper3.memory import HypergraphMemory
from hyper3.multiway import ExpansionReport, MultiwayEngine, MultiwayGraph, MultiwayState
from hyper3.multiway_causal import StateConvergenceEngine
from hyper3.rules import (
    AbductiveRule,
    ContextualSubstitutionRule,
    GeneralizationRule,
    HubInferenceRule,
    InverseRule,
    PropertyPropagationRule,
    Rule,
    RuleMatch,
    StructuralProjectionRule,
    TransitiveRule,
)


class TestTransitiveRule:
    def test_finds_transitive_chain(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        matches = rule.find_matches(g, frozenset({"a", "b", "c"}))
        assert len(matches) == 1
        assert matches[0].bindings == {"A": "a", "B": "b", "C": "c"}

    def test_applies_creates_edge(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        rule = TransitiveRule(edge_label="rel", new_label="inferred_rel")
        match = rule.find_matches(g, frozenset({"a", "b", "c"}))[0]
        nodes, edges = rule.apply(g, match)
        assert len(edges) == 1
        new_edge = g.get_edge(edges[0])
        assert new_edge.label == "inferred_rel"
        assert "a" in new_edge.source_ids
        assert "c" in new_edge.target_ids

    def test_no_match_wrong_label(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="foo"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="bar"))
        rule = TransitiveRule(edge_label="foo")
        matches = rule.find_matches(g, frozenset({"a", "b", "c"}))
        assert len(matches) == 0

    def test_no_match_existing_edge(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        matches = rule.find_matches(g, frozenset({"a", "b", "c"}))
        assert len(matches) == 0

    def test_wildcard_matches_any_label(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="y"))
        rule = TransitiveRule()
        matches = rule.find_matches(g, frozenset({"a", "b", "c"}))
        assert len(matches) == 1


class TestInverseRule:
    def test_finds_inverse_match(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes"))
        rule = InverseRule(edge_label="causes", inverse_label="caused_by")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 1
        assert matches[0].bindings == {"source": "a", "target": "b"}

    def test_applies_creates_inverse(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes"))
        rule = InverseRule(edge_label="causes", inverse_label="caused_by")
        match = rule.find_matches(g, frozenset({"a", "b"}))[0]
        _, edges = rule.apply(g, match)
        new_edge = g.get_edge(edges[0])
        assert new_edge.label == "caused_by"
        assert "b" in new_edge.source_ids
        assert "a" in new_edge.target_ids

    def test_no_duplicate_inverse(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="inv"))
        rule = InverseRule(edge_label="rel", inverse_label="inv")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 0


class TestGeneralizationRule:
    def test_finds_similar_nodes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="cat", data="feline"))
        g.add_node(Hypernode(id="b", label="dog", data="feline"))
        rule = GeneralizationRule()
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 1

    def test_creates_abstract_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="cat", data="feline"))
        g.add_node(Hypernode(id="b", label="dog", data="feline"))
        rule = GeneralizationRule()
        match = rule.find_matches(g, frozenset({"a", "b"}))[0]
        nodes, edges = rule.apply(g, match)
        assert len(nodes) == 1
        assert len(edges) == 1
        abstract = g.get_node(nodes[0])
        assert abstract is not None
        assert "abstract_" in abstract.label

    def test_no_match_different_data(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", data="cat"))
        g.add_node(Hypernode(id="b", data="dog"))
        rule = GeneralizationRule()
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 0

    def test_no_match_none_data(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        rule = GeneralizationRule()
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 0


class TestAbductiveRule:
    def test_finds_abductive_match(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="cause", label="rain"))
        g.add_node(Hypernode(id="effect", label="wet_ground"))
        g.add_edge(Hyperedge(source_ids=frozenset({"cause"}), target_ids=frozenset({"effect"}), label="leads_to"))
        rule = AbductiveRule(effect_label="leads_to")
        matches = rule.find_matches(g, frozenset({"cause", "effect"}))
        assert len(matches) == 1

    def test_creates_hypothesis(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="cause", label="rain"))
        g.add_node(Hypernode(id="effect", label="wet_ground"))
        g.add_edge(Hyperedge(source_ids=frozenset({"cause"}), target_ids=frozenset({"effect"}), label="leads_to"))
        rule = AbductiveRule(effect_label="leads_to")
        match = rule.find_matches(g, frozenset({"cause", "effect"}))[0]
        nodes, edges = rule.apply(g, match)
        assert len(nodes) == 1
        assert len(edges) == 1
        hypothesis = g.get_node(nodes[0])
        assert "hypothesis" in hypothesis.label

    def test_wildcard_matches_all_effects(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"b"}), label="y"))
        rule = AbductiveRule()
        matches = rule.find_matches(g, frozenset({"a", "b", "c"}))
        assert len(matches) == 2


class TestPropertyPropagationRule:
    def test_propagates_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", metadata=Metadata(custom={"domain": "physics"})))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="related"))
        rule = PropertyPropagationRule(property_key="domain")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 1

    def test_applies_sets_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", metadata=Metadata(custom={"domain": "physics"})))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        rule = PropertyPropagationRule(property_key="domain")
        match = rule.find_matches(g, frozenset({"a", "b"}))[0]
        rule.apply(g, match)
        target = g.get_node("b")
        assert target.metadata.custom["domain"] == "physics"

    def test_no_match_if_already_has_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", metadata=Metadata(custom={"domain": "physics"})))
        g.add_node(Hypernode(id="b", metadata=Metadata(custom={"domain": "chemistry"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        rule = PropertyPropagationRule(property_key="domain")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 0


class TestTransitiveRuleEdgeCases:
    def test_self_loop_prevention(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        for m in matches:
            assert m.bindings["A"] != m.bindings["C"]

    def test_edge_exists_helper(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        assert rule._edge_exists(g, "a", "b")
        assert not rule._edge_exists(g, "b", "a")


class TestInverseRuleEdgeCases:
    def test_no_match_when_inverse_exists(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="inv"))
        rule = InverseRule(edge_label="rel", inverse_label="inv")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 0

    def test_creates_inverse_when_not_exists(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        rule = InverseRule(edge_label="rel", inverse_label="inv")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 1


class TestGeneralizationRuleEdgeCases:
    def test_abstract_exists_prevents_duplicate(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="cat", data="feline"))
        g.add_node(Hypernode(id="b", label="dog", data="feline"))
        rule = GeneralizationRule()
        match = rule.find_matches(g, frozenset({"a", "b"}))[0]
        rule.apply(g, match)
        matches2 = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches2) == 0

    def test_apply_returns_empty_for_missing_nodes(self):
        g = Hypergraph()
        rule = GeneralizationRule()
        match = RuleMatch(rule_name="generalization", bindings={"A": "nonexistent", "B": "alsogone"}, context={})
        nodes, edges = rule.apply(g, match)
        assert nodes == []
        assert edges == []


class TestAbductiveRuleEdgeCases:
    def test_deduplicates_after_applying_twice(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="cause", label="rain"))
        g.add_node(Hypernode(id="effect", label="wet"))
        g.add_edge(Hyperedge(source_ids=frozenset({"cause"}), target_ids=frozenset({"effect"}), label="leads_to"))
        rule = AbductiveRule(effect_label="leads_to")
        match = rule.find_matches(g, frozenset({"cause", "effect"}))[0]
        rule.apply(g, match)
        rule.find_matches(g, frozenset({"cause", "effect"}))
        cause_edges = [e for e in g.edges if e.label == "possible_cause"]
        assert len(cause_edges) == 1

    def test_handles_missing_node_in_find(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="effect", label="wet"))
        rule = AbductiveRule(effect_label="x")
        matches = rule.find_matches(g, frozenset({"effect"}))
        assert len(matches) == 0


class TestPropertyPropagationEdgeCases:
    def test_skips_missing_source_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="b"))
        rule = PropertyPropagationRule(property_key="domain")
        matches = rule.find_matches(g, frozenset({"nonexistent", "b"}))
        assert len(matches) == 0

    def test_skips_missing_target_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", metadata=Metadata(custom={"color": "red"})))
        g.add_node(Hypernode(id="ghost"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"ghost"})))
        g.remove_node("ghost")
        rule = PropertyPropagationRule(property_key="color")
        matches = rule.find_matches(g, frozenset({"a"}))
        assert all(m.bindings["target"] != "ghost" for m in matches)

    def test_apply_returns_empty_for_missing_target(self):
        g = Hypergraph()
        rule = PropertyPropagationRule(property_key="color")
        match = RuleMatch(
            rule_name="propagate(color)",
            bindings={"source": "a", "target": "nonexistent"},
            context={"property_value": "red", "via_edge": "e1"},
        )
        nodes, edges = rule.apply(g, match)
        assert nodes == []
        assert edges == []

    def test_respects_edge_label_filter(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", metadata=Metadata(custom={"color": "red"})))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="wrong"))
        rule = PropertyPropagationRule(property_key="color", edge_label="correct")
        matches = rule.find_matches(g, frozenset({"a", "b"}))
        assert len(matches) == 0


class TestMultiwayGraph:
    def test_add_state(self):
        mw = MultiwayGraph()
        state = MultiwayState(id="s0", active_node_ids=frozenset({"a", "b"}))
        mw.add_state(state)
        assert mw.state_count == 1
        assert mw.get_state("s0") is state

    def test_parent_child_tracking(self):
        mw = MultiwayGraph()
        parent = MultiwayState(id="p", active_node_ids=frozenset({"a"}))
        child = MultiwayState(id="c", parent_id="p", active_node_ids=frozenset({"a", "b"}))
        mw.add_state(parent)
        mw.add_state(child)
        assert mw.get_children("p") == [child]
        assert child.parent_id == "p"

    def test_siblings(self):
        mw = MultiwayGraph()
        parent = MultiwayState(id="p")
        c1 = MultiwayState(id="c1", parent_id="p")
        c2 = MultiwayState(id="c2", parent_id="p")
        c3 = MultiwayState(id="c3", parent_id="p")
        mw.add_state(parent)
        mw.add_state(c1)
        mw.add_state(c2)
        mw.add_state(c3)
        siblings = mw.get_siblings("c1")
        assert len(siblings) == 2
        assert all(s.id in {"c2", "c3"} for s in siblings)

    def test_ancestors(self):
        mw = MultiwayGraph()
        root = MultiwayState(id="r")
        mid = MultiwayState(id="m", parent_id="r")
        leaf = MultiwayState(id="l", parent_id="m")
        mw.add_state(root)
        mw.add_state(mid)
        mw.add_state(leaf)
        ancestors = mw.get_ancestors("l")
        assert [s.id for s in ancestors] == ["m", "r"]

    def test_leaves(self):
        mw = MultiwayGraph()
        root = MultiwayState(id="r")
        c1 = MultiwayState(id="c1", parent_id="r")
        c2 = MultiwayState(id="c2", parent_id="r")
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        leaves = mw.get_leaves()
        assert len(leaves) == 2

    def test_branchial_distance(self):
        mw = MultiwayGraph()
        root = MultiwayState(id="r")
        c1 = MultiwayState(id="c1", parent_id="r")
        c2 = MultiwayState(id="c2", parent_id="r")
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        assert mw.branchial_distance("c1", "c2") == 2.0
        assert mw.branchial_distance("c1", "c1") == 0.0

    def test_common_ancestor(self):
        mw = MultiwayGraph()
        root = MultiwayState(id="r")
        c1 = MultiwayState(id="c1", parent_id="r")
        c2 = MultiwayState(id="c2", parent_id="r")
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        assert mw.find_common_ancestor("c1", "c2") == "r"

    def test_branchial_relations(self):
        mw = MultiwayGraph()
        root = MultiwayState(id="r")
        c1 = MultiwayState(id="c1", parent_id="r")
        c2 = MultiwayState(id="c2", parent_id="r")
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        relations = mw.get_branchial_relations()
        assert len(relations) >= 1
        assert all(r.common_ancestor_id == "r" for r in relations)


class TestMultiwayEngine:
    def _build_chain_graph(self):
        g = Hypergraph()
        nodes = [Hypernode(id=f"n{i}", label=f"node{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        for i in range(4):
            g.add_edge(Hyperedge(
                source_ids=frozenset({f"n{i}"}),
                target_ids=frozenset({f"n{i+1}"}),
                label="next",
            ))
        return g

    def test_expand_creates_branches(self):
        g = self._build_chain_graph()
        engine = MultiwayEngine(g)
        rules = [TransitiveRule(edge_label="next")]
        report = engine.expand({"n0", "n1", "n2", "n3", "n4"}, rules, max_depth=3)
        assert report.rules_applied > 0
        assert report.states_created > 1
        assert report.edges_produced > 0

    def test_expand_from_labels(self):
        g = self._build_chain_graph()
        engine = MultiwayEngine(g)
        rules = [TransitiveRule(edge_label="next")]
        report = engine.expand_from_labels({"node0"}, rules, max_depth=2)
        assert report.states_created >= 1

    def test_max_depth_respected(self):
        g = self._build_chain_graph()
        engine = MultiwayEngine(g)
        rules = [TransitiveRule(edge_label="next")]
        report = engine.expand({"n0", "n1", "n2", "n3", "n4"}, rules, max_depth=1)
        assert report.max_depth_reached <= 1

    def test_max_total_states(self):
        g = self._build_chain_graph()
        engine = MultiwayEngine(g)
        rules = [TransitiveRule(edge_label="next")]
        report = engine.expand({"n0", "n1", "n2", "n3", "n4"}, rules, max_depth=5, max_total_states=5)
        assert report.states_created <= 5

    def test_multiple_rules_branch(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = MultiwayEngine(g)
        rules = [
            TransitiveRule(edge_label="rel"),
            InverseRule(edge_label="rel", inverse_label="inv_rel"),
        ]
        report = engine.expand({"a", "b", "c"}, rules, max_depth=2)
        assert report.rules_applied >= 2

    def test_find_convergent_states(self):
        g = Hypergraph()
        for label in ["x", "y"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"x"}), target_ids=frozenset({"y"}), label="rel"))
        engine = MultiwayEngine(g)
        rules = [InverseRule(edge_label="rel", inverse_label="inv")]
        engine.expand({"x", "y"}, rules, max_depth=1)
        convergences = engine.find_convergent_states()
        assert isinstance(convergences, list)

    def test_lateral_insights(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = MultiwayEngine(g)
        rules = [
            TransitiveRule(edge_label="rel"),
            InverseRule(edge_label="rel", inverse_label="inv"),
        ]
        engine.expand({"a", "b", "c"}, rules, max_depth=1)
        root = engine.multiway.get_root()
        assert root is not None
        children = engine.multiway.get_children(root.id)
        if children:
            insights = engine.get_lateral_insights(children[0].id)
            assert isinstance(insights, list)

    def test_empty_rules_no_expansion(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        engine = MultiwayEngine(g)
        report = engine.expand({"a"}, [], max_depth=3)
        assert report.rules_applied == 0
        assert report.states_created == 1
        assert report.branches == 1


class TestRuleFromDictAllTypes:
    def _round_trip(self, rule: Rule) -> None:
        data = rule.to_dict()
        restored = Rule.from_dict(data)
        assert isinstance(restored, type(rule))
        assert restored.to_dict() == data

    def test_transitive_rule(self):
        self._round_trip(TransitiveRule(edge_label="causes", new_label="inferred"))

    def test_transitive_rule_no_label(self):
        self._round_trip(TransitiveRule())

    def test_inverse_rule(self):
        self._round_trip(InverseRule(edge_label="causes", inverse_label="prevented_by"))

    def test_generalization_rule(self):
        self._round_trip(GeneralizationRule())

    def test_abductive_rule(self):
        self._round_trip(AbductiveRule())

    def test_property_propagation_rule(self):
        self._round_trip(PropertyPropagationRule(property_key="color"))

    def test_structural_projection_rule(self):
        self._round_trip(StructuralProjectionRule())

    def test_hub_inference_rule(self):
        self._round_trip(HubInferenceRule())

    def test_contextual_substitution_rule(self):
        self._round_trip(ContextualSubstitutionRule())

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            Rule.from_dict({"rule_type": "NonexistentRule"})


class TestRuleConfidence:
    def test_transitive_rule_sets_confidence(self):
        g, a, b, c = _make_rule_graph()
        rule = TransitiveRule(edge_label="next")
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) == 1
        rule.apply(g, matches[0])
        inferred = [e for e in g.edges if e.metadata.custom.get("inferred")]
        assert len(inferred) == 1
        assert inferred[0].metadata.custom["confidence"] == 0.9

    def test_inverse_rule_sets_confidence(self):
        g, a, b, c = _make_rule_graph()
        rule = InverseRule(edge_label="next", inverse_label="prev")
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) == 2
        rule.apply(g, matches[0])
        inferred = [e for e in g.edges if e.metadata.custom.get("inferred")]
        assert any(e.metadata.custom.get("confidence") == 0.9 for e in inferred)

    def test_abductive_rule_sets_confidence(self):
        g, a, b, c = _make_rule_graph()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({a.id}),
                target_ids=frozenset({b.id}),
                label="causes",
            )
        )
        rule = AbductiveRule(effect_label="causes")
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) == 1
        rule.apply(g, matches[0])
        inferred = [e for e in g.edges if e.metadata.custom.get("inferred")]
        assert len(inferred) == 1
        assert any(e.metadata.custom.get("confidence") == 0.5 for e in inferred)


class TestIncrementalExpansion:
    def test_reason_incremental(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason({"a", "b", "c"}, use_overlay=False)
        assert result["expansion"]["rules_applied"] > 0
        mem.store("d")
        mem.relate("c", "d", label="next")
        inc_result = mem.reason_incremental({"c", "d"})
        assert "expansion" in inc_result

    def test_reason_incremental_no_prior_session(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.reason_incremental({"a"})
        assert "error" in result


class TestExhaustiveReasoning:
    def test_exhaustive_explores_more_states(self):
        mem = HypergraphMemory(evolve_interval=0)
        for ch in "abcdefghij":
            mem.store(ch)
        for i in range(9):
            mem.relate(chr(ord("a") + i), chr(ord("a") + i + 1), label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        bounded = mem.reason({"a", "b", "c", "d"}, max_total_states=2)
        bounded_states = bounded.expansion.states_created if bounded.expansion else 0
        mem2 = HypergraphMemory(evolve_interval=0)
        for ch in "abcdefghij":
            mem2.store(ch)
        for i in range(9):
            mem2.relate(chr(ord("a") + i), chr(ord("a") + i + 1), label="next")
        mem2.add_rules(TransitiveRule(edge_label="next"))
        exhaustive = mem2.reason({"a", "b", "c", "d"}, max_total_states=2, exhaustive=True)
        exhaustive_states = exhaustive.expansion.states_created if exhaustive.expansion else 0
        assert exhaustive_states >= bounded_states

    def test_exhaustive_flag_signature(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        result = mem.reason({"x"}, exhaustive=True)
        assert result.error is None or isinstance(result.error, str)


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
        assert len(matches) == 1
        assert "analogy_score" in matches[0].context

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
        assert ab_matches[0].context["confidence"] == 0.75
        assert ab_matches[0].context["support"] == 3

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
        assert len(matches) == 3

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


class TestRuleScoring:
    def test_transitive_rule_scores_high_for_weighted_edges(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next", weight=2.0))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next", weight=2.0))
        rule = TransitiveRule(edge_label="next")
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) > 0
        score = rule.score_match(matches[0], g)
        assert score > 1.0

    def test_default_score_is_one(self):
        rule = InverseRule(edge_label="x", inverse_label="y")
        match = RuleMatch(rule_name="test", bindings={"source": "a", "target": "b"})
        g = Hypergraph()
        assert rule.score_match(match, g) >= 0.0



def _make_rule_graph():
    g = Hypergraph()
    a = Hypernode(label="a", data={"x": 1})
    b = Hypernode(label="b", data={"x": 1})
    c = Hypernode(label="c", data={"x": 1})
    g.add_node(a)
    g.add_node(b)
    g.add_node(c)
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"
        )
    )
    return g, a, b, c



def _setup_memory():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.relate("a", "b", label="next")
    mem.relate("b", "c", label="next")
    mem.add_rules(TransitiveRule(edge_label="next"))
    return mem


class TestRuleBaseClass:
    def test_base_score_match_returns_one(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x"))
        rule = TransitiveRule()
        match = RuleMatch(rule_name="test", bindings={"A": "x", "B": "x", "C": "x"})
        assert rule.score_match(match, g) == 1.0

    def test_base_find_derivation_returns_empty(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x"))
        rule = TransitiveRule()
        assert rule.find_derivation("x", g) == []


class TestTransitiveRuleDerivation:
    def test_find_derivation_finds_chain(self):
        g = Hypergraph()
        a, b, c = Hypernode(id="a"), Hypernode(id="b"), Hypernode(id="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        derivations = rule.find_derivation("c", g)
        assert len(derivations) == 1
        assert derivations[0].bindings["C"] == "c"
        assert derivations[0].bindings["B"] == "b"
        assert derivations[0].bindings["A"] == "a"

    def test_find_derivation_skips_self_loop(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="rel"))
        rule = TransitiveRule(edge_label="rel")
        derivations = rule.find_derivation("a", g)
        assert all(d.bindings["A"] != d.bindings["C"] for d in derivations)

    def test_find_derivation_empty_for_isolated(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x"))
        rule = TransitiveRule()
        assert rule.find_derivation("x", g) == []


class TestInverseRuleDerivation:
    def test_find_derivation_finds_inverse(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="next"))
        rule = InverseRule(edge_label="next", inverse_label="prev")
        derivations = rule.find_derivation("b", g)
        assert len(derivations) == 1
        assert derivations[0].bindings["source"] == "a"
        assert derivations[0].bindings["target"] == "b"

    def test_find_derivation_skips_existing_inverse(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="prev"))
        rule = InverseRule(edge_label="next", inverse_label="prev")
        derivations = rule.find_derivation("b", g)
        assert len(derivations) == 0


class TestGeneralizationRuleScoreMatch:
    def test_score_match_uses_context_similarity(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = GeneralizationRule(similarity_threshold=0.5)
        match = RuleMatch(rule_name="generalization", bindings={}, context={"similarity": 0.8})
        assert rule.score_match(match, g) == 0.8

    def test_score_match_defaults_to_half(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = GeneralizationRule(similarity_threshold=0.5)
        match = RuleMatch(rule_name="generalization", bindings={}, context={})
        assert rule.score_match(match, g) == 0.5


class TestAbductiveRuleScoreMatch:
    def test_score_match_with_via_edge(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        edge = Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            label="causes",
            weight=2.0,
            metadata=Metadata(custom={"confidence": 0.8}),
        )
        g.add_edge(edge)
        rule = AbductiveRule(effect_label="causes")
        match = RuleMatch(rule_name="abductive", bindings={}, context={"via_edge": edge.id})
        score = rule.score_match(match, g)
        expected = min(max(2.0 * 0.6 * 0.8, 0.1), 1.0)
        assert score == pytest.approx(expected)

    def test_score_match_fallback_without_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = AbductiveRule()
        match = RuleMatch(rule_name="abductive", bindings={}, context={})
        assert rule.score_match(match, g) == 0.3


class TestPropertyPropagationRuleScoreMatch:
    def test_score_match_with_numeric_value(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), weight=2.0)
        g.add_edge(edge)
        rule = PropertyPropagationRule(property_key="k")
        match = RuleMatch(rule_name="prop", bindings={}, context={"via_edge": edge.id, "property_value": 5.0})
        score = rule.score_match(match, g)
        specificity = min(abs(5.0) * 0.1, 0.5) + 0.5
        expected = min(max(2.0 * 0.7 * specificity, 0.1), 1.0)
        assert score == pytest.approx(expected)

    def test_score_match_with_string_value(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        edge = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), weight=1.0)
        g.add_edge(edge)
        rule = PropertyPropagationRule(property_key="k")
        match = RuleMatch(rule_name="prop", bindings={}, context={"via_edge": edge.id, "property_value": "abc"})
        score = rule.score_match(match, g)
        specificity = min(len("abc") * 0.05, 0.5) + 0.5
        expected = min(max(1.0 * 0.7 * specificity, 0.1), 1.0)
        assert score == pytest.approx(expected)

    def test_score_match_fallback_without_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = PropertyPropagationRule(property_key="k")
        match = RuleMatch(rule_name="prop", bindings={}, context={})
        assert rule.score_match(match, g) == 0.4


class TestStructuralProjectionRuleEdgeCases:
    def test_fewer_than_four_embeddings_returns_empty(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)

        class SmallEngine:
            def get_embedding(self, node_id):
                return np.array([1.0])

        rule = StructuralProjectionRule(similarity_threshold=0.5)
        rule.set_embedding_engine(SmallEngine())
        matches = rule.find_matches(g, frozenset({a.id, b.id}))
        assert matches == []

    def test_cosine_sim_with_zero_norm(self):
        rule = StructuralProjectionRule()
        assert rule._cosine_sim(np.array([0.0, 0.0]), np.array([1.0, 0.0])) == 0.0

    def test_cosine_sim_with_vectors(self):
        rule = StructuralProjectionRule()
        sim = rule._cosine_sim(np.array([1.0, 0.0]), np.array([1.0, 0.0]))
        assert sim == pytest.approx(1.0)


class TestHubInferenceRuleEdgeCases:
    def test_skips_unlabeled_edges(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label=""))
        rule = HubInferenceRule(min_support=1, confidence_threshold=0.5)
        matches = rule.find_matches(g, frozenset({a.id, b.id}))
        assert len(matches) == 0

    def test_skips_self_target(self):
        g = Hypergraph()
        a = Hypernode(id="a")
        g.add_node(a)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({a.id}), label="self"))
        rule = HubInferenceRule(min_support=1, confidence_threshold=0.5)
        matches = rule.find_matches(g, frozenset({a.id}))
        assert len(matches) == 0

    def test_existing_causes_edge_prevents_match(self):
        g = Hypergraph()
        a, b = Hypernode(id="a"), Hypernode(id="b")
        g.add_node(a)
        g.add_node(b)
        for _ in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="leads_to"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="causes"))
        rule = HubInferenceRule(min_support=2, confidence_threshold=0.5, causes_label="causes")
        matches = rule.find_matches(g, frozenset({a.id, b.id}))
        assert len(matches) == 0

    def test_score_match_uses_confidence(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = HubInferenceRule()
        match = RuleMatch(rule_name="hub", bindings={}, context={"confidence": 0.85})
        assert rule.score_match(match, g) == 0.85


class TestContextualSubstitutionScoreMatch:
    def test_score_match_uses_similarity(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = ContextualSubstitutionRule()
        match = RuleMatch(rule_name="sub", bindings={}, context={"similarity": 0.7})
        assert rule.score_match(match, g) == 0.7

    def test_score_match_defaults(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = ContextualSubstitutionRule()
        match = RuleMatch(rule_name="sub", bindings={}, context={})
        assert rule.score_match(match, g) == 0.5


class TestStructuralProjectionScoreMatch:
    def test_score_match_uses_analogy_score(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = StructuralProjectionRule()
        match = RuleMatch(rule_name="proj", bindings={}, context={"analogy_score": 0.6})
        assert rule.score_match(match, g) == 0.6

    def test_score_match_defaults(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        rule = StructuralProjectionRule()
        match = RuleMatch(rule_name="proj", bindings={}, context={})
        assert rule.score_match(match, g) == 0.5

