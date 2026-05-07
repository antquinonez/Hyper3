# Showcase Example Modernization Analysis

Date: 2026-05-06

## Summary

35+ showcase example scripts were analyzed against 73 source modules. 14 Tier 1 examples use only kernel-level APIs (CRUD, statistics, centrality, connectivity) and completely miss Hyper3's core differentiators. 7 subsystems have zero example coverage.

## Tier 1: Highest Benefit (kernel-only, no advanced features)

These examples use only basic CRUD, statistics, centrality, and connectivity APIs. Adding reasoning, belief, evolution, anomaly detection, or multi-frame analysis would demonstrate Hyper3's unique value.

| # | Example | Current APIs | Best new features |
|---|---------|-------------|-------------------|
| 1 | `construction_and_queries` | store, relate, query_nodes, neighbors, ensure | reason() with TransitiveRule, evolve(), collapse_subgraph() |
| 2 | `statistics_and_metrics` | degree, degree_centrality, pagerank | Evolution showing stats change after decay/prune, Hebbian learning |
| 3 | `centrality_and_pagerank` | centrality suite, katz_centrality | detect_structural_anomalies(), multi_frame_analysis() |
| 4 | `centrality_comparison` | centrality suite comparison | Anomaly detection, community detection, multi-frame |
| 5 | `graph_statistics` | density, degree_distribution, max_edge_order | Evolution, abstraction, temporal events |
| 6 | `shortest_paths_and_traversal` | shortest_path, find_paths, recall | SliceConfig/ObserverSlice for perspective-aware traversal |
| 7 | `advanced_paths` | weighted/unweighted path APIs | Abstraction changing distances, graph diff, evolution |
| 8 | `connectivity_and_distances` | connected_components, s_persistence | Evolution changing connectivity, abstraction |
| 9 | `spectral_methods` | spectral_embedding, s_persistence | Community detection validating spectral clusters |
| 10 | `matrix_computations` | raw incidence_matrix, laplacian | Abstraction changing matrix properties, graph diff |
| 11 | `graph_transformations` | to_dual, to_line_graph, to_bipartite | Evolution on transformed graphs, validation |
| 12 | `clustering_coefficient` | clustering_coefficient only | Community detection, Hebbian learning |
| 13 | `generative_models` | random_sbm, random_chung_lu, etc. | Reasoning on generated graphs, community validation |
| 14 | `generative_and_workflow/temporal_reasoning` | temporal + TransitiveRule | Belief distributions, spreading activation, multi-frame |

## Tier 2: Moderate Benefit (domain-specific, some advanced features)

| Example | Has | Missing |
|---------|-----|---------|
| `network_analytics` | kernel only (865 lines!) | reasoning, belief, anomaly detection, evolution, temporal |
| `threat_intelligence` | kernel only | reasoning, belief, temporal lifecycle |
| `financial_risk_network` | reasoning, abstraction, communities, Hebbian, graph_diff | belief distributions, temporal, multi-frame |
| `fraud_detection` | reasoning, retrieval, patterns | belief, provenance, overlay, temporal |
| `code_dependency_analysis` | reasoning, overlay, communities | abstraction, temporal, belief, graph_diff |
| `medical_diagnosis` | reasoning, structural patterns | belief distributions for differential diagnosis, temporal, anomaly detection |

## Zero-Coverage Subsystems (no dedicated example)

1. **structural_anomaly.py** - detect_structural_anomalies() with ExplorationReport
2. **abstraction.py** - full collapse/expand/list_summaries hierarchy
3. **graph_diff.py** - capture_version, diff_from_version, rollback_to_version, history
4. **validation.py** - run_comparison(), run_validation_suite()
5. **snapshot.py** - full system serialization and restore
6. **constraints.py** - WeightConstraint, ChainDepthConstraint, ConstraintPipeline
7. **frame_transform.py** - FrameTransformer.transform(), information_loss()

## Outdated Patterns in Existing Examples

1. ~~Dict-style access on typed results instead of attribute access (overlay_commit_rollback, iterative_frame_reasoning, advanced_rules)~~ **Fixed** — replaced with typed attribute access
2. ~~Direct engine imports bypassing the facade (StateConvergenceEngine in 3 examples)~~ **Fixed** — changed to import from public `hyper3` package
3. ~~Private state manipulation (mem._meta._state.architectural_fitness)~~ **Accepted** — no public API alternative; documented as demo-only in self_evolving_cognition
4. Raw graph iteration (`mem.graph.nodes`) instead of facade methods — **Accepted** — no facade method exists to list all node labels; this is a facade API gap

## Suggested New Examples

1. Uncertainty and Confidence Analysis
2. Structural Anomaly Detection
3. Graph Versioning, Diffing, and Rollback
4. Hierarchical Abstraction and Multi-Level Analysis
5. Constraint-Pipeline Validation
6. Full System Snapshot and Restore
7. Validation Engine Comparison
