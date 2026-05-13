"""
Hypergraph Construction, Queries, and Reasoning
================================================
Shows how to build hypergraphs, add nodes/edges, query structure,
access basic statistics, and then apply reasoning and evolution
to demonstrate Hyper3's adaptive capabilities.

Run: .venv/bin/python examples/showcase/core/construction_and_queries/construction_and_queries.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: CONSTRUCTION")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for name in ["alice", "bob", "carol", "dave", "eve", "frank", "grace", "henry"]:
        mem.add(name, data={})

    mem.link("alice", "bob", label="collaborates")
    mem.link("bob", "carol", label="collaborates")
    mem.link("carol", "dave", label="reports_to")
    mem.link("dave", "eve", label="collaborates")
    mem.link("dave", "frank", label="collaborates")
    mem.link("dave", "grace", label="collaborates")
    mem.link("grace", "henry", label="mentors")

    print(f"nodes: {mem.size[0]}, edges: {mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: N-ARY HYPEREDGES")
    print("=" * 70)

    mem.link_hyper(
        sources={"alice", "bob", "carol"},
        targets={"dave"},
        label="joint_project",
    )
    mem.link_hyper(
        sources={"dave"},
        targets={"eve", "frank", "grace", "henry"},
        label="team_assignment",
    )

    hyperedges = mem.analyze.edges(min_source_cardinality=2)
    print(f"\nN-ary hyperedges (source cardinality >= 2): {len(hyperedges)}")
    for he in hyperedges:
        print(f"  {he.label}: {set(he.source_labels)} -> {set(he.target_labels)}")

    print("\n" + "=" * 70)
    print("SECTION 3: BASIC QUERIES")
    print("=" * 70)

    all_labels = [n.label for n in mem.engine.graph.nodes]
    print(f"all nodes: {all_labels}")

    desc = mem.analyze.describe()
    print(f"\ngraph description:")
    print(f"  nodes: {desc.node_count}")
    print(f"  edges: {desc.edge_count}")
    print(f"  edge labels: {desc.edge_labels}")
    print(f"  density: {desc.density:.4f}")
    print(f"  isolated nodes: {desc.isolated_nodes}")
    print(f"  components: {desc.components}")

    print("\n" + "=" * 70)
    print("SECTION 4: SEMANTIC METADATA")
    print("=" * 70)

    mem.ensure("alice", data={"role": "engineer", "team": "platform", "level": 5}, update=True)
    mem.ensure("dave", data={"role": "manager", "team": "platform", "level": 7}, update=True)
    mem.ensure("eve", data={"role": "designer", "team": "ux", "level": 4}, update=True)

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
    print("SECTION 6: REASONING (Hyper3 advantage)")
    print("=" * 70)

    from hyper3 import TransitiveRule

    mem.add_rules(
        TransitiveRule(edge_label="collaborates", new_label="indirect_collaboration"),
    )

    result = mem.reason(seeds={"alice"}, max_depth=3)
    print(f"\nreasoning from 'alice':")
    print(f"  edges produced: {result.expansion.edges_produced}")
    print(f"  states created: {result.expansion.states_created}")

    indirect = [
        (e.label, e.source_labels[0], e.target_labels[0])
        for e in mem.analyze.edges(label="indirect_collaboration")
        if e.source_labels and e.target_labels
    ]
    if indirect:
        print(f"\nindirect collaborations inferred:")
        for lbl, src, tgt in indirect:
            print(f"  {src} -[{lbl}]-> {tgt}")
    else:
        print(f"\nno indirect collaborations inferred (need longer collaborates chains)")

    print("\n" + "=" * 70)
    print("SECTION 7: SELF-EVOLUTION (Hyper3 advantage)")
    print("=" * 70)

    before_nodes = mem.size[0]
    before_edges = mem.size[1]

    mem.search.activate("dave", energy=1.0)
    mem.cognitive.hebbian_reinforce()

    evolve_result = mem.evolve()
    print(f"\nevolution cycle:")
    print(f"  nodes before/after: {before_nodes}/{mem.size[0]}")
    print(f"  edges before/after: {before_edges}/{mem.size[1]}")
    print(f"  edges decayed: {evolve_result.decayed}")
    print(f"  nodes pruned: {evolve_result.pruned}")
    print(f"  nodes merged: {evolve_result.merged}")

    desc_after = mem.analyze.describe()
    print(f"\npost-evolution description:")
    print(f"  density: {desc_after.density:.4f}")
    print(f"  components: {desc_after.components}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
