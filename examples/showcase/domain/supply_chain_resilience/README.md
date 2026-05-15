# Supply Chain Resilience Showcase

> Multi-tier supply-chain risk analysis with transitive reasoning, cascade tracing, lead-time exposure, and diversification prioritization.

**What you will learn:**

- How to model a realistic 3-tier supplier network as a hypergraph with typed nodes and labeled edges
- How transitive rule inference materializes hidden multi-hop risk cascades across dependency chains
- How centrality metrics (degree, betweenness) identify chokepoints and single points of failure
- How to trace disruption paths from a geopolitical or natural risk event to a finished product
- How cumulative lead-time analysis reveals the longest recovery windows in a multi-tier chain
- How to score and prioritize diversification candidates by reliability deficit, lead time, and backup coverage

## 1. What this example demonstrates

This script builds a realistic supply-chain graph and answers resilience questions with graph-native analytics:

- chokepoints via centrality
- single-point-of-failure inventory
- multi-hop risk cascade inference
- disruption path tracing to final product
- cumulative lead-time stress analysis
- backup coverage and diversification priorities

The key insight is that supply chain resilience is fundamentally a graph problem. Risks do not stay confined to the node they first touch; they propagate through multi-hop dependency chains (supplier → component → assembly → product). Transitive rule inference materializes these hidden connections automatically, turning an explicitly-modeled 2-hop graph into a graph that reveals 3- and 4-hop cascade paths that would otherwise remain invisible until a disruption occurs.

## 2. Run

```bash
.venv/bin/python examples/showcase/domain/supply_chain_resilience/supply_chain_resilience.py
```

## 3. Current validated graph profile

Initial graph construction:

- 126 nodes
- 268 edges

Edge groups:

- `supplies_to`: 61
- `manufactured_at`: 16
- `stored_at`: 24
- `transported_via`: 20
- `affected_by`: 68
- `depends_on`: 39
- `serves`: 25
- `backup_for`: 15

After reasoning (current script):

- 288 total edges
- `cascade_affected_by`: 10
- `indirectly_supplies`: 10

## 4. Walkthrough

### Section 1: Build typed network

Adds suppliers (tiers 1-3), products, factories, distribution centers, transport lanes, risks, and markets with attributes like reliability, lead time, and single-source status.

### Section 2: Centrality scan

- degree centrality for ripple potential
- betweenness centrality for chokepoints

Current top chokepoints are product-assembly hubs (e.g., `prod_vehicle`, `prod_battery_pack`, `prod_ecu`).

### Section 3: SPOF identification

Finds:

- single-source suppliers
- critical products with <=1 alternate
- single-source suppliers with no backup coverage

### Section 4: Two-pass reasoning

Rules:

- `TransitiveRule(edge_label="affected_by", new_label="cascade_affected_by")`
- `TransitiveRule(edge_label="supplies_to", new_label="indirectly_supplies")`

The script runs these in separate phases (rule-scoped calls) so reported cascade/supply outputs are interpretable.

### Section 5: Risk-to-product path tracing

Uses a custom `_trace_paths` helper with label-semantic filtering (`allowed_labels`) to trace disruption paths to `prod_vehicle`. This avoids misleading paths through unrelated edge semantics.

### Section 6: Lead-time and reliability stress

- tier-level lead-time summary
- worst-case 3-tier cumulative chain
- reliability-weighted risk ranking with single-source penalty

### Section 7: Backup gaps and diversification priorities

Ranks highest-priority diversification candidates by combined score:

- reliability deficit
- lead time
- connected risk exposure
- backup absence penalty

**Expected Output** (Section 7 diversification priorities):

```
  Diversification priorities (top 5):
    1. sup_t3_russia_palladium
       country=Russia  material=palladium  reliability=0.65
       lead_time=70d  risk_exposure=0.80  has_backup=NO
    2. sup_t3_drc_cobalt
       country=DRC  material=cobalt_ore  reliability=0.68
       lead_time=65d  risk_exposure=0.95  has_backup=NO
    3. sup_t2_congo_cobalt
       country=DRC  material=cobalt  reliability=0.72
       lead_time=50d  risk_exposure=1.75  has_backup=NO
    4. sup_t2_kazakhstan_uranium
       country=Kazakhstan  material=uranium  reliability=0.78
       lead_time=55d  risk_exposure=0.80  has_backup=NO
    5. sup_t1_china_rare_earth
       country=China  material=rare_earth  reliability=0.85
       lead_time=35d  risk_exposure=0.85  has_backup=NO
```

## 5. Mermaid (representative)

```mermaid
graph TD
    RISK[1) risk_trade_war] -->|affected_by| T2[sup_t2_china_silicon]
    T2 -->|supplies_to| T1[sup_t1_taiwan_semicon]
    T1 -->|supplies_to| P1[2) prod_semiconductor]
    P1 -->|affected_by| MC[prod_microcontroller]
    MC -->|affected_by| P2[prod_ecu]
    P2 -->|affected_by| VEH[3) prod_vehicle]
```

This is a simplified slice; real graph includes 126 nodes and many parallel paths.

How to read it:

- Follow the chain left-to-right to see risk propagation from event to final product. The mermaid diagram shows a full 6-hop cascade: the `risk_trade_war` geopolitical event hits `sup_t2_china_silicon` (tier-2 silicon supplier), which `supplies_to` `sup_t1_taiwan_semicon` (tier-1 semiconductor fab), which `supplies_to` `prod_semiconductor`, which propagates via `affected_by` to `prod_microcontroller`, then to `prod_ecu`, and finally to `prod_vehicle`. Each hop represents a dependency that can fail independently.
- Supplier tiers appear in the early middle of the path; product assembly dependencies appear later.
- The same final product usually has many alternative paths, which is why the full analysis includes centrality, not just one path trace.

## 6. How To Interpret Risk Outputs

- High degree means broad immediate ripple; high betweenness means bridge fragility and rerouting risk.
- A short path with high-impact nodes can outrank a long path in practical severity.
- Cumulative lead time is a recovery-lag proxy; it helps estimate how long disruption remains latent before visible shortage.
- Diversification ranking is a prioritization tool, not a procurement decision by itself.

### Centrality Scores

| Metric | What It Measures | High Value Means |
|--------|-----------------|-----------------|
| Degree centrality | Direct connections (weighted by network size) | Wide ripple effect — disruption spreads to many neighbors |
| Betweenness centrality | Fraction of shortest paths passing through | Bridge node — removal fragments the network |

### Risk Scores

The diversification priority score combines:

- `(1 - reliability_score)` — lower reliability increases urgency
- `lead_time_days` — longer lead times increase recovery difficulty
- `risk_exposure` — sum of connected risk impact values
- `2x penalty` if no backup exists

### Cascade Edge Labels

| Label | Produced By | Meaning |
|-------|-------------|---------|
| `cascade_affected_by` | TransitiveRule on `affected_by` | Multi-hop risk propagation |
| `indirectly_supplies` | TransitiveRule on `supplies_to` | Indirect material flow across tiers |
| `supplied_by` | InverseRule on `supplies_to` | Reverse direction of supply (registered but not applied in rule-scoped phases) |

## 7. API Methods

| Method | Purpose |
|--------|---------|
| `HypergraphMemory(evolve_interval=0)` | Create memory with deterministic behavior |
| `mem.add(name, data=...)` | Add a typed node with attributes |
| `mem.link(src, tgt, label=...)` | Create a directed edge between nodes |
| `mem.analyze.centrality("degree")` | Compute normalized degree for all nodes |
| `mem.analyze.centrality("betweenness")` | Compute normalized betweenness for all nodes |
| `mem.reason.add_rules(...)` | Register inference rules |
| `mem.reason(seeds=..., rules=..., max_depth=..., max_total_states=...)` | Run multiway reasoning (optionally scoped to specific rules) |
| `mem.pattern_match(edge_label=...)` | Find edges matching a label |
| `_trace_paths(mem, src, tgt, allowed_labels=..., max_depth=..., max_paths=...)` | Custom label-scoped path tracer (used instead of `find_paths` for semantic filtering) |
| `mem.connected_components()` | Find connected subgraphs |
| `mem.stats()` | Get graph statistics |
| `mem.size` | Tuple of (node_count, edge_count) |
| `top_k(scores, k=N)` | Get top N items from a centrality dict |

## 8. Related Examples

- **Microservices Reasoning** — TransitiveRule and InverseRule applied to service dependency blast radius
- **Centrality and Ranking** — Degree, betweenness, and PageRank on network graphs
- **Paths and Connectivity** — Path tracing, connected components, and network connectivity
- **Multiway Reasoning** — Deep dive into the multiway expansion engine

## 9. Real-world gap

Production rollout still needs:

- continuous ERP/procurement/logistics ingestion
- temporal inventory and buffer modeling
- probabilistic expected-loss scoring (risk probability x impact x path dependence)
- policy constraints (contract lock-ins, minimum order commitments)
