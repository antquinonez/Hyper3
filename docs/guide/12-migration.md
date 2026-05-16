# 12. API Migration

If you followed the previous version of the user guide, some method names have
changed. This table maps old names to their current equivalents.

## Removed Methods

These methods no longer exist and will raise `AttributeError`:

| Old (broken) | Current API |
|---|---|
| `mem.store(concept, data=...)` | `mem.add(concept, data=...)` |
| `mem.relate(source, target, label=...)` | `mem.link(source, target, label=...)` |
| `mem.stimulate(concept, energy=...)` | `mem.search.activate(concept, ...)` |
| `mem.spread_activation(iterations=N)` | `mem.search.activate(concept, ...)` |
| `mem.degree_centrality()` | `mem.analyze.centrality("degree")` |
| `mem.betweenness_centrality()` | `mem.analyze.centrality("betweenness")` |
| `mem.pattern_match(source_label=..., edge_label=...)` | `mem.analyze.pattern(source=..., label=...)` |
| `mem.detect_cycles()` | `mem.analyze.cycles()` |
| `mem.connected_components()` | `mem.analyze.components()` |
| `mem.subgraph(concepts)` | `mem.analyze.subgraph(concepts)` |

## Renamed Parameters

| Method | Old Parameter | Current Parameter |
|--------|--------------|-------------------|
| `mem.reason()` | `seed_concepts` | positional first argument |
| `mem.reason()` | `max_depth` | `depth` |
| `mem.create_distribution()` | (method) | `mem.belief.create()` |
| `mem.sample(state)` | (method) | `mem.belief.sample(state)` |
| `mem.commit_inferences()` | (method) | `mem.reason.commit()` |
| `mem.rollback_inferences()` | (method) | `mem.reason.rollback()` |
| `mem.add_rules(rule)` | (method) | `mem.reason.add_rules(rule)` |

## Stale Conceptual Names

| Old Name | Current Name |
|----------|-------------|
| `QuantumInterpretationLayer` | `BeliefLayer` |
| `QuantumInterpretationLayer` (in docs) | `BeliefLayer` |

## Shortcut Methods Still Work

Some methods exist both as shortcuts on the facade and in their namespace:

```python
mem.reason.add_rules(rule)  # preferred
mem.add_rules(rule)         # still works as shortcut

mem.reason({"A", "B"}, depth=2)  # preferred
mem.reason({"A", "B"}, max_depth=2)  # still works

mem.belief.create(...)  # preferred
mem.create_distribution(...)  # still works as shortcut
```

The namespace form is preferred for clarity, but shortcuts will not break
existing code.
