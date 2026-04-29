# Draft 04: `has_node()` — Public Node Existence Check

## Problem
Wikipedia pipeline uses the private `_find_node()` method:
```python
present_seeds = [s for s in seeds if mem._find_node(s) is not None]
```

Other pipelines reach through to the kernel:
```python
mem.graph.get_node_by_label(x) is not None
```

There should be a clean public API for checking whether a concept exists.

## Proposed API

Add to `CoreMixin` in `memory_core.py`:

```python
def has_node(self, concept: str) -> bool:
```

Also add `__contains__` to `HypergraphMemory`:

```python
def __contains__(self, concept: str) -> bool:
    return self.has_node(concept)
```

### Parameters
- `concept` — label to check

### Returns
- `bool` — True if a node with this label exists

### Examples
```python
if mem.has_node("cancer"):
    ...

if "cancer" in mem:
    ...

present = [s for s in seed_concepts if s in mem]
```

## Implementation Notes
- Delegates to `self._find_node(concept) is not None` (reuses existing resolution logic including cache, label index, and aliases)
- `__contains__` goes on `HypergraphMemory` class in `memory.py` (the facade)
- Simple, ~3 lines of code total

## Tests
- Returns True for existing node
- Returns False for non-existing node
- Returns True for node created then evolved (still exists)
- `__contains__` works with `in` operator
- Works after save/load cycle
