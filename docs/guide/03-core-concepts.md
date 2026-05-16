# 3. Core Concepts

## 3.1 Nodes

Every concept in Hyper3 is a node with a human-readable **label**, an optional
**data** payload (an arbitrary dictionary), and a **weight** that tracks
importance over time.

```python
mem.add("X", data={"confidence": 0.9, "source": "analyst"})
```

Methods for node operations:

| Method | Description |
|--------|-------------|
| `mem.add(concept, *, data=..., weight=...)` | Create a node. Returns the concept label. |
| `mem.get(concept, key, *, default=None)` | Retrieve a data field from a node. |
| `mem.has(concept)` | Check if a node exists. |
| `mem.ensure(concept, *, data=..., update=False)` | Create only if absent. `update=True` merges new data into existing. |

Labels are the public interface. Node IDs (auto-generated UUIDs) are internal
-- you rarely need to interact with them directly.

## 3.2 Pairwise Edges

`link()` creates a directed edge from one concept to another with a semantic
label and an importance weight.

```python
mem.link("X", "Y", label="causes", weight=5.0)
```

**Weight means importance**, not cost. Higher weight = stronger relationship.
Algorithms interpret weight accordingly: shortest path inverts it (high weight
= low cost = preferred route); PageRank uses it directly as endorsement
strength.

Multiple edges can exist between the same pair of nodes with different labels:

```python
mem.link("X", "Y", label="causes", weight=5.0)
mem.link("X", "Y", label="correlates_with", weight=0.5)
```

### Direction

Edges are directed. `link("A", "B")` creates an edge from A to B. Query
neighbors with a direction filter:

```python
mem.neighbors("A", direction="out")   # concepts A points to
mem.neighbors("A", direction="in")    # concepts pointing to A
mem.neighbors("A", direction="any")   # both directions (default)
```

## 3.3 N-ary Directed Hyperedges

This is where Hyper3 departs from standard graph libraries.

A **pairwise edge** connects exactly one source to exactly one target. But many
real relationships involve groups: three researchers jointly author a paper, two
enzymes cooperatively catalyze a reaction, a vulnerability affects multiple
services simultaneously.

An **n-ary hyperedge** connects a *set* of source nodes to a *set* of target
nodes in a single edge. The collective semantics are preserved -- removing any
source node changes the meaning of the edge, rather than simply removing one of
several independent pairwise links.

### Creating N-ary Edges

`link_hyper()` creates an n-ary directed hyperedge:

```python
mem.add("alice")
mem.add("bob")
mem.add("carol")
mem.add("project_x")

mem.link_hyper(
    sources={"alice", "bob", "carol"},
    targets={"project_x"},
    label="joint_project",
    weight=10.0,
)
```

This single edge says "alice, bob, and carol *collectively* deliver project_x."
Decomposing it into three pairwise edges (`alice -> project_x`, `bob ->
project_x`, `carol -> project_x`) would lose the collective semantics:
removing carol from the pairwise version leaves two edges intact, whereas the
real relationship no longer holds.

### Rules for N-ary Edges

- All source and target concepts must already exist (created with `add()`).
  `link_hyper()` raises `NodeNotFoundError` for missing concepts.
- Both `sources` and `targets` must be non-empty sets.
- Weight must be positive (> 0).
- Sets are unordered: `{"alice", "bob"}` and `{"bob", "alice"}` produce the
  same edge.
- A single n-ary edge counts as **one** incident edge per participating node
  for degree calculations.

### Pairwise and N-ary Coexist

`link()` and `link_hyper()` work on the same graph. All algorithms handle both
edge types transparently.

```python
mem.link("alice", "bob", label="collaborates")
mem.link_hyper(
    sources={"alice", "bob", "carol"},
    targets={"project_x"},
    label="joint_project",
    weight=10.0,
)
```

This graph has one pairwise edge and one 3-source n-ary edge. Centrality,
shortest path, community detection, and other algorithms operate on the full
mixed structure without requiring you to specify edge types.

### Fan-out and Fan-in

A single source can fan out to multiple targets, or multiple sources can
converge on a single target:

```python
mem.link_hyper(
    sources={"web_host"},
    targets={"svc_http", "svc_https", "svc_ssh"},
    label="runs",
    weight=1.0,
)
```

## 3.4 Querying Hyperedges

### Filter by Cardinality

`query_hyperedges()` filters edges by how many nodes they connect:

```python
mem.query_hyperedges(min_source_cardinality=2)
```

Returns edges where the source set has 2 or more nodes -- the true n-ary edges.
Without filters, it returns all edges.

### Filter by Node Membership

Find every edge that a specific concept participates in:

```python
mem.query_hyperedges(containing="TP53")
```

### Co-participation

`hyperedge_neighbors()` returns a dict mapping each neighboring concept to the
list of shared edges. This answers "which concepts co-occur in the same
relationships as this node?"

```python
neighbors = mem.hyperedge_neighbors("alice")
for neighbor, shared_edges in neighbors.items():
    print(f"  {neighbor}: {len(shared_edges)} shared edges")
```

```
  bob: 2 shared edges
  project_x: 1 shared edge
  carol: 1 shared edge
```

### Edge Size Statistics

```python
mem.graph.unique_edge_sizes()   # distinct node counts across edges
mem.graph.max_edge_order()      # largest edge cardinality minus 1
```

### A Note on Return Types

`query_hyperedges()` returns raw `Hyperedge` objects, which use internal node
IDs. To get human-readable labels, convert with `mem.node_label()` or use
`mem.analyze.edges()` which provides `source_labels` and `target_labels`
directly.

## 3.5 Hypergraph-Native Algorithms

Hyper3 implements its graph algorithms natively on the hypergraph structure,
rather than decomposing n-ary edges into pairwise edges and running standard
graph algorithms on the decomposition.

What this means concretely:

### Shortest Path

An edge `{A, B} -> {C, D}` is treated as a **single hop**. Both A and B can
reach both C and D in distance 1. In a pairwise decomposition, this would be
four separate edges each counted as one step.

### Connected Components

Components are computed via union-find on hyperedge vertex overlap. Two nodes
are in the same component if they share an edge. The `s` parameter controls
the overlap threshold: `s=2` requires edges to share at least 2 nodes to be
considered connected.

### PageRank

PageRank uses the incidence-based transition matrix
`P = D_v^{-1} H W D_e^{-1} H^T` (Zhou, Huang, Schoelkopf 2006), which accounts
for edge cardinality through the `D_e^{-1}` normalization. This produces
different scores than adjacency-based PageRank on a pairwise projection.

### Betweenness Centrality

Paths are enumerated treating each hyperedge as a single structural unit. A
node that sits between two large n-ary edges has higher betweenness than one
between two pairwise edges.

### Graceful Degradation

When all edges are pairwise (1 source, 1 target), these algorithms produce the
same results as standard graph algorithms. Hypergraph-native behavior only
manifests when n-ary edges are present.

## 3.6 The Facade and Namespaces

`HypergraphMemory` is the single entry point. It composes from twelve mixins,
each owning a domain. Operations are accessed through **namespace properties**:

| Namespace | Attribute | Domain |
|-----------|-----------|--------|
| Reason | `mem.reason` | Inference rules, multiway expansion |
| Belief | `mem.belief` | Born-rule distributions, sampling |
| Bayesian | `mem.bayes` | Prior/posterior, MAP, Bayes factors |
| Search | `mem.search` | Activation, similarity, structured search |
| Analyze | `mem.analyze` | Centrality, paths, communities, spectral |
| Temporal | `mem.temporal` | Allen interval algebra, causal chains |
| Cognitive | `mem.cognitive` | Backward chaining, Hebbian learning |
| Monitor | `mem.monitor` | System health, introspection |

Shortcut methods exist on the facade for the most common operations (`mem.add`,
`mem.link`, `mem.evolve`, `mem.recall`) and delegate to the appropriate
namespace.

## 3.7 Evolve Interval

`HypergraphMemory(evolve_interval=N)` runs self-evolution (decay, prune,
merge) automatically every N operations. Set to `0` (default) to disable
auto-evolution and call `mem.evolve()` manually.

```python
mem = HypergraphMemory()                    # no auto-evolution
mem = HypergraphMemory(evolve_interval=10)  # evolve every 10 ops
```

Most scripts use `evolve_interval=0` for deterministic behavior.

Next: [Retrieval and Search](04-retrieval-and-search.md)
