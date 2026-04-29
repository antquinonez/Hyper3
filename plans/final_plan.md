# Final Implementation Plan: Hyper3 API Surface Expansion

Synthesized from 8 draft designs. Implements in dependency order.

## Overview

8 new capabilities addressing the top gaps identified across 5 production pipelines:

| # | Feature | Location | Type |
|---|---------|----------|------|
| 1 | `has_node()` / `__contains__` | memory_core.py, memory.py | New method |
| 2 | `ensure()` | memory_core.py | New method |
| 3 | `weight` on `relate()` | memory_core.py | Parameter addition |
| 4 | `neighbors()` | memory_core.py | New method |
| 5 | `query_nodes()` | memory_analytics.py | New method |
| 6 | `describe()` | memory_analytics.py | New method + result type |
| 7 | `pagerank()` | memory_analytics.py | New method |
| 8 | `top_k` on centrality + utility | memory_analytics.py, results.py | Parameter + utility |

## New Result Dataclass

Add to `results.py`:

```python
@dataclass
class GraphDescription(_SimpleResultBase):
    node_count: int = 0
    edge_count: int = 0
    node_types: dict[str, int] = field(default_factory=dict)
    edge_labels: dict[str, int] = field(default_factory=dict)
    degree_min: int = 0
    degree_max: int = 0
    degree_mean: float = 0.0
    degree_median: float = 0.0
    isolated_nodes: int = 0
    components: int = 0
    density: float = 0.0
```

## New Utility Function

Add to `results.py`:

```python
def top_k(scores: dict[str, float], k: int = 10) -> list[tuple[str, float]]:
```

## File Changes (in order)

### 1. `src/hyper3/results.py`
- Add `GraphDescription` dataclass
- Add `top_k()` utility function

### 2. `src/hyper3/memory_core.py`

**Add `has_node()`:**
```python
def has_node(self, concept: str) -> bool:
    return self._find_node(concept) is not None
```

**Add `ensure()`:**
```python
def ensure(self, concept: str, *, data=None, modalities=None,
           abstraction=AbstractionLayer.INTERMEDIATE, tags=None,
           update: bool = False) -> Hypernode:
```
- Check `get_node_by_label(concept)` first
- If exists: optionally merge data, return node
- If not: create via `Hypernode()` + `add_node()`, no reinforcement/evolution

**Add `weight` to `relate()`:**
- Add `weight: float = 1.0` keyword parameter
- Pass to both `Hyperedge()` constructors (forward and bidirectional reverse)

**Add `neighbors()`:**
```python
def neighbors(self, concept: str, *, edge_label: str | None = None,
              direction: str = "any") -> list[str]:
```
- Resolve label via `_find_node()`
- Iterate `edges_for()`, filter by label + direction
- Return labels via `_node_label()`

### 3. `src/hyper3/memory_analytics.py`

**Add `query_nodes()`:**
```python
def query_nodes(self, *, type: str | None = None,
                data: dict[str, Any] | None = None,
                labels: set[str] | None = None,
                limit: int | None = None) -> list[str]:
```

**Add `describe()`:**
```python
def describe(self) -> GraphDescription:
```

**Add `pagerank()`:**
```python
def pagerank(self, *, alpha: float = 0.85, max_iter: int = 100,
             tol: float = 1e-06, weighted: bool = True,
             top_k: int | None = None) -> dict[str, float]:
```

**Add `top_k` to existing centrality methods:**
- `degree_centrality(*, top_k: int | None = None)`
- `betweenness_centrality(*, top_k: int | None = None)`

Update imports at top of file to include `GraphDescription` from results.

### 4. `src/hyper3/memory.py`

**Add `__contains__` to `HypergraphMemory` facade:**
```python
def __contains__(self, concept: str) -> bool:
    return self.has_node(concept)
```

### 5. `src/hyper3/__init__.py`

Export additions:
- `GraphDescription` (if other result types are exported)
- `top_k` utility function

### 6. `tests/test_api_surface.py` (new file)

Comprehensive tests for all 8 features.

## Cross-Cutting Design Decisions

1. **All new query methods return labels** (EP-1, DP-4)
2. **All query methods return empty results for missing concepts** (EP-5)
3. **All optional parameters are keyword-only** (EP-6)
4. **No comments in code** (AGENTS.md convention)
5. **`top_k=None` preserves backward compatibility** on existing methods
6. **`type` param on `query_nodes()` is shorthand** for `data={"type": value}` — merged at call site
7. **PageRank uses raw weights** (not inverted) because PageRank transition probability is proportional to edge importance
8. **`ensure()` does NOT trigger evolution** — it's a build-phase operation
9. **`neighbors()` lives in CoreMixin** (fundamental graph operation) while `query_nodes()` lives in AnalyticsMixin (analytical filter)

## Implementation Order

1. `results.py` — `GraphDescription` + `top_k()` (no dependencies)
2. `memory_core.py` — `has_node()`, `ensure()`, `weight` on `relate()`, `neighbors()` (depends on 1)
3. `memory_analytics.py` — `query_nodes()`, `describe()`, `pagerank()`, `top_k` on centrality (depends on 1)
4. `memory.py` — `__contains__` (depends on 2)
5. `__init__.py` — exports (depends on 1-4)
6. Tests — all features

## Validation

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
```
