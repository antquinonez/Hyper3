# Draft 03: PageRank Centrality

## Problem
Every comparison implementation cites PageRank as a NetworkX advantage:
- CVE comparison: uses `nx.pagerank(G, alpha=0.85, weight="weight")`
- Wikipedia comparison: uses `nx.pagerank(G, alpha=0.85, max_iter=100)`
- Hyper3 has `degree_centrality()` and `betweenness_centrality()` but no PageRank

PageRank is a standard graph algorithm that complements the existing centrality measures.

## Proposed API

Add to `AnalyticsMixin` in `memory_analytics.py`:

```python
def pagerank(
    self,
    *,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-06,
    weighted: bool = True,
) -> dict[str, float]:
```

### Parameters
- `alpha` — damping factor (default 0.85, standard PageRank)
- `max_iter` — maximum iterations
- `tol` — convergence tolerance
- `weighted` — if True, use inverted edge weights; if False, unweighted

### Returns
- `dict[str, float]` — concept labels mapped to PageRank scores (EP-1, consistent with `betweenness_centrality()`)

### Examples
```python
pr = mem.pagerank()
top_concepts = sorted(pr.items(), key=lambda x: -x[1])[:10]

pr_unweighted = mem.pagerank(alpha=0.9, weighted=False)
```

## Implementation Notes
- Goes in `AnalyticsMixin` alongside `degree_centrality()` and `betweenness_centrality()`
- Uses `self._graph._to_networkx_inverted_weights()` for weighted, `self._graph.to_networkx()` for unweighted
- Edge weight semantics: Hyper3 weights are importance (higher = more important), so invert to cost for PageRank personalization. Actually, for PageRank, higher weight edges should contribute MORE to rank, so we should use weights directly (not inverted). Need to verify.
  - Actually, `nx.pagerank(G, weight="weight")` uses edge weight as the transition probability. Higher weight = more likely to traverse = higher rank contribution. Since Hyper3 weights are importance, we should use them directly for PageRank (no inversion needed).
  - For consistency with `betweenness_centrality()`, offer `weighted` flag.
- Returns `{label: score}` using `self._node_label(nid)` for ID-to-label conversion

## Weight Semantics Note
From AGENTS.md: "Edge weights are importance, not cost. The kernel inverts weights to cost = 1/weight when calling networkx algorithms (shortest path, betweenness centrality)."

For PageRank, the weight semantics are different: higher weight = stronger endorsement = higher rank. So we should **NOT** invert weights for PageRank. This is consistent with how PageRank works (transition probability proportional to weight).

But for consistency with the existing `betweenness_centrality()` pattern (which uses inverted weights), the `weighted` flag should:
- `weighted=True`: use raw weights as transition probabilities (no inversion)
- `weighted=False`: unweighted (all edges equal)

## Tests
- Basic PageRank computation
- Consistency with networkx on small graph
- Weighted vs unweighted produces different results
- Custom alpha
- Empty graph returns {}
- Single node returns {label: 1.0}
- Disconnected components
