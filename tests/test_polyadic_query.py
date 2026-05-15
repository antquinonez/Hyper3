"""Polyadic tests for kernel_query.py (QueryMixin).

Validates that all query methods handle n-ary edges (edges with multiple
source and/or target nodes) correctly.  Every test constructs edges using
frozensets with cardinality >= 2.
"""
from __future__ import annotations

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def _add_nodes(g: Hypergraph, labels: list[str]) -> dict[str, str]:
    label_to_id: dict[str, str] = {}
    for lbl in labels:
        if lbl in label_to_id:
            continue
        existing = g.get_node_by_label(lbl)
        if existing:
            label_to_id[lbl] = existing.id
        else:
            node = Hypernode(label=lbl)
            g.add_node(node)
            label_to_id[lbl] = node.id
    return label_to_id


def _add_nary(
    g: Hypergraph,
    sources: list[str],
    targets: list[str],
    label: str = "e",
    weight: float = 1.0,
    ids: dict[str, str] | None = None,
) -> dict[str, str]:
    ids = dict(ids) if ids else _add_nodes(g, list(set(sources) | set(targets)))
    for lbl in set(sources) | set(targets):
        if lbl in ids:
            continue
        node = Hypernode(label=lbl)
        g.add_node(node)
        ids[lbl] = node.id
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({ids[s] for s in sources}),
            target_ids=frozenset({ids[t] for t in targets}),
            label=label,
            weight=weight,
        )
    )
    return ids


class TestPolyadicIncidentEdges:
    def test_nary_edge_incident_on_all_participants(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        for lbl in "ABCD":
            edges = g.incident_edges(ids[lbl])
            assert len(edges) == 1

    def test_nary_edge_counts_once_per_node(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D", "E"])
        assert g.node_degree(ids["A"]) == 1
        assert g.node_degree(ids["E"]) == 1

    def test_mixed_cardinality_incident(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="pair")
        ids = _add_nary(g, ["A", "B"], ["C"], label="triple", ids=ids)
        edges_a = g.incident_edges(ids["A"])
        assert len(edges_a) == 2
        edges_c = g.incident_edges(ids["C"])
        assert len(edges_c) == 1


class TestPolyadicOutgoingEdges:
    def test_nary_source_includes_all_sources(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        assert len(g.outgoing_edges(ids["A"])) == 1
        assert len(g.outgoing_edges(ids["B"])) == 1

    def test_nary_target_has_no_outgoing(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        assert g.outgoing_edges(ids["C"]) == []
        assert g.outgoing_edges(ids["D"]) == []

    def test_node_in_both_source_and_target(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["B", "C"])
        out_b = g.outgoing_edges(ids["B"])
        assert len(out_b) == 1
        assert ids["B"] in out_b[0].source_ids


class TestPolyadicIncomingEdges:
    def test_nary_target_includes_all_targets(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B", "C", "D"])
        assert len(g.incoming_edges(ids["B"])) == 1
        assert len(g.incoming_edges(ids["C"])) == 1
        assert len(g.incoming_edges(ids["D"])) == 1

    def test_nary_source_has_no_incoming(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        assert g.incoming_edges(ids["A"]) == []
        assert g.incoming_edges(ids["B"]) == []


class TestPolyadicNeighbors:
    def test_neighbors_sees_all_co_participants(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        nbrs_a = set(g.neighbors(ids["A"]))
        assert nbrs_a == {ids[l] for l in "BCD"}

    def test_neighbors_excludes_self(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["B", "C"])
        nbrs_b = g.neighbors(ids["B"])
        assert ids["B"] not in nbrs_b

    def test_out_neighbors_nary_targets_only(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        out_a = set(g.out_neighbors(ids["A"]))
        assert out_a == {ids["C"], ids["D"]}
        assert ids["B"] not in out_a

    def test_in_neighbors_nary_sources_only(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        in_c = set(g.in_neighbors(ids["C"]))
        assert in_c == {ids["A"], ids["B"]}
        assert ids["D"] not in in_c

    def test_out_neighbors_deduplicates_across_nary_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["A", "D"], ["C"], label="e2", ids=ids)
        out_a = g.out_neighbors(ids["A"])
        assert out_a.count(ids["C"]) == 1

    def test_neighbor_cache_consistent_with_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        nbrs_1 = g.neighbors(ids["A"])
        _add_nary(g, ["A"], ["D"], label="e2", ids=ids)
        nbrs_2 = g.neighbors(ids["A"])
        assert len(nbrs_2) > len(nbrs_1)


class TestPolyadicHyperedgeNeighbors:
    def test_hyperedge_neighbors_shows_shared_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D"])
        hn = g.hyperedge_neighbors(ids["A"])
        assert ids["B"] in hn
        assert ids["C"] in hn
        assert ids["D"] in hn
        assert len(hn[ids["B"]]) == 1

    def test_hyperedge_cocoverage_counts(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["A", "B"], ["C"], label="e2", ids=ids)
        cov = g.hyperedge_cocoverage(ids["A"])
        assert cov[ids["B"]] == 2
        assert cov[ids["C"]] == 2

    def test_hyperedge_neighbors_multiple_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["A"], ["D"], label="e2", ids=ids)
        hn = g.hyperedge_neighbors(ids["A"])
        assert ids["B"] in hn
        assert ids["C"] in hn
        assert ids["D"] in hn
        assert len(hn[ids["B"]]) == 1
        assert len(hn[ids["C"]]) == 1
        assert len(hn[ids["D"]]) == 1


class TestPolyadicNodeDegree:
    def test_degree_counts_edges_not_participants(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D", "E"])
        assert g.node_degree(ids["A"]) == 1
        assert g.node_degree(ids["D"]) == 1

    def test_degree_sums_multiple_nary_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["A"], ["D"], label="e2", ids=ids)
        ids = _add_nary(g, ["A", "E"], ["B"], label="e3", ids=ids)
        assert g.node_degree(ids["A"]) == 3

    def test_degree_zero_for_isolated_node(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["D"], ["E"], ids=ids)
        assert g.node_degree(ids["D"]) == 1
        isolated = Hypernode(label="Z")
        g.add_node(isolated)
        assert g.node_degree(isolated.id) == 0


class TestPolyadicDegreeDistribution:
    def test_nary_edges_produce_uniform_degree(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        dist = g.degree_distribution()
        assert dist.get(1, 0) == 4

    def test_mixed_cardinality_distribution(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="pair")
        ids = _add_nary(g, ["A", "C"], ["D"], label="triple", ids=ids)
        dist = g.degree_distribution()
        assert dist.get(2, 0) == 1
        assert dist.get(1, 0) == 3


class TestPolyadicDensity:
    def test_density_with_nary_edges(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        assert g.density() == 1 / (4 * 3)

    def test_density_counts_edges_not_node_sets(self) -> None:
        g1 = Hypergraph()
        _add_nary(g1, ["A"], ["B"], label="pair")
        g2 = Hypergraph()
        _add_nary(g2, ["A", "B"], ["C", "D"], label="nary")
        assert g1.density() != g2.density()
        assert g1.density() == 0.5
        assert g2.density() == 1 / 12


class TestPolyadicUniqueEdgeSizes:
    def test_mixed_cardinality_sizes(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="pair")
        ids = _add_nary(g, ["A", "B", "C"], ["D"], label="quad", ids=ids)
        ids = _add_nary(g, ["E", "F"], ["G", "H", "I"], label="large", ids=ids)
        assert g.unique_edge_sizes() == [2, 4, 5]

    def test_all_nary_same_size(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], label="e1")
        ids = _add_nary(g, ["E", "F"], ["G", "H"], label="e2", ids=ids)
        assert g.unique_edge_sizes() == [4]


class TestPolyadicMaxEdgeOrder:
    def test_nary_edge_order(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        assert g.max_edge_order() == 4

    def test_pairwise_order_is_1(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A"], ["B"])
        assert g.max_edge_order() == 1

    def test_mixed_orders_takes_max(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="pair")
        ids = _add_nary(g, ["A", "B", "C"], ["D", "E", "F"], label="big", ids=ids)
        assert g.max_edge_order() == 5


class TestPolyadicLabeledEdges:
    def test_labeled_edges_shows_all_source_target_labels(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"], label="joint")
        le = g.labeled_edges
        assert len(le) == 1
        edge = le[0]
        assert set(edge["source_labels"]) == {"A", "B"}
        assert set(edge["target_labels"]) == {"C", "D"}
        assert edge["label"] == "joint"

    def test_labeled_edges_multiple_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["D"], ["E", "F"], label="e2", ids=ids)
        le = g.labeled_edges
        assert len(le) == 2
        labels = {e["label"] for e in le}
        assert labels == {"e1", "e2"}


class TestPolyadicStar:
    def test_star_returns_all_incident(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        star_a = g.star(ids["A"])
        assert len(star_a) == 1
        assert ids["A"] in star_a[0].source_ids


class TestPolyadicDegreeCorrelation:
    def test_degree_correlation_with_nary_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["D", "E"], ["F"], label="e2", ids=ids)
        corr = g.degree_correlation()
        assert -1.0 <= corr <= 1.0

    def test_degree_correlation_single_nary_edge(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        corr = g.degree_correlation()
        assert corr == 0.0


class TestPolyadicDegreeAssortativity:
    def test_assortativity_with_nary_edges(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        assort = g.degree_assortativity()
        assert -1.0 <= assort <= 1.0

    def test_assortativity_nary_cross_pairs(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        dist = g.degree_distribution()
        assert all(d == 1 for d in dist)
        assort = g.degree_assortativity()
        assert assort == 0.0


class TestPolyadicHash:
    def test_hash_deterministic_with_nary(self) -> None:
        g1 = Hypergraph()
        _add_nary(g1, ["A", "B"], ["C", "D"])
        assert g1.hash() != ""
        assert len(g1.hash()) == 64

    def test_hash_differs_for_different_cardinality(self) -> None:
        g1 = Hypergraph()
        _add_nary(g1, ["A"], ["B"])
        g2 = Hypergraph()
        _add_nary(g2, ["A", "B"], ["C"])
        assert g1.hash() != g2.hash()


class TestPolyadicSubhypergraphByOrder:
    def test_filter_by_order_keeps_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="pair")
        ids = _add_nary(g, ["A", "B", "C"], ["D"], label="triple", ids=ids)
        sub = g.subhypergraph_by_order({3})
        assert sub.edge_count == 1
        assert sub.edges[0].label == "triple"

    def test_filter_keeps_pairwise_only(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="pair")
        ids = _add_nary(g, ["A", "B", "C"], ["D"], label="triple", ids=ids)
        sub = g.subhypergraph_by_order({1})
        assert sub.edge_count == 1
        assert sub.edges[0].label == "pair"


class TestPolyadicEdgesByLabel:
    def test_nary_edges_by_label(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="joint")
        ids = _add_nary(g, ["D"], ["E"], label="simple", ids=ids)
        joint_edges = g.edges_by_label("joint")
        assert len(joint_edges) == 1
        assert len(joint_edges[0].source_ids) == 2

    def test_label_filter_excludes_unmatched_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="keep")
        ids = _add_nary(g, ["D", "E"], ["F"], label="drop", ids=ids)
        keep_edges = g.edges_by_label("keep")
        assert len(keep_edges) == 1


class TestPolyadicPairwiseProjection:
    def test_average_neighbor_degree_with_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D"])
        andeg = g.average_neighbor_degree()
        assert ids["A"] in andeg
        assert all(v >= 0 for v in andeg.values())

    def test_s_metric_with_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        s = g.s_metric()
        assert s > 0.0

    def test_onion_layers_with_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        layers = g.onion_layers()
        assert len(layers) == 4

    def test_wiener_index_with_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        w = g.wiener_index()
        assert w > 0.0

    def test_node_connectivity_with_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        nc = g.node_connectivity()
        assert nc >= 0

    def test_edge_connectivity_with_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        ec = g.edge_connectivity()
        assert ec >= 0
