# Draft 08: `top_k` Helper and Scored Result Sorting

## Problem
All 5 pipelines sort score dicts identically:
```python
sorted(centrality.items(), key=lambda x: -x[1])[:10]
sorted(bc.items(), key=lambda x: x[1], reverse=True)[:15]
```

This is repeated for centrality, activation results, pattern counts, and custom scoring.

## Proposed API

Two complementary additions:

### 1. `top_k()` utility function

Add a module-level utility in `results.py`:

```python
def top_k(scores: dict[str, float], k: int = 10) -> list[tuple[str, float]]:
```

Returns the top-k items sorted by score descending.

### 2. `top_k` parameter on centrality methods

Modify existing centrality methods to accept `top_k`:

```python
def degree_centrality(self, *, top_k: int | None = None) -> dict[str, float]:
def betweenness_centrality(self, *, top_k: int | None = None) -> dict[str, float]:
def pagerank(self, *, alpha: float = 0.85, ..., top_k: int | None = None) -> dict[str, float]:
```

When `top_k` is set, returns only the top-k entries.

### Examples
```python
# Utility function
top_genres = top_k(genre_counts, k=5)

# On centrality methods
top_10 = mem.betweenness_centrality(top_k=10)
all_scores = mem.betweenness_centrality()  # unchanged behavior

# Chaining
for concept, score in mem.pagerank(top_k=20):
    print(f"  {concept}: {score:.4f}")
```

## Implementation Notes

### `top_k()` utility
- Goes in `results.py` (utility for result processing)
- Simple: `sorted(scores.items(), key=lambda x: -x[1])[:k]`
- Returns `list[tuple[str, float]]`, not dict (preserves ordering)

### `top_k` on centrality methods
- Keyword-only parameter (EP-6)
- `top_k=None` returns all (backward compatible)
- `top_k=N` returns dict with only top-N entries
- Applied AFTER computing all scores (no early termination — the computation is the expensive part, not the sorting)

### Export from `__init__.py`
- `top_k` should be exported for user convenience

## Tests
- `top_k()` returns correctly sorted results
- `top_k()` with k > len(scores) returns all
- `top_k()` with k=1 returns single-item list
- `top_k()` with empty dict returns []
- `top_k=None` on centrality returns all (backward compatible)
- `top_k=5` on centrality returns only 5 entries
- Returned dict is correctly sorted by score descending
