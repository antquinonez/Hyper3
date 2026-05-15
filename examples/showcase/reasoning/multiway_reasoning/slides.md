---
marp: true
mermaid: true
theme: default
paginate: true
backgroundColor: #fff
style: |
  section {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
  h1 {
    color: #2c3e50;
  }
  h2 {
    color: #34495e;
  }
  table {
    font-size: 0.9em;
  }
---

# Multiway Lateral Reasoning Showcase

**Exploring Alternative Incident Hypotheses with Multiway Expansion**

---

## 1. The Approach

When a cloud infrastructure health check fails, multiple root causes are possible:
- database failure
- network partition
- bad deployment
- cache stampede

**The Linear Bottleneck:** Traditional diagnostic logic forces agents to chase a single narrative sequence until it fails.

**The Hyper3 Approach:** Explore ALL hypotheses simultaneously through **multiway expansion**.

---

## 2. A Simple Analogy

Think of this like a doctor who simultaneously explores multiple possible diagnoses (flu, infection, allergy) rather than chasing one theory at a time.

Each "branch" of reasoning represents a different diagnosis, and Hyper3 compares them to find which best explains the symptoms.

---

## 3. Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **Multiway Expansion** | Exploring multiple "what if" scenarios at the same time |
| **State** | One possible version of the truth |
| **Leaf State** | A final conclusion after applying rules |
| **State Convergence** | Merging equivalent states from different paths |
| **Simultaneity Group** | Hypotheses at the same "depth" that can be compared directly |
| **Lateral Comparison** | Identifying differences between states in the same group |

---

## 4. Quick Start

Run the flagship showcase:

```bash
.venv/bin/python examples/showcase/reasoning/multiway_reasoning/multiway_lateral_insights.py
```

**What You'll See:** 66 leaf states (distinct terminal hypotheses) from a single failed health check. Note: the expansion report shows `branches=46` (pre-convergence terminals); the full leaf count of 66 is after the state convergence engine merges equivalents.

---

## 5. The Scenario & Topology

The example models a realistic, multi-region cloud infrastructure:

- **3 Geographic Regions:** `us-east`, `us-west`, `eu-west`
- **Service Mesh:** API, web, auth, cache, worker, orchestration layers
- **Shared Core:** PostgreSQL, RabbitMQ, Redis clusters
- **The Trigger:** Failed health check on `us-east-api`

```mermaid
graph TB
    subgraph "Traffic Layer"
        CDN["CDN Edge"]
        LB_G["Load Balancer Global"]
    end

    subgraph "us-east-1"
        LB_E["LB us-east"]
        API_E["API Service"]
        CACHE_E["Cache Replica"]
        DB_RE["DB Replica"]
    end

    subgraph "us-west-2"
        LB_W["LB us-west"]
        API_W["API Service"]
    end

    subgraph "Shared Infrastructure"
        DB["DB Primary PostgreSQL"]
        CACHE["Cache Primary Redis"]
    end

    CDN --> LB_G
    LB_G --> LB_E
    LB_G --> LB_W
    LB_E --> API_E
    API_E --> CACHE_E
    API_E --> DB_RE
    DB --> DB_RE
```

---

## 6. The Physics of Expansion

Ten inference rules operate simultaneously, creating a branching DAG of 66 leaf states (after convergence).

**10 Rules:**
- 5 Transitive (causes, depends_on, affects, indicates, routes_to)
- 4 Inverse (caused_by, depended_on_by, monitored_by, affected_by)
- 1 Abductive (possible_cause)

---

## How the Engine Works

Figure: The engine takes seed concepts and applies multiple inference rules simultaneously, creating a branching tree of hypotheses.

```mermaid
graph TD
    SEED["Seed Concepts: failed-health-check, latency-spike, db-primary-down..."]
    SEED --> MW{"Multiway Engine"}
    MW -->|"TransitiveRule"| B1["Branch: indirect chains"]
    MW -->|"InverseRule"| B2["Branch: reverse edges"]
    MW -->|"AbductiveRule"| B3["Branch: possible causes"]
    B1 --> LEAF["Leaf States: 66 total"]
    B2 --> LEAF
    B3 --> LEAF
    LEAF --> SCORE["Leaf Scoring vs Symptoms"]
```

---

## 7. Tied Top Hypotheses

Each leaf state is scored against 8 observed symptoms using a composite metric:

```
score = (edge_hits + symptom_overlap) / (total_symptoms + produced_edges + 1)
```

**The Discovery:** Multiple leaf states tie at score **0.800**. All are produced by `TransitiveRule(depends_on)` -- with `max_states=50`, the ~70 `depends_on` edges in the graph fill the state cap before other rules contribute.

**One illustrative chain:** `us-west-web` -[depends_on]-> `us-west-ratelimiter` -[depends_on]-> `cache-replica-eu-west` yields `us-west-web -[cascade_depends]-> cache-replica-eu-west`

**Key Insight:** The tied scores indicate multiple dependency chains explain the observed symptoms equally well. Increasing `max_states` to 200+ would allow other rules (causes, inverse, abductive) to contribute, producing genuinely diverse hypothesis branches.

---

## 8. State Convergence

**State convergence (automatic):** The engine merges structurally equivalent states. In this example, 20 states were merged, reducing redundancy in the state space.

**Cross-rule convergence:** Not applicable at `max_states=50` since only `TransitiveRule(depends_on)` produces matches. With a higher state budget, checking whether different rule types independently reach overlapping conclusions would be meaningful.

| Type | Result |
|------|--------|
| State convergence | 20 states merged |
| Cross-rule convergence | Not applicable (single rule type at this budget) |

---

## 9. Lateral Comparison

By comparing states within the same simultaneity group, the engine identifies structural differences.

**In this example**, manual lateral comparison across all 4 simultaneity groups produces no unique edges between states. All branches use `TransitiveRule(depends_on)` and activate the same seed nodes, so states within each group are structurally similar.

**With a higher state budget** (`max_states=200+`), multiple rule types would contribute, and lateral comparison would identify complementary explanations across rule families (e.g., `depends_on` chains vs. `causes` chains).

Note: `mem.lateral_insights(concept)` returns empty for the seed concepts in this example because it operates on the multiway state space, not on graph node labels directly. The showcase script performs manual comparison across simultaneity groups to demonstrate the concept.

---

## 10. Leaf Score Interpretation

| Score Range | Meaning |
|------------|---------|
| 0.9+ | Leaf explains most symptoms -- strong candidate |
| 0.7-0.9 | Leaf explains a subset -- partial match |
| 0.5-0.7 | Leaf touches some symptoms -- weak signal |
| < 0.5 | Leaf largely irrelevant |

---

## 11. Key Metrics

| Metric | Value |
|--------|-------|
| Graph nodes | 81 |
| Graph edges (initial) | 203 |
| Seed concepts | 16 |
| States created | 51 |
| Leaf states (post-convergence) | 66 |
| Inference edges produced | 50 |
| Causal invariants merged (state convergence) | 20 |
| Cross-rule convergent pairs | Not applicable (single rule type) |
| Manual lateral differences | 0 (all branches use same rule) |
| Best leaf score | 0.800 (tied, transitive(depends_on)) |
| Per-branch overlay edges | 90 total, 11 unique after dedup |

---

## 12. The Observability Gap

Hyper3 reasons once the semantic graph exists. The real-world challenge is the data engineering pipeline:

1. **Relationship Extraction:** Converting raw Terraform/K8s telemetry into semantic edges
2. **Causal Discovery:** Using Granger causality to separate true causation from correlation
3. **Ontology Mapping:** Normalizing disparate vendor labels into a canonical schema
4. **Knowledge Construction:** Building a federated pipeline to ingest real-time events

**The Pipeline:**
```
Terraform/K8s -> Entity Extraction -> Jaeger/Prometheus -> Relationship Inference ->
Causal Discovery -> Semantic Labeling -> Entity Resolution -> Hyper3 Graph
```

Hyper3 provides the **reasoning engine**; the data engineering pipeline that feeds it is a separate concern.

---

## 13. Key API Methods

| Method | Purpose |
|--------|---------|
| `mem.reason(seeds, depth, max_states)` | Run multiway expansion |
| `mem.lateral_insights(concept)` | Find knowledge transferable across branches |
| `mem.state_clustering.simultaneity_groups` | Get groups of states at the same depth |
| `result.clustering` | State clustering report from reasoning |
| `result.state_convergence` | Merge report from state convergence |
| `result.expansion` | Expansion statistics (states, rules, edges, branches) |

---

## Related Examples

| Example | Focus |
|---------|-------|
| `examples/showcase/workflow/self_evolving_cognition/` | Feedback-driven evolution |
| `examples/showcase/belief/adaptive_learning/` | Rule effectiveness learning |
| `examples/showcase/domain/infrastructure_self_healing/` | Multiway reasoning integration |
| `examples/showcase/domain/medical_diagnosis/` | Backward chaining |
| `examples/showcase/domain/fraud_detection/` | Cycle detection |

---

## Thank You!

**Hyper3: Multiway Lateral Reasoning for Modern Infrastructure**

> Multiway expansion explores multiple hypotheses in parallel, comparing branches to identify the best explanation for observed symptoms.

[View the code ->](multiway_lateral_insights.py)
