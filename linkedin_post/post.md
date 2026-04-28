# The Problem With Disconnected Threat Intelligence

Your SIEM generates alerts. Your threat feeds give you IOCs. Your vulnerability
scanner gives you CVEs. Your CTI team tracks APT groups.

Each of these lives in its own silo. The relationships between them -- which
APT group exploits which CVE, using which malware, targeting which sector --
exist only in analysts' heads and spreadsheets.

When a new CVE drops (Log4j, MOVEit, PAN-OS), the first question is always the
same: *who does this affect and how?* Answering that means cross-referencing
dozens of sources, each in a different format, with different identifiers,
maintained by different teams.

This is a graph problem. The data points are nodes. The relationships between
them are edges. The questions analysts need answered are graph queries.

---

## The Approach: A Self-Contained Knowledge Graph

Hyper3 is a Python library that treats threat intelligence as what it is: a
hypergraph. Threat actors, CVEs, malware families, TTPs, infrastructure, and
target sectors are nodes. The relationships between them -- exploits, uses,
targets, communicates_with, attributed_to -- are labeled, weighted edges.

Three dependencies: numpy, scipy, networkx. No database. No API calls. No LLM.
Runs on a laptop.

```python
from hyper3 import CognitiveMemory

mem = CognitiveMemory()

mem.store("APT28", data={"origin": "Russia", "sophistication": "high"})
mem.store("CVE-2023-44228", data={"cvss": 10.0, "product": "Apache_Log4j2"})
mem.relate("APT28", "CVE-2023-44228", label="exploits")
mem.relate("APT28", "GOV", label="targets")
```

Store concepts. Connect them with labeled relationships. Then ask questions.

---

## Six Capabilities, One Graph

I built a 73-node, 122-edge threat intelligence graph from publicly available
CTI data -- 21 threat actors, 10 CVEs, 14 malware families, 7 TTPs, 7
infrastructure nodes, 11 target sectors, plus 3 stale IOCs. Then I applied
six different analytical approaches to answer the questions a SOC analyst needs
answered at 2 AM.

### 1. Rule-Based Inference

InverseRule creates reverse-lookup edges automatically. For every
APT-[exploits]->CVE, it creates CVE-[exploited_by]->APT. AbductiveRule
generates attribution hypotheses from targeting patterns.

```
States explored:    32
Rules applied:      31
New edges inferred: 31
```

Result: "Who exploits Log4j?" is now a direct edge-label query, not a graph
traversal. 31 new edges discovered in under a second.

### 2. Spreading Activation for Alert Triage

Stimulate CVE-2023-44228 with energy=1.0. Energy propagates through
relationship edges. The nodes that light up are structurally relevant --
even if they're several hops away.

```
Activated threat actors (16):
  APT28                   energy=0.477
  Lazarus                 energy=0.373
  Volt_Typhoon            energy=0.366
  Fancy_Bear              energy=0.242

Affected sectors (6):
  GOV                     energy=0.521
  MIL                     energy=0.214
  FIN                     energy=0.204
```

One graph operation replaces an analyst manually cross-referencing MITRE ATT&CK,
CISA KEV, and internal threat feeds.

### 3. Quantum-Inspired Attribution Ranking

Four suspects, weighted by CTI reporting. The system holds all four as a
superposition with probability amplitudes, then collapses via Born-rule
sampling.

```
Prior distribution:
  APT28         probability=0.607
  APT29         probability=0.168
  Lazarus       probability=0.143
  Volt_Typhoon  probability=0.081

Collapse frequency over 1000 trials:
  APT28         605 (60.5%)   ############################################################
  APT29         171 (17.1%)   #################
  Lazarus       138 (13.8%)   #############
  Volt_Typhoon   86 (8.6%)   ########
```

The distribution matches the priors. Add context (e.g., evidence favoring APT28
with weight 3.0) and the collapse shifts to 84.8% APT28 -- the system updates
its beliefs based on evidence.

This is Born-rule sampling over density matrices -- mathematically rigorous
quantum probability applied to a practical attribution problem.

### 4. Self-Evolution

The graph tracks which nodes are accessed. Evolution decays weights on unused
edges, prunes below-threshold nodes, merges equivalent concepts, and reinforces
frequently-used paths.

Three stale IOCs (weight=0.05, access_count=0) were pruned automatically.
44 equivalent nodes were merged (actors with identical data and structural
overlap). The graph gets smaller and more focused as it evolves.

```
Before: 94 nodes, 153 edges
After:  47 nodes, 153 edges
  Pruned:  3 stale IOCs
  Merged: 44 equivalent nodes
```

### 5. Centrality and Pattern Matching

Degree centrality on the relationship graph -- not just the vulnerability
database. A node's danger is proportional to how many attack paths pass through
it.

```
Top 5 most connected threat actors:
  1. APT28     centrality=0.8696   exploits=8  targets=9  uses=10
  2. APT41     centrality=0.5435   exploits=6  targets=7  uses=6
  3. FIN6      centrality=0.4783   exploits=5  targets=7  uses=7

Top 5 most connected CVEs:
  1. CVE-2023-44228   centrality=0.3696   CVSS=10.0   Apache_Log4j2
  2. CVE-2024-3400    centrality=0.1087   CVSS=10.0   PAN-OS
  3. CVE-2023-20198   centrality=0.0435   CVSS=10.0   Cisco_IOS_XE_WebUI
```

APT28's full profile subgraph: 16 nodes, 38 edges. One method call extracts
the complete operational picture around any threat actor.

---

## What Makes This Different From a Database

Graph databases (Neo4j, TigerGraph) solve the storage and query problem.
Hyper3 adds active processing on top of the graph:

- **Rule-based inference** discovers indirect relationships (InverseRule,
  AbductiveRule, TransitiveRule, CompositionRule -- 8 rule types built in)
- **Spreading activation** finds structurally relevant nodes through energy
  propagation -- no manual cross-referencing needed
- **Self-evolution** prunes stale data, merges duplicates, reinforces active
  paths -- the graph improves with use
- **Born-rule collapse** ranks competing hypotheses with rigorous probability --
  weighted Bayesian sampling using density matrices

None of this requires a GPU, a cloud service, or an API key.

---

## The Bigger Picture

Threat intelligence is a graph problem masquerading as a data problem. The
industry's answer has been more feeds, more dashboards, more alerts. But the
value isn't in the data points -- it's in the relationships between them.

Hyper3 represents those relationships natively, then provides the analytical
tools to exploit them: inference rules, spreading activation, centrality,
pattern matching, subgraph extraction, and self-evolution.

The full 6-section example above runs in under 2 seconds on a laptop with
3 pip dependencies.

---

## Try It

```bash
pip install hyper3
```

The threat intelligence example is a single self-contained script:
`examples/domain/threat_intel_full_chain.py`

---

*Hyper3 is a hypergraph kernel library for knowledge representation and
reasoning. Pure Python, three dependencies, zero external services.*
