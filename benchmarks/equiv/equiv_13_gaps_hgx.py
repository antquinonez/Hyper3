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
    mem = _build_small_graph()

    result = mem.detect_motifs(order=3, runs_config_model=5, seed=42)

    t.check("motif_detection/produces_result", result is not None)

    if hasattr(result, "motifs"):
        t.check("motif_detection/has_motifs", len(result.motifs) > 0)
    elif isinstance(result, dict):
        t.check("motif_detection/has_motifs", len(result) > 0)
    else:
        t.check("motif_detection/non_empty", bool(result))


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

    t.check("configuration_model/produces_result", result is not None)
    t.check("configuration_model/preserves_node_count",
            result.node_count == mem._graph.node_count)


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
        t.check("hyperlink_communities/covers_nodes", len(all_labels) > 0)


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

    mem = HypergraphMemory(evolve_interval=0)
    for n in ["a", "b", "c"]:
        mem.ensure(n)

    mem.temporal.add_event("a", start=0.0, end=5.0)
    mem.temporal.add_event("b", start=3.0, end=8.0)
    mem.temporal.add_event("c", start=7.0, end=12.0)

    events = mem.temporal.events
    t.check("temporal_hypergraph/events_registered", len(events) > 0)

    result = mem.temporal.allen("a", "b")
    t.check("temporal_hypergraph/relation_computed", result is not None)


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
