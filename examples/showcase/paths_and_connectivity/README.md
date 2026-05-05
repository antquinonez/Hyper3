# Paths and Connectivity

> Shortest paths, distance matrices, connected components, and traversal across three graph topologies

## 1. The Approach

Path analysis answers three questions about a knowledge graph: **Can I get from A to B?** (connected components), **What is the shortest route?** (shortest paths), and **How far apart are all pairs of nodes?** (distance matrices). These are the foundational operations for reachability analysis, clustering, anomaly detection, and information flow.

In a hypergraph, these questions gain a new dimension. A hyperedge connects multiple source nodes to multiple target nodes in a single edge. When path-finding algorithms treat a hyperedge as a single hop rather than decomposing it into pairwise connections, the shortest path can change. Two nodes that appear distant through pairwise edges may be adjacent through a shared hyperedge.

The three scripts in this showcase demonstrate these capabilities across progressively more complex topologies:

- **Script 20** — a 7-node city network with a transit-zone hyperedge
- **Script 29** — three separate graphs: a disconnected graph with isolated components, a weighted chain, and a mixed-edge-size graph
- **Script 35** — an 8-node road network with weighted/unweighted path comparison and disconnected islands

## 2. Key Concepts

| Concept | What it measures | Why it matters |
|---------|-----------------|----------------|
| **Shortest path** | Minimum-hop (or minimum-cost) route between two nodes | Identifies optimal traversal routes; the basis for distance computation |
| **Hyperedge-as-single-hop** | N-ary edges count as one hop in path finding | Reduces path lengths when multiple nodes are jointly connected; reflects that collective relationships enable direct access |
| **All-pairs distance matrix** | Distance from every node to every other node | Reveals global structure: clusters appear as blocks of short distances, bottlenecks appear as rows with high values |
| **Single-source distances** | Distance from one seed node to all reachable nodes | Useful for influence-radius analysis and nearest-neighbor queries |
| **Connected components** | Maximal sets of mutually reachable nodes | Determines whether the graph is fully traversable or fragmented into isolated subgraphs |
| **Density** | Ratio of actual edges to maximum possible edges | Indicates graph sparsity; low density suggests sparse relationships, high density suggests redundancy |
| **Edge size / order** | Number of nodes participating in an edge (order = size - 1) | Characterizes whether the graph uses only pairwise edges or higher-arity hyperedges |
| **Weighted vs unweighted** | Weighted paths use `cost = 1/weight`; unweighted paths count hops | Weighted paths favor high-importance edges; unweighted paths favor fewer hops. They can produce different shortest paths |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/paths_and_connectivity/20_shortest_paths_and_traversal.py
```

```
cities: 7, routes: 9

shortest path london -> rome: ['london', 'prague', 'vienna', 'rome']
  length (hops): 3

shortest path london -> prague: ['london', 'prague']
  hyperedge 'europass_zone' treats {london,paris} -> {berlin,prague} as 1 hop
```

```bash
.venv/bin/python examples/showcase/paths_and_connectivity/29_connectivity_and_distances.py
```

```
is_connected: False
connected components: 3
  component 0: ['a', 'b', 'c', 'd']
  component 1: ['x', 'y', 'z']
  component 2: ['isolated']

density: 0.0714
max edge order: 4
```

```bash
.venv/bin/python examples/showcase/paths_and_connectivity/35_advanced_paths.py
```

```
shortest path (weighted):   ['s', 'a', 'c', 't']
shortest path (unweighted): ['s', 'a', 'c', 't']

from s: {'a': 0.1, 'b': 0.5, 'c': 0.3, 'd': 0.6, 't': 0.425}
from t: {}
```

## 4. Script Walkthroughs

### 4a. Shortest Paths and Traversal (`shortest_paths_and_traversal.py`)

**Graph**: 7 city nodes, 8 pairwise routes, 1 hyperedge (`europass_zone` connecting {london, paris} to {berlin, prague}).

**Shortest paths** use Dijkstra with `cost = 1/weight`. The route london -> rome takes 3 hops (london -> prague -> vienna -> rome). The route madrid -> prague returns `None` because directed edges do not create a path from madrid to prague (madrid only has an outgoing edge to rome).

**All paths** enumeration finds 7 distinct routes from london to rome. Some paths appear duplicated because the hyperedge and pairwise edges create parallel connections between the same node pairs.

**BFS traversal** via `recall("london", max_depth=3)` reaches 6 of the 7 cities within 3 hops from london (rome is at depth 4).

**Hyperedge-as-single-hop**: The `europass_zone` hyperedge connects {london, paris} to {berlin, prague} in one hop. Without it, the shortest path london -> prague would be london -> berlin -> prague (2 hops). With the hyperedge, it is london -> prague (1 hop). This matters because collective relationships — transit zones, collaboration groups, shared resources — enable direct access that pairwise decomposition would not reflect.

### 4b. Connectivity and Distances (`connectivity_and_distances.py`)

**Graph 1 (disconnected)**: 8 nodes, 5 pairwise edges forming three isolated components: {a, b, c, d}, {x, y, z}, and {isolated}. The graph is not connected. `component_of("b")` returns {a, b, c, d}; `component_of("isolated")` returns only {isolated}.

**Graph 2 (weighted chain)**: 6 nodes in a linear chain (s0 -> s1 -> ... -> s5), each edge weighted 2.0. The all-pairs distance matrix shows triangular structure with `cost = 1/2.0 = 0.5` per hop. `s0` to `s5` costs 2.50 (5 hops x 0.50). Unweighted single-source from `s3` counts pure hops: {s3: 0, s4: 1, s5: 2}. Upper-triangular `inf` values reflect the directed chain — no reverse path exists.

**Graph 3 (mixed edges)**: 8 nodes, 4 edges (2 pairwise + 2 hyperedges of sizes 5 and 3). Density is 0.0714 (4 edges out of 56 possible). The unique edge sizes [2, 3, 5] show a mix of pairwise and higher-arity edges. Max edge order is 4 (the 5-node hyperedge). The graph splits into two components despite having hyperedges: the {x, y, z} triple-edge is disconnected from {a, b, c, d, e}.

### 4c. Advanced Paths (`advanced_paths.py`)

**Graph**: 6 nodes (s, a, b, c, d, t) with 8 directed weighted edges, later extended with 2 disconnected nodes (x, y).

**Weighted vs unweighted**: Both produce the same shortest path s -> t: `['s', 'a', 'c', 't']`. This happens because the high-weight edges (10.0 for s->a, 5.0 for a->c, 8.0 for c->t) also happen to form the fewest-hop route. In graphs where cheap edges take detours, weighted and unweighted paths diverge.

**All-pairs distance matrix**: The weighted matrix shows cost from each node to each reachable node. Node `t` has `inf` to all others (no outgoing edges). Node `s` reaches all others. The unweighted matrix replaces costs with hop counts — `s` to `t` is 3 hops regardless of edge weights.

**Single-source from multiple seeds**: From `s`, reachable nodes cost 0.1 (a) to 0.425 (t). From `a`, costs drop because `a` is already one hop into the network. From `c`, `t` costs only 0.125 (weight 8.0, cost 1/8). From `t`, no nodes are reachable (sink node).

**Disconnected islands**: Adding nodes `x` and `y` with a single edge between them creates a separate component. `single_source_distances("s")` reaches 8 nodes but not `x` or `y`. `single_source_distances("x")` reaches only {x: 0.0, y: 0.2}.

## 5. Key Metrics

| Metric | Script 20 | Script 29 | Script 35 |
|--------|-----------|-----------|-----------|
| Nodes | 7 | 8 / 6 / 8 | 6 (+2 island) |
| Edges | 9 (8 pairwise + 1 hyperedge) | 5 / 5 / 4 | 8 (+1 island) |
| Connected components | 1 | 3 / 1 / 2 | 1 (+1 island) |
| Shortest path london->rome | 3 hops | — | — |
| Shortest path s->t | — | — | 3 hops |
| All paths london->rome | 7 | — | — |
| All paths s->t | — | — | 5 |
| Density | — | — / — / 0.0714 | — |
| Max edge order | 3 (europass_zone: 4 nodes) | — / — / 4 | — |
| Unique edge sizes | — | — / — / [2, 3, 5] | — |
| Hyperedge 1-hop shortcut | london->prague (1 hop instead of 2) | — | — |
| Disconnected nodes | madrid->prague: None | isolated node | x, y unreachable from s |

## 6. What Makes This Different

**Hyperedges count as single hops in path finding.** The `europass_zone` hyperedge connects {london, paris} to {berlin, prague} as one edge. When Dijkstra traverses the graph, it treats this as a single hop with the hyperedge's weight, not as four separate pairwise connections. This produces shorter paths that reflect the collective semantics of the relationship. Decomposing the hyperedge into pairwise edges would show london -> prague as a 2-hop path; the hyperedge makes it 1 hop.

**Directed distance matrices expose graph asymmetry.** The upper-triangular `inf` values in the chain graph's distance matrix are not errors — they show that information can flow forward along the chain but not backward. In an undirected projection, every node would reach every other node. The directed distance matrix preserves this asymmetry, which is critical for flow analysis, influence propagation, and dependency tracking.

**Connectivity queries handle hyperedges correctly.** In the mixed-edge graph, the 5-node hyperedge ({a, b, c} -> {d, e}) connects all five nodes into a single component even though the underlying pairwise edges only connect a-b and b-c. The connectivity algorithm traverses through the hyperedge, recognizing that all five nodes are mutually reachable.

## 7. Code Implementation

### Shortest path (weighted)

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
mem.ensure("a")
mem.ensure("b")
mem.relate("a", "b", label="link", weight=5.0)

path = mem.shortest_path("a", "b", weighted=True)
# ['a', 'b']
```

### All-pairs distance matrix

```python
dists = mem.shortest_path_lengths(weighted=True)
# {'a': {'a': 0.0, 'b': 0.2}, 'b': {'b': 0.0}}
```

### Single-source distances

```python
from_a = mem.single_source_distances("a", weighted=True)
# {'a': 0.0, 'b': 0.2}
```

### Connected components

```python
components = mem.connected_components()
# [['a', 'b']]

mem.is_connected()       # True if 1 component
mem.largest_connected_component()  # largest component as set
mem.component_of("a")    # component containing 'a'
```

### Hyperedge as single hop

```python
mem.relate_hyperedge(
    sources={"london", "paris"},
    targets={"berlin", "prague"},
    label="europass_zone",
    weight=10.0,
)

path = mem.shortest_path("london", "prague")
# ['london', 'prague']  -- 1 hop through the hyperedge
```

### Graph metrics

```python
mem.density()             # actual_edges / max_possible_edges
mem.unique_edge_sizes()   # set of (src_size + tgt_size) per edge
mem.max_edge_order()      # largest edge size minus 1
```

## 8. Real-World Gap

- **Scale**: All three scripts operate on 6-8 node graphs. Performance on graphs with 10K+ nodes and high-arity hyperedges is untested. The underlying algorithms use Dijkstra (O(E log V) per source) and BFS, which should scale, but hyperedge expansion increases the effective branching factor.
- **Data pipeline**: Graphs are constructed programmatically with `store()` and `relate()`. Loading from external data sources (CSV, graph databases, APIs) requires integration work outside the scope of these examples.
- **Dynamic graphs**: These scripts analyze static snapshots. The `evolve_interval` parameter enables continuous structural evolution (decay, prune, merge), but path analysis on evolving graphs is not demonstrated here.
- **Weight semantics**: Edge weights represent importance (higher = stronger). The `cost = 1/weight` inversion is a convention, not configurable. Applications with different weight semantics (monetary cost, latency) would need to pre-invert weights.

## 9. Reference

### API Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `mem.shortest_path(src, tgt, weighted=True)` | `list[str] \| None` | Node labels along the shortest path, or `None` if unreachable |
| `mem.find_paths(src, tgt, max_paths=10)` | `list[list[str]]` | All simple paths between two nodes |
| `mem.shortest_path_lengths(weighted=True)` | `dict[str, dict[str, float]]` | All-pairs distance matrix |
| `mem.single_source_distances(src, weighted=True)` | `dict[str, float]` | Distances from one node to all reachable nodes |
| `mem.connected_components()` | `list[set[str]]` | All connected components as label sets |
| `mem.is_connected()` | `bool` | Whether the graph has exactly one component |
| `mem.largest_connected_component()` | `set[str]` | Nodes in the largest component |
| `mem.component_of(concept)` | `set[str]` | Component containing the given concept |
| `mem.density()` | `float` | Edge-to-maximum-possible-edge ratio |
| `mem.unique_edge_sizes()` | `list[int]` | Distinct node counts across all edges |
| `mem.max_edge_order()` | `int` | Largest edge size minus 1 |
| `mem.recall(concept, max_depth=N)` | `list[Hypernode]` | BFS-like traversal up to N hops |
| `mem.relate_hyperedge(sources, targets, label, weight)` | `Hyperedge` | Create an N-ary directed hyperedge |
