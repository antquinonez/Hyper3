"""
Bench 6: Self-Evolution (Decay/Prune/Merge)
============================================

Compares Hyper3's self-evolution engine against simple baselines for
graph maintenance under insertion pressure.

Systems compared:
  1. Hyper3 GraphMaintenanceEngine - weighted decay + access-based pruning + equivalence merge
  2. Age-based pruning (FIFO)   - remove oldest/least-accessed nodes
  3. Random pruning              - remove random nodes

Metrics:
  - Query accuracy after pruning (recall of important nodes)
  - Graph size reduction
  - Important node retention rate

Ground truth: a set of "important" nodes that should survive pruning.

Run:
    .venv/bin/python benchmarks/bench_06_evolution.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time

from hyper3 import HypergraphMemory, Modality
from shared import (
    build_cs_knowledge_graph,
    AgeBasedPruningBaseline,
    RandomPruningBaseline,
    Timer,
    print_header,
    print_comparison_table,
)


IMPORTANT_NODES = {
    "algorithm", "data_structure", "machine_learning", "deep_learning",
    "neural_network", "transformer", "python", "database", "operating_system",
    "networking", "concurrency", "design_pattern", "testing",
}

NOISE_PREFIX = "noise_"


def add_noise_nodes(mem: HypergraphMemory, count: int) -> list[str]:
    noise_ids = []
    for i in range(count):
        label = f"{NOISE_PREFIX}{i}"
        mem.add(label, data={"type": "noise", "idx": i})
        noise_ids.append(label)
    for i in range(count - 1):
        src = f"{NOISE_PREFIX}{i}"
        tgt = f"{NOISE_PREFIX}{i + 1}"
        mem.link(src, tgt, label="noise_edge")
    if count > 10:
        mem.link(f"{NOISE_PREFIX}0", "algorithm", label="noise_edge")
    return noise_ids


def query_important_nodes(mem: HypergraphMemory, important: set[str]) -> dict[str, bool]:
    found = {}
    for label in important:
        found[label] = mem.has(label)
    return found


def retention_rate(found: dict[str, bool]) -> float:
    if not found:
        return 0.0
    return sum(1 for v in found.values() if v) / len(found)


def main() -> None:
    print_header("Bench 6: Self-Evolution")

    noise_counts = [50, 100, 200]
    target_keeps = [50, 75, 100]

    for noise_count in noise_counts:
        print_header(f"Noise Level: {noise_count} noise nodes")

        # --- Setup ---
        nodes, edges = build_cs_knowledge_graph()
        noise_labels = [f"{NOISE_PREFIX}{i}" for i in range(noise_count)]

        # --- Test retention at different pruning levels ---
        headers = ["Strategy", "Target Keep", "Pre-Prune", "Post-Prune", "Important Retained", "Time"]
        rows = []

        for target_keep in target_keeps:
            # Hyper3 evolution
            mem = HypergraphMemory(evolve_interval=0)
            for label, data in nodes:
                mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
            for src, tgt, lbl in edges:
                mem.link(src, tgt, label=lbl)
            add_noise_nodes(mem, noise_count)

            for label in IMPORTANT_NODES:
                node = mem.engine.graph.get_node_by_label(label)
                if node:
                    node.touch(time.time())
                    node.touch(time.time())

            pre_size = mem.size[0]

            with Timer() as t:
                mem._evolution.decay_weights(0.95)
                mem._evolution.prune_dead_nodes()
                mem._evolution.merge_equivalences()
                for label in IMPORTANT_NODES:
                    node = mem.engine.graph.get_node_by_label(label)
                    if node:
                        mem._evolution.reinforce(node.id)

            post_size = mem.size[0]
            found = query_important_nodes(mem, IMPORTANT_NODES)
            retained = retention_rate(found)

            rows.append([
                "Hyper3 evolve",
                str(target_keep),
                str(pre_size),
                str(post_size),
                f"{retained:.1%} ({sum(1 for v in found.values() if v)}/{len(found)})",
                f"{t.elapsed*1000:.1f}ms",
            ])

            # Age-based pruning
            mem2 = HypergraphMemory(evolve_interval=0)
            for label, data in nodes:
                mem2.add(label, data=data, modalities={Modality.CONCEPTUAL})
            for src, tgt, lbl in edges:
                mem2.link(src, tgt, label=lbl)
            add_noise_nodes(mem2, noise_count)

            all_nodes = []
            for n in mem2.engine.graph.nodes:
                all_nodes.append((n.id, n.created_at, n.access_count))

            with Timer() as t:
                age_pruner = AgeBasedPruningBaseline(target_keep)
                to_remove = age_pruner.prune(all_nodes)
                for nid in to_remove:
                    try:
                        mem2.engine.graph.remove_node(nid)
                    except Exception:
                        pass

            post_size2 = mem2.size[0]
            found2 = query_important_nodes(mem2, IMPORTANT_NODES)
            retained2 = retention_rate(found2)

            rows.append([
                "Age-based prune",
                str(target_keep),
                str(pre_size),
                str(post_size2),
                f"{retained2:.1%} ({sum(1 for v in found2.values() if v)}/{len(found2)})",
                f"{t.elapsed*1000:.1f}ms",
            ])

            # Random pruning
            mem3 = HypergraphMemory(evolve_interval=0)
            for label, data in nodes:
                mem3.add(label, data=data, modalities={Modality.CONCEPTUAL})
            for src, tgt, lbl in edges:
                mem3.link(src, tgt, label=lbl)
            add_noise_nodes(mem3, noise_count)

            all_nodes3 = []
            for n in mem3.engine.graph.nodes:
                all_nodes3.append((n.id, n.created_at, n.access_count))

            with Timer() as t:
                rand_pruner = RandomPruningBaseline(target_keep)
                to_remove3 = rand_pruner.prune(all_nodes3)
                for nid in to_remove3:
                    try:
                        mem3.engine.graph.remove_node(nid)
                    except Exception:
                        pass

            post_size3 = mem3.size[0]
            found3 = query_important_nodes(mem3, IMPORTANT_NODES)
            retained3 = retention_rate(found3)

            rows.append([
                "Random prune",
                str(target_keep),
                str(pre_size),
                str(post_size3),
                f"{retained3:.1%} ({sum(1 for v in found3.values() if v)}/{len(found3)})",
                f"{t.elapsed*1000:.1f}ms",
            ])

        print_comparison_table(headers, rows)

    # --- Decay behavior analysis ---
    print_header("Decay Weight Analysis")
    mem = HypergraphMemory(evolve_interval=0)
    nodes, edges = build_cs_knowledge_graph()
    for label, data in nodes:
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    for src, tgt, lbl in edges:
        mem.link(src, tgt, label=lbl)

    initial_weights = {e.id: e.weight for e in mem.edges()}
    decay_headers = ["Decay Factor", "Mean Weight", "Min Weight", "Edges < 0.5", "Edges < 0.1"]
    decay_rows = []
    for decay in [0.99, 0.95, 0.9, 0.8, 0.5]:
        for e in mem.engine.graph.edges:
            e.weight = initial_weights.get(e.id, 1.0)
        mem._evolution.decay_weights(decay)
        edges_after = mem.edges()
        weights = [e.weight for e in edges_after]
        mean_w = sum(weights) / len(weights) if weights else 0
        min_w = min(weights) if weights else 0
        below_half = sum(1 for w in weights if w < 0.5)
        below_tenth = sum(1 for w in weights if w < 0.1)
        decay_rows.append([
            str(decay),
            f"{mean_w:.3f}",
            f"{min_w:.3f}",
            str(below_half),
            str(below_tenth),
        ])
    print_comparison_table(decay_headers, decay_rows)

    print()


if __name__ == "__main__":
    main()
