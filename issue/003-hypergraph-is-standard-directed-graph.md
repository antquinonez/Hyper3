# Issue 003: Hypergraph Implementation is a Standard Directed Graph

**Severity**: High
**Module**: `kernel.py` (712 lines), all downstream consumers
**Status**: Closed (Option A implemented: hypergraph primitives added, honest naming retained)

## Problem

The `Hypergraph` class stores edges with `frozenset[str]` source and target IDs, which structurally supports n-ary hyperedges (edges connecting multiple source nodes to multiple target nodes). However, every graph algorithm in the codebase immediately flattens hyperedges into pairwise directed edges via `to_networkx()`, and no true hypergraph algorithms are implemented. The system is a directed multigraph wearing hypergraph clothing.

## Specific Deficiencies

### 1. All algorithms delegate to networkx pairwise conversion

**File**: `kernel.py:455-471` (`to_networkx`)

```python
def to_networkx(self) -> nx.DiGraph:
    G = nx.DiGraph()
    for node in self._nodes.values():
        G.add_node(node.id, label=node.label, weight=node.weight, data=node.data)
    for edge in self._edges.values():
        for src in edge.source_ids:
            for tgt in edge.target_ids:
                G.add_edge(src, tgt, label=edge.label, weight=edge.weight, edge_id=edge.id)
    return G
```

A hyperedge `{A, B} → {C, D}` becomes four pairwise edges: A→C, A→D, B→C, B→D. This loses the hyperedge semantics — the original edge represents a single *joint* relationship between the source set and target set, not four independent pairwise relationships.

**All downstream algorithms use this conversion:**
- `betweenness_centrality` (line 530-539) — uses `nx.betweenness_centrality` on flattened graph
- `connected_components` (line 541-550) — uses `nx.weakly_connected_components`
- `has_cycle` / `detect_cycles` (line 552-586) — uses `nx.find_cycle` / `nx.simple_cycles`
- `shortest_path` (line 588-614) — uses `nx.dijkstra_path`
- Every algorithm in `multiway_causal.py`, `multiway_branchial.py`, `relativity.py`, `transfinite.py` builds its own `nx.DiGraph` from the hypergraph

### 2. No hypergraph Laplacian

A hypergraph Laplacian is defined as `L = D_v - H W D_e^{-1} H^T` where:
- `H` is the incidence matrix (nodes × hyperedges)
- `W` is the hyperedge weight matrix
- `D_v` is the node degree matrix
- `D_e` is the hyperedge degree matrix

This is not implemented. The spectral gap used in `relativity.py:652-679` computes eigenvalues of the *pairwise* adjacency matrix, not the hypergraph Laplacian. For true hyperedges (multi-source or multi-target), the pairwise adjacency matrix is a poor approximation.

### 3. No hypergraph-specific algorithms

The following standard hypergraph algorithms are absent:

| Algorithm | Purpose | Current Status |
|---|---|---|
| Hypergraph Laplacian eigenvalues | Spectral clustering, connectivity | Not implemented |
| Hypergraph random walk (with edge-dependent transition probabilities) | Traversal, PageRank | Not implemented |
| Hypergraph partitioning (via LP relaxation or spectral methods) | Community detection | Not implemented (uses label propagation on pairwise graph) |
| Hyperedge contraction | Abstraction, summarization | Not implemented (abstraction.py works on subgraphs, not hyperedges) |
| s-walk connectivity | Generalized connectivity | Not implemented |
| Hypergraph incidence matrix | Foundation for all hypergraph algorithms | Not implemented |

### 4. The `neighbors()` method treats hyperedges as undirected

**File**: `kernel.py:263-283` (`neighbors`)

```python
for edge in self.edges_for(nid):
    nbrs.update(edge.node_ids)  # union of source_ids and target_ids
```

This computes neighbors as `source_ids ∪ target_ids - {self}`, which is an undirected notion of neighborhood. For directed hyperedges (which this graph claims to support), the natural neighborhood is the out-neighborhood via target IDs. The method conflates sources and targets.

### 5. `edges_for()` does not distinguish direction

**File**: `kernel.py:251-261`

`edges_for(node_id)` returns all edges where the node appears in *either* source_ids or target_ids. There is no `outgoing_edges_for()` or `incoming_edges_for()` method. Every consumer must filter manually:

```python
outgoing = [e for e in self._graph.edges_for(node.id) if node.id in e.source_ids]
incoming = [e for e in self._graph.edges_for(node.id) if node.id in e.target_ids]
```

This pattern appears in `transfinite.py:304-305`, `relativity.py:296`, `community.py`, and many other modules.

### 6. No hyperedge-aware pattern matching

**File**: `kernel.py:354-405` (`pattern_match`)

Pattern matching works on the pairwise expansion: it checks if a label appears in `source_labels` or `target_labels` without considering whether the edge is a true hyperedge (multi-source/multi-target). The `structural_match.py` module also works on pairwise chains and diamonds, not hypergraph motifs.

## Impact

- **Hyperedge data is stored but never used natively**: Users can create n-ary edges, but every algorithm silently flattens them.
- **Community detection on hypergraphs is incorrect**: Label propagation on the pairwise expansion can produce different communities than hypergraph-specific partitioning (Rodriguez, 2002).
- **Spectral analysis is misleading**: Eigenvalues of the pairwise adjacency matrix are not eigenvalues of the hypergraph. Papers on hypergraph spectral theory (Zhou et al., 2006) define a different normalization.
- **The `multi_edge_count` stat** in `MemoryStats` counts true hyperedges but the rest of the system ignores them.

## Recommended Fix

### Option A: Implement core hypergraph primitives (recommended first step)

Add the following to `kernel.py`:

1. **Incidence matrix**:
   ```python
   def incidence_matrix(self) -> tuple[np.ndarray, list[str], list[str]]:
       """Return (H, node_ids, edge_ids) where H[i,j] = 1 if node i is in edge j."""
   ```

2. **Hypergraph Laplacian**:
   ```python
   def hypergraph_laplacian(self) -> np.ndarray:
       """Compute L = D_v - H W D_e^{-1} H^T."""
   ```

3. **Directed edge accessors**:
   ```python
   def outgoing_edges(self, node_id: str) -> list[Hyperedge]:
       """Edges where node_id is in source_ids."""
   def incoming_edges(self, node_id: str) -> list[Hyperedge]:
       """Edges where node_id is in target_ids."""
   def out_neighbors(self, node_id: str) -> list[str]:
       """Target IDs of outgoing edges."""
   def in_neighbors(self, node_id: str) -> list[str]:
       """Source IDs of incoming edges."""
   ```

4. **Hypergraph-aware neighbors**:
   ```python
   def neighbors(self, node_id: str) -> list[str]:
       """Return out-neighbors for directed edges, all neighbors for undirected."""
   ```

5. **Hyperedge-aware random walk**:
   ```python
   def hypergraph_random_walk(self, start_id: str, steps: int) -> list[str]:
       """Random walk using hyperedge-dependent transition probabilities."""
   ```

### Option B: Keep pairwise internally, document honestly

If hypergraph algorithms are not a priority, rename the class to `DirectedMultigraph` and document that hyperedges are stored as n-ary relations but processed pairwise. Add `is_hyperedge(edge)` method and `true_hyperedge_count` stat. This is the minimal honesty fix.

### Option C: Full hypergraph algorithm suite

Implement:
- Hypergraph spectral clustering (Zhou et al., "Learning with Hypergraphs", 2006)
- s-walk connectivity
- Hypergraph PageRank (using the hypergraph random walk)
- Hyperedge contraction for hierarchical abstraction
- Hypergraph motif counting (beyond dyads and chains)

This is a significant research implementation effort.

## Files Affected

- `src/hyper3/kernel.py` — core data structure
- Every module that calls `to_networkx()` or builds `nx.DiGraph`:
  - `src/hyper3/relativity.py` (spectral gap, curvature, frame dragging, traversals)
  - `src/hyper3/transfinite.py` (SCC computation, centrality)
  - `src/hyper3/community.py` (label propagation)
  - `src/hyper3/multiway_branchial.py` (distance metrics)
  - `src/hyper3/multiway_causal.py` (isomorphism)
  - `src/hyper3/multiway_rulial.py` (adjacency matrix)
  - `src/hyper3/evolution.py` (potentially)
- `src/hyper3/analytics.py` or wherever betweenness/centrality/paths are computed
- All test files for the above modules
