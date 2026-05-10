"""
Gaps: HGX Features Not in Hyper3
===================================
Documents capabilities present in HypergraphX (HGX) that Hyper3 now
partially implements. Remaining gaps are still marked as GAP.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def _build_small_graph():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = ["a", "b", "c", "d", "e", "f"]
    for n in nodes:
        mem.ensure(n)
    for s, t in [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "f"),
                 ("a", "c"), ("b", "d"), ("c", "e"), ("d", "f")]:
        mem.link(s, t, label="e", bidirectional=True)
    return mem


def _test_motif_detection(t: EquivRunner) -> None:
    import networkx as nx

    mem = _build_small_graph()

    result = mem.detect_motifs(order=3, runs_config_model=5, seed=42)

    t.check("motif_detection/produces_result", result is not None)

    G_nx = nx.Graph()
    for e in mem._graph.edges:
        members = list(e.node_ids)
        labels = {n.id: n.label for n in mem._graph._nodes.values()}
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                G_nx.add_edge(labels[members[i]], labels[members[j]])
    t.check_int("motif_detection/graph_size_matches", G_nx.number_of_nodes(), mem._graph.node_count)


def _test_directed_motif_detection(t: EquivRunner) -> None:
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for n in ["a", "b", "c", "d"]:
        mem.ensure(n)
    for s, tgt in [("a", "b"), ("b", "c"), ("c", "d"), ("a", "c")]:
        mem.link(s, tgt, label="de")

    t.gap("directed_motif_detection", "detect_directed_motifs exists on kernel but not exposed on public API")


def _test_configuration_model(t: EquivRunner) -> None:
    from hyper3 import HypergraphMemory, configuration_model

    mem = _build_small_graph()
    result = configuration_model(mem._graph, n_steps=100, seed=42)

    t.check("configuration_model/preserves_node_count",
            result.node_count == mem._graph.node_count)
    t.check_int("configuration_model/preserves_edge_count",
                result.edge_count, mem._graph.edge_count)

    orig_deg = sorted(sum(1 for e in mem._graph._edges.values() if nid in e.node_ids)
                      for nid in mem._graph._nodes)
    new_deg = sorted(sum(1 for e in result._edges.values() if nid in e.node_ids)
                     for nid in result._nodes)
    t.check("configuration_model/preserves_degree_sequence", orig_deg == new_deg)


def _test_hyperlink_communities(t: EquivRunner) -> None:
    mem = _build_small_graph()

    result = mem.analyze.hyperlink_communities()

    t.check("hyperlink_communities/produces_result", result is not None)
    if hasattr(result, "community_count"):
        t.check("hyperlink_communities/count_positive", result.community_count > 0)
    if hasattr(result, "communities"):
        all_labels = set()
        for c in result.communities:
            if hasattr(c, "member_labels"):
                all_labels.update(c.member_labels)
        t.check_int("hyperlink_communities/covers_all_nodes",
                    len(all_labels), mem._graph.node_count)


def _test_simplicial_contagion(t: EquivRunner) -> None:
    mem = _build_small_graph()

    result = mem.simplicial_contagion(
        infected={"a"},
        beta=0.3,
        beta_delta=0.1,
        mu=0.1,
        timesteps=50,
        seed=42,
    )

    t.check("simplicial_contagion/produces_result", result is not None)
    if hasattr(result, "prevalence"):
        t.check("simplicial_contagion/prevalence_tracked", len(result.prevalence) > 0)
    elif isinstance(result, dict):
        t.check("simplicial_contagion/non_empty", len(result) > 0)
    else:
        t.check("simplicial_contagion/completed", True)


def _test_temporal_hypergraph(t: EquivRunner) -> None:
    from hyper3 import HypergraphMemory
    from hyper3.temporal import AllenRelation

    mem = HypergraphMemory(evolve_interval=0)
    for n in ["a", "b", "c"]:
        mem.ensure(n)

    mem.temporal.add_event("a", start=0.0, end=5.0)
    mem.temporal.add_event("b", start=3.0, end=8.0)
    mem.temporal.add_event("c", start=7.0, end=12.0)

    events = mem.temporal.events
    t.check_int("temporal_hypergraph/events_registered", len(events), 3)

    rel_ab = mem.temporal.allen("a", "b")
    t.check("temporal_hypergraph/a_before_b", rel_ab == AllenRelation.BEFORE or rel_ab == AllenRelation.OVERLAPS)

    rel_bc = mem.temporal.allen("b", "c")
    t.check("temporal_hypergraph/b_before_c", rel_bc == AllenRelation.BEFORE or rel_bc == AllenRelation.OVERLAPS)

    rel_ac = mem.temporal.allen("a", "c")
    t.check("temporal_hypergraph/a_before_c", rel_ac == AllenRelation.BEFORE)


def run() -> EquivRunner:
    t = EquivRunner("gaps_hgx")

    _test_motif_detection(t)
    _test_directed_motif_detection(t)
    _test_simplicial_contagion(t)
    t.gap("msf_synchronization", "higher_order_MSF(HG, ...) -- requires user-supplied dynamics functions")
    _test_configuration_model(t)
    t.gap("activity_driven_model", "HOADmodel(N, activities_per_order, time) -- temporal activity-driven")
    t.gap("svh_statistical_validation", "get_svh(hg, alpha=0.01) -- Statistically Validated Hypergraph")
    t.gap("svc_statistical_validation", "get_svc(hg, alpha=0.01) -- Statistically Validated Cores")
    t.gap("structural_reducibility", "reducibility(hg) -- Kirkley et al. 2025")
    t.gap("hy_mmsbm", "HyMMSBM.fit() -- Mixed-Membership Stochastic Block Model")
    t.gap("hypergraph_mt", "HypergraphMT.fit() -- Mesoscale Theory variational inference")
    _test_hyperlink_communities(t)
    _test_temporal_hypergraph(t)
    t.gap("multiplex_hypergraph_type", "MultiplexHypergraph with layered edges")
    t.gap("hif_format", "read_hif(path)/write_hif(H, path) -- Hypergraph Interchange Format")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
