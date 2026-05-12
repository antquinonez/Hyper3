# Centrality and Ranking

> Three scripts demonstrating degree, betweenness, PageRank, and Katz centrality on small graphs, plus structural statistics, anomaly detection, community detection, evolution, and abstraction.

## 1. The Approach

Different centrality measures answer different questions about node importance:

- **Degree centrality** asks "who has the most connections?" — a local measure of activity.
- **Betweenness centrality** asks "who sits on the most shortest paths?" — a structural measure of control over information flow.
- **PageRank** asks "who is connected to other important nodes?" — a recursive measure that propagates influence through the graph.
- **Katz centrality** asks "who is reachable via short paths?" — attenuates influence by path length, useful when the graph has structural bottlenecks.

No single measure captures all aspects of importance. A node with high degree may have low betweenness if its connections are peripheral. A node with low degree may have high betweenness if it bridges two clusters. These three scripts demonstrate each measure in isolation and then compare them side-by-side to show where they agree and diverge, then use structural anomaly detection and community detection to explain the patterns.

## 2. Key Concepts

| Concept | What it measures | When to use it |
|---------|-----------------|----------------|
| Degree centrality | Fraction of nodes a node connects to (normalized by n-1) | Identifying highly-connected hubs |
| Betweenness centrality | Fraction of shortest paths passing through a node | Finding bottlenecks and bridges |
| PageRank | Steady-state probability of a random walk with restart | Ranking nodes by propagated influence |
| Katz centrality | Weighted sum of paths from a node, attenuated by length | Capturing reachability when PageRank is too diffuse |
| Weighted centrality | Same measures using edge weights as transition probabilities | When edge importance varies (strong vs weak ties) |
| `describe()` | One-call structural summary (counts, degrees, density, types) | Quick sanity check on graph structure |
| Structural anomaly detection | Classifies nodes as low_risk, boundary, or anomalous based on graph structure | Finding cyclic dependencies and structural outliers |
| Community detection | Groups nodes by connectivity patterns using modularity optimization | Discovering clusters and subgroups |
| Evolution | Decays, prunes, merges, and reinforces graph structure | Maintaining graph health over time |
| Abstraction (`collapse_subgraph`) | Replaces a set of nodes with a single summary node | Creating higher-level views of complex subgraphs |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/core/centrality_and_ranking/centrality_and_pagerank.py
.venv/bin/python examples/showcase/core/centrality_and_ranking/centrality_comparison.py
.venv/bin/python examples/showcase/core/centrality_and_ranking/graph_statistics.py
```

**Script 1 output** (10-node org chart, centrality + anomaly detection + community detection):

```
nodes: 10, edges: 15

  concept  deg_centrality
---------------------------
    alice          0.5556
      bob          0.5556
    carol          0.4444
     iris          0.4444

  concept   pagerank
----------------------
    frank   0.105286
      bob   0.103567
    carol   0.103499

pagerank sum (should be ~1.0): 1.000000

alice:
  anomaly status: anomalous
  boundary score: 0.3233
iris:
  anomaly status: anomalous
  boundary score: 0.3067

communities detected: 1
modularity: 0.0000
coverage: 1.0000
```

**Script 2 output** (8-node hub-and-chain, four centrality measures + anomalies + communities):

```
nodes: 8, edges: 11

--- Top node by each measure ---
        degree: hub (0.714286)
   betweenness: hub (0.500000)
      pagerank: d (0.127752)
          katz: hub (0.378416)

all measures agree on top node: False

hub:
  anomaly status: anomalous
  boundary score: 0.4543

communities detected: 2
modularity: 0.2149
  community 0: ['a', 'b', 'c', 'd', 'hub'] (5 nodes)
  community 1: ['e', 'f', 'g'] (3 nodes)
```

**Script 3 output** (7-node project graph, statistics + evolution + abstraction):

```
nodes: 7
edges: 13
degree min=2, max=6, mean=3.86, median=3.0
components: 1
density: 0.3095

before evolution:
  nodes: 7, edges: 13, density: 0.3095
after evolution:
  nodes: 6, edges: 13, density: 0.4333
  nodes merged: 1

collapsed eng_team from {alice, bob, dave}
  summary label: eng_team
  edges collapsed: 3
  external connections: 1

after collapse:
  nodes: 6, edges: 3, density: 0.1000
```

## 4. Script Walkthroughs

### 4a. Centrality and PageRank (`centrality_and_pagerank.py`)

Builds a 10-node, 15-edge org chart with weighted directed edges and one 3-to-3 hyperedge (`project_team`).

**Degree centrality** ranks alice and bob tied at 0.5556 — both connect to 5 of 9 other nodes. This reflects their roles: alice manages bob and carol, and bob collaborates widely.

**Betweenness centrality** ranks iris highest at 0.3819 — iris connects the product team to engineering via her collaborations with eve and grace, and coordinates back to alice. Despite having the same degree as carol (0.4444), iris has 6x higher betweenness than carol (0.0625). The difference: iris sits on paths between otherwise disconnected subgroups, while carol's connections are more local.

**PageRank** ranks frank highest at 0.105286, even though frank's degree (0.3333) is lower than alice's (0.5556). Why this matters: PageRank counts the importance of neighbors, not just their count. Frank receives connections from carol and henry, both of whom are themselves well-connected, and the `project_team` hyperedge routes flow through frank's neighborhood.

**Weighted vs unweighted PageRank**: The weighted top-3 (frank, bob, carol) differs from the unweighted top-3 (iris, grace, frank). Edge weights change which paths the random walk prefers, shifting influence toward nodes connected by strong edges.

**Structural anomaly detection** identifies alice, iris, and bob as anomalous (boundary scores 0.3233, 0.3067, 0.3233) due to cyclic dependency structures — alice manages bob, jack collaborates with bob, and iris coordinates back to alice, forming cycles. Eve, on the other hand, is classified as low_risk (0.2900) because her connections are acyclic.

**Community detection** finds a single community covering all 10 nodes (modularity 0.0000, coverage 1.0000). The org chart is densely connected enough that no natural subgroup boundary exists — everyone is reachable from everyone else through short paths.

### 4b. Centrality Comparison (`centrality_comparison.py`)

Builds an 8-node, 11-edge network with a star-like hub and a peripheral chain (a-b-c-d-e-f-g-hub). Runs four centrality measures and checks agreement.

**Key finding**: The four measures disagree on the top node. Degree, betweenness, and Katz all pick `hub` (0.7143, 0.5000, 0.3784), but PageRank picks `d` (0.127752). Why this happens: `hub` has the most connections and sits on many paths, but PageRank's random-walk model spreads probability mass along the chain. Node `d` sits at the midpoint of the longest chain segment, accumulating steady-state probability from both directions.

**Pairwise agreement** is low — degree vs betweenness agrees on 0/8 positions, degree vs pagerank agrees on 0/8 positions. The highest agreement is degree vs katz and pagerank vs katz, each at 3/8. This illustrates why choosing the right centrality measure matters: they produce genuinely different rankings.

**Structural anomaly detection** classifies hub as anomalous (boundary score 0.4543) — its star topology creates an unusual concentration of connections. Node d is also anomalous (0.3182) due to its betweenness-bridging position. Node a is low_risk (0.2829) because it sits at the periphery with no structural surprises.

**Community detection** separates the graph into two communities: {a, b, c, d, hub} (5 nodes) and {e, f, g} (3 nodes), with modularity 0.2149. This split reflects the asymmetric topology: the hub anchors one community with its direct neighbors and the first half of the chain, while the far end of the chain forms its own group.

### 4c. Graph Statistics (`graph_statistics.py`)

Builds a 7-node, 13-edge graph with typed nodes (5 persons, 1 language, 1 project) and labeled edges, including one hyperedge (`team_of` connecting {alice, bob} to {project_x}).

**`describe()`** provides a one-call structural snapshot: 7 nodes, 13 edges, density 0.3095, single connected component, no isolated nodes, mean degree 3.86.

**Directional degree** reveals role asymmetry: `project_x` has in-degree 6 and out-degree 0 — everything flows into it, nothing flows out. `alice` has in-degree 0 and out-degree 5 — she initiates all her connections. Without direction, both would show degree 5 and 6 respectively, losing this role information.

**Weighted degree** surfaces another distinction: alice (weighted 26.0) and bob (25.0) have nearly identical raw degree (5 and 5), but alice's weighted degree is slightly higher because her edges carry stronger weights (5.0 on `leads` and `uses`, vs bob's mix of 4.0 and 2.0 edges).

**Edge statistics**: The graph has edges of size 2 and 3 (the `team_of` hyperedge), giving max edge order 2. The degree distribution (1 node at degree 2, 3 at degree 3, 2 at degree 5, 1 at degree 6) shows a right-skewed pattern with `project_x` as the high-degree outlier.

**Evolution impact**: After stimulating alice, bob, and project_x, spreading activation, running Hebbian reinforcement, and evolving, the graph merges 1 node (alice and eve have identical neighbor patterns through project_x and python). The result: 6 nodes, density increases from 0.3095 to 0.4333, degree range shifts to 2-8 with mean 4.17. Evolution reduces redundancy while preserving connectivity.

**Abstraction**: On a separate 5-node graph, `collapse_subgraph` replaces {alice, bob, dave} with a single `eng_team` summary node. The collapse eliminates 3 internal edges and creates 1 external connection (eng_team → project_x), reducing the graph from 5 nodes/6 edges/density 0.3000 to 6 nodes/3 edges/density 0.1000 (the 6th node is the summary node itself alongside carol and project_x). `list_summaries()` confirms 1 active summary mapping eng_team to its detail nodes.

## 5. Key Metrics

| Metric | Script 1 | Script 2 | Script 3 |
|--------|----------|----------|----------|
| Nodes | 10 | 8 | 7 |
| Edges | 15 | 11 | 13 |
| Density | — | — | 0.3095 |
| Components | — | — | 1 |
| Highest degree | alice, bob (0.5556) | hub (0.7143) | project_x (6) |
| Highest betweenness | iris (0.3819) | hub (0.5000) | — |
| Highest PageRank | frank (0.105286) | d (0.127752) | — |
| Highest Katz | — | hub (0.378416) | — |
| PageRank sum | 1.000000 | — | — |
| Top-3 agree across measures | No | No | — |
| Degree vs betweenness agreement | — | 0/8 | — |
| Degree vs PageRank agreement | — | 0/8 | — |
| Max edge order | — | — | 2 |
| Anomaly: alice | anomalous (0.3233) | — | — |
| Anomaly: iris | anomalous (0.3067) | — | — |
| Anomaly: bob | anomalous (0.3233) | — | — |
| Anomaly: eve | low_risk (0.2900) | — | — |
| Anomaly: hub | — | anomalous (0.4543) | — |
| Anomaly: d | — | anomalous (0.3182) | — |
| Anomaly: a | — | low_risk (0.2829) | — |
| Communities | 1 (modularity 0.0000) | 2 (modularity 0.2149) | — |
| Evolution: nodes merged | — | — | 1 |
| Evolution: density before/after | — | — | 0.3095 → 0.4333 |
| Collapse: edges collapsed | — | — | 3 |
| Collapse: external connections | — | — | 1 |

## 6. What Makes This Different

**Different measures rank nodes differently, and understanding why is the key insight.** In Script 1, alice has the highest degree but the 4th-lowest betweenness — her connections are local to her direct reports, not bridging distant parts of the graph. In Script 2, hub dominates degree, betweenness, and Katz but loses PageRank to d because the random walk spends time traversing the chain rather than bouncing off the hub.

**Edge weights shift rankings.** Script 1 shows that weighted and unweighted PageRank produce different top-3 lists (frank/bob/carol vs iris/grace/frank). When edge importance varies, the unweighted view can be misleading.

**Directional degree separates source and sink roles.** Script 3 shows that `project_x` (in-degree 6, out-degree 0) and `alice` (in-degree 0, out-degree 5) play structurally opposite roles. Undirected degree conflates these into single numbers (6 and 5), losing the direction information.

**Structural statistics provide a first-pass sanity check.** `describe()` gives node counts, density, degree range, and component count in one call — enough to verify the graph was built correctly before running more expensive centrality computations.

**Anomaly detection surfaces structural patterns that centrality alone misses.** Script 1 flags alice, iris, and bob as anomalous due to cyclic dependencies — a pattern invisible to degree or PageRank. Script 2 flags hub as the most anomalous node (0.4543), confirming that its star topology is structurally unusual.

**Community detection reveals subgroups that explain centrality disagreement.** In Script 2, the two communities ({a, b, c, d, hub} and {e, f, g}) explain why PageRank favors d — d sits at the boundary between the hub-centric community and the chain community, accumulating flow from both.

**Evolution compresses graphs while preserving connectivity.** Script 3 shows evolution merging one node and increasing density from 0.3095 to 0.4333, demonstrating that structural maintenance reduces redundancy without losing information.

**Abstraction creates multi-level views.** `collapse_subgraph` replaces 3 engineering nodes with a single `eng_team` summary, reducing edge count from 6 to 3. This enables analysis at different granularity levels without modifying the underlying graph.

## 7. Code Implementation

**Degree, betweenness, and PageRank:**

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
mem.add("alice", data={"role": "lead"})
mem.link("alice", "bob", label="manages", weight=5.0)

deg = mem.analyze.centrality("degree", )
betw = mem.analyze.centrality("betweenness", )
pr = mem.pagerank(alpha=0.85, weighted=True, top_k=3)
```

**Four-way centrality comparison:**

```python
deg = mem.analyze.centrality("degree", )
betw = mem.analyze.centrality("betweenness", )
pr = mem.pagerank(alpha=0.85)
katz = mem.katz_centrality(alpha=0.1)
```

**Structural anomaly detection:**

```python
anomaly = mem.analyze.anomalies("alice")
print(f"status: {anomaly.anomaly_status}, score: {anomaly.boundary_score:.4f}")
```

**Community detection:**

```python
comm = mem.analyze.communities(seed=42)
print(f"communities: {comm.community_count}, modularity: {comm.modularity:.4f}")
for community in comm.communities:
    print(f"  {sorted(community.member_labels)} ({community.size} nodes)")
```

**Structural statistics:**

```python
desc = mem.describe()
print(f"nodes: {desc.node_count}, density: {desc.density:.4f}")
print(f"degree range: {desc.degree_min}-{desc.degree_max}, mean: {desc.degree_mean:.2f}")

deg = mem.degree()
deg_w = mem.degree(weighted=True)
in_deg = mem.in_degree()
out_deg = mem.out_degree()
print(f"density: {mem.density():.4f}")
print(f"max edge order: {mem.max_edge_order()}")
```

**Evolution:**

```python
mem.activate("alice", energy=1.0)
mem.activate(iterations=2)
mem.hebbian_reinforce()
result = mem.evolve()
print(f"decayed: {result.decayed}, pruned: {result.pruned}, merged: {result.merged}")
```

**Abstraction:**

```python
summary = mem.collapse_subgraph(
    {"alice", "bob", "dave"},
    summary_label="eng_team",
    summary_data={"type": "team", "dept": "eng"},
)
print(f"edges collapsed: {summary.edges_collapsed}")
print(f"external connections: {summary.external_connections}")

for s in mem.list_summaries():
    print(f"{s.summary_label} -> {sorted(s.detail_labels)}")
```

## 8. Real-World Gap

- **Scale**: These scripts run on 5-10 nodes. Centrality algorithms (especially betweenness, which is O(nm)) slow down on graphs with thousands of nodes. The `max_samples` parameter on `betweenness_centrality` enables approximation for larger graphs.
- **Edge semantics**: The scripts use generic labels (`collaborates`, `connects`). Real graphs have heterogeneous edge types with domain-specific meaning that affects interpretation of centrality scores.
- **Temporal dynamics**: These centrality scores are point-in-time snapshots. In practice, centrality evolves as the graph changes, and tracking it over time requires recomputation or incremental algorithms.
- **Weight calibration**: The scripts assign integer weights manually. Production use requires deriving weights from interaction frequency, recency, or domain-specific metrics.
- **Community detection resolution**: Script 1 finds a single community because the org chart is densely connected. Real graphs often have clearer community structure, and resolution parameters may need tuning.
- **Evolution parameters**: The scripts use default decay and merge thresholds. Production use requires tuning these to the domain — aggressive decay can lose important low-activity nodes, while conservative settings allow redundancy to accumulate.

## 9. Reference

| Method | Returns | Description |
|--------|---------|-------------|
| `mem.analyze.centrality("degree", )` | `dict[str, float]` | Normalized degree (degree / n-1) for each node |
| `mem.analyze.centrality("betweenness", )` | `dict[str, float]` | Normalized betweenness centrality |
| `mem.pagerank(alpha, weighted, top_k)` | `dict[str, float]` | Hypergraph PageRank with damping factor |
| `mem.katz_centrality(alpha)` | `dict[str, float]` | Katz centrality with attenuation parameter |
| `mem.describe()` | `DescribeResult` | Structural summary (nodes, edges, density, degrees, types) |
| `mem.degree(weighted)` | `dict[str, int\|float]` | Raw or weighted degree per node |
| `mem.in_degree()` | `dict[str, int]` | Incoming edge count per node |
| `mem.out_degree()` | `dict[str, int]` | Outgoing edge count per node |
| `mem.density()` | `float` | Edge density of the graph |
| `mem.unique_edge_sizes()` | `list[int]` | Distinct edge cardinalities present |
| `mem.max_edge_order()` | `int` | Largest edge order (size - 1) |
| `mem.degree_distribution()` | `dict[int, int]` | Histogram: degree value to node count |
| `mem.analyze.anomalies(concept)` | `ExplorationReport` | Anomaly status, boundary score, structural insights |
| `mem.analyze.communities(seed)` | `CommunityResult` | Communities, modularity, coverage, member labels |
| `mem.evolve()` | `EvolveResult` | Decayed edges, pruned nodes, merged nodes |
| `mem.activate(concept, energy)` | `None` | Injects activation energy into a node |
| `mem.activate(iterations)` | `None` | Propagates activation across edges |
| `mem.hebbian_reinforce()` | `None` | Strengthens edges between co-activated nodes |
| `mem.collapse_subgraph(nodes, summary_label, summary_data)` | `CollapseResult` | Replaces nodes with summary, returns mapping and edge changes |
| `mem.list_summaries()` | `list[SummaryMapping]` | Active summary-to-detail mappings |
