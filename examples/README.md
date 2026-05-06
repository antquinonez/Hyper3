Hyper3 Examples
===============

Self-contained examples demonstrating Hyper3's knowledge graph capabilities
with realistic synthetic data (100+ nodes, 200+ edges per example).

Each example targets practitioners in security, risk, and IT operations,
producing actionable outputs that would not be obvious from manual inspection.

Running Examples
----------------

All examples are self-contained and can be run directly:

    .venv/bin/python examples/showcase/threat_intelligence/knowledge_basics.py

No external dependencies beyond the core Hyper3 installation are required.

Showcase Examples (`showcase/`)
-------------------------------

| Directory | File | Focus |
|-----------|------|-------|
| `threat_intelligence/` | `knowledge_basics.py` | Threat intel KB (140 nodes), multi-modal storage, pattern matching, centrality, attack paths |
| `microservices_reasoning/` | `reasoning_walkthrough.py` | Microservice dependencies (70 nodes), TransitiveRule, InverseRule, blast radius, betweenness centrality |
| `multiway_reasoning/` | `multiway_lateral_insights.py` | Multi-hypothesis exploration, state clustering, lateral insights (81 nodes, 10 rules, 66 branches) |
| `construction_and_queries/` | `construction_and_queries.py` | Hypergraph construction (8 nodes), n-ary edges, semantic metadata, neighborhood queries |
| `retrieval_and_feedback/` | `retrieval_and_feedback.py` | Security knowledge retrieval (177 nodes), spreading activation, RRF fusion, learning-to-rank |
| `statistics_and_metrics/` | `statistics_and_metrics.py` | Degree, edge-size, centrality stats, weighted degree, multi-stat comparison |
| `directed_hypergraphs/` | `directed_hypergraphs.py` | Directed hyperedges (5 nodes), in/out degree, hyperedge neighbors, transitive inference |
| `temporal_reasoning/` | `temporal_reasoning.py` | Incident timeline analysis (46 events), Allen interval algebra, causal chains, temporal anomalies |
| `provenance_and_retraction/` | `provenance_and_retraction.py` | Provenance tracking, explain(), cascading retraction, impact analysis |
| `network_analytics/` | `graph_analytics.py` | Centrality, cycles, components, risk scoring (128 nodes) |
| `text_enrichment/` | `text_enrichment.py` | Regex extraction, custom LLMProvider, security reports (16 reports) |
| `advanced_rules/` | `advanced_rules.py` | HubInferenceRule, GeneralizationRule, StructuralProjectionRule, auto-discovery |
| `structural_patterns/` | `structural_patterns_and_communities.py` | Chain/diamond/fan-out detection, community detection, cross-analysis |
| `bayesian_reasoning/` | `bayesian_reasoning.py` | Priors, likelihoods, posteriors, Bayes factors, credible sets |
| `centrality_and_ranking/` | `centrality_and_pagerank.py` | Degree/betweenness centrality, hypergraph PageRank, multi-centrality comparison |
| `communities_and_clustering/` | `community_detection.py` | Label propagation, s-persistence, modularity, hyperedge-aware communities |
| `paths_and_connectivity/` | `shortest_paths_and_traversal.py` | Shortest path, all paths, BFS recall, hyperedge-as-single-hop |
| `spectral_and_matrix/` | `spectral_methods.py` | Incidence matrix, Laplacian, spectral embedding, s-persistence |
| `generative_and_workflow/` | `temporal_reasoning.py` | Allen algebra, causal chains, temporal consistency |
| `overlay_commit_rollback/` | `overlay_commit_rollback.py` | Speculative incident investigation (82 nodes), overlay commit/rollback, multi-hypothesis exploration |
| `iterative_frame_reasoning/` | `iterative_frame_reasoning.py` | Multi-perspective risk assessment (80 nodes), 4 analysis perspectives, cross-perspective invariants |
| `quantum_diagnostics/` | `quantum_diagnostics.py` | Probabilistic hypothesis management (62 nodes), Bayesian comparison, entropy as uncertainty measure |
| `adaptive_learning/` | `adaptive_learning.py` | Self-tuning knowledge graph (111 nodes), rule effectiveness, basis learning, frame learning |
| `self_evolving_cognition/` | `self_evolving_cognition.py` | Self-evolving cognitive system, feedback-driven evolution, metamorphosis validation, bias profile |
| `hypergraph_native/` | `hypergraph_native.py` | Protein interaction network (35 nodes), n-ary hyperedges, s-persistence, gated diffusion |
| `knowledge_reasoning/` | `knowledge_reasoning.py` | Knowledge reasoning, transitive inference, backward chaining, provenance, belief revision |
| `self_evolution/` | `self_evolution.py` | Self-evolution, decay/prune/merge, Hebbian learning, feedback-driven evolution |
| `belief_and_bayesian/` | `belief_and_bayesian.py` | Belief & Bayesian, `sample_distribution()`, Bayesian updating, concept correlation, credible sets |
| `retrieval_and_similarity/` | `retrieval_and_similarity.py` | Retrieval & similarity, spreading activation, embedding similarity, RRF retrieval |
| `it_troubleshooting/` | `demo.py` (package) | IT root cause analysis, backward chaining, proof chains, issue tree visualization |
| `job_skill_matching/` | `demo.py` (package) | Skill substitution chains, n-ary job requirements, self-evolving skill graph |
| `medical_timeline/` | `demo.py` (package) | Allen interval algebra, symptom timelines, causal chain detection, duration analysis |
| `recipe_substitution/` | `demo.py` (package) | Ingredient substitution chains, n-ary groups, self-evolving knowledge base |
| `supply_chain_resilience/` | `supply_chain_resilience.py` | Multi-tier supply chain (126 nodes), risk cascades, single-point-of-failure, diversification |
| `code_dependency_analysis/` | `code_dependency_analysis.py` | Monorepo dependencies (129 nodes), blast radius, circular deps, test coverage gaps |
| `fraud_detection/` | `fraud_detection_intelligence.py` | Fraud ring (119 nodes), circular money flows, suspect ranking, hidden connections |
| `medical_diagnosis/` | `medical_diagnosis.py` | Clinical KB (96 nodes), backward chaining, belief revision, uncertainty propagation |

| `threat_intel_full_chain/` | `threat_intel_full_chain.py` | Full-chain CTI (73 nodes), rule reasoning, activation triage, belief sampling, self-evolution |
| `financial_risk_network/` | `financial_risk_network.py` | Cross-asset risk (76 nodes), community detection, graph diffing, Hebbian learning |
| `infrastructure_self_healing/` | `infrastructure_self_healing.py` | Self-healing infrastructure (47 nodes), feedback-driven evolution, metamorphosis validation |

See `showcase/multiway_reasoning/README.md` for detailed architecture diagrams and explanations.

Project Examples (`projects/`)
------------------------------

Production-grade data pipelines that fetch live external data, use Prefect
orchestration, and run multi-stage analysis. Unlike showcase examples, projects
require network access and external dependencies (requests, prefect).

| Directory | File | Data Source | Key Analysis |
|-----------|------|-------------|--------------|
| `arxiv_navigator/` | `pipeline.py` | ArXiv API (cs.AI + cs.LG) | Anomaly detection, activation, centrality, communities, prolific authors |
| `cve_vulnerability_intel/` | `pipeline.py` | NIST NVD API (+ fallback) | Transitive reasoning, blast radius, chokepoints, vulnerability clusters |
| `dependency_scanner/` | `pipeline.py` | GitHub Advisory DB + PyPI | Dependency chains, blast radius, ecosystem communities |
| `movie_recommendations/` | `pipeline.py` | Synthetic (offline) | Genre/actor/bridge/retrieval recommendation strategies |
| `wikipedia_concepts/` | `pipeline.py` | Wikipedia API (+ offline) | Hub detection, anomaly analysis, ML sub-topic communities |

Each project directory has its own README.md with pipeline architecture, Hyper3
integration details, and output interpretation guides.

Root Demos
----------

The project root contains additional demo scripts:

- `demo_walkthrough.py` - Full car diagnostic walkthrough (all 10 steps)
- `demo_integrated.py` - Weather-impact domain with full pipeline
- `demo_multiway.py` - Low-level multiway engine demo
- `demo_discovery.py` - Rule discovery engine demo
- `demo_feedback.py` - Retrieval feedback and LTR demo

Comparison Examples (`comparison/`)
------------------------------------

Two categories of comparison scripts:

### Framework-level comparisons (XGI / HNX / NetworkX)

Runnable scripts implementing the same operations as Hyper3 examples
15-22 using XGI, HyperNetX, or NetworkX. Each produces comparable output
with inline notes on capability gaps.

| File | Framework | Hyper3 Counterpart | Key Differences |
|------|-----------|-------------------|-----------------|
| `xgi_01_construction.py` | XGI | `showcase/construction_and_queries/` | XGI: integer node IDs, lazy stat objects. Hyper3: labeled nodes, n-ary edges, semantic metadata |
| `xgi_02_statistics.py` | XGI | `showcase/statistics_and_metrics/` | XGI: `.asdict()/.aslist()/.aspandas()` stat API. Hyper3: `degree()`, `describe()`, `edges_labeled()` |
| `xgi_03_directed.py` | XGI | `showcase/directed_hypergraphs/` | XGI: clean DiHypergraph API. Hyper3: `in_degree()`/`out_degree()`, semantic inference on edges |
| `xgi_04_centrality.py` | XGI | `showcase/centrality_and_ranking/` | XGI: h-eigenvector, katz centrality. Hyper3: hypergraph PageRank, betweenness |
| `xgi_05_community.py` | XGI | `showcase/communities_and_clustering/` | XGI: connected components only. Hyper3: label propagation, s-persistence, modularity |
| `xgi_06_paths.py` | XGI | `showcase/paths_and_connectivity/` | XGI: s-walk distances. Hyper3: hyperedge-as-hop paths, weighted shortest path |
| `xgi_07_spectral.py` | XGI | `showcase/spectral_and_matrix/` | XGI: Laplacian, multiorder Laplacian. Hyper3: spectral embedding, s-persistence |
| `nx_08_temporal.py` | NetworkX | `showcase/generative_and_workflow/` | NX: no temporal support. Hyper3: Allen algebra, causal chains, `allen_relation()` |

### Domain-level comparisons (NetworkX)

Full domain examples re-implemented in raw NetworkX + numpy. Each `nx_*`
script mirrors a corresponding Hyper3 domain or advanced example.

| File | Equivalent Hyper3 Example | Key Differences |
|------|--------------------------|-----------------|
| `nx_threat_intel_full_chain.py` | `domain/threat_intel_full_chain.py` | Custom rule engine, spreading activation, Born-rule collapse, self-evolution (~110 LOC) |
| `nx_financial_risk.py` | `domain/financial_risk_network.py` | Community detection, graph diffing, hierarchical abstraction, Hebbian learning |
| `nx_medical_diagnosis.py` | `domain/medical_diagnosis.py` | Backward chaining, belief revision, uncertainty propagation |
| `nx_structural_patterns.py` | `advanced/13_structural_patterns_and_communities.py` | Chain/diamond/fan-out detection, community detection |
| `nx_it_troubleshooting.py` | `domain/it_troubleshooting/` | Backward chaining, n-ary hyperedge expansion to pairwise, custom graph wrapper (~130 LOC) |

### Reference copies (`comparison/laminar/`)

The original laminar examples remain in `comparison/laminar/` as
reference copies. The canonical versions live in `showcase/`.

Hyper3 Gaps (capabilities in XGI/HNX not in Hyper3)
----------------------------------------------------

- Generative models (`random_hypergraph`, `uniform_HPPM`)
- Lazy stat objects (`NodeStat` with `.asdict()`, `.aslist()`, `.aspandas()`)
- Multi-stat DataFrames (`nodes.multi(["degree", "clustering_coefficient"]).aspandas()`)
- H-eigenvector / Z-eigenvector / Katz centrality
- Spectral clustering (k-means on Laplacian eigenvectors)
- Flag complex construction
- Hypergraph dual construction
- HIF (Hypergraph Interchange Format) support
- User-defined statistics via decorators (`@nodestat_func`)

Competitor Gaps (capabilities in Hyper3 not in XGI/HNX/NetworkX)
----------------------------------------------------------------

- N-ary hyperedge construction with semantic labels and metadata
- Label-based API (`edges_labeled()`, `degree()`, `in_degree()`, `out_degree()`)
- Rule-based reasoning (transitive, abductive, generalization rules)
- Temporal reasoning (Allen interval algebra, causal chains, consistency checking)
- Belief distributions with Born-rule sampling
- Bayesian updating with priors, posteriors, Bayes factors, credible sets
- Self-evolution (decay, prune, merge, reinforce, feedback-driven)
- Provenance tracking with cascading retraction
- Overlay commit/rollback for speculative investigation
- Multiway expansion with state clustering analysis
- Spreading activation and RRF-based retrieval
- Learning-to-rank with relevance feedback
