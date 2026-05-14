# Design 10: Context-Aware Cache Eviction

**Status: Design**

**Effort**: L (~200 LoC new) | **Value**: L | **Risk**: L

## Problem

`LazyCache` (in `cache.py`) has TTL-based expiration and Markov-model
prefetching. Entries expire when their time-to-live elapses, regardless of
whether they're still contextually relevant. When the observer's focus shifts
(e.g., from exploring causal relationships to examining temporal patterns), the
cache still holds entries from the old context that consume capacity.

The inspiration document (Appendix E) describes: "Cache expiration based on
reduced contextual relevance" and "dynamic cache refreshing based on evolving
priorities." This design adds context-aware eviction that ties cache lifecycle
to the current observer slice context.

## Scope

A `ContextAwareEviction` policy for `LazyCache` that evicts entries outside the
current observer context when capacity is pressure. Implemented as an extension
to the existing cache, not a replacement.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Cache expiration based on contextual relevance" | Evict entries outside current modality/dimension |
| "Dynamic cache refreshing" | Boost TTL of entries matching current context |
| "Lazy evaluation protocol" | Existing `LazyCache` with enhanced eviction |

## Architecture

```
Layer 1: Utility   -- ContextAwareEviction (extend cache.py)
Layer 2: Mixin     -- minor modification to SubsystemMixin (memory_subsystems.py)
Layer 3: Facade    -- no changes
```

## Existing Code

- `LazyCache` in `cache.py`: LRU cache with TTL, optional Markov prefetching.
  Methods: `get()`, `set()`, `invalidate()`, `_evict_expired()`.
- `AdaptiveSliceEngine` in `adaptive_slice.py`: recommends slice parameters.
- `SliceConfig` in `traversal.py`: `max_depth`, `max_nodes`, `min_weight`,
  `modalities`.
- `Modality` enum in `kernel_types.py`.
- `HypergraphMemory.cache` property exposes the raw `LazyCache`.

## Design: Layer 1 -- ContextAwareEviction

### Approach

Add an eviction policy to `LazyCache` that considers entry context tags when
deciding what to evict under memory pressure.

```python
class LazyCache:
    def __init__(
        self,
        max_size: int = 128,
        ttl: float = 300.0,
        *,
        context_aware: bool = False,
    ) -> None:
        ...
        self._context_tags: dict[str, set[str]] = {}  # key -> tags
        self._active_context: set[str] = set()  # current context tags
        self._context_aware = context_aware
```

### Context Tagging

When entries are set, they can carry context tags:

```python
def set(self, key: str, value: Any, *, context_tags: set[str] | None = None) -> None:
    ...
    if context_tags:
        self._context_tags[key] = context_tags
```

Context tags are domain-specific strings like `"causal"`, `"temporal"`,
`"conceptual"`, or `"retrieval:<concept_label>"`.

### Active Context

The cache tracks the "active context" -- the set of tags representing the
current operational focus:

```python
def set_active_context(self, tags: set[str]) -> None:
    self._active_context = tags
```

### Context-Aware Eviction

When the cache needs to evict (capacity reached), prefer entries whose context
tags do NOT overlap with the active context:

```python
def _evict_for_capacity(self) -> None:
    if len(self._cache) < self._max_size:
        return

    # Partition entries: in-context vs out-of-context
    out_of_context = []
    in_context = []
    for key in self._cache:
        tags = self._context_tags.get(key, set())
        if tags and not (tags & self._active_context):
            out_of_context.append(key)
        else:
            in_context.append(key)

    # Evict out-of-context first (sorted by age)
    out_of_context.sort(key=lambda k: self._timestamps.get(k, 0))
    for key in out_of_context:
        if len(self._cache) < self._max_size:
            break
        self._remove(key)

    # If still over capacity, evict oldest in-context entries
    in_context.sort(key=lambda k: self._timestamps.get(k, 0))
    for key in in_context:
        if len(self._cache) < self._max_size:
            break
        self._remove(key)
```

### Context-Aware TTL Boost

Entries matching the active context get their TTL extended:

```python
def get(self, key: str) -> Any | None:
    ...
    if self._context_aware and key in self._cache:
        tags = self._context_tags.get(key, set())
        if tags & self._active_context:
            # Boost TTL for contextually relevant entries
            self._timestamps[key] = time.time()
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
    ...
```

### Integration with Prefetch

When `LazyCache` has Markov prefetching enabled, the prefetch model should
prefer keys that match the active context:

```python
def _prefetch_related(self, key: str) -> None:
    if not self._markov_model:
        return
    candidates = self._markov_model.predict(key)
    for candidate in candidates:
        tags = self._context_tags.get(candidate, set())
        if self._active_context and not (tags & self._active_context):
            continue  # skip prefetch for out-of-context entries
        if candidate not in self._cache:
            # ... fetch and cache
```

## Design: Layer 2 -- Mixin Wiring

### SubsystemMixin (memory_subsystems.py)

Set the active context when recall/traversal operations change focus:

```python
def _update_cache_context(self, concept: str) -> None:
    if self._cache._context_aware:
        node = self._graph.get_node_by_label(concept)
        if node:
            tags = {m.value for m in node.metadata.modality_tags}
            tags.add(f"retrieval:{concept}")
            self._cache.set_active_context(tags)
```

Called from `recall()` and `activate()` to keep cache context in sync with
the current operational focus.

## Design: Layer 3 -- Facade

No facade changes. The context-aware behavior is transparent to users who
enable it via `LazyCache(context_aware=True)`.

### Constructor Integration

```python
# In HypergraphMemory.__init__():
if enable_context_cache:
    self._cache = LazyCache(max_size=cache_size, ttl=cache_ttl, context_aware=True)
```

## Challenge: Tag Granularity

Context tags need to be meaningful. Too coarse (just `"retrieval"`) and
everything matches. Too fine (per-concept tags) and nothing matches. The design
uses modality values as primary tags plus `"retrieval:<concept>"` for
operation-specific context. This gives 7 modality buckets plus per-query
granularity.

## Challenge: Backward Compatibility

`context_aware=False` by default. All existing `LazyCache` behavior is preserved.
Only users who opt in get context-aware eviction.

## Test Plan (~20 tests)

- `LazyCache(context_aware=True)` construction
- `set` with context_tags stores tags
- `set_active_context` updates active context
- Eviction: out-of-context entries evicted first
- Eviction: in-context entries preserved when possible
- Eviction: all entries in-context -> oldest evicted
- Eviction: no active context -> standard LRU
- TTL boost: in-context entries get extended TTL
- TTL boost: out-of-context entries age normally
- Prefetch: skips out-of-context candidates
- Prefetch: includes in-context candidates
- `get` returns value for valid entry
- `get` returns None for expired entry (TTL still applies)
- Integration: cache with context_aware after recall
- Context tag inheritance: entries inherit from operation context
- Edge: empty cache -> no eviction
- Edge: single entry -> never evicted
- Edge: context_aware=False -> no context behavior
- Performance: eviction scan is O(N) where N = cache size (bounded by max_size)
- `_remove` cleans up context_tags

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/cache.py` | MODIFY | +120 LoC (context-aware eviction) |
| `tests/test_cache.py` | MODIFY | +150 LoC (context-aware tests) |
| `src/hyper3/memory_subsystems.py` | MODIFY | +10 LoC (context update hook) |
| `src/hyper3/memory.py` | MODIFY | +5 LoC (constructor option) |

**Estimated total**: ~285 LoC new/modified.
