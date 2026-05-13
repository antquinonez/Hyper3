# Threat Intelligence Knowledge Base Showcase

> Build and query a 140-node CTI graph with traversal, ranking, components, communities, anomaly detection, and rule-based inference.

**What you will learn:**

- How to construct a multi-entity CTI hypergraph with typed metadata and semantic edge labels
- Neighborhood traversal (BFS) and pattern-matching queries for analyst workflows
- Degree centrality for CVE prioritization and attack-surface ranking
- Malware variant lineage analysis using `variant_of` edges (Zeus family tree, actor-to-variant mapping)
- Connected-component decomposition for ecosystem boundary detection
- Rule-based inference (transitive chains, inverse attribution) and structural anomaly classification

## 1. What this example focuses on

This showcase is a broad CTI graph exploration demo. It emphasizes:

- graph construction across six CTI entity classes
- neighborhood and path traversal for analyst workflows
- centrality-based vulnerability prioritization
- ecosystem discovery via connected components and communities
- structural anomaly classification for actor topology
- reasoning pass for inferred attribution inverses

This example is a **breadth-first** exploration of CTI graph analytics: 13 sections covering traversal, centrality, path tracing, malware lineage, components, modality filtering, communities, and anomalies across the full 140-node dataset. In contrast, `threat_intel_full_chain` is a **depth-first** single-pipeline analysis that chains rule inference, spreading activation, and self-evolution into one continuous workflow focused on a smaller seed set.

## 2. Run

```bash
.venv/bin/python examples/showcase/domain/threat_intelligence/knowledge_basics.py
```

## 3. Current validated metrics

From current runtime:

- Nodes: 140
- Initial edges: 293
- Final edges after reasoning: 309
- Inferred edges produced in reasoning pass: 16
- Connected components: 14
- Communities detected: typically around 15 (label propagation)

Entity counts:

- 32 threat actors
- 32 CVEs
- 22 malware families
- 23 TTPs
- 16 infrastructure nodes
- 15 target industries

## 4. Walkthrough

### Section 1: Build graph

Loads actors, CVEs, malware, TTPs, infrastructure, and industries with typed metadata and modalities.

### Section 2: Recall and traversal

Uses `mem.recall()` and BFS query to inspect local attack context (example: Lazarus neighborhood, GOV reachability).

### Section 3-4: Pattern and centrality

- edge-label pattern counts (`exploits`, `uses`, `targets`)
- degree centrality for CVE prioritization

Current top CVE by centrality: `CVE-2023-44228`.

### Section 5-6: Subgraph and path tracing

- extracts APT28 profile subgraph
- traces actor-to-sector paths (e.g., Lazarus -> FIN)

### Section 7: Malware variant lineage

Uses `variant_of` edges to trace the Zeus malware family tree: Emotet, TrickBot, QakBot, and Dridex are all Zeus descendants. The section then cross-references each variant back to the threat actors that deploy it, producing an actor-to-variant mapping (e.g., APT38 uses Zeus, FIN6 and TA505 use Emotet, BlackBasta uses QakBot).

### Section 8-9: Isolation and components

- identifies isolated nodes needing enrichment
- decomposes graph into connected ecosystems

### Section 10: Modality slices

Queries the same seed concept via CAUSAL/SENSORY/CONCEPTUAL modalities.

### Section 11: Reasoning

Registers rules via namespace style (`mem.reason.add_rules(...)`) and runs reasoning.

In current data shape:

- `exploited_by` reverse edges enable vulnerability-centric analyst workflows (which actors exploit this CVE?)
- `used_by` reverse edges enable malware-centric queries (which actors use this tool?)
- `attributed_to_inverse` reverse edges support infrastructure-to-actor tracing

### Section 12: Communities

Runs label-propagation community detection. Results are useful but not deterministic partitions.

### Section 13: Structural anomalies

Runs anomaly scoring for selected actors and reports low_risk/boundary/anomalous classifications.

### Expected Output (Section 7 — variant lineage)

```
SECTION 7: Malware Variant Lineage
======================================================================
  Known malware variant relationships (8):
    Emotet (Trojan) --> variant_of --> Zeus
    TrickBot (Trojan) --> variant_of --> Zeus
    QakBot (Trojan) --> variant_of --> Zeus
    Dridex (Trojan) --> variant_of --> Zeus
    ...

  Zeus malware family tree:
    Direct descendants: Dridex, Emotet, QakBot, TrickBot
    Actors using Zeus descendants: APT38, BlackBasta, Carbanak, FIN6, FIN12, Lazarus, TA505
```

## 5. Mermaid (representative)

```mermaid
graph TD
    APT28[1) APT28] -->|uses| COBALT[Cobalt_Strike]
    APT28 -->|exploits| LOG4J[2) CVE-2023-44228]
    APT28 -->|targets| GOV[3) GOV]
    COBALT -->|communicates_with| C2[C2_VPN_GATE_01]
    C2 -->|attributed_to| APT28
```

This is a subset; the full script graph is much larger.

How to read it:

- This micro-pattern links actor behavior (`uses` + `exploits`) to mission outcome (`targets`).
- Infrastructure attribution edges (`attributed_to`) support campaign grouping and component/community analyses.
- In the full graph, many actors share tools and CVEs, which creates the dense ecosystem seen in component output.

## 6. How To Use This Example As an Analyst

- Start with pattern counts to estimate attack-surface breadth by relationship type.
- Use centrality to prioritize investigation sequence, then validate with explicit path analysis.
- Use components for macro ecosystem boundaries, then communities for sub-cluster structure.
- Treat anomaly status as structural signal, not threat-severity verdict.

### Centrality Interpretation

| Centrality Range | Meaning |
|------------------|---------|
| 0.08+ | Extremely well-connected — critical node, high impact if compromised |
| 0.04-0.08 | Well-connected — significant role in attack chains |
| 0.02-0.04 | Moderately connected — part of multiple attack paths |
| < 0.02 | Peripheral — limited connections |

### Component Analysis

| Component Size | Interpretation |
|----------------|----------------|
| 100+ nodes | Major threat ecosystem — multiple actors sharing infrastructure |
| 20-50 nodes | Regional/medium cluster — related actors or shared campaigns |
| 5-20 nodes | Small cluster — specific campaign or malware family |
| 1-5 nodes | Isolated or emerging — needs enrichment |

### Attack Path Analysis

| Path Length | Meaning |
|-------------|---------|
| 1 hop | Direct relationship (actor targets sector directly) |
| 2 hops | Indirect via malware or CVE (actor -> malware -> sector) |
| 3-4 hops | Complex chain (actor -> malware -> CVE -> infrastructure -> sector) |

### Anomaly Score Interpretation

| Score Range | Status | Meaning |
|-------------|--------|---------|
| 0.37+ | anomalous | Cyclic or high-centrality structure detected — unusual connectivity pattern |
| 0.10-0.37 | boundary | Some structural features worth investigating |
| < 0.10 | low_risk | No unusual structural patterns detected |

## 7. Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **Threat Actor** | APT groups, ransomware operators (e.g., APT28, Lazarus, Conti) |
| **CVE** | Published vulnerability with CVSS score (e.g., Log4j CVE-2023-44228) |
| **Malware** | RATs, ransomware, trojans used by actors (e.g., Cobalt Strike, Emotet) |
| **TTP** | MITRE ATT&CK tactics and techniques (e.g., T1566 Phishing) |
| **Infrastructure** | C2 servers, botnets, exfiltration servers |
| **Modality** | The lens through which you view a node (CAUSAL, SENSORY, CONCEPTUAL, ABSTRACT) |
| **Pattern Match** | Finding edges by label or source node |
| **Centrality** | How connected a node is — high centrality = high impact |
| **Subgraph** | Extracting a subset of the graph around a specific node |
| **Connected Component** | A cluster of nodes where every node can reach every other |
| **Inference Rule** | A pattern that generates new edges from existing structure |
| **Community** | A group of nodes with dense internal connections, detected algorithmically |
| **Anomaly Status** | Classification along low_risk / boundary / anomalous based on structural analysis |

## 8. API Methods

| Method | Purpose |
|--------|---------|
| `mem.add(label, data, modalities)` | Create a node with metadata and modalities |
| `mem.link(source, target, label)` | Create a semantic edge between nodes |
| `mem.recall(concept, max_depth)` | BFS traversal from a node |
| `mem.query(concept, modality=, strategy=, max_depth=)` | Modality/strategy-filtered traversal |
| `mem.pattern_match(edge_label, source_label, target_label)` | Find edges matching criteria |
| `mem.analyze.centrality("degree")` | Compute centrality scores for all nodes |
| `mem.analyze.edges()` | Iterate all edges (for label filtering) |
| `mem.subgraph(labels)` | Extract a subgraph around specific nodes |
| `mem.analyze.paths(source, target, max_depth)` | Find attack paths between nodes |
| `mem.analyze.components()` | Identify threat ecosystems (clusters) |
| `mem.stats()` | Get graph statistics |
| `mem.reason.add_rules(*rules)` | Register inference rules for reasoning |
| `mem.reason(seeds, max_depth)` | Apply rules to infer new edges |
| `mem.analyze.communities(seed)` | Detect communities via label propagation |
| `mem.analyze.anomalies(concept)` | Analyze structural anomaly status |

## 9. Related Examples

| Example | Focus |
|---------|-------|
| `examples/showcase/domain/threat_intel_full_chain/threat_intel_full_chain.py` | Full-chain analysis with rule inference, spreading activation, and self-evolution |
| `examples/showcase/core/network_analytics/graph_analytics.py` | Centrality, cycles, components, risk scoring |
| `examples/showcase/reasoning/knowledge_reasoning/knowledge_reasoning.py` | Transitive inference, backward chaining, belief revision |

## 10. Real-world gap

Production CTI graph operations still require external pipelines for:

- feed ingestion and normalization
- entity/alias resolution
- temporal campaign evolution
- confidence/provenance lifecycle management
