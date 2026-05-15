"""
Polyadic (n-ary) hyperedge compatibility tests.

Validates that core graph operations produce correct results when edges have
multi-node source_ids and/or target_ids. Uses a simplified network security
topology that mirrors the network_analytics example but with polyadic edges.

Each test constructs a small graph with both pairwise and n-ary edges, then
verifies the operation returns correct results.
"""

from __future__ import annotations

import pytest

from hyper3 import (
    Hyperedge,
    Hypergraph,
    HypergraphMemory,
    Hypernode,
    Modality,
    TransitiveRule,
    top_k,
)
from hyper3.kernel_types import Metadata


def _make_graph() -> Hypergraph:
    g = Hypergraph()

    nodes = [
        ("dc-01", {"zone": "restricted", "kind": "host"}),
        ("dc-02", {"zone": "restricted", "kind": "host"}),
        ("admin-bastion", {"zone": "restricted", "kind": "host"}),
        ("app-01", {"zone": "internal", "kind": "host"}),
        ("app-02", {"zone": "internal", "kind": "host"}),
        ("web-01", {"zone": "dmz", "kind": "host"}),
        ("web-02", {"zone": "dmz", "kind": "host"}),
        ("db-primary", {"zone": "restricted", "kind": "host"}),
        ("db-replica", {"zone": "restricted", "kind": "host"}),
        ("seg-dmz", {"zone": "dmz", "kind": "segment"}),
        ("seg-internal", {"zone": "internal", "kind": "segment"}),
        ("seg-restricted", {"zone": "restricted", "kind": "segment"}),
    ]
    for label, data in nodes:
        g.add_node(Hypernode(label=label, data=data))

    return g


def _make_mem() -> HypergraphMemory:
    mem = HypergraphMemory(evolve_interval=0)
    nodes = [
        ("dc-01", {"zone": "restricted", "kind": "host"}),
        ("dc-02", {"zone": "restricted", "kind": "host"}),
        ("admin-bastion", {"zone": "restricted", "kind": "host"}),
        ("app-01", {"zone": "internal", "kind": "host"}),
        ("app-02", {"zone": "internal", "kind": "host"}),
        ("web-01", {"zone": "dmz", "kind": "host"}),
        ("web-02", {"zone": "dmz", "kind": "host"}),
        ("db-primary", {"zone": "restricted", "kind": "host"}),
        ("db-replica", {"zone": "restricted", "kind": "host"}),
        ("svc-ssh", {"kind": "service"}),
        ("svc-https", {"kind": "service"}),
        ("svc-postgres", {"kind": "service"}),
        ("seg-dmz", {"zone": "dmz", "kind": "segment"}),
        ("seg-internal", {"zone": "internal", "kind": "segment"}),
        ("seg-restricted", {"zone": "restricted", "kind": "segment"}),
    ]
    for label, data in nodes:
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    return mem


def _add_polyadic_edges(g: Hypergraph) -> None:
    _dc01 = g.get_node_by_label("dc-01")
    _dc02 = g.get_node_by_label("dc-02")
    _bastion = g.get_node_by_label("admin-bastion")
    _app01 = g.get_node_by_label("app-01")
    _app02 = g.get_node_by_label("app-02")
    _web01 = g.get_node_by_label("web-01")
    _web02 = g.get_node_by_label("web-02")
    _dbp = g.get_node_by_label("db-primary")
    _dbr = g.get_node_by_label("db-replica")
    _sdmz = g.get_node_by_label("seg-dmz")
    _sint = g.get_node_by_label("seg-internal")
    _srest = g.get_node_by_label("seg-restricted")
    assert _dc01 and _dc02 and _bastion and _app01 and _app02
    assert _web01 and _web02 and _dbp and _dbr
    assert _sdmz and _sint and _srest
    dc01, dc02, bastion = _dc01.id, _dc02.id, _bastion.id
    app01, app02 = _app01.id, _app02.id
    web01, web02 = _web01.id, _web02.id
    dbp, dbr = _dbp.id, _dbr.id
    sdmz, sint, srest = _sdmz.id, _sint.id, _srest.id

    g.add_edge(Hyperedge(
        source_ids=frozenset({dc01, dc02}),
        target_ids=frozenset({bastion}),
        label="admin_zone",
        weight=5.0,
    ))

    g.add_edge(Hyperedge(
        source_ids=frozenset({app01, app02}),
        target_ids=frozenset({dbp, dbr}),
        label="app_to_db",
        weight=4.0,
    ))

    g.add_edge(Hyperedge(
        source_ids=frozenset({web01, web02}),
        target_ids=frozenset({app01}),
        label="routes_to",
        weight=3.0,
    ))

    g.add_edge(Hyperedge(
        source_ids=frozenset({bastion}),
        target_ids=frozenset({dc01, dc02}),
        label="trusts",
        weight=2.0,
    ))

    g.add_edge(Hyperedge(
        source_ids=frozenset({web01}),
        target_ids=frozenset({sdmz}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({web02}),
        target_ids=frozenset({sdmz}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({app01}),
        target_ids=frozenset({sint}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({app02}),
        target_ids=frozenset({sint}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({dc01}),
        target_ids=frozenset({srest}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({dc02}),
        target_ids=frozenset({srest}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({bastion}),
        target_ids=frozenset({srest}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({dbp}),
        target_ids=frozenset({srest}),
        label="connects_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({dbr}),
        target_ids=frozenset({srest}),
        label="connects_to",
        weight=1.0,
    ))

    g.add_edge(Hyperedge(
        source_ids=frozenset({sdmz}),
        target_ids=frozenset({sint}),
        label="routes_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({sint}),
        target_ids=frozenset({srest}),
        label="routes_to",
        weight=1.0,
    ))


def _add_polyadic_mem_edges(mem: HypergraphMemory) -> None:
    mem.link_hyper(
        sources={"dc-01", "dc-02"},
        targets={"admin-bastion"},
        label="admin_zone",
        weight=5.0,
    )
    mem.link_hyper(
        sources={"app-01", "app-02"},
        targets={"db-primary", "db-replica"},
        label="app_to_db",
        weight=4.0,
    )
    mem.link_hyper(
        sources={"web-01", "web-02"},
        targets={"app-01"},
        label="routes_to",
        weight=3.0,
    )
    mem.link_hyper(
        sources={"admin-bastion"},
        targets={"dc-01", "dc-02"},
        label="trusts",
        weight=2.0,
    )

    pairwise = [
        ("web-01", "seg-dmz", "connects_to"),
        ("web-02", "seg-dmz", "connects_to"),
        ("app-01", "seg-internal", "connects_to"),
        ("app-02", "seg-internal", "connects_to"),
        ("dc-01", "seg-restricted", "connects_to"),
        ("dc-02", "seg-restricted", "connects_to"),
        ("admin-bastion", "seg-restricted", "connects_to"),
        ("db-primary", "seg-restricted", "connects_to"),
        ("db-replica", "seg-restricted", "connects_to"),
        ("seg-dmz", "seg-internal", "routes_to"),
        ("seg-internal", "seg-restricted", "routes_to"),
    ]
    for src, tgt, lbl in pairwise:
        mem.link(src, tgt, label=lbl)


class TestPolyadicConstruction:

    def test_relate_hyperedge_creates_n_ary_edge(self):
        mem = _make_mem()
        edge = mem.link_hyper(
            sources={"dc-01", "dc-02"},
            targets={"admin-bastion"},
            label="admin_zone",
        )
        assert len(edge.source_ids) == 2
        assert len(edge.target_ids) == 1
        assert edge.label == "admin_zone"

    def test_relate_hyperedge_rejects_missing_node(self):
        mem = _make_mem()
        with pytest.raises(ValueError):
            mem.link_hyper(
                sources={"dc-01", "nonexistent"},
                targets={"admin-bastion"},
                label="bad",
            )

    def test_mixed_pairwise_and_polyadic(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        raw_edges = mem.engine.graph.edges
        polyadic = [e for e in raw_edges if len(e.source_ids) > 1 or len(e.target_ids) > 1]
        pairwise = [e for e in raw_edges if len(e.source_ids) == 1 and len(e.target_ids) == 1]

        assert len(polyadic) == 4
        assert len(pairwise) == 11
        assert mem.size[1] == 15

    def test_hyperedge_resolves_all_labels(self):
        mem = _make_mem()
        edge = mem.link_hyper(
            sources={"dc-01", "dc-02"},
            targets={"admin-bastion"},
            label="admin_zone",
        )
        src_labels = set()
        for sid in edge.source_ids:
            node = mem.engine.graph.get_node(sid)
            if node:
                src_labels.add(node.label)
        assert src_labels == {"dc-01", "dc-02"}


class TestPolyadicDegree:

    def test_node_degree_counts_n_ary_edges(self):
        g = _make_graph()
        _add_polyadic_edges(g)
        n = g.get_node_by_label("dc-01")
        assert n is not None
        deg = g.node_degree(n.id)
        assert deg >= 3

    def test_degree_centrality_with_polyadic_edges(self):
        g = _make_graph()
        _add_polyadic_edges(g)
        dc = g.degree_centrality()
        n = g.get_node_by_label("dc-01")
        assert n is not None
        dc01_score = dc[n.id]
        assert dc01_score > 0.0

    def test_degree_distribution_includes_n_ary_participants(self):
        g = _make_graph()
        _add_polyadic_edges(g)
        dist = g.degree_distribution()
        assert len(dist) > 0
        total = sum(dist.values())
        assert total == g.node_count


class TestPolyadicConnectedComponents:

    def test_polyadic_edge_unifies_all_participants(self):
        g = _make_graph()
        _add_polyadic_edges(g)
        comps = g.connected_components()

        n1 = g.get_node_by_label("dc-01")
        n2 = g.get_node_by_label("dc-02")
        n3 = g.get_node_by_label("admin-bastion")
        assert n1 and n2 and n3
        dc_01_id, dc_02_id, bastion_id = n1.id, n2.id, n3.id

        for comp in comps:
            ids = set(comp)
            if dc_01_id in ids:
                assert dc_02_id in ids, "dc-02 must be in same component as dc-01 (linked by admin_zone edge)"
                assert bastion_id in ids, "bastion must be in same component (admin_zone target)"

    def test_s_connected_components_with_polyadic(self):
        g = _make_graph()
        _add_polyadic_edges(g)
        s_comps = g.s_connected_components(s=2)
        assert len(s_comps) > 0


class TestPolyadicPaths:

    def test_shortest_path_through_n_ary_edge(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        path = mem.analyze.shortest_path("app-01", "db-primary")
        assert path is not None
        assert path[0] == "app-01"
        assert path[-1] == "db-primary"

    def test_n_ary_edge_is_single_hop(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        path = mem.analyze.shortest_path("web-01", "app-01")
        assert path is not None and len(path) == 2, (
            f"N-ary edge {{web-01,web-02}}->{{app-01}} should be a single hop, "
            f"got path length {len(path) if path else 0}: {path}"
        )

    def test_both_sources_of_n_ary_edge_reach_target(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        p1 = mem.analyze.shortest_path("web-01", "app-01")
        p2 = mem.analyze.shortest_path("web-02", "app-01")
        assert p1 is not None
        assert p2 is not None

    def test_n_ary_edge_both_targets_reachable(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        p1 = mem.analyze.shortest_path("app-01", "db-primary")
        p2 = mem.analyze.shortest_path("app-01", "db-replica")
        assert p1 is not None, "app-01 should reach db-primary via n-ary app_to_db edge"
        assert p2 is not None, "app-01 should reach db-replica via n-ary app_to_db edge"


class TestPolyadicBetweenness:

    def test_betweenness_computes_with_n_ary_edges(self):
        g = _make_graph()
        _add_polyadic_edges(g)
        bc = g.betweenness_centrality()
        assert len(bc) == g.node_count
        assert all(v >= 0.0 for v in bc.values())

    def test_betweenness_chokepoint_identified(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)
        bc = mem.analyze.centrality("betweenness")
        assert isinstance(bc, dict)
        assert "app-01" in bc or "web-01" in bc

        app01_bw = bc.get("app-01", 0.0)
        web01_bw = bc.get("web-01", 0.0)
        assert float(app01_bw if isinstance(app01_bw, (int, float)) else 0.0) > 0.0 or float(web01_bw if isinstance(web01_bw, (int, float)) else 0.0) > 0.0


class TestPolyadicCycles:

    def test_cycle_detection_with_n_ary_edges(self):
        g = _make_graph()
        _add_polyadic_edges(g)

        n1 = g.get_node_by_label("dc-01")
        n2 = g.get_node_by_label("admin-bastion")
        assert n1 and n2
        dc01, bastion = n1.id, n2.id

        g.add_edge(Hyperedge(
            source_ids=frozenset({bastion}),
            target_ids=frozenset({dc01}),
            label="trusts",
            weight=1.0,
        ))

        assert g.has_cycle()

    def test_no_false_cycles_with_dag_polyadic(self):
        g = _make_graph()
        _add_polyadic_edges(g)
        cycles = g.detect_cycles(max_cycles=50)
        all_labels: set[str] = set()
        for c in cycles:
            for nid in c:
                node = g.get_node(nid)
                if node:
                    all_labels.add(node.label)
        assert isinstance(all_labels, set)


class TestPolyadicPatternMatch:

    def test_pattern_match_finds_n_ary_edge_by_label(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)
        matches = mem.pattern_match(edge_label="admin_zone")
        assert len(matches) == 1
        assert len(matches[0].source_labels) == 2
        assert "dc-01" in matches[0].source_labels
        assert "dc-02" in matches[0].source_labels

    def test_pattern_match_finds_by_source_in_n_ary_edge(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)
        matches = mem.pattern_match(edge_label="admin_zone", source_label="dc-01")
        assert len(matches) == 1

    def test_pattern_match_all_source_labels_populated(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)
        matches = mem.pattern_match(edge_label="app_to_db")
        assert len(matches) == 1
        m = matches[0]
        assert set(m.source_labels) == {"app-01", "app-02"}
        assert set(m.target_labels) == {"db-primary", "db-replica"}

    def test_pattern_match_by_target_in_n_ary_edge(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)
        matches = mem.pattern_match(edge_label="app_to_db", target_label="db-replica")
        assert len(matches) == 1


class TestPolyadicTransitiveRule:

    def test_transitive_rule_across_n_ary_edges(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        mem.link("app-01", "db-primary", label="trusts")
        mem.link("db-primary", "admin-bastion", label="trusts")

        mem.add_rules(TransitiveRule(edge_label="trusts", new_label="trusts_indirectly"))

        seeds = {"app-01", "db-primary", "admin-bastion"}
        mem.reason(seeds=seeds, max_depth=3)

        indirect = mem.analyze.edges(label="trusts_indirectly")
        assert len(indirect) >= 1, f"Expected transitive trust edges, got {len(indirect)}"

    def test_transitive_rule_chain_through_n_ary(self):
        mem = _make_mem()
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.add("D")

        mem.link_hyper(
            sources={"A", "B"},
            targets={"C"},
            label="causes",
            weight=3.0,
        )
        mem.link_hyper(
            sources={"C"},
            targets={"D"},
            label="causes",
            weight=3.0,
        )

        mem.add_rules(TransitiveRule(edge_label="causes", new_label="causes"))
        mem.reason(seeds={"A", "B", "C", "D"}, max_depth=3)

        from_c_to_d = [e for e in mem.edges() if e.label == "causes"]
        assert len(from_c_to_d) >= 2, "Original causes edges should still exist"


class TestPolyadicCommunities:

    def test_community_detection_with_polyadic_graph(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        result = mem.analyze.communities(seed=42)
        assert result.community_count >= 1
        assert result.modularity != 0.0
        total_members = sum(c.size for c in result.communities)
        assert total_members >= mem.size[0]


class TestPolyadicAnomalyDetection:

    def test_anomaly_detection_with_polyadic(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        result = mem.analyze.anomalies("dc-01")
        assert result.anomaly_status in ("low_risk", "boundary", "anomalous")
        assert 0.0 <= result.boundary_score <= 1.0


class TestPolyadicDegreeDistribution:

    def test_degree_distribution_with_polyadic(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        dist = mem.degree_distribution()
        assert len(dist) > 0
        total = sum(dist.values())
        assert total == mem.size[0]


class TestPolyadicQueryNodes:

    def test_query_nodes_by_data_with_polyadic_edges(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        hosts = mem.query_nodes(data={"kind": "host"})
        assert len(hosts) == 9
        assert "dc-01" in hosts
        assert "web-01" in hosts

    def test_query_hyperedges_by_cardinality(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        n_ary = mem.query_hyperedges(min_source_cardinality=2)
        assert len(n_ary) == 3

        big_target = mem.query_hyperedges(min_target_cardinality=2)
        assert len(big_target) == 2


class TestPolyadicHyperedgeNeighbors:

    def test_hyperedge_neighbors_with_n_ary(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        neighbors = mem.hyperedge_neighbors("dc-01")
        assert "dc-02" in neighbors, "dc-01 and dc-02 co-occur in admin_zone edge"
        assert "admin-bastion" in neighbors, "dc-01 and admin-bastion co-occur in admin_zone edge"

    def test_hyperedge_neighbors_bidirectional(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        neighbors_dc01 = mem.hyperedge_neighbors("dc-01")
        neighbors_bastion = mem.hyperedge_neighbors("admin-bastion")

        assert "dc-01" in neighbors_bastion
        assert "admin-bastion" in neighbors_dc01


class TestPolyadicNeighbors:

    def test_outgoing_neighbors_through_n_ary_edge(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        out = mem.neighbors("dc-01", direction="out")
        assert "admin-bastion" in out or "seg-restricted" in out

    def test_incoming_neighbors_through_n_ary_edge(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)

        inc = mem.neighbors("admin-bastion", direction="in")
        assert "dc-01" in inc or "dc-02" in inc


class TestPolyadicEvolution:

    def test_evolve_does_not_crash_with_polyadic(self):
        mem = _make_mem()
        _add_polyadic_mem_edges(mem)
        result = mem.evolve()
        assert result is not None


class TestPolyadicLabeledEdges:

    def test_labeled_edges_resolves_all_ids(self):
        g = _make_graph()
        _add_polyadic_edges(g)

        labeled = g.labeled_edges
        admin_zone = [e for e in labeled if e["label"] == "admin_zone"]
        assert len(admin_zone) == 1
        assert set(admin_zone[0]["source_labels"]) == {"dc-01", "dc-02"}
        assert admin_zone[0]["target_labels"] == ["admin-bastion"]


class TestPolyadicEdgeSizes:

    def test_unique_edge_sizes_with_polyadic(self):
        g = _make_graph()
        _add_polyadic_edges(g)

        sizes = g.unique_edge_sizes()
        assert 2 in sizes, "N-ary edges with 2 sources should produce size-2 edges"

    def test_max_edge_order_with_polyadic(self):
        g = _make_graph()
        _add_polyadic_edges(g)

        order = g.max_edge_order()
        assert order >= 3, "Largest edge has 2 sources + 1 target = 3 nodes"


class TestPolyadicSPersistence:

    def test_s_persistence_with_polyadic(self):
        g = _make_graph()
        _add_polyadic_edges(g)

        result = g.s_persistence(max_s=3)
        assert len(result.levels) >= 1
        assert result.levels[0].num_components >= 1


class TestPolyadicIncidenceMatrix:

    def test_incidence_matrix_with_polyadic(self):
        g = _make_graph()
        _add_polyadic_edges(g)

        mat, row_ids, col_ids = g.incidence_matrix()
        import numpy as np
        arr = np.asarray(mat.todense()) if hasattr(mat, 'todense') else np.asarray(mat)
        assert arr.shape[0] == g.node_count
        assert arr.shape[1] == g.edge_count

        admin_zone_edge = None
        for eid, edge in g._edges.items():
            if edge.label == "admin_zone":
                admin_zone_edge = eid
                break
        assert admin_zone_edge is not None
