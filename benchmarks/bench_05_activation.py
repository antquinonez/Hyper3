"""
Bench 5: Spreading Activation vs Alternatives
==============================================

Compares Hyper3's spreading activation against standard graph-based
retrieval methods for associative recall quality.

Systems compared:
  1. Hyper3 SpreadingActivation - configurable decay, label rates, normalization
  2. Personalized PageRank (nx)  - standard graph ranking
  3. Random Walk with Restart    - Monte Carlo PPR approximation
  4. BFS expansion               - uniform energy distribution

Metrics: Precision@k, NDCG@k against ground-truth relevance judgments.

Run:
    .venv/bin/python benchmarks/bench_05_activation.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import networkx as nx
import numpy as np

from hyper3 import HypergraphMemory, Modality
from shared import (
    build_cs_knowledge_graph,
    build_nx_digraph,
    build_hyper3_memory,
    BFSRetrievalBaseline,
    PersonalizedPageRankBaseline,
    RandomWalkRestartBaseline,
    CS_RETRIEVAL_GROUND_TRUTH,
    precision_at_k,
    ndcg_at_k,
    recall_at_k,
    average_precision,
    Timer,
    print_header,
    print_comparison_table,
)


def main() -> None:
    print_header("Bench 5: Spreading Activation")

    nodes, edges = build_cs_knowledge_graph()
    nx_graph, _ = build_nx_digraph(nodes, edges)
    mem = build_hyper3_memory(nodes, edges)

    print(f"\n  Graph: {len(nodes)} nodes, {len(edges)} edges")
    print(f"  Test queries: {len(CS_RETRIEVAL_GROUND_TRUTH)}")

    systems = ["Hyper3 Activation", "PPR", "RWR", "BFS"]
    metrics = ["p@5", "p@10", "r@10", "map", "ndcg@10"]
    results: dict[str, dict[str, list[float]]] = {s: {m: [] for m in metrics} for s in systems}
    timings: dict[str, float] = {s: 0.0 for s in systems}

    ppr = PersonalizedPageRankBaseline(nx_graph)
    rwr = RandomWalkRestartBaseline(nx_graph)
    bfs = BFSRetrievalBaseline(nx_graph)

    for query, relevant in CS_RETRIEVAL_GROUND_TRUTH.items():
        if not mem.has(query):
            continue

        # Hyper3 activation
        with Timer() as t:
            activated = mem.activate(query, energy=1.0, top_k=10, iterations=3)
        timings["Hyper3 Activation"] += t.elapsed
        act_labels = [r.label for r in activated]

        # PPR
        with Timer() as t:
            ppr_labels = ppr.retrieve(query, top_k=10)
        timings["PPR"] += t.elapsed

        # RWR
        with Timer() as t:
            rwr_labels = rwr.retrieve(query, steps=2000, top_k=10)
        timings["RWR"] += t.elapsed

        # BFS
        with Timer() as t:
            bfs_labels = bfs.retrieve(query, max_depth=3, top_k=10)
        timings["BFS"] += t.elapsed

        all_results = {
            "Hyper3 Activation": act_labels,
            "PPR": ppr_labels,
            "RWR": rwr_labels,
            "BFS": bfs_labels,
        }

        for system, labels in all_results.items():
            results[system]["p@5"].append(precision_at_k(labels, relevant, 5))
            results[system]["p@10"].append(precision_at_k(labels, relevant, 10))
            results[system]["r@10"].append(recall_at_k(labels, relevant, 10))
            results[system]["map"].append(average_precision(labels, relevant))
            results[system]["ndcg@10"].append(ndcg_at_k(labels, relevant, 10))

    # --- Summary ---
    print_header("Results (mean over queries)")
    headers = ["System", "P@5", "P@10", "R@10", "MAP", "NDCG@10", "Time"]
    rows = []
    for system in systems:
        r = results[system]
        n = len(r["p@5"])
        if n == 0:
            continue
        rows.append([
            system,
            f"{sum(r['p@5'])/n:.3f}",
            f"{sum(r['p@10'])/n:.3f}",
            f"{sum(r['r@10'])/n:.3f}",
            f"{sum(r['map'])/n:.3f}",
            f"{sum(r['ndcg@10'])/n:.3f}",
            f"{timings[system]*1000:.1f}ms",
        ])
    print_comparison_table(headers, rows)

    # --- Iteration sensitivity ---
    print_header("Activation Iteration Sensitivity")
    seed = "transformer"
    relevant = CS_RETRIEVAL_GROUND_TRUTH.get(seed, set())
    seed_id = mem.resolve_id(seed)
    if seed_id:
        it_headers = ["Iterations", "P@5", "P@10", "R@10", "NDCG@10", "Activated"]
        it_rows = []
        for iters in [1, 2, 3, 4, 5]:
            with Timer():
                act = mem.activate(seed, energy=1.0, top_k=10, iterations=iters)
            labels = [r.label for r in act]
            it_rows.append([
                str(iters),
                f"{precision_at_k(labels, relevant, 5):.3f}",
                f"{precision_at_k(labels, relevant, 10):.3f}",
                f"{recall_at_k(labels, relevant, 10):.3f}",
                f"{ndcg_at_k(labels, relevant, 10):.3f}",
                str(len(act)),
            ])
        print_comparison_table(it_headers, it_rows)

    # --- Decay sensitivity ---
    print_header("Activation Decay Sensitivity")
    if seed_id:
        from hyper3.retrieval_activation import ActivationConfig, SpreadingActivation
        dec_headers = ["Decay", "P@5", "P@10", "Activated"]
        dec_rows = []
        for decay in [0.5, 0.7, 0.85, 0.95]:
            sa = SpreadingActivation(mem.engine.graph, config=ActivationConfig(decay_factor=decay))
            sa.stimulate(seed_id, 1.0)
            sa.spread(3)
            act = sa.get_activated(top_k=10)
            act = [r for r in act if r.node_id != seed_id][:10]
            labels = [r.label for r in act]
            dec_rows.append([
                str(decay),
                f"{precision_at_k(labels, relevant, 5):.3f}",
                f"{precision_at_k(labels, relevant, 10):.3f}",
                str(len(act)),
            ])
        print_comparison_table(dec_headers, dec_rows)

    print()


if __name__ == "__main__":
    main()
