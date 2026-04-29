# Hypergraph-Native Algorithm Migration

## Status: In Progress

## Problem

The `Hypergraph` data model correctly stores n-ary hyperedges (`source_ids` and `target_ids` are `frozenset[str]`), but almost every algorithm immediately decomposes them into pairwise edges via `to_networkx()` or inline `for src ... for tgt ...` cartesian products. The result: the "hypergraph" is a standard directed multigraph in practice.

- 7 NetworkX-based algorithms decompose to pairwise via `to_networkx()`
- 14+ files contain inline pairwise decomposition
- Only 1 rule (`GeneralizationRule`) ever creates a true n-ary edge
- The incidence matrix and hypergraph Laplacian have zero production consumers
- 4 methods assume singleton cardinality via `next(iter(...))`

## Decisions

- **Scope**: All four phases (API, algorithms, internal migration, new features)
- **Migration**: In-place replacement (existing methods replaced with hypergraph-native versions that degrade gracefully to pairwise behavior)
- **NetworkX**: Kept for visualization and graph isomorphism only; removed from all algorithm paths

## Phase 1: API -- Enable n-ary Edge Creation and Querying

### kernel.py additions

| Method | Signature | Purpose |
|---|---|---|
| `add_hyperedge` | `(source_ids: frozenset[str], target_ids: frozenset[str], *, label, weight, data, modality, abstraction_layer) -> Hyperedge` | Explicit n-ary edge creation. Thin wrapper over `add_edge`. |
| `star` | `(node_id: str) -> list[Hyperedge]` | Public alias for `edges_for()`. All edges incident to a node. |
| `directed_out_edges` | `(node_id: str) -> list[Hyperedge]` | Edges where `node_id in source_ids`. N-ary aware. |
| `directed_in_edges` | `(node_id: str) -> list[Hyperedge]` | Edges where `node_id in target_ids`. N-ary aware. |
| `hyperedge_neighbors` | `(node_id: str) -> dict[str, list[Hyperedge]]` | `{neighbor_id: [shared_edges]}` grouped by co-participating nodes. |

### memory_core.py additions

| Method | Signature | Purpose |
|---|---|---|
| `relate_hyperedge` | `(sources: set[str], targets: set[str], *, label, weight, **kw) -> Hyperedge` | Label-at-boundary wrapper for n-ary edge creation. |
| `query_hyperedges` | `(*, min_source_cardinality=1, min_target_cardinality=1, label=None, containing=None) -> list[Hyperedge]` | Filter edges by cardinality, label, node membership. |
| `hyperedge_neighbors` | `(concept: str) -> dict[str, list[Hyperedge]]` | Public wrapper returning co-participating concepts. |

## Phase 2: Native Hypergraph Algorithms (In-Place Replacement)

All replacements degrade to standard graph algorithms when all edges are pairwise.

### 2a. connected_components() -- s-connected components

Replace `nx.weakly_connected_components()` with native union-find via shared hyperedges.

Algorithm:
- For each edge e, take `all_nodes = e.source_ids | e.target_ids`
- Union all nodes in `all_nodes` (they share an edge, so they're connected)
- Extract connected components from union-find
- Add `s` parameter: require shared edges have overlap >= s to merge components

### 2b. shortest_path() -- Hypergraph s-shortest path

Build s-line graph lazily (cached, invalidated on mutation).
- Nodes in s-line graph = hyperedges
- Edge between hyperedges if `|nodes(e1) & nodes(e2)| >= s`
- For vertex-to-vertex path: find edges containing source, find edges containing target, BFS on s-line graph
- Reconstruct vertex path from hyperedge sequence

### 2c. betweenness_centrality() -- Hypergraph betweenness

s-path-based betweenness centrality:
- For each node v, count fraction of s-paths that pass through v
- Approximate via sampling for large graphs

### 2d. has_cycle() / detect_cycles() -- Hypergraph cycle detection

Use bipartite (node-edge) representation or directed s-line graph for cycle detection.

### 2e. pagerank() -- Hypergraph PageRank via incidence matrix

```
P = D_v^{-1} @ H @ W @ D_e^{-1} @ H^T
pr^{(t+1)} = (1 - alpha) * P @ pr^{(t)} + alpha * v_0
```

Uses existing `incidence_matrix()`. scipy sparse iterative power method.

### 2f. (New) spectral_embedding()

Bottom-k eigenvectors of normalized hypergraph Laplacian.
```
L_norm = I - D_v^{-1/2} H W D_e^{-1} H^T D_v^{-1/2}
```

### 2g. (New) hypergraph_diffusion()

Replace pairwise spreading activation with hypergraph transition matrix.
Support modes: linear, and, or, majority.

## Phase 3: Internal Migration

Update 14+ files to stop inline pairwise decomposition.

| File | Change |
|---|---|
| `community.py` | Use `star()` + directed edge accessors |
| `rules.py` | Use `directed_out_edges()` / `directed_in_edges()` |
| `structural_anomaly.py` | Call kernel methods instead of building inline nx.DiGraph |
| `multiway_rulial.py` | Use `incidence_matrix()` + SVD |
| `multi_perspective.py` | Use Laplacian eigenvalues |
| `multiway_causal.py` | Keep NetworkX isomorphism (document as acceptable) |
| `system_monitor.py` | Use `star()` + directed accessors |
| `constraints.py` | Use `star()` + directed accessors |
| `hebbian.py` | Handle n-ary edges properly |
| `memory_reasoning.py` | Handle n-ary source_ids |
| `belief_revision.py` | Group by frozenset identity |
| `structural_match.py` | N-ary aware pattern matching |
| `embedding_graph.py` | Use `star()` for neighborhood |
| `multiway_branchial.py` | Use `star()` for participation |

## Phase 4: Uniquely Hypergraph Features

### 4a. s-persistence filtration

Compute s-connected components for s = 1, 2, ..., max_s.
Returns filtration: nested hierarchy of component splits.

### 4b. Nonlinear hypergraph diffusion

AND/OR/majority modes for n-ary edge activation flow.

### 4c. Hyperedge similarity search

Jaccard/Sorensen-Dice/overlap coefficient between hyperedge node sets.

### 4d. Hypergraph normalized cut

Spectral partitioning via hypergraph normalized cut formula.
```
cut(A, A_bar) = sum w(e) * |e & A| * |e & A_bar| / (|e| - 1)
```

## New Result Dataclasses

- `SPersistenceLevel` -- s-value, components, counts
- `HyperedgeSimilarityResult` -- query edge, similar edges, metric
- `HypergraphCutResult` -- partitions, cut values
- `SpectralEmbeddingResult` -- node-to-vector mapping, eigenvalues

## References

- Zhou, Huang, Schoelkopf. "Learning with Hypergraphs." NIPS 2006.
- Aksoy, Joslyn, Marron, Purvine. "Hypernetwork Science via High-Order Hypergraph Traversal." 2020.
- Li, Milenkovic. "Submodular Hypergraphs." KDD 2018.
- Benson, Gleich, Leskovec. "Higher-Order Organization of Complex Networks." Science 2016.
- Kamiński, Poulin, et al. "Modularity in Hypergraphs." 2019.
