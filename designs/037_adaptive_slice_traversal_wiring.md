# Design 6: Adaptive Slice Traversal Wiring

**Status: Design**

**Effort**: L (~150 LoC new) | **Value**: M | **Risk**: L

## Problem

`AdaptiveSliceEngine` (in `adaptive_slice.py`) recommends observer slice
parameters using Thompson sampling over historical success outcomes. It
computes context features (degree ratio, label diversity, modality count, weight
spread, connectivity, neighbor count) for a concept and returns a
`RecommendedSlice` with `max_depth`, `max_nodes`, `min_weight`.

However, this engine is **never consulted automatically** during traversal.
When users call `mem.recall()` with a `SliceConfig`, the adaptive engine is not
involved. Users must manually:

1. Call `engine.recommend(concept_id)` to get parameters
2. Convert to a `SliceConfig`
3. Pass to `recall()`

The inspiration document (Figure 7, Appendix D) describes a continuous feedback
loop where observer slices adjust automatically based on interaction signals.
This design wires the adaptive engine into the traversal pipeline.

## Scope

Wire `AdaptiveSliceEngine` into `recall()` and `traverse()` so that when no
explicit `SliceConfig` is provided, the adaptive engine recommends parameters
automatically. Record traversal success back to the adaptive engine.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Continuous feedback loop adjusting observer slices" | Automatic slice recommendation in `recall()` |
| "User interaction signals" | Recall result quality as success signal |
| "Adaptive adjustment thresholds" | Thompson sampling in AdaptiveSliceEngine |

## Architecture

```
No new engine -- wiring only.
Layer 2: Mixin     -- modify CoreMixin (memory_core.py)
Layer 3: Facade    -- no changes (recall() already exists)
```

## Existing Code

- `AdaptiveSliceEngine` in `adaptive_slice.py`: `recommend(concept_id) -> RecommendedSlice`,
  `record_outcome(concept_id, max_depth, max_nodes, min_weight, success)`.
- `RecommendedSlice` in `adaptive_slice.py`: `max_depth`, `max_nodes`, `min_weight`,
  `confidence`, `strategy`.
- `SliceConfig` in `traversal.py`: `max_depth`, `max_nodes`, `min_weight`,
  `modalities`, `abstraction_layers`.
- `CoreMixin.recall()` in `memory_core.py`: traverses from a concept with
  optional `SliceConfig`.
- `ObserverSlice` in `traversal.py`: applies `SliceConfig` to filter traversal
  results.
- `TraversalEngine` in `traversal.py`: BFS, DFS, adaptive traversals.

## Design

### Approach

Modify `CoreMixin.recall()` to accept an optional `adaptive` flag:

```python
def recall(
    self,
    concept: str,
    *,
    config: SliceConfig | None = None,
    adaptive: bool = False,
    max_depth: int = 3,
    max_nodes: int = 50,
) -> RecallResult:
    concept_id = self._resolve(concept)

    if config is None and adaptive and self._adaptive_slice is not None:
        recommended = self._adaptive_slice.recommend(concept_id)
        config = SliceConfig(
            max_depth=recommended.max_depth,
            max_nodes=recommended.max_nodes,
            min_weight=recommended.min_weight,
        )

    result = self._traverse(concept_id, config=config, ...)

    if adaptive and self._adaptive_slice is not None:
        success = len(result.nodes) > 0
        self._adaptive_slice.record_outcome(
            concept_id,
            max_depth=config.max_depth if config else max_depth,
            max_nodes=config.max_nodes if config else max_nodes,
            min_weight=config.min_weight if config else 0.0,
            success=success,
        )

    return result
```

### Success Signal

A traversal is "successful" if it returns at least one node beyond the seed.
This is a simple heuristic. Future iterations could use richer signals (user
feedback, relevance scores), but the initial implementation uses non-empty
results as the success criterion.

### Lazy Initialization of AdaptiveSliceEngine

The engine is lazily initialized in `_MemoryBase` (or `SubsystemMixin`):

```python
@property
def _adaptive_slice(self) -> AdaptiveSliceEngine | None:
    if self.__adaptive_slice is None:
        self.__adaptive_slice = AdaptiveSliceEngine(self._graph)
    return self.__adaptive_slice
```

### Key Design Decisions

1. **Opt-in via `adaptive=True`**: Not enabled by default to preserve existing
   behavior. Users must explicitly request adaptive slicing.

2. **No `SliceConfig` override when explicit config provided**: If the user
   passes a `SliceConfig`, it takes precedence. Adaptive recommendation only
   applies when `config is None`.

3. **Success recording is fire-and-forget**: The recording happens after
   traversal completes and doesn't affect the return value. Failures are logged
   alongside successes to improve future recommendations.

4. **No modification to `AdaptiveSliceEngine`**: The existing engine's
   `recommend()` and `record_outcome()` APIs are sufficient. No changes needed.

## Challenge: Cold Start

When the adaptive engine has no history, `recommend()` falls back to heuristics
based on the concept's local structure (degree ratio, weight spread, etc.).
This provides reasonable defaults from the first query. The heuristic logic
already exists in `AdaptiveSliceEngine._heuristic_recommend()`.

## Test Plan (~15 tests)

- `recall(adaptive=True)` with no history -> uses heuristic recommendation
- `recall(adaptive=True)` with history -> uses Thompson sampling recommendation
- `recall(adaptive=True)` records success when results non-empty
- `recall(adaptive=True)` records failure when results empty
- `recall(config=..., adaptive=True)` -> explicit config takes precedence
- `recall(adaptive=False)` -> no adaptive behavior (default)
- Adaptive engine lazy-initialized on first adaptive recall
- Recommended SliceConfig has correct field mapping
- Heuristic recommendation produces valid SliceConfig
- Multiple adaptive recalls build up outcome history
- `record_outcome` called with correct parameters
- Integration: sequence of adaptive recalls improves recommendations over time
- Edge: concept not found -> no recording, empty result
- Edge: adaptive engine None (manually set) -> graceful fallback
- Adaptive recall with modality filtering (SliceConfig with modalities + adaptive)

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/memory_core.py` | MODIFY | +30 LoC (adaptive recall logic) |
| `src/hyper3/memory_subsystems.py` | MODIFY | +10 LoC (lazy init) |
| `src/hyper3/memory_base.py` | MODIFY | +2 LoC (type declaration) |
| `tests/test_adaptive_slice.py` | MODIFY | +80 LoC (wiring tests) |

**Estimated total**: ~122 LoC new/modified. This is the smallest design.
