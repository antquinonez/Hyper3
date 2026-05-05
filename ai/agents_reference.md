# Architecture and Reference

Extracted from [AGENTS.md](../AGENTS.md). Read this to understand where things live and how modules relate.

## Architecture

The codebase is in `src/hyper3/` with a flat module structure (no sub-packages):

- **kernel.py** — Thin composition facade. `Hypergraph` inherits from 11 focused mixins (CoreMixin, QueryMixin, PathMixin, ComponentMixin, CycleMixin, CentralityMixin, SpectralMixin, ClusteringMixin, PatternMixin, TransformMixin, SimilarityMixin). Re-exports `Hypernode`, `Hyperedge`, `Modality`, `AbstractionLayer`, `Metadata` from `kernel_types.py`.
- **kernel_types.py** — Data structures: `Hypernode`, `Hyperedge`, `Metadata`, `Modality`, `AbstractionLayer`.
- **kernel_base.py** — `_GraphBase` (shared state declarations + cross-mixin method stubs) and `CoreMixin` (CRUD: add/get/remove nodes and edges, merge_node, batch mode).
- **kernel_query.py** — `QueryMixin`: incident_edges, outgoing_edges, incoming_edges, neighbors, out_neighbors, in_neighbors, star, hyperedge_neighbors, hyperedge_cocoverage, node_degree, degree_distribution, query_dimension, labeled_edges, node_count, edge_count, density, unique_edge_sizes, max_edge_order, hash, degree_correlation.
- **kernel_paths.py** — `PathMixin`: find_paths, shortest_path (Dijkstra/BFS), shortest_path_lengths, single_source_shortest_path_lengths.
- **kernel_components.py** — `ComponentMixin`: connected_components (union-find), s_connected_components, s_persistence, is_connected, largest_connected_component, component_of, strongly_connected_components, biconnected_components, articulation_points, greedy_modularity_communities.
- **kernel_cycles.py** — `CycleMixin`: has_cycle, detect_cycles, girth.
- **kernel_centrality.py** — `CentralityMixin`: degree_centrality, betweenness_centrality, pagerank, katz_centrality, closeness_centrality, eigenvector_centrality.
- **kernel_spectral.py** — `SpectralMixin`: incidence_matrix, incidence_matrix_unsigned, hypergraph_laplacian, adjacency_matrix, normalized_laplacian, spectral_embedding, algebraic_connectivity, fiedler_vector, spectral_bisection, spectral_bipartivity, bethe_hessian_matrix, transition_matrix, incidence_matrix_by_order.
- **kernel_clustering.py** — `ClusteringMixin`: clustering_coefficient, average_clustering_coefficient, spectral_clustering, transitivity.
- **kernel_pattern.py** — `PatternMixin`: pattern_match, subgraph.
- **kernel_transforms.py** — `TransformMixin`: to_networkx, to_dual, to_line_graph, to_bipartite_graph, clique_projection.
- **kernel_similarity.py** — `SimilarityMixin`: hyperedge_similarity.
- **exceptions.py** — Domain-specific exception hierarchy (`Hyper3Error`, `NodeNotFoundError`, `EdgeNotFoundError`, etc.). `NodeNotFoundError` extends both `Hyper3Error` and `ValueError` for catch-ergonomics.
- **event_log.py** — `EventLog` records timestamped events with query/filter support.
- **equivalence.py** — `EquivalenceEngine` finds similar nodes using data + structural similarity with blocking.
- **cache.py** — `LazyCache` LRU cache with TTL, optional Markov-model prefetching.
- **traversal.py** — `TraversalEngine` (BFS, DFS, dimension-filtered, adaptive weight-priority), `SliceConfig`, `ObserverSlice`.
- **evolution.py** — `GraphMaintenanceEngine` with decay, prune, merge, reinforce. Returns typed `EvolveResult`. `EvolutionMetrics` dataclass.
- **rules.py** — `Rule` ABC with 8 concrete implementations. Rules have `find_matches()` (pure query, no side effects) and `apply()` (mutates the graph).
- **multiway.py** — `MultiwayEngine` drives expansion (including lazy generator-based expansion); `MultiwayGraph` stores the state DAG; `MultiwayState` is a node in that DAG.
- **multiway_causal.py** — `StateConvergenceEngine` merges convergent states with graph isomorphism detection. Returns typed `MergeReport`.
- **belief.py** — `BeliefLayer` provides distribution creation/sampling/correlation/interference, adaptive coherence time, and sampling profile learning via Thompson sampling. Also contains `BeliefState`, `Outcome`, `ConceptCorrelation`, `EvidenceInteraction`, `SamplingProfile`, `SamplingTrigger`, and `BUILTIN_BASES`.
- **state_clustering.py** — `StateClusteringEngine` maps multiway states into a coordinate space with distance metrics, clustering, lateral inference, and multi-scale analysis. Returns typed `StateClusteringReport`.
- **rule_analytics.py** — `RuleAnalytics` tracks rule effectiveness, meta-patterns, and high-level insights from rule usage. Returns typed `RuleAnalyticsReport` and `RuleNeighborhoodResult`.
- **structural_anomaly.py** — `StructuralAnomalyDetector` detects structural anomalies (cycles, high centrality, contradictory labels, unusual connectivity) and classifies concepts along a low_risk/boundary/anomalous spectrum. `ExplorationReport` dataclass tracks coverage bounds.
- **multi_perspective.py** — `MultiPerspectiveAnalyzer` provides multi-perspective analysis (classical/quantum/hypergraph/probabilistic perspectives) with perspective effectiveness learning via Thompson sampling.
- **system_monitor.py** — `SystemMonitor` provides introspection and metamorphosis trigger detection. `introspect()` returns typed `HealthReport`, `analyze()` returns typed `MonitorStats`.
- **memory.py** — `HypergraphMemory` is the unified facade that integrates all subsystems. It composes from 7 mixins for maintainability. This is the main entry point users interact with.
- **memory_base.py** — `_MemoryBase` declares shared type annotations for all memory mixins.
- **memory_core.py** — `CoreMixin`: store, recall, relate, query, evolve, find_node, node_label.
- **memory_reasoning.py** — `ReasoningMixin`: reason (with decomposed helpers), reason_incremental, reason_iterative, reason_with_frame, derive, commit/rollback inferences.
- **memory_belief.py** — `BeliefMixin`: create_distribution, sample, correlate, lateral_insights, structural anomaly detection.
- **memory_bayesian.py** — `BayesianMixin`: set_prior, update_belief, get_belief, map_estimate, bayes_factor, credible_set, reset_belief.
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants.
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats.
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, system monitor, multi-perspective analysis, discovery.
- **persistence.py** — `Serializer` handles JSON save/load.
- **rules_discovery.py** — `RuleDiscoveryEngine` discovers transitive/inverse/hub patterns in the graph. `analyze()` returns typed `DiscoveryAnalysis`.
- **retrieval_activation.py** — `SpreadingActivation` provides associative recall via energy propagation through the graph. Configurable decay, per-label propagation rates, directional mode, and normalization.
- **embedding.py** — `EmbeddingEngine` provides semantic similarity via pluggable embedding providers. `HashEmbeddingProvider` is the built-in fallback; users can supply custom providers (e.g., sentence-transformers) via the `EmbeddingProvider` ABC. Supports cosine similarity, euclidean distance, find_similar, find_all_similar_pairs, and analogy (vector arithmetic). Optional FAISS index (`enable_faiss()`) for sub-millisecond similarity search on large graphs.
- **retrieval_engine.py** — `RetrievalEngine` combines activation + semantic signals via Reciprocal Rank Fusion (RRF). `FeedbackStore` and `LearningToRank` enable relevance feedback: users mark results relevant/irrelevant, then `train_retriever()` learns optimal feature weights. `RetrievalResult` carries activation, similarity, RRF score, and rank positions. `train()` and `train_from_feedback()` return typed `TrainResult`.
- **visualization.py** — Optional matplotlib plotting (requires `[viz]` extra).

## Performance Indexes

The following are already optimized — maintain them when making changes:

- `Hypergraph._label_index: dict[str, str]` — Maps label → node_id. Updated in `add_node`, `remove_node`, `merge_node`. Used by `get_node_by_label()`.
- `Hypergraph._neighbor_cache: dict[str, list[str]] | None` — Full neighbor map, lazily built, invalidated on any edge/node mutation.
- `MultiwayGraph._leaves_cache: list[MultiwayState] | None` — Cached leaf list, invalidated when a state gains children.
- `StateClusteringEngine._distance_cache: dict[tuple[str, str], StateDistanceMetrics]` — Cached pairwise distances.
- `TransitiveRule` uses a pre-built `edge_set: set[tuple[str, str]]` for O(1) edge-existence checks instead of scanning `incident_edges()`.
- `EmbeddingEngine` supports optional FAISS index (`enable_faiss()`). When enabled, `find_similar()` uses inner-product search instead of brute-force O(N) scan. IndexFlatIP for <1K nodes, IndexIVFFlat for >=1K. FAISS is an optional `[faiss]` extra.

## Extracted Modules (from kernel.py refactoring)

- **kernel_types.py** — `Hypernode`, `Hyperedge`, `Metadata`, `Modality`, `AbstractionLayer` (extracted from kernel.py)
- **kernel_base.py** — `_GraphBase` (shared state) and `CoreMixin` (CRUD, merge, batch) (extracted from kernel.py)
- **kernel_query.py** — `QueryMixin` (edge lookups, neighbors, degree, stats, hash, degree_correlation) (extracted from kernel.py)
- **kernel_paths.py** — `PathMixin` (find_paths, shortest_path, Dijkstra, BFS) (extracted from kernel.py)
- **kernel_components.py** — `ComponentMixin` (s-components, s-persistence, union-find, SCCs, biconnected, articulation, modularity) (extracted from kernel.py)
- **kernel_cycles.py** — `CycleMixin` (has_cycle, detect_cycles, girth) (extracted from kernel.py)
- **kernel_centrality.py** — `CentralityMixin` (degree/betweenness/pagerank/katz/closeness/eigenvector centrality) (extracted from kernel.py)
- **kernel_spectral.py** — `SpectralMixin` (incidence, Laplacian, adjacency, eigenvalues, spectral embedding, algebraic connectivity, Fiedler, bisection, bipartivity, Bethe-Hessian, transition matrix, incidence_by_order) (extracted from kernel.py)
- **kernel_clustering.py** — `ClusteringMixin` (clustering_coefficient, spectral_clustering, transitivity) (extracted from kernel.py)
- **kernel_pattern.py** — `PatternMixin` (pattern_match, subgraph) (extracted from kernel.py)
- **kernel_transforms.py** — `TransformMixin` (to_networkx, to_dual, to_line_graph, to_bipartite, clique_projection) (extracted from kernel.py)
- **kernel_similarity.py** — `SimilarityMixin` (hyperedge_similarity, cocoverage) (extracted from kernel.py)
- **event_log.py** — `EventLog` (extracted from kernel.py)
- **equivalence.py** — `EquivalenceEngine` (extracted from kernel.py)
- **cache.py** — `LazyCache` (extracted from kernel.py)
- **traversal.py** — `TraversalEngine`, `SliceConfig`, `ObserverSlice` (extracted from kernel.py)
- **evolution.py** — `GraphMaintenanceEngine`, `EvolutionMetrics` (extracted from kernel.py)
- **belief.py** — `BeliefLayer` and all belief data types (extracted from multiway_causal.py)
- **memory_base.py** — `_MemoryBase` shared type annotations for memory mixins
- **memory_core.py** — `CoreMixin`: store, recall, relate, query, evolve, find_node, node_label
- **memory_reasoning.py** — `ReasoningMixin`: reason (with decomposed helpers), reason_incremental, reason_iterative, reason_with_frame, derive, commit/rollback inferences
- **memory_belief.py** — `BeliefMixin`: create_distribution, sample, correlate, lateral_insights, structural anomaly detection
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, system monitor, multi-perspective analysis, discovery
- **bayesian.py** — `BayesianLayer` with `CategoricalDistribution`, `Evidence`, `UpdateResult` dataclasses
- **memory_bayesian.py** — `BayesianMixin`: set_prior, update_belief, get_belief, map_estimate, bayes_factor, credible_set, reset_belief
- **structural_anomaly.py** — `StructuralAnomalyDetector`. Detects cycles, centrality, contradictions.
- **multi_perspective.py** — `MultiPerspectiveAnalyzer`. Multi-frame parameter selection.

## New Modules (Round 1-2 Additions)

- **overlay.py** — `HypergraphOverlay` provides a temporary inference layer on top of the base graph. Supports `commit()` (merge to base) and `rollback()` (discard). Tracks per-edge confidence. `reason(use_overlay=True, auto_commit=False)` enables review-before-commit workflow.
- **provenance.py** — `ProvenanceTracker` records inference derivations (rule name, input edges, depth). `explain()` produces recursive `Explanation` objects with `render()`. `retract()` cascades: removing a premise removes all dependent conclusions. Facade methods `explain()` and `retract_inference()` accept `edge_label: str | None = None` to filter by edge label.
- **temporal.py** — `TemporalReasoner` with full Allen interval algebra (13 relations), causal chain detection, temporal proximity queries, constraint checking, and edge-level temporal consistency.
- **enrichment.py** — `LLMEnricher` extracts entities/relations from text. `RegexExtractor` is the zero-dependency fallback. Pluggable `LLMProvider` ABC for real language models.
- **embedding_graph.py** — `RandomWalkEmbeddingProvider` (Node2Vec-style skip-gram with negative sampling), `NeighborhoodFingerprintProvider` (TF-IDF-weighted edge label hashing), `CompositeEmbeddingProvider` (weighted combination with optional PCA). All implement `EmbeddingProvider.embed_node()` for graph-structure-aware embeddings.
- **feedback.py** — `OperationFeedback` tracks sampling, retrieval, inference, and evolution outcomes with accuracy/precision/acceptance metrics and fitness trend detection. `cross_operation_summary()` computes aggregate health and identifies correlated nodes across operation types. `FeedbackSignal` dataclass for individual outcome records.

## New Modules (Round 3 Additions — Gap Fill)

- **snapshot.py** — `SystemSnapshot` dataclass for cross-session continuity. `capture()` freezes full memory state; `restore()` rebuilds from snapshot. Supports save/load to disk.
- **frame_transform.py** — `FrameTransformer` defines 12 pair-wise transformation rules between classical/quantum/hypergraph/probabilistic frames. Returns `TransformedConfig` with transformed problem features.
- **validation.py** — `ValidationEngine` compares simple vs enhanced reasoning with A/B testing. Produces `ValidationReport` with `AgreementMetrics` (precision, recall, F1, divergence).
- **capabilities.py** — `CapabilityLevel` enum (BASIC/ENHANCED/ADVANCED) for staged implementation. `detect_capability_level()` inspects graph/engine state. `require_capability()` decorator gates functions.
- **constraints.py** — `ConstraintCheck` ABC for boundary constraints. `BoundaryNavigator` checks and navigates constraints. Built-in: `NoSelfLoopConstraint`, `WeightInflationConstraint`, `ProvenanceDepthConstraint`.

## New Modules (Round 4 — Essential Cognitive Capabilities)

- **backward_chain.py** — `BackwardChainEngine` provides goal-directed reasoning via backward chaining from a target concept through inference rules. `prove()` returns `BackwardChainResult` with proof tree, missing premises, and alternative plans. `prove_batch()` accumulates proven facts across multiple targets.
- **hebbian.py** — `HebbianLearner` implements co-activation learning: nodes activated together have their connecting edges strengthened. Integrates with `SpreadingActivation`. `HebbianConfig` controls learning rate, decay, and thresholds. `reinforce_from_activation()` runs a full Hebbian cycle from current activation state.
- **uncertainty.py** — `UncertaintyEngine` propagates confidence through inference chains using provenance depth. `compute_confidence()` scores individual nodes (1.0 for observed, decaying for inferred). Supports geometric, minimum, and average combination strategies. `trace_chain()` finds the highest-confidence path between two nodes.
- **structural_match.py** — `StructuralPatternEngine` provides subgraph pattern matching beyond label-based filtering. `PatternTemplate` defines role-based node/edge templates. `match_chain()` finds linear chains, `match_diamond()` finds convergence patterns, `match_fan_out()` finds hub nodes, `match_pattern()` matches arbitrary templates with data-type and label-pattern constraints.
- **belief_revision.py** — `ContradictionResolver` detects and resolves contradictory edges. Built-in negation map (`supports`/`opposes`, `causes`/`prevents`, etc.) with custom extension. Resolution strategies: `higher_confidence`, `higher_weight`, `observed_over_inferred`, `newer`. `revise()` cascades retraction to dependent inferences.
- **abstraction.py** — `AbstractionNavigator` collapses subgraphs into summary nodes and expands them back. `collapse_subgraph()` removes internal edges, rewires external connections to the summary node. `expand_node()` restores original structure. `AbstractionMapping` tracks the collapse/expand relationship.
- **community.py** — `CommunityDetector` identifies communities (clusters) in the main hypergraph. Label propagation (unweighted and weighted) and connected-components methods. Returns `CommunityResult` with per-community membership, internal/external edge counts, modularity, and coverage.
- **graph_diff.py** — `GraphDiffer` captures graph versions and computes deltas. `capture()` snapshots node/edge state. `diff_from_version()` and `diff_between_versions()` produce `GraphDelta` with added/removed/modified nodes and edges. `rollback_to_version()` restores a prior state.

## Terminology Mapping

This table documents the mathematical status of named algorithms and metrics in the codebase. Entries marked "Heuristic" use structural approximations rather than formal mathematics; entries marked "Rigorous" implement textbook algorithms correctly.

| Feature | Implementation | Module | Mathematical Status |
|---|---|---|---|
| Structural anomaly detection | Cycle detection + eigenvector centrality + label contradiction matching | `structural_anomaly.py` | Heuristic |
| Contradiction detection | Hardcoded contradictory label pairs + near-disjoint source sets | `structural_anomaly.py` | Heuristic |
| Partial proofs | 2-hop BFS neighborhood exploration with Chernoff bounds | `structural_anomaly.py` | Heuristic (Chernoff bounds are rigorous, but the "proof" is a coverage count) |
| Multi-perspective analysis | Multi-perspective parameter selection (4 scalar complexity estimators) | `multi_perspective.py` | Heuristic |
| Local clustering coefficient | Triangle density of neighbor subgraph | `multi_perspective.py` | Rigorous |
| Perspective overlap | Jaccard containment of two BFS reachable sets | `multi_perspective.py` | Heuristic |
| Frame information loss | Product of complexity and information loss scalars | `multi_perspective.py` | Heuristic |
| High-level insights | Pattern detection from rule frequency and graph structure | `rule_analytics.py` | Heuristic |
| Concept correlation | Classical correlation matrix lookup between outcome distributions | `belief.py` | Classical |
| Born-rule sampling | Sampling from `|amplitude|^2` with complex amplitudes | `belief.py` | Rigorous |
| Von Neumann entropy | Density matrix eigenvalue entropy | `belief.py` | Rigorous |
| Von Neumann entropy (multi_perspective) | Normalized Shannon entropy over edge target distribution | `multi_perspective.py` | Heuristic (method renamed to `_normalized_shannon_entropy`) |
| Partial trace | Tensor contraction over subsystems | `belief.py` | Rigorous |
| Unitary evolution | Matrix multiplication with renormalization | `belief.py` | Rigorous |
| Computational density | Graph activity density (avg_degree * 0.25 + rule_diversity * 0.75) | `rule_analytics.py` | Weighted composite metric |
| Structural complexity | Mean of spectral entropy and motif diversity | `rule_analytics.py` | Composite metric |
| Conservative extension | Removed (was always `True`, not proof-theoretic) | `structural_anomaly.py` | N/A |
| Spectral entropy | SVD of adjacency matrix, Shannon entropy of singular values | `rule_analytics.py` | Rigorous |
| Kolmogorov complexity | zlib compression ratio | `multi_perspective.py` | Approximation (well-known technique) |
| Thompson sampling | Beta distribution sampling for frame/basis selection | `multi_perspective.py`, `belief.py` | Rigorous |
| Reciprocal Rank Fusion | Standard `1/(60+rank)` scoring | `multi_perspective.py` | Rigorous |
| Spectral gap complexity | Eigenvalue gap of local adjacency matrix | `multi_perspective.py` | Rigorous |
| State correlation | Dice coefficient of shared active nodes between multiway states | `state_clustering.py` | Structural metric |
| Hypergraph | Directed multigraph with n-ary edge storage, native hypergraph algorithms (union-find components, s-path shortest path, incidence-based PageRank, spectral embedding, s-persistence) | `kernel.py` | Rigorous (incidence matrix, Laplacian, s-connected components, hypergraph PageRank are textbook-correct; degrades to standard graph algorithms on pairwise edges) |
| Coherence time | Timeout-based exponential amplitude decay | `belief.py` | Heuristic (not environmental decoherence T1/T2) |
| MeasurementBasis | Named dimension weights + Thompson sampling for selection | `belief.py` | Heuristic (not a Hermitian operator; feature weighting profile) |
| Interference | Standard formula comparing \|sum(amps)\|^2 vs sum(\|amp\|^2) | `belief.py` | Rigorous |
| s-connected components | Union-find on hyperedge vertex overlap with threshold s | `kernel.py` | Rigorous (textbook s-walk framework from Aksoy et al.) |
| s-persistence filtration | Nested sequence of s-connected component structures | `kernel.py` | Rigorous (filtration on s-line graph) |
| Hypergraph PageRank | Incidence-based transition matrix P = D_v^{-1} H W D_e^{-1} H^T | `kernel.py` | Rigorous (Zhou, Huang, Schoelkopf 2006) |
| Hypergraph spectral embedding | Bottom-k eigenvectors of normalized hypergraph Laplacian | `kernel.py` | Rigorous |
| Hyperedge diffusion (AND/OR/majority) | Gate modes on n-ary edge activation flow | `retrieval_activation.py` | Structural heuristic (linear mode is rigorous; gate modes are practical extensions) |
| Spectral entropy (hypergraph) | SVD of incidence matrix, Shannon entropy of singular values | `rule_analytics.py` | Rigorous |

## File Layout

```
src/hyper3/          Source code (flat, no sub-packages)
  kernel.py          Thin facade composing 11 mixins, re-exports types
  kernel_types.py    Data structures: Hypernode, Hyperedge, Metadata, Modality, AbstractionLayer
  kernel_base.py     _GraphBase + CoreMixin: shared state, CRUD, merge, batch
  kernel_query.py    QueryMixin: edge lookups, neighbors, degree, stats, hash, degree_correlation
  kernel_paths.py    PathMixin: find_paths, shortest_path, Dijkstra, BFS
  kernel_components.py ComponentMixin: s-components, s-persistence, union-find, SCCs, biconnected, articulation, modularity, s_components_by_size
  kernel_cycles.py   CycleMixin: has_cycle, detect_cycles, girth, chordless_cycles
  kernel_centrality.py CentralityMixin: degree/betweenness/pagerank/katz/closeness/eigenvector centrality, eigenvector_centrality_numpy, katz_centrality_solve
  kernel_spectral.py SpectralMixin: incidence, Laplacian, adjacency, eigenvalues, Fiedler, bisection, bipartivity, Bethe-Hessian, transition matrix, incidence_by_order, multiorder_laplacian, dual_random_walk_adjacency, random_walk, random_walk_density, stationary_state, algebraic_connectivity
  kernel_clustering.py ClusteringMixin: clustering_coefficient, spectral_clustering, transitivity, square_clustering, triangles
  kernel_pattern.py  PatternMixin: pattern_match, subgraph
  kernel_transforms.py TransformMixin: to_networkx, to_dual, to_line_graph, to_bipartite, clique_projection, simplicial_complex, bipartite_projected_graph, bipartite_weighted_projection
  kernel_similarity.py SimilarityMixin: hyperedge_similarity
  exceptions.py      Exception hierarchy
  event_log.py       EventLog for timestamped event recording
  equivalence.py     EquivalenceEngine for node similarity
  cache.py           LazyCache with TTL and Markov prefetch
  traversal.py       TraversalEngine, SliceConfig, ObserverSlice
  evolution.py       GraphMaintenanceEngine, EvolutionMetrics
  belief.py          BeliefLayer and belief data types
  bayesian.py        BayesianLayer with CategoricalDistribution, Evidence
  rules.py           Rule ABC with 8 concrete implementations
  rules_discovery.py RuleDiscoveryEngine
  multiway.py        MultiwayEngine, MultiwayGraph, MultiwayState
  state_clustering.py StateClusteringEngine with distance/clustering
  multiway_causal.py StateConvergenceEngine
  rule_analytics.py RuleAnalytics for rule effectiveness tracking
  structural_anomaly.py StructuralAnomalyDetector
  multi_perspective.py MultiPerspectiveAnalyzer
  system_monitor.py  SystemMonitor
  memory.py          HypergraphMemory facade (thin, uses mixins)
  memory_base.py     _MemoryBase shared type annotations
  memory_core.py     CoreMixin: store, recall, relate, query, evolve
  memory_reasoning.py ReasoningMixin: reason, derive, commit/rollback
  memory_belief.py     BeliefMixin: create_distribution, sample, correlate
  memory_bayesian.py   BayesianMixin: set_prior, update_belief, get_belief
  memory_analytics.py AnalyticsMixin: paths, centrality, cycles
  memory_persistence.py PersistenceMixin: save/load, import/export
  memory_subsystems.py SubsystemMixin: temporal, enrichment, etc.
  persistence.py     Serializer for JSON save/load
  embedding.py       EmbeddingEngine with pluggable providers
  embedding_graph.py Graph-structure-aware embedding providers
  retrieval_activation.py SpreadingActivation
  retrieval_engine.py RetrievalEngine with RRF and learning-to-rank
  temporal.py        TemporalReasoner with Allen interval algebra
  provenance.py      ProvenanceTracker with explain/retract
  overlay.py         HypergraphOverlay for inference layers
  enrichment.py      LLMEnricher, RegexExtractor
  feedback.py        OperationFeedback for outcome tracking
  snapshot.py        SystemSnapshot for cross-session continuity
  frame_transform.py FrameTransformer with 12 pair-wise transforms
  validation.py      ValidationEngine with A/B comparison
  capabilities.py    CapabilityLevel enum + detection + require_capability
  constraints.py     ConstraintCheck ABC + BoundaryNavigator
  backward_chain.py  BackwardChainEngine for goal-directed reasoning
  hebbian.py         HebbianLearner for co-activation learning
  uncertainty.py     UncertaintyEngine for confidence propagation
  structural_match.py StructuralPatternEngine for subgraph matching
  belief_revision.py ContradictionResolver for contradiction resolution
  abstraction.py     AbstractionNavigator for hierarchical collapse/expand
  community.py       CommunityDetector for graph clustering
  graph_diff.py      GraphDiffer for versioned evolution tracking
  visualization.py   Optional matplotlib plotting
  __init__.py        Public API re-exports
tests/               Test files (test_<module>.py naming)
examples/            Example scripts organized by difficulty
  basic/             Foundational operations (store, recall, reason, retrieve)
  intermediate/      Single-subsystem deep dives (temporal, provenance, analytics, text)
  advanced/          Multi-subsystem workflows (overlay, iterative reasoning, multiway, belief)
  domain/            Full end-to-end domain applications
  README.md          Index of all examples
demos/               Runnable demo scripts
benchmarks/          Performance microbenchmarks and evaluation suite
pyproject.toml       Project config (hatchling build backend)
resources/           Reference patent documents (architecture spec)
ai/                  AI utility scripts for bulk operations
  add_docstrings.py  Bulk docstring insertion via AST
```
