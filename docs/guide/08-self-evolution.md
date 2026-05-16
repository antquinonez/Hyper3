# 8. Self-Evolution

The graph continuously optimizes its own structure through four operations:
decay, prune, merge, and reinforce.

```python
evo = mem.evolve()
print(f"Decayed:    {evo.decayed}")
print(f"Pruned:     {evo.pruned}")
print(f"Merged:     {evo.merged}")
print(f"Reinforced: {evo.reinforced}")
```

## What Happens

### Decay

Every node's weight is multiplied by 0.85. Nodes that cross the decay threshold
(default 0.1) are counted as "decayed." This models the intuition that unused
knowledge gradually loses relevance.

### Prune

Nodes below the decay threshold with `access_count == 0` are removed entirely.
These are stale indicators, old data, or unused concepts that no part of the
system has touched.

### Merge

Nodes with identical or highly similar data and overlapping neighborhoods are
merged. The primary node absorbs the secondary's edges and data.

The equivalence engine combines:
- **Data similarity**: fraction of matching dict values on shared keys.
- **Structural similarity**: Jaccard overlap of neighbor sets.
- A combined score >= 0.8 triggers a merge.

Two nodes with no edges have structural similarity 0.0 (no evidence of
equivalence), not 1.0. Provide rich, discriminative data to avoid false merges.
If two nodes share all dict values, they will be merged regardless of semantic
meaning.

### Reinforce

Frequently-accessed nodes get their weight boosted. This models the intuition
that actively-used knowledge should stay prominent.

## Automatic Evolution

Set `evolve_interval` at construction to run evolution automatically after every
N operations:

```python
mem = HypergraphMemory(evolve_interval=50)
```

For deterministic behavior in scripts and tests, use `evolve_interval=0`
(default) and call `mem.evolve()` explicitly.

## Feedback-Driven Evolution

`mem.monitor.evolve_with_feedback()` checks the fitness trend from
`OperationFeedback` and adapts evolution parameters:

- **Declining fitness**: intensifies decay (1.5x), lowers pruning threshold
  (0.75x), reinforces top-3 positively-reinforced nodes, force-prunes
  suppressed nodes.
- **Stable or improving fitness**: standard parameters.

This requires prior feedback recording via `mem.search.feedback` and other
feedback channels.

Next: [Temporal Reasoning](09-temporal.md)
