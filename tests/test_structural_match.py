from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.structural_match import (
    PatternEdge,
    PatternNode,
    PatternTemplate,
    StructuralMatch,
    StructuralPatternEngine,
)


class TestStructuralMatchBasic:
    def test_match_chain(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="next")
        mem.relate("B", "C", label="next")
        chains = mem.match_chains(edge_label="next", min_length=2)
        assert len(chains) >= 1
        assert len(chains[0]) >= 3

    def test_match_chain_empty_graph(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        chains = mem.match_chains()
        assert chains == []

    def test_match_diamond(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "C", label="feeds")
        mem.relate("B", "C", label="feeds")
        diamonds = mem.match_diamonds()
        assert len(diamonds) >= 1

    def test_match_fan_out(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("hub")
        for i in range(5):
            mem.store(f"spoke_{i}")
            mem.relate("hub", f"spoke_{i}", label="connects")
        fans = mem.match_fan_out(min_fan=3)
        assert len(fans) >= 1
        assert fans[0]["fan_out"] >= 3

    def test_match_structural_pattern(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="depends_on")
        result = mem.match_structural_pattern(
            nodes=[{"role": "source"}, {"role": "target"}],
            edges=[{"source_role": "source", "target_role": "target", "label": "depends_on"}],
        )
        assert result.total_match_count >= 1

    def test_match_structural_pattern_no_match(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="connects")
        result = mem.match_structural_pattern(
            edges=[{"source_role": "x", "target_role": "y", "label": "nonexistent"}],
        )
        assert result.total_match_count == 0


class TestStructuralPatternEngine:
    def test_match_pattern_with_weight_filter(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="strong")
        edge.weight = 5.0
        engine = StructuralPatternEngine(mem.graph)
        pattern = PatternTemplate(
            name="strong_edge",
            nodes=[PatternNode(role="src"), PatternNode(role="tgt")],
            edges=[PatternEdge(source_role="src", target_role="tgt", label="strong", min_weight=3.0)],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 1

    def test_match_pattern_with_data_type_constraint(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A", data={"type": "person"})
        mem.store("B", data={"type": "place"})
        mem.relate("A", "B", label="lives_in")
        engine = StructuralPatternEngine(mem.graph)
        pattern = PatternTemplate(
            name="typed",
            nodes=[
                PatternNode(role="person", data_type="dict"),
                PatternNode(role="place"),
            ],
            edges=[PatternEdge(source_role="person", target_role="place", label="lives_in")],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 1

    def test_match_pattern_with_label_pattern(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("svc_auth")
        mem.store("svc_orders")
        mem.relate("svc_auth", "svc_orders", label="calls")
        engine = StructuralPatternEngine(mem.graph)
        pattern = PatternTemplate(
            name="service_call",
            nodes=[
                PatternNode(role="caller", label_pattern="^svc_"),
                PatternNode(role="callee", label_pattern="^svc_"),
            ],
            edges=[PatternEdge(source_role="caller", target_role="callee", label="calls")],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 1

    def test_fan_out_no_results(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        engine = StructuralPatternEngine(mem.graph)
        result = engine.match_fan_out(min_fan=10)
        assert result == []

    def test_structural_matcher_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.structural_matcher is None
        mem.match_chains()
        assert mem.structural_matcher is not None


class TestStructuralMatchIntegration:
    def test_complex_pattern(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("client")
        mem.store("gateway")
        mem.store("service")
        mem.store("db")
        mem.relate("client", "gateway", label="calls")
        mem.relate("gateway", "service", label="routes_to")
        mem.relate("service", "db", label="queries")
        result = mem.match_structural_pattern(
            pattern_name="three_tier",
            nodes=[{"role": "front"}, {"role": "mid"}, {"role": "back"}],
            edges=[
                {"source_role": "front", "target_role": "mid", "label": "calls"},
                {"source_role": "mid", "target_role": "back", "label": "routes_to"},
            ],
        )
        assert result.total_match_count >= 1






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
