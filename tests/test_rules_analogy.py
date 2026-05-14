from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata
from hyper3.memory import HypergraphMemory
from hyper3.rules import RuleMatch
from hyper3.rules_analogy import AnalogicalReasoningRule


def _make_analogy_graph() -> tuple[Hypergraph, Hypernode, Hypernode, Hypernode, Hypernode]:
    g = Hypergraph()
    dog = Hypernode(label="dog")
    cat = Hypernode(label="cat")
    bark = Hypernode(label="bark")
    meow = Hypernode(label="meow")
    g.add_node(dog)
    g.add_node(cat)
    g.add_node(bark)
    g.add_node(meow)
    g.add_edge(Hyperedge(source_ids=frozenset({dog.id}), target_ids=frozenset({bark.id}), label="sound"))
    g.add_edge(Hyperedge(source_ids=frozenset({dog.id}), target_ids=frozenset({cat.id}), label="is_mammal"))
    g.add_edge(Hyperedge(source_ids=frozenset({cat.id}), target_ids=frozenset({meow.id}), label="sound"))
    g.add_edge(Hyperedge(source_ids=frozenset({cat.id}), target_ids=frozenset({dog.id}), label="is_mammal"))
    return g, dog, cat, bark, meow


class TestConstruction:
    def test_name(self):
        rule = AnalogicalReasoningRule()
        assert rule.name == "analogy"

    def test_default_parameters(self):
        rule = AnalogicalReasoningRule()
        d = rule.to_dict()
        assert d["edge_label"] == "analogous_to"
        assert d["similarity_threshold"] == 0.6
        assert d["min_outgoing_labels"] == 2
        assert d["max_candidates"] == 50

    def test_custom_parameters(self):
        rule = AnalogicalReasoningRule(
            edge_label="similar_to",
            similarity_threshold=0.8,
            min_outgoing_labels=3,
            max_candidates=10,
        )
        d = rule.to_dict()
        assert d["edge_label"] == "similar_to"
        assert d["similarity_threshold"] == 0.8
        assert d["min_outgoing_labels"] == 3
        assert d["max_candidates"] == 10


class TestFindMatches:
    def test_no_nodes(self):
        g = Hypergraph()
        rule = AnalogicalReasoningRule()
        assert rule.find_matches(g, frozenset()) == []

    def test_single_node(self):
        g = Hypergraph()
        n = Hypernode(label="a")
        g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id}), target_ids=frozenset({n.id}), label="self"))
        rule = AnalogicalReasoningRule()
        assert rule.find_matches(g, frozenset({n.id})) == []

    def test_two_nodes_identical_labels_one_match(self):
        g, dog, cat, bark, meow = _make_analogy_graph()
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        assert len(matches) == 1
        m = matches[0]
        assert m.bindings["A"] != m.bindings["C"]
        assert m.context["similarity"] > 0.0
        assert "sound" in m.context["shared_labels"]
        assert "is_mammal" in m.context["shared_labels"]

    def test_disjoint_labels_no_match(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        x = Hypernode(label="x")
        y = Hypernode(label="y")
        g.add_node(a)
        g.add_node(b)
        g.add_node(x)
        g.add_node(y)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({x.id}), label="eats"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({y.id}), label="drinks"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({x.id}), label="watches"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({y.id}), label="ignores"))
        rule = AnalogicalReasoningRule()
        assert rule.find_matches(g, frozenset({a.id, b.id})) == []

    def test_below_min_outgoing_labels(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="only_one"))
        rule = AnalogicalReasoningRule(min_outgoing_labels=2)
        assert rule.find_matches(g, frozenset({a.id, b.id})) == []

    def test_existing_analogy_edge_no_rematch(self):
        g, dog, cat, bark, meow = _make_analogy_graph()
        g.add_edge(Hyperedge(
            source_ids=frozenset({dog.id}),
            target_ids=frozenset({cat.id}),
            label="analogous_to",
        ))
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        assert matches == []

    def test_similarity_below_threshold(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        c = Hypernode(label="c")
        d = Hypernode(label="d")
        e = Hypernode(label="e")
        f = Hypernode(label="f")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_node(d)
        g.add_node(e)
        g.add_node(f)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), label="y"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({e.id}), label="z"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({f.id}), label="w"))
        rule = AnalogicalReasoningRule(similarity_threshold=0.99)
        assert rule.find_matches(g, frozenset({a.id, b.id})) == []

    def test_max_candidates_limits_output(self):
        g = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(20)]
        for n in nodes:
            g.add_node(n)
        targets = [Hypernode(label=f"t{i}") for i in range(40)]
        for t in targets:
            g.add_node(t)
        for i, n in enumerate(nodes):
            g.add_edge(Hyperedge(source_ids=frozenset({n.id}), target_ids=frozenset({targets[2 * i].id}), label="sound"))
            g.add_edge(Hyperedge(source_ids=frozenset({n.id}), target_ids=frozenset({targets[2 * i + 1].id}), label="eats"))
        rule = AnalogicalReasoningRule(max_candidates=3)
        matches = rule.find_matches(g, frozenset(n.id for n in nodes) | frozenset(t.id for t in targets))
        assert len(matches) <= 3

    def test_self_analogy_prevented(self):
        g = Hypergraph()
        n = Hypernode(label="a")
        g.add_node(n)
        x = Hypernode(label="x")
        y = Hypernode(label="y")
        g.add_node(x)
        g.add_node(y)
        g.add_edge(Hyperedge(source_ids=frozenset({n.id}), target_ids=frozenset({x.id}), label="p"))
        g.add_edge(Hyperedge(source_ids=frozenset({n.id}), target_ids=frozenset({y.id}), label="q"))
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({n.id}))
        assert matches == []

    def test_empty_graph(self):
        g = Hypergraph()
        rule = AnalogicalReasoningRule()
        assert rule.find_matches(g, frozenset()) == []


class TestApply:
    def test_creates_edge_with_correct_label(self):
        g, dog, cat, bark, meow = _make_analogy_graph()
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        assert len(matches) == 1
        new_nodes, new_edges = rule.apply(g, matches[0])
        assert new_nodes == []
        assert len(new_edges) == 1
        edge = g.get_edge(new_edges[0])
        assert edge.label == "analogous_to"
        assert matches[0].bindings["A"] in edge.source_ids
        assert matches[0].bindings["C"] in edge.target_ids

    def test_edge_metadata(self):
        g, dog, cat, bark, meow = _make_analogy_graph()
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        _, new_edges = rule.apply(g, matches[0])
        edge = g.get_edge(new_edges[0])
        assert edge.metadata.custom["rule"] == "analogy"
        assert edge.metadata.custom["inferred"] is True
        assert isinstance(edge.metadata.custom["similarity"], float)
        assert isinstance(edge.metadata.custom["shared_labels"], list)

    def test_custom_edge_label(self):
        g, dog, cat, bark, meow = _make_analogy_graph()
        rule = AnalogicalReasoningRule(edge_label="similar_to")
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        _, new_edges = rule.apply(g, matches[0])
        edge = g.get_edge(new_edges[0])
        assert edge.label == "similar_to"


class TestScoreMatch:
    def test_returns_similarity(self):
        rule = AnalogicalReasoningRule()
        match = RuleMatch(
            rule_name="analogy",
            bindings={"A": "x", "C": "y"},
            context={"similarity": 0.85},
        )
        assert rule.score_match(match, Hypergraph()) == 0.85

    def test_default_on_missing_context(self):
        rule = AnalogicalReasoningRule()
        match = RuleMatch(rule_name="analogy", bindings={"A": "x", "C": "y"})
        assert rule.score_match(match, Hypergraph()) == 0.5


class TestSerialization:
    def test_to_dict_round_trip(self):
        original = AnalogicalReasoningRule(
            edge_label="sim",
            similarity_threshold=0.7,
            min_outgoing_labels=3,
            max_candidates=20,
        )
        data = original.to_dict()
        assert data["rule_type"] == "AnalogicalReasoningRule"
        restored = AnalogicalReasoningRule._from_dict(data)
        assert restored.to_dict() == data

    def test_from_dict_defaults(self):
        restored = AnalogicalReasoningRule._from_dict({"rule_type": "AnalogicalReasoningRule"})
        assert restored.to_dict()["edge_label"] == "analogous_to"
        assert restored.to_dict()["similarity_threshold"] == 0.6


class TestContext:
    def test_shared_labels_accurate(self):
        g, dog, cat, bark, meow = _make_analogy_graph()
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        assert len(matches) == 1
        shared = matches[0].context["shared_labels"]
        assert set(shared) == {"sound", "is_mammal"}

    def test_similarity_in_range(self):
        g, dog, cat, bark, meow = _make_analogy_graph()
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        assert len(matches) == 1
        sim = matches[0].context["similarity"]
        assert 0.0 <= sim <= 1.0


class TestIntegration:
    def test_reason_produces_analogy_edges(self):
        mem = HypergraphMemory(evolve_interval=0, rules=[AnalogicalReasoningRule()])
        mem.add("dog")
        mem.add("cat")
        mem.add("bark")
        mem.add("meow")
        mem.link("dog", "bark", label="sound")
        mem.link("dog", "cat", label="is_mammal")
        mem.link("cat", "meow", label="sound")
        mem.link("cat", "dog", label="is_mammal")
        mem.reason(seeds={"dog", "cat", "bark", "meow"}, depth=1)
        analogy_edges = [
            e for e in mem.graph.edges
            if e.label == "analogous_to"
        ]
        assert len(analogy_edges) >= 1

    def test_identical_data_different_structure(self):
        g = Hypergraph()
        a = Hypernode(label="a", data={"type": "x"})
        b = Hypernode(label="b", data={"type": "x"})
        c = Hypernode(label="c")
        d = Hypernode(label="d")
        e = Hypernode(label="e")
        f = Hypernode(label="f")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_node(d)
        g.add_node(e)
        g.add_node(f)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="p"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), label="q"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({e.id}), label="p"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({f.id}), label="q"))
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id, d.id, e.id, f.id}))
        assert len(matches) == 1
        assert matches[0].context["similarity"] >= 0.6

    def test_bidirectional_edges(self):
        g = Hypergraph()
        dog = Hypernode(label="dog")
        cat = Hypernode(label="cat")
        bark = Hypernode(label="bark")
        meow = Hypernode(label="meow")
        g.add_node(dog)
        g.add_node(cat)
        g.add_node(bark)
        g.add_node(meow)
        g.add_edge(Hyperedge(source_ids=frozenset({dog.id}), target_ids=frozenset({bark.id}), label="sound"))
        g.add_edge(Hyperedge(source_ids=frozenset({dog.id}), target_ids=frozenset({cat.id}), label="is_mammal"))
        g.add_edge(Hyperedge(source_ids=frozenset({cat.id}), target_ids=frozenset({meow.id}), label="sound"))
        g.add_edge(Hyperedge(source_ids=frozenset({cat.id}), target_ids=frozenset({dog.id}), label="is_mammal"))
        rule = AnalogicalReasoningRule()
        matches = rule.find_matches(g, frozenset({dog.id, cat.id, bark.id, meow.id}))
        assert len(matches) >= 1
        a_id = matches[0].bindings["A"]
        c_id = matches[0].bindings["C"]
        rule.apply(g, matches[0])
        reverse_match = RuleMatch(
            rule_name="analogy",
            bindings={"A": c_id, "C": a_id},
            context=matches[0].context,
        )
        rule.apply(g, reverse_match)
        analogy_edges = [
            e for e in g.edges
            if e.label == "analogous_to"
            and ((a_id in e.source_ids and c_id in e.target_ids) or (c_id in e.source_ids and a_id in e.target_ids))
        ]
        assert len(analogy_edges) == 2
