# Full-Chain Threat Intelligence Analysis

> One-script CTI pipeline: rule inference, alert triage activation, attribution sampling, stale IOC pruning, and centrality ranking.

## 1. Why this example is valuable

Most CTI examples isolate one technique. This one composes several on a shared graph:

1. build CTI knowledge base
2. infer reverse/abductive relationships
3. run spreading activation from a live alert
4. sample attribution hypotheses (Born rule)
5. evolve graph to remove stale indicators
6. rank actors/CVEs by connectivity impact

## 2. Run

```bash
.venv/bin/python examples/showcase/domain/threat_intel_full_chain/threat_intel_full_chain.py
```

## 3. Current validated runtime metrics

Initial graph:

- 73 nodes
- 122 edges

After reasoning:

- +30 newly created edges in this reasoning pass
- 39 total inferred-labeled edges present (including pre-existing overlap categories)

After evolution:

- 56 nodes
- 152 edges
- stale IOCs pruned: 3
- merged nodes: 14

Belief sampling (1000 draws) typically tracks configured priors:

- APT28 ~55%
- APT29 ~21%
- Lazarus ~14%
- Volt_Typhoon ~10%

Context-weighted sampling can push APT28 near ~80%+.

## 4. Walkthrough

### Section 1: Build CTI graph

Adds typed nodes for actors, CVEs, malware, industries, infrastructure, TTPs, plus stale IOC nodes with low weight.

### Section 2: Rule-based reasoning

Registers rules via namespace style:

```python
mem.reason.add_rules(...)
```

Key outputs:

- `exploited_by` reverse edges
- `targeted_by`, `used_by`, and `communicates_with` reverse edges
- abductive `suspected_attacker` hypotheses

### Section 3: Spreading activation

Injects activation at `CVE-2023-44228`, propagates for 4 iterations, and surfaces actors/sectors/CVEs that light up first.

### Section 4: Attribution sampling

Uses belief-layer distribution and Born-rule sampling to compare prior vs context-weighted attribution outcomes.

### Section 5: Self-evolution

Recalls active nodes via `mem.recall()`, then runs `mem.evolve()` to prune stale IOC nodes and merge equivalents.

### Section 6: Centrality and pattern views

Ranks top actors and CVEs by degree centrality and summarizes APT28 profile subgraph.

## 5. Mermaid (representative)

```mermaid
graph LR
    APT28[1) APT28] -->|exploits| LOG4J[CVE-2023-44228]
    APT28 -->|uses| COBALT[Cobalt_Strike]
    APT28 -->|targets| GOV[2) GOV]
    COBALT -->|communicates_with| C2[C2_VPN_GATE_01]
    LOG4J -->|exploited_by| APT28
```

The full script includes many more actors/edges than this slice.

How to read it:

- Forward edges (`exploits`, `uses`, `targets`) represent observed campaign behavior.
- Reverse edge (`exploited_by`) is inferred for analyst-friendly reverse lookup.
- Activation and centrality sections in the script operate over both observed and inferred structure.

## 6. How To Read CTI Results

- Inference edges improve query ergonomics (reverse lookups), but they are still only as good as source labeling quality.
- Activation energy is comparative ranking, not probability.
- Born-rule sampling is useful for uncertainty exploration; operational decisions should aggregate multiple samples.
- Evolution pruning can remove stale IOCs and improve precision, but analysts should preserve historical archives separately.

### Spreading Activation Energy

Energy is a relative measure of graph proximity to the stimulated node. Direct neighbors receive the most energy (depth=1), with decay at each hop. The absolute values depend on branching factor and iteration count — use them for ranking, not as absolute thresholds.

### Born-Rule Probability vs. Context-Weighted Probability

The raw Born-rule probability is `|amplitude|²` normalized across all outcomes. Context weights scale individual outcome amplitudes before sampling, shifting the distribution.

### Centrality Scores

Degree centrality = (number of neighbors) / (total nodes - 1). This counts all edge types through `incident_edges()`.

### Evolution Metrics

- **Pruned**: nodes whose weight fell below the pruning threshold, removed from the graph
- **Merged**: structurally equivalent nodes collapsed into one
- **Decayed**: edges whose weights were reduced but not removed
- **Reinforced**: edges whose weights were increased due to frequent access

## 7. Key Concepts

| Term | What it means here |
|---|---|
| **Labeled hyperedge** | A directed relationship between nodes — `APT28 -[exploits]-> CVE-2023-44228` is one edge with a semantic label |
| **Inverse rule** | For every `A -[exploits]-> B`, create `B -[exploited_by]-> A`, enabling reverse lookups |
| **Abductive rule** | Given an effect (APT targets sector), hypothesize a cause (suspected attacker), producing attribution hypotheses |
| **Spreading activation** | Inject energy into a node (the alert), propagate it along edges, measure which nodes receive the most |
| **Born-rule sampling** | Each attribution hypothesis has a complex amplitude; sampling uses \|amplitude\|² as the probability |
| **Self-evolution** | The graph decays unused edges, prunes below-threshold nodes, and merges equivalent nodes |
| **Degree centrality** | Fraction of nodes a given node connects to — measures how many attack paths pass through it |
| **IOC** | Indicator of Compromise — an IP, domain, or hash associated with malicious activity |

### Glossary

| Term | Definition |
|---|---|
| **CTI** | Cyber Threat Intelligence — information about threats, adversaries, and vulnerabilities |
| **APT** | Advanced Persistent Threat — a sustained, targeted attack campaign |
| **CVE** | Common Vulnerabilities and Exposures — a standardized vulnerability identifier |
| **IOC** | Indicator of Compromise — observable evidence of a security breach |
| **TTP** | Tactics, Techniques, and Procedures — adversary behavior patterns (MITRE ATT&CK) |
| **CVSS** | Common Vulnerability Scoring System — numerical severity rating (0-10) |
| **SOC** | Security Operations Center — the team that monitors and responds to alerts |
| **C2** | Command and Control — infrastructure used to communicate with compromised systems |

## 8. API Methods

| Method | Purpose |
|---|---|
| `HypergraphMemory(evolve_interval=0)` | Create memory with auto-evolution disabled |
| `mem.add(label, data=..., modalities=...)` | Create a hypernode with typed data |
| `mem.link(source, target, label=..., weight=...)` | Create a labeled directed hyperedge |
| `mem.reason.add_rules(*rules)` | Register inference rules |
| `mem.reason(seeds=..., max_depth=..., auto_commit=True)` | Run multiway reasoning |
| `mem.activate(concept, energy=..., iterations=...)` | Inject activation energy and propagate along edges |
| `mem.recall(concept, max_depth=..., max_nodes=...)` | Retrieve neighborhood (accesses nodes, affecting evolution) |
| `mem.belief.create(outcomes, amplitudes=...)` | Create a belief state |
| `mem.belief.sample(distribution, context=...)` | Sample an outcome via Born rule |
| `mem.evolve()` | Run decay/prune/merge/reinforce cycle |
| `mem.analyze.centrality("degree")` | Compute degree centrality for all nodes |
| `mem.pattern_match(source_label=..., edge_label=...)` | Find edges matching a pattern |
| `mem.subgraph(node_labels)` | Extract a subgraph |
| `mem.stats()` | Get graph statistics |
| `top_k(scores, k=5)` | Return top-k items from a score dict |

### Inference Rules Used

| Rule | What it does |
|---|---|
| `InverseRule(edge_label, inverse_label)` | Creates reverse edges for bidirectional lookup |
| `AbductiveRule(effect_label, cause_label)` | Hypothesizes causes from observed effects |

## 9. Real-world gap

Still synthetic/local. Production CTI deployments need:

- feed ingestion (STIX/TAXII, scanner/SIEM enrichment)
- entity resolution across aliases
- temporal campaign modeling
- confidence/provenance management at scale
