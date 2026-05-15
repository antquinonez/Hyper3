"""Tests for DecompositionRule."""

from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata
from hyper3.rules import Rule, RuleMatch
from hyper3.rules_decomposition import DecompositionRule


def _make_graph_with_hub(
    hub_label: str = "hub",
    neighbor_labels: list[str] | None = None,
    edge_label: str = "relates_to",
) -> tuple[Hypergraph, str, list[str]]:
    g = Hypergraph()
    hub = Hypernode(label=hub_label)
    g.add_node(hub)
    nids: list[str] = []
    for nl in neighbor_labels or []:
        n = Hypernode(label=nl)
        g.add_node(n)
        nids.append(n.id)
        e = Hyperedge(
            source_ids=frozenset({hub.id}),
            target_ids=frozenset({n.id}),
            label=edge_label,
        )
        g.add_edge(e)
    return g, hub.id, nids


class TestConstruction:
    def test_default_parameters(self):
        rule = DecompositionRule()
        assert rule.name == "decomposition"
        assert rule._min_degree == 5
        assert rule._min_group_size == 2
        assert rule._edge_label == "decomposes_into"
        assert rule._max_hubs == 10

    def test_custom_parameters(self):
        rule = DecompositionRule(min_degree=3, min_group_size=3, edge_label="parts", max_hubs=5)
        assert rule._min_degree == 3
        assert rule._min_group_size == 3
        assert rule._edge_label == "parts"
        assert rule._max_hubs == 5

    def test_name_property(self):
        assert DecompositionRule().name == "decomposition"


class TestFindMatches:
    def test_node_below_min_degree_no_matches(self):
        g = Hypergraph()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(4):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            e = Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="relates_to")
            g.add_edge(e)
        rule = DecompositionRule(min_degree=5)
        matches = rule.find_matches(g, frozenset({hub.id}))
        assert matches == []

    def test_hub_with_two_label_groups(self):
        g = Hypergraph()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(3):
            n = Hypernode(label=f"a{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="type_a"))
        for i in range(2):
            n = Hypernode(label=f"b{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="type_b"))
        rule = DecompositionRule(min_degree=5)
        matches = rule.find_matches(g, frozenset({hub.id}))
        assert len(matches) == 1
        assert matches[0].bindings["hub"] == hub.id
        assert matches[0].context["group_count"] == 2
        assert "type_a" in matches[0].context["groups"]
        assert "type_b" in matches[0].context["groups"]

    def test_all_neighbors_same_label_no_partition(self):
        g, hub_id, _ = _make_graph_with_hub("hub", [f"n{i}" for i in range(6)], "same_label")
        rule = DecompositionRule(min_degree=5, min_group_size=2)
        matches = rule.find_matches(g, frozenset({hub_id}))
        assert matches == []

    def test_hub_with_three_groups(self):
        g = Hypergraph()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for label in ("type_a", "type_b", "type_c"):
            for i in range(2):
                n = Hypernode(label=f"{label}_{i}")
                g.add_node(n)
                g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label=label))
        rule = DecompositionRule(min_degree=5, min_group_size=2)
        matches = rule.find_matches(g, frozenset({hub.id}))
        assert len(matches) == 1
        assert matches[0].context["group_count"] == 3

    def test_existing_decomposes_into_edge_skips(self):
        g = Hypergraph()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(3):
            n = Hypernode(label=f"a{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="type_a"))
        for i in range(2):
            n = Hypernode(label=f"b{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="type_b"))
        existing_summary = Hypernode(label="hub_type_a")
        g.add_node(existing_summary)
        g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({existing_summary.id}), label="decomposes_into"))
        rule = DecompositionRule(min_degree=5)
        matches = rule.find_matches(g, frozenset({hub.id}))
        assert matches == []

    def test_max_hubs_limits_output(self):
        rule = DecompositionRule(min_degree=5, min_group_size=2, max_hubs=2)
        g = Hypergraph()
        all_ids: set[str] = set()
        for h in range(4):
            hub = Hypernode(label=f"hub{h}")
            g.add_node(hub)
            all_ids.add(hub.id)
            for label in ("x", "y"):
                for i in range(3):
                    n = Hypernode(label=f"h{h}_{label}_{i}")
                    g.add_node(n)
                    all_ids.add(n.id)
                    g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label=label))
        matches = rule.find_matches(g, frozenset(all_ids))
        assert len(matches) == 2

    def test_inactive_node_skipped(self):
        g = Hypergraph()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for i in range(3):
            n = Hypernode(label=f"a{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="type_a"))
        for i in range(2):
            n = Hypernode(label=f"b{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="type_b"))
        rule = DecompositionRule(min_degree=5)
        matches = rule.find_matches(g, frozenset())
        assert matches == []

    def test_empty_graph(self):
        g = Hypergraph()
        rule = DecompositionRule()
        matches = rule.find_matches(g, frozenset())
        assert matches == []

    def test_hub_with_degree_exactly_min_degree(self):
        g = Hypergraph()
        hub = Hypernode(label="hub")
        g.add_node(hub)
        for label in ("x", "y"):
            for i in range(2):
                n = Hypernode(label=f"{label}_{i}")
                g.add_node(n)
                g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label=label))
        extra = Hypernode(label="extra")
        g.add_node(extra)
        g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({extra.id}), label="z"))
        rule = DecompositionRule(min_degree=5, min_group_size=2)
        matches = rule.find_matches(g, frozenset({hub.id}))
        assert len(matches) == 1
        assert matches[0].context["group_count"] == 2


class TestApply:
    def _make_match(self) -> tuple[Hypergraph, DecompositionRule, RuleMatch]:
        g = Hypergraph()
        hub = Hypernode(label="system")
        g.add_node(hub)
        members_a: list[str] = []
        for i in range(3):
            n = Hypernode(label=f"a{i}")
            g.add_node(n)
            members_a.append(n.id)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="hardware"))
        members_b: list[str] = []
        for i in range(2):
            n = Hypernode(label=f"b{i}")
            g.add_node(n)
            members_b.append(n.id)
            g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({n.id}), label="software"))
        rule = DecompositionRule(min_degree=5)
        matches = rule.find_matches(g, frozenset({hub.id}))
        assert len(matches) == 1
        return g, rule, matches[0]

    def test_creates_summary_nodes_for_each_group(self):
        g, rule, match = self._make_match()
        node_count_before = g.node_count
        new_nodes, _ = rule.apply(g, match)
        assert len(new_nodes) == 2
        assert g.node_count == node_count_before + 2

    def test_creates_decomposes_into_edges(self):
        g, rule, match = self._make_match()
        _, new_edges = rule.apply(g, match)
        decomp_edges = [eid for eid in new_edges if (e := g.get_edge(eid)) is not None and e.label == "decomposes_into"]
        assert len(decomp_edges) == 2

    def test_creates_contains_edges(self):
        g, rule, match = self._make_match()
        _, new_edges = rule.apply(g, match)
        contains_edges = [eid for eid in new_edges if (e := g.get_edge(eid)) is not None and e.label == "contains"]
        assert len(contains_edges) == 2

    def test_returns_node_and_edge_ids(self):
        g, rule, match = self._make_match()
        new_nodes, new_edges = rule.apply(g, match)
        assert len(new_nodes) == 2
        assert len(new_edges) == 4

    def test_summary_node_label_contains_hub_and_group(self):
        g, rule, match = self._make_match()
        new_nodes, _ = rule.apply(g, match)
        labels = {n.label for nid in new_nodes if (n := g.get_node(nid)) is not None}
        assert "system_hardware" in labels
        assert "system_software" in labels

    def test_nary_contains_edge_has_all_members(self):
        g, rule, match = self._make_match()
        _, new_edges = rule.apply(g, match)
        contains_edges = [e for eid in new_edges if (e := g.get_edge(eid)) is not None and e.label == "contains"]
        member_counts = {len(e.target_ids) for e in contains_edges}
        assert 3 in member_counts
        assert 2 in member_counts


class TestScoreMatch:
    def test_returns_score(self):
        rule = DecompositionRule()
        match = RuleMatch(
            rule_name="decomposition",
            bindings={"hub": "x"},
            context={"group_count": 3},
        )
        score = rule.score_match(match, Hypergraph())
        assert 0.0 <= score <= 1.0
        assert score == pytest.approx(0.3)


class TestSerialization:
    def test_to_dict_round_trip(self):
        rule = DecompositionRule(min_degree=7, min_group_size=3, edge_label="parts", max_hubs=5)
        data = rule.to_dict()
        assert data["rule_type"] == "DecompositionRule"
        assert data["min_degree"] == 7
        assert data["min_group_size"] == 3
        assert data["edge_label"] == "parts"
        assert data["max_hubs"] == 5

    def test_from_dict_round_trip(self):
        original = DecompositionRule(min_degree=8, min_group_size=4, edge_label="sub", max_hubs=3)
        data = original.to_dict()
        restored = Rule.from_dict(data)
        assert isinstance(restored, DecompositionRule)
        assert restored._min_degree == 8
        assert restored._min_group_size == 4
        assert restored._edge_label == "sub"
        assert restored._max_hubs == 3
