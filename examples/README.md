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
| `multiway_reasoning/` | `01_multiway_lateral_insights.py` | Multi-hypothesis exploration, state clustering, lateral insights (81 nodes, 10 rules, 66 branches) |
| `construction_and_queries/` | `15_construction_and_queries.py` | Hypergraph construction (8 nodes), n-ary edges, semantic metadata, neighborhood queries |
| `retrieval_and_feedback/` | `03_retrieval_and_feedback.py` | Security knowledge retrieval (177 nodes), spreading activation, RRF fusion, learning-to-rank |
| `statistics_and_metrics/` | `16_statistics_and_metrics.py` | Degree, edge-size, centrality stats, weighted degree, multi-stat comparison |
| `directed_hypergraphs/` | `17_directed_hypergraphs.py` | Directed hyperedges (5 nodes), in/out degree, hyperedge neighbors, transitive inference |
| `temporal_reasoning/` | `04_temporal_reasoning.py` | Incident timeline analysis (46 events), Allen interval algebra, causal chains, temporal anomalies |
| `provenance_and_retraction/` | `05_provenance_and_retraction.py` | Provenance tracking, explain(), cascading retraction, impact analysis |
| `network_analytics/` | `06_graph_analytics.py` | Centrality, cycles, components, risk scoring (128 nodes) |
| `text_enrichment/` | `07_text_enrichment.py` | Regex extraction, custom LLMProvider, security reports (16 reports) |
| `advanced_rules/` | `12_advanced_rules.py` | HubInferenceRule, GeneralizationRule, StructuralProjectionRule, auto-discovery |
| `structural_patterns/` | `13_structural_patterns_and_communities.py` | Chain/diamond/fan-out detection, community detection, cross-analysis |
| `bayesian_reasoning/` | `14_bayesian_reasoning.py` | Priors, likelihoods, posteriors, Bayes factors, credible sets |
| `centrality_and_ranking/` | `18_centrality_and_pagerank.py` | Degree/betweenness centrality, hypergraph PageRank, multi-centrality comparison |
| `communities_and_clustering/` | `19_community_detection.py` | Label propagation, s-persistence, modularity, hyperedge-aware communities |
| `paths_and_connectivity/` | `20_shortest_paths_and_traversal.py` | Shortest path, all paths, BFS recall, hyperedge-as-single-hop |
| `spectral_and_matrix/` | `21_spectral_methods.py` | Incidence matrix, Laplacian, spectral embedding, s-persistence |
| `generative_and_workflow/` | `22_temporal_reasoning.py` | Allen algebra, causal chains, temporal consistency |
| `overlay_commit_rollback/` | `08_overlay_commit_rollback.py` | Speculative incident investigation (82 nodes), overlay commit/rollback, multi-hypothesis exploration |
| `iterative_frame_reasoning/` | `09_iterative_frame_reasoning.py` | Multi-perspective risk assessment (80 nodes), 4 analysis perspectives, cross-perspective invariants |
| `quantum_diagnostics/` | `11_quantum_diagnostics.py` | Probabilistic hypothesis management (62 nodes), Bayesian comparison, entropy as uncertainty measure |
| `adaptive_learning/` | `12_adaptive_learning.py` | Self-tuning knowledge graph (111 nodes), rule effectiveness, basis learning, frame learning |
| `self_evolving_cognition/` | `13_self_evolving_cognition.py` | Self-evolving cognitive system, feedback-driven evolution, metamorphosis validation, bias profile |
| `hypergraph_native/` | `14_hypergraph_native.py` | Protein interaction network (35 nodes), n-ary hyperedges, s-persistence, gated diffusion |
| `knowledge_reasoning/` | `23_knowledge_reasoning.py` | Knowledge reasoning, transitive inference, backward chaining, provenance, belief revision |
| `self_evolution/` | `24_self_evolution.py` | Self-evolution, decay/prune/merge, Hebbian learning, feedback-driven evolution |
| `belief_and_bayesian/` | `25_belief_and_bayesian.py` | Belief & Bayesian, `sample_distribution()`, Bayesian updating, concept correlation, credible sets |
| `retrieval_and_similarity/` | `26_retrieval_and_similarity.py` | Retrieval & similarity, spreading activation, embedding similarity, RRF retrieval |

See `showcase/multiway_reasoning/README.md` for detailed architecture diagrams and explanations.

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
| `it_troubleshooting/` | IT Troubleshooting | 13 | Backward chaining, goal-directed reasoning, proof chains, issue tree visualization |

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
