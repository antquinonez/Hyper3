# 11. Troubleshooting

## "Rules applied: 0" but I added rules

Rules only match edges where both endpoints are in the seed set (or reached by
prior rule applications). If your seeds are `{"CVE-X"}` but the edges go
`APT28 -> CVE-X`, the rule will not see APT28 because it is not a seed.

Include both endpoints in the seeds:

```python
mem.reason({"APT28", "CVE-X", "GOV"}, depth=3)
```

Or use `exhaustive=True` to bypass seed scoping entirely.

## Collapsed to the wrong hypothesis

Sampling is probabilistic (Born rule). A single sample may not return the
highest-probability outcome. Run multiple trials to see the distribution, or
use `mem.belief.probabilities(state)` to inspect the weights before sampling.

## Merge merged unrelated nodes

The equivalence engine merges nodes with matching data and overlapping
neighborhoods. If two nodes have identical `data` dicts (same keys, same
values), they will be merged regardless of semantic meaning.

Provide discriminative data -- a unique `id` or `name` field prevents false
merges:

```python
mem.add("concept_a", data={"id": "a_001", "source": "feed_1"})
mem.add("concept_b", data={"id": "b_002", "source": "feed_2"})
```

## Spreading activation activates too few nodes

On small graphs, the default normalization compresses the activation tail.
Increase `iterations` or lower the energy threshold:

```python
results = mem.search.activate("concept", top_k=20)
```

## Evolution doesn't prune stale nodes

Nodes are only pruned if their weight is below the decay threshold (default
0.1) **and** their access count is 0. After `add()`, a node has
`access_count=1`. To force pruning, lower the weight and clear the access
count before evolving:

```python
node = mem.graph.get_node_by_label("stale_concept")
node.weight = 0.05
node.access_count = 0
mem.evolve()
```

## N-ary edge didn't fire in "and" diffusion mode

`and` mode requires **all** source nodes of an edge to be active. Starting
from a single node in a multi-source edge will not fire that edge. Use `"or"`
or `"majority"` mode if any-source activation is intended.

## `query_hyperedges()` returns UUIDs, not labels

Raw `Hyperedge` objects use internal node IDs. Convert with `mem.node_label()`:

```python
for e in mem.query_hyperedges(containing="TP53"):
    src_labels = [mem.node_label(s) for s in e.source_ids]
    tgt_labels = [mem.node_label(t) for t in e.target_ids]
```

Or use `mem.analyze.edges()` which returns objects with `source_labels` and
`target_labels` already resolved.

## Community detection gives different results each run

Label propagation uses random tie-breaking. Even with a fixed seed, results
can vary across process invocations. Use `method="connected_components"` for
deterministic results, or `method="louvain"` for stable modularity
optimization.

## `recall()` returns Hypernodes, not (label, depth) pairs

`recall()` returns a list of `Hypernode` objects. Each has a `.label` attribute.
There is no `.depth` attribute on the return value -- depth is an internal
traversal parameter, not a per-node property.

```python
for node in mem.recall("concept", max_depth=3):
    print(node.label)
```

Next: [API Migration](12-migration.md)
