# 7. Analytics

Hyper3 provides graph analytics through the `mem.analyze` namespace. All
algorithms operate on the full hypergraph structure -- mixed pairwise and n-ary
edges are handled transparently.

## 7.1 Centrality

Centrality measures identify the most important nodes in a graph.

```python
pr = mem.analyze.centrality("pagerank", top_k=5)
for label, score in list(pr.items())[:5]:
    print(f"  {label}: {score:.4f}")
```

Available methods:

| Method | What it measures |
|--------|-----------------|
| `"pagerank"` | Influence propagation (incidence-based, Zhou 2006) |
| `"betweenness"` | How many shortest paths pass through each node |
| `"degree"` | Number of incident edges |
| `"in_degree"` | Number of edges where the node is a target |
| `"out_degree"` | Number of edges where the node is a source |
| `"closeness"` | Average inverse distance to all other nodes |
| `"eigenvector"` | Influence of neighbors, recursively |
| `"katz"` | Eigenvector centrality with a damping term |

All return a `dict[str, float]` mapping concept labels to scores. Use `top_k=N`
to return only the top N entries, or omit it for all nodes.

### Direction Matters for N-ary Edges

A node in the source set of a multi-source edge gets out-degree credit. A node
in the target set gets in-degree credit. For a node in both sets, it gets
contributions to both.

```
mem.analyze.centrality("in_degree")   # "how many edges point to this node"
mem.analyze.centrality("out_degree")  # "how many edges originate from this node"
```

These tell different stories. A node with high in-degree but low out-degree is a
convergence point (many things feed into it). The reverse is a broadcaster.

## 7.2 Paths and Connectivity

### Shortest Path

```python
paths = mem.analyze.paths("ATM", "cell_cycle_arrest")
```

Returns all paths between two concepts. An n-ary edge `{A, B} -> {C, D}` is a
single hop: A and B both reach C and D in distance 1.

### Single Shortest Path

```python
path = mem.analyze.shortest_path("A", "D", weighted=True)
```

Returns the lowest-cost path. Weighted mode inverts edge weights (high weight =
low cost = preferred).

### Graph Statistics

```python
desc = mem.analyze.describe()
print(f"{desc.node_count} nodes, {desc.edge_count} edges, density={desc.density:.4f}")
```

`describe()` returns degree statistics (min, max, mean, median), isolated node
count, component count, and density.

## 7.3 Community Detection

Communities are groups of nodes that are more densely connected to each other
than to the rest of the graph.

```python
comps = mem.analyze.communities(method="connected_components")
for c in comps.communities:
    labels = sorted(c.member_labels)
    print(f"  Community {c.community_id}: {labels} ({c.size} nodes)")
```

`communities()` returns a `CommunityResult` with:

| Field | Description |
|-------|-------------|
| `communities` | List of `Community` objects, each with `member_labels`, `size`, `internal_edges`, `external_edges` || `community_count` | Number of communities found |
| `modularity` | Modularity score (higher = better separation) |
| `coverage` | Fraction of nodes assigned to a community |

Available methods:

| Method | Deterministic? | Description |
|--------|---------------|-------------|
| `"connected_components"` | Yes | Union-find on hyperedge overlap |
| `"label_propagation"` | No | Iterative label voting with random tie-breaking |
| `"louvain"` | Yes | Modularity optimization |
| `"greedy_modularity"` | No | Greedy agglomeration |

### S-Connected Components

The `s` parameter controls the minimum vertex overlap threshold for
connectivity. Higher `s` produces more (smaller) components:

```python
comps_s1 = mem.analyze.components(s=1)  # standard: any shared edge
comps_s2 = mem.analyze.components(s=2)  # require 2 shared nodes
```

## 7.4 S-Persistence

`s_persistence()` computes s-connected components for `s = 1, 2, ..., max_s`
and tracks how the component structure fragments as `s` increases. This
reveals hierarchical structure in the hypergraph.

```python
sp = mem.s_persistence(max_s=3)
for level in sp.levels:
    print(f"s={level.s}: {level.num_components} components, largest={level.largest_component_size}")
```

```
s=1: 1 components, largest=8
s=2: 5 components, largest=4
s=3: 5 components, largest=4
```

At `s=1`, all nodes are in one broad component. As `s` increases, the
components fragment into smaller, more tightly-coupled groups. The progression
reveals hierarchical structure: broad clusters at low `s`, fine-grained
pathways at high `s`.

This is unique to Hyper3. No other framework in this space provides
multi-resolution component filtration on hypergraphs.

## 7.5 Spectral Methods

### Spectral Embedding

`spectral_embedding()` projects nodes into a coordinate space using the bottom-k
eigenvectors of the normalized hypergraph Laplacian
`L = I - D_v^{-1/2} H W D_e^{-1} H^T D_v^{-1/2}`.

```python
emb = mem.analyze.spectral_embedding(dimensions=8)
print(f"Embedded {len(emb)} nodes")
```

Nodes that co-participate in edges map to nearby coordinates. This embedding
powers `search.similar()` and `search.analogy()`.

### Spectral Clustering

```python
clusters = mem.analyze.spectral_clustering(k=3)
```

Partitions nodes into `k` clusters using the spectral embedding and k-means.

## 7.6 Structural Patterns

`mem.analyze` provides pattern detection for common graph motifs:

| Method | Pattern |
|--------|---------|
| `match_chains(label=..., min_length=3)` | Linear chains: A->B->C->D |
| `match_diamonds(label=...)` | Convergence: A and B both feed C |
| `match_fan_out(label=..., min_fan=3)` | Fan-out: A feeds B, C, D |

These use the n-ary edge structure directly -- a multi-source edge is itself a
diamond or fan-out pattern.

## 7.7 Cycles

```python
cycles = mem.analyze.cycles(max_cycles=10)
print(f"Found {len(cycles)} cycles")
```

`max_cycles` is a soft limit. The algorithm may return slightly more than N.
Use `detect_cycles()` for unbounded detection.

Next: [Self-Evolution](08-self-evolution.md)
