# Spectral Analysis, Matrix Computations, and Graph Transformations

> Three scripts demonstrating how Hyper3 computes matrix representations of hypergraphs — incidence, adjacency, Laplacian, and normalized Laplacian — and how graph transformations (dual, line graph, bipartite) reveal structural properties invisible in the original representation.

## 1. The Approach

Spectral graph theory connects the structure of a graph to the eigenvalues and eigenvectors of its matrix representations. The Laplacian matrix is the central object: its eigenvalues encode the number of connected components (count of zero eigenvalues), cluster structure (spectral gap between small eigenvalues), and connectivity strength. Spectral embedding projects nodes into a coordinate space derived from eigenvectors, where cluster membership becomes geometric proximity.

For hypergraphs, the Laplacian generalizes beyond pairwise edges. An incidence matrix with shape (12, 22) — 12 nodes participating in 22 edges — produces a Laplacian whose eigenvalues reflect the multi-body connectivity. The hypergraph Laplacian accounts for edge cardinality and node degree simultaneously, capturing relationships that pairwise graph Laplacians cannot represent.

S-persistence adds a multi-resolution dimension. By varying a parameter `s` that controls how aggressively nodes are grouped, the analysis reveals which cluster structures are stable across resolutions and which dissolve. A structure that appears at `s=1` (1 component), splits into 10 components at `s=2`, and fragments into 22 at `s=3` has a clear hierarchy: the three-cluster structure at `s=2` is the natural resolution.

Graph transformations provide orthogonal views of the same data. The dual hypergraph swaps nodes and edges, making edge-overlap patterns visible as node neighborhoods. The line graph converts edges into nodes, making edge adjacency explicit. The bipartite graph separates node and edge identities into distinct partitions, enabling bipartite-specific algorithms.

## 2. Key Concepts

| Concept | What it is | Why it matters |
|---------|-----------|----------------|
| Incidence matrix | A matrix where rows are nodes, columns are edges, and entries indicate participation (signed for direction) | The foundational matrix from which adjacency, Laplacian, and all spectral quantities are derived |
| Hypergraph Laplacian | `L = D_v - H W D_e^{-1} H^T` — combines vertex degree, edge weights, and edge degrees | Eigenvalues reveal connected components, cluster count, and connectivity; generalizes the graph Laplacian to n-ary edges |
| Normalized Laplacian | `L_norm = D_v^{-1/2} L D_v^{-1/2}` — degree-normalized version | Eigenvalues bounded in [0, 2], making spectra comparable across graphs of different sizes |
| Spectral embedding | Projects nodes into a low-dimensional space using Laplacian eigenvectors | Nodes in the same cluster map to nearby coordinates; enables visualization and clustering |
| S-persistence | Multi-resolution analysis varying the grouping parameter `s` | Reveals which cluster structures are stable across resolutions and which dissolve |
| Dual hypergraph | Swaps nodes and edges — original edges become nodes, original nodes become edges | Makes edge-overlap structure visible; useful when edge relationships are the analysis target |
| Line graph | Each original edge becomes a node; edges connect when original edges share a node | Explicitly represents edge adjacency, enabling edge-centric algorithms |
| Bipartite graph | Nodes and edges become separate partitions; membership edges connect them | Separates node and edge identities, enabling bipartite projections and two-mode analysis |

## 3. Quick Start

```bash
# Spectral methods on a 12-node clustered hypergraph
.venv/bin/python examples/showcase/spectral_and_matrix/21_spectral_methods.py
```

```
nodes: 12, edges: 22
structure: 3 dense clusters (4 nodes each) with bridge edges

incidence matrix shape: (12, 22)
  rows (nodes): 12, cols (edges): 22
  non-zeros: 48

hypergraph Laplacian shape: (12, 12)
  eigenvalues (sorted): [-0.      0.1191  0.3346  6.      6.      6.3612]
  zero eigenvalues (= components): 1

spectral embeddings (dim=3):
  n0: [-0.314, 0.352, -0.156]
  n4: [-0.324, -0.084, 0.363]
  n8: [-0.256, -0.337, -0.248]

s-persistence analysis:
  s=1: 1 components
  s=2: 10 components
  s=3: 22 components
```

```bash
# Matrix computations on 5-6 node graphs
.venv/bin/python examples/showcase/spectral_and_matrix/28_matrix_computations.py
```

```
incidence matrix shape: (5, 4)
  nnz: 8, sparsity: 0.6000

Laplacian eigenvalues: [-0.     0.191  0.691  1.309  1.809]
normalized Laplacian eigenvalues: [-0.      0.1464  0.5     0.8536  1.    ]

n-ary incidence matrix shape: (6, 2)
  edge sizes: [3, 4], max edge order: 3
n-ary Laplacian eigenvalues: [-0.      0.4505  1.      5.      5.      5.5495]
```

```bash
# Graph transformations on a 4-node graph
.venv/bin/python examples/showcase/spectral_and_matrix/31_graph_transformations.py
```

```
original: nodes=4, edges=4
dual: nodes=4, edges=4
line graph: nodes=4, edges=5
bipartite graph: nodes=8, edges=8

original adjacency: shape=(4, 4), density=0.3333
original Laplacian eigenvalues: [-0.   0.5  1.5  2. ]
dual adjacency: shape=(4, 4), density=0.3333
```

## 4. Script Walkthroughs

### 4.1 Spectral Methods (`21_spectral_methods.py`)

**Graph construction** — 12 nodes in 3 groups (alpha: n0–n3, beta: n4–n7, gamma: n8–n11). Each group has dense intra-cluster edges (weight=3.0) plus two bridge edges (n0→n4, n4→n8) with weight=1.0. Two hyperedges connect node pairs across clusters (weight=5.0). Result: 12 nodes, 22 edges.

**Incidence matrix** — Shape (12, 22) with 48 non-zero entries. Each non-zero indicates a node's participation in an edge. The 48 non-zeros across 264 total entries give a sparse matrix — most nodes participate in a small fraction of edges.

**Hypergraph Laplacian** — The 12x12 Laplacian's diagonal (degree vector) starts at `[8.75, 8.25, 8.25, 8.25, 9.25]...`, reflecting weighted degrees. The sorted eigenvalues are `[-0., 0.1191, 0.3346, 6., 6., 6.3612]...`. The single zero eigenvalue confirms 1 connected component. The spectral gap between 0.3346 and 6.0 is large — this is the signature of strong cluster structure. In a graph with weak clusters, the small eigenvalues would be more evenly spaced.

**Spectral embedding** — Each node maps to a 3-dimensional vector. Nodes within the same group cluster together: n0 through n3 (alpha) have similar coordinates (first component near -0.30, second near 0.36), n4 through n7 (beta) cluster in a different region (second component near -0.08, third near 0.39), and n8 through n11 (gamma) form a third cluster. The bridge nodes n0 and n4 show coordinates at the boundary of their respective groups.

**S-persistence** — At `s=1`, all 12 nodes form 1 component (everything is connected). At `s=2`, this splits into 10 components — the three clusters fragment, with bridge nodes appearing in multiple small components. At `s=3`, there are 22 components — essentially every pair and singleton. The jump from 1 to 10 to 22 shows the three-cluster structure at `s=2` is transitional: the dense intra-cluster edges hold groups together at `s=1`, but the weaker bridge edges dissolve first.

### 4.2 Matrix Computations (`28_matrix_computations.py`)

**Incidence and adjacency on pairwise edges** — A 5-node path-like graph (v0→v1→v2→v3, v0→v4) produces an incidence matrix of shape (5, 4) with 8 non-zeros and sparsity 0.6000. The signed incidence matrix encodes direction: +1 for source participation, -1 for target. The adjacency matrix is symmetric with non-zero entries at (v0, v1), (v0, v4), (v1, v2), (v2, v3).

**Laplacian eigenvalues** — `[0.0, 0.191, 0.691, 1.309, 1.809]`. The single zero eigenvalue confirms one connected component. The Fiedler value (second-smallest eigenvalue) of 0.191 indicates weak overall connectivity — this is a path graph, which is the most fragile connected topology.

**Normalized Laplacian** — Eigenvalues `[0.0, 0.1464, 0.5, 0.8536, 1.0]`, bounded in [0, 1] for this graph (maximum possible is 2.0 for bipartite graphs). The normalization by `D_v^{-1/2}` makes these values comparable across graphs of different sizes and degrees.

**N-ary edges** — Adding hyperedges (one with 3 nodes, one with 4 nodes) to a 6-node graph changes the matrices. The 4-node edge creates a dense block in the adjacency matrix: nodes u0, u1, u2, u3 are all mutually adjacent (clique sub-block). The Laplacian eigenvalues shift to `[0.0, 0.4505, 1.0, 5.0, 5.0, 5.5495]` — the larger eigenvalues (5.0, 5.5495) reflect the strong connectivity within the 4-node hyperedge. The Fiedler value jumps from 0.191 to 0.4505, reflecting denser connectivity from the n-ary edges.

### 4.3 Graph Transformations (`31_graph_transformations.py`)

**Dual hypergraph** — The original graph has 4 nodes (v0–v3) and 4 edges (ab, bc, ac, cd). The dual swaps these: 4 dual nodes (e0–e3, one per original edge) and 4 dual edges (one per original node). In the dual, node e0 (originally edge ab) has neighbors e1 and e2 — meaning edges ab and bc share node v1, and edges ab and ac share node v0. The dual makes edge overlap patterns directly navigable.

**Line graph** — 4 nodes (one per original edge), 5 edges connecting edges that share a node. Edge ab connects to bc (share v1), ac (share v0), and bc connects to ac (share v2) and cd (share v2). The line graph has more edges than the original (5 vs 4) because multiple edge pairs share nodes.

**Bipartite graph** — 8 nodes (4 in the node partition, 4 in the edge partition) with 8 membership edges. Each original edge generates as many bipartite edges as its cardinality: edge ab generates v0--ab and v1--ab, edge bc generates v1--bc and v2--bc, and so on. The bipartite representation preserves all structural information while separating the two entity types.

**Matrix properties** — The original adjacency (4x4, density 0.3333) and dual adjacency (4x4, density 0.3333) have identical density because the dual of a graph with equal node and edge counts produces a same-sized matrix. The original Laplacian eigenvalues `[0.0, 0.5, 1.5, 2.0]` confirm one connected component with moderate spectral spread.

## 5. Key Metrics

| Metric | Script | Value |
|--------|--------|-------|
| Nodes (spectral graph) | 21 | 12 |
| Edges (spectral graph) | 21 | 22 |
| Incidence matrix shape | 21 | (12, 22) |
| Incidence non-zeros | 21 | 48 |
| Laplacian shape | 21 | (12, 12) |
| Laplacian eigenvalues (first 6) | 21 | [0.0, 0.1191, 0.3346, 6.0, 6.0, 6.3612] |
| Connected components | 21 | 1 |
| S-persistence: s=1 components | 21 | 1 |
| S-persistence: s=2 components | 21 | 10 |
| S-persistence: s=3 components | 21 | 22 |
| Nodes (matrix graph, pairwise) | 28 | 5 |
| Edges (matrix graph, pairwise) | 28 | 4 |
| Incidence shape (pairwise) | 28 | (5, 4) |
| Incidence nnz | 28 | 8 |
| Incidence sparsity | 28 | 0.6000 |
| Laplacian eigenvalues (pairwise) | 28 | [0.0, 0.191, 0.691, 1.309, 1.809] |
| Normalized Laplacian eigenvalues | 28 | [0.0, 0.1464, 0.5, 0.8536, 1.0] |
| Nodes (matrix graph, n-ary) | 28 | 6 |
| N-ary edge sizes | 28 | [3, 4] |
| Max edge order (n-ary) | 28 | 3 |
| N-ary Laplacian eigenvalues | 28 | [0.0, 0.4505, 1.0, 5.0, 5.0, 5.5495] |
| Nodes (transformations) | 31 | 4 |
| Edges (transformations) | 31 | 4 |
| Dual nodes | 31 | 4 |
| Dual edges | 31 | 4 |
| Line graph nodes | 31 | 4 |
| Line graph edges | 31 | 5 |
| Bipartite nodes | 31 | 8 |
| Bipartite edges | 31 | 8 |
| Original adjacency density | 31 | 0.3333 |
| Dual adjacency density | 31 | 0.3333 |
| Original Laplacian eigenvalues | 31 | [0.0, 0.5, 1.5, 2.0] |

## 6. What Makes This Different

**Hypergraph Laplacian generalizes the graph Laplacian to n-ary edges.** A standard graph Laplacian assumes edges connect exactly two nodes. The hypergraph Laplacian `L = D_v - H W D_e^{-1} H^T` accounts for edge cardinality through `D_e^{-1}`, which down-weights the contribution of high-cardinality edges. This matters because a 4-node hyperedge should not contribute the same per-node weight as a pairwise edge — the normalization by edge degree corrects for this. The n-ary example (script 28) shows how a single 4-node edge produces a dense clique sub-block in the adjacency matrix and shifts the Laplacian eigenvalue spectrum.

**S-persistence provides multi-resolution cluster analysis.** Standard spectral clustering fixes `k` (the number of clusters) and computes a single partition. S-persistence varies the resolution parameter `s` and tracks how components form and dissolve. The 12-node graph shows 1→10→22 components as `s` increases from 1 to 3. The natural cluster count (3) appears implicitly as the resolution where dense intra-cluster edges survive but inter-cluster bridges dissolve. Without s-persistence, choosing `k` requires external knowledge or heuristics.

**Signed incidence matrices encode edge direction.** The incidence matrix uses +1 for source participation and -1 for target participation, distinguishing direction. This matters for directed hypergraphs where the source-target distinction carries semantic meaning (e.g., causal relationships). An unsigned incidence matrix would conflate these roles.

**Graph transformations are first-class operations.** Dual, line graph, and bipartite conversion produce new `Hypergraph` or `networkx.Graph` objects that support the full matrix API. The dual of the 4-node graph has identical density (0.3333) to the original, which is a structural property of self-dual-like configurations. Computing Laplacian eigenvalues on transformed graphs reveals properties invisible in the original representation — the dual's spectrum tells you about edge overlap, not node connectivity.

## 7. Code Implementation

**Compute the incidence matrix and Laplacian:**

```python
from hyper3 import Hypergraph, Hypernode, Hyperedge

g = Hypergraph()
nodes = [g.add_node(Hypernode(label=f"v{i}")) for i in range(5)]
g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))

H, node_ids, edge_ids = g.incidence_matrix()
L = g.hypergraph_laplacian()
eigenvalues = np.sort(np.linalg.eigvalsh(L))
```

**Spectral embedding and s-persistence:**

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
for i in range(12):
    mem.store(f"n{i}")

embeddings = mem.spectral_embedding(dimensions=3)
sp = mem.s_persistence(max_s=3)
for entry in sp.levels:
    print(f"s={entry['s']}: {entry['num_components']} components")
```

**Dual, line graph, and bipartite transformations:**

```python
dual = g.to_dual()
lg = g.to_line_graph()
bp = g.to_bipartite_graph()

A_dual, _ = dual.adjacency_matrix()
L_dual = dual.hypergraph_laplacian()
```

## 8. Reference

### API Methods

| Method | Class | Returns | Description |
|--------|-------|---------|-------------|
| `incidence_matrix()` | `Hypergraph` | `(ndarray, list[str], list[str])` | Signed incidence matrix with node/edge ID ordering |
| `incidence_matrix_unsigned()` | `Hypergraph` | `(ndarray, list[str], list[str])` | Unsigned incidence matrix (binary participation) |
| `adjacency_matrix()` | `Hypergraph` | `(matrix, list[str])` | Node-to-node adjacency matrix |
| `hypergraph_laplacian()` | `Hypergraph` | `ndarray` | `L = D_v - H W D_e^{-1} H^T` |
| `normalized_laplacian()` | `Hypergraph` | `(ndarray, list[str])` | Degree-normalized Laplacian |
| `spectral_embedding(dimensions)` | `HypergraphMemory` | `dict[str, ndarray]` | Node label to embedding vector |
| `s_persistence(max_s)` | `HypergraphMemory` | `SPersistenceResult` | Multi-resolution component analysis |
| `to_dual()` | `Hypergraph` | `Hypergraph` | Dual hypergraph (edges become nodes) |
| `to_line_graph()` | `Hypergraph` | `networkx.Graph` | Edge-adjacency graph |
| `to_bipartite_graph()` | `Hypergraph` | `networkx.Graph` | Two-partition node/edge membership graph |
| `unique_edge_sizes()` | `Hypergraph` | `list[int]` | Distinct edge cardinalities |
| `max_edge_order()` | `Hypergraph` | `int` | Largest edge cardinality minus 1 |
| `density()` | `Hypergraph` | `float` | Edge fraction relative to maximum possible |

### Laplacian eigenvalue interpretation

| Eigenvalue pattern | Meaning |
|-------------------|---------|
| Count of zero eigenvalues | Number of connected components |
| Small Fiedler value (2nd eigenvalue) | Weak connectivity; graph is close to disconnecting |
| Large spectral gap between eigenvalue k and k+1 | Strong k-cluster structure |
| Eigenvalues clustered near a single value | Regular or near-regular graph |

### Scripts in this showcase

| Script | Nodes | Focus |
|--------|-------|-------|
| `21_spectral_methods.py` | 12 | Laplacian, spectral embedding, s-persistence |
| `28_matrix_computations.py` | 5–6 | Incidence, adjacency, normalized Laplacian, n-ary effects |
| `31_graph_transformations.py` | 4 | Dual, line graph, bipartite, cross-transformation matrices |

### Real-World Gap

- **Scale**: These examples run on 4–12 node graphs. Spectral decomposition of the Laplacian is O(n^3) for dense matrices. At 10K+ nodes, approximate methods (Lanczos, randomized SVD) would be needed.
- **Data pipeline**: Graphs are constructed programmatically. Real use requires loading data from databases, log files, or knowledge bases.
- **Cluster validation**: S-persistence reveals cluster structure at multiple resolutions, but selecting the "right" resolution for a downstream task requires domain judgment.
- **Edge semantics**: The Laplacian treats all edges uniformly after weighting. Directed edges with different semantic types (causal, hierarchical, associative) may require separate Laplacians or weighted combinations.
