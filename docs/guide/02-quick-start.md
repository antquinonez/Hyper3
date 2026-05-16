# 2. Quick Start

Build a small knowledge graph, run inference, and inspect the results.

## Build the Graph

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)

mem.add("Log4j", data={"type": "vulnerability", "cvss": 10.0})
mem.add("APT28", data={"type": "threat_actor", "origin": "Russia"})
mem.add("GOV", data={"type": "sector", "name": "Government"})

mem.link("APT28", "Log4j", label="exploits")
mem.link("APT28", "GOV", label="targets")
```

`add()` creates a concept node with a human-readable label and an optional data
payload. `link()` creates a directed edge between two concepts. Both accept
keyword-only optional parameters.

## Explore

```python
results = mem.recall("Log4j", max_depth=2)
for r in results:
    print(f"  {r.label}")
```

```
  Log4j
  APT28
```

`recall()` performs a breadth-first traversal from a concept and returns the
reachable nodes.

## Query Neighbors

```python
print(mem.neighbors("APT28", direction="out"))
```

```
['Log4j', 'GOV']
```

Neighbors returns the labels of adjacent nodes. Use `direction="in"` for
incoming edges, `direction="out"` for outgoing, or `direction="any"` (default)
for both.

## Check and Retrieve Data

```python
print(mem.has("Log4j"))
print(mem.get("Log4j", "type"))
```

```
True
vulnerability
```

## Run Inference

```python
from hyper3 import TransitiveRule

mem.add("Paris")
mem.add("France")
mem.add("Europe")

mem.link("Paris", "France", label="located_in", weight=5.0)
mem.link("France", "Europe", label="located_in", weight=4.0)

mem.reason.add_rules(TransitiveRule(edge_label="located_in"))
result = mem.reason({"Paris", "France", "Europe"}, depth=2)

print(f"States created: {result.expansion.states_created}")
print(f"Edges after reasoning: {mem.graph.edge_count}")
```

```
States created: 2
Edges after reasoning: 3
```

The `TransitiveRule` detected that Paris is in France and France is in Europe,
so Paris must be in Europe. It created a new inferred edge. We will cover
reasoning in depth in [Chapter 5](05-reasoning.md).

## What Just Happened

- `add()` / `link()` build a directed graph of labeled concepts.
- `recall()` / `neighbors()` traverse it.
- `reason()` applies inference rules to discover new edges.
- All public methods accept and return **labels** (strings), not internal IDs.

Next: [Core Concepts](03-core-concepts.md)
