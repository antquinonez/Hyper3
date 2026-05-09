from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.multiway import MultiwayGraph, MultiwayState
from hyper3.rules_simultaneity import SimultaneityRule


def _make_setup() -> tuple[Hypergraph, MultiwayGraph, SimultaneityRule]:
    g = Hypergraph()
    mw = MultiwayGraph()
    rule = SimultaneityRule(mw)
    return g, mw, rule


class TestSimultaneityRuleConstruction:
    def test_name(self):
        _, _, rule = _make_setup()
        assert rule.name == "simultaneity"


class TestFindMatches:
    def test_no_multiway_states(self):
        g, mw, rule = _make_setup()
        assert rule.find_matches(g, frozenset()) == []

    def test_single_leaf_no_match(self):
        g, mw, rule = _make_setup()
        n = Hypernode(label="a")
        g.add_node(n)
        root = MultiwayState(active_node_ids=frozenset({n.id}))
        mw.add_state(root)
        leaf = MultiwayState(parent_id=root.id, active_node_ids=frozenset({n.id}))
        mw.add_state(leaf)
        assert rule.find_matches(g, frozenset({n.id})) == []

    def test_two_leaves_same_parent(self):
        g, mw, rule = _make_setup()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        root = MultiwayState(active_node_ids=frozenset({n1.id, n2.id}))
        mw.add_state(root)
        leaf1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({n1.id}))
        leaf2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({n2.id}))
        mw.add_state(leaf1)
        mw.add_state(leaf2)
        matches = rule.find_matches(g, frozenset({n1.id, n2.id}))
        assert len(matches) == 1
        assert matches[0].bindings["source"] != matches[0].bindings["target"]

    def test_two_leaves_different_parents(self):
        g, mw, rule = _make_setup()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        root1 = MultiwayState(active_node_ids=frozenset({n1.id}))
        root2 = MultiwayState(active_node_ids=frozenset({n2.id}))
        mw.add_state(root1)
        mw.add_state(root2)
        leaf1 = MultiwayState(parent_id=root1.id, active_node_ids=frozenset({n1.id}))
        leaf2 = MultiwayState(parent_id=root2.id, active_node_ids=frozenset({n2.id}))
        mw.add_state(leaf1)
        mw.add_state(leaf2)
        matches = rule.find_matches(g, frozenset({n1.id, n2.id}))
        assert matches == []

    def test_existing_edge_no_rematch(self):
        g, mw, rule = _make_setup()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        g.add_edge(Hyperedge(
            source_ids=frozenset({n1.id}),
            target_ids=frozenset({n2.id}),
            label="simultaneous",
        ))
        root = MultiwayState(active_node_ids=frozenset({n1.id, n2.id}))
        mw.add_state(root)
        leaf1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({n1.id}))
        leaf2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({n2.id}))
        mw.add_state(leaf1)
        mw.add_state(leaf2)
        matches = rule.find_matches(g, frozenset({n1.id, n2.id}))
        assert matches == []

    def test_not_in_active_nodes(self):
        g, mw, rule = _make_setup()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        n3 = Hypernode(label="c")
        g.add_node(n1)
        g.add_node(n2)
        g.add_node(n3)
        root = MultiwayState(active_node_ids=frozenset({n1.id, n2.id}))
        mw.add_state(root)
        leaf1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({n1.id}))
        leaf2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({n2.id}))
        mw.add_state(leaf1)
        mw.add_state(leaf2)
        matches = rule.find_matches(g, frozenset({n1.id}))
        assert matches == []


class TestApply:
    def test_creates_edge(self):
        g, _, rule = _make_setup()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        match_dict = type("M", (), {
            "rule_name": "simultaneity",
            "bindings": {"source": n1.id, "target": n2.id},
            "context": {},
        })()
        new_nodes, new_edges = rule.apply(g, match_dict)
        assert new_nodes == []
        assert len(new_edges) == 1
        edge = g.get_edge(new_edges[0])
        assert edge.label == "simultaneous"
        assert n1.id in edge.source_ids
        assert n2.id in edge.target_ids
