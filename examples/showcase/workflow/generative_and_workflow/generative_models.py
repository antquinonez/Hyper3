"""
Generative Models: Building Random Hypergraphs
==============================================
Parallels XGI Tutorial 4 (generative models).

Demonstrates Hyper3's generator functions for creating random, structured,
and clustered hypergraphs. Each generator produces a Hypergraph with
reproducible random structure via seed parameters.

Run: .venv/bin/python examples/showcase/workflow/generative_and_workflow/27_generative_models.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: random_hypergraph (Erdos-Renyi)")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.random_hypergraph(n=15, ps={2: 0.3, 3: 0.1})")

    from hyper3 import random_hypergraph

    g1 = random_hypergraph(15, {0: 0.3, 1: 0.1}, seed=42)
    print(f"\nnodes: {g1.node_count}, edges: {g1.edge_count}")

    deg_dist = g1.degree_distribution()
    print(f"degree distribution: {dict(sorted(deg_dist.items()))}")

    print(f"unique edge sizes: {g1.unique_edge_sizes()}")
    print(f"max edge order: {g1.max_edge_order()}")
    print(f"is connected: {g1.is_connected()}")

    g2 = random_hypergraph(20, {0: 0.5}, seed=7)
    print(f"\npairwise-only: nodes={g2.node_count}, edges={g2.edge_count}")
    print(f"is connected: {g2.is_connected()}")

    print("\n" + "=" * 70)
    print("SECTION 2: random_uniform_hypergraph (k-uniform)")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.uniform_erdos_renyi_hypergraph(n=10, m=8, k=3)")

    from hyper3 import random_uniform_hypergraph

    g3 = random_uniform_hypergraph(10, 8, 3, seed=42)
    print(f"\nnodes: {g3.node_count}, edges: {g3.edge_count}")
    print(f"unique edge sizes: {g3.unique_edge_sizes()}")

    node_labels = sorted(n.label for n in g3.nodes)
    print(f"node labels: {node_labels}")

    deg_dist3 = g3.degree_distribution()
    print(f"degree distribution: {dict(sorted(deg_dist3.items()))}")

    print("\n" + "=" * 70)
    print("SECTION 3: random_sbm (Stochastic Block Model)")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.uniform_HSBM(n=30, k=2, sizes=[15, 15], p=0.5, q=0.01)")

    from hyper3 import random_sbm

    g4 = random_sbm(20, 2, [10, 10], p_in=0.6, p_out=0.05, seed=42)
    print(f"\nnodes: {g4.node_count}, edges: {g4.edge_count}")
    print(f"density: {g4.density():.4f}")

    components = g4.connected_components()
    print(f"connected components: {len(components)}")
    for i, comp in enumerate(components):
        labels = sorted(g4.get_node(nid).label for nid in comp if g4.get_node(nid))
        print(f"  component {i}: {labels}")

    print("\n" + "=" * 70)
    print("SECTION 4: complete_hypergraph and star_hypergraph")
    print("=" * 70)

    from hyper3 import complete_hypergraph, star_hypergraph

    g5 = complete_hypergraph(5)
    print(f"\ncomplete(5): nodes={g5.node_count}, edges={g5.edge_count}")
    print(f"  density: {g5.density():.4f}")
    print(f"  is connected: {g5.is_connected()}")

    g6 = complete_hypergraph(4, order=2)
    print(f"\ncomplete(4, order=2): nodes={g6.node_count}, edges={g6.edge_count}")
    print(f"  unique edge sizes: {g6.unique_edge_sizes()}")

    g7 = star_hypergraph(7)
    print(f"\nstar(7): nodes={g7.node_count}, edges={g7.edge_count}")

    center = g7.get_node_by_label("n0")
    if center:
        center_deg = len(g7.incident_edges(center.id))
        print(f"  center degree: {center_deg}")

    print("\n" + "=" * 70)
    print("SECTION 5: ring_lattice")
    print("=" * 70)

    from hyper3 import ring_lattice

    g8 = ring_lattice(8, 2, 3, prefix="v")
    print(f"\nring(8, d=2, k=3): nodes={g8.node_count}, edges={g8.edge_count}")
    print(f"  unique edge sizes: {g8.unique_edge_sizes()}")

    g9 = ring_lattice(10, 4, 2, prefix="r")
    print(f"\nring(10, d=4, k=2): nodes={g9.node_count}, edges={g9.edge_count}")
    print(f"  is connected: {g9.is_connected()}")

    print("\n" + "=" * 70)
    print("SECTION 6: random_chung_lu (Configuration Model)")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.chung_lu_hypergraph(k1, k2)")

    from hyper3 import random_chung_lu

    k1 = [3, 3, 3, 2, 2, 1, 1, 1]
    k2 = [2, 2, 3, 3]
    g10 = random_chung_lu(8, k1, k2, seed=42)
    print(f"\nchung_lu(n=8): nodes={g10.node_count}, edges={g10.edge_count}")
    print(f"  unique edge sizes: {g10.unique_edge_sizes()}")

    print("\n" + "=" * 70)
    print("SECTION 7: ANALYSIS ON GENERATED GRAPHS")
    print("=" * 70)

    from hyper3.community import CommunityDetector
    from hyper3 import HypergraphMemory

    print("\n--- Community detection on SBM graph ---")
    sbm_detector = CommunityDetector(g4)
    sbm_cr = sbm_detector.detect_label_propagation(seed=42)
    print(f"  communities found: {sbm_cr.community_count}")
    print(f"  modularity: {sbm_cr.modularity:.4f}")
    for comm in sbm_cr.communities:
        labels = sorted(comm.member_labels)
        print(f"  community {comm.community_id}: {labels} (size={comm.size})")

    print("\n--- Reasoning on random graph ---")
    mem = HypergraphMemory(evolve_interval=0)
    for node in g1.nodes:
        mem.add(node.label, data={})
    for edge in g1.edges:
        srcs = list(edge.source_ids)
        tgts = list(edge.target_ids)
        if srcs and tgts:
            src_label = g1.get_node(srcs[0]).label if g1.get_node(srcs[0]) else srcs[0]
            tgt_label = g1.get_node(tgts[0]).label if g1.get_node(tgts[0]) else tgts[0]
            mem.link(src_label, tgt_label, label=edge.label or "link", weight=edge.weight)

    from hyper3.rules import TransitiveRule

    mem.add_rules(TransitiveRule(edge_label="link", new_label="inferred_link"))

    result = mem.reason(seeds={"n0"}, max_depth=2)
    print(f"\nreasoning on random_hypergraph from 'n0':")
    if result.expansion:
        print(f"  edges produced: {result.expansion.edges_produced}")
        print(f"  rules applied: {result.expansion.rules_applied}")
        print(f"  states created: {result.expansion.states_created}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
