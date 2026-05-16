"""Polyadic tests for kernel_components.py (ComponentMixin).

Validates that connected components, s-components, s-persistence,
strongly connected components, biconnected components, articulation
points, and modularity communities handle n-ary edges correctly.
"""
from __future__ import annotations

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def _add_nary(
    g: Hypergraph,
    sources: list[str],
    targets: list[str],
    label: str = "e",
    weight: float = 1.0,
    ids: dict[str, str] | None = None,
) -> dict[str, str]:
    ids = dict(ids) if ids else {}
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


class TestPolyadicConnectedComponents:
    def test_nary_edge_unifies_all_participants(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        comps = g.connected_components()
        assert len(comps) == 1
        assert len(comps[0]) == 4

    def test_nary_5source_all_connected(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C", "D"], ["E"])
        comps = g.connected_components()
        assert len(comps) == 1
        assert len(comps[0]) == 5

    def test_two_disjoint_nary_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="g1")
        ids = _add_nary(g, ["D", "E"], ["F"], label="g2", ids=ids)
        comps = g.connected_components()
        assert len(comps) == 2
        sizes = sorted(len(c) for c in comps)
        assert sizes == [3, 3]

    def test_nary_bridge_merges_two_groups(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="left")
        ids = _add_nary(g, ["D", "E"], ["F"], label="right", ids=ids)
        ids = _add_nary(g, ["C"], ["D"], label="bridge", ids=ids)
        comps = g.connected_components()
        assert len(comps) == 1
        assert len(comps[0]) == 6

    def test_isolated_node_separate_component(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        iso = Hypernode(label="Z")
        g.add_node(iso)
        comps = g.connected_components()
        assert len(comps) == 2
        sizes = sorted(len(c) for c in comps)
        assert sizes == [1, 3]

    def test_is_connected_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        assert g.is_connected()

    def test_largest_connected_component_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        ids = _add_nary(g, ["E"], ["F"], ids=ids)
        largest = g.largest_connected_component()
        assert len(largest) == 4

    def test_component_of_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        comp = g.component_of(ids["B"])
        assert len(comp) == 4
        assert ids["D"] in comp


class TestPolyadicSComponents:
    def test_s1_nary_single_component(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        comps = g.connected_components(s=1)
        assert len(comps) == 1

    def test_s2_splits_on_overlap(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D"], label="e1")
        ids = _add_nary(g, ["D", "E"], ["F"], label="e2", ids=ids)
        comps = g.connected_components(s=2)
        assert len(comps) == 2
        sizes = sorted(len(c) for c in comps)
        assert sizes == [3, 4]

    def test_s3_higher_than_overlap_splits_all(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        comps = g.connected_components(s=3)
        assert len(comps) == 2

    def test_s_connected_components_method(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        comps = g.s_connected_components(s=1)
        assert len(comps) == 1


class TestPolyadicSPersistence:
    def test_persistence_nary_increases_components(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D"], label="e1")
        ids = _add_nary(g, ["D", "E"], ["F"], label="e2", ids=ids)
        result = g.s_persistence(max_s=5)
        assert len(result.levels) == 5
        assert result.levels[0].num_components == 1
        assert result.levels[1].num_components == 2
        assert result.levels[-1].num_components == 2

    def test_persistence_nary_single_edge(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        result = g.s_persistence()
        assert result.levels[0].num_components == 1


class TestPolyadicSCCs:
    def test_nary_cycle_creates_scc(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], label="fwd")
        ids = _add_nary(g, ["C", "D"], ["A", "B"], label="bwd", ids=ids)
        sccs = g.strongly_connected_components()
        assert len(sccs) == 1
        assert len(sccs[0]) == 4

    def test_nary_dag_no_scc_merge(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        sccs = g.strongly_connected_components()
        assert len(sccs) == 4

    def test_nary_partial_cycle(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="fwd")
        ids = _add_nary(g, ["C"], ["A"], label="back", ids=ids)
        sccs = g.strongly_connected_components()
        scc_sizes = sorted(len(s) for s in sccs)
        assert scc_sizes == [1, 2]
        scc_2 = [s for s in sccs if len(s) == 2][0]
        assert ids["A"] in scc_2
        assert ids["C"] in scc_2

    def test_nary_two_cycles_separate(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="fwd1")
        ids = _add_nary(g, ["B"], ["A"], label="bwd1", ids=ids)
        ids = _add_nary(g, ["C"], ["D"], label="fwd2", ids=ids)
        ids = _add_nary(g, ["D"], ["C"], label="bwd2", ids=ids)
        sccs = g.strongly_connected_components()
        assert len(sccs) == 2
        sizes = sorted(len(s) for s in sccs)
        assert sizes == [2, 2]


class TestPolyadicBiconnected:
    def test_nary_edge_is_biconnected(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        bicomp = g.biconnected_components()
        assert len(bicomp) == 1
        all_nodes = set().union(*bicomp)
        assert len(all_nodes) == 4

    def test_nary_two_edges_shared_node(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        bicomp = g.biconnected_components()
        assert len(bicomp) == 2
        sizes = sorted(len(bc) for bc in bicomp)
        assert sizes == [3, 3]


class TestPolyadicArticulation:
    def test_nary_shared_node_is_articulation(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        art = g.articulation_points()
        assert ids["C"] in art
        assert len(art) == 1

    def test_nary_no_articulation_in_clique(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        ids = _add_nary(g, ["A", "C"], ["B", "D"], label="cross", ids=ids)
        art = g.articulation_points()
        assert len(art) == 0


class TestPolyadicModularity:
    def test_nary_two_clusters(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="left", weight=10.0)
        ids = _add_nary(g, ["A", "B"], ["C"], label="left2", weight=10.0, ids=ids)
        ids = _add_nary(g, ["D", "E"], ["F"], label="right", weight=10.0, ids=ids)
        ids = _add_nary(g, ["D", "E"], ["F"], label="right2", weight=10.0, ids=ids)
        ids = _add_nary(g, ["C"], ["D"], label="bridge", weight=0.01, ids=ids)
        communities = g.greedy_modularity_communities()
        assert len(communities) == 2
        sizes = sorted(len(c) for c in communities)
        assert sizes == [3, 3]

    def test_nary_single_cluster(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        communities = g.greedy_modularity_communities()
        assert len(communities) == 1
        assert len(communities[0]) == 5


class TestPolyadicSComponentsBySize:
    def test_filter_by_size(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], label="big")
        ids = _add_nary(g, ["E"], ["F"], label="small", ids=ids)
        result = g.s_components_by_size(min_size=3)
        assert len(result) == 1
        assert len(result[0]) == 4

    def test_max_size_filter(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], label="big")
        ids = _add_nary(g, ["E"], ["F"], label="small", ids=ids)
        result = g.s_components_by_size(max_size=2)
        assert len(result) == 1
        assert len(result[0]) == 2
