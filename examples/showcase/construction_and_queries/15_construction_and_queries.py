"""
Laminar Comparison: Hypergraph Construction & Basic Queries
============================================================
Parallels:
  - XGI: "XGI in 5 minutes" tutorial
  - HNX: "Basic 1 - HNX Basics"
  - NetworkX: basic graph construction

Shows how to build hypergraphs, add nodes/edges, query structure,
and access basic statistics in each library, then adds Hyper3-only
layers (metadata, modalities, semantics).

Run: .venv/bin/python examples/showcase/construction_and_queries/15_construction_and_queries.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: CONSTRUCTION — XGI / HNX / NetworkX patterns")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H = xgi.Hypergraph([[1,2,3], [3,4], [4,5,6,7]])")
    print("H.add_node(8)")
    print("H.add_edge([7, 8])")
    print(f"nodes: {len([1,2,3,4,5,6,7,8])}, edges: 4")

    print("\n--- HNX equivalent ---")
    print("h = hnx.Hypergraph({'e1': [1,2,3], 'e2': [3,4], 'e3': [4,5,6,7]})")
    print(f"nodes: 8, edges: 3")

    print("\n--- NetworkX equivalent (pairwise only) ---")
    print("G = nx.Graph()")
    print("G.add_edges_from([(1,3), (3,4), (4,5), (4,6), (4,7)])")
    print(f"nodes: 7, edges: 5 (pairwise, no n-ary)")

    print("\n--- Hyper3 ---")
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    mem.store("alice")
    mem.store("bob")
    mem.store("carol")
    mem.store("dave")
    mem.store("eve")
    mem.store("frank")
    mem.store("grace")
    mem.store("henry")

    mem.relate("alice", "bob", label="collaborates")
    mem.relate("bob", "carol", label="collaborates")
    mem.relate("carol", "dave", label="reports_to")
    mem.relate("dave", "eve", label="collaborates")
    mem.relate("dave", "frank", label="collaborates")
    mem.relate("dave", "grace", label="collaborates")
    mem.relate("grace", "henry", label="mentors")

    print(f"nodes: {mem.graph.node_count}, edges: {mem.graph.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: N-ARY HYPEREDGES (Hyper3 advantage)")
    print("=" * 70)

    mem.relate_hyperedge(
        sources={"alice", "bob", "carol"},
        targets={"dave"},
        label="joint_project",
    )
    mem.relate_hyperedge(
        sources={"dave"},
        targets={"eve", "frank", "grace", "henry"},
        label="team_assignment",
    )

    hyperedges = mem.edges_labeled(min_source_cardinality=2)
    print(f"\nN-ary hyperedges (source cardinality >= 2): {len(hyperedges)}")
    for he in hyperedges:
        print(f"  {he.label}: {set(he.source_labels)} -> {set(he.target_labels)}")

    print("\n" + "=" * 70)
    print("SECTION 3: BASIC QUERIES")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H.nodes  -> [0, 1, 2, ...]")
    print("H.edges.members()  -> [{0,9}, {0,10}, ...]")
    print("xgi.max_edge_order(H)  -> 2")
    print("xgi.unique_edge_sizes(H)  -> [2, 3]")

    print("\n--- Hyper3 ---")
    all_labels = [n.label for n in mem.graph.nodes]
    print(f"all nodes: {all_labels}")

    labeled = mem.graph.labeled_edges
    print(f"labeled edges: {[(e['label'], len(e.get('source_labels', []))) for e in labeled]}")

    desc = mem.describe()
    print(f"\ngraph description:")
    print(f"  nodes: {desc.node_count}")
    print(f"  edges: {desc.edge_count}")
    print(f"  edge labels: {desc.edge_labels}")
    print(f"  density: {desc.density:.4f}")
    print(f"  isolated nodes: {desc.isolated_nodes}")
    print(f"  components: {desc.components}")

    print("\n" + "=" * 70)
    print("SECTION 4: SEMANTIC METADATA (Hyper3-only layer)")
    print("=" * 70)

    mem.store("alice", data={"role": "engineer", "team": "platform", "level": 5})
    mem.store("dave", data={"role": "manager", "team": "platform", "level": 7})
    mem.store("eve", data={"role": "designer", "team": "ux", "level": 4})

    engineers = mem.query_nodes(data={"role": "engineer"})
    print(f"engineers: {engineers}")

    platform_team = mem.query_nodes(data={"team": "platform"})
    print(f"platform team: {platform_team}")

    print("\n" + "=" * 70)
    print("SECTION 5: NEIGHBORHOOD QUERIES")
    print("=" * 70)

    dave_neighbors_out = mem.neighbors("dave", direction="out")
    dave_neighbors_in = mem.neighbors("dave", direction="in")
    dave_neighbors_all = mem.neighbors("dave", direction="any")
    print(f"dave out-neighbors: {dave_neighbors_out}")
    print(f"dave in-neighbors: {dave_neighbors_in}")
    print(f"dave all-neighbors: {dave_neighbors_all}")

    collab_partners = mem.neighbors("dave", edge_label="collaborates")
    print(f"dave collaborators: {collab_partners}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
