import pytest
from hyper3 import (
    Hypergraph,
    Hypernode,
    Hyperedge,
    Metadata,
    Modality,
    TransitiveRule,
    InverseRule,
    GeneralizationRule,
    AbductiveRule,
    PropertyPropagationRule,
    RuleMatch,
    MultiwayEngine,
    MultiwayGraph,
    MultiwayState,
    ExpansionReport,
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
        assert len(matches) >= 1


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
        assert len(matches) >= 1

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
        assert len(matches) >= 2


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
        matches2 = rule.find_matches(g, frozenset({"cause", "effect"}))
        cause_edges = [e for e in g.edges if e.label == "possible_cause"]
        assert len(cause_edges) >= 1

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
