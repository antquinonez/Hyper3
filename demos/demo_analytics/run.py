"""
Graph Analytics Walkthrough
===========================

Social/influence network analysis of a professional network. Computes
centrality metrics to identify key players, finds shortest paths, detects
structural properties (diameter, density, clustering), and explores
spectral embedding and s-persistence for multi-resolution analysis.

Key Hyper3 API demonstrated:
    - mem.analyze.centrality()  — degree, pagerank, betweenness, eigenvector
    - mem.analyze.shortest_path() — weighted shortest path
    - mem.analyze.paths()       — all paths between two nodes
    - mem.analyze.components()  — connected components
    - mem.analyze.is_connected()
    - mem.analyze.has_cycle() / mem.analyze.cycles()
    - mem.analyze.describe()    — graph summary
    - mem.analyze.diameter() / mem.analyze.radius() / mem.analyze.center()
    - mem.analyze.spectral_embedding()
    - mem.analyze.spersistence() — s-persistence filtration
    - mem.analyze.eccentricity()
    - mem.degree() / mem.in_degree() / mem.out_degree()

Supporting infrastructure:
    - data.py     — people, reporting, collaboration, mentorship edges
    - storage.py  — DuckDB for metric persistence and comparison queries

Run: .venv/bin/python demos/demo_analytics/run.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper3 import HypergraphMemory

try:
    from .data import PEOPLE, ALL_EDGES
    from .storage import open_db, store_node_metrics, store_topology, store_path, top_nodes, metric_comparison
except ImportError:
    from data import PEOPLE, ALL_EDGES
    from storage import open_db, store_node_metrics, store_topology, store_path, top_nodes, metric_comparison


def header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def main() -> None:
    print(
        """
    +------------------------------------------------------------------+
    |  GRAPH ANALYTICS WALKTHROUGH                                     |
    |  Scenario: Professional network analysis                         |
    +------------------------------------------------------------------+
    """
    )

    mem = HypergraphMemory(evolve_interval=0)
    db = open_db()

    # ── STEP 1: Build the professional network ───────────────────────
    #
    # People become nodes with role/department data. Edges encode three
    # relationship types: reporting (hierarchy), collaboration (peer),
    # and mentorship (cross-level). This creates a realistic org chart
    # with identifiable hubs (middle management) and bridges (PMs).
    #
    header("STEP 1: Building the professional network")

    for name, data in PEOPLE.items():
        mem.add(name, data=data)

    for src, tgt, label in ALL_EDGES:
        mem.link(src, tgt, label=label)

    desc = mem.analyze.describe()
    print(f"  Nodes: {desc.node_count}  |  Edges: {desc.edge_count}")
    print(f"  Density: {desc.density:.4f}")
    print(f"  Components: {desc.components}")
    print(f"  Degree range: {desc.degree_min} to {desc.degree_max} (mean={desc.degree_mean:.1f})")
    store_topology(db, {
        "node_count": desc.node_count,
        "edge_count": desc.edge_count,
        "density": desc.density,
        "components": desc.components,
    })

    # ── STEP 2: Degree centrality — who has the most connections? ────
    #
    # Degree counts the total number of edges incident to a node.
    # In-degree = incoming edges (who is managed/consulted).
    # Out-degree = outgoing edges (who manages/reaches out).
    # Total degree = overall connectivity.
    #
    header("STEP 2: Degree centrality — raw connection counts")

    deg = mem.degree()
    in_deg = mem.in_degree()
    out_deg = mem.out_degree()

    store_node_metrics(db, "total_degree", {k: float(v) for k, v in deg.items()})
    store_node_metrics(db, "in_degree", {k: float(v) for k, v in in_deg.items()})
    store_node_metrics(db, "out_degree", {k: float(v) for k, v in out_deg.items()})

    print("  Top-5 by total degree (most connected people):")
    for name, count in sorted(deg.items(), key=lambda x: -x[1])[:5]:
        print(f"    {name:12s}  degree={count}  in={in_deg[name]}  out={out_deg[name]}")

    print("\n  Why degree matters: high-degree nodes are communication hubs.")
    print("  Carol/Dave/Eve should rank high (middle management connects many people).")

    # ── STEP 3: PageRank — who is the most important? ────────────────
    #
    # PageRank weights connections by the importance of the connecting
    # node. A link from the CTO counts more than a link from an intern.
    # It uses the incidence-based transition matrix P = D_v^{-1} H W D_e^{-1} H^T.
    #
    header("STEP 3: PageRank — authority-weighted importance")

    pr = mem.analyze.centrality(method="pagerank", top_k=5)
    store_node_metrics(db, "pagerank", pr)

    print("  Top-5 by PageRank:")
    for name, score in sorted(pr.items(), key=lambda x: -x[1])[:5]:
        bar = "#" * int(score * 200)
        print(f"    {name:12s}  pagerank={score:.4f}  {bar}")

    print("\n  Why PageRank differs from degree: it captures quality of connections,")
    print("  not just quantity. Being linked from Alice (CTO) boosts your score more.")

    # ── STEP 4: Betweenness centrality — who are the bridges? ────────
    #
    # Betweenness measures how often a node appears on shortest paths
    # between other node pairs. High betweenness = information bottleneck
    # or bridge between communities.
    #
    header("STEP 4: Betweenness centrality — bridge nodes")

    bc = mem.analyze.centrality(method="betweenness", top_k=5)
    store_node_metrics(db, "betweenness", bc)

    print("  Top-5 by betweenness (bridge nodes):")
    for name, score in sorted(bc.items(), key=lambda x: -x[1])[:5]:
        bar = "#" * int(score * 100)
        print(f"    {name:12s}  betweenness={score:.4f}  {bar}")

    print("\n  Why betweenness matters: high-betweenness nodes control information flow.")
    print("  Removing them would fragment the network.")

    # ── STEP 5: Metric comparison via DuckDB ──────────────────────────
    #
    # All metrics have been stored in DuckDB. We can query it to produce
    # a comparison table showing how different metrics rank the same nodes.
    #
    header("STEP 5: Cross-metric comparison (via DuckDB)")

    comparison = metric_comparison(db, ["total_degree", "pagerank", "betweenness"], limit=5)
    print(f"  {'Node':12s}  {'Degree':>8s}  {'PageRank':>10s}  {'Betweenness':>12s}")
    print(f"  {'-' * 12}  {'-' * 8}  {'-' * 10}  {'-' * 12}")
    for row in comparison:
        deg_val = row.get('total_degree') or 0
        pr_val = row.get('pagerank') or 0
        bc_val = row.get('betweenness') or 0
        print(
            f"  {row['node']:12s}  {deg_val:>8.1f}  "
            f"{pr_val:>10.4f}  {bc_val:>12.4f}"
        )

    # ── STEP 6: Shortest paths — how are people connected? ───────────
    #
    # shortest_path() uses Dijkstra (weighted) or BFS (unweighted).
    # Edge weights represent importance: high weight = low cost = preferred.
    #
    header("STEP 6: Shortest paths")

    path_pairs = [
        ("alice", "heidi", "CTO to platform engineer (down the hierarchy)"),
        ("alice", "ivan", "CTO to ML engineer (down the hierarchy)"),
        ("oscar", "ivan", "QA to ML engineer (via carol/eve)"),
    ]
    for source, target, description in path_pairs:
        sp = mem.analyze.shortest_path(source, target)
        if sp:
            path_text = " -> ".join(sp)
            print(f"  {description}")
            print(f"    {source} -> {target}: {path_text}")
            store_path(db, source, target, path_text, "shortest_path")
        else:
            print(f"  {description}: no path found")

    # ── STEP 7: Connected components ──────────────────────────────────
    #
    # A connected component is a set of nodes where every pair is
    # reachable via edges. Most real-world networks have one giant
    # component and a few small ones.
    #
    header("STEP 7: Connected components")

    components = mem.analyze.components()
    print(f"  Number of components: {len(components)}")
    for i, comp in enumerate(components):
        roles = [PEOPLE.get(n, {}).get("role", n) for n in comp if n in PEOPLE]
        print(f"    Component {i}: {sorted(comp)}")
        print(f"      Roles: {', '.join(roles)}")

    is_conn = mem.analyze.is_connected()
    print(f"\n  Is fully connected: {is_conn}")

    # ── STEP 8: Structural topology ───────────────────────────────────
    #
    # Diameter: longest shortest path in the network.
    # Radius: minimum eccentricity (best-positioned node).
    # Center: nodes with eccentricity equal to the radius.
    # Periphery: nodes at the network edges.
    #
    header("STEP 8: Structural topology — diameter, radius, center")

    diameter = mem.analyze.diameter()
    radius = mem.analyze.radius()
    ecc = {label: mem.analyze.eccentricity(label) for label in PEOPLE}
    center = [n for n, e in ecc.items() if e == radius]
    periphery = [n for n, e in ecc.items() if e == diameter]

    print(f"  Diameter (longest shortest path): {diameter}")
    print(f"  Radius (min eccentricity): {radius}")
    print(f"  Center nodes (best positioned): {center}")
    print(f"  Periphery nodes (at the edges): {periphery}")

    store_topology(db, {"diameter": diameter, "radius": radius})

    print("\n  Interpretation:")
    print("    Diameter tells you the worst-case communication distance.")
    print("    Center nodes can reach everyone in the fewest hops.")
    print("    Periphery nodes are furthest from the rest of the network.")

    # ── STEP 9: Clustering coefficient ────────────────────────────────
    #
    # The local clustering coefficient measures how interconnected a
    # node's neighbors are. High clustering = tight-knit local community.
    # Low clustering = the node bridges different groups.
    #
    header("STEP 9: Clustering coefficient — local community density")

    avg_cc = mem.average_clustering_coefficient()
    print(f"  Average clustering coefficient: {avg_cc:.4f}")

    key_people = ["carol", "dave", "eve", "judy", "alice"]
    print(f"\n  Individual clustering coefficients:")
    for name in key_people:
        cc = mem.clustering_coefficient(name)
        role = PEOPLE.get(name, {}).get("role", "")
        print(f"    {name:12s} ({role:15s}): {cc:.4f}")

    store_topology(db, {"avg_clustering": avg_cc})

    print("\n  High clustering: neighbors know each other (tight team).")
    print("  Low clustering: neighbors don't know each other (bridge role).")

    # ── STEP 10: Spectral embedding ───────────────────────────────────
    #
    # Spectral embedding positions nodes in vector space using the
    # bottom-k eigenvectors of the normalized hypergraph Laplacian.
    # Nodes with similar connectivity patterns are placed close together.
    # This is the mathematical foundation for graph visualization and
    # similarity search.
    #
    header("STEP 10: Spectral embedding — 2D graph positions")

    embeddings = mem.analyze.spectral_embedding(dimensions=2)
    print("  Node positions in 2D spectral space:")
    for name in sorted(embeddings.keys()):
        vec = embeddings[name]
        role = PEOPLE.get(name, {}).get("role", "")
        print(f"    {name:12s} ({role:15s}): ({vec[0]:+.3f}, {vec[1]:+.3f})")

    print("\n  Nodes with similar connectivity patterns cluster in this space.")
    print("  Carol/Dave/Eve (middle management) should be near each other.")

    # ── STEP 11: s-persistence — multi-resolution structure ───────────
    #
    # s-persistence computes s-connected components for increasing values
    # of s. As s increases, components split, revealing multi-scale
    # community structure. s=1 means any edge overlap connects nodes.
    # s=2 requires 2+ shared edges for connectivity.
    #
    header("STEP 11: s-persistence — multi-resolution community structure")

    persistence = mem.analyze.spersistence(max_s=3)
    for level in persistence.levels:
        print(
            f"  s={level.s}: {level.num_components} components, "
            f"largest={level.largest_component_size} nodes"
        )

    print("\n  As s increases, components split into smaller, tighter groups.")
    print("  This reveals the hierarchical community structure of the network.")

    # ── STEP 12: Cycle detection and DAG analysis ─────────────────────
    header("STEP 12: Cycle detection")

    has_cycle = mem.analyze.has_cycle()
    print(f"  Has cycle: {has_cycle}")
    if has_cycle:
        cycles = mem.analyze.cycles(max_cycles=5)
        print(f"  Cycles detected: {len(cycles)}")
        for c in cycles[:3]:
            print(f"    {' -> '.join(c)} -> {c[0]}")
    else:
        print("  Graph is a DAG (directed acyclic graph).")

    # ── SUMMARY ──────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    print("""
    1. DEGREE         — Counts connections; identifies communication hubs
    2. PAGERANK       — Authority-weighted importance; connection quality
    3. BETWEENNESS    — Bridge nodes; information flow controllers
    4. CROSS-METRIC   — DuckDB comparison reveals how metrics disagree
    5. SHORTEST PATHS — Routes between people through the network
    6. COMPONENTS     — Connected subgroups in the network
    7. TOPOLOGY       — Diameter, radius, center, periphery
    8. CLUSTERING     — Local community density; tight vs bridging nodes
    9. SPECTRAL       — Embedding positions from Laplacian eigenvectors
    10. s-PERSISTENCE — Multi-resolution community structure
    11. CYCLES        — Whether the graph has feedback loops
    """)

    db.close()


if __name__ == "__main__":
    main()
