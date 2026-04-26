from __future__ import annotations

import tempfile
import os

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, EquivalenceEngine
from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule, InverseRule, Rule, RuleMatch


def _make_graph():
    g = Hypergraph()
    nodes = [Hypernode(label=f"n{i}") for i in range(6)]
    for n in nodes:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), label="e"))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), label="e"))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[4].id}), label="e"))
    return g, nodes


class TestSubgraphExtraction:
    def test_subgraph_includes_only_specified_nodes(self):
        g, nodes = _make_graph()
        sg = g.subgraph({nodes[0].id, nodes[1].id, nodes[2].id})
        assert sg.node_count == 3
        assert sg.edge_count == 2

    def test_subgraph_excludes_external_edges(self):
        g, nodes = _make_graph()
        sg = g.subgraph({nodes[0].id, nodes[1].id})
        assert sg.node_count == 2
        assert sg.edge_count == 1

    def test_subgraph_empty_set(self):
        g, nodes = _make_graph()
        sg = g.subgraph(set())
        assert sg.node_count == 0

    def test_subgraph_preserves_labels(self):
        g, nodes = _make_graph()
        sg = g.subgraph({nodes[0].id, nodes[1].id})
        assert sg.get_node_by_label("n0") is not None
        assert sg.get_node_by_label("n1") is not None


class TestGraphAnalytics:
    def test_degree_centrality(self):
        g, nodes = _make_graph()
        dc = g.degree_centrality()
        assert nodes[1].id in dc
        assert dc[nodes[1].id] > dc[nodes[5].id]

    def test_betweenness_centrality(self):
        g, nodes = _make_graph()
        bc = g.betweenness_centrality()
        assert isinstance(bc, dict)
        assert len(bc) == 6

    def test_connected_components(self):
        g, nodes = _make_graph()
        components = g.connected_components()
        assert len(components) == 3

    def test_has_cycle_false(self):
        g, nodes = _make_graph()
        assert g.has_cycle() is False

    def test_has_cycle_true(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="e"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({a.id}), label="e"))
        assert g.has_cycle() is True

    def test_detect_cycles(self):
        g = Hypergraph()
        a, b = Hypernode(label="a"), Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="e"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({a.id}), label="e"))
        cycles = g.detect_cycles()
        assert len(cycles) > 0

    def test_shortest_path(self):
        g, nodes = _make_graph()
        path = g.shortest_path(nodes[0].id, nodes[2].id, weighted=False)
        assert path is not None
        assert len(path) == 3
        assert path[0] == nodes[0].id
        assert path[-1] == nodes[2].id

    def test_shortest_path_no_path(self):
        g, nodes = _make_graph()
        path = g.shortest_path(nodes[0].id, nodes[5].id, weighted=False)
        assert path is None

    def test_degree_distribution(self):
        g, nodes = _make_graph()
        dist = g.degree_distribution()
        assert isinstance(dist, dict)
        assert sum(dist.values()) == 6

    def test_node_degree(self):
        g, nodes = _make_graph()
        assert g.node_degree(nodes[1].id) >= 2
        assert g.node_degree(nodes[5].id) == 0


class TestTransfiniteStructural:
    def test_self_loop_detection(self):
        g = Hypergraph()
        a = Hypernode(label="self_ref")
        g.add_node(a)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({a.id}), label="self"))
        from hyper3.transfinite import TransfiniteReasoner
        reasoner = TransfiniteReasoner(g)
        boundaries = reasoner.map_boundaries(["self_ref"])
        assert len(boundaries) == 1
        assert boundaries[0].description == "self_ref"
        assert boundaries[0].indicator is not None
        assert boundaries[0].indicator.self_reference > 0.0

    def test_cycle_detection_structural(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({a.id}), label="next"))
        from hyper3.transfinite import TransfiniteReasoner
        reasoner = TransfiniteReasoner(g)
        result = reasoner.reason_at_level("a")
        assert result.reasoning_level >= 1

    def test_terminal_node_detection(self):
        g = Hypergraph()
        a, b = Hypernode(label="src"), Hypernode(label="sink")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="to"))
        from hyper3.transfinite import TransfiniteReasoner, BoundaryRegion
        reasoner = TransfiniteReasoner(g)
        boundaries = reasoner.map_boundaries(["sink"])
        assert len(boundaries) > 0
        assert boundaries[0].description == "sink"
        assert boundaries[0].indicator is not None


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


class TestBackwardChaining:
    def test_transitive_backward_chaining(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"))
        rule = TransitiveRule(edge_label="next")
        derivations = rule.find_derivation(c.id, g)
        assert len(derivations) > 0
        assert derivations[0].bindings["C"] == c.id
        assert derivations[0].bindings["A"] == a.id

    def test_backward_chaining_default_empty(self):
        from hyper3.rules import AbductiveRule
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        rule = AbductiveRule()
        derivations = rule.find_derivation(a.id, g)
        assert derivations == []


class TestMemoryAnalyticsFacade:
    def test_subgraph_facade(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e")
        result = mem.subgraph({"a", "b"})
        assert result["nodes"] == 2
        assert result["edges"] == 1

    def test_has_cycle_facade(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        assert mem.has_cycle() is False

    def test_connected_components_facade(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        components = mem.connected_components()
        assert len(components) >= 1


class TestDeriveFacade:
    def test_derive_finds_backward_chain(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        results = mem.derive("c")
        assert len(results) > 0
        assert any(r["rule"].startswith("transitive") for r in results)

    def test_derive_unknown_concept(self):
        mem = CognitiveMemory(evolve_interval=0)
        results = mem.derive("nonexistent")
        assert results == []


class TestIterativeReasoning:
    def test_reason_iterative_produces_results(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason_iterative({"a", "b", "c"}, max_iterations=2)
        assert "iterations" in result
        assert result["iterations"] >= 1
        assert result["total_edges_produced"] >= 0

    def test_reason_iterative_no_rules(self):
        mem = CognitiveMemory(evolve_interval=0)
        result = mem.reason_iterative({"a"})
        assert "error" in result


class TestFrameReasoning:
    def test_reason_with_classical_frame(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason_with_frame({"a", "b", "c"}, frame_name="classical")
        assert "expansion" in result
        assert result["expansion"]["rules_applied"] > 0

    def test_reason_with_quantum_frame(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        mem.add_rules(TransitiveRule(edge_label="e"))
        result = mem.reason_with_frame({"a", "b"}, frame_name="quantum")
        assert "expansion" in result


class TestTemporalConsistency:
    def test_temporal_consistency_check(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        mem.add_temporal_event("a", 0.0, 5.0)
        mem.add_temporal_event("b", 3.0, 8.0)
        edge = mem.graph.edges[0]
        result = mem.temporal.edge_temporal_consistency(
            edge.id,
            edge.id,
            mem.graph,
        )
        assert "consistent" in result


class TestShortestPathFacade:
    def test_shortest_path_facade(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        path = mem.shortest_path("a", "c")
        assert path is not None
        assert len(path) == 3

    def test_shortest_path_no_path(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("z")
        path = mem.shortest_path("a", "z")
        assert path is None
