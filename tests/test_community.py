from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory
from hyper3.community import CommunityDetector
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


class TestCommunityBasic:
    def test_detect_communities(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="connects")
        mem.link("B", "C", label="connects")
        result = mem.analyze.communities(seed=42)
        assert result.community_count == 1
        assert result.coverage == 1.0

    def test_detect_communities_empty_graph(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.analyze.communities()
        assert result.community_count == 0
        assert result.modularity == 0.0

    def test_detect_communities_disconnected(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.add("D")
        mem.link("A", "B", label="group1")
        mem.link("C", "D", label="group2")
        result = mem.analyze.communities(method="connected_components")
        assert result.community_count == 2

    def test_weighted_propagation(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        e1 = mem.link("A", "B", label="strong")
        e2 = mem.link("B", "C", label="weak")
        e1.weight = 10.0
        e2.weight = 0.1
        result = mem.analyze.communities(method="weighted_label_propagation", seed=42)
        assert result.community_count == 1

    def test_community_labels(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("alpha")
        mem.add("beta")
        mem.link("alpha", "beta", label="link")
        result = mem.analyze.communities(seed=42)
        assert result.community_count == 1
        assert set(result.communities[0].member_labels) == {"alpha", "beta"}

    def test_modularity(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"N{i}")
        for i in range(9):
            mem.link(f"N{i}", f"N{i+1}", label="link")
        result = mem.analyze.communities(seed=42)
        assert abs(result.modularity - 0.3889) < 0.01

    def test_communities_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.engine.community is None
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="link")
        result = mem.analyze.communities(seed=42)
        assert mem.engine.community is not None
        assert result.community_count >= 1


class TestCommunityDetector:
    def test_with_edge_label_filter(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="type1")
        mem.link("B", "C", label="type2")
        detector = CommunityDetector(mem.graph)
        result = detector.detect_label_propagation(edge_label="type1", seed=42)
        assert result.community_count == 2

    def test_reproducible_with_seed(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"N{i}")
            if i > 0:
                mem.link(f"N{i-1}", f"N{i}", label="link")
        detector = CommunityDetector(mem.graph)
        r1 = detector.detect_label_propagation(seed=123)
        detector2 = CommunityDetector(mem.graph)
        r2 = detector2.detect_label_propagation(seed=123)
        assert r1.community_count == r2.community_count
        assert [sorted(c.member_ids) for c in r1.communities] == [sorted(c.member_ids) for c in r2.communities]

    def test_coverage_is_one_for_connected(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="link")
        result = mem.analyze.communities(seed=42)
        assert result.coverage == 1.0

    def test_avg_community_size(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.add(f"N{i}")
        mem.link("N0", "N1", label="link")
        mem.link("N2", "N3", label="link")
        mem.link("N4", "N5", label="link")
        result = mem.analyze.communities(method="connected_components")
        assert result.avg_community_size == 2.0
        assert result.community_count == 3

    def test_weighted_fallback_on_negative_modularity(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"N{i}")
        for i in range(9):
            e = mem.link(f"N{i}", f"N{i+1}", label="link")
            e.weight = 0.1 + i * 0.5
        detector = CommunityDetector(mem.graph)
        result = detector.detect_label_propagation(seed=42, weighted_fallback=True)
        assert result.community_count >= 1
        assert result.modularity >= 0

    def test_weighted_fallback_disabled(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"N{i}")
        for i in range(9):
            mem.link(f"N{i}", f"N{i+1}", label="link")
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
        mem.add("X")
        mem.add("Y")
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
            mem.add(f"N{i}")
        mem.link("N0", "N1", label="x")
        mem.link("N1", "N2", label="x")
        mem.link("N3", "N4", label="x")
        mem.link("N4", "N5", label="x")
        result = mem.analyze.communities(seed=42)
        all_members = []
        for c in result.communities:
            all_members.extend(c.member_ids)
        assert len(all_members) == len(set(all_members))
        assert len(all_members) == 6

    def test_modularity_bounds(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.add(f"N{i}")
        mem.link("N0", "N1", label="x")
        mem.link("N1", "N2", label="x")
        mem.link("N3", "N4", label="x")
        mem.link("N4", "N5", label="x")
        result = mem.analyze.communities(seed=42)
        assert result.modularity > 0.0

    def test_coverage_less_than_one_with_cross_community_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.add(f"N{i}")
        for a in ["N0", "N1", "N2"]:
            for b in ["N0", "N1", "N2"]:
                if a != b:
                    mem.link(a, b, label="x")
        for a in ["N3", "N4", "N5"]:
            for b in ["N3", "N4", "N5"]:
                if a != b:
                    mem.link(a, b, label="x")
        mem.link("N2", "N3", label="x")
        result = mem.analyze.communities(seed=0)
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


def _make_nary_edge(
    graph: Hypergraph,
    sources: list[str],
    targets: list[str],
    label: str = "e",
    weight: float = 1.0,
    ids: dict[str, str] | None = None,
) -> dict[str, str]:
    """Add an n-ary edge, reusing existing nodes when ids dict provides them."""
    label_to_id = dict(ids) if ids else {}
    for lbl in set(sources) | set(targets):
        if lbl in label_to_id:
            continue
        node = Hypernode(label=lbl)
        graph.add_node(node)
        label_to_id[lbl] = node.id
    graph.add_edge(
        Hyperedge(
            source_ids=frozenset({label_to_id[s] for s in sources}),
            target_ids=frozenset({label_to_id[t] for t in targets}),
            label=label,
            weight=weight,
        )
    )
    return label_to_id


class TestPolyadicNeighborMap:
    def test_nary_edge_creates_bidirectional_neighbors(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["C", "D"])
        det = CommunityDetector(g)
        nmap = det._build_neighbor_map(None)
        assert ids["C"] in [nb for nb, _w in nmap[ids["A"]]]
        assert ids["D"] in [nb for nb, _w in nmap[ids["A"]]]
        assert ids["A"] in [nb for nb, _w in nmap[ids["C"]]]
        assert ids["B"] in [nb for nb, _w in nmap[ids["C"]]]

    def test_nary_edge_no_self_neighbor(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["B", "C"])
        det = CommunityDetector(g)
        nmap = det._build_neighbor_map(None)
        neighbor_ids = [nb for nb, _w in nmap.get(ids["B"], [])]
        assert ids["B"] not in neighbor_ids

    def test_nary_edge_weight_propagated(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A"], ["B", "C"], weight=5.0)
        det = CommunityDetector(g)
        nmap = det._build_neighbor_map(None)
        weights_for_b = [w for nb, w in nmap[ids["A"]] if nb == ids["B"]]
        assert weights_for_b == [5.0]

    def test_nary_3source_edge_neighbors(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B", "C"], ["D"])
        det = CommunityDetector(g)
        nmap = det._build_neighbor_map(None)
        assert len(nmap[ids["A"]]) == 1
        assert len(nmap[ids["D"]]) == 3
        assert ids["D"] in [nb for nb, _w in nmap[ids["A"]]]


class TestPolyadicConnectedComponents:
    def test_nary_edge_unifies_all_participants(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B"], ["C", "D"])
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 1
        assert result.communities[0].size == 4

    def test_two_nary_edges_two_components(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B"], ["C"], label="g1")
        _make_nary_edge(g, ["D", "E"], ["F"], label="g2")
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 2
        assert all(c.size == 3 for c in result.communities)

    def test_nary_bridge_unifies_two_groups(self) -> None:
        g = Hypergraph()
        ids1 = _make_nary_edge(g, ["A", "B"], ["C"], label="left")
        ids2 = _make_nary_edge(g, ["D", "E"], ["F"], label="right")
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({ids1["C"]}),
                target_ids=frozenset({ids2["D"]}),
                label="bridge",
            )
        )
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 1
        assert result.communities[0].size == 6

    def test_nary_5source_all_connected(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B", "C", "D"], ["E"])
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 1
        assert result.communities[0].size == 5


class TestPolyadicLabelPropagation:
    def test_nary_edge_single_community(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B"], ["C", "D"])
        det = CommunityDetector(g)
        result = det.detect_label_propagation(seed=42)
        assert result.community_count == 1
        assert result.communities[0].size == 4

    def test_nary_edges_two_clusters(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B"], ["C"], label="cluster1")
        _make_nary_edge(g, ["D", "E"], ["F"], label="cluster2")
        det = CommunityDetector(g)
        result = det.detect_label_propagation(seed=42)
        assert result.community_count == 2
        sizes = sorted(c.size for c in result.communities)
        assert sizes == [3, 3]

    def test_weighted_nary_propagation(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["C", "D"], weight=10.0, label="strong")
        ids = _make_nary_edge(g, ["D", "E"], ["F"], weight=0.1, label="weak", ids=ids)
        det = CommunityDetector(g)
        result = det.detect_weighted_label_propagation(seed=42)
        assert result.community_count >= 1
        all_members = set()
        for c in result.communities:
            all_members.update(c.member_ids)
        assert len(all_members) == 6

    def test_nary_community_labels_are_human_readable(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["alpha", "beta"], ["gamma"])
        det = CommunityDetector(g)
        result = det.detect_label_propagation(seed=42)
        assert result.community_count == 1
        assert set(result.communities[0].member_labels) == {"alpha", "beta", "gamma"}


class TestPolyadicLouvain:
    def test_nary_single_cluster(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B"], ["C", "D"])
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 1
        assert result.communities[0].size == 4

    def test_nary_two_clusters_with_bridge(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["C"], label="left")
        _make_nary_edge(g, ["A", "B"], ["C"], label="left_internal", ids=ids)
        ids = _make_nary_edge(g, ["D", "E"], ["F"], label="right", ids=ids)
        _make_nary_edge(g, ["D", "E"], ["F"], label="right_internal", ids=ids)
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({ids["C"]}),
                target_ids=frozenset({ids["D"]}),
                label="bridge",
            )
        )
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 2
        assert result.modularity == pytest.approx(0.3, abs=1e-3)
        all_members: set[str] = set()
        for c in result.communities:
            all_members.update(c.member_ids)
        assert len(all_members) == 6

    def test_nary_weighted_louvain(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["C"], weight=10.0, label="strong")
        ids = _make_nary_edge(g, ["D", "E"], ["F"], weight=10.0, label="strong2", ids=ids)
        _make_nary_edge(g, ["C", "D"], ["X"], weight=0.01, label="weak_bridge", ids=ids)
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.community_count == 2
        assert result.modularity == pytest.approx(0.4998, abs=1e-3)

    def test_nary_louvain_edge_label_filter(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["C"], label="keep")
        ids = _make_nary_edge(g, ["D", "E"], ["F"], label="keep", ids=ids)
        _make_nary_edge(g, ["C", "D"], ["X"], label="ignore", ids=ids)
        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42, edge_label="keep")
        assert result.community_count == 3


class TestPolyadicModularity:
    def test_nary_tight_cluster_positive_modularity(self) -> None:
        g = Hypergraph()
        for _ in range(3):
            _make_nary_edge(g, ["A", "B"], ["C"], label="internal")
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.modularity > 0.0

    def test_nary_internal_external_edge_counts(self) -> None:
        g = Hypergraph()
        ids1 = _make_nary_edge(g, ["A", "B"], ["C"], label="g1")
        ids2 = _make_nary_edge(g, ["D", "E"], ["F"], label="g2")
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({ids1["C"]}),
                target_ids=frozenset({ids2["D"]}),
                label="cross",
            )
        )
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 1

    def test_nary_disjoint_zero_external(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B"], ["C"], label="g1")
        _make_nary_edge(g, ["D", "E"], ["F"], label="g2")
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 2
        assert all(c.external_edges == 0 for c in result.communities)
        assert all(c.internal_edges > 0 for c in result.communities)


class TestPolyadicGirvanNewman:
    def test_nary_two_clusters(self) -> None:
        g = Hypergraph()
        ids1 = _make_nary_edge(g, ["A", "B"], ["C"])
        ids2 = _make_nary_edge(g, ["D", "E"], ["F"])
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({ids1["C"]}),
                target_ids=frozenset({ids2["D"]}),
                label="bridge",
            )
        )
        det = CommunityDetector(g)
        result = det.detect_girvan_newman(n_communities=2)
        assert result.community_count == 2
        all_members: set[str] = set()
        for c in result.communities:
            all_members.update(c.member_ids)
        assert len(all_members) == 6

    def test_nary_single_component(self) -> None:
        g = Hypergraph()
        _make_nary_edge(g, ["A", "B", "C"], ["D"])
        det = CommunityDetector(g)
        result = det.detect_girvan_newman(n_communities=2)
        assert result.community_count == 2


class TestPolyadicMixed:
    def test_nary_plus_dyadic_combined(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["C"], label="nary")
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({ids["C"]}),
                target_ids=frozenset({ids["A"]}),
                label="dyadic",
            )
        )
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 1
        assert result.communities[0].size == 3

    def test_nary_facade_via_memory(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("svc-a")
        mem.add("svc-b")
        mem.add("svc-c")
        mem.link_hyper(sources={"svc-a", "svc-b"}, targets={"svc-c"}, label="joint")
        result = mem.analyze.communities(method="connected_components")
        assert result.community_count == 1
        assert result.communities[0].size == 3

    def test_multiple_nary_edges_coverage(self) -> None:
        g = Hypergraph()
        ids = _make_nary_edge(g, ["A", "B"], ["C", "D"], label="e1")
        ids = _make_nary_edge(g, ["A", "C"], ["E"], label="e2", ids=ids)
        det = CommunityDetector(g)
        result = det.detect_connected_components()
        assert result.community_count == 1
        assert result.coverage == 1.0


class TestGirvanNewman:
    def _build_graph(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(8)]
        for n in nodes:
            g.add_node(n)
        pairs = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(3,4)]
        for i, j in pairs:
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id, nodes[j].id}), target_ids=frozenset()))
        return g, nodes

    def test_two_communities(self):
        g, nodes = self._build_graph()
        det = CommunityDetector(g)
        result = det.detect_girvan_newman(n_communities=2)
        assert result.community_count == 2
        all_members = set()
        for c in result.communities:
            all_members.update(c.member_ids)
        assert len(all_members) == 8

    def test_single_component(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(3)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        det = CommunityDetector(g)
        result = det.detect_girvan_newman(n_communities=2)
        assert result.community_count == 2

    def test_empty(self):
        g = Hypergraph()
        det = CommunityDetector(g)
        result = det.detect_girvan_newman()
        assert result.community_count == 0

    def test_disconnected(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(4)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        det = CommunityDetector(g)
        result = det.detect_girvan_newman(n_communities=2)
        assert result.community_count == 2


class TestHyperlinkCommunities:
    def test_basic(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(6)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id, nodes[3].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id, nodes[4].id, nodes[5].id}), target_ids=frozenset()))
        det = CommunityDetector(g)
        result = det.detect_hyperlink_communities()
        assert result.community_count == 2
        assert len(result.dendrogram) == 2
        assert len(result.edge_labels) == 3

    def test_cut_height(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(6)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id, nodes[4].id}), target_ids=frozenset()))
        det = CommunityDetector(g)
        result = det.detect_hyperlink_communities(cut_height=0.5)
        assert result.community_count == 3

    def test_n_communities(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(6)]
        for n in nodes:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id, nodes[4].id, nodes[5].id}), target_ids=frozenset()))
        det = CommunityDetector(g)
        result = det.detect_hyperlink_communities(n_communities=2)
        assert result.community_count == 2

    def test_empty(self):
        g = Hypergraph()
        det = CommunityDetector(g)
        result = det.detect_hyperlink_communities()
        assert result.community_count == 0


class TestLouvainExtended:
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
            mem.add(f"n{i}")
        for s, t in [("n0", "n1"), ("n1", "n2"), ("n0", "n2"), ("n3", "n4"), ("n4", "n5"), ("n3", "n5")]:
            mem.link(s, t)
        mem.link("n2", "n3")
        result = mem.analyze.communities(method="louvain", seed=42)
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
