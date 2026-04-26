Hyper3 Examples
===============

A comprehensive set of examples demonstrating Hyper3's capabilities,
organized by difficulty level and domain.

Running Examples
----------------

All examples are self-contained and can be run directly:

    .venv/bin/python examples/basic/01_knowledge_basics.py

No external dependencies beyond the core Hyper3 installation are required.

Basic Examples (`basic/`)
-------------------------

| # | File | Use Case | Concepts |
|---|------|----------|----------|
| 01 | `01_knowledge_basics.py` | Medical symptoms KB | store, recall, relate, query, pattern_match, subgraph, event log |
| 02 | `02_reasoning_walkthrough.py` | IT incident diagnosis | auto_discover, reason, TransitiveRule, InverseRule, superpose, collapse |
| 03 | `03_retrieval_and_feedback.py` | Document knowledge base | activate, retrieve (RRF), feedback, train_retriever, analogy |

Intermediate Examples (`intermediate/`)
----------------------------------------

| # | File | Use Case | Concepts |
|---|------|----------|----------|
| 04 | `04_temporal_reasoning.py` | Project management timeline | temporal events, Allen relations, causal chains, constraint checking |
| 05 | `05_provenance_and_retraction.py` | Research knowledge graph | provenance tracking, explain(), retract_inference(), cascading retraction |
| 06 | `06_graph_analytics.py` | Social network analysis | centrality, cycles, components, paths, degree distribution |
| 07 | `07_text_enrichment.py` | News article extraction | ingest, ingest_batch, regex extraction, custom LLM provider |

Advanced Examples (`advanced/`)
-------------------------------

| # | File | Use Case | Concepts |
|---|------|----------|----------|
| 08 | `08_overlay_commit_rollback.py` | Threat intelligence | overlay, commit, rollback, confidence tracking |
| 09 | `09_iterative_frame_reasoning.py` | Fraud detection | reason_iterative, reason_with_frame, multi_frame_analysis, derive |
| 10 | `10_multiway_lateral_insights.py` | Scientific hypotheses | multiway DAG, branchial space, lateral insights, causal invariance |
| 11 | `11_quantum_diagnostics.py` | Medical diagnosis | superposition, entanglement, collapse, interference, measurement bases |

Domain Examples (`domain/`)
----------------------------

| File | Domain | Description |
|------|--------|-------------|
| `supply_chain_resilience.py` | Supply Chain | Network analysis, disruption cascades, temporal lead times, quantum risk |
| `code_dependency_analysis.py` | Software Architecture | Dependency cycles, centrality, blast radius, layer analysis |

Additional Demos
----------------

The project root contains additional demo scripts:

- `demo_walkthrough.py` - Full car diagnostic walkthrough (all 10 steps)
- `demo_integrated.py` - Weather-impact domain with full pipeline
- `demo_multiway.py` - Low-level multiway engine demo
- `demo_discovery.py` - Rule discovery engine demo
- `demo_feedback.py` - Retrieval feedback and LTR demo
