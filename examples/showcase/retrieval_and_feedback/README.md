# Semantic Retrieval with Relevance Feedback Showcase

> **Multi-Signal Retrieval and Learning-to-Rank on a 177-Node Cybersecurity Knowledge Base**

## 1. The Approach

Information retrieval systems typically rely on a single signal — keyword matching, vector similarity, or graph traversal. Each signal has blind spots: keyword search misses synonyms, vector similarity misses structural context, and graph traversal misses nodes outside the connected neighborhood.

**The Single-Signal Problem:** A security analyst searching for "ransomware" needs results that include both structurally related concepts (encryption, backup protection, detection tools) and semantically similar concepts (other malware types). A single retrieval method covers only part of this need.

**The Hyper3 Approach:** Combine three retrieval signals — spreading activation (graph topology), embedding similarity (semantic closeness), and Reciprocal Rank Fusion (RRF) to merge ranked lists. Then train a learning-to-rank model from user relevance feedback to weight signals based on which ones produce better results for actual queries.

## 2. Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **Spreading Activation** | Energy propagates from a seed node through graph edges; nodes closer to the seed receive higher activation scores |
| **Embedding Similarity** | Cosine similarity between vector embeddings of node labels; captures semantic relatedness independent of graph structure |
| **Reciprocal Rank Fusion (RRF)** | Merges two ranked lists by assigning each item a score of `1/(k + rank)` from each list, then summing |
| **Relevance Feedback** | User marks retrieved results as relevant or not; the system learns which signals correlate with relevance |
| **Learning-to-Rank (LTR)** | A linear model trained on per-item features (activation, similarity, degree, depth) to predict relevance |

## 3. Quick Start

Run the showcase to build a 177-node cybersecurity knowledge base and demonstrate retrieval with feedback:

```bash
.venv/bin/python examples/showcase/retrieval_and_feedback/03_retrieval_and_feedback.py
```

### What You'll See

The example builds a cybersecurity/IT operations graph and runs 11 analysis sections:

```
======================================================================
SECTION 1: Knowledge Base Construction
======================================================================
  Nodes: 177
  Edges: 251
    incident: 36 nodes
    infrastructure: 47 nodes
    organization: 23 nodes
    security: 71 nodes
```

## 4. The Scenario

The example models a cybersecurity and IT operations knowledge base with **177 nodes and 251 edges** across four categories:

- **71 Security Nodes:** Threats (ransomware, phishing, ddos), vulnerabilities (CVEs, misconfigs), controls (firewall, IDS, WAF), tools (nmap, burp_suite), protocols (TLS, OAuth2), frameworks (NIST CSF, MITRE ATT&CK)
- **47 Infrastructure Nodes:** Servers (web, app, db), networks (DMZ, internal, management), databases (Postgres, Redis, Elasticsearch), cloud resources (AWS, Azure, GCP, Kubernetes), monitoring (Prometheus, Grafana, ELK)
- **36 Incident Nodes:** Alerts (brute force, malware, data leak), logs (syslog, auth log, flow log), response actions (isolate, block, revoke), severity levels (critical through info)
- **23 Organization Nodes:** Teams (SOC, IR, DevOps), assets (PII, source code), policies (password, access control), compliance (SOC2, PCI, GDPR)

### Knowledge Base Topology

Figure 1: Four categories connected through threat-response, infrastructure-dependency, and governance edges.

```mermaid
graph TB
    subgraph "Security (71 nodes)"
        RANSOM["ransomware"]
        PHISH["phishing"]
        DDOS["ddos"]
        WAF["waf"]
        EDR["edr"]
        SIEM["siem"]
        MFA["mfa"]
        YARA["yara"]
        NIST["nist_csf"]
        PCI["pci_dss"]
    end

    subgraph "Infrastructure (47 nodes)"
        WEB["web_server_01"]
        APP["app_server_01"]
        DB["db_primary"]
        REDIS["redis_cache"]
        PROM["prometheus_server"]
        K8S["kubernetes_cluster"]
    end

    subgraph "Incident (36 nodes)"
        ALERT_M["alert_malware_detected"]
        ALERT_D["alert_ddos_spike"]
        ISOLATE["isolate_host"]
        BLOCK["block_ip"]
        SEV_C["severity_critical"]
    end

    subgraph "Organization (23 nodes)"
        SOC["soc_team"]
        IR["incident_response_team"]
        PII["customer_pii"]
        BACKUP["backup_vault"]
    end

    RANSOM --"mitigated_by"--> EDR
    RANSOM --"mitigated_by"--> WAF
    PHISH --"mitigated_by"--> MFA
    DDOS --"mitigated_by"--> EDR
    YARA --"detects"--> RANSOM

    EDR --"produces"--> ALERT_M
    ALERT_M --"triggers"--> ISOLATE
    ISOLATE --"executed_by"--> EDR

    ALERT_M --"classified_as"--> SEV_C
    SEV_C --"triggers"--> BLOCK

    SOC --"triages"--> ALERT_M
    IR --"responsible_for"--> ISOLATE
    PII --"protected_by"--> PCI
    BACKUP --"vulnerable_to"--> RANSOM
```

### Edge Label Taxonomy

| Category | Labels | Meaning |
|----------|--------|---------|
| **Threat Response** | `mitigated_by`, `detected_by`, `detects`, `tests` | How threats are countered |
| **Vulnerability Chain** | `enables`, `part_of` | How vulnerabilities lead to threats |
| **Infrastructure** | `depends_on`, `routes_to`, `part_of`, `hosts` | Service dependency graph |
| **Monitoring** | `monitors`, `collects`, `produces`, `notifies` | Observability pipeline |
| **Incident** | `triggers`, `classified_as`, `executed_by`, `assigned_to` | Alert-to-response chain |
| **Governance** | `requires`, `enforces`, `prevents`, `protected_by` | Policy-to-control mapping |

## 5. Analysis Pipeline

### Section 1: Knowledge Base Construction

Bulk-create 177 nodes across 4 categories with typed data, then wire them together with 251 semantic edges:

```python
mem = HypergraphMemory(evolve_interval=0)
_build_kb(mem)
```

**Result:** 177 nodes, 251 edges. Security is the largest category (71 nodes) because it includes threats, vulnerabilities, controls, tools, protocols, and frameworks.

### Section 2: Spreading Activation from "ransomware"

Energy propagates outward from the seed node through graph edges. Nodes directly connected to "ransomware" receive the highest activation:

```
encryption_at_rest    0.8273  depth=1
backup_vault          0.7710  depth=1
dlp                   0.6848  depth=1
yara                  0.5157  depth=1
customer_pii          0.3116  depth=2
gdpr                  0.2552  depth=2
```

13 results returned. Depth-1 results are directly connected to ransomware (mitigated_by, detected_by, vulnerable_to edges). Depth-2 results are two hops away (e.g., `customer_pii` → `encryption_at_rest` → `ransomware`).

### Section 3: Embedding Similarity

The `HashEmbeddingProvider` generates deterministic vectors from label hashes. This is a placeholder — it produces similarity scores that are not semantically meaningful:

```
gdpr               0.2472
ddos               0.2412
escalate_to_tier2  0.2255
terraform_state    0.2097
aws_s3_data        0.1957
```

These results illustrate the limitation: "ransomware" is most similar to "gdpr" and "ddos" under the hash embedding, which reflects hash collisions rather than semantic relationships. In production, a real embedding provider (sentence-transformers, OpenAI embeddings) would produce semantically coherent similarity rankings.

### Section 4: Reciprocal Rank Fusion

RRF merges the activation and similarity ranked lists into a single ranking:

```
gdpr                   0.0315
aws_s3_data            0.0303
yara                   0.0280
dlp                    0.0279
data_retention_policy  0.0252
backup_vault           0.0230
encryption_at_rest     0.0221
```

15 results returned. Items that rank well in both lists (e.g., `gdpr` at activation rank 6, similarity rank 1) score highest. Items strong in only one signal (e.g., `encryption_at_rest` at activation rank 1 but similarity rank 114) appear lower.

### Section 5: Recording Relevance Feedback

For each of 4 queries, the script marks 9 of the 15 retrieved results as relevant:

```
Query 'ransomware': 15 judgments, 9 relevant
Query 'phishing':   15 judgments, 9 relevant
Query 'ddos':       15 judgments, 9 relevant
Query 'zero_day':   15 judgments, 9 relevant
Total feedback records: 60
```

60 total judgments (15 results x 4 queries), with 36 marked relevant (9 per query).

### Section 6: Training the Learning-to-Rank Model

The LTR model learns feature weights from the 60 feedback samples:

```
Trained: True
Samples: 60
Learned feature weights:
  activation           +0.3971
  inverse_depth        +0.3182
  degree               +0.2130
  similarity           +0.0717
```

Activation (+0.40) and inverse_depth (+0.32) dominate — the model learned that graph-topology signals predict relevance better than hash-based embedding similarity (+0.07). The hash embedding produces nonsensical similarity rankings (ransomware ~ gdpr, ddos), so the model correctly downweights it relative to graph structure.

### Section 7: Retrieval Comparison (Before vs After LTR)

Comparing top-5 relevant hits between RRF (untrained) and LTR (trained):

| Query | RRF Hits | LTR Hits | Change |
|-------|----------|----------|--------|
| ransomware | 2/5 | 4/5 | +2 (promoted dlp, backup_vault) |
| phishing | 2/5 | 2/5 | 0 (swapped: promoted apache_access_log, internal_wiki; demoted iam, password_policy) |
| ddos | 3/5 | 3/5 | 0 (swapped: promoted ips; demoted alert_ddos_spike) |
| zero_day | 2/5 | 3/5 | +1 (promoted alert_privilege_escalation, xdr; demoted siem, buffer_overflow) |

LTR improved top-5 precision for 2 of 4 queries. The phishing and ddos queries show rank swaps without net improvement — the LTR model's learned weights produced different but equally effective top-5 sets. With only 60 training samples, per-query variation is expected.

### Section 8: Activation vs Embedding by Query Type

Comparing the top-5 results from activation and embedding for 5 different query types:

| Query | Type | Overlap |
|-------|------|---------|
| ransomware | threat-focused | 0/5 |
| db_primary | infrastructure-focused | 0/5 |
| severity_critical | classification-focused | 0/5 |
| soc_team | organizational-focused | 0/5 |
| oauth2 | protocol-focused | 0/5 |

Zero overlap across all query types. The hash embedding produces completely disjoint results from graph activation. This confirms the two signals capture orthogonal information — which is what RRF fusion exploits — but also confirms the hash embedding is not capturing semantic relationships a real embedding provider would.

### Section 9: Threat Chain Discovery via Reasoning

Transitive rules discover multi-hop attack chains that retrieval alone cannot find. A `TransitiveRule` on the `enables` label chains vulnerability-to-threat edges:

```python
mem.add_rules(TransitiveRule(edge_label="enables", new_label="enables_chain"))
result = mem.reason(seeds={"sql_injection", "phishing"}, max_depth=3, auto_commit=True)
```

In the 177-node graph, the `enables` edges form a star topology (vulnerabilities enabling individual threats) without two-hop chains, so the rule confirms existing relationships rather than discovering new ones. In denser threat graphs where vulnerabilities chain through shared CWEs or products, transitive reasoning uncovers attack paths invisible to single-hop retrieval.

**Why this matters:** Retrieval finds nodes connected to the query. Reasoning finds nodes connected to nodes connected to the query. For threat intelligence, this distinction separates "what is directly related" from "what is reachable through an attack chain."

### Section 10: Threat Cluster Identification

Community detection groups related threats with their mitigations and detection tools, enabling rapid identification of defense coverage gaps and attack surface clustering:

```
Communities detected: 25
Modularity: 0.6827
Coverage: 0.8008
  Cluster (36 nodes): buffer_overflow, rootkit, keylogger, zero_day, apt, supply_chain_attack
  Cluster (23 nodes): ransomware, insider_threat, data_exfiltration, misconfig_s3_bucket, dlp, encryption_at_rest
  Cluster (16 nodes): ddos, brute_force, credential_stuffing, cve_2023_44487, weak_tls, default_credentials
```

The largest cluster (36 nodes) groups advanced persistent threats with their detection tools. The second largest (23 nodes) clusters data-related threats with their defensive controls (DLP, encryption). These clusters reveal whether the knowledge base has adequate detection and mitigation coverage for each threat family.

**Why this matters:** A threat without mitigation or detection tools in its cluster represents a defense gap. Community detection surfaces these gaps by showing which threats are isolated from their controls.

### Section 11: Anomalous Threat Pattern Detection

Structural anomaly detection flags threats with unusual connectivity patterns:

```
zero_day              status=low_risk     boundary_score=0.0009
apt                   status=low_risk     boundary_score=0.1217
supply_chain_attack   status=low_risk     boundary_score=0.1217
ransomware            status=low_risk     boundary_score=0.1234
insider_threat        status=low_risk     boundary_score=0.1217
```

All threats classify as low_risk because the knowledge base models them with typical threat-control-response patterns. An anomalous threat would have unusual connectivity (e.g., connected to infrastructure but not to any controls or detection tools), indicating either a novel attack vector or a modeling gap.

**Why this matters:** In a real threat intelligence graph, anomalous threats warrant deeper investigation — they may represent emerging attack techniques that haven't been mapped to existing defenses.

## 6. Understanding Output

### Activation Score Interpretation

| Score Range | Meaning |
|-------------|---------|
| 0.7-1.0 | Directly connected to seed — strong associative link |
| 0.3-0.7 | 1-2 hops away — moderate association |
| 0.0-0.3 | 2-3 hops away — indirect association |
| 0.0 | Not reached within iteration limit |

### RRF Score Interpretation

| Score Range | Meaning |
|-------------|---------|
| 0.028+ | Ranked in top tier of both activation and similarity lists |
| 0.020-0.028 | Strong in one signal, moderate in the other |
| < 0.020 | Present in both lists but ranked lower in at least one |

### LTR Weight Interpretation

| Weight | Interpretation |
|--------|----------------|
| activation +0.40 | Graph topology is the strongest relevance predictor |
| inverse_depth +0.32 | Shallower (closer) nodes are more relevant |
| degree +0.21 | Better-connected nodes are moderately more relevant |
| similarity +0.07 | Hash embedding contributes minimally — not semantically meaningful |

## 7. Key Metrics

| Metric | Value |
|--------|-------|
| Graph nodes | 177 |
| Graph edges | 251 |
| Security nodes | 71 |
| Infrastructure nodes | 47 |
| Incident nodes | 36 |
| Organization nodes | 23 |
| Activation results (ransomware) | 13 |
| Top activation score | encryption_at_rest 0.8273 |
| RRF results (ransomware) | 15 |
| Top RRF score | gdpr 0.0315 |
| Feedback queries | 4 |
| Judgments per query | 15 |
| Relevant per query | 9 |
| Total feedback records | 60 |
| LTR training samples | 60 |
| LTR weight: activation | +0.3971 |
| LTR weight: inverse_depth | +0.3182 |
| LTR weight: degree | +0.2130 |
| LTR weight: similarity | +0.0717 |
| Activation/embedding overlap (5 queries) | 0/5 for all |
| Event log entries | 457 |
| Threat reasoning: states created | 1 |
| Threat reasoning: edges inferred | 0 |
| Threat communities detected | 25 |
| Threat community modularity | 0.6827 |
| Threat community coverage | 0.8008 |
| Anomaly detection: all threats | low_risk |

## 8. What Makes This Different

A keyword search for "ransomware" returns only nodes containing the word "ransomware." A vector similarity search returns nodes with similar labels. Neither captures the graph structure: what is ransomware connected to, and what are those connections connected to?

**Hyper3's multi-signal approach** combines three retrieval methods:

1. **Spreading activation** traverses the graph from the seed, finding nodes connected through semantic edges (ransomware → encryption_at_rest → customer_pii)
2. **Embedding similarity** finds nodes with similar vector representations, capturing semantic relatedness beyond graph topology
3. **RRF fusion** merges the two ranked lists without requiring score normalization
4. **Relevance feedback** records which results users mark as relevant
5. **Learning-to-rank** trains a model that weights each signal based on what actually predicts relevance

The feedback loop is the key difference from static retrieval. After 60 judgments across 4 queries, the LTR model learned that activation (+0.40) matters more than hash-based similarity (+0.07) for this domain. With a real embedding provider, the balance might shift — the model adapts to whatever signals are available.

## 9. Code Implementation

Building a retrieval system with relevance feedback in Hyper3 requires five steps.

**1. Build the Knowledge Base**

```python
mem = HypergraphMemory(evolve_interval=0)

for label in security_threats:
    mem.store(label, data={"type": "threat", "category": "security"})

mem.relate("ransomware", "encryption_at_rest", label="mitigated_by")
mem.relate("ransomware", "dlp", label="mitigated_by")
```

**2. Retrieve with Spreading Activation**

```python
activated = mem.activate("ransomware", energy=1.0, top_k=15, iterations=3)
for r in activated:
    print(f"{r.label}: activation={r.activation:.4f}, depth={r.depth}")
```

**3. Find Similar Concepts**

```python
similar = mem.find_similar("ransomware", top_k=15, threshold=-1.0)
for s in similar:
    print(f"{s.label_b}: similarity={s.similarity:.4f}")
```

**4. Retrieve with RRF Fusion**

```python
rrf_results = mem.retrieve("ransomware", top_k=15, iterations=3)
for r in rrf_results:
    print(f"{r.label}: rrf={r.rrf_score:.4f}, act={r.activation:.4f}, sim={r.similarity:.4f}")
```

**5. Record Feedback and Train**

```python
relevant = {"encryption_at_rest", "dlp", "edr", "backup_vault", ...}
mem.record_feedback("ransomware", rrf_results, relevant)

report = mem.train_retriever()
print(report["weights"])

results_after = mem.retrieve("ransomware", top_k=15, iterations=3, use_ltr=True)
```

## 10. Real-World Gap

**HashEmbeddingProvider is a placeholder.** It generates deterministic vectors from label hashes, producing similarity scores that reflect hash collisions rather than semantic relationships. The zero overlap between activation and embedding top-5 results (Section 8) and the LTR model's low similarity weight (+0.12) both reflect this limitation.

Production deployment would require:

1. **Real embeddings:** Replace `HashEmbeddingProvider` with sentence-transformers, OpenAI embeddings, or domain-specific models via `mem.set_embedding_provider(provider)`
2. **Larger feedback corpus:** 60 samples is minimal. Production LTR models benefit from thousands of relevance judgments across diverse query types
3. **Query expansion:** The current system retrieves from single seed concepts. Real retrieval often involves multi-concept queries with query expansion
4. **Evaluation framework:** This showcase uses per-query relevance sets. Production needs held-out test sets, MAP/NDCG metrics, and statistical significance testing
5. **Online learning:** The current model trains once on batch feedback. Production systems update incrementally as new feedback arrives

## 11. Reference

### Key API Methods

| Method | Purpose |
|--------|---------|
| `mem.store(label, data)` | Create a node with metadata |
| `mem.relate(source, target, label)` | Create a semantic edge |
| `mem.activate(seed, energy, top_k, iterations)` | Spreading activation retrieval |
| `mem.find_similar(seed, top_k, threshold)` | Embedding-based similarity retrieval |
| `mem.retrieve(seed, top_k, iterations)` | RRF fusion of activation and similarity |
| `mem.record_feedback(query, results, relevant_set)` | Record relevance judgments |
| `mem.train_retriever()` | Train LTR model from feedback |
| `mem.retrieve(seed, top_k, iterations, use_ltr=True)` | Retrieve using trained LTR model |
| `mem.stats()` | Get graph statistics |
| `mem.set_embedding_provider(provider)` | Replace the default embedding provider |

### Related Examples

| Example | Focus |
|---------|-------|
| `examples/showcase/threat_intelligence/knowledge_basics.py` | Threat intel graph with pattern matching, centrality |
| `examples/showcase/microservices_reasoning/reasoning_walkthrough.py` | Transitive/inverse rule inference on microservices |
| `examples/showcase/network_analytics/graph_analytics.py` | Centrality, cycles, components, risk scoring |
| `examples/showcase/self_evolving_cognition/self_evolving_cognition.py` | Feedback-driven evolution, metamorphosis |
