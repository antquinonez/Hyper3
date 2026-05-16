# Clinical Diagnosis Knowledge Graph Showcase

> Backward chaining, contradiction handling, confidence propagation, and probabilistic differential diagnosis on a 92-node clinical graph.

**What you will learn:**

- How to construct a typed clinical knowledge graph with diseases, symptoms, labs, imaging, risk factors, and medications
- How backward chaining from candidate diagnoses to observed evidence exposes missing premises and ranks a differential
- How a combined coverage + proof-confidence scoring metric separates leading diagnoses from plausible alternatives
- How contradiction detection and belief revision resolve opposing clinical evidence edges automatically
- How Born-rule probabilistic sampling represents diagnostic uncertainty as a superposition collapsed by context
- How structural anomaly detection identifies diagnostic bottleneck symptoms via graph topology

## 1. The Approach

Clinical diagnosis is fundamentally a graph problem: diseases connect to findings, findings overlap across diseases, and evidence can conflict. This showcase models that structure directly and demonstrates a practical workflow:

1. Build a typed clinical graph (diseases, symptoms, labs, imaging, risk factors, treatments)
2. Run rule-based reasoning (`caused_by`, `indirectly_causes`)
3. Score a differential diagnosis using a combined metric:
   - evidence coverage against patient findings
   - proof confidence from `mem.prove()`
4. Detect and revise contradictory evidence
5. Inspect structural ambiguity (diamonds/fan-out/anomalies)
6. Sample probabilistic diagnoses with Born-rule sampling

The key insight is that clinical diagnosis is fundamentally a graph matching problem. Each disease is a pattern of findings — a subgraph of symptom, lab, and imaging edges — and differential diagnosis is the search for which disease subgraphs best explain the observed patient findings. Overlapping findings (cough, fever, dyspnea) create shared subgraphs that make the matching ambiguous; the scoring and reasoning steps quantify that ambiguity and reduce it.

## 2. Quick Start

```bash
.venv/bin/python examples/showcase/domain/medical_diagnosis/medical_diagnosis.py
```

## 3. What the Script Builds

The script creates a 92-node graph with 139 initial edges:

- 15 diseases
- 21 symptoms
- 15 lab findings
- 11 imaging findings
- 15 risk factors
- 15 medications

Initial edge counts:

- `causes`: 100
- `increases_risk`: 21
- `treats`: 16
- conflict edges: 2 (`conflicts_with`, `worsens`)

After reasoning + evidence updates, a typical run ends near:

- 94 nodes
- 151 edges

## 4. Walkthrough

### Section 1: Build the graph

Entities are added with typed metadata, then connected with semantic labels.

### Section 2: Backward chaining and differential ranking

Rules added:

- `TransitiveRule(edge_label="causes", new_label="indirectly_causes")`
- `InverseRule(edge_label="causes", inverse_label="caused_by")`

For each candidate diagnosis, the script computes:

- `prove`: confidence from `mem.prove(dx, known_facts=...)`
- `coverage`: fraction of patient findings directly covered by `dx --causes--> finding`
- `combined = 0.70 * coverage + 0.30 * prove`

Because the knowledge graph is densely connected, `prove()` returns 1.00 for most candidates. The combined score is therefore driven primarily by evidence coverage, making coverage the key differentiator in the ranked differential.

### Section 3: Contradiction handling

Adds opposing evidence (`supports` and `opposes`) against the same diagnosis, then runs:

- `mem.detect_contradictions()`
- `mem.revise_beliefs(strategy="higher_weight")`

Typical result: 1 contradiction detected, 1 weaker edge removed.

### Section 4: Uncertainty propagation

Uses:

- `mem.cognitive.all_confidences()`
- `mem.cognitive.low_confidence(threshold=0.5)`
- `mem.cognitive.confidence(label)`

to inspect graph-wide confidence and diagnosis-specific confidence sources.

### Section 5: Structural pattern analysis

Uses:

- `mem.match_chains(edge_label="causes", min_length=2)`
- `mem.match_diamonds(edge_label="causes")`
- `mem.match_fan_out(edge_label="causes")`

to expose shared-symptom ambiguity (diamond patterns) and high-manifestation diseases (fan-out).

### Section 6: Treatment links

Uses `mem.match_chains(edge_label="treats", ...)` to summarize medication->disease treatment pathways.

### Section 7: Probabilistic differential diagnosis

Creates a belief distribution over candidate diagnoses:

```python
qs = mem.belief.create(
    ["pneumonia", "pulmonary_embolism", "bronchitis", "pleural_effusion", "copd_exacerbation"],
    amplitudes=[0.70, 0.35, 0.30, 0.20, 0.25],
)
```

Then samples 15 times via `mem.belief.sample(qs)`. Frequencies vary by run (probabilistic), but `pneumonia` should dominate because of the highest Born-rule probability.

### Section 8: Structural anomaly detection

Runs `mem.analyze.anomalies(concept)` on key symptoms/diseases to identify topology-driven bottlenecks.

### Expected Output

Typical ranked differential diagnosis output from Section 2:

```
  Ranked differential (coverage-weighted):
    1. pneumonia                 combined=1.00  coverage=1.00  prove=1.00
    2. bronchitis                combined=0.77  coverage=0.67  prove=1.00
    3. pulmonary_embolism        combined=0.53  coverage=0.33  prove=1.00
    4. copd_exacerbation         combined=0.53  coverage=0.33  prove=1.00
    5. pleural_effusion          combined=0.35  coverage=0.50  prove=0.00
```

Exact values may vary slightly between runs due to non-deterministic multiway expansion, but the ranking structure is stable: `pneumonia` consistently ranks first because it covers all six presented findings (fever, cough, productive cough, dyspnea, pleuritic chest pain, tachycardia). `bronchitis` ranks second due to covering 4 of 6 findings. `prove()` returns 1.00 for most candidates because the densely-connected clinical graph satisfies premise structures quickly.

## 5. Mermaid Topology (Representative Subgraph)

```mermaid
graph TD
    PNEU[1) pneumonia] -->|causes| COUGH[cough]
    PNEU -->|causes| FEVER[fever]
    PNEU -->|causes| DYSP[dyspnea]

    PE[2) pulmonary_embolism] -->|causes| SUDDEN_DYSP[sudden_onset_dyspnea]
    PE -->|causes| PLEUR[pleuritic_chest_pain]

    BRON[3) bronchitis] -->|causes| COUGH
    BRON -->|causes| FEVER

    AMOX[4) amoxicillin] -->|treats| PNEU
    IMMOB[5) prolonged_immobility] -->|increases_risk| PE
```

Note: this diagram is intentionally a subset for readability; the script graph is substantially larger.

How to read it:

- Numbered nodes indicate clinical roles: **1) pneumonia** is the leading diagnosis, **2) pulmonary_embolism** is the primary differential, **3) bronchitis** is a secondary differential, **4) amoxicillin** is the first-line treatment, and **5) prolonged_immobility** is a risk-factor modifier.
- Start at disease nodes (1-3), then follow `causes` edges into findings. Shared findings like **cough** (reached from both pneumonia and bronchitis) and **pleuritic_chest_pain** (reached from both pneumonia and pulmonary embolism) are exactly what create diagnostic ambiguity — the script's coverage-weighted scoring resolves this by measuring how much of the patient's finding set each disease explains.
- `increases_risk` edges (5 → 2) encode pre-test probability modifiers that shift the prior before evidence is evaluated, while `treats` edges (4 → 1) capture intervention paths once the diagnosis is confirmed.

## 6. Key Metrics (Current Script)

- Initial graph: 92 nodes, 139 edges
- Post-reasoning/evidence graph: 94 nodes, 151 edges
- Differential candidates: 5
- Contradictions resolved: 1
- Born-rule diagnosis sampling: 15 draws (stochastic)

## 7. Understanding the Output

### Confidence Interpretation

| Confidence Range | Meaning |
|------------------|---------|
| > 0.9 | Direct evidence — node has multiple strong supporting edges |
| 0.7 - 0.9 | Inferred — node's confidence derives from reasoning, not direct observation |
| 0.5 - 0.7 | Moderate — some evidence but significant gaps remain |
| < 0.5 | Low — insufficient evidence, flagged for further investigation |

### Contradiction Severity

| Severity | Interpretation |
|----------|---------------|
| > 0.7 | Strong contradiction — opposing evidence with comparable weights, requires resolution |
| 0.4 - 0.7 | Moderate — evidence partially conflicts, may coexist |
| < 0.4 | Weak — minor tension, may not require action |

### Fan-out Interpretation

| Fan-out | Diagnostic Implication |
|---------|----------------------|
| 10+ | High-fan-out disease explains many findings but overlaps with many other diseases |
| 5 - 10 | Moderate — distinctive enough to narrow the differential with targeted testing |
| < 5 | Low — few manifestations, easy to miss, often requires specific testing |

### Anomaly Status Interpretation

| Status | Interpretation |
|--------|---------------|
| anomalous | Diagnostic bottleneck — high convergence or cyclic structure, targeted testing needed |
| boundary | Approaching anomaly — some structural tension, worth monitoring |
| low_risk | Well-characterized node — few competing explanations |

### Belief Distribution Interpretation

| Born-Rule Probability | Diagnostic Confidence |
|-----------------------|----------------------|
| > 0.5 | Leading candidate — strongly supported by evidence |
| 0.1 - 0.5 | Active consideration — plausible, awaiting further evidence |
| < 0.1 | Low priority — unlikely but not ruled out |

## 8. Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **Differential Diagnosis** | A ranked list of candidate diseases that could explain a patient's findings |
| **Backward Chaining** | Working from a suspected diagnosis backward to the evidence needed to prove it |
| **Belief Revision** | Detecting and resolving contradictory findings in the evidence graph |
| **Belief Distribution** | A quantum superposition of candidate diagnoses, each with a complex amplitude |
| **Born-Rule Sampling** | Collapsing a belief distribution to a single diagnosis with probability proportional to amplitude squared |
| **Diamond Pattern** | Two diseases that share a common symptom (convergent evidence) |
| **Fan-out** | Number of symptoms a disease produces (high fan-out = more distinctive) |
| **Structural Anomaly** | A concept flagged as a diagnostic bottleneck due to its graph topology |
| **Premise Satisfaction** | How many required evidence items are present vs. total needed |

## 9. Key API Methods

| Method | Purpose |
|--------|---------|
| `mem.add(label, data)` | Create a clinical entity node |
| `mem.link(source, target, label)` | Create a semantic clinical edge |
| `mem.reason.add_rules(*rules)` | Register inference rules |
| `mem.reason(seeds, max_depth)` | Apply rules to generate inferred edges |
| `mem.prove(concept, known_facts)` | Backward-chain from diagnosis to evidence |
| `mem.detect_contradictions()` | Find opposing evidence edges |
| `mem.revise_beliefs(strategy)` | Resolve contradictions by edge weight |
| `mem.cognitive.all_confidences()` | Calculate confidence for all nodes |
| `mem.cognitive.confidence(concept)` | Calculate confidence for a specific node |
| `mem.cognitive.low_confidence(threshold)` | Identify nodes below a confidence threshold |
| `mem.match_diamonds(edge_label)` | Find convergent symptom patterns |
| `mem.match_fan_out(edge_label, min_fan)` | Find diseases with many manifestations |
| `mem.match_chains(edge_label, min_length)` | Find inference chains of minimum length |
| `mem.belief.create(concepts, amplitudes)` | Create a belief distribution over candidate diagnoses |
| `mem.belief.sample(distribution)` | Collapse a belief distribution to a single diagnosis via the Born rule |
| `mem.analyze.anomalies(concept)` | Identify diagnostic bottlenecks through graph topology |

## 10. Related Examples

| Example | Focus |
|---------|-------|
| `examples/showcase/belief/belief_and_bayesian/belief_and_bayesian.py` | Born-rule sampling, Bayesian updating, outcome distributions |
| `examples/showcase/reasoning/knowledge_reasoning/knowledge_reasoning.py` | Transitive inference, backward chaining, rule application |
| `examples/showcase/core/structural_patterns/structural_patterns_and_communities.py` | Diamond, fan-out, and chain pattern detection |

## 11. Real-World Gap

This remains a synthetic showcase. Production clinical decision support would still require:

- validated clinical ontology/terminology integration
- patient-specific temporal evidence handling
- calibrated probabilities from real epidemiologic and diagnostic-performance data
- regulatory-grade validation and governance
