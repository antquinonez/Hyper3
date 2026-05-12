# Knowledge Graph from Security Incident Reports

> Extracting structured entities and relations from unstructured security text using regex extraction, manual indicator enrichment, and a pluggable LLM provider interface.

## 1. The Approach

Security incident reports contain unstructured text with embedded technical indicators: IP addresses, CVE identifiers, MITRE technique codes, file hashes, domains, and file paths. These indicators live in plain English sentences like "The threat actor used CVE-2024-3094 to compromise the build server at 10.0.1.50" -- readable by analysts, but invisible to structured analysis tools.

Text enrichment extracts these entities from prose and loads them into a knowledge graph, connecting textual intelligence to graph-based traversal, pattern matching, and multi-hop reasoning. Without this extraction step, the knowledge in incident reports remains locked in unstructured text.

This showcase demonstrates a two-stage approach:

1. **Built-in RegexExtractor** for general English patterns (causes, leads_to, is_part_of) and noun phrases
2. **Manual domain-specific regex** for technical indicators the built-in extractor misses (IPs, CVEs, hashes), plus a pluggable `LLMProvider` interface for swapping in a real NER model

The showcase is honest about what regex-based extraction catches versus misses.

## 2. A Simple Analogy

Imagine reading 16 police reports and highlighting every license plate, phone number, and address in yellow, then drawing lines between related items on a corkboard. Regex extraction is the yellow highlighter -- it finds structured patterns in text. The knowledge graph is the corkboard with strings connecting related entities.

The built-in highlighter catches names and general relationships ("Person A caused Incident B"). But it cannot highlight license plates or phone numbers -- those need a domain-specific highlighter. This showcase uses both.

## 3. Key Concepts

| Concept | Plain English |
|---|---|
| RegexExtractor | Built-in text parser that finds noun phrases and relation patterns (X causes Y) using regular expressions |
| Technical indicator | A structured entity in security text: IP address, CVE ID, file hash, MITRE technique, domain, URL |
| LLMProvider | Pluggable interface for text extraction backends. Swap regex for a real NER model without changing application code |
| Knowledge graph enrichment | Adding extracted entities as nodes and their relationships as edges in the hypergraph |
| `ingest_batch()` | Processes multiple text documents, extracting entities and relations into the graph in one call |
| `ensure()` | Creates a node only if it does not already exist, avoiding duplicates during enrichment |
| `pattern_match()` | Queries the graph for edges matching a specific label, returning source/target pairs |

## 4. Quick Start

```bash
.venv/bin/python examples/showcase/retrieval/text_enrichment/07_text_enrichment.py
```

```
======================================================================
SUMMARY
======================================================================
  Final graph: 98 nodes, 19 edges
  Connected components: 79
  Has cycles: False
  Incident reports processed: 16
  Entity types discovered: 9 categories
```

## 5. The Scenario

The script processes 16 synthetic security incident reports covering a range of attack types: supply chain compromise, phishing, credential harvesting, ransomware, reconnaissance, SQL injection, lateral movement, rootkit deployment, DNS tunneling, web shell deployment, Bluetooth exploitation, VPN abuse, incident response, and cryptocurrency mining.

Each report is 2-3 sentences containing a mix of narrative text and embedded technical indicators:

```
Report 1: On 2025-01-15 the threat actor used CVE-2024-3094 to compromise the
build server at 10.0.1.50. The attacker exploited a supply chain vulnerability
in the compression library.

Report 2: Malicious payload 4a2b8c3d1e5f6a7b8c9d0e1f2a3b4c5d was delivered via
phishing email from attacker@c2-domain.xyz. The malware communicates with
192.168.45.100 on port 4444 using technique T1059.001.
```

The 9 categories of technical indicators present across all reports:

| Category | Occurrences | Unique |
|---|---|---|
| mitre_technique | 10 | 10 |
| ip_address | 8 | 8 |
| cve_id | 4 | 4 |
| sha256_hash | 4 | 4 |
| domain | 4 | 4 |
| file_path_unix | 4 | 4 |
| file_path_windows | 3 | 3 |
| email | 1 | 1 |
| url | 1 | 1 |

## 6. Analysis Pipeline

### Section 1: Load Reports

The 16 incident reports are loaded as plain strings. No preprocessing or tokenization is applied.

### Section 2: Built-in RegexExtractor

`ingest_batch()` processes all 16 reports through the built-in `RegexExtractor`, which finds:

- Capitalized noun phrases (Cobalt Strike, Mimikatz, Active Directory)
- General English relation patterns (X causes Y, X is associated with Y, X leads to Y)
- Quoted terms and appositions

This produces **78 entity mentions** and **11 relations** across **74 unique nodes**.

Sample extracted relations:
```
The beacon --[causes]--> a C2 channel to
The exfiltration --[leads_to]--> regulatory notification requirements
This reconnaissance --[is_part_of]--> technique T1087
Each query --[contains]--> encoded data in the
```

These relations are grammatically correct but often include surrounding words in the entity labels ("The beacon" rather than "beacon"). The built-in extractor works on sentence structure, not domain semantics.

### Section 3: What RegexExtractor Caught vs Missed

This is where the honesty matters. Of the 39 unique technical indicators present in the reports, the built-in extractor caught approximately **17** and missed approximately **22**.

What it caught: CVE IDs and MITRE technique IDs that happened to appear as part of noun phrases or within matched relation patterns. These were incidental catches, not intentional extraction.

What it missed (examples):
```
[ip_address] 203.0.113.50
[ip_address] 10.0.3.100
[ip_address] 10.0.1.50
[ip_address] 198.51.100.23
[sha256_hash] 9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b
[sha256_hash] a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

IP addresses, file hashes, domains, and file paths are invisible to the built-in extractor because they do not match English noun-phrase or relation patterns. This is not a bug -- it is the expected behavior of a general-purpose regex parser applied to domain-specific text.

**Why this matters**: If you rely on the built-in extractor alone for security text, you lose over half the indicators. The extraction must be supplemented with domain-specific patterns or a real NER model.

### Section 4: Manual Technical Indicator Extraction

Domain-specific regex patterns extract the indicators the built-in extractor misses:

```python
patterns = {
    "ip_address": r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}...',
    "cve_id": r'\bCVE-\d{4}-\d{4,7}\b',
    "mitre_technique": r'\bT\d{4}(?:\.\d{3})?\b',
    "sha256_hash": r'\b[a-f0-9]{32,64}\b',
    ...
}
```

Each extracted indicator is added to the graph via `ensure()` (idempotent -- no duplicates), and domain-specific relations connect them:

- `communicated_with` between IPs and domains
- `exploited_via` between IPs and CVEs
- `maps_to` between MITRE techniques and CVEs
- `found_at` between hashes and file paths

After manual enrichment, the graph grows from 74 nodes to **98 nodes** and from 11 edges to **19 edges**.

### Section 5: Querying the Knowledge Graph

Three example queries demonstrate graph traversal:

```
recall('CVE-2024-3094', max_depth=2) -> 2 nodes
  Neighbors: ['CVE-2024-3094', '10.0.1.50']
recall('10.0.1.50', max_depth=2) -> 2 nodes
  Neighbors: ['10.0.1.50', 'CVE-2024-3094']
recall('T1059.001', max_depth=2) -> 1 nodes
  Neighbors: ['T1059.001']
```

CVE-2024-3094 and 10.0.1.50 are connected via the `exploited_via` relation. T1059.001 appears in the graph but has no neighbors within depth 2 because the built-in extractor's noun-phrase matches do not link to it.

`pattern_match()` finds specific relation types:

```
'causes' relationships (2):
  The beacon causes a C2 channel to
  The exploitation causes remote code execution and

'exploited_via' relationships (2):
  10.0.1.50 exploited_via CVE-2024-3094
  10.0.3.100 exploited_via CVE-2024-5678
```

The `causes` relations come from the built-in extractor (with noisy labels). The `exploited_via` relations come from manual enrichment (with clean labels). Both coexist in the same graph.

### Section 6: Pluggable LLMProvider

The `LLMProvider` interface defines a single method -- `complete(prompt)` -- that any extraction backend can implement. The showcase demonstrates with a mock `SecurityNERProvider` that returns structured entity JSON:

```
Report 1: [('CVE-2024-3094', 'vulnerability')]
Report 2: [('T1059.001', 'mitre_technique')]
Report 3: [('T1053.005', 'mitre_technique'), ('Cobalt Strike', 'tool')]
```

The mock uses a hardcoded lookup table. In production, `complete()` would call a real NER model, returning structured entities with types (vulnerability, tool, technique) that the built-in regex extractor cannot determine.

**Why the pluggable interface matters**: Application code calls `ingest_batch()` the same way regardless of which provider is active. Switching from regex to a fine-tuned NER model or an LLM API requires implementing `LLMProvider`, not rewriting the enrichment pipeline.

### Section 7: Honest Assessment

The script provides its own summary:

- Built-in RegexExtractor: zero dependencies, good at generic English patterns, cannot parse structured identifiers
- Manual regex: catches all technical indicators, but each pattern must be written and maintained by hand
- LLMProvider: the extension point for production-quality extraction

## 7. Understanding Output

### Extraction coverage

| Metric | Value |
|---|---|
| Technical indicators in reports | 39 unique |
| Caught by built-in RegexExtractor | ~17 |
| Caught by manual domain regex | 39 |
| Missed by built-in extractor | ~22 |

### Graph connectivity

The final graph has **79 connected components** for 98 nodes, meaning most nodes are isolated or in small clusters. This reflects the extraction reality: many indicators appear once, connected to one or two other entities, with no cross-report linking. The 16 reports describe separate incidents with limited overlap.

### Relation quality comparison

| Source | Relations | Label quality |
|---|---|---|
| Built-in RegexExtractor | 11 | Noisy (includes function words: "The beacon", "a C2 channel to") |
| Manual enrichment | 8 | Clean (structured: `exploited_via`, `communicated_with`, `maps_to`, `found_at`) |

## 8. Key Metrics

| Metric | Value |
|---|---|
| Incident reports processed | 16 |
| Entity mentions (built-in extractor) | 78 |
| Relations (built-in extractor) | 11 |
| Nodes after built-in extraction | 74 |
| Edges after built-in extraction | 11 |
| Technical indicator categories | 9 |
| Unique technical indicators | 39 |
| Indicators caught by built-in | ~17 |
| Indicators missed by built-in | ~22 |
| Nodes after manual enrichment | 98 |
| Edges after manual enrichment | 19 |
| Connected components | 79 |
| Has cycles | False |
| `causes` relations | 2 |
| `exploited_via` relations | 2 |

## 9. What Makes This Different

**Pluggable extraction via LLMProvider** -- The `LLMProvider` interface decouples extraction logic from graph construction. Implement `complete(prompt)` with any backend (regex, spaCy, HuggingFace, commercial LLM) and the rest of the pipeline -- `ingest_batch()`, `ensure()`, `relate()` -- works identically. This matters because extraction requirements vary widely by domain, but the graph-building code should not.

**Two-stage enrichment** -- The built-in RegexExtractor handles general English text (noun phrases, relation patterns) without configuration. Domain-specific extraction adds structured indicators on top. Both contribute to the same graph, and queries like `pattern_match()` and `recall()` return results from both sources.

**Honest gap analysis** -- The script explicitly measures what the built-in extractor misses and reports the numbers. The ~22 missed indicators are not hidden -- they are printed with their categories. This matters because the gap between "extracted something" and "extracted everything relevant" determines whether the knowledge graph is useful for real analysis.

## 10. Code Implementation

### Built-in extraction

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
results = mem.ingest_batch(reports, extract=True, deduplicate=True)

total_entities = sum(len(r.entities) for r in results)
total_relations = sum(len(r.relations) for r in results)
```

### Domain-specific indicator extraction and graph enrichment

```python
import re

def extract_technical_indicators(text):
    patterns = {
        "ip_address": r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b',
        "cve_id": r'\bCVE-\d{4}-\d{4,7}\b',
        "mitre_technique": r'\bT\d{4}(?:\.\d{3})?\b',
        "sha256_hash": r'\b[a-f0-9]{32,64}\b',
    }
    return {k: re.findall(p, text, re.IGNORECASE) for k, p in patterns.items()
            if re.findall(p, text, re.IGNORECASE)}

for report in reports:
    indicators = extract_technical_indicators(report)
    for category, values in indicators.items():
        for value in values:
            mem.ensure(value, data={"type": category, "source": "manual_regex"})
    for ip in indicators.get("ip_address", []):
        for cve in indicators.get("cve_id", []):
            mem.link(ip, cve, label="exploited_via")
```

### Pluggable LLMProvider

```python
from hyper3 import HypergraphMemory, LLMProvider

class SecurityNERProvider(LLMProvider):
    def complete(self, prompt: str) -> str:
        return call_real_ner_model(prompt)

mem = HypergraphMemory(evolve_interval=0)
mem.set_llm_provider(SecurityNERProvider())
results = mem.ingest_batch(reports, extract=True, deduplicate=True)
```

### Querying the enriched graph

```python
recalled = mem.recall("CVE-2024-3094", max_depth=2)
causes_edges = mem.pattern_match(edge_label="causes")
exploited_edges = mem.pattern_match(edge_label="exploited_via")
```

## 11. Real-World Gap

**Regex extraction is not NER.** The built-in RegexExtractor finds English noun phrases and relation patterns. It does not perform named entity recognition, coreference resolution, or domain classification. For security text, it misses the majority of technical indicators. The manual regex patterns catch structured identifiers, but each pattern must be hand-written and maintained.

**No cross-report entity resolution.** The same attacker, tool, or infrastructure may appear in multiple reports under different names. The showcase does not deduplicate across reports beyond string matching. "The threat actor" in report 1 and "The attacker" in report 2 may be the same entity, but the graph treats them as separate nodes.

**No document chunking or long-text handling.** Each report is 2-3 sentences. Real incident reports span pages. Processing longer documents requires chunking, context window management, and cross-chunk entity linking, none of which this showcase addresses.

**The LLMProvider is a mock.** The `SecurityNERProvider` returns hardcoded entity lookups. Production use requires integrating a real NER model (spaCy custom NER, HuggingFace token classifier, or LLM API). The interface is designed for this swap, but the implementation is not included.

**No relation normalization.** The built-in extractor produces noisy relation labels ("The beacon causes a C2 channel to"). Manual enrichment produces clean labels (`exploited_via`). The graph stores both without normalization. A production pipeline would need relation canonicalization.

**Scale is untested.** The showcase processes 16 short reports producing 98 nodes. Real security operations process thousands of reports daily. Performance at scale depends on the extraction backend, not the graph construction.

## 12. Reference

### API Methods

| Method | Purpose |
|---|---|
| `HypergraphMemory(evolve_interval=0)` | Create a memory instance with auto-evolution disabled for deterministic behavior |
| `mem.ingest_batch(texts, extract=True, deduplicate=True)` | Process multiple texts, extracting entities and relations into the graph |
| `mem.ensure(label, data={...})` | Create a node only if absent; idempotent for batch enrichment |
| `mem.link(source, target, label=..., weight=...)` | Create a directed edge between two concepts |
| `mem.recall(concept, max_depth=N)` | Traverse the graph from a concept, returning reachable nodes |
| `mem.pattern_match(edge_label=...)` | Find all edges matching a specific relation label |
| `mem.set_llm_provider(provider)` | Set a custom `LLMProvider` for text extraction |
| `mem.stats()` | Return graph statistics (nodes, edges, components, cycles) |

### Types

| Type | Description |
|---|---|
| `ExtractionResult` | Returned by `ingest_batch()`: contains `.entities` and `.relations` lists |
| `LLMProvider` | Abstract base class with a single `complete(prompt) -> str` method |
