# Microservices Dependency Reasoning Showcase

> Infer hidden transitive dependencies and blast radius from an 82-node service graph.

**What you will learn:**

- How to build a labeled dependency graph from microservice metadata and relationship edges
- Why direct dependency maps undercount blast radius and how transitive inference closes the gap
- How to rank infrastructure nodes by betweenness centrality to surface single points of failure
- How TransitiveRule discovers hidden A→B→C chains and InverseRule flips direction for impact analysis
- How to simulate outage scenarios and quantify affected teams, regions, and criticality buckets
- How to use EfficiencyTracker to measure latency of reasoning, centrality, and retrieval operations
- How to interpret blast-radius ratios and chain-length fragility for operational hardening decisions

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
- After reasoning: 536 edges (300 inferred)

Inference configuration:

- `TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on")`
- `InverseRule(edge_label="depends_on", inverse_label="depended_on_by")`

Reasoning run:

- states explored: 301
- rules applied: 300
- inferred edges: 300

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

Examples from current run:

- `db-pg-orders`: 11 direct + 4 indirect = 15 total
- `cache-redis-auth`: 7 direct + 6 indirect = 13 total
- `db-mongo-sessions`: 6 direct + 7 indirect = 13 total

### Section 7: SPOF ranking

Betweenness centrality surfaces bridge nodes. In current run, top entries include:

- `cache-redis-general`
- `svc-order-api`
- `queue-kafka-events`

### Section 8: Critical chains

Finds longest dependency chains. Current longest chains are 8 hops.

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

Typical output shows reasoning as the slowest operation (single invocation, ~300-400ms for 82-node graph), while centrality and search operations complete in under 100ms.

### Expected Output

Key blast radius lines from a typical run:

```
  db-pg-orders
    Direct dependents:    11
    Transitive dependents: 4 (discovered by inference)
    Total blast radius:   15
    Hidden: ['svc-analytics-dash', 'svc-analytics-reports', 'svc-gateway-admin', 'svc-order-history']

  cache-redis-auth
    Direct dependents:    7
    Transitive dependents: 6 (discovered by inference)
    Total blast radius:   13

  db-mongo-sessions
    Direct dependents:    6
    Transitive dependents: 7 (discovered by inference)
    Total blast radius:   13
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

Hyper3 solves the reasoning layer; observability ingestion is a separate pipeline.
