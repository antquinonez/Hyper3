# Multiway Lateral Reasoning Showcase

> **Exploring Alternative Incident Hypotheses with Multiway Expansion**

## The Problem

A cloud infrastructure health check has failed. Multiple root causes are possible: database failure, network partition, bad deployment, or cache stampede.

**Traditional approach**: Pick one hypothesis (e.g., "it's the database") and investigate. If wrong, start over.

**Hyper3's approach**: Explore ALL hypotheses simultaneously through **multiway expansion**, then cross-compare the results to find the best explanation.

## Why This Matters

In critical incidents, time is money. Traditional troubleshooting chases one theory at a time — if you're wrong, you've wasted precious minutes. Hyper3 explores every possibility in parallel, giving you a ranked list of candidates and insights from across all hypotheses in a single pass.

## A Simple Analogy

Think of this like a doctor who simultaneously explores multiple possible diagnoses (flu, infection, allergy) rather than chasing one theory at a time. Each "branch" of reasoning represents a different diagnosis, and Hyper3 compares them to find which best explains the symptoms.

## Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **Multiway Expansion** | Exploring multiple "what if" scenarios at the same time |
| **State** | One possible version of the truth (e.g., "what if the database is down") |
| **Branch** | A chain of reasoning from seed → conclusion |
| **Leaf State** | A final conclusion after applying rules |
| **Convergence** | When different paths lead to the same conclusion |
| **Simultaneity Group** | Hypotheses at the same "depth" that can be compared directly |
| **Lateral Insights** | Knowledge from one branch that applies to another |

## Quick Start

```bash
.venv/bin/python examples/showcase/multiway_reasoning/01_multiway_lateral_insights.py
```

## What You'll See

When you run the example, you'll see output like this:

```
======================================================================
SECTION 1: Cloud Infrastructure Graph
======================================================================
  Nodes: 81
  Edges: 203

======================================================================
SECTION 2: Multiway Expansion from Failed Health Check
======================================================================
  States created:    51
  Rules applied:     50
  New edges:         50
  New nodes:         0
  Max depth:         3
  Branches (leaves): 66
```

This tells you the engine explored 66 different hypothesis branches from a single failed health check.

## Scenario

The example models a realistic multi-region cloud infrastructure with:
- 3 geographic regions (us-east, us-west, eu-west)
- Shared databases, caches, and queues
- Monitoring and alerting systems
- A failed health check as the trigger event

### System Topology

Figure 1: The infrastructure we're analyzing — three regions with shared databases.

```mermaid
graph TB
    subgraph "Traffic Layer"
        CDN["CDN Edge"]
        LB_G["Load Balancer<br/>Global"]
    end

    subgraph "us-east-1"
        LB_E["LB us-east"]
        API_E["API Service"]
        WEB_E["Web Frontend"]
        AUTH_E["Auth Service"]
        CACHE_E["Cache Replica"]
        DB_RE["DB Replica"]
    end

    subgraph "us-west-2"
        LB_W["LB us-west"]
        API_W["API Service"]
        WEB_W["Web Frontend"]
        AUTH_W["Auth Service"]
        CACHE_W["Cache Replica"]
        DB_RW["DB Replica"]
    end

    subgraph "eu-west-1"
        LB_EU["LB eu-west"]
        API_EU["API Service"]
        WEB_EU["Web Frontend"]
        AUTH_EU["Auth Service"]
        CACHE_EU["Cache Replica"]
        DB_REU["DB Replica"]
    end

    subgraph "Shared Infrastructure"
        DB["DB Primary<br/>PostgreSQL"]
        Q["Queue Primary<br/>RabbitMQ"]
        CACHE["Cache Primary<br/>Redis"]
    end

    subgraph "Monitoring & Ops"
        HC["Health Checker"]
        PROM["Prometheus"]
        PD["PagerDuty Alert"]
        IR["Incident Response"]
    end

    CDN --> LB_G
    LB_G --> LB_E
    LB_G --> LB_W
    LB_G --> LB_EU
    LB_E --> API_E
    LB_W --> API_W
    LB_EU --> API_EU

    API_E --> AUTH_E
    API_E --> CACHE_E
    API_E --> DB_RE
    API_W --> AUTH_W
    API_W --> CACHE_W
    API_W --> DB_RW

    DB --> DB_RE
    DB --> DB_RW
    DB --> DB_REU

    HC --> API_E
    HC --> DB
    PROM --> API_E
    PROM --> DB
    PD --> PROM
    IR --> PD
```

### Edge Label Taxonomy

Figure 2: How relationships are labeled in the graph.

```mermaid
graph LR
    classDef routing fill:#e1f5fe
    classDef dependency fill:#fff3e0
    classDef causality fill:#fce4ec
    classDef observation fill:#e8f5e9
    classDef resolution fill:#f3e5f5

    R1["routes_to"]:::routing
    R2["fails_over_to"]:::routing
    R3["hosts"]:::routing

    D1["depends_on"]:::dependency
    D2["replicates_to"]:::dependency
    D3["distributes_to"]:::dependency

    C1["causes"]:::causality
    C2["affects"]:::causality
    C3["indicates"]:::causality

    O1["monitors"]:::observation
    O2["collects_from"]:::observation
    O3["traces"]:::observation

    R4["resolves"]:::resolution
    R5["deploys"]:::resolution
    R6["triggers"]:::resolution
```

| Category | Labels | Meaning |
|----------|---------|---------|
| **Routing** | `routes_to`, `fails_over_to`, `hosts`, `serves` | Network traffic flow |
| **Dependency** | `depends_on`, `replicates_to`, `distributes_to` | Service reliance |
| **Causality** | `causes`, `affects`, `indicates` | Cause-effect relationships |
| **Observation** | `monitors`, `collects_from`, `traces` | Telemetry links |
| **Resolution** | `resolves`, `deploys`, `triggers` | Remediation pathways |
| **Security** | `protects`, `secures`, `authenticates` | Security boundaries |

## How the Reasoning Engine Works

### Multiway Expansion

Figure 3: The engine takes seed concepts and applies multiple inference rules simultaneously, creating a branching tree of hypotheses.

```mermaid
graph TD
    SEED["Seed Concepts<br/>16 nodes: failed-health-check,<br/>latency-spike, db-primary-down..."]

    SEED --> MW{"Multiway<br/>Engine"}

    MW -->|"TransitiveRule<br/>depends_on"| B1["Branch: cascade_depends"]
    MW -->|"TransitiveRule<br/>causes"| B2["Branch: indirectly_causes"]
    MW -->|"TransitiveRule<br/>affects"| B3["Branch: indirectly_affects"]
    MW -->|"TransitiveRule<br/>indicates"| B4["Branch: correlates_with"]
    MW -->|"TransitiveRule<br/>routes_to"| B5["Branch: indirectly_routes"]
    MW -->|"InverseRule<br/>depends_on"| B6["Branch: depended_on_by"]
    MW -->|"InverseRule<br/>causes"| B7["Branch: caused_by"]
    MW -->|"InverseRule<br/>monitors"| B8["Branch: monitored_by"]
    MW -->|"InverseRule<br/>affects"| B9["Branch: affected_by"]
    MW -->|"AbductiveRule<br/>causes"| B10["Branch: possible_cause"]

    B1 --> LEAF1["Leaf States<br/>66 total"]
    B2 --> LEAF1
    B3 --> LEAF1
    B4 --> LEAF1
    B5 --> LEAF1
    B6 --> LEAF1
    B7 --> LEAF1
    B8 --> LEAF1
    B9 --> LEAF1
    B10 --> LEAF1

    LEAF1 --> SCORE["Branch Scoring<br/>vs Observed Symptoms"]
    LEAF1 --> CLUSTER["State Clustering<br/>Similarity Analysis"]
    LEAF1 --> CONVERGE["Convergence Detection<br/>Causal Invariants"]
    LEAF1 --> LATERAL["Lateral Insights<br/>Cross-branch Transfer"]
```

Each application of a rule creates a new **state** in a directed acyclic graph (DAG). States at the same depth that share active nodes form **simultaneity groups** — these are hypotheses that can be compared directly.

Figure 4: States at the same depth form groups that can be directly compared.

```mermaid
stateDiagram-v2
    [*] --> Root: Seed {failed-health-check, ...}
    Root --> S1: TransitiveRule(causes) depth=1
    Root --> S2: InverseRule(causes) depth=1
    Root --> S3: TransitiveRule(depends_on) depth=1
    Root --> S4: AbductiveRule(causes) depth=1
    Root --> S5: TransitiveRule(affects) depth=1

    S1 --> S1a: TransitiveRule(causes) depth=2
    S1 --> S1b: InverseRule(depends_on) depth=2
    S2 --> S2a: TransitiveRule(causes) depth=2
    S2 --> S2b: TransitiveRule(depends_on) depth=2
    S3 --> S3a: TransitiveRule(causes) depth=2
    S3 --> S3b: InverseRule(causes) depth=2
    S4 --> S4a: TransitiveRule(causes) depth=2
    S4 --> S4b: InverseRule(depends_on) depth=2
    S5 --> S5a: TransitiveRule(causes) depth=2
    S5 --> S5b: TransitiveRule(depends_on) depth=2

    S1a --> S1aa: InverseRule(depends_on) depth=3
    S1a --> S1ab: TransitiveRule(causes) depth=3
    S2a --> S2aa: InverseRule(causes) depth=3
    S3a --> S3aa: TransitiveRule(depends_on) depth=3

    note right of S1a
        Simultaneity Group:
        All states at depth=2
        are compared together
    end note
```

### The 10 Inference Rules

Ten inference rules operate simultaneously on the graph:

| Rule | Edge Pattern | Produces | Purpose |
|------|-------------|----------|---------|
| `TransitiveRule(causes)` | A-[causes]->B, B-[causes]->C | A-[indirectly_causes]->C | Chain cause-effect |
| `TransitiveRule(depends_on)` | A-[depends_on]->B, B-[depends_on]->C | A-[cascade_depends]->C | Dependency chains |
| `TransitiveRule(affects)` | A-[affects]->B, B-[causes]->C | A-[indirectly_affects]->C | Impact propagation |
| `TransitiveRule(indicates)` | A-[indicates]->B, B-[indicates]->C | A-[correlates_with]->C | Symptom correlation |
| `TransitiveRule(routes_to)` | A-[routes_to]->B, B-[routes_to]->C | A-[indirectly_routes]->C | Network path tracing |
| `InverseRule(causes)` | A-[causes]->B | B-[caused_by]->A | Reverse causality |
| `InverseRule(depends_on)` | A-[depends_on]->B | B-[depended_on_by]->A | Reverse dependency |
| `InverseRule(monitors)` | A-[monitors]->B | B-[monitored_by]->A | Reverse telemetry |
| `InverseRule(affects)` | A-[affects]->B | B-[affected_by]->A | Reverse impact |
| `AbductiveRule(causes)` | A-[causes]->B (B observed) | B-[possible_cause]->A | Diagnostic inference |

## The Analysis Pipeline

### Phase 1: Graph Construction

The example builds an **81-node, 203-edge** hypergraph representing the infrastructure topology. Each node carries typed metadata (type, tier, category, severity). Edges are labeled with semantic relationship types.

```mermaid
pie showData
    title Node Type Distribution
    "Services (API, Web, Auth...)" : 27
    "Databases & Replicas" : 4
    "Caches & Replicas" : 4
    "Queues & Consumers" : 4
    "Load Balancers" : 4
    "Monitoring & Alerting" : 5
    "Symptoms" : 12
    "Incidents" : 4
    "Security & Networking" : 9
    "Process & Runbooks" : 4
    "Other Infrastructure" : 4
```

### Phase 2: Multiway Expansion

From 16 seed concepts (the failed health check and related symptoms), the engine applies all 10 rules simultaneously, creating a branching structure:

```
                     ┌── transitive(causes)      ──> indirectly_causes chains
                     ├── transitive(depends_on)  ──> cascade_depends chains
                     ├── transitive(affects)     ──> indirectly_affects chains
Seed (16 nodes) ────├── transitive(indicates)   ──> correlates_with chains
                     ├── transitive(routes_to)   ──> indirectly_routes chains
                     ├── inverse(causes)         ──> caused_by reverse edges
                     ├── inverse(depends_on)     ──> depended_on_by reverse
                     ├── inverse(monitors)       ──> monitored_by reverse
                     ├── inverse(affects)        ──> affected_by reverse
                     └── abductive(causes)       ──> possible_cause diagnosis
```

**Result**: 51 states created, 50 rules applied, 50 inference edges produced, 66 leaf states.

### Phase 3: Branch Scoring

Each leaf state is scored against the **8 observed symptoms** using a composite metric:

```
score = (edge_hits + symptom_overlap) / (total_symptoms + produced_edges + 1)
```

This measures how well a branch explains the observed symptoms. Higher scores mean the branch's inferred edges and active nodes better cover the symptom set.

**Top-scoring branches** typically involve `transitive(causes)` rules that chain through the causal graph, connecting root causes (db-primary-down, network-partition, cache-stampede) to observed symptoms (failed-health-check, latency-spike, etc.).

### Phase 4: State Clustering

Figure 5: States are grouped by depth into simultaneity groups for comparison.

```mermaid
graph LR
    subgraph "Group 1 (16 states)"
        G1_1["transitive(depends_on) d=1"]
        G1_2["transitive(depends_on) d=1"]
        G1_3["transitive(depends_on) d=1"]
    end

    subgraph "Group 4 (14 states)"
        G4_1["transitive(depends_on) d=2"]
        G4_2["transitive(causes) d=2"]
        G4_3["transitive(causes) d=2"]
    end

    subgraph "Group 5 (10 states)"
        G5_1["transitive(routes_to) d=2"]
        G5_2["transitive(causes) d=2"]
        G5_3["transitive(causes) d=2"]
    end

    G1_1 -.similarity.-> G4_1
    G4_1 -.similarity.-> G5_1
    G4_2 -.novel.-> G4_3
    G5_2 -.novel.-> G5_3
```

States are mapped into a coordinate space using multidimensional scaling. The engine identifies **simultaneity groups** — sets of states at the same depth that represent competing hypotheses.

### Phase 5: Convergence Detection

Figure 6: When different rules reach the same conclusion, that's a convergent insight.

```mermaid
flowchart LR
    A["State A:\nRule: transitive(causes)\nTargets: {failed-health-check, latency-spike}"]
    B["State B:\nRule: inverse(causes)\nTargets: {failed-health-check, slow-query}"]

    A -->|"overlap:\nfailed-health-check"| C{"Convergent?\nYes -- shared target"}
    B --> C
```

The engine detects when **different rules reach overlapping conclusions** — this is a causal invariant. Two states that applied different rules but produced edges targeting the same nodes represent convergent reasoning paths.

**Result**: 20 causal invariants found and merged.

### Phase 6: Lateral Insights

Figure 7: Comparing branches within the same group reveals unique knowledge.

```mermaid
graph TB
    subgraph "Branch A: depends_on chain"
        A1["us-west-scheduler -[cascade_depends]-> us-west-storage"]
        A2["eu-west-web -[cascade_depends]-> eu-west-auth"]
    end

    subgraph "Branch B: causes chain"
        B1["cache-stampede -[indirectly_causes]-> latency-spike"]
        B2["network-partition -[indirectly_causes]-> timeout-error"]
        B3["db-primary-down -[indirectly_causes]-> slow-query"]
    end

    A1 -.unique to A.-> L{"Lateral Insight:\nIf cache-stampede causes\nlatency, then us-west-storage\nmay be implicated too"}
    B1 -.unique to B.-> L
```

The most powerful feature: comparing branches within the same simultaneity group to find **novel knowledge** — nodes or edges present in one branch but absent in another.

## Understanding the Output

### Branch Score Interpretation

| Score Range | Meaning |
|------------|---------|
| 0.9+ | Branch explains most symptoms — strong candidate root cause |
| 0.7-0.9 | Branch explains a subset of symptoms — partial match |
| 0.5-0.7 | Branch touches some symptoms — weak signal |
| < 0.5 | Branch largely irrelevant to observed symptoms |

### Simultaneity Groups

States in the same simultaneity group are **at the same depth** in the multiway DAG and can be directly compared. The group number indicates which "wave" of reasoning the states belong to.

### Lateral Insight Types

| Type | Description | Example |
|------|-------------|---------|
| **Novel in source** | Nodes/edges in the reference branch not in the comparison | A dependency chain unique to one hypothesis |
| **Novel in lateral** | Nodes/edges in the comparison branch not in the reference | A causal link unique to another hypothesis |
| **Complementary** | Different branches that together cover more symptoms | One branch explains DB issues, another explains network |

## What Makes This Different

Traditional diagnostic systems follow a **single path**: pick the most likely hypothesis, pursue it, backtrack if wrong. Hyper3's multiway engine explores **all hypotheses in parallel** through a branching state space, then uses structural comparison to identify:

1. **Which branches best explain the evidence** (branch scoring)
2. **Which branches converge on the same conclusions** (causal invariants)
3. **What knowledge from one branch applies to another** (lateral insights)

This is particularly valuable in incident response where the root cause is unknown and time is critical — instead of chasing one hypothesis while the incident worsens, you get a ranked set of candidates with cross-hypothesis insights.

## Key Metrics

| Metric | Value |
|--------|-------|
| Graph nodes | 81 |
| Graph edges (initial) | 203 |
| Graph edges (after reasoning) | 253 |
| Seed concepts | 16 |
| Inference rules | 10 |
| States created | 51 |
| Rules applied | 50 |
| Inference edges produced | 50 |
| Leaf states | 66 |
| Simultaneity groups | 5 |
| Causal invariants merged | 20 |
| Lateral insights discovered | 6 |
| Best branch score | 0.909 |

## Code Walkthrough

### 1. Infrastructure Construction

```python
mem = HypergraphMemory(evolve_interval=0)
build_infrastructure(mem)  # 81 nodes, 203 edges
```

The `build_infrastructure()` function creates the full topology: 3 regions, each with API, web, auth, cache, worker, scheduler, storage, and k8s nodes, plus shared databases, queues, caches, load balancers, and monitoring infrastructure.

### 2. Register Inference Rules

```python
rules = [
    TransitiveRule(edge_label="depends_on", new_label="cascade_depends"),
    TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
    TransitiveRule(edge_label="affects", new_label="indirectly_affects"),
    TransitiveRule(edge_label="indicates", new_label="correlates_with"),
    TransitiveRule(edge_label="routes_to", new_label="indirectly_routes"),
    InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
    InverseRule(edge_label="causes", inverse_label="caused_by"),
    InverseRule(edge_label="monitors", inverse_label="monitored_by"),
    InverseRule(edge_label="affects", inverse_label="affected_by"),
    AbductiveRule(effect_label="causes", cause_label="possible_cause"),
]
mem.add_rules(*rules)
```

### 3. Seed and Reason

```python
seed = {
    "failed-health-check", "latency-spike", "error-rate-spike",
    "connection-refused", "timeout-error", "slow-query",
    "db-primary-down", "network-partition", "bad-deploy",
    "us-east-api", "us-east-auth", "us-east-cache",
    "db-replica-us-east", "cache-replica-us-east",
    "lb-us-east", "lb-global",
}
result = mem.reason(seed_concepts=seed, max_depth=3, max_total_states=50)
```

### 4. Score Branches

```python
symptom_ids = {node.id for node in symptom_nodes}
leaves = mw_graph.get_leaves()
for leaf in leaves:
    score = score_branch_against_symptoms(mem, leaf, symptom_ids)
```

### 5. Analyze Clustering and Convergence

```python
clustering_report = result.clustering
convergence_report = result.state_convergence
groups = mem.state_clustering.simultaneity_groups
```

### 6. Extract Lateral Insights

```python
for concept in ["failed-health-check", "db-primary-down", "network-partition", "bad-deploy"]:
    insights = mem.lateral_insights(concept)
```

## Related Examples

| Example | Focus |
|---------|-------|
| `examples/advanced/13_self_evolving_cognition.py` | Feedback-driven evolution, metamorphosis validation |
| `examples/advanced/12_adaptive_learning.py` | Rule effectiveness learning, Thompson sampling |
| `examples/domain/infrastructure_self_healing.py` | Multiway reasoning + feedback loop integration |
| `examples/domain/medical_diagnosis.py` | Backward chaining for differential diagnosis |
| `examples/domain/fraud_detection_intelligence.py` | Cycle detection, funnel account identification |

## API Reference

| Method | Purpose |
|--------|---------|
| `mem.reason(seed_concepts, max_depth, max_total_states)` | Run multiway expansion from seed nodes |
| `mem.lateral_insights(concept)` | Find knowledge transferable across branches |
| `mem.state_clustering.simultaneity_groups` | Get groups of states at the same depth |
| `mem.state_clustering.coordinates` | Get state coordinate embeddings |
| `result.clustering` | State clustering report from reasoning |
| `result.state_convergence` | Merge report from state convergence |
| `result.expansion` | Expansion statistics (states, rules, edges) |
