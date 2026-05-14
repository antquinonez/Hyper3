# Design 4: Context Compression Engine

**Status: Design**

**Effort**: M (~350 LoC new) | **Value**: H | **Risk**: M

## Problem

`EquivalenceEngine` and `StateConvergenceEngine` merge **multiway states**, not
the main graph. As the main graph grows, structural redundancy accumulates:
nodes with overlapping neighborhoods, parallel edges with similar labels, and
hub-adjacent clusters that could be collapsed into summary nodes.

`evolve()` handles decay/prune/merge, but `merge_node` requires the caller to
identify candidates. `EquivalenceEngine.find_equivalences()` finds candidates
but is not wired into any compression pipeline. The doc's Figure 17 describes
"real-time contextual compression via equivalence merging" -- a mechanism that
discovers and compresses redundant structure automatically.

## Scope

A `ContextCompressionEngine` that uses `EquivalenceEngine` to detect redundant
substructures in the main graph and compresses them via `AbstractionNavigator`'s
collapse mechanism. Returns a typed `CompressionResult` describing what was
compressed.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Real-time contextual compression" | Automated compression pass over main graph |
| "Equivalence merging" | `EquivalenceEngine.find_equivalences()` on main graph nodes |
| "Optimized information with reduced overhead" | `CompressionResult` with before/after stats |

## Architecture

```
Layer 1: Engine    -- ContextCompressionEngine (new: context_compression.py)
Layer 2: Mixin     -- extend StructuralMixin via memory_subsystems.py
Layer 3: Facade    -- expose via mem.compress_context() shortcut
```

## Existing Code

- `EquivalenceEngine` in `equivalence.py`: `find_equivalences() -> list[(id, id, score)]`
  with combined data + structural similarity.
- `AbstractionNavigator` in `abstraction.py`: `collapse_subgraph()`,
  `expand_node()`, `AbstractionMapping`.
- `GraphMaintenanceEngine` in `evolution.py`: `evolve()` with decay/prune/merge.
- `Hypergraph.merge_node()` in `kernel_base.py`: merges two nodes.
- `CommunityDetector` in `community.py`: label propagation communities.
- `OperationFeedback` in `feedback.py`: tracks operation outcomes.

## Design: Layer 1 -- ContextCompressionEngine

**New file**: `src/hyper3/context_compression.py`

### Data Structures

```python
@dataclass
class CompressionCandidate(_SimpleResultBase):
    node_a_id: str = ""
    node_b_id: str = ""
    similarity: float = 0.0
    strategy: str = ""  # "merge" | "collapse"
    shared_neighbors: int = 0
    edge_overlap: float = 0.0

@dataclass
class CompressionResult(_SimpleResultBase):
    candidates_evaluated: int = 0
    merged_pairs: int = 0
    collapsed_groups: int = 0
    nodes_before: int = 0
    nodes_after: int = 0
    edges_before: int = 0
    edges_after: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class CompressionReport(_SimpleResultBase):
    total_compressions: int = 0
    total_nodes_saved: int = 0
    avg_similarity: float = 0.0
    strategies_used: dict[str, int] = field(default_factory=dict)
```

### Engine API

```python
class ContextCompressionEngine:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        similarity_threshold: float = 0.8,
        max_merge_per_pass: int = 20,
        min_cluster_size: int = 3,
    ) -> None: ...

    def find_candidates(self) -> list[CompressionCandidate]: ...
    def compress(self, *, strategy: str = "auto") -> CompressionResult: ...
    def compress_pair(self, a_id: str, b_id: str, *, strategy: str = "merge") -> CompressionResult: ...
    def report(self) -> CompressionReport: ...
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> ContextCompressionEngine: ...
```

### Compression Strategies

**`"merge"`**: Use `Hypergraph.merge_node(a, b)` to merge the less-connected
node into the more-connected one. Preserves all edges; the merged node inherits
data from both.

**`"collapse"`**: Use `AbstractionNavigator.collapse_subgraph()` to create a
summary node representing a cluster. Internal edges are removed; external
connections are rewired to the summary node.

**`"auto"`** (default): Choose strategy based on candidate characteristics:
- If two nodes share > 70% of their neighbor sets -> `"merge"` (they're
  near-duplicates)
- If 3+ nodes form a tight cluster with high internal density -> `"collapse"`
  (they're a coherent sub-structure)
- Otherwise -> skip (insufficient evidence)

### Candidate Discovery

1. Call `EquivalenceEngine.find_equivalences()` to get high-similarity pairs.
2. For each pair, compute edge overlap (Jaccard of incident edge sets).
3. Also use `CommunityDetector.detect_label_propagation()` to find clusters.
4. Clusters with high internal density (> 0.5) become collapse candidates.
5. Rank candidates by similarity score (descending).

### Key Design Decisions

1. **Not integrated into `evolve()`**: Compression is a separate operation, not
   part of the decay/prune/merge cycle. This keeps `evolve()` fast and
   predictable. Users call `compress_context()` explicitly or wire it into their
   own maintenance schedule.

2. **No automatic collapse without user opt-in**: The `"auto"` strategy only
   merges near-duplicates. Collapsing clusters (which destroys internal edges)
   requires explicit `strategy="collapse"` or `strategy="auto"` with sufficiently
   high-density clusters.

3. **Preserves provenance**: Every compression records which nodes were affected
   and what strategy was used in `CompressionResult.details`.

## Design: Layer 2 -- Mixin Wiring

### SubsystemMixin (memory_subsystems.py)

Add lazy initialization and one method:

```python
@property
def _context_compression(self) -> ContextCompressionEngine:
    if self.__context_compression is None:
        self.__context_compression = ContextCompressionEngine(self._graph)
    return self.__context_compression

def compress_context(self, *, strategy: str = "auto") -> CompressionResult:
    return self._context_compression.compress(strategy=strategy)
```

## Design: Layer 3 -- Facade

Add a shortcut method to `HypergraphMemory`:

```python
def compress_context(self, *, strategy: str = "auto") -> CompressionResult:
    return SubsystemMixin.compress_context(self, strategy=strategy)
```

No namespace needed -- this is an explicit maintenance operation.

## Challenge: Data Loss from Merge

Merging nodes combines their data dicts. If node A has `{"color": "red"}` and
node B has `{"color": "blue"}`, the merged node gets one value (whichever node
is the primary). The `CompressionResult.details` records which values were lost
so users can audit.

## Test Plan (~25 tests)

- Engine construction
- `find_candidates`: empty graph -> empty
- `find_candidates`: two similar nodes with shared neighbors -> 1 candidate
- `find_candidates`: threshold filters low-similarity pairs
- `compress`: merge strategy combines two similar nodes
- `compress`: collapse strategy creates summary node for cluster
- `compress`: auto strategy selects merge for near-duplicates
- `compress`: auto strategy selects collapse for dense clusters
- `compress`: auto strategy skips ambiguous cases
- `compress_pair`: explicit pair merge
- `compress_pair`: nodes not found -> empty result
- `report`: accumulates statistics across compressions
- `to_dict` / `from_dict`: round-trip serialization
- Before/after node/edge counts correct
- `CompressionResult.details` contains strategy used
- Integration: `mem.compress_context()` returns CompressionResult
- Integration: compression followed by `evolve()` works correctly
- Edge: self-compression (same node) -> no-op
- Edge: already merged nodes -> no re-compression
- Edge: nodes with conflicting data -> merge preserves primary
- Edge: large cluster -> `max_merge_per_pass` limits per call
- Edge: compression preserves external edges
- Edge: collapsed group can be expanded via AbstractionNavigator
- Data loss tracking in details
- compression idempotent -- second call finds no new candidates

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/context_compression.py` | NEW | ~350 LoC |
| `tests/test_context_compression.py` | NEW | ~400 LoC |
| `src/hyper3/memory_subsystems.py` | MODIFY | +25 LoC (compress_context) |
| `src/hyper3/memory.py` | MODIFY | +8 LoC (shortcut) |
| `src/hyper3/memory_base.py` | MODIFY | +2 LoC (type declaration) |
| `src/hyper3/__init__.py` | MODIFY | +3 exports |

**Estimated total**: ~775 LoC new, ~35 LoC modified.
