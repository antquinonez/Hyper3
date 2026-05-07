"""
Gaps: HGX Features Not in Hyper3
====================================
Documents capabilities present in HypergraphX (HGX) that Hyper3 lacks.
All tests are marked as GAP to serve as a guiding backlog.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("gaps_hgx")

    t.gap("motif_detection", "compute_motifs(HG, order=3) -- isomorphism enumeration + config model comparison")
    t.gap("directed_motif_detection", "compute_directed_motifs(DHG, order=3)")
    t.gap("simplicial_contagion", "simplicial_contagion(HG, I0, T, beta, beta_D, mu) -- SIS with 3-body infection")
    t.gap("msf_synchronization", "higher_order_MSF(HG, ...) -- Master Stability Function on hypergraph")
    t.gap("configuration_model", "configuration_model(hg, n_steps=1000) -- MCMC preserving degree sequence")
    t.gap("activity_driven_model", "HOADmodel(N, activities_per_order, time) -- temporal activity-driven")
    t.gap("svh_statistical_validation", "get_svh(hg, alpha=0.01) -- Statistically Validated Hypergraph")
    t.gap("svc_statistical_validation", "get_svc(hg, alpha=0.01) -- Statistically Validated Cores")
    t.gap("structural_reducibility", "reducibility(hg) -- Kirkley et al. 2025")
    t.gap("hy_mmsbm", "HyMMSBM.fit() -- Mixed-Membership Stochastic Block Model")
    t.gap("hypergraph_mt", "HypergraphMT.fit() -- Mesoscale Theory variational inference")
    t.gap("hyperlink_communities", "hyperlink_communities(hg) -- Ahn-Bagrow-Leicht edge clustering")
    t.gap("temporal_hypergraph_type", "TemporalHypergraph with time-indexed edges")
    t.gap("multiplex_hypergraph_type", "MultiplexHypergraph with layered edges")
    t.gap("hif_format", "read_hif(path)/write_hif(H, path) -- Hypergraph Interchange Format")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
