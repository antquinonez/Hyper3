# Microservices Dependency Reasoning Showcase

> Infer hidden transitive dependencies and blast radius from an 82-node service graph.

**What you will learn:**

- How to build a labeled dependency graph from microservice metadata and relationship edges
- Why direct dependency maps undercount blast radius and how transitive inference closes the gap
- How to rank infrastructure nodes by betweenness centrality to surface single points of failure
- How TransitiveRule discovers hidden A->B->C chains and InverseRule flips direction for impact analysis
- How to simulate outage scenarios and quantify affected teams, regions, and criticality buckets
- How to use EfficiencyTracker to measure latency of reasoning, centrality, and retrieval operations
- How per-branch overlay deduplication collapses duplicate inferences across multiway branches

## 1. What this example demonstrates

At 3 AM the pager goes off for a database outage. The on-call engineer needs to know the blast radius — not just the services that directly connect to that database, but every service transitively affected through the dependency chain — and needs it now. This script models that scenario on a realistic 82-node microservices environment and answers the incident-response questions that direct dependency maps miss:

- direct vs transitive dependency exposure
- full blast radius per infra node (DB/queue/cache)
- single points of failure (betweenness centrality)
- longest dependency chains (fragile paths)
- outage scenario summaries with teams/regions affected

## 2. Run

```bash
.venv/bin/python examples/showcase/domain/microservices_reasoning/reasoning_walkthrough.py
```

## 3. Current validated metrics

From current runtime:

- Nodes: 82
  - 53 microservices
  - 17 infrastructure nodes
  - 12 external services
- Initial edges: 236
- After reasoning: 248 edges (12 unique inferred from 300 raw productions)

Inference configuration:

- `TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on")`
- `InverseRule(edge_label="depends_on", inverse_label="depended_on_by")`

Reasoning run:

- states explored: 301
- rules applied: 300
- raw edges produced: 300 (across all multiway branches)
- unique edges after dedup: 12

The 300-to-12 deduplication ratio (96% duplicates) occurs because the multiway engine explores branches independently with per-branch overlays. Many branches independently discover the same transitive chains through the shared `depends_on` network. After overlay collection, only the unique (source, target, label) triples are committed to the graph.

## 4. Walkthrough

### Section 1-2: Graph construction

Creates domain services, infrastructure, external providers, and relationship edges (`depends_on`, `reads_from`, `writes_to`, `publishes_to`, `subscribes_to`, `routes_to`, etc.).

### Section 3: Direct dependency baseline

Builds a map from infra node -> direct dependent services. This establishes the "tip of iceberg" baseline.

### Section 4-5: Rule-based expansion

Registers reasoning rules and runs expansion over all node labels. This discovers hidden `indirectly_depends_on` paths.

### Section 6: Blast radius

For each DB/queue, computes:

- direct dependents
- transitive dependents (newly inferred)
- total blast radius

Typical results (specific transitive dependents vary across runs):

- `db-pg-orders`: 11 direct + 0 indirect = 11 total
- `queue-kafka-events`: 13 direct + 0 indirect = 13 total
- `db-pg-payments`: 6 direct + 1 indirect = 7 total

Note: which specific transitive dependents are discovered is non-deterministic. The 12 unique inferred edges are the same set each run, but which edges map to `indirectly_depends_on` vs `depended_on_by` can vary. Most infra nodes show 0 transitive dependents because the 12 unique edges are distributed across the graph and only a few target infrastructure nodes.

### Section 7: SPOF ranking

Betweenness centrality surfaces bridge nodes. Top entries typically include:

- `svc-order-api` (~0.022)
- `svc-pay-processor` (~0.013)
- `svc-analytics-ingest` (~0.012)
- `svc-auth-gateway` (~0.010)

### Section 8: Critical chains

Finds longest dependency chains. Longest chains are typically 8 hops.

### Section 9: Outage scenarios

Simulates infra outages and reports:

- direct vs indirect impact counts
- total impacted services
- criticality buckets
- affected teams and regions

### Section 10: Operation efficiency report

Tracks latency of key operations using `EfficiencyTracker`:

- Wraps `reason()`, `betweenness_centrality`, `query_nodes`, and `activate` with `tracker.track()`
- Reports per-operation statistics: count, avg, P50, P95, max duration
- Shows cache hit/miss ratios and degradation detection

Typical output shows reasoning as the slowest operation (single invocation, ~550ms for 82-node graph), while centrality and search operations complete in under 10ms.

### Expected Output

Key blast radius lines from a typical run:

```
  db-pg-orders
    Direct dependents:    11
    Transitive dependents: 0 (discovered by inference)
    Total blast radius:   11

  queue-kafka-events
    Direct dependents:    13
    Transitive dependents: 0 (discovered by inference)
    Total blast radius:   13

  db-pg-payments
    Direct dependents:    6
    Transitive dependents: 1 (discovered by inference)
    Total blast radius:   7
```

## 5. Mermaid (representative subgraph)

```mermaid
graph LR
    GW[1) svc-gateway-main] -->|depends_on| RATE[svc-rate-limiter]
    RATE -->|depends_on| REDIS[cache-redis-general]

    ORD[2) svc-order-api] -->|depends_on| AUTH[svc-auth-gateway]
    AUTH -->|depends_on| AUTHCACHE[cache-redis-auth]
    ORD -->|depends_on| DBORD[db-pg-orders]

    PAY[3) svc-pay-processor] -->|depends_on| DBPAY[db-pg-payments]
    PAY -->|depends_on| KAFKA[queue-kafka-events]
```

This is a simplified slice; the real graph is much denser.

How to read it:

- Numbered nodes call out the three most operationally significant roles: **1)** `svc-gateway-main` is the entry gateway that all external traffic flows through; **2)** `svc-order-api` is the order service with the widest dependency fan-out; **3)** `svc-pay-processor` is the payment service where failures have direct revenue impact.
- Start at entry services (`svc-gateway-main`, `svc-pay-processor`) and walk downstream to infra nodes.
- Any path ending at an infra node contributes to that node's blast radius. Blast radius propagates through the chain: `svc-order-api` depends on `svc-auth-gateway`, which depends on `cache-redis-auth` — so the order service is in the auth cache's blast radius even though it has no direct connection to it.
- Transitive inference effectively adds implied long-range dependencies (for example, gateway-level services depending on deep infra through intermediary services).

## 6. How To Use the Results Operationally

- Treat direct dependencies as incident starting scope, then escalate to transitive blast radius for paging scope.
- Nodes with high betweenness are architecture fragility hotspots; prioritize hardening and redundancy there.
- Long dependency chains are rollback and deployment risk indicators, not just outage indicators.
- Compare outage scenarios by critical service counts, not only total counts.

### Blast Radius Interpretation

| Ratio (Total / Direct) | Meaning |
|------------------------|---------|
| 1.0-1.2 | Mostly direct dependencies — simple architecture |
| 1.2-1.5 | Moderate chaining — some transitive dependencies |
| 1.5+ | Significant transitive chains — hidden dependencies |

### Betweenness Centrality Interpretation

| Centrality Range | Meaning |
|------------------|---------|
| 0.20+ | Critical shared dependency — high risk |
| 0.08-0.20 | Important hub — moderate risk |
| 0.03-0.08 | Moderate connector — lower risk |
| < 0.03 | Peripheral node — minimal risk |

### Critical Path Interpretation

| Chain Length | Meaning |
|--------------|---------|
| 1-3 hops | Short, resilient path |
| 4-6 hops | Moderate fragility |
| 7+ hops | Highly fragile — failure at any point cascades |

## 7. Key Concepts

| Term | Semantic Definition |
|------|-------------------|
| **Microservice** | A domain-scoped service with port, team, criticality |
| **Infrastructure Node** | Database, cache, queue, proxy, service discovery |
| **TransitiveRule** | Discovers A->B->C chains as A->C indirect dependencies |
| **InverseRule** | Reverses edge direction for impact analysis |
| **Blast Radius** | All services affected by an infrastructure failure |
| **Betweenness Centrality** | Measure of how many paths pass through a node |
| **Critical Path** | Longest dependency chain from service to infrastructure |
| **Per-Branch Overlay** | Each multiway state gets its own overlay for branch isolation |
| **Overlay Deduplication** | Same logical edge from multiple branches appears only once after commit |

## 8. API Methods

| Method | Purpose |
|--------|---------|
| `mem.add(label, data, modalities)` | Create a node with metadata |
| `mem.link(source, target, label)` | Create a semantic edge |
| `mem.reason.add_rules(*rules)` | Register inference rules |
| `mem.reason(seeds, max_depth)` | Run multiway expansion with rules |
| `mem.analyze.centrality("betweenness")` | Compute centrality scores |
| `mem.query_nodes(data=...)` | Find nodes matching data attributes |
| `mem.pattern_match(edge_label)` | Find edges by label |
| `mem.stats()` | Get graph statistics |
| `mem.size` | Tuple of (node_count, edge_count) |
| `top_k(scores, k=N)` | Get top N items from a score dict |
| `EfficiencyTracker()` | Track operation latency and cache efficiency |
| `tracker.track(OperationType, metadata)` | Context manager to time an operation |
| `tracker.get_report()` | Full efficiency report with percentiles |

## 9. Related Examples

| Example | Focus |
|---------|-------|
| `examples/showcase/domain/threat_intelligence/knowledge_basics.py` | Threat intel graph with pattern matching, centrality |
| `examples/showcase/core/network_analytics/graph_analytics.py` | Centrality, cycles, components, risk scoring |
| `examples/showcase/domain/code_dependency_analysis/code_dependency_analysis.py` | Software architecture dependency analysis |

## 10. Real-world integration gap

This remains a synthetic snapshot. Production requires upstream graph feeding from:

- service mesh and tracing telemetry
- infra discovery metadata
- deployment/change streams
- health and incident systems

The blast radius analysis here is limited by the per-branch overlay deduplication: with 300 raw productions across multiway branches, only 12 unique transitive chains survive dedup. In a production system, the `indirectly_depends_on` edges would be computed once via a dedicated transitive closure algorithm (not through multiway expansion), producing the full set of unique transitive dependencies. The multiway approach here demonstrates the concept but is not the most efficient method for computing a complete transitive closure.

Hyper3 solves the reasoning layer; observability ingestion is a separate pipeline.
