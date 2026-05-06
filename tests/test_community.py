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
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="link")
        result = mem.detect_communities(seed=42)
        assert mem.communities is not None
        assert result.community_count >= 1


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
        assert [sorted(c.member_ids) for c in r1.communities] == [sorted(c.member_ids) for c in r2.communities]

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
        assert result.modularity >= 0

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
        assert len(all_members) == 6

    def test_modularity_bounds(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"N{i}")
        mem.relate("N0", "N1", label="x")
        mem.relate("N1", "N2", label="x")
        mem.relate("N3", "N4", label="x")
        mem.relate("N4", "N5", label="x")
        result = mem.detect_communities(seed=42)
        assert result.modularity > 0.0

    def test_coverage_less_than_one_with_cross_community_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"N{i}")
        for a in ["N0", "N1", "N2"]:
            for b in ["N0", "N1", "N2"]:
                if a != b:
                    mem.relate(a, b, label="x")
        for a in ["N3", "N4", "N5"]:
            for b in ["N3", "N4", "N5"]:
                if a != b:
                    mem.relate(a, b, label="x")
        mem.relate("N2", "N3", label="x")
        result = mem.detect_communities(seed=0)
        assert result.community_count >= 2
        assert result.coverage < 1.0

    def test_external_edges_count_cross_community(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "ABCDEF"}
        for n in nodes.values():
            g.add_node(n)
        for s, t in [("A", "B"), ("B", "C"), ("A", "C")]:
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[s].id}), target_ids=frozenset({nodes[t].id}), label="x"))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[t].id}), target_ids=frozenset({nodes[s].id}), label="x"))
        for s, t in [("D", "E"), ("E", "F"), ("D", "F")]:
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[s].id}), target_ids=frozenset({nodes[t].id}), label="x"))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[t].id}), target_ids=frozenset({nodes[s].id}), label="x"))
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 2
        total_external = sum(c.external_edges for c in result.communities)
        assert total_external == 0
        assert all(c.external_edges == 0 for c in result.communities)
        assert all(c.internal_edges > 0 for c in result.communities)


class TestLouvain:
    def _build_two_clusters_with_bridge(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcdef"}
        for n in nodes.values():
            g.add_node(n)
        for s, t in [("a", "b"), ("b", "c"), ("a", "c"), ("d", "e"), ("e", "f"), ("d", "f")]:
            g.add_edge(
                Hyperedge(
                    source_ids=frozenset({nodes[s].id}),
                    target_ids=frozenset({nodes[t].id}),
                )
            )
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["c"].id}),
                target_ids=frozenset({nodes["d"].id}),
            )
        )
        return g, nodes

    def test_louvain_basic(self):
        g, _ = self._build_two_clusters_with_bridge()
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 2
        assert abs(result.modularity - 0.3571) < 0.01

    def test_louvain_seed_reproducibility(self):
        g, _ = self._build_two_clusters_with_bridge()
        det = CommunityDetector(g)
        r1 = det.detect_louvain(seed=123)
        det2 = CommunityDetector(g)
        r2 = det2.detect_louvain(seed=123)
        assert r1.community_count == r2.community_count
        assert [sorted(c.member_ids) for c in r1.communities] == [
            sorted(c.member_ids) for c in r2.communities
        ]

    def test_louvain_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="x"))
        det = CommunityDetector(g)
        result = det.detect_louvain()
        assert result.community_count == 1

    def test_louvain_empty_graph(self):
        g = Hypergraph()
        det = CommunityDetector(g)
        result = det.detect_louvain()
        assert result.community_count == 0

    def test_louvain_disconnected(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcd"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["a"].id}),
                target_ids=frozenset({nodes["b"].id}),
            )
        )
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["c"].id}),
                target_ids=frozenset({nodes["d"].id}),
            )
        )
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 2

    def test_louvain_clique(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcd"}
        for n in nodes.values():
            g.add_node(n)
        for s in "abcd":
            for t in "abcd":
                if s < t:
                    g.add_edge(
                        Hyperedge(
                            source_ids=frozenset({nodes[s].id}),
                            target_ids=frozenset({nodes[t].id}),
                        )
                    )
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 1
        assert abs(result.modularity) < 0.01

    def test_louvain_edge_label_filter(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcd"}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["a"].id}),
                target_ids=frozenset({nodes["b"].id}),
                label="keep",
            )
        )
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["c"].id}),
                target_ids=frozenset({nodes["d"].id}),
                label="keep",
            )
        )
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["b"].id}),
                target_ids=frozenset({nodes["c"].id}),
                label="ignore",
            )
        )
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42, edge_label="keep")
        assert result.community_count == 2

    def test_louvain_weighted(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in "abcde"}
        for n in nodes.values():
            g.add_node(n)
        for s, t, w in [("a", "b", 10.0), ("b", "c", 10.0), ("a", "c", 10.0)]:
            g.add_edge(
                Hyperedge(
                    source_ids=frozenset({nodes[s].id}),
                    target_ids=frozenset({nodes[t].id}),
                    weight=w,
                )
            )
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["c"].id}),
                target_ids=frozenset({nodes["d"].id}),
                weight=0.1,
            )
        )
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes["d"].id}),
                target_ids=frozenset({nodes["e"].id}),
                weight=10.0),
        )
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count >= 2

    def test_louvain_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"n{i}")
        for s, t in [("n0", "n1"), ("n1", "n2"), ("n0", "n2"), ("n3", "n4"), ("n4", "n5"), ("n3", "n5")]:
            mem.relate(s, t)
        mem.relate("n2", "n3")
        result = mem.detect_communities(method="louvain", seed=42)
        assert result.community_count == 2
        assert abs(result.modularity - 0.3571) < 0.01

    def test_louvain_isolated_nodes(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 2

    def test_louvain_single_edge(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({a.id}),
                target_ids=frozenset({b.id}),
            )
        )
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 1
