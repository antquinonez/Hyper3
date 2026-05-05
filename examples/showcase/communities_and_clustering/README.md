# Community Detection and Clustering

> Three scripts demonstrating label propagation communities, spectral clustering, and clustering coefficients on hypergraphs from 4 to 30 nodes.

## 1. The Approach

Real graphs have natural clusters — teams in an organization, subsystems in a codebase, regions in a network. Community detection finds these groups without prior labels. When you know which nodes belong together, you can reason about subsystem boundaries, identify bridge nodes between groups, and detect structural anomalies at group interfaces.

Clustering coefficients answer a different question: how densely interconnected are a node's neighbors? A node whose neighbors all know each other (high clustering) sits inside a tight-knit group. A node whose neighbors never connect (low clustering) may be a broker or bridge between groups. Together, community detection and clustering coefficients give a two-level view of graph structure — which groups exist and how cohesive they are.

This showcase runs three scripts:

- **`community_detection.py`** — Label propagation on a 14-node graph with 3 planted clusters and bridge edges
- **`spectral_clustering.py`** — Spectral clustering via Laplacian eigenvectors + k-means on a 30-node stochastic block model
- **`clustering_coefficient.py`** — Local and average clustering coefficients across triangle, chain, star, and complete topologies

## 2. Key Concepts

| Term | What it measures |
|------|-----------------|
| **Label propagation** | Iterative community detection: each node adopts the most common label among its neighbors. Fast, probabilistic — results depend on seed. |
| **Spectral clustering** | Partitions nodes using eigenvectors of the graph Laplacian. The number of near-zero eigenvalues reveals connected components; k-means on the first k eigenvectors produces k clusters. |
| **S-persistence** | Filters edges by minimum weight threshold (s-level). As s increases, weak edges disappear and the graph fragments. The rate of fragmentation reveals how many structural scales exist. |
| **Clustering coefficient** | Fraction of a node's neighbor pairs that are themselves connected. 1.0 means every neighbor pair has an edge; 0.0 means none do. |
| **Stochastic block model (SBM)** | Random graph generator with planted community structure. High intra-cluster edge probability (`p_in`), low inter-cluster probability (`p_out`). |
| **Modularity** | Quality score for a partition: how much more intra-community edge weight exists than expected by chance. Range [-0.5, 1.0]; higher is better. |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/communities_and_clustering/community_detection.py
```

```
nodes: 14, edges: 28
communities detected: 3
modularity: 0.5797
coverage: 0.9286
  community 0: ['a1', 'a2', 'a3', 'a4', 'a5'] (5 nodes)
  community 1: ['b1', 'b2', 'b3', 'b4', 'b5'] (5 nodes)
  community 2: ['c1', 'c2', 'c3', 'c4'] (4 nodes)
```

```bash
.venv/bin/python examples/showcase/communities_and_clustering/spectral_clustering.py
```

```
nodes: 30, edges: 105
density: 0.1207
number of clusters: 3
normalized Laplacian eigenvalues (first 5): [0.     0.0467 0.0795 0.3216 0.3707]
cluster agreement (greedy match): 100.00%
```

```bash
.venv/bin/python examples/showcase/communities_and_clustering/clustering_coefficient.py
```

```
       graph  avg_clustering
-------------------------------
    triangle          1.0000
       chain          0.0000
        star          0.0000
    complete          1.0000
```

## 4. Script Walkthroughs

### 4.1 Community Detection (`community_detection.py`)

The script builds a 14-node graph with three dense clusters (cluster_a: 5 nodes, cluster_b: 5 nodes, cluster_c: 4 nodes) connected by two bridge edges (`a1-b1` and `b5-c1`). Within each cluster, every pair of nodes connects with weight 5.0. Bridge edges use weight 1.0.

**Connected components** — The graph is fully connected (1 component, all 14 nodes). This confirms the bridges link all three clusters into one graph.

**Label propagation** — With `seed=42`, label propagation recovers all three planted communities exactly. Modularity 0.5797 indicates the partition captures substantially more intra-community structure than random. Coverage 0.9286 means 93% of edges fall within communities (the two bridge edges are the 7% that cross community boundaries).

**S-persistence** — The script analyzes structural resolution at three s-levels:
- `s=1`: 1 component, 14 nodes — the full graph
- `s=2`: 28 components, largest is 2 nodes — only the strongest edges survive
- `s=3`: 28 components, largest is 2 nodes — no additional fragmentation

The jump from 1 component at s=1 to 28 components at s=2 shows the graph has one structural scale: intra-cluster edges are strong (weight 5.0) and bridges are weak (weight 1.0). Raising the threshold above the bridge weight fragments the graph completely.

**Hyperedge-aware communities** — After adding two cross-team hyperedges (`{a1,a2,a3} -> {b1,b2}` and `{b3,b4} -> {c1,c2,c3}` with weight 10.0), label propagation collapses to 1 community with modularity 0.0000. The strong hyperedges create enough cross-cluster connectivity that label propagation can no longer separate the groups. This demonstrates how hyperedge weight can overwhelm community structure — a consideration when mixing pairwise and n-ary edges.

### 4.2 Spectral Clustering (`spectral_clustering.py`)

The script generates a 30-node stochastic block model with 3 blocks of 10 nodes each (`p_in=0.7`, `p_out=0.03`, `seed=42`). This produces 105 edges at density 0.1207 in a single connected component.

**Spectral clustering** — The normalized Laplacian's first 5 eigenvalues are `[0.0, 0.0467, 0.0795, 0.3216, 0.3707]`. There is 1 near-zero eigenvalue (matching the 1 connected component). The gap between eigenvalue 2 (0.0795) and eigenvalue 3 (0.3216) suggests 3 natural clusters — the k-means step projects nodes onto the first 3 eigenvectors and separates them.

Both spectral clustering and label propagation find 3 clusters of 10 nodes each. The greedy pairwise agreement is 100.00% — the two methods assign every node to the same cluster (possibly with different label ordering).

Why spectral clustering matters: label propagation relies on local neighbor voting and can miss global structure in sparse graphs. Spectral clustering uses the Laplacian's eigenvectors, which encode global connectivity patterns. The 100% agreement here confirms the SBM's community structure is strong enough for both methods to recover it. On weaker or noisier graphs, spectral clustering tends to be more robust.

### 4.3 Clustering Coefficient (`clustering_coefficient.py`)

The script constructs four canonical topologies and measures local clustering at every node:

| Topology | Nodes | Avg clustering | Why |
|----------|-------|---------------|-----|
| Triangle | 3 | 1.0000 | Every node's two neighbors are connected |
| Chain | 5 | 0.0000 | Interior nodes have 2 neighbors that are never directly connected |
| Star | 6 | 0.0000 | Hub's neighbors are disconnected; leaves have degree 1 (no neighbor pairs) |
| Complete | 4 | 1.0000 | Every possible edge exists |

Clustering coefficient is undefined for nodes with fewer than 2 neighbors (degree < 2), which return 0.0. In the star graph, the hub has 5 neighbors but none of those neighbors connect to each other, giving clustering 0.0. The leaves each have degree 1, also returning 0.0.

The script also builds a 4-node hypergraph with pairwise edges plus one n-ary hyperedge (`{a,b} -> {c,d}`, weight 5.0). All four nodes have clustering coefficient 1.0000 because the pairwise edges form a complete graph (a-b, b-c, c-d, d-a, a-c). The n-ary hyperedge does not affect clustering coefficient calculations — only pairwise edges contribute.

## 5. Key Metrics

| Script | Metric | Value |
|--------|--------|-------|
| `community_detection.py` | Nodes | 14 |
| | Edges | 28 |
| | Communities | 3 |
| | Modularity | 0.5797 |
| | Coverage | 0.9286 |
| | s=1 components | 1 (14 nodes) |
| | s=2 components | 28 (largest: 2 nodes) |
| | s=3 components | 28 (largest: 2 nodes) |
| | Post-hyperedge communities | 1 |
| | Post-hyperedge modularity | 0.0000 |
| `spectral_clustering.py` | Nodes | 30 |
| | Edges | 105 |
| | Density | 0.1207 |
| | Spectral clusters | 3 (10, 10, 10) |
| | Label propagation clusters | 3 (10, 10, 10) |
| | Near-zero eigenvalues | 1 |
| | Cluster agreement | 100.00% |
| | Modularity | 0.5581 |
| | Coverage | 0.8952 |
| `clustering_coefficient.py` | Triangle avg CC | 1.0000 |
| | Chain avg CC | 0.0000 |
| | Star avg CC | 0.0000 |
| | Complete avg CC | 1.0000 |
| | N-ary hypergraph avg CC | 1.0000 |

## 6. What Makes This Different

**S-persistence for multi-resolution analysis.** Rather than running community detection at a single resolution, s-persistence filters edges by weight threshold and tracks how the graph fragments. The 14-node graph goes from 1 component to 28 components between s=1 and s=2, revealing that the graph has a single dominant structural scale (intra-cluster weight 5.0 vs bridge weight 1.0). This is useful for understanding whether a graph has nested community structure (multiple plateaus) or a single clean partition (one sharp drop).

**Hyperedge-aware community detection.** Community detection operates on the full mixed graph — pairwise and n-ary edges contribute equally. Adding strong cross-cluster hyperedges (weight 10.0) collapses the three communities into one. This reveals a structural tension: hyperedges that span communities can pull detection toward a single-group solution. When mixing edge types, the relative weights between intra-community pairwise edges and cross-community hyperedges determine whether communities remain detectable.

**Clustering coefficients on hypergraphs.** The clustering coefficient implementation handles graphs that contain both pairwise and n-ary edges. The n-ary edges are excluded from clustering calculations (only pairwise edges form neighbor pairs), so the metric reflects the pairwise substructure. This is a design choice: including n-ary edges in neighbor counting would inflate the coefficient for nodes that participate in large hyperedges, even if their pairwise neighborhood is sparse.

## 7. Code Implementation

Label propagation community detection:

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
result = mem.detect_communities(seed=42)
print(f"communities: {result.community_count}")
print(f"modularity: {result.modularity:.4f}")
for community in result.communities:
    print(f"  {sorted(community.member_labels)} ({community.size} nodes)")
```

Spectral clustering on an SBM graph:

```python
from hyper3 import random_sbm

g = random_sbm(30, 3, [10, 10, 10], p_in=0.7, p_out=0.03, seed=42)
clusters = g.spectral_clustering(k=3)
for i, cluster in enumerate(clusters):
    print(f"  cluster {i}: {len(cluster)} nodes")
```

Clustering coefficient:

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
mem.ensure("a")
mem.ensure("b")
mem.ensure("c")
mem.relate("a", "b", label="e")
mem.relate("b", "c", label="e")
mem.relate("c", "a", label="e")

cc = mem.clustering_coefficient("a")     # 1.0
avg = mem.average_clustering_coefficient() # 1.0
```

## 8. Reference

### API Methods

| Method | Class | Returns | Notes |
|--------|-------|---------|-------|
| `detect_communities(seed=)` | `HypergraphMemory` | `CommunityResult` | Label propagation; probabilistic, set seed for reproducibility |
| `connected_components()` | `HypergraphMemory` | `list[list[str]]` | Labels of nodes in each connected component |
| `s_persistence(max_s=)` | `HypergraphMemory` | `SPersistenceResult` | Multi-resolution analysis via weight thresholds |
| `hyperedge_neighbors(concept)` | `HypergraphMemory` | `dict[str, list]` | Nodes sharing n-ary hyperedges with the given concept |
| `random_sbm(n, k, sizes, p_in, p_out, seed=)` | module-level | `Hypergraph` | Stochastic block model generator |
| `spectral_clustering(k=)` | `Hypergraph` | `list[set[str]]` | Node ID sets, one per cluster |
| `normalized_laplacian()` | `Hypergraph` | `(ndarray, dict)` | Normalized Laplacian matrix and node index |
| `connected_components()` | `Hypergraph` | `list[set[str]]` | Node ID sets |
| `density()` | `Hypergraph` | `float` | Edge count / maximum possible edges |
| `is_connected()` | `Hypergraph` | `bool` | Single connected component check |
| `clustering_coefficient(concept)` | `HypergraphMemory` | `float` | Local coefficient for one node |
| `average_clustering_coefficient()` | `HypergraphMemory` | `float` | Mean across all nodes |
| `CommunityDetector(graph)` | module-level | detector | Standalone detector for direct use on `Hypergraph` |
| `detect_label_propagation(seed=)` | `CommunityDetector` | `CommunityResult` | Same algorithm as `mem.detect_communities()` |

### Real-World Gap

- **Scale**: These scripts run on 4–30 nodes. Performance at 10K+ nodes is untested.
- **Synthetic data**: All graphs are hand-constructed or generated by SBM. Real graphs have noisy labels, missing edges, and overlapping communities.
- **Non-determinism**: Label propagation is probabilistic. Different seeds may produce different community assignments, especially on graphs with weak community structure.
- **Hyperedge impact**: The scripts demonstrate that strong cross-community hyperedges can collapse community detection. Production use requires calibrating edge weights to preserve meaningful community boundaries.
- **Directed edges**: Clustering coefficients and community detection treat the graph as undirected for these computations. Directed community structure (e.g., feed-forward vs feedback groups) is not captured.
