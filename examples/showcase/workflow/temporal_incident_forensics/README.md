# Temporal Incident Forensics

> Production deployment incident forensics using temporal event registration, Allen interval relations, causal chain detection, and infrastructure impact analysis on a 20-node temporal-infrastructure graph.

## 1. The Approach

A production incident is both a structural event (which components are affected) and a temporal event (when things happen and in what order). This example models a SaaS deployment incident as a dual graph: an infrastructure dependency graph showing component relationships, and a temporal event graph showing the incident timeline. The temporal subsystem uses Allen interval algebra to analyze event ordering and auto-detect causal chains.

This is the first Hyper3 example demonstrating the temporal subsystem: `add_temporal_event`, `allen_relation`, `detect_temporal_causal_chains`, `infer_temporal_constraints`, and `check_temporal_constraint_consistency`.

## 2. Key Concepts

| Term | What it does |
|------|-------------|
| **Temporal event** | An event with start/end times and metadata |
| **Allen interval relation** | One of 13 possible relationships between two time intervals (before, after, overlaps, contains, meets, etc.) |
| **Causal chain** | A sequence of temporally-ordered events connected by graph edges |
| **Temporal constraint** | An inferred Allen relation between two events |
| **Constraint consistency** | Checking the inferred constraint network for contradictions |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/workflow/temporal_incident_forensics/temporal_incident_forensics.py
```

## 4. The Scenario

A routine deployment of config-service:v2.3 pushes a stale configuration (max_connections=50 instead of 500). Over the next 10 minutes, the connection pool fills, API latency spikes, customers experience timeouts, and the incident response team intervenes with a rollback.

### Timeline (11 events, T+0 to T+12 minutes)

| Time | Event | Duration |
|------|-------|----------|
| T+0.0 | routine_deploy_v2_3 | 0.5m |
| T+0.3 | stale_config_pushed | 0.5m |
| T+2.0 | db_pool_growth_begins | 12.0m |
| T+4.0 | api_latency_increase | 12.0m |
| T+5.5 | customer_timeouts | 11.5m |
| T+6.0 | pager_alert_fired | 0.2m |
| T+7.0 | incident_declared | 0.1m |
| T+8.0 | rollback_initiated | 0.3m |
| T+8.5 | pool_draining | 2.5m |
| T+10.0 | service_restored | 0.5m |
| T+12.0 | post_mortem_scheduled | 0.2m |

### Infrastructure Graph (9 components, 12 dependencies)

Components: api_gateway, auth_service, order_service, payment_service, connection_pool, postgres, redis, load_balancer, config_service.

The knowledge graph ultimately contains 20 nodes (9 infrastructure + 11 temporal events) because temporal events are registered as graph nodes. Infrastructure-only queries filter by node data. The 12 dependency edges connect infrastructure components; temporal events are linked separately via `timeline_link` edges.

```mermaid
graph TB
    LB[load_balancer] -->|routes_to| API[api_gateway]
    CFG[config_service] -->|configures| API
    CFG -->|configures| CP[connection_pool]
    API -->|routes_to| AUTH[auth_service]
    API -->|routes_to| ORD[order_service]
    API -->|routes_to| PAY[payment_service]
    AUTH -->|uses| CP
    ORD -->|uses| CP
    ORD -->|uses| REDIS[redis]
    PAY -->|writes_to| PG[postgres]
    AUTH -->|reads_from| REDIS
    CP -->|connects_to| PG
```

## 5. Analysis Pipeline

### Section 1: Infrastructure Graph Construction
Creates 9 infrastructure nodes and 12 dependency edges. The dependency graph enables impact propagation analysis.

### Section 2: Incident Timeline Registration
11 temporal events are registered with precise start/end times and metadata (metric names, thresholds, severity levels).

### Section 3: Allen Interval Analysis
Computes Allen interval relations between key event pairs:
- `routine_deploy` -> `stale_config_pushed`: **overlaps** (deploy still running when bad config pushed)
- `stale_config` -> `db_pool_growth`: **before** (config error precedes pool growth)
- `db_pool_growth` -> `api_latency`: **overlaps** (pool growth overlaps with latency impact)
- `rollback` -> `service_restored`: **before** (rollback precedes restoration)

The "overlaps" relation is the most informative: it indicates concurrent degrading conditions.

### Section 4: Automatic Causal Chain Detection
After linking temporal events via `timeline_link` edges, the system detects 109 causal chains. The most relevant chains trace the full incident lifecycle: `routine_deploy -> rollback_initiated -> service_restored -> post_mortem_scheduled`.

### Section 5: Temporal Constraint Consistency
55 temporal constraints are inferred between all event pairs. No consistency violations are found, confirming the timeline is internally consistent.

### Section 6: Infrastructure Impact Analysis
Shortest path from config_service to payment_service reveals the impact propagation route: `config_service -> api_gateway -> payment_service`. Betweenness centrality identifies api_gateway as the primary bottleneck (0.0292).

## 6. Key Metrics

| Metric | Value |
|--------|-------|
| Infrastructure nodes | 9 |
| Infrastructure edges | 12 |
| Temporal events | 11 |
| Allen relations analyzed | 7 pairs |
| Causal chains detected | 109 |
| Temporal constraints | 55 |
| Consistency violations | 0 |

## 7. What Makes This Different

**Allen interval algebra** provides a precise vocabulary for temporal relationships that goes beyond simple "before/after" timestamps. The 13 relations capture nuances like "overlaps" (both events active simultaneously) and "meets" (one ends exactly when the other begins) that reveal incident dynamics.

**Automatic causal chain detection** reconstructs the incident narrative from temporal data without manual timeline construction. Given the event registrations and graph edges, the system identifies all possible causal sequences.

**Infrastructure-temporal integration** bridges structural analysis (which components are affected) with temporal analysis (when they were affected), enabling forensic reconstruction of how a single config error cascaded through the system.

## 8. Code Implementation

```python
from hyper3 import HypergraphMemory, TransitiveRule

mem = HypergraphMemory(evolve_interval=0)

# Build infrastructure graph
mem.add("api_gateway", data={"tier": "edge", "team": "platform"})
mem.link("config_service", "connection_pool", label="configures", weight=3.0)

# Register temporal events with intervals and metadata
mem.add_temporal_event("deploy", start=0.0, end=0.5,
                       deployer="ci_cd", artifact="config-service:v2.3")
mem.add_temporal_event("outage", start=2.0, end=10.0)

# Compute Allen relation between two events
relation = mem.allen_relation("deploy", "outage")
print(relation.value)  # "before"

# Link events to enable causal chain detection
mem.link("deploy", "stale_config_pushed", label="timeline_link", weight=3.0)
mem.link("stale_config_pushed", "db_pool_growth_begins", label="timeline_link", weight=3.0)

# Detect causal chains through temporal + graph structure
chains = mem.temporal.detect_causal_chains(min_chain_length=3)
print(f"Found {len(chains)} chains")

# Check temporal consistency
constraints = mem.temporal.infer_temporal_constraints()
issues = mem.temporal.check_constraint_consistency()

# Infrastructure impact analysis
path = mem.analyze.shortest_path("config_service", "payment_service", weighted=True)
centrality = mem.analyze.centrality("betweenness", top_k=5)
```

## 9. Real-World Gap

- **Manual event registration.** Events are registered programmatically. A production system would ingest events from monitoring systems (Prometheus, Datadog) and incident management tools (PagerDuty, Jira).
- **Fixed time intervals.** Real incident timestamps are imprecise. The system assumes exact start/end times.
- **No probabilistic ordering.** Allen relations are deterministic. Real forensic analysis requires probabilistic ordering when timestamps are uncertain.
- **Causal chains are topological.** The detected chains are based on temporal ordering and graph connectivity, not proven causation. Correlation is not causation.

## 10. Reference

### API Methods

| Method | Purpose |
|--------|---------|
| `mem.add_temporal_event(label, start, end, **metadata)` | Register a temporal event with time interval |
| `mem.allen_relation(source, target)` | Compute Allen interval relation between two events |
| `mem.detect_temporal_causal_chains(min_chain_length)` | Auto-detect causal chains from temporal+graph structure |
| `mem.infer_temporal_constraints()` | Infer Allen constraints between all event pairs |
| `mem.check_temporal_constraint_consistency()` | Check constraint network for contradictions |
| `mem.list_temporal_events()` | List all registered temporal events |

### Related Examples

| Example | Topic |
|---------|-------|
| `examples/showcase/domain/infrastructure_self_healing/` | Feedback-driven infrastructure evolution |
| `examples/showcase/belief/quantum_diagnostics/` | Hypothesis management during incidents |
