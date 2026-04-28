Hyper3 Examples
===============

Self-contained examples demonstrating Hyper3's knowledge graph capabilities
with realistic synthetic data (100+ nodes, 200+ edges per example).

Each example targets practitioners in security, risk, and IT operations,
producing actionable outputs that would not be obvious from manual inspection.

Running Examples
----------------

All examples are self-contained and can be run directly:

    .venv/bin/python examples/basic/01_knowledge_basics.py

No external dependencies beyond the core Hyper3 installation are required.

Basic Examples (`basic/`)
-------------------------

| # | File | Use Case | Key Features |
|---|------|----------|--------------|
| 01 | `01_knowledge_basics.py` | Threat intelligence KB (140 nodes) | store, recall, relate, query, pattern_match, subgraph, centrality, connected components |
| 02 | `02_reasoning_walkthrough.py` | Microservice dependency chains (82 nodes) | TransitiveRule, InverseRule, blast radius analysis, betweenness centrality |
| 03 | `03_retrieval_and_feedback.py` | Security knowledge retrieval (176 nodes) | spreading activation, embedding similarity, RRF fusion, relevance feedback, learning-to-rank |

Intermediate Examples (`intermediate/`)
----------------------------------------

| # | File | Use Case | Key Features |
|---|------|----------|--------------|
| 04 | `04_temporal_reasoning.py` | Incident timeline analysis (46 events) | Allen interval algebra, causal chains, constraint checking, temporal anomalies |
| 05 | `05_provenance_and_retraction.py` | Evidence chains in threat intel | provenance tracking, explain(), cascading retraction, impact analysis |
| 06 | `06_graph_analytics.py` | Network attack surface analysis (128 nodes) | centrality, cycles, components, cross-zone violations, composite risk scoring |
| 07 | `07_text_enrichment.py` | Security report extraction (16 reports) | ingest, regex extraction, custom LLMProvider, honest limitation assessment |
| 12 | `12_advanced_rules.py` | Infrastructure pattern discovery (125 nodes) | CausalInferenceRule, GeneralizationRule, AnalogicalReasoningRule, auto-discovery |
| 13 | `13_structural_patterns_and_communities.py` | Technology ecosystem analysis (76 nodes) | chain/diamond/fan-out detection, community detection, cross-analysis |

Advanced Examples (`advanced/`)
-------------------------------

| # | File | Use Case | Key Features |
|---|------|----------|--------------|
| 08 | `08_overlay_commit_rollback.py` | Speculative incident investigation (82 nodes) | overlay commit/rollback, multi-hypothesis exploration, confidence comparison |
| 09 | `09_iterative_frame_reasoning.py` | Multi-perspective risk assessment (80 nodes) | 4 analysis perspectives, cross-perspective invariants, disagreement regions |
| 10 | `10_multiway_lateral_insights.py` | Alternative hypothesis exploration (81 nodes) | multiway DAG, branch analysis, convergence detection, lateral insights |
| 11 | `11_quantum_diagnostics.py` | Probabilistic hypothesis management (62 nodes) | honest quantum formalism, Bayesian comparison, entropy as uncertainty measure |
| 12 | `12_adaptive_learning.py` | Self-tuning knowledge graph (111 nodes) | rule effectiveness, basis learning, frame learning, meta-cognitive introspection |
| 13 | `13_self_evolving_cognition.py` | Self-evolving cognitive system | feedback-driven evolution, metamorphosis validation, cross-operation feedback, bias profile, causal merge insights |

Domain Examples (`domain/`)
----------------------------

| File | Domain | Nodes | Key Outputs |
|------|--------|-------|-------------|
| `supply_chain_resilience.py` | Supply Chain Risk | 126 | Risk cascade paths, single-source dependencies, diversification priorities |
| `code_dependency_analysis.py` | Software Architecture | 125 | Blast radius, circular deps, outdated packages, test coverage gaps |
| `fraud_detection_intelligence.py` | Financial Fraud | 119 | Suspicious clusters, circular money flows, funnel accounts, ring leader ID |
| `medical_diagnosis.py` | Clinical Medicine | 94 | Backward chaining, belief revision, uncertainty propagation, structural patterns |
| `financial_risk_network.py` | Financial Risk | 76 | Community detection, graph diffing, hierarchical abstraction, Hebbian learning |
| `infrastructure_self_healing.py` | Infrastructure Monitoring | 130+ | Feedback-driven evolution, suppression of stale nodes, cross-operation correlation, bias profile, metamorphosis validation |
| `threat_intel_full_chain.py` | Cyber Threat Intelligence | 73 | Rule-based inference, spreading activation, quantum attribution, self-evolution, centrality |

Additional Demos
----------------

The project root contains additional demo scripts:

- `demo_walkthrough.py` - Full car diagnostic walkthrough (all 10 steps)
- `demo_integrated.py` - Weather-impact domain with full pipeline
- `demo_multiway.py` - Low-level multiway engine demo
- `demo_discovery.py` - Rule discovery engine demo
- `demo_feedback.py` - Retrieval feedback and LTR demo

Comparison Examples (`comparison/`)
------------------------------------

NetworkX-only equivalents of Hyper3 examples, implementing the same
analytical capabilities using raw networkx + numpy. Each `nx_*` script
mirrors a corresponding Hyper3 domain or advanced example.

| File | Equivalent Hyper3 Example | Key Differences |
|------|--------------------------|-----------------|
| `nx_threat_intel_full_chain.py` | `domain/threat_intel_full_chain.py` | Custom rule engine, spreading activation, Born-rule collapse, self-evolution (~110 LOC) |
| `nx_financial_risk.py` | `domain/financial_risk_network.py` | Community detection, graph diffing, hierarchical abstraction, Hebbian learning |
| `nx_medical_diagnosis.py` | `domain/medical_diagnosis.py` | Backward chaining, belief revision, uncertainty propagation |
| `nx_structural_patterns.py` | `advanced/13_structural_patterns_and_communities.py` | Chain/diamond/fan-out detection, community detection |
