"""Hyperedge walkthrough: n-ary directed edges in a research lab graph.

Run:
    .venv/bin/python -m demos.demo_hyperedges
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper3 import HypergraphMemory

try:
    from .data import DELIVERABLES, HYPEREDGES, MENTORSHIP_EDGES, PEOPLE, RESOURCES
except ImportError:
    from data import DELIVERABLES, HYPEREDGES, MENTORSHIP_EDGES, PEOPLE, RESOURCES


def _labels(mem: HypergraphMemory, id_set: frozenset[str]) -> list[str]:
    return sorted(
        mem.graph.get_node(nid).label
        for nid in id_set
        if mem.graph.get_node(nid)
    )


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    # ==================================================================
    # Step 1: Build the lab graph — people, resources, deliverables
    # ==================================================================
    print("=" * 70)
    print("STEP 1: Build the lab graph")
    print("=" * 70)

    for name, info in PEOPLE.items():
        mem.add(name, data=info)
    for name, info in RESOURCES.items():
        mem.add(name, data=info)
    for name, info in DELIVERABLES.items():
        mem.add(name, data=info)

    # Pairwise mentorship edges
    for mentor, mentee, label in MENTORSHIP_EDGES:
        mem.link(mentor, mentee, label=label)

    print(f"  Nodes: {mem.graph.node_count}")
    print(f"  Pairwise mentorship edges: {len(MENTORSHIP_EDGES)}")
    print()

    # ==================================================================
    # Step 2: Create n-ary hyperedges
    # ==================================================================
    print("=" * 70)
    print("STEP 2: Create n-ary hyperedges")
    print("=" * 70)

    for sources, targets, label, weight in HYPEREDGES:
        edge = mem.link_hyper(sources, targets, label=label, weight=weight)
        src_labels = _labels(mem, edge.source_ids)
        tgt_labels = _labels(mem, edge.target_ids)
        print(f"  {src_labels} --[{label}]--> {tgt_labels}  (weight={weight})")

    print(f"\n  Total edges now: {mem.graph.edge_count}")
    print()

    # ==================================================================
    # Step 3: Edge size distribution
    # ==================================================================
    print("=" * 70)
    print("STEP 3: Edge size distribution")
    print("=" * 70)

    sizes = mem.unique_edge_sizes()
    max_order = mem.max_edge_order()
    print(f"  Unique edge sizes (|source| + |target|): {sorted(sizes)}")
    print(f"  Max edge order (largest single-side cardinality): {max_order}")
    print()

    # ==================================================================
    # Step 4: Query hyperedges by cardinality
    # ==================================================================
    print("=" * 70)
    print("STEP 4: Query hyperedges with min_source_cardinality >= 2")
    print("=" * 70)

    multi_src = mem.query_hyperedges(min_source_cardinality=2)
    for edge in multi_src:
        src = _labels(mem, edge.source_ids)
        tgt = _labels(mem, edge.target_ids)
        print(f"  {src} --[{edge.label}]--> {tgt}")
    print(f"\n  Found {len(multi_src)} multi-source hyperedges")
    print()

    # ==================================================================
    # Step 5: Query hyperedges containing a specific node
    # ==================================================================
    print("=" * 70)
    print("STEP 5: Hyperedges containing 'alice'")
    print("=" * 70)

    alice_edges = mem.query_hyperedges(containing="alice")
    for edge in alice_edges:
        src = _labels(mem, edge.source_ids)
        tgt = _labels(mem, edge.target_ids)
        print(f"  {src} --[{edge.label}]--> {tgt}")
    print(f"\n  Alice participates in {len(alice_edges)} edges")
    print()

    # ==================================================================
    # Step 6: Hyperedge neighbor analysis — co-participation
    # ==================================================================
    print("=" * 70)
    print("STEP 6: Hyperedge neighbors of 'alice' (co-participation)")
    print("=" * 70)

    neighbors = mem.hyperedge_neighbors("alice")
    for neighbor, shared_edges in sorted(neighbors.items()):
        edge_labels = [e.label for e in shared_edges]
        print(f"  alice <-> {neighbor}: shared edges {edge_labels}")
    print(f"\n  Alice co-participates with {len(neighbors)} other concepts")
    print()

    # ==================================================================
    # Step 7: Hyperedge similarity
    # ==================================================================
    print("=" * 70)
    print("STEP 7: Hyperedge similarity (jaccard) for 'paper_transformers'")
    print("=" * 70)

    similar = mem.hyperedge_similarity("paper_transformers", metric="jaccard", top_k=5)
    for other_label, score in similar:
        print(f"  {other_label}: {score:.4f}")

    if not similar:
        print("  (no similar hyperedges found)")
    print()

    # ==================================================================
    # Step 8: Why n-ary edges matter
    # ==================================================================
    print("=" * 70)
    print("STEP 8: Why n-ary edges matter")
    print("=" * 70)

    coauth = mem.query_hyperedges(min_source_cardinality=2, label="coauthored")
    print("  Co-authored papers as n-ary hyperedges:")
    for edge in coauth:
        authors = _labels(mem, edge.source_ids)
        paper = _labels(mem, edge.target_ids)
        print(f"    {authors} --[coauthored]--> {paper}")

    print()
    print("  With pairwise edges, 'alice, bob, eve coauthored paper_diffusion'")
    print("  would require 6 separate edges (3 author-author + 3 author-paper).")
    print("  A single n-ary hyperedge captures the collective semantics:")
    print("  all three authors jointly produced one paper.")
    print()
    print("  The 'shares' edge connects all 6 lab members to gpu_cluster")
    print("  in a single edge. Removing a member means updating one edge,")
    print("  not N pairwise edges.")
    print()
    print("  Similarly, the 'funds' edge {grant_nsf} -> {paper_transformers,")
    print("  paper_rl_agent} captures one grant funding two papers — a")
    print("  one-to-many relationship that pairwise edges would split apart.")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
