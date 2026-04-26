"""
Graph Analytics
===============

This example demonstrates Hyper3's graph analytics capabilities:
centrality measures, cycle detection, connected components,
path finding, and degree distribution.

Use case: Social network analysis. An analyst wants to identify
influencers, communities, and information flow paths in an
organizational communication network.

Run with:
    .venv/bin/python examples/intermediate/06_graph_analytics.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, Modality


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Building a Social Network
    # =====================================================================
    # We model an organization's communication network: people and
    # their communication channels.

    print("=" * 70)
    print("SECTION 1: Building Organizational Network")
    print("=" * 70)

    people = {
        "alice": {"role": "cto", "department": "leadership"},
        "bob": {"role": "vp_engineering", "department": "engineering"},
        "carol": {"role": "vp_product", "department": "product"},
        "dave": {"role": "senior_engineer", "department": "engineering"},
        "eve": {"role": "senior_engineer", "department": "engineering"},
        "frank": {"role": "product_manager", "department": "product"},
        "grace": {"role": "designer", "department": "design"},
        "heidi": {"role": "data_scientist", "department": "data"},
        "ivan": {"role": "devops_engineer", "department": "engineering"},
        "judy": {"role": "qa_engineer", "department": "engineering"},
        "karl": {"role": "ml_engineer", "department": "data"},
        "laura": {"role": "frontend_engineer", "department": "engineering"},
        "mike": {"role": "backend_engineer", "department": "engineering"},
        "nancy": {"role": "security_engineer", "department": "security"},
        "oscar": {"role": "sre", "department": "engineering"},
    }
    for name, data in people.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    # Communication channels
    comms = [
        ("alice", "bob", "manages"),
        ("alice", "carol", "manages"),
        ("bob", "dave", "manages"),
        ("bob", "eve", "manages"),
        ("bob", "ivan", "manages"),
        ("bob", "judy", "manages"),
        ("bob", "laura", "manages"),
        ("bob", "mike", "manages"),
        ("bob", "oscar", "manages"),
        ("carol", "frank", "manages"),
        ("carol", "grace", "manages"),
        ("frank", "grace", "collaborates"),
        ("dave", "eve", "collaborates"),
        ("dave", "ivan", "collaborates"),
        ("eve", "laura", "collaborates"),
        ("eve", "mike", "collaborates"),
        ("heidi", "karl", "collaborates"),
        ("heidi", "dave", "consults"),
        ("karl", "mike", "consults"),
        ("nancy", "ivan", "consults"),
        ("nancy", "oscar", "collaborates"),
        ("ivan", "oscar", "collaborates"),
        ("judy", "dave", "tests_for"),
        ("judy", "eve", "tests_for"),
        ("judy", "laura", "tests_for"),
        ("alice", "heidi", "consults"),
        ("alice", "nancy", "consults"),
        ("grace", "laura", "collaborates"),
        ("frank", "dave", "communicates"),
        ("frank", "eve", "communicates"),
    ]
    for src, tgt, label in comms:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} people, {mem.graph.edge_count} communication channels")
    print()

    # =====================================================================
    # SECTION 2: Degree Centrality (Influence)
    # =====================================================================
    # Degree centrality measures how many connections a node has.
    # High degree = more connections = more influence.

    print("=" * 70)
    print("SECTION 2: Degree Centrality (Influence Measurement)")
    print("=" * 70)

    centrality = mem.degree_centrality_labels()
    sorted_centrality = sorted(centrality.items(), key=lambda x: -x[1])
    print("  Degree centrality (higher = more connected):")
    for name, score in sorted_centrality:
        bar = "#" * int(score * 40)
        print(f"    {name:10s} {score:.3f} {bar}")
    print()

    # =====================================================================
    # SECTION 3: Betweenness Centrality (Brokerage)
    # =====================================================================
    # Betweenness centrality measures how often a node lies on the
    # shortest path between other nodes. High betweenness = information
    # broker / bottleneck.

    print("=" * 70)
    print("SECTION 3: Betweenness Centrality (Information Brokerage)")
    print("=" * 70)

    betweenness = mem.betweenness_centrality_labels()
    sorted_betweenness = sorted(betweenness.items(), key=lambda x: -x[1])
    print("  Betweenness centrality (higher = more brokerage):")
    for name, score in sorted_betweenness:
        if score > 0:
            bar = "#" * int(score * 40)
            print(f"    {name:10s} {score:.3f} {bar}")
    print()

    # =====================================================================
    # SECTION 4: Connected Components (Communities)
    # =====================================================================
    # Connected components identify isolated groups.

    print("=" * 70)
    print("SECTION 4: Connected Components (Communities)")
    print("=" * 70)

    components = mem.connected_components_labels()
    print(f"  Found {len(components)} connected components:")
    for i, comp in enumerate(components):
        print(f"    Component {i+1}: {sorted(comp)}")
    print()

    # =====================================================================
    # SECTION 5: Cycle Detection
    # =====================================================================
    # Cycles indicate circular dependencies or feedback loops.

    print("=" * 70)
    print("SECTION 5: Cycle Detection (Feedback Loops)")
    print("=" * 70)

    has_cycles = mem.has_cycle()
    print(f"  Graph has cycles: {has_cycles}")

    if has_cycles:
        cycles = mem.detect_cycles_labels(max_cycles=5)
        print(f"  Found {len(cycles)} cycles (showing up to 5):")
        for i, cycle in enumerate(cycles):
            print(f"    Cycle {i+1}: {' -> '.join(cycle)} -> {cycle[0]}")
    print()

    # =====================================================================
    # SECTION 6: Path Finding
    # =====================================================================
    # Find communication paths between any two people.

    print("=" * 70)
    print("SECTION 6: Communication Paths")
    print("=" * 70)

    # Shortest path from heidi to grace
    shortest = mem.shortest_path_labels("heidi", "grace")
    if shortest:
        print(f"  Shortest path from heidi to grace:")
        print(f"    {' -> '.join(shortest)}")

    # All paths from karl to alice
    paths = mem.find_paths_labels("karl", "alice", max_depth=5, max_paths=5)
    print(f"\n  All paths from karl to alice (up to 5):")
    for i, path in enumerate(paths):
        print(f"    Path {i+1} (length {len(path)}): {' -> '.join(path)}")
    print()

    # =====================================================================
    # SECTION 7: Degree Distribution
    # =====================================================================
    # Shows how many nodes have each degree (number of connections).

    print("=" * 70)
    print("SECTION 7: Degree Distribution")
    print("=" * 70)

    dist = mem.degree_distribution()
    print("  Degree distribution:")
    for degree in sorted(dist.keys()):
        count = dist[degree]
        bar = "#" * count
        print(f"    degree {degree:2d}: {count:2d} nodes {bar}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    top_influencer = sorted_centrality[0]
    top_broker = sorted_betweenness[0]
    print(f"  Most connected: {top_influencer[0]} (degree centrality={top_influencer[1]:.3f})")
    print(f"  Top information broker: {top_broker[0]} (betweenness={top_broker[1]:.3f})")
    print(f"  Communities: {len(components)}")
    print(f"  Has feedback loops: {has_cycles}")
    print()


if __name__ == "__main__":
    main()
