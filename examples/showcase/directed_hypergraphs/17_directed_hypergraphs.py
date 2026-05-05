"""
Laminar Comparison: Directed Hypergraphs
=========================================
Parallels:
  - XGI: "Tutorial 7 - Directed Hypergraphs"
  - HNX: basic directed edges

Shows directed hyperedge construction, in/out degree,
source/target access, and extends with Hyper3's semantic
direction and inference.

Run: .venv/bin/python examples/showcase/directed_hypergraphs/17_directed_hypergraphs.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: DIRECTED HYPERGRAPH CONSTRUCTION — XGI pattern")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("DH = xgi.DiHypergraph()")
    print("DH.add_edge([{1,2,3}, {3,4}])  # tail={1,2,3}, head={3,4}")
    print("DH.edges.dimembers()  -> [({1,2,3}, {3,4})]")
    print("DH.edges.head()       -> [{3,4}]")
    print("DH.edges.tail()       -> [{1,2,3}]")

    print("\n--- Hyper3 ---")
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for node in ["enzyme_a", "enzyme_b", "enzyme_c", "substrate_x", "product_y"]:
        mem.store(node, data={"type": node.split("_")[0]})

    mem.relate("enzyme_a", "substrate_x", label="binds", weight=3.0)
    mem.relate("enzyme_b", "substrate_x", label="binds", weight=2.0)
    mem.relate("enzyme_c", "substrate_x", label="binds", weight=1.0)

    mem.relate("substrate_x", "product_y", label="catalyzes", weight=5.0)

    mem.relate_hyperedge(
        sources={"enzyme_a", "enzyme_b", "enzyme_c"},
        targets={"product_y"},
        label="cooperative_catalysis",
        weight=10.0,
    )

    print(f"nodes: {mem.graph.node_count}, edges: {mem.graph.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: IN-DEGREE / OUT-DEGREE — XGI pattern")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("DH.nodes.in_degree.asdict()")
    print("DH.nodes.out_degree.asdict()")

    in_deg = mem.in_degree()
    out_deg = mem.out_degree()

    print(f"\n{'concept':>14} {'out_deg':>8} {'in_deg':>8} {'total':>8}")
    print("-" * 44)
    for label in sorted(in_deg.keys()):
        print(f"{label:>14} {out_deg.get(label, 0):>8} {in_deg.get(label, 0):>8} {out_deg.get(label, 0) + in_deg.get(label, 0):>8}")

    print("\n" + "=" * 70)
    print("SECTION 3: SOURCE / TARGET ACCESS — XGI pattern")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("DH.edges.dimembers()  -> (tail, head) pairs")
    print("DH.edges.head_size    -> head cardinality")
    print("DH.edges.tail_size    -> tail cardinality")

    for e in mem.edges_labeled():
        print(f"  {e.label}: {set(e.source_labels)} -> {set(e.target_labels)}  (tail={e.source_cardinality}, head={e.target_cardinality})")

    print("\n" + "=" * 70)
    print("SECTION 4: HYPEREDGE NEIGHBORS (Hyper3 advantage)")
    print("=" * 70)

    co_neighbors = mem.hyperedge_neighbors("substrate_x")
    print(f"\nsubstrate_x co-participates in hyperedges with:")
    for neighbor, edges in co_neighbors.items():
        print(f"  {neighbor}: {len(edges)} shared hyperedge(s)")

    print("\n" + "=" * 70)
    print("SECTION 5: SEMANTIC DIRECTION + INFERENCE (Hyper3-only layer)")
    print("=" * 70)

    from hyper3.rules import TransitiveRule

    mem.add_rules(
        TransitiveRule(edge_label="catalyzes", new_label="enables_production"),
    )

    mem.store("downstream_product")
    mem.relate("product_y", "downstream_product", label="catalyzes", weight=3.0)

    result = mem.reason(seed_concepts={"substrate_x"}, max_depth=2)
    print(f"\nreasoning from 'substrate_x':")
    print(f"  edges produced: {result.expansion.edges_produced}")
    print(f"  rules applied: {result.expansion.rules_applied}")

    new_labeled = [(e.label, e.source_labels[0], e.target_labels[0]) for e in mem.edges_labeled(edge_label="enables_production") if e.source_labels and e.target_labels]
    for lbl, src, tgt in new_labeled:
        print(f"  inferred: {src} -[{lbl}]-> {tgt}")


if __name__ == "__main__":
    main()
