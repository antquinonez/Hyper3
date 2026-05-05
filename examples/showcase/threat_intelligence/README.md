# Threat Intelligence Knowledge Base

A comprehensive showcase demonstrating how to build and query a cyber threat intelligence knowledge graph using Hyper3's hypergraph capabilities.

## Overview

This example creates a realistic threat intelligence graph with 100+ nodes and 200+ edges representing:

- **30+ Threat Actors** (APT groups, ransomware operators)
- **30 CVEs** (vulnerabilities with CVSS scores from 2023-2024)
- **20 Malware families** (RATs, ransomware, trojans, backdoors)
- **25 TTPs** (MITRE ATT&CK tactics and techniques)
- **15 Infrastructure nodes** (C2 servers, botnets, exfiltration servers)
- **14 Target industries** (government, energy, financial, etc.)

## Key Concepts Demonstrated

| Concept | Description |
|---------|-------------|
| **Multi-modal storage** | Nodes stored with different modalities (CAUSAL, SENSORY, CONCEPTUAL, ABSTRACT) |
| **Relationship modeling** | Six edge types: `uses`, `exploits`, `targets`, `variant_of`, `communicates_with`, `attributed_to`, `mitigates`, `uses_tactic` |
| **Neighborhood traversal** | `recall()` with depth and node limits |
| **BFS traversal** | `query()` with strategy="bfs" for controlled exploration |
| **Pattern matching** | `pattern_match()` to find edges by label or source |
| **Centrality analysis** | `degree_centrality()` to find most-connected CVEs |
| **Subgraph extraction** | `subgraph()` to isolate a threat actor's full profile |
| **Path finding** | `find_paths()` to trace attack chains |
| **Component analysis** | `connected_components()` to identify threat ecosystems |
| **Modality filtering** | Query with modality constraints (CAUSAL, SENSORY, CONCEPTUAL) |

## Running the Example

```bash
.venv/bin/python examples/showcase/threat_intelligence/knowledge_basics.py
```

## Output Sections

1. **Building the Knowledge Base** - Bulk node/edge creation
2. **Recall and Neighborhood Traversal** - Exploring Lazarus group's connections
3. **Pattern Matching for Attack Chains** - Linking CVEs to target industries
4. **Top 5 Most Connected CVEs** - Centrality-based ranking
5. **Subgraph Extraction** - APT28's complete profile
6. **Attack Paths** - Tracing Lazarus to Financial sector, Volt Typhoon to Energy
7. **Isolated Indicators** - Finding nodes needing enrichment
8. **Connected Components** - Mapping threat ecosystems
9. **Modality-Filtered Traversal** - Exploring from Log4j CVE by modality

## Use Case

A security operations center (SOC) analyst needs to:
- Understand which CVEs are most heavily linked to active threat actors
- Find isolated indicators that lack context
- Trace attack paths from specific APT groups to targeted industries
- Identify which threat ecosystems are connected through shared infrastructure or malware

## Requirements

- Hyper3 installed in editable mode (`.venv/bin/pip install -e ".[dev]"`)
- No external dependencies beyond the core Hyper3 package
