from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory
from hyper3.structural_match import (
    StructuralPatternEngine,
    PatternTemplate,
    PatternNode,
    PatternEdge,
    StructuralMatch,
)
from hyper3.kernel import Hypergraph, Hypernode, Hyperedge


class TestMatchPatternDeep:
    def test_pattern_with_source_only_binding(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="A"))
        g.add_node(Hypernode(id="b", label="B"))
        g.add_node(Hypernode(id="c", label="C"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        engine = StructuralPatternEngine(g)
        pattern = PatternTemplate(
            name="multi_target",
            nodes=[PatternNode(role="src"), PatternNode(role="tgt")],
            edges=[
                PatternEdge(source_role="src", target_role="tgt", label="rel"),
            ],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 2

    def test_pattern_with_target_only_binding(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="A"))
        g.add_node(Hypernode(id="b", label="B"))
        g.add_node(Hypernode(id="c", label="C"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = StructuralPatternEngine(g)
        pattern = PatternTemplate(
            name="multi_source",
            nodes=[PatternNode(role="src"), PatternNode(role="tgt")],
            edges=[
                PatternEdge(source_role="src", target_role="tgt", label="rel"),
            ],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 2

    def test_pattern_no_nodes_or_edges(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        engine = StructuralPatternEngine(g)
        pattern = PatternTemplate(name="empty")
        result = engine.match_pattern(pattern)
        assert result.total_match_count == 0

    def test_pattern_max_matches(self):
        g = Hypergraph()
        for i in range(10):
            g.add_node(Hypernode(id=f"n{i}", label=f"N{i}"))
            if i > 0:
                g.add_edge(Hyperedge(
                    source_ids=frozenset({f"n{i-1}"}),
                    target_ids=frozenset({f"n{i}"}),
                    label="next",
                ))
        engine = StructuralPatternEngine(g)
        pattern = PatternTemplate(
            name="chain",
            nodes=[PatternNode(role="s"), PatternNode(role="t")],
            edges=[PatternEdge(source_role="s", target_role="t", label="next")],
        )
        result = engine.match_pattern(pattern, max_matches=3)
        assert result.total_match_count <= 3

    def test_pattern_node_constraint_mismatch(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="alpha", data="string_data"))
        g.add_node(Hypernode(id="b", label="beta"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        engine = StructuralPatternEngine(g)
        pattern = PatternTemplate(
            name="typed",
            nodes=[
                PatternNode(role="s", data_type="dict"),
                PatternNode(role="t"),
            ],
            edges=[PatternEdge(source_role="s", target_role="t", label="rel")],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count == 0

    def test_pattern_label_pattern_mismatch(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="alpha"))
        g.add_node(Hypernode(id="b", label="beta"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        engine = StructuralPatternEngine(g)
        pattern = PatternTemplate(
            name="patterned",
            nodes=[
                PatternNode(role="s", label_pattern="^xyz_"),
                PatternNode(role="t"),
            ],
            edges=[PatternEdge(source_role="s", target_role="t", label="rel")],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count == 0

    def test_pattern_node_data_constraint(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="A", data={"role": "server"}))
        g.add_node(Hypernode(id="b", label="B", data={"role": "client"}))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="serves"))
        engine = StructuralPatternEngine(g)
        pattern = PatternTemplate(
            name="server_client",
            nodes=[
                PatternNode(role="s", constraints={"role": "server"}),
                PatternNode(role="c", constraints={"role": "client"}),
            ],
            edges=[PatternEdge(source_role="s", target_role="c", label="serves")],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 1


class TestMatchChainDeep:
    def test_chain_with_edge_label(self):
        g = Hypergraph()
        for lbl in "abcde":
            g.add_node(Hypernode(id=lbl, label=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="other"))
        engine = StructuralPatternEngine(g)
        chains = engine.match_chain(edge_label="next", min_length=2)
        assert len(chains) >= 1

    def test_chain_max_chains(self):
        g = Hypergraph()
        for i in range(20):
            g.add_node(Hypernode(id=f"n{i}", label=f"N{i}"))
            if i > 0:
                g.add_edge(Hyperedge(
                    source_ids=frozenset({f"n{i-1}"}),
                    target_ids=frozenset({f"n{i}"}),
                ))
        engine = StructuralPatternEngine(g)
        chains = engine.match_chain(min_length=1, max_chains=3)
        assert len(chains) <= 3


class TestMatchDiamondDeep:
    def test_diamond_with_edge_label(self):
        g = Hypergraph()
        for lbl in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=lbl, label=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"d"}), label="flow"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"d"}), label="flow"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="flow"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="flow"))
        engine = StructuralPatternEngine(g)
        diamonds = engine.match_diamond(edge_label="flow")
        assert len(diamonds) >= 1

    def test_diamond_no_matches(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        engine = StructuralPatternEngine(g)
        diamonds = engine.match_diamond()
        assert diamonds == []


class TestMatchFanOutDeep:
    def test_fan_out_with_edge_label(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="hub"))
        for i in range(5):
            n = Hypernode(id=f"s{i}", label=f"S{i}")
            g.add_node(n)
            g.add_edge(Hyperedge(
                source_ids=frozenset({"hub"}),
                target_ids=frozenset({f"s{i}"}),
                label="connects",
            ))
        engine = StructuralPatternEngine(g)
        fans = engine.match_fan_out(edge_label="connects", min_fan=3)
        assert len(fans) >= 1
        hub_id, targets = fans[0]
        assert hub_id == "hub"
        assert len(targets) >= 3


class TestStructuralMatchResultAccess:
    def test_result_dict_access(self):
        match = StructuralMatch(
            pattern_name="test",
            bindings={"a": "b"},
            score=0.9,
        )
        assert match["pattern_name"] == "test"
        assert match["score"] == 0.9
