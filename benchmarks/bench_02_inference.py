"""
Bench 2: Transitive Inference
==============================

Compares Hyper3's rule-based multiway reasoning against simpler approaches
for inferring transitive dependencies in a software dependency graph.

Systems compared:
  1. Hyper3 TransitiveRule  - Multiway expansion with just TransitiveRule
  2. Hyper3 Multi-Rule      - Multiway expansion with TransitiveRule + InverseRule
  3. BFS Transitive Closure - Standard graph BFS reachability (label-filtered)
  4. Warshall (nx)          - networkx transitive_closure (all edges)

Metrics:
  - Completeness: fraction of true transitive deps discovered
  - Precision: fraction of discovered deps that are valid transitive deps
  - Edges inferred: total new edges produced
  - Time

Ground truth: all pairs (A, C) where A depends_on B and B depends_on C
              (verified by manual inspection of the dependency graph).

Run:
    .venv/bin/python benchmarks/bench_02_inference.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import networkx as nx

from hyper3 import HypergraphMemory, TransitiveRule, InverseRule, Modality
from shared import (
    build_dependency_graph,
    build_nx_digraph,
    Timer,
    print_header,
    print_comparison_table,
)


def compute_ground_truth(
    nx_graph: nx.DiGraph,
    edge_labels: dict[tuple[str, str], str],
    label: str,
) -> set[tuple[str, str]]:
    """Compute all true transitive pairs A->C where A->B and B->C with same label."""
    pairs: set[tuple[str, str]] = set()
    for a in nx_graph.nodes:
        for b in nx_graph.successors(a):
            if edge_labels.get((a, b)) != label:
                continue
            for c in nx_graph.successors(b):
                if edge_labels.get((b, c)) != label:
                    continue
                if a != c and (a, c) not in nx_graph.edges:
                    pairs.add((a, c))
    return pairs


def run_h3_reasoning(
    nodes: list[tuple[str, dict]],
    edges: list[tuple[str, str, str]],
    rules: list,
    label: str,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], float]:
    """Run Hyper3 reasoning and return (transitive_set, all_inferred_set, time)."""
    with Timer() as t:
        mem = HypergraphMemory(evolve_interval=0)
        for lbl, data in nodes:
            mem.store(lbl, data=data, modalities={Modality.CONCEPTUAL})
        for src, tgt, lbl in edges:
            mem.relate(src, tgt, label=lbl)

        mem.add_rules(*rules)
        all_labels = {n.label for n in mem.graph.nodes}
        mem.reason(all_labels, max_depth=3, max_total_states=500)

    transitive_set: set[tuple[str, str]] = set()
    all_inferred: set[tuple[str, str]] = set()
    for edge in mem.graph.edges:
        if edge.metadata.custom.get("inferred"):
            src = mem.graph.get_node(next(iter(edge.source_ids)))
            tgt = mem.graph.get_node(next(iter(edge.target_ids)))
            if src and tgt:
                all_inferred.add((src.label, tgt.label))
                if label in edge.label or "indirectly_depends" in edge.label:
                    transitive_set.add((src.label, tgt.label))

    return transitive_set, all_inferred, t.elapsed


def main() -> None:
    print_header("Bench 2: Transitive Inference")

    nodes, edges = build_dependency_graph()
    nx_graph, edge_labels = build_nx_digraph(nodes, edges)

    ground_truth = compute_ground_truth(nx_graph, edge_labels, "depends_on")
    print(f"\n  Graph: {len(nodes)} modules, {len(edges)} dependencies")
    print(f"  Ground truth transitive pairs (not in original): {len(ground_truth)}")

    results: dict[str, dict] = {}

    # --- Hyper3 TransitiveRule only ---
    print_header("Running Hyper3 (TransitiveRule only)")
    h3_trans, h3_all, h3_time = run_h3_reasoning(
        nodes, edges,
        [TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on")],
        "indirectly_depends_on",
    )
    h3_hits = h3_trans & ground_truth
    h3_prec = len(h3_hits) / len(h3_trans) if h3_trans else 0.0
    h3_rec = len(h3_hits) / len(ground_truth) if ground_truth else 0.0
    results["H3 TransitiveRule"] = {
        "discovered": len(h3_trans), "total": len(h3_all),
        "hits": len(h3_hits), "precision": h3_prec, "recall": h3_rec,
        "time": h3_time,
    }
    print(f"  Transitive: {len(h3_trans)}  All inferred: {len(h3_all)}")
    print(f"  Hits: {len(h3_hits)}/{len(ground_truth)}  P={h3_prec:.3f}  R={h3_rec:.3f}")
    print(f"  Time: {h3_time*1000:.1f}ms")

    # --- Hyper3 Multi-Rule ---
    print_header("Running Hyper3 (TransitiveRule + InverseRule)")
    h3m_trans, h3m_all, h3m_time = run_h3_reasoning(
        nodes, edges,
        [
            TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on"),
            InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
        ],
        "indirectly_depends_on",
    )
    h3m_hits = h3m_trans & ground_truth
    h3m_prec = len(h3m_hits) / len(h3m_trans) if h3m_trans else 0.0
    h3m_rec = len(h3m_hits) / len(ground_truth) if ground_truth else 0.0
    results["H3 Multi-Rule"] = {
        "discovered": len(h3m_trans), "total": len(h3m_all),
        "hits": len(h3m_hits), "precision": h3m_prec, "recall": h3m_rec,
        "time": h3m_time,
    }
    print(f"  Transitive: {len(h3m_trans)}  All inferred: {len(h3m_all)}")
    print(f"  Hits: {len(h3m_hits)}/{len(ground_truth)}  P={h3m_prec:.3f}  R={h3m_rec:.3f}")
    print(f"  Time: {h3m_time*1000:.1f}ms")

    # --- BFS Transitive Closure ---
    print_header("Running BFS Transitive Closure (label-filtered)")
    with Timer() as t:
        bfs_discovered: set[tuple[str, str]] = set()
        for node in nx_graph.nodes:
            reachable = nx.descendants(nx_graph, node)
            for r in reachable:
                if (node, r) not in nx_graph.edges:
                    try:
                        path = nx.shortest_path(nx_graph, node, r)
                    except nx.NetworkXNoPath:
                        continue
                    if len(path) >= 3:
                        all_dep = all(
                            edge_labels.get((path[i], path[i+1])) == "depends_on"
                            for i in range(len(path) - 1)
                        )
                        if all_dep:
                            bfs_discovered.add((node, r))

    bfs_hits = bfs_discovered & ground_truth
    bfs_prec = len(bfs_hits) / len(bfs_discovered) if bfs_discovered else 0.0
    bfs_rec = len(bfs_hits) / len(ground_truth) if ground_truth else 0.0
    results["BFS Closure"] = {
        "discovered": len(bfs_discovered), "total": len(bfs_discovered),
        "hits": len(bfs_hits), "precision": bfs_prec, "recall": bfs_rec,
        "time": t.elapsed,
    }
    print(f"  Discovered: {len(bfs_discovered)}")
    print(f"  Hits: {len(bfs_hits)}/{len(ground_truth)}  P={bfs_prec:.3f}  R={bfs_rec:.3f}")
    print(f"  Time: {t.elapsed*1000:.1f}ms")

    # --- networkx transitive_closure ---
    print_header("Running networkx transitive_closure")
    with Timer() as t:
        tc_graph = nx.transitive_closure(nx_graph)
        nx_discovered: set[tuple[str, str]] = set()
        for u, v in tc_graph.edges:
            if (u, v) not in nx_graph.edges:
                nx_discovered.add((u, v))

    nx_hits = nx_discovered & ground_truth
    nx_prec = len(nx_hits) / len(nx_discovered) if nx_discovered else 0.0
    nx_rec = len(nx_hits) / len(ground_truth) if ground_truth else 0.0
    results["nx transitive_closure"] = {
        "discovered": len(nx_discovered), "total": len(nx_discovered),
        "hits": len(nx_hits), "precision": nx_prec, "recall": nx_rec,
        "time": t.elapsed,
    }
    print(f"  Discovered: {len(nx_discovered)}")
    print(f"  Hits: {len(nx_hits)}/{len(ground_truth)}  P={nx_prec:.3f}  R={nx_rec:.3f}")
    print(f"  Time: {t.elapsed*1000:.1f}ms")

    # --- Summary ---
    print_header("Comparison Summary")
    headers = ["System", "Discovered", "Hits/GT", "Precision", "Recall", "F1", "Time", "Extra*"]
    rows = []
    for name, r in results.items():
        f1 = 2 * r["precision"] * r["recall"] / (r["precision"] + r["recall"]) if (r["precision"] + r["recall"]) > 0 else 0
        extra = r["total"] - r["discovered"]
        rows.append([
            name,
            str(r["discovered"]),
            f"{r['hits']}/{len(ground_truth)}",
            f"{r['precision']:.3f}",
            f"{r['recall']:.3f}",
            f"{f1:.3f}",
            f"{r['time']*1000:.1f}ms",
            str(extra) if extra > 0 else "-",
        ])
    print_comparison_table(headers, rows)
    print("  * Extra = total inferred beyond transitive (e.g., inverse edges)")

    # Show what Hyper3 found that baselines didn't
    h3_only = (h3m_trans | h3_trans) - bfs_discovered
    bfs_only = bfs_discovered - (h3m_trans | h3_trans)
    if h3_only:
        print_header("Hyper3 Only (not in BFS closure)")
        for src, tgt in sorted(h3_only)[:10]:
            print(f"    {src} -> {tgt}")
    if bfs_only:
        print_header("BFS Only (not in Hyper3)")
        for src, tgt in sorted(bfs_only)[:10]:
            print(f"    {src} -> {tgt}")

    print()


if __name__ == "__main__":
    main()
