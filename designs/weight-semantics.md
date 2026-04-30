# Edge Weight Semantics

## Status: Accepted

## Context

`Hyperedge.weight` represents edge importance/strength (higher = more important).
Different graph algorithms interpret weights differently. This document clarifies
how each algorithm uses weights and why.

## Decision

All algorithms treat weight as **importance**: higher values mean stronger or more
significant edges. Where algorithms require a cost metric (minimization), the
library inverts weights internally.

### Per-Algorithm Semantics

| Algorithm | Weight Role | Transformation | Rationale |
|-----------|------------|----------------|-----------|
| `shortest_path` (Dijkstra) | Cost = 1/weight | Inverted | Dijkstra minimizes; high importance = low cost |
| `pagerank` | Transition probability | Direct | Higher weight = stronger endorsement = higher rank |
| `betweenness_centrality` | Unweighted | Ignored | Current implementation uses BFS-based shortest path counting |
| `degree_centrality` | Unweighted | Ignored | Counts edges, not weights |
| `find_paths` | Unweighted | Ignored | Enumerates paths regardless of weight |
| `detect_cycles` | Unweighted | Ignored | Cycle detection is structural |
| `connected_components` | Unweighted | Ignored | Union-find on edge connectivity |

### Betweenness Centrality Normalization

`betweenness_centrality()` normalizes by `1/n` (where n = number of source nodes),
not the standard `1/((n-1)(n-2))` used in textbook directed betweenness. This means
values can exceed 1.0 for dense graphs. With `max_samples`, normalization is
`1/max_samples` and values are raw pairwise dependency counts that can exceed 1.0.

This is documented per AGENTS.md: "`betweenness_centrality(max_samples=N)` is not normalized."

### PageRank

PageRank uses edge weights as transition probabilities:
- From source `i`, the probability of following edge `e` to target `j` is
  `weight(e) / (edge_cardinality(e) * sum_of_outgoing_weights(i))`
- Dangling nodes (no outgoing edges) have their mass redistributed proportionally
  via vector renormalization, not uniformly
- This is a weighted PageRank variant, degrading to standard PageRank when all
  weights equal 1.0

## Consequences

- Users should set higher weights on more important edges
- `relate(a, b, weight=10.0)` makes A->B a strong/preferred connection
- Shortest path will prefer this edge; PageRank will give it higher transition probability
- Betweenness and degree centrality ignore weights entirely (structural metrics only)
