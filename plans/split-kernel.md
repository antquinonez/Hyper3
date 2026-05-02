# Plan: Split kernel.py into Focused Modules

## Problem

`kernel.py` is 1,856 lines containing 5 data structure classes and the `Hypergraph` class with 72 methods spanning 14 functional areas. It is the largest file in the codebase and the most frequently edited during algorithm work (the upcoming laminar implementation will touch it heavily).

## Design

Use the **same mixin composition pattern already used by `HypergraphMemory`**. The `Hypergraph` class becomes a thin facade composing from focused mixins, each owning a coherent domain.

```
Hypergraph(_GraphBase, CoreMixin, QueryMixin, PathMixin, ComponentMixin,
           CycleMixin, CentralityMixin, SpectralMixin, ClusteringMixin,
           PatternMixin, TransformMixin, SimilarityMixin)
```

This keeps `Hypergraph` as the single class name that all callers use. No import paths change. No public API changes.

## Why mixins (not free functions)

- Hypergraph's methods share mutable state (`_nodes`, `_edges`, `_label_index`, `_neighbor_cache`). Free functions would need the graph passed explicitly, creating a two-API problem.
- Mixins match the existing HypergraphMemory pattern (DP-1).
- Each mixin can be independently tested and understood.
- New algorithms get added by creating a new mixin and extending the class list.

## Proposed Module Layout

```
src/hyper3/
  kernel.py              <-- stays, becomes thin composition + re-exports
  kernel_types.py         <-- Hypernode, Hyperedge, Metadata, Modality, AbstractionLayer (82 lines)
  kernel_base.py          <-- _GraphBase: shared state declarations + CRUD (198 lines)
  kernel_query.py         <-- QueryMixin: edge lookups, neighbors, directed queries, degree (155 lines)
  kernel_paths.py         <-- PathMixin: find_paths, shortest_path, Dijkstra, BFS (181 lines)
  kernel_components.py    <-- ComponentMixin: s-components, s-persistence, union-find (248 lines)
  kernel_cycles.py        <-- CycleMixin: has_cycle, detect_cycles (78 lines)
  kernel_centrality.py    <-- CentralityMixin: degree/betweenness/pagerank/katz (192 lines)
  kernel_spectral.py      <-- SpectralMixin: incidence, Laplacian, adjacency, eigenvalues (202 lines)
  kernel_clustering.py    <-- ClusteringMixin: clustering_coefficient, spectral_clustering (86 lines)
  kernel_pattern.py       <-- PatternMixin: pattern_match, subgraph (97 lines)
  kernel_transforms.py    <-- TransformMixin: to_networkx, to_dual, to_line_graph, to_bipartite (77 lines)
  kernel_similarity.py    <-- SimilarityMixin: hyperedge_similarity, cocoverage (62 lines)
```

**Total from extraction: 1,656 lines across 12 new modules**
**kernel.py after: ~200 lines** (imports, re-exports, Hypergraph composition, __init__)

## Module Details

### kernel_types.py (82 lines)

Move from kernel.py top-level:
- `Modality` enum
- `AbstractionLayer` enum
- `Metadata` dataclass
- `Hypernode` dataclass (with `touch`, `is_active`, `matches`)
- `Hyperedge` dataclass (with `node_ids` property)

**Why**: These are pure data structures with no dependency on `Hypergraph`. Every other module imports them. Isolating them breaks the circular import risk (currently kernel.py imports from exceptions.py and results.py, but the types don't need those).

### kernel_base.py (~198 lines)

```python
class _GraphBase:
    _nodes: dict[str, Hypernode]
    _edges: dict[str, Hyperedge]
    _label_index: dict[str, str]
    _neighbor_cache: dict[str, list[str]] | None
    _dimension_index: dict[str, set[str]]
    _batch_mode: bool

class CoreMixin(_GraphBase):
    def __init__(self): ...
    def add_node(self, node): ...
    def get_node(self, node_id): ...
    def get_node_by_label(self, label): ...
    def remove_node(self, node_id): ...
    def add_edge(self, edge): ...
    def get_edge(self, edge_id): ...
    def remove_edge(self, edge_id): ...
    def merge_node(self, primary_id, secondary_id): ...
    def begin_batch(self): ...
    def end_batch(self): ...
```

**Why**: CRUD + index management + batch mode. These are the foundational operations that all other mixins build on. Every other mixin calls `incident_edges` (in QueryMixin) and some call `add_node`/`add_edge` (in CoreMixin).

### kernel_query.py (~155 lines)

```python
class QueryMixin(_GraphBase):
    def incident_edges(self, node_id): ...
    def edges_for(self, node_id): ...          # deprecated alias
    def neighbors(self, node_id): ...
    def outgoing_edges(self, node_id): ...
    def incoming_edges(self, node_id): ...
    def out_neighbors(self, node_id): ...
    def in_neighbors(self, node_id): ...
    def star(self, node_id): ...
    def hyperedge_neighbors(self, node_id): ...
    def hyperedge_cocoverage(self, node_id): ...
    def query_dimension(self, modality): ...
```

**Hub dependency**: `incident_edges` and `outgoing_edges` are called by 5+ other mixins. This is expected — they are the fundamental read operations on the graph.

### kernel_paths.py (~181 lines)

```python
class PathMixin(_GraphBase):
    def find_paths(self, source_id, target_id, ...): ...
    def _find_paths_dfs(self, ...): ...
    def shortest_path(self, source_id, target_id, ...): ...
    def _bfs_shortest_path(self, ...): ...
    def _dijkstra_hypergraph(self, ...): ...
    def shortest_path_lengths(self, ...): ...
    def single_source_shortest_path_lengths(self, ...): ...
    def _dijkstra_all_distances(self, ...): ...
    def _bfs_all_distances(self, ...): ...
```

**External deps**: `heapq`, `collections.deque`. Calls `outgoing_edges` (QueryMixin).

### kernel_components.py (~248 lines)

```python
class ComponentMixin(_GraphBase):
    def connected_components(self, *, s=1): ...
    def _connected_components_basic(self): ...
    def _connected_components_s(self, s): ...
    def _union_s_adjacent_edges(self, ...): ...
    def _build_node_components_from_edge_groups(self, ...): ...
    def s_connected_components(self, s): ...
    def s_persistence(self, *, max_s=None): ...
    def _compute_edge_overlaps(self, ...): ...
    def _compute_s_level(self, s, overlaps): ...
    def _union_overlapping_edges(self, ...): ...
    def is_connected(self): ...
    def largest_connected_component(self): ...
    def component_of(self, node_id): ...
```

**External deps**: `results.py` (SPersistenceResult, SPersistenceLevel). Self-contained otherwise.

### kernel_cycles.py (~78 lines)

```python
class CycleMixin(_GraphBase):
    def has_cycle(self): ...
    def detect_cycles(self, max_cycles=10): ...
    def _detect_cycles_dfs(self, ...): ...
```

**External deps**: Calls `outgoing_edges` (QueryMixin).

### kernel_centrality.py (~192 lines)

```python
class CentralityMixin(_GraphBase):
    def degree_centrality(self): ...
    def betweenness_centrality(self, *, max_samples=None): ...
    def _betweenness_bfs(self, ...): ...
    def pagerank(self, *, alpha=0.85, ...): ...
    def _build_pagerank_transition(self): ...
    def _pagerank_iterate(self, ...): ...
    def katz_centrality(self, *, alpha=0.1, ...): ...
```

**External deps**: `numpy`, `random`. Calls `incident_edges`, `outgoing_edges` (QueryMixin), `adjacency_matrix` (SpectralMixin).

### kernel_spectral.py (~202 lines)

```python
class SpectralMixin(_GraphBase):
    def incidence_matrix(self): ...
    def incidence_matrix_unsigned(self): ...
    def hypergraph_laplacian(self): ...
    def adjacency_matrix(self): ...
    def normalized_laplacian(self): ...
    def spectral_embedding(self, *, dimensions=8): ...
```

**External deps**: `numpy`, `scipy.sparse`, `scipy.sparse.linalg`, `results.py` (SpectralEmbeddingResult). Self-contained mathematically.

### kernel_clustering.py (~86 lines)

```python
class ClusteringMixin(_GraphBase):
    def clustering_coefficient(self, node_id): ...
    def average_clustering_coefficient(self): ...
    def spectral_clustering(self, k=2): ...
```

**External deps**: `numpy`, `scipy.sparse`, `scipy.sparse.linalg`. Calls `neighbors` (QueryMixin), `normalized_laplacian` (SpectralMixin).

### kernel_pattern.py (~97 lines)

```python
class PatternMixin(_GraphBase):
    def pattern_match(self, *, edge_label=None, ...): ...
    def subgraph(self, node_ids): ...
```

**External deps**: None beyond base. Calls `add_node`, `add_edge` (CoreMixin) for subgraph construction.

### kernel_transforms.py (~77 lines)

```python
class TransformMixin(_GraphBase):
    def to_networkx(self): ...
    def _to_networkx_inverted_weights(self): ...
    def to_dual(self): ...
    def to_line_graph(self): ...
    def to_bipartite_graph(self): ...
```

**External deps**: `networkx`. Calls `incident_edges` (QueryMixin), `add_node`/`add_edge` (CoreMixin) for dual construction.

### kernel_similarity.py (~62 lines)

```python
class SimilarityMixin(_GraphBase):
    def hyperedge_similarity(self, edge_id, *, metric="jaccard", ...): ...
    def _compute_similarity_scores(self, ...): ...
```

**External deps**: `results.py` (HyperedgeSimilarityResult).

## Dependency Graph (No Cycles)

```
kernel_types.py          (no deps beyond stdlib)
    |
    v
kernel_base.py           (imports kernel_types, exceptions)
    |
    v
kernel_query.py          (imports kernel_types)
    |
    +---> kernel_paths.py         (calls outgoing_edges)
    +---> kernel_components.py    (self-contained)
    +---> kernel_cycles.py        (calls outgoing_edges)
    +---> kernel_similarity.py    (imports results)
    |
    +---> kernel_spectral.py      (imports numpy, scipy, results)
    |        |
    |        +---> kernel_centrality.py  (calls adjacency_matrix)
    |        +---> kernel_clustering.py  (calls normalized_laplacian)
    |
    +---> kernel_pattern.py       (calls add_node, add_edge)
    +---> kernel_transforms.py    (calls incident_edges, add_node, add_edge)
```

No circular dependencies. All imports flow downward.

## kernel.py After Split (~200 lines)

```python
from __future__ import annotations

from hyper3.kernel_base import _GraphBase, CoreMixin
from hyper3.kernel_types import (
    AbstractionLayer,
    Hyperedge,
    Hypernode,
    Metadata,
    Modality,
)
from hyper3.kernel_centrality import CentralityMixin
from hyper3.kernel_clustering import ClusteringMixin
from hyper3.kernel_components import ComponentMixin
from hyper3.kernel_cycles import CycleMixin
from hyper3.kernel_pattern import PatternMixin
from hyper3.kernel_paths import PathMixin
from hyper3.kernel_query import QueryMixin
from hyper3.kernel_similarity import SimilarityMixin
from hyper3.kernel_spectral import SpectralMixin
from hyper3.kernel_transforms import TransformMixin


class Hypergraph(
    CoreMixin,
    QueryMixin,
    PathMixin,
    ComponentMixin,
    CycleMixin,
    CentralityMixin,
    SpectralMixin,
    ClusteringMixin,
    PatternMixin,
    TransformMixin,
    SimilarityMixin,
):
    pass


__all__ = [
    "Hypergraph",
    "Hypernode",
    "Hyperedge",
    "Modality",
    "AbstractionLayer",
    "Metadata",
]
```

## Properties Stay Grouped

Properties that are trivial accessors stay with their natural mixin:
- `node_count`, `edge_count`, `nodes`, `edges` → `QueryMixin` (they query graph state)
- `labeled_edges` → `QueryMixin` (produces labeled edge view)
- `density`, `unique_edge_sizes`, `max_edge_order` → `QueryMixin` (statistics about graph structure)

## Import Impact

### Modules that import from `hyper3.kernel`

These all stay unchanged because `kernel.py` re-exports everything:

```python
from hyper3.kernel import Hypergraph, Hypernode, Hyperedge, Modality, AbstractionLayer, Metadata
```

No changes needed in:
- `memory_base.py`, `memory_core.py`, and all other `memory_*.py` files
- `equivalence.py`, `evolution.py`, `traversal.py`, `rules.py`, `multiway.py`, etc.
- `generators.py`, `community.py`, `graph_diff.py`, etc.
- All 2,301 tests
- All 106 examples

### Internal imports within new modules

New modules import from each other via `_GraphBase` and `kernel_types`:

```python
# kernel_paths.py
from hyper3.kernel_base import _GraphBase

class PathMixin(_GraphBase):
    def shortest_path(self, source_id, target_id, *, weighted=True):
        ...
```

## Execution Plan

### Phase 1: Create kernel_types.py (lowest risk)

1. Move `Modality`, `AbstractionLayer`, `Metadata`, `Hypernode`, `Hyperedge` to `kernel_types.py`
2. In `kernel.py`, import them back: `from hyper3.kernel_types import ...`
3. Update `__init__.py` to also re-export from `kernel_types.py`
4. Run tests + linter. All 2,301 must pass.

### Phase 2: Create _GraphBase + CoreMixin (kernel_base.py)

1. Create `kernel_base.py` with `_GraphBase` (shared state fields) and `CoreMixin` (CRUD methods + batch mode)
2. Move `__init__`, `add_node`, `get_node`, `get_node_by_label`, `remove_node`, `add_edge`, `get_edge`, `remove_edge`, `merge_node`, `begin_batch`, `end_batch` from kernel.py
3. In kernel.py, import `CoreMixin` and compose `Hypergraph(CoreMixin)`
4. Run tests. All 2,301 must pass.

### Phase 3: Create QueryMixin (kernel_query.py)

1. Move all query methods: `incident_edges`, `edges_for`, `neighbors`, `outgoing_edges`, `incoming_edges`, `out_neighbors`, `in_neighbors`, `star`, `hyperedge_neighbors`, `hyperedge_cocoverage`, `query_dimension`
2. Move properties: `node_count`, `edge_count`, `nodes`, `edges`, `labeled_edges`, `density`, `unique_edge_sizes`, `max_edge_order`
3. Compose `Hypergraph(CoreMixin, QueryMixin)`
4. Run tests.

### Phase 4: Extract algorithm mixins (can be parallelized)

Each extraction follows the same pattern:
1. Create new file with mixin class extending `_GraphBase`
2. Move methods from kernel.py
3. Add mixin to Hypergraph's inheritance list
4. Run tests after each extraction

Order (by dependency depth, shallowest first):

| Step | Module | Methods | Lines | Depends on |
|------|--------|---------|-------|-----------|
| 4a | `kernel_components.py` | ComponentMixin | 248 | CoreMixin only |
| 4b | `kernel_cycles.py` | CycleMixin | 78 | QueryMixin |
| 4c | `kernel_similarity.py` | SimilarityMixin | 62 | CoreMixin only |
| 4d | `kernel_paths.py` | PathMixin | 181 | QueryMixin |
| 4e | `kernel_spectral.py` | SpectralMixin | 202 | CoreMixin only |
| 4f | `kernel_centrality.py` | CentralityMixin | 192 | QueryMixin, SpectralMixin |
| 4g | `kernel_clustering.py` | ClusteringMixin | 86 | QueryMixin, SpectralMixin |
| 4h | `kernel_pattern.py` | PatternMixin | 97 | CoreMixin |
| 4i | `kernel_transforms.py` | TransformMixin | 77 | QueryMixin, CoreMixin |

### Phase 5: Final cleanup

1. Verify kernel.py is ~200 lines (composition + re-exports only)
2. Run full validation: tests + pyright + ruff + equiv battery + examples + demos
3. Update AGENTS.md Architecture section with new modules
4. Update `__init__.py` if needed
5. Update benchmarks/README.md

## Risk Mitigation

### Circular imports

The dependency graph has no cycles (verified above). But Python's import system can still cause issues if two mixins import each other. Mitigation: all mixins only import `_GraphBase` from `kernel_base.py`. Cross-mixin calls happen through `self.method()` which resolves at runtime via MRO.

### Method resolution order

The mixin composition order matters for MRO. The chosen order is:
```
Hypergraph(CoreMixin, QueryMixin, PathMixin, ComponentMixin, CycleMixin,
           CentralityMixin, SpectralMixin, ClusteringMixin, PatternMixin,
           TransformMixin, SimilarityMixin)
```

No method name collisions exist across mixins (verified: all 72 method names are unique).

### Test compatibility

All tests import `from hyper3.kernel import Hypergraph` or `from hyper3 import Hypergraph`. Since kernel.py re-exports the composed class, zero test changes needed.

### Performance

Method calls through `self.method()` with MRO resolution have negligible overhead vs direct method calls on a monolithic class. Python already resolves all methods through MRO.

## What NOT to Do

- **Don't split Hypergraph into multiple classes.** The class must remain unified. Mixins compose into one class.
- **Don't change any public API.** Same class name, same method signatures, same imports.
- **Don't create sub-packages.** Flat `kernel_*.py` modules in `src/hyper3/`, matching the existing `memory_*.py` pattern.
- **Don't move result dataclasses.** `SpectralEmbeddingResult`, `SPersistenceResult`, etc. stay in `results.py`.

## Estimated Effort

| Phase | New files | Lines moved | Risk | Time |
|-------|-----------|------------|------|------|
| 1. kernel_types.py | 1 | 82 | Very low | 10 min |
| 2. kernel_base.py | 1 | 198 | Low | 15 min |
| 3. kernel_query.py | 1 | 155 | Low | 15 min |
| 4. Algorithm mixins | 9 | 1,221 | Medium | 60 min |
| 5. Cleanup + validate | 0 | 0 | Low | 15 min |
| **Total** | **11** | **1,656** | | **~2 hours** |

## Verification Checklist

After each phase:
- [ ] `ruff check src/hyper3/` passes
- [ ] `pyright src/hyper3/` passes (0 errors)
- [ ] `pytest tests/ -q --tb=short` passes (2301 tests)
- [ ] `python benchmarks/equiv/run_equiv.py` passes (0 fails)

After all phases:
- [ ] kernel.py is < 250 lines
- [ ] All kernel_*.py modules are < 300 lines
- [ ] No circular imports (verify with `python -c "import hyper3"`)
- [ ] AGENTS.md updated with new modules
- [ ] __init__.py re-exports unchanged
