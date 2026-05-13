# Paths and Connectivity

> Shortest paths, distance matrices, connected components, traversal, reasoning, activation, versioning, evolution, and community detection across three graph topologies

## 1. The Approach

Path analysis answers three questions about a knowledge graph: **Can I get from A to B?** (connected components), **What is the shortest route?** (shortest paths), and **How far apart are all pairs of nodes?** (distance matrices). These are the foundational operations for reachability analysis, clustering, anomaly detection, and information flow.

In a hypergraph, these questions gain a new dimension. A hyperedge connects multiple source nodes to multiple target nodes in a single edge. When path-finding algorithms treat a hyperedge as a single hop rather than decomposing it into pairwise connections, the shortest path can change. Two nodes that appear distant through pairwise edges may be adjacent through a shared hyperedge.

The three scripts in this showcase demonstrate these capabilities across progressively more complex topologies:

- **Shortest paths and traversal** — a 7-node city network with hyperedge shortcuts, transitive reasoning, and spreading activation
- **Connectivity and distances** — three separate graphs: a disconnected graph, a weighted chain, and a mixed-edge graph, plus evolution impact and community detection
- **Advanced paths** — a 6-node road network with weighted/unweighted path divergence and graph versioning

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
| **Transitive reasoning** | Infers indirect connections via rule-based multiway expansion | Discovers routes not explicitly stored: if A connects to B and B connects to C, the system infers A connects to C |
| **Spreading activation** | Propagates energy from a seed node through the graph | Surfaces nodes that are structurally close to the seed, weighted by edge strength and distance |
| **Graph versioning** | Captures snapshots and computes deltas between versions | Tracks structural changes to the graph over time, showing what was added or removed |
| **Evolution** | Decay, prune, and merge operations that reshape the graph | Simulates how knowledge graphs self-maintain: removing noise, merging duplicates, and preserving strong connections |
| **Community detection** | Groups nodes into communities based on edge structure | Identifies clusters of densely-connected nodes; useful for understanding graph topology and subgraph structure |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/core/paths_and_connectivity/shortest_paths_and_traversal.py
```

```
cities: 7, routes: 9

shortest path london -> rome: ['london', 'prague', 'vienna', 'rome']
  length (hops): 3

shortest path london -> prague: ['london', 'prague']
  hyperedge 'europass_zone' treats {london,paris} -> {berlin,prague} as 1 hop
```

```bash
.venv/bin/python examples/showcase/core/paths_and_connectivity/connectivity_and_distances.py
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
.venv/bin/python examples/showcase/core/paths_and_connectivity/advanced_paths.py
```

```
shortest path (weighted):   ['s', 'a', 'c', 't']
shortest path (unweighted): ['s', 'b', 'c', 't']

from s: {'a': 0.1, 'b': 0.5, 'c': 0.30000000000000004, 'd': 0.6, 't': 0.42500000000000004}
from t: {}
```

## 4. Script Walkthroughs

### 4a. Shortest Paths and Traversal (`shortest_paths_and_traversal.py`)

**Graph**: 7 city nodes, 8 pairwise routes, 1 hyperedge (`europass_zone` connecting {london, paris} to {berlin, prague}).

**Shortest paths** use Dijkstra with `cost = 1/weight`. The route london -> rome takes 3 hops (london -> prague -> vienna -> rome). The route madrid -> prague returns `None` because directed edges do not create a path from madrid to prague (madrid only has an outgoing edge to rome).

**All paths** enumeration finds 7 distinct routes from london to rome. Some paths appear duplicated because the hyperedge and pairwise edges create parallel connections between the same node pairs.

**BFS traversal** via `recall("london", depth=3)` reaches 6 of the 7 cities within 3 hops from london (rome is at depth 4).

**Hyperedge-as-single-hop**: The `europass_zone` hyperedge connects {london, paris} to {berlin, prague} in one hop. Without it, the shortest path london -> prague would be london -> berlin -> prague (2 hops). With the hyperedge, it is london -> prague (1 hop). This matters because collective relationships — transit zones, collaboration groups, shared resources — enable direct access that pairwise decomposition would not reflect.

**Reasoning**: A `TransitiveRule` with `edge_label="train"` infers indirect train routes. The graph contains chains like london -> paris -> berlin (`train`) and prague -> vienna (`train`). The rule finds that berlin connects to prague (`train`) and prague connects to vienna (`train`), producing 1 inferred edge: berlin -[indirect_train]-> vienna. The reasoning expansion creates 2 states, applies 1 rule, and reaches max depth 1.

**Spreading activation**: Stimulating london with energy 1.0 and spreading for 3 iterations activates 6 nodes. Paris and berlin receive the highest activation (1.0000 and 0.9625) at depth 1 because they are directly connected to london via high-weight edges. London itself retains activation 0.8094. Prague reaches 0.7215 at depth 1 (via the hyperedge). Vienna (0.1502) and madrid (0.1060) receive lower activation at depth 2. This reveals which cities are most strongly associated with london in terms of edge weight and connectivity.

### 4b. Connectivity and Distances (`connectivity_and_distances.py`)

**Graph 1 (disconnected)**: 8 nodes, 5 pairwise edges forming three isolated components: {a, b, c, d}, {x, y, z}, and {isolated}. The graph is not connected. `component_of("b")` returns {a, b, c, d}; `component_of("isolated")` returns only {isolated}.

**Graph 2 (weighted chain)**: 6 nodes in a linear chain (s0 -> s1 -> ... -> s5), each edge weighted 2.0. The all-pairs distance matrix shows triangular structure with `cost = 1/2.0 = 0.5` per hop. `s0` to `s5` costs 2.50 (5 hops x 0.50). Unweighted single-source from `s3` counts pure hops: {s3: 0, s4: 1, s5: 2}. Upper-triangular `inf` values reflect the directed chain — no reverse path exists.

**Graph 3 (mixed edges)**: 8 nodes, 4 edges (2 pairwise + 2 hyperedges of sizes 5 and 3). Density is 0.0714 (4 edges out of 56 possible). The unique edge sizes [2, 3, 5] show a mix of pairwise and higher-arity edges. Max edge order is 4 (the 5-node hyperedge). The graph splits into two components despite having hyperedges: the {x, y, z} triple-edge is disconnected from {a, b, c, d, e}.

**Evolution impact**: An 8-node graph with 6 edges (4 strong links weighted 5.0, 2 weak links weighted 0.1) starts with 2 components. After evolution, the engine merges 4 nodes, reducing the graph to 4 nodes and 6 edges while maintaining 2 components. The merge operation combines equivalent nodes (nodes with overlapping connectivity and data), demonstrating how evolution can simplify graph structure without changing the component topology.

**Community detection**: Running community detection on the mixed-edge graph (Graph 3) finds 2 communities matching the component structure: {a, b, c, d, e} (size 5) and {x, y, z} (size 3). Modularity is 0.2778 and coverage is 1.0000, meaning every node is assigned to a community and the communities capture all within-community edges.

### 4c. Advanced Paths (`advanced_paths.py`)

**Graph**: 6 nodes (s, a, b, c, d, t) with 8 directed weighted edges, later extended with 2 disconnected nodes (x, y).

**Weighted vs unweighted**: The two modes produce *different* shortest paths from s to t. The weighted path is `['s', 'a', 'c', 't']` (cost 0.10 + 0.20 + 0.12 = 0.43, favoring the high-weight edges s->a=10.0, a->c=5.0, c->t=8.0). The unweighted path is `['s', 'b', 'c', 't']` (3 hops, tied with the weighted path but preferring a different route). This demonstrates that weight-aware path finding produces different results when cheap-by-weight edges diverge from the fewest-hop route.

**All-pairs distance matrix**: The weighted matrix shows cost from each node to each reachable node. Node `t` has `inf` to all others (no outgoing edges). Node `s` reaches all others. The unweighted matrix replaces costs with hop counts — `s` to `t` is 3 hops regardless of edge weights.

**Single-source from multiple seeds**: From `s`, reachable nodes cost 0.1 (a) to 0.425 (t). From `a`, costs drop because `a` is already one hop into the network. From `c`, `t` costs only 0.125 (weight 8.0, cost 1/8). From `t`, no nodes are reachable (sink node).

**Disconnected islands**: Adding nodes `x` and `y` with a single edge between them creates a separate component. `single_source_distances("s")` reaches 6 nodes but not `x` or `y`. `single_source_distances("x")` reaches only {x: 0.0, y: 0.2}.

**Graph versioning**: `capture_version()` records a snapshot of the graph (8 nodes, 9 edges at version 0). After adding two new edges (s->c weight 1.5 and b->t weight 1.0), `diff_from_version(0)` computes the delta: 2 total changes, 2 edges added, node count unchanged (8), edge count growing from 9 to 11. The shortest weighted path after the new edges remains `['s', 'a', 'c', 't']` because the existing high-weight edges still outperform the new lower-weight additions.

## 5. Key Metrics

| Metric | Shortest Paths | Connectivity | Advanced Paths |
|--------|---------------|-------------|----------------|
| Nodes | 7 | 8 / 6 / 8 | 6 (+2 island) |
| Edges | 9 (8 pairwise + 1 hyperedge) | 5 / 5 / 4 | 8 (+1 island) |
| Connected components | 1 | 3 / 1 / 2 | 1 (+1 island) |
| Shortest path london->rome | 3 hops | — | — |
| Shortest path s->t (weighted) | — | — | 3 hops (`s,a,c,t`) |
| Shortest path s->t (unweighted) | — | — | 3 hops (`s,b,c,t`) |
| All paths london->rome | 7 | — | — |
| All paths s->t | — | — | 5 |
| Density | — | — / — / 0.0714 | — |
| Max edge order | 3 (europass_zone: 4 nodes) | — / — / 4 | — |
| Unique edge sizes | — | — / — / [2, 3, 5] | — |
| Hyperedge 1-hop shortcut | london->prague (1 hop instead of 2) | — | — |
| Disconnected nodes | madrid->prague: None | isolated node | x, y unreachable from s |
| Inferred edges (reasoning) | 1 (berlin->vienna indirect_train) | — | — |
| Activation spread from london | 6 nodes activated | — | — |
| Evolution merged nodes | — | 4 (8 -> 4 nodes) | — |
| Communities detected | — | 2 (modularity 0.2778) | — |
| Version delta edges added | — | — | 2 (9 -> 11 edges) |

## 6. What Makes This Different

**Hyperedges count as single hops in path finding.** The `europass_zone` hyperedge connects {london, paris} to {berlin, prague} as one edge. When Dijkstra traverses the graph, it treats this as a single hop with the hyperedge's weight, not as four separate pairwise connections. This produces shorter paths that reflect the collective semantics of the relationship. Decomposing the hyperedge into pairwise edges would show london -> prague as a 2-hop path; the hyperedge makes it 1 hop.

**Rule-based reasoning discovers indirect connections.** The `TransitiveRule` applied to the city network inferred that berlin connects to vienna via an `indirect_train` edge — a relationship not explicitly stored in the graph but logically implied by the train route chain prague -> vienna reachable from berlin. This is path analysis enriched by inference: instead of only computing distances on existing edges, the system discovers new edges that compress multi-hop chains into single-hop connections.

**Spreading activation surfaces weighted proximity.** Stimulating london and spreading activation for 3 iterations ranked all 6 reachable cities by structural proximity. The result (paris 1.0000, berlin 0.9625, prague 0.7215) reflects not just hop distance but edge weight and graph topology. A simple hop count would rank all depth-1 nodes equally; activation captures that paris and berlin are more strongly connected to london than prague.

**Graph versioning tracks structural changes over time.** `capture_version()` snapshots the graph state, and `diff_from_version()` computes the delta — showing exactly which edges and nodes were added or removed between versions. This is useful for understanding how graph construction or evolution changes path connectivity.

**Evolution reshapes connectivity.** The evolution engine's merge operation reduced an 8-node graph to 4 nodes by combining equivalent nodes, demonstrating that path analysis operates on a dynamic structure. After evolution, previously separate nodes become single entities, potentially creating new paths or removing old ones.

**Directed distance matrices expose graph asymmetry.** The upper-triangular `inf` values in the chain graph's distance matrix are not errors — they show that information can flow forward along the chain but not backward. In an undirected projection, every node would reach every other node. The directed distance matrix preserves this asymmetry, which is critical for flow analysis, influence propagation, and dependency tracking.

**Community detection complements component analysis.** While connected components identify mutually reachable node sets, community detection groups nodes by edge density. In the mixed-edge graph, communities align with components, but in denser graphs communities can reveal substructure within a single connected component that component analysis alone would not expose.

## 7. Code Implementation

### Shortest path (weighted)

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
mem.ensure("a")
mem.ensure("b")
mem.link("a", "b", label="link", weight=5.0)

path = mem.analyze.shortest_path("a", "b", weighted=True)
# ['a', 'b']
```

### All-pairs distance matrix

```python
dists = mem.shortest_path_lengths(weighted=True)
# {'a': {'a': 0.0, 'b': 0.2}, 'b': {'b': 0.0}}
```

### Single-source distances

```python
from_a = mem.analyze.distances("a", weighted=True)
# {'a': 0.0, 'b': 0.2}
```

### Connected components

```python
components = mem.analyze.components()
# [['a', 'b']]

mem.analyze.is_connected()       # True if 1 component
mem.analyze.largest_component()  # largest component as set
mem.analyze.component_of("a")    # component containing 'a'
```

### Hyperedge as single hop

```python
mem.link_hyper(
    sources={"london", "paris"},
    targets={"berlin", "prague"},
    label="europass_zone",
    weight=10.0,
)

path = mem.analyze.shortest_path("london", "prague")
# ['london', 'prague']  -- 1 hop through the hyperedge
```

### Reasoning with TransitiveRule

```python
from hyper3 import TransitiveRule

mem.add_rules(TransitiveRule(edge_label="train", new_label="indirect_train"))
result = mem.reason(seeds={"london"}, max_depth=3)
# result.expansion.edges_produced -> inferred indirect connections
```

### Spreading activation

```python
activated = mem.search.activate("london", energy=1.0)
# activated: list of (label, activation, depth) sorted by activation
```

### Graph versioning

```python
version_info = mem.capture_version()
# {'version_id': 0, 'node_count': 8, 'edge_count': 9}

mem.link("s", "c", label="new_road", weight=1.5)
delta = mem.diff_from_version(version_info["version_id"])
# delta.edges_added, delta.node_count_before, delta.edge_count_after
```

### Evolution

```python
evolve_result = mem.evolve()
# evolve_result.decayed, evolve_result.pruned, evolve_result.merged
```

### Community detection

```python
cr = mem.analyze.communities(seed=42)
# cr.community_count, cr.modularity, cr.coverage
# cr.communities: list of community objects with member_labels
```

### Graph metrics

```python
mem.analyze.describe().density  # actual_edges / max_possible_edges
mem.unique_edge_sizes()   # set of (src_size + tgt_size) per edge
mem.max_edge_order()      # largest edge size minus 1
```

## 8. Real-World Gap

- **Scale**: All three scripts operate on 6-8 node graphs. Performance on graphs with 10K+ nodes and high-arity hyperedges is untested. The underlying algorithms use Dijkstra (O(E log V) per source) and BFS, which should scale, but hyperedge expansion increases the effective branching factor.
- **Data pipeline**: Graphs are constructed programmatically with `store()` and `relate()`. Loading from external data sources (CSV, graph databases, APIs) requires integration work outside the scope of these examples.
- **Dynamic graphs**: The evolution demo shows a single evolve step. Continuous evolution with `evolve_interval` over time, and path analysis on graphs that change between queries, is not demonstrated here.
- **Weight semantics**: Edge weights represent importance (higher = stronger). The `cost = 1/weight` inversion is a convention, not configurable. Applications with different weight semantics (monetary cost, latency) would need to pre-invert weights.
- **Activation determinism**: Spreading activation results depend on graph structure and iteration count. Different graphs or iteration limits produce different activation rankings.
- **Community detection**: Uses label propagation with a random seed. Results may vary across runs for graphs with ambiguous community structure.

## 9. Reference

### API Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `mem.analyze.shortest_path(src, tgt, weighted=True)` | `list[str] \| None` | Node labels along the shortest path, or `None` if unreachable |
| `mem.find_paths(src, tgt, max_paths=10)` | `list[list[str]]` | All simple paths between two nodes |
| `mem.shortest_path_lengths(weighted=True)` | `dict[str, dict[str, float]]` | All-pairs distance matrix |
| `mem.analyze.distances(src, weighted=True)` | `dict[str, float]` | Distances from one node to all reachable nodes |
| `mem.analyze.components()` | `list[set[str]]` | All connected components as label sets |
| `mem.analyze.is_connected()` | `bool` | Whether the graph has exactly one component |
| `mem.analyze.largest_component()` | `set[str]` | Nodes in the largest component |
| `mem.analyze.component_of(concept)` | `set[str]` | Component containing the given concept |
| `mem.analyze.describe().density` | `float` | Edge-to-maximum-possible-edge ratio |
| `mem.unique_edge_sizes()` | `list[int]` | Distinct node counts across all edges |
| `mem.max_edge_order()` | `int` | Largest edge size minus 1 |
| `mem.recall(concept, depth=N)` | `list[Hypernode]` | BFS-like traversal up to N hops |
| `mem.link_hyper(sources, targets, label, weight)` | `Hyperedge` | Create an N-ary directed hyperedge |
| `mem.reason(seeds, depth)` | `ReasoningResult` | Apply inference rules to discover new edges |
| `mem.add_rules(*rules)` | `None` | Register inference rules for reasoning |
| `mem.search.activate(concept, energy)` | `list[ActivationHit]` | Inject energy into a node for activation |
| `mem.search.diffuse(concept, iterations)` | `list[ActivationHit]` | Spread activation energy through the graph |
| `mem.clear_activations()` | `None` | Reset all node activations to zero |
| `mem.capture_version()` | `dict` | Snapshot current graph state (version_id, node_count, edge_count) |
| `mem.diff_from_version(version_id)` | `VersionDelta \| None` | Compute changes since a captured version |
| `mem.evolve()` | `EvolveResult` | Run decay, prune, and merge on the graph |
| `mem.analyze.communities(seed)` | `CommunityResult` | Detect communities via label propagation |
| `mem.edges_labeled(edge_label)` | `list[Hyperedge]` | Retrieve all edges with a given label |
