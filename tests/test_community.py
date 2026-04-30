from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory
from hyper3.community import CommunityDetector
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


class TestCommunityBasic:
    def test_detect_communities(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="connects")
        mem.relate("B", "C", label="connects")
        result = mem.detect_communities(seed=42)
        assert result.community_count == 1
        assert result.coverage == 1.0

    def test_detect_communities_empty_graph(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.detect_communities()
        assert result.community_count == 0
        assert result.modularity == 0.0

    def test_detect_communities_disconnected(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.store("D")
        mem.relate("A", "B", label="group1")
        mem.relate("C", "D", label="group2")
        result = mem.detect_communities(method="connected_components")
        assert result.community_count == 2

    def test_weighted_propagation(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        e1 = mem.relate("A", "B", label="strong")
        e2 = mem.relate("B", "C", label="weak")
        e1.weight = 10.0
        e2.weight = 0.1
        result = mem.detect_communities(method="weighted_label_propagation", seed=42)
        assert result.community_count == 1

    def test_community_labels(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("alpha")
        mem.store("beta")
        mem.relate("alpha", "beta", label="link")
        result = mem.detect_communities(seed=42)
        assert result.community_count == 1
        assert set(result.communities[0].member_labels) == {"alpha", "beta"}

    def test_modularity(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"N{i}")
        for i in range(9):
            mem.relate(f"N{i}", f"N{i+1}", label="link")
        result = mem.detect_communities(seed=42)
        assert abs(result.modularity - 0.3889) < 0.01

    def test_communities_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.communities is None
        mem.detect_communities()
        assert mem.communities is not None


class TestCommunityDetector:
    def test_with_edge_label_filter(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="type1")
        mem.relate("B", "C", label="type2")
        detector = CommunityDetector(mem.graph)
        result = detector.detect_label_propagation(edge_label="type1", seed=42)
        assert result.community_count == 2

    def test_reproducible_with_seed(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"N{i}")
            if i > 0:
                mem.relate(f"N{i-1}", f"N{i}", label="link")
        detector = CommunityDetector(mem.graph)
        r1 = detector.detect_label_propagation(seed=123)
        detector2 = CommunityDetector(mem.graph)
        r2 = detector2.detect_label_propagation(seed=123)
        assert r1.community_count == r2.community_count

    def test_coverage_is_one_for_connected(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="link")
        result = mem.detect_communities(seed=42)
        assert result.coverage == 1.0

    def test_avg_community_size(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"N{i}")
        mem.relate("N0", "N1", label="link")
        mem.relate("N2", "N3", label="link")
        mem.relate("N4", "N5", label="link")
        result = mem.detect_communities(method="connected_components")
        assert result.avg_community_size == 2.0
        assert result.community_count == 3

    def test_weighted_fallback_on_negative_modularity(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"N{i}")
        for i in range(9):
            e = mem.relate(f"N{i}", f"N{i+1}", label="link")
            e.weight = 0.1 + i * 0.5
        detector = CommunityDetector(mem.graph)
        result = detector.detect_label_propagation(seed=42, weighted_fallback=True)
        assert result.community_count >= 1

    def test_weighted_fallback_disabled(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"N{i}")
        for i in range(9):
            mem.relate(f"N{i}", f"N{i+1}", label="link")
        detector = CommunityDetector(mem.graph)
        unweighted = detector.detect_label_propagation(seed=42, weighted_fallback=False)
        with_fallback = detector.detect_label_propagation(seed=42, weighted_fallback=True)
        assert with_fallback.modularity >= unweighted.modularity


class TestCommunityEdgeCases:
    def test_weighted_empty_graph(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        detector = CommunityDetector(mem.graph)
        result = detector.detect_weighted_label_propagation(seed=42)
        assert result.community_count == 0

    def test_isolated_nodes_zero_edges(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("X")
        mem.store("Y")
        detector = CommunityDetector(mem.graph)
        result = detector.detect_label_propagation(seed=42)
        assert result.community_count == 2
        assert result.modularity == 0.0

    def test_connected_components_empty(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        detector = CommunityDetector(mem.graph)
        result = detector.detect_connected_components()
        assert result.community_count == 0


class TestSemanticCommunity:
    def test_communities_are_disjoint(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"N{i}")
        mem.relate("N0", "N1", label="x")
        mem.relate("N1", "N2", label="x")
        mem.relate("N3", "N4", label="x")
        mem.relate("N4", "N5", label="x")
        result = mem.detect_communities(seed=42)
        all_members = []
        for c in result.communities:
            all_members.extend(c.member_ids)
        assert len(all_members) == len(set(all_members))

    def test_modularity_bounds(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"N{i}")
        mem.relate("N0", "N1", label="x")
        mem.relate("N1", "N2", label="x")
        mem.relate("N3", "N4", label="x")
        mem.relate("N4", "N5", label="x")
        result = mem.detect_communities(seed=42)
        assert -0.5 <= result.modularity <= 1.0

    def test_coverage_less_than_one_with_cross_community_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"N{i}")
        mem.relate("N0", "N1", label="x")
        mem.relate("N1", "N2", label="x")
        mem.relate("N2", "N3", label="x")
        mem.relate("N3", "N4", label="x")
        mem.relate("N4", "N5", label="x")
        result = mem.detect_communities(seed=42)
        if result.community_count > 1:
            assert result.coverage < 1.0

    def test_external_edges_count_cross_community(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "ABCDEF"}
        for n in nodes.values():
            g.add_node(n)
        for s, t in [("A", "B"), ("B", "C"), ("A", "C")]:
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[s].id}), target_ids=frozenset({nodes[t].id}), label="x"))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[t].id}), target_ids=frozenset({nodes[s].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["C"].id}), target_ids=frozenset({nodes["D"].id}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["D"].id}), target_ids=frozenset({nodes["C"].id}), label="x"))
        for s, t in [("D", "E"), ("E", "F"), ("D", "F")]:
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[s].id}), target_ids=frozenset({nodes[t].id}), label="x"))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[t].id}), target_ids=frozenset({nodes[s].id}), label="x"))
        det = CommunityDetector(g)
        result = det.detect_label_propagation()
        total_external = sum(c.external_edges for c in result.communities)
        assert total_external >= 2
