# Draft 07: `ensure()` — Idempotent Store

## Problem
Movie pipeline wraps `store()` in try/except 6 times:
```python
try:
    mem.store(genre, data={"type": "genre"})
except Exception:
    pass
try:
    mem.relate(title, genre, label="has_genre")
except Exception:
    pass
```

The issue: `store()` actually IS idempotent (returns existing node if label matches), but the pattern of "create node if absent, then relate" is still verbose because:
1. Users don't know `store()` is idempotent
2. The try/except is defensive against unknown behavior
3. There's no single call that does "create both nodes and the edge"

## Proposed API

Add to `CoreMixin` in `memory_core.py`:

```python
def ensure(
    self,
    concept: str,
    *,
    data: Any = None,
    modalities: set[Modality] | None = None,
    abstraction: AbstractionLayer = AbstractionLayer.INTERMEDIATE,
    tags: dict[str, Any] | None = None,
    update: bool = False,
) -> Hypernode:
```

### Parameters
- Same as `store()` (concept, data, modalities, abstraction, tags)
- `update` — if True and node exists, **merge** new data into existing data dict. If False, leave existing data unchanged.

### Behavior
- If node does NOT exist: create it (identical to `store()`)
- If node DOES exist: return it unchanged (if `update=False`) or merge data (if `update=True`)
- Does NOT call `touch()` or `reinforce()` — this is a pure existence guarantee, not a signal of importance
- Does NOT increment the operation counter or trigger evolution

### Difference from `store()`
- `store()` reinforces the node (bumps weight, records in cache, increments op counter)
- `ensure()` is silent — no reinforcement, no cache update, no evolution trigger
- `ensure()` is for initialization; `store()` is for interaction

### Why not just document `store()` as idempotent?
Because `store()` has side effects (reinforcement, cache population, evolution triggering). When building a graph from external data (like the movie pipeline), you don't want to reinforce every genre node 200 times. `ensure()` separates "make sure this exists" from "this concept is important."

### Examples
```python
# Build phase: ensure nodes exist without side effects
mem.ensure("Drama", data={"type": "genre"})
mem.ensure("The Matrix", data={"type": "movie", "year": 1999})
mem.relate("The Matrix", "Drama", label="has_genre")

# Later: actual interaction reinforces
mem.store("The Matrix")  # signals importance
```

## Implementation Notes
- Goes in `CoreMixin`
- Checks `self._graph.get_node_by_label(concept)` first
- If exists and `update=True`: merge data dicts
- If exists and `update=False`: return existing node
- If not exists: create via `Hypernode()` + `self._graph.add_node()` (bypassing store's reinforcement)
- Does NOT call `self._maybe_evolve()`

## Tests
- Creates node when absent
- Returns existing node when present (no mutation)
- `update=True` merges data into existing node
- `update=False` leaves existing data unchanged
- Does NOT increment operation counter
- Does NOT add to cache
- Works with `relate()` pattern (ensure both ends, then relate)
