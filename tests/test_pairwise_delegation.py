from __future__ import annotations

import networkx as nx
import pytest

from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hyperedge, Hypernode


def _build_cycle(n: int = 6) -> tuple[Hypergraph, list[Hypernode]]:
    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(n)]
    for nd in nodes:
        g.add_node(nd)
    for i in range(n):
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[i].id}),
                target_ids=frozenset({nodes[(i + 1) % n].id}),
            )
        )
    return g, nodes


def _build_path(n: int = 5) -> tuple[Hypergraph, list[Hypernode]]:
    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(n)]
    for nd in nodes:
        g.add_node(nd)
    for i in range(n - 1):
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[i].id}),
                target_ids=frozenset({nodes[i + 1].id}),
            )
        )
    return g, nodes


def _build_with_data(n: int = 4, attr: str = "val") -> tuple[Hypergraph, list[Hypernode]]:
    g = Hypergraph()
    nodes = [Hypernode(label=str(i), data={attr: float(i)}) for i in range(n)]
    for nd in nodes:
        g.add_node(nd)
    for i in range(n - 1):
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[i].id}),
                target_ids=frozenset({nodes[i + 1].id}),
            )
        )
    return g, nodes


class TestCentralityDelegation:

    def test_harmonic_centrality_returns_all_nodes(self):
        g, nodes = _build_cycle()
        result = g.harmonic_centrality()
        assert len(result) == 6
        assert all(isinstance(v, float) for v in result.values())
        for nd in nodes:
            assert nd.id in result

    def test_harmonic_centrality_single_node(self):
        g, nodes = _build_cycle()
        result = g.harmonic_centrality(source=nodes[0].id)
        assert nodes[0].id in result
        assert len(result) == 1

    def test_harmonic_centrality_matches_nx(self):
        g, nodes = _build_cycle()
        result = g.harmonic_centrality()
        G = nx.Graph()
        G.add_edges_from([(str(i), str((i + 1) % 6)) for i in range(6)])
        nx_result = nx.harmonic_centrality(G)
        id_to_label = {nd.id: nd.label for nd in nodes}
        for nd in nodes:
            label = id_to_label[nd.id]
            assert abs(result[nd.id] - nx_result[label]) < 1e-6

    def test_information_centrality_returns_all_nodes(self):
        g, nodes = _build_cycle()
        result = g.information_centrality()
        assert len(result) == 6

    def test_load_centrality_returns_all_nodes(self):
        g, nodes = _build_cycle()
        result = g.load_centrality()
        assert len(result) == 6

    def test_current_flow_betweenness_centrality(self):
        g, nodes = _build_cycle()
        result = g.current_flow_betweenness_centrality()
        assert len(result) == 6
        assert all(0 <= v <= 1 for v in result.values())

    def test_current_flow_closeness_centrality(self):
        g, nodes = _build_cycle()
        result = g.current_flow_closeness_centrality()
        assert len(result) == 6

    def test_approximate_current_flow_betweenness(self):
        g, nodes = _build_cycle()
        result = g.approximate_current_flow_betweenness_centrality(seed=42)
        assert len(result) == 6

    def test_percolation_centrality(self):
        g, nodes = _build_with_data(4, "risk")
        result = g.percolation_centrality("risk")
        assert len(result) == 4

    def test_percolation_centrality_missing_attribute(self):
        g, nodes = _build_cycle()
        result = g.percolation_centrality("nonexistent")
        assert len(result) == 6

    def test_voterank(self):
        g, nodes = _build_cycle()
        result = g.voterank()
        assert isinstance(result, list)
        assert all(nid in {nd.id for nd in nodes} for nid in result)

    def test_voterank_with_limit(self):
        g, nodes = _build_cycle()
        result = g.voterank(number_of_nodes=2)
        assert len(result) <= 2

    def test_empty_graph_centrality(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="a"))
        h = g.harmonic_centrality()
        assert len(h) == 1
        assert list(h.values())[0] == 0.0
        assert len(g.load_centrality()) == 1


class TestQueryDelegation:

    def test_wiener_index(self):
        g, nodes = _build_path()
        result = g.wiener_index()
        assert isinstance(result, float)
        assert result > 0

    def test_wiener_index_matches_nx(self):
        g, nodes = _build_path(5)
        result = g.wiener_index()
        G = nx.path_graph(5)
        assert abs(result - nx.wiener_index(G)) < 1e-6

    def test_s_metric(self):
        g, nodes = _build_cycle()
        result = g.s_metric()
        assert isinstance(result, float)

    def test_node_connectivity(self):
        g, nodes = _build_cycle()
        result = g.node_connectivity()
        assert isinstance(result, int)
        assert result >= 1

    def test_edge_connectivity(self):
        g, nodes = _build_cycle()
        result = g.edge_connectivity()
        assert isinstance(result, int)
        assert result >= 1

    def test_rich_club_coefficient(self):
        g, nodes = _build_cycle()
        result = g.rich_club_coefficient()
        assert isinstance(result, dict)
        assert all(isinstance(k, int) for k in result)

    def test_onion_layers(self):
        g, nodes = _build_cycle()
        result = g.onion_layers()
        assert len(result) == 6
        assert all(isinstance(v, int) for v in result.values())


class TestEulerianDelegation:

    def test_cycle_is_eulerian(self):
        g, nodes = _build_cycle()
        assert g.is_eulerian() is True

    def test_path_is_not_eulerian(self):
        g, nodes = _build_path()
        assert g.is_eulerian() is False

    def test_path_has_eulerian_path(self):
        g, nodes = _build_path()
        assert g.has_eulerian_path() is True

    def test_eulerian_circuit_cycle(self):
        g, nodes = _build_cycle()
        circuit = g.eulerian_circuit()
        assert isinstance(circuit, list)
        assert len(circuit) == 6

    def test_eulerian_circuit_non_eulerian(self):
        g, nodes = _build_path()
        with pytest.raises(nx.NetworkXError):
            g.eulerian_circuit()


class TestSimilarityDelegation:

    def test_simrank_similarity(self):
        g, nodes = _build_cycle()
        result = g.simrank_similarity()
        assert len(result) == 6
        for nid in nodes:
            assert nid.id in result
            assert abs(result[nid.id][nid.id] - 1.0) < 1e-6

    def test_simrank_similarity_source(self):
        g, nodes = _build_cycle()
        result = g.simrank_similarity(source=nodes[0].id)
        assert len(result) == 6

    def test_panther_similarity(self):
        g, nodes = _build_cycle()
        result = g.panther_similarity(nodes[0].id, seed=42)
        assert len(result) > 0


class TestIsomorphismDelegation:

    def test_self_isomorphic(self):
        g, _ = _build_cycle()
        assert g.is_isomorphic(g) is True

    def test_same_structure_isomorphic(self):
        g1, _ = _build_cycle(4)
        g2, _ = _build_cycle(4)
        assert g1.is_isomorphic(g2) is True

    def test_different_structure_not_isomorphic(self):
        g1, _ = _build_cycle(4)
        g2, _ = _build_path(4)
        assert g1.is_isomorphic(g2) is False

    def test_could_be_isomorphic(self):
        g1, _ = _build_cycle(4)
        g2, _ = _build_cycle(4)
        assert g1.could_be_isomorphic(g2) is True

    def test_graph_edit_distance_self(self):
        g, _ = _build_cycle()
        dist = g.graph_edit_distance(g, timeout=5.0)
        assert dist == 0.0

    def test_graph_edit_distance_different_graphs(self):
        g1, _ = _build_cycle()
        g2, _ = _build_path()
        dist = g1.graph_edit_distance(g2, timeout=5.0)
        assert dist is not None
        assert dist > 0

    def test_graph_edit_distance_timeout_returns_none(self):
        g1, _ = _build_cycle()
        g2, _ = _build_cycle(6)
        dist = g1.graph_edit_distance(g2, timeout=0.0001)
        assert dist is None or isinstance(dist, float)


class TestLinkPredictionDelegation:

    def test_adamic_adar_index(self):
        g, nodes = _build_cycle()
        result = g.adamic_adar_index()
        assert isinstance(result, dict)
        assert all(isinstance(v, float) for v in result.values())

    def test_jaccard_coefficient(self):
        g, nodes = _build_cycle()
        result = g.jaccard_coefficient()
        assert isinstance(result, dict)

    def test_resource_allocation_index(self):
        g, nodes = _build_cycle()
        result = g.resource_allocation_index()
        assert isinstance(result, dict)

    def test_preferential_attachment(self):
        g, nodes = _build_cycle()
        result = g.preferential_attachment()
        assert isinstance(result, dict)

    def test_common_neighbor_centrality(self):
        g, nodes = _build_cycle()
        result = g.common_neighbor_centrality()
        assert isinstance(result, dict)

    def test_link_prediction_with_ebunch(self):
        g, nodes = _build_cycle()
        pair = (nodes[0].id, nodes[3].id)
        result = g.adamic_adar_index(ebunch=[pair])
        assert (nodes[0].id, nodes[3].id) in result

    def test_cn_soundarajan_hopcroft(self):
        g, nodes = _build_with_data(4, "community")
        result = g.cn_soundarajan_hopcroft("community")
        assert isinstance(result, dict)

    def test_ra_index_soundarajan_hopcroft(self):
        g, nodes = _build_with_data(4, "community")
        result = g.ra_index_soundarajan_hopcroft("community")
        assert isinstance(result, dict)

    def test_within_inter_cluster(self):
        g, nodes = _build_with_data(4, "community")
        result = g.within_inter_cluster("community")
        assert isinstance(result, dict)


class TestStructuralDelegation:

    def test_dominating_set(self):
        g, nodes = _build_cycle()
        ds = g.dominating_set()
        assert isinstance(ds, set)
        assert len(ds) > 0
        assert len(ds) < len(nodes)

    def test_is_dominating_set(self):
        g, nodes = _build_cycle()
        ds = g.dominating_set()
        assert g.is_dominating_set(ds) is True

    def test_is_not_dominating_set(self):
        g, nodes = _build_cycle()
        assert g.is_dominating_set(set()) is False

    def test_maximal_independent_set(self):
        g, nodes = _build_cycle()
        mis = g.maximal_independent_set(seed=42)
        assert isinstance(mis, set)
        ids = [nd.id for nd in nodes]
        for nid in mis:
            assert nid in ids

    def test_min_weighted_vertex_cover(self):
        g, nodes = _build_cycle()
        vc = g.min_weighted_vertex_cover()
        assert isinstance(vc, set)
        assert len(vc) > 0

    def test_find_cliques(self):
        g, nodes = _build_cycle()
        cliques = g.find_cliques()
        assert isinstance(cliques, list)
        assert all(isinstance(c, set) for c in cliques)

    def test_max_weight_clique(self):
        g, nodes = _build_cycle()
        clique = g.max_weight_clique()
        assert isinstance(clique, set)
        assert len(clique) >= 2

    def test_is_chordal(self):
        g, nodes = _build_cycle()
        assert g.is_chordal() is False

    def test_chordal_graph(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(4)]
        for nd in nodes:
            g.add_node(nd)
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[3].id})))
        assert g.is_chordal() is True


class TestHyperedgeProjection:

    def test_hyperedge_produces_clique_in_find_cliques(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(4)]
        for nd in nodes:
            g.add_node(nd)
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[0].id}),
                target_ids=frozenset({nodes[1].id, nodes[2].id, nodes[3].id}),
            )
        )
        cliques = g.find_cliques()
        large = [c for c in cliques if len(c) == 4]
        assert len(large) == 1

    def test_hyperedge_dominating_set(self):
        g = Hypergraph()
        nodes = [Hypernode(label=str(i)) for i in range(5)]
        for nd in nodes:
            g.add_node(nd)
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[0].id}),
                target_ids=frozenset({nodes[1].id, nodes[2].id, nodes[3].id, nodes[4].id}),
            )
        )
        ds = g.dominating_set()
        assert len(ds) >= 1
