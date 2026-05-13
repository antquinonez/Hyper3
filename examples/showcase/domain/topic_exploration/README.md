# Explore a Research Topic with ConceptSet

> Chainable concept exploration on a climate knowledge graph: traversal, causal chains, centrality, coverage gaps, and evidence mapping.

## 1. What this example teaches

This is the most "analysis notebook" style domain showcase. It shows how to use ConceptSet pipelines to:

- expand from a seed concept
- trace causal paths
- rank by centrality
- detect adaptation and evidence gaps
- run transitive reasoning to materialize indirect causes

## 2. Run

```bash
.venv/bin/python examples/showcase/domain/topic_exploration/topic_exploration.py
```

## 3. Current validated metrics

Current run output:

- initial graph: 77 nodes, 116 edges
- final graph after inference: 77 nodes, 149 edges
- direct `causes` edges: 37
- inferred `indirectly_causes` edges: 33
- connected components: 1

Domain counts:

- phenomena: 20
- drivers: 15
- impacts: 15
- solutions: 15
- measurements: 12

## 4. Walkthrough

### Section 1-2: Build graph and relationships

Stores typed concept nodes with metadata, then adds labeled relationships (`causes`, `contributes_to`, `mitigates`, `evidence_for`, etc.).

### Section 3: Seeded exploration

Starts from `global_warming` and expands first- and second-order neighborhoods through ConceptSet chaining.

### Section 4: Causal chain discovery

Uses `paths_to()` from source concepts into specific impacts (e.g., `co2_emissions -> coastal_flooding`).

### Section 5: Multi-hop impact slices

Shows strict label-constrained traversal (`edge_label="causes"`) and downstream expansion from critical-impact nodes.

### Section 6: Centrality-guided prioritization

Ranks neighborhood concepts with degree and PageRank to identify high-leverage concepts.

### Section 7: Solution coverage gaps

Computes impacts directly addressed by adaptation solutions, then reports uncovered impacts.

### Section 8: Feedback loops

Checks 2-hop loopback behavior for feedback-category concepts.

### Section 9: Transitive causal inference

Runs:

```python
mem.reason.add_rules(TransitiveRule(edge_label="causes", new_label="indirectly_causes"))
result = mem.reason(
    seeds={...},
    max_depth=4,
    max_total_states=80,
)
```

with `TransitiveRule(edge_label="causes", new_label="indirectly_causes")` to materialize indirect links.

### Section 10-11: Cross-domain spread + evidence mapping

- multi-hop spread from an emissions driver across domain boundaries
- evidence coverage of phenomena (`evidence_for`)

## 5. Mermaid (representative)

```mermaid
graph LR
    CO2[1) co2_emissions] -->|causes| GH[greenhouse_effect]
    GH -->|causes| GW[2) global_warming]
    GW -->|causes| SLR[sea_level_rise]
    SLR -->|causes| CF[3) coastal_flooding]
    SW[4) sea_wall_construction] -->|mitigates| CF
    SAT[5) satellite_temperature] -->|evidence_for| GW
```

How to read it:

- Path 1->2->3 is the causal chain that `paths_to()` and transitive reasoning make explicit.
- Node 4 is an intervention point on downstream impact, not on the upstream driver directly.
- Node 5 is evidentiary support for a phenomenon, enabling evidence-gap analysis separate from causal structure.

## 6. How To Use ConceptSet Effectively

- Keep chains short and inspect intermediate sets; long chains are powerful but can hide where noise enters.
- Use label-constrained neighbors (`edge_label=...`) when asking causal questions; unconstrained expansion is better for discovery.
- Pair centrality ranking with domain filters to avoid over-prioritizing structurally large but low-actionability concepts.
- Use set differences (`all - evidenced`, `all - addressed`) for explicit gap detection workflows.

### ConceptSet Chain Output

Each ConceptSet method returns a new ConceptSet. The `.labels` property extracts the final list of deduplicated concept names.

| Method | Returns | Chain continues? |
|--------|---------|-----------------|
| `.neighbors()` | ConceptSet | Yes |
| `.paths_to()` | ConceptSet | Yes |
| `.similar()` | ConceptSet | Yes |
| `.activate()` | ConceptSet | Yes |
| `.diffuse()` | ConceptSet | Yes |
| `.query()` | ConceptSet | Yes |
| `.top(k)` | ConceptSet | Yes |
| `.filter(fn)` | ConceptSet | Yes |
| `.threshold(min)` | ConceptSet | Yes |
| `.exclude(...)` | ConceptSet | Yes |
| `.unique()` | ConceptSet | Yes |
| `.centrality()` | ConceptSet | Yes |
| `.communities()` | CommunityResult | No (terminal) |
| `.anomalies()` | list | No (terminal) |
| `.describe()` | GraphDescription | No (terminal) |
| `.labels` | list[str] | No (terminal) |
| `.scores` | dict[str, float] | No (terminal) |
| `.items` | list[tuple] | No (terminal) |

### Centrality Score Interpretation

| Score Range | Meaning |
|-------------|---------|
| 0.25+ | Central hub — connects to a large fraction of the graph |
| 0.10-0.25 | Important connector — significant structural role |
| 0.05-0.10 | Moderate — notable but not dominant |
| Below 0.05 | Peripheral — limited connectivity |

### Impact Irreversibility

Irreversibility scores range from 0.3 to 0.9 and represent how difficult it is to reverse an impact once it occurs.

| Score Range | Meaning |
|-------------|---------|
| 0.8-0.9 | Near-permanent — extremely difficult to reverse |
| 0.5-0.7 | Significant — costly or slow to reverse |
| 0.3-0.4 | Moderate — reversible with targeted intervention |

## 7. API Methods

| Method | Layer | Purpose |
|--------|-------|---------|
| `mem.add(label, data)` | 1 (Data) | Create a concept node with metadata |
| `mem.link(source, target, label)` | 1 (Data) | Create a labeled relationship edge |
| `mem.find(label)` / `mem.find(data=...)` | 3 (ConceptSet) | Entry point for chainable exploration |
| `mem.info(label)` | 1 (Data) | Get node metadata (used heavily for display) |
| `mem.neighbors(label, ...)` | 1 (Data) | Get neighbor labels |
| `cs.neighbors()` | 3 (ConceptSet) | Expand ConceptSet to neighbors |
| `cs.paths_to(target)` | 3 (ConceptSet) | Find path concepts between set and target |
| `cs.top(k)` / `cs.filter(fn)` / `cs.exclude(...)` | 3 (ConceptSet) | Narrow the concept set |
| `cs.unique()` | 3 (ConceptSet) | Deduplicate, keeping best score |
| `cs.centrality(method)` | 3 (ConceptSet) | Score by graph centrality |
| `cs.labels` / `cs.scores` / `cs.items` | 3 (ConceptSet) | Terminal extraction |
| `mem.reason.add_rules(TransitiveRule(...))` | 2 (Reason) | Register transitive inference rule |
| `mem.reason(seeds, max_depth, ...)` | 2 (Reason) | Apply rules via multiway expansion |
| `mem.pattern_match(edge_label)` | 1 (Data) | Find edges by label |
| `mem.analyze.edges()` | 1 (Data) | Iterate all edges (for label filtering) |
| `mem.stats()` | 1 (Data) | Graph statistics |
| `mem.size` | 1 (Data) | Tuple of (node_count, edge_count) |

## 8. Related Examples

| Example | Focus |
|---------|-------|
| `examples/showcase/domain/code_dependency_analysis/` | Dependency blast radius with centrality, cycles, subgraph collapse |
| `examples/showcase/domain/microservices_reasoning/` | Microservice blast radius with TransitiveRule and InverseRule |
| `examples/showcase/core/centrality_and_ranking/` | Degree, betweenness, PageRank, and eigenvector centrality |

## 9. Real-world gap

Production research graph workflows still require:

- literature ingestion and relation extraction pipelines
- concept normalization/ontology mapping across disciplines
- temporal versioning of evolving evidence
- provenance and confidence scoring on edges
