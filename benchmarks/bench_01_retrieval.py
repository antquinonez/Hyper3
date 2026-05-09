"""
Bench 1: Retrieval Quality
==========================

Compares Hyper3's retrieval (spreading activation + semantic RRF fusion)
against simpler baselines on a real knowledge graph.

Systems compared:
  1. Hyper3 RRF  - Spreading activation + embedding similarity via RRF
  2. BFS expand  - BFS neighbor expansion (what most people would write)
  3. PPR         - Personalized PageRank (standard graph retrieval)
  4. RWR         - Random walk with restart (Monte Carlo approximation)

Metrics: P@5, P@10, R@10, MAP, NDCG@10

Ground truth: domain-expert judgments on the CS knowledge graph.

Run:
    .venv/bin/python benchmarks/bench_01_retrieval.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared import (
    build_cs_knowledge_graph,
    build_nx_digraph,
    build_hyper3_memory,
    BFSRetrievalBaseline,
    PersonalizedPageRankBaseline,
    RandomWalkRestartBaseline,
    CS_RETRIEVAL_GROUND_TRUTH,
    precision_at_k,
    recall_at_k,
    average_precision,
    ndcg_at_k,
    f1_at_k,
    Timer,
    print_header,
    print_comparison_table,
)


def main() -> None:
    print_header("Bench 1: Retrieval Quality")

    nodes, edges = build_cs_knowledge_graph()
    nx_graph, _ = build_nx_digraph(nodes, edges)
    mem = build_hyper3_memory(nodes, edges)

    print(f"\n  Graph: {len(nodes)} nodes, {len(edges)} edges")
    print(f"  Queries: {len(CS_RETRIEVAL_GROUND_TRUTH)}")
    print(f"  K values: 5, 10")

    baselines = {
        "BFS expand": BFSRetrievalBaseline(nx_graph),
        "PPR": PersonalizedPageRankBaseline(nx_graph),
        "RWR": RandomWalkRestartBaseline(nx_graph),
    }

    results: dict[str, dict[str, list[float]]] = {
        "Hyper3 RRF": {"p5": [], "p10": [], "r10": [], "map": [], "ndcg": [], "f1_10": []},
        "BFS expand": {"p5": [], "p10": [], "r10": [], "map": [], "ndcg": [], "f1_10": []},
        "PPR": {"p5": [], "p10": [], "r10": [], "map": [], "ndcg": [], "f1_10": []},
        "RWR": {"p5": [], "p10": [], "r10": [], "map": [], "ndcg": [], "f1_10": []},
    }
    timings: dict[str, float] = {"Hyper3 RRF": 0.0, "BFS expand": 0.0, "PPR": 0.0, "RWR": 0.0}

    for query, relevant in CS_RETRIEVAL_GROUND_TRUTH.items():
        if not mem.has(query):
            print(f"  WARNING: seed '{query}' not found in graph, skipping")
            continue

        with Timer() as t:
            h3_results = mem.search.query(query, top_k=10)
        timings["Hyper3 RRF"] += t.elapsed
        h3_labels = [r.label for r in h3_results]

        for name, baseline in baselines.items():
            with Timer() as t:
                if name == "BFS expand":
                    bl_labels = baseline.retrieve(query, max_depth=3, top_k=10)
                elif name == "PPR":
                    bl_labels = baseline.retrieve(query, top_k=10)
                elif name == "RWR":
                    bl_labels = baseline.retrieve(query, steps=1000, top_k=10)
                else:
                    bl_labels = []
            timings[name] += t.elapsed

            results[name]["p5"].append(precision_at_k(bl_labels, relevant, 5))
            results[name]["p10"].append(precision_at_k(bl_labels, relevant, 10))
            results[name]["r10"].append(recall_at_k(bl_labels, relevant, 10))
            results[name]["map"].append(average_precision(bl_labels, relevant))
            results[name]["ndcg"].append(ndcg_at_k(bl_labels, relevant, 10))
            results[name]["f1_10"].append(f1_at_k(bl_labels, relevant, 10))

        results["Hyper3 RRF"]["p5"].append(precision_at_k(h3_labels, relevant, 5))
        results["Hyper3 RRF"]["p10"].append(precision_at_k(h3_labels, relevant, 10))
        results["Hyper3 RRF"]["r10"].append(recall_at_k(h3_labels, relevant, 10))
        results["Hyper3 RRF"]["map"].append(average_precision(h3_labels, relevant))
        results["Hyper3 RRF"]["ndcg"].append(ndcg_at_k(h3_labels, relevant, 10))
        results["Hyper3 RRF"]["f1_10"].append(f1_at_k(h3_labels, relevant, 10))

    print_header("Results (averaged over queries)")

    headers = ["System", "P@5", "P@10", "R@10", "MAP", "NDCG@10", "F1@10", "Time"]
    rows = []
    for system in ["Hyper3 RRF", "BFS expand", "PPR", "RWR"]:
        r = results[system]
        n_queries = len(r["p5"])
        if n_queries == 0:
            continue
        rows.append([
            system,
            f"{sum(r['p5'])/n_queries:.3f}",
            f"{sum(r['p10'])/n_queries:.3f}",
            f"{sum(r['r10'])/n_queries:.3f}",
            f"{sum(r['map'])/n_queries:.3f}",
            f"{sum(r['ndcg'])/n_queries:.3f}",
            f"{sum(r['f1_10'])/n_queries:.3f}",
            f"{timings[system]*1000:.1f}ms",
        ])

    print_comparison_table(headers, rows)

    print_header("Per-Query Breakdown (P@10)")
    for query in sorted(CS_RETRIEVAL_GROUND_TRUTH.keys()):
        relevant = CS_RETRIEVAL_GROUND_TRUTH[query]
        if not mem.has(query):
            continue
        h3 = mem.search.query(query, top_k=10)
        h3_labels = [r.label for r in h3]
        bfs_labels = baselines["BFS expand"].retrieve(query, max_depth=3, top_k=10)
        ppr_labels = baselines["PPR"].retrieve(query, top_k=10)
        print(f"  {query:25s}  H3={precision_at_k(h3_labels, relevant, 10):.2f}  "
              f"BFS={precision_at_k(bfs_labels, relevant, 10):.2f}  "
              f"PPR={precision_at_k(ppr_labels, relevant, 10):.2f}  "
              f"relevant={len(relevant)}")

    print()


if __name__ == "__main__":
    main()
