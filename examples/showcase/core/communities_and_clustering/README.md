# Community Detection and Clustering

> Three scripts demonstrating label propagation communities, spectral clustering, and clustering coefficients — with community-aware clustering analysis and spreading activation — on hypergraphs from 3 to 30 nodes.

## 1. The Approach

Real graphs have natural clusters — teams in an organization, subsystems in a codebase, regions in a network. Community detection finds these groups without prior labels. When you know which nodes belong together, you can reason about subsystem boundaries, identify bridge nodes between groups, and detect structural anomalies at group interfaces.

Clustering coefficients answer a different question: how densely interconnected are a node's neighbors? A node whose neighbors all know each other (high clustering) sits inside a tight-knit group. A node whose neighbors never connect (low clustering) may be a broker or bridge between groups. Together, community detection and clustering coefficients give a two-level view of graph structure — which groups exist and how cohesive they are.

This showcase runs three scripts in a progression from global to local structure:

- **`community_detection.py`** — Label propagation on a 14-node graph with 3 planted clusters and bridge edges. Demonstrates that communities can be recovered from connectivity patterns alone.
- **`spectral_clustering.py`** — Spectral clustering via Laplacian eigenvectors + k-means on a 30-node stochastic block model. Demonstrates a mathematically grounded alternative that agrees with label propagation on clean data.
- **`clustering_coefficient.py`** — Local and average clustering coefficients across canonical topologies, community detection on a mixed graph, and spreading activation from the highest-clustering node. Demonstrates that local density and global grouping are complementary perspectives.

## 2. Key Concepts

| Term | What it measures |
|------|-----------------|
| **Label propagation** | Iterative community detection: each node adopts the most common label among its neighbors. Fast, probabilistic — results depend on seed. |
| **Spectral clustering** | Partitions nodes using eigenvectors of the graph Laplacian. The number of near-zero eigenvalues reveals connected components; k-means on the first k eigenvectors produces k clusters. |
| **S-persistence** | Filters edges by minimum weight threshold (s-level). As s increases, weak edges disappear and the graph fragments. The rate of fragmentation reveals how many structural scales exist. |
| **Clustering coefficient** | Fraction of a node's neighbor pairs that are themselves connected. 1.0 means every neighbor pair has an edge; 0.0 means none do. |
| **Stochastic block model (SBM)** | Random graph generator with planted community structure. High intra-cluster edge probability (`p_in`), low inter-cluster probability (`p_out`). |
| **Modularity** | Quality score for a partition: how much more intra-community edge weight exists than expected by chance. Range [-0.5, 1.0]; higher is better. |
| **Spreading activation** | Propagates a stimulus from a seed node through the graph, with activation strength decaying over distance. Reveals which nodes are reachable and how strongly connected they are to the seed. |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/core/communities_and_clustering/community_detection.py
```

```
nodes: 14, edges: 28
communities detected: 3
modularity: 0.6358
coverage: 0.9848
  community 0: ['a1', 'a2', 'a3', 'a4', 'a5'] (5 nodes)
  community 1: ['b1', 'b2', 'b3', 'b4', 'b5'] (5 nodes)
  community 2: ['c1', 'c2', 'c3', 'c4'] (4 nodes)
```

```bash
.venv/bin/python examples/showcase/core/communities_and_clustering/spectral_clustering.py
```

```
nodes: 30, edges: 105
density: 0.1207
number of clusters: 3
normalized Laplacian eigenvalues (first 5): [0.     0.0467 0.0795 0.3216 0.3707]
cluster agreement (greedy match): 100.00%
```

```bash
.venv/bin/python examples/showcase/core/communities_and_clustering/clustering_coefficient.py
```

```
       graph  avg_clustering
-------------------------------
    triangle          1.0000
       chain          0.0000
        star          0.0000
    complete          1.0000

community detection on mixed graph (non-deterministic; either outcome is typical):
  communities: 2 or 3 (varies across runs)
  modularity: 0.2392 or 0.5822

  Outcome A (2 communities, modularity 0.2392):
    community 5: ['a', 'b', 'c', 'd', 'e', 'f'] (size=6, avg_cc=0.7778)
    community 7: ['g', 'h'] (size=2, avg_cc=0.0000)

  Outcome B (3 communities, modularity 0.5822):
    community 0: ['a', 'b', 'c'] (size=3, avg_cc=0.7778)
    community 5: ['d', 'e', 'f'] (size=3, avg_cc=0.7778)
    community 7: ['g', 'h'] (size=2, avg_cc=0.0000)

stimulating highest-clustering node: 'a' (cc=1.0000)

activated nodes after spreading from 'a':
  c: energy=1.0000, cc=0.3333
  b: energy=0.9882, cc=1.0000
  d: energy=0.1644, cc=0.3333
  f: energy=0.1045, cc=1.0000
  e: energy=0.1045, cc=1.0000
```

## 4. Script Walkthroughs

### 4.1 Community Detection (`community_detection.py`)

The script builds a 14-node graph with three dense clusters (cluster_a: 5 nodes, cluster_b: 5 nodes, cluster_c: 4 nodes) connected by two bridge edges (`a1-b1` and `b5-c1`). Within each cluster, every pair of nodes connects with weight 5.0. Bridge edges use weight 1.0.

**Connected components** — The graph is fully connected (1 component, all 14 nodes). This confirms the bridges link all three clusters into one graph.

**Label propagation** — With `seed=42`, label propagation recovers all three planted communities exactly. Modularity 0.6358 indicates the partition captures substantially more intra-community structure than random. Coverage 0.9848 means 98% of edges fall within communities (the two bridge edges are the small fraction that cross community boundaries).

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

The script constructs four canonical topologies, measures local clustering at every node, then applies community detection and spreading activation to a mixed graph.

#### Sections 1-4: Canonical Topologies and Hypergraph Clustering

| Topology | Nodes | Avg clustering | Why |
|----------|-------|---------------|-----|
| Triangle | 3 | 1.0000 | Every node's two neighbors are connected |
| Chain | 5 | 0.0000 | Interior nodes have 2 neighbors that are never directly connected |
| Star | 6 | 0.0000 | Hub's neighbors are disconnected; leaves have degree 1 (no neighbor pairs) |
| Complete | 4 | 1.0000 | Every possible edge exists |

Clustering coefficient is undefined for nodes with fewer than 2 neighbors (degree < 2), which return 0.0. In the star graph, the hub has 5 neighbors but none of those neighbors connect to each other, giving clustering 0.0. The leaves each have degree 1, also returning 0.0.

The script also builds a 4-node hypergraph with pairwise edges plus one n-ary hyperedge (`{a,b} -> {c,d}`, weight 5.0). All four nodes have clustering coefficient 1.0000 because the pairwise edges form a complete graph (a-b, b-c, c-d, d-a, a-c). The n-ary hyperedge does not affect clustering coefficient calculations — only pairwise edges contribute.

#### Section 5: Community Detection on a Mixed Graph

The script constructs an 8-node mixed graph with two triangles (a-b-c and d-e-f), a reciprocal pair (g-h), and a single bridge edge (c-d, weight 1.0). Triangle and pair edges use weight 5.0.

Label propagation with `seed=42` produces one of two outcomes, varying across runs due to the algorithm's sensitivity to hash-based node ordering:

**Outcome A** — 2 communities (modularity 0.2392):

| Community | Nodes | Size | Avg CC | Why this grouping |
|-----------|-------|------|--------|-------------------|
| 5 | [a, b, c, d, e, f] | 6 | 0.7778 | Both triangles merge via the weak bridge (c-d) into one community |
| 7 | [g, h] | 2 | 0.0000 | Isolated pair with no path to the main cluster |

**Outcome B** — 3 communities (modularity 0.5822):

| Community | Nodes | Size | Avg CC | Why this grouping |
|-----------|-------|------|--------|-------------------|
| 0 | [a, b, c] | 3 | 0.7778 | First triangle: strong intra-cluster edges (weight 5.0) resist the weak bridge |
| 5 | [d, e, f] | 3 | 0.7778 | Second triangle: dense internal connections keep it separate |
| 7 | [g, h] | 2 | 0.0000 | Isolated pair with no path to the main cluster |

Both outcomes are valid. The graph sits at a decision boundary: the weak bridge (c-d, weight 1.0) is strong enough to sometimes merge the two triangles, but weak enough that label propagation can also separate them. The per-community average clustering is 0.7778 for each triangle community (whether separate or merged) — two pure triangle members have CC 1.0 while the bridge endpoints (c, d) have CC 0.3333 due to their extra cross-group neighbor.

Why this matters: this non-determinism is a feature of label propagation, not a bug. The algorithm makes locally-optimal label assignments that can tip either way near structural boundaries. If deterministic community assignments are needed, spectral clustering (see `spectral_clustering.py`) provides a more stable alternative.

#### Section 6: Spreading Activation from Highest-Clustering Node

The script computes clustering coefficients for all 8 nodes in the mixed graph:

| Node | CC | Role |
|------|----|------|
| a | 1.0000 | Pure triangle member |
| b | 1.0000 | Pure triangle member |
| e | 1.0000 | Pure triangle member |
| f | 1.0000 | Pure triangle member |
| c | 0.3333 | Triangle + bridge endpoint |
| d | 0.3333 | Triangle + bridge endpoint |
| g | 0.0000 | Isolated pair member |
| h | 0.0000 | Isolated pair member |

Node `a` is selected (highest CC, alphabetically first among ties at 1.0000) and stimulated with energy 1.0. After 3 iterations of spreading activation:

| Node | Activation | CC |
|------|-----------|----|
| c | 1.0000 | 0.3333 |
| b | 0.9882 | 1.0000 |
| d | 0.1644 | 0.3333 |
| f | 0.1045 | 1.0000 |
| e | 0.1045 | 1.0000 |

Activation reaches 5 nodes — the first triangle (a-b-c) and, through the bridge, the second triangle (d-e-f). Node c receives the highest activation despite having the lowest CC in the first triangle, because edge weights and network topology concentrate activation flow through it. The bridge (c-d, weight 1.0) allows some activation to reach the second triangle, but at much lower levels than the directly-connected first triangle.

Why this matters: clustering coefficient and spreading activation answer fundamentally different questions about the same graph. Clustering coefficient measures local density — "how tightly woven is this node's immediate neighborhood?" Spreading activation measures global reach — "how far does influence travel from this node?" A node like `a` has maximum local density (CC=1.0) but its activation dies off quickly beyond the first triangle because the weak bridge (c-d, weight 1.0) throttles flow. In contrast, a node like `c` has lower local density (CC=0.3333) but acts as a gateway between two triangles, making it a better target for information dissemination despite being less embedded in a single cluster. The two metrics together help identify nodes that are locally cohesive versus globally influential — a distinction invisible to either metric alone.

## 5. Key Metrics

| Script | Metric | Value |
|--------|--------|-------|
| `community_detection.py` | Nodes | 14 |
| | Edges | 28 |
| | Communities | 3 |
| | Modularity | 0.6358 |
| | Coverage | 0.9848 |
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
| | Mixed graph nodes | 8 |
| | Mixed graph communities | 2 or 3 (non-deterministic) |
| | Mixed graph modularity | 0.2392 (2 communities) or 0.5822 (3 communities) |
| | Triangle community avg CC | 0.7778 (both outcomes) |
| | Pair community avg CC | 0.0000 |
| | Activation seed node | a (CC=1.0000) |
| | Activated nodes (3 iterations) | 5 (b, c, d, e, f) |
| | Max activation (depth 1) | c: 1.0000 |

## 6. What Makes This Different

**S-persistence for multi-resolution analysis.** Rather than running community detection at a single resolution, s-persistence filters edges by weight threshold and tracks how the graph fragments. The 14-node graph goes from 1 component to 28 components between s=1 and s=2, revealing that the graph has a single dominant structural scale (intra-cluster weight 5.0 vs bridge weight 1.0). This is useful for understanding whether a graph has nested community structure (multiple plateaus) or a single clean partition (one sharp drop).

**Hyperedge-aware community detection.** Community detection operates on the full mixed graph — pairwise and n-ary edges contribute equally. Adding strong cross-cluster hyperedges (weight 10.0) collapses the three communities into one. This reveals a structural tension: hyperedges that span communities can pull detection toward a single-group solution. When mixing edge types, the relative weights between intra-community pairwise edges and cross-community hyperedges determine whether communities remain detectable.

**Clustering coefficients on hypergraphs.** The clustering coefficient implementation handles graphs that contain both pairwise and n-ary edges. The n-ary edges are excluded from clustering calculations (only pairwise edges form neighbor pairs), so the metric reflects the pairwise substructure. This is a design choice: including n-ary edges in neighbor counting would inflate the coefficient for nodes that participate in large hyperedges, even if their pairwise neighborhood is sparse.

**Community detection complementing clustering analysis.** Running community detection alongside clustering coefficients reveals how local density (CC) and global group structure (communities) interact. In the mixed graph, the two triangles may each form their own community (3 communities, modularity 0.5822) or merge into one via the weak bridge (2 communities, modularity 0.2392) — the outcome varies across runs. In either case, triangle communities have average clustering 0.7778 (pure members at CC 1.0, bridge endpoints at CC 0.3333), and the isolated pair has zero clustering. Community detection identifies the groups; clustering coefficient grades how cohesive each group is. Together they distinguish between tight-knit clusters and loosely-connected aggregations. The non-determinism itself is informative: it reveals that the weak bridge puts the graph near a structural decision boundary, where the triangles are neither clearly separate nor clearly connected.

**Spreading activation as a reachability probe.** Stimulating the highest-clustering node and observing which nodes receive activation reveals the effective neighborhood radius of dense clusters — but this radius is bounded by edge weights. Activation from node `a` reaches the first triangle (a, b, c) strongly and the second triangle (d, e, f) weakly through the bridge. The isolated pair (g, h) receives no activation at all, disconnected from the activation wavefront. This shows that high local clustering does not imply uniform global reachability — the weak bridge (weight 1.0) attenuates activation, though it does not fully block it. The gap between activation energy at node b (0.9882) and node d (0.1644) quantifies the bridge's throttling effect.

## 7. Code Implementation

Label propagation community detection:

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
result = mem.analyze.communities(seed=42)
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
mem.link("a", "b", label="e")
mem.link("b", "c", label="e")
mem.link("c", "a", label="e")

cc = mem.clustering_coefficient("a")     # 1.0
avg = mem.average_clustering_coefficient() # 1.0
```

Community detection with per-community clustering:

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
mem.add("a")
mem.add("b")
mem.add("c")
mem.link("a", "b", label="e", weight=5.0)
mem.link("b", "c", label="e", weight=5.0)
mem.link("c", "a", label="e", weight=5.0)

result = mem.analyze.communities(seed=42)
for comm in result.communities:
    avg_cc = sum(mem.clustering_coefficient(l) for l in comm.member_labels) / comm.size
    print(f"  community {comm.community_id}: avg_cc={avg_cc:.4f}")
```

Spreading activation from highest-clustering node:

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)

cc_values = {c: mem.clustering_coefficient(c) for c in ["a", "b", "c"]}
seed_node = max(cc_values, key=cc_values.get)

activated = mem.search.activate(seed_node, energy=1.0)
for act in activated:
    print(f"  {act.label}: energy={act.energy:.4f}")
```

## 8. Reference

### API Methods

| Method | Class | Returns | Notes |
|--------|-------|---------|-------|
| `mem.analyze.communities(seed=)` | `HypergraphMemory` | `CommunityResult` | Label propagation; probabilistic, set seed for reproducibility |
| `mem.connected_components()` | `HypergraphMemory` | `list[set[str]]` | Labels of nodes in each connected component |
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
| `mem.search.activate(concept, energy=)` | `HypergraphMemory` | `list[ActivationHit]` | Inject activation energy at a seed node |
| `mem.search.diffuse(concept, iterations=)` | `HypergraphMemory` | `list[ActivationHit]` | Propagate activation and return activated nodes with activation levels and depths |
| `clear_activations()` | `HypergraphMemory` | `None` | Reset all node activations to zero |
| `CommunityDetector(graph)` | module-level | detector | Standalone detector for direct use on `Hypergraph` |
| `detect_label_propagation(seed=)` | `CommunityDetector` | `CommunityResult` | Same algorithm as `mem.analyze.communities()` |

### Real-World Gap

- **Scale**: These scripts run on 3–30 nodes. Performance at 10K+ nodes is untested.
- **Synthetic data**: All graphs are hand-constructed or generated by SBM. Real graphs have noisy labels, missing edges, and overlapping communities.
- **Non-determinism**: Label propagation is probabilistic. Different seeds may produce different community assignments, especially on graphs with weak community structure. Even with the same seed, results can vary across process invocations due to hash-based node ordering. The mixed graph in `clustering_coefficient.py` produces 2 or 3 communities across runs with seed=42. Community IDs are arbitrary labels from the propagation process and vary between runs even with the same seed. If deterministic assignments are required, use spectral clustering instead.
- **Hyperedge impact**: The scripts demonstrate that strong cross-community hyperedges can collapse community detection. Production use requires calibrating edge weights to preserve meaningful community boundaries.
- **Directed edges**: Clustering coefficients and community detection treat the graph as undirected for these computations. Directed community structure (e.g., feed-forward vs feedback groups) is not captured.
- **Activation spread**: Spreading activation uses fixed iteration count and decay. Production use would require tuning decay rates, iteration depth, and convergence thresholds for the specific graph.
