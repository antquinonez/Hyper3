"""
Bench 12: Community Detection
==============================

Compares Hyper3's community detection against networkx algorithms for
community quality on a real knowledge graph.

Systems compared:
  1. Hyper3 label propagation - label propagation on pairwise projection
  2. Hyper3 Louvain - Louvain modularity optimization
  3. NX Louvain - python-louvain / networkx community detection
  4. NX label propagation - networkx label_propagation_communities

Metrics:
  - Modularity: standard graph modularity score
  - Community count: number of detected communities
  - Coverage: fraction of nodes assigned to communities
  - Silhouette: intra-community density vs inter-community separation

Ground truth: domain-expert community assignments for CS concept graph.

Run:
    .venv/bin/python benchmarks/bench_12_community.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import networkx as nx

from hyper3 import HypergraphMemory, Modality
from shared import (
    build_cs_knowledge_graph,
    build_nx_digraph,
    build_hyper3_memory,
    Timer,
    print_header,
    print_comparison_table,
)


GROUND_TRUTH_COMMUNITIES = {
    "algorithms": {"algorithm", "sorting", "search", "dynamic_programming", "greedy", "divide_and_conquer", "recursion"},
    "data_structures": {"data_structure", "hash_table", "binary_tree", "linked_list", "stack", "queue", "heap", "graph_ds", "b_tree", "red_black_tree", "array"},
    "os": {"operating_system", "process_scheduling", "memory_management", "file_system", "concurrency", "deadlock", "thread", "mutex"},
    "networks": {"networking", "tcp_ip", "http", "dns", "socket"},
    "databases": {"database", "sql", "normalization", "indexing", "transaction", "acid"},
    "ml_basic": {"machine_learning", "gradient_descent", "loss_function", "overfitting", "regularization", "dropout", "batch_norm"},
    "dl": {"deep_learning", "neural_network", "backpropagation", "cnn", "rnn", "transformer", "attention"},
    "nlp": {"nlp", "bert", "gpt", "word_embedding", "tokenization"},
    "cv": {"computer_vision", "object_detection", "image_classification"},
    "rl": {"reinforcement_learning", "q_learning", "policy_gradient", "reward_function"},
    "se": {"python", "java", "c_programming", "rust", "oop", "functional_programming", "design_pattern", "mvc", "singleton", "observer_pattern", "agile", "testing", "version_control", "git"},
}


def modularity_score(nx_graph: nx.Graph, communities: list[set[str]]) -> float:
    try:
        from networkx.algorithms.community.quality import modularity
        return modularity(nx_graph, communities)
    except Exception:
        return 0.0


def community_purity(
    detected: list[set[str]],
    ground_truth: dict[str, set[str]],
) -> float:
    if not detected or not ground_truth:
        return 0.0
    total_correct = 0
    total_nodes = 0
    for comm in detected:
        if not comm:
            continue
        best_match = 0
        for gt_comm in ground_truth.values():
            overlap = len(comm & gt_comm)
            best_match = max(best_match, overlap)
        total_correct += best_match
        total_nodes += len(comm)
    return total_correct / total_nodes if total_nodes > 0 else 0.0


def main() -> None:
    print_header("Bench 12: Community Detection")

    nodes, edges = build_cs_knowledge_graph()
    nx_graph, _ = build_nx_digraph(nodes, edges)
    nx_undirected = nx_graph.to_undirected()
    mem = build_hyper3_memory(nodes, edges)

    print(f"\n  Graph: {len(nodes)} nodes, {len(edges)} edges")
    print(f"  Ground truth communities: {len(GROUND_TRUTH_COMMUNITIES)}")

    results: dict[str, dict] = {}

    print_header("Hyper3 Label Propagation")
    with Timer() as t:
        lp_result = mem.analyze.communities(method="label_propagation", seed=42)
    results["H3 Label Prop"] = {
        "count": lp_result.community_count,
        "modularity": lp_result.modularity,
        "coverage": lp_result.coverage,
        "largest": lp_result.largest_community_size,
        "time": t.elapsed,
    }
    print(f"  Communities: {lp_result.community_count}")
    print(f"  Modularity: {lp_result.modularity:.4f}")
    print(f"  Coverage: {lp_result.coverage:.4f}")
    print(f"  Largest community: {lp_result.largest_community_size}")
    print(f"  Time: {t.elapsed*1000:.1f}ms")

    for i, comm in enumerate(lp_result.communities[:5]):
        labels = comm.member_labels[:8]
        print(f"    Community {i+1} ({comm.size} nodes): {', '.join(labels)}")

    print_header("Hyper3 Louvain")
    with Timer() as t:
        lv_result = mem.analyze.communities(method="louvain", seed=42)
    results["H3 Louvain"] = {
        "count": lv_result.community_count,
        "modularity": lv_result.modularity,
        "coverage": lv_result.coverage,
        "largest": lv_result.largest_community_size,
        "time": t.elapsed,
    }
    print(f"  Communities: {lv_result.community_count}")
    print(f"  Modularity: {lv_result.modularity:.4f}")
    print(f"  Coverage: {lv_result.coverage:.4f}")
    print(f"  Largest community: {lv_result.largest_community_size}")
    print(f"  Time: {t.elapsed*1000:.1f}ms")

    print_header("NX Label Propagation")
    with Timer() as t:
        nx_lp_communities = list(nx.community.label_propagation_communities(nx_undirected))
    nx_lp_sets = [set(c) for c in nx_lp_communities]
    nx_lp_mod = modularity_score(nx_undirected, nx_lp_sets)
    results["NX Label Prop"] = {
        "count": len(nx_lp_communities),
        "modularity": nx_lp_mod,
        "coverage": 1.0,
        "largest": max(len(c) for c in nx_lp_communities) if nx_lp_communities else 0,
        "time": t.elapsed,
    }
    print(f"  Communities: {len(nx_lp_communities)}")
    print(f"  Modularity: {nx_lp_mod:.4f}")
    print(f"  Largest community: {max(len(c) for c in nx_lp_communities)}")
    print(f"  Time: {t.elapsed*1000:.1f}ms")

    print_header("NX Louvain (greedy modularity)")
    with Timer() as t:
        try:
            nx_lv = nx.community.greedy_modularity_communities(nx_undirected)
        except Exception:
            nx_lv = []
    nx_lv_sets = [set(c) for c in nx_lv]
    nx_lv_mod = modularity_score(nx_undirected, nx_lv_sets)
    results["NX Greedy Mod"] = {
        "count": len(nx_lv),
        "modularity": nx_lv_mod,
        "coverage": 1.0,
        "largest": max(len(c) for c in nx_lv) if nx_lv else 0,
        "time": t.elapsed,
    }
    print(f"  Communities: {len(nx_lv)}")
    print(f"  Modularity: {nx_lv_mod:.4f}")
    print(f"  Largest community: {max(len(c) for c in nx_lv) if nx_lv else 0}")
    print(f"  Time: {t.elapsed*1000:.1f}ms")

    print_header("Community Purity (vs Ground Truth)")
    purity_data: list[list[str]] = []
    for name, res in results.items():
        if name == "H3 Label Prop":
            detected = [set(c.member_labels) for c in lp_result.communities]
        elif name == "H3 Louvain":
            detected = [set(c.member_labels) for c in lv_result.communities]
        elif name == "NX Label Prop":
            detected = nx_lp_sets
        elif name == "NX Greedy Mod":
            detected = nx_lv_sets
        else:
            detected = []

        purity = community_purity(detected, GROUND_TRUTH_COMMUNITIES)
        purity_data.append([
            name,
            str(res["count"]),
            f"{res['modularity']:.4f}",
            f"{purity:.3f}",
            f"{res['coverage']:.4f}",
            f"{res['time']*1000:.1f}ms",
        ])

    purity_headers = ["System", "Communities", "Modularity", "Purity", "Coverage", "Time"]
    print_comparison_table(purity_headers, purity_data)

    print()
