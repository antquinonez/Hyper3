# Draft 01: `query_nodes()` — Node Filtering by Data Attributes

## Problem
Every pipeline manually iterates `mem.graph.nodes` and filters by `node.data.get("type")`:
```python
# Repeated in movie, arxiv, dependency scanner pipelines
movies = [n for n in mem.graph.nodes if n.data.get("type") == "movie"]
packages = [n for n in mem.graph.nodes if n.data.get("type") == "package"]
```

This reaches through to the kernel (`mem.graph.nodes`), violating the label-at-the-boundary principle (DP-4).

## Proposed API

Add to `AnalyticsMixin` in `memory_analytics.py`:

```python
def query_nodes(
    self,
    *,
    type: str | None = None,
    data: dict[str, Any] | None = None,
    labels: set[str] | None = None,
    limit: int | None = None,
) -> list[str]:
```

### Parameters
- `type` — shorthand for `data={"type": value}` (the most common case)
- `data` — dict of key-value pairs that must all be present in `node.data`. Partial matching: all specified keys must match, but node.data may have additional keys.
- `labels` — filter to only these specific concept labels
- `limit` — max results (None = all)

### Returns
- `list[str]` — concept labels of matching nodes (per EP-1: labels out)

### Behavior
- Query/read operation: returns empty list if no matches (per EP-5)
- Does NOT traverse — just filters the node set by data attributes
- Iterates `self._graph.nodes` internally, checking data fields

### Examples
```python
movie_labels = mem.query_nodes(type="movie")
packages = mem.query_nodes(data={"ecosystem": "pypi", "type": "package"})
authors = mem.query_nodes(data={"kind": "author"}, limit=20)
specific = mem.query_nodes(labels={"cancer", "dna_damage"})
```

## Implementation Notes
- Goes in `AnalyticsMixin` (read-only query)
- Uses `self._graph.nodes` internally (kernel-level iteration)
- Returns labels, not node objects (EP-1)
- `type` param is a convenience shorthand, not a separate code path
- If both `type` and `data` are provided, `type` is merged into `data` dict

## Tests
- Filter by type only
- Filter by multiple data fields
- Filter by labels set
- Combined type + data
- Limit parameter
- Empty result returns []
- Nodes without data field are excluded (no crash)
