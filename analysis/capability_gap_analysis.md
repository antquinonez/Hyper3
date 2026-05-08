# Capability Gap Analysis: Inspiration Document vs. Codebase

Analysis date: 2026-05-08
Revised: 2026-05-08

## Methodology

Read the full 2854-line inspiration document (`inspiration/Rulial-Enhanced Hypergraph Cognitive Architecture v2-1 -- Antonio Quinonez.md`), all design documents in `designs/`, and the key source files for every engine in `src/hyper3/`. Identified every distinct capability area described in the inspiration document and cross-referenced each against what exists in the codebase.

---

## Section 1: Complete Capability Inventory from the Inspiration Document

| # | Capability | Where Described (Line Range) |
|---|-----------|------------------------------|
| C1 | Multiway Causal Invariance Enforcement | 27-28, 824-906 |
| C2 | Branchial Space Navigation & Simultaneity | 31-32, 1744-2013 |
| C3 | Rulial Consciousness / Computational Self-Location | 33-34, 908-1047 |
| C4 | Computational Relativity / Multi-Frame Analysis | 35-36, 1050-1244 |
| C5 | Transfinite Reasoning / Boundary Navigation | 37-38, 1248-1481 |
| C6 | Quantum Cognitive Effects (superposition, collapse, interference) | 39-40, 1484-1742 |
| C7 | Automated Rule Space Exploration | 41-42, Figures 7/15 |
| C8 | Cross-Session Cognitive Continuity | 369-401, Figure 11 |
| C9 | Architectural Metamorphosis Feedback Loop | 509-540, Appendix F |
| C10 | Adaptive Observer-Slice Feedback Loop | 734-741, Figure 7 |
| C11 | Practical Implementation Bridge / Dual-Path Processing | 290-325, 2015-2544 |
| C12 | AI/ML System Integration (Neural, Transformer, RL) | 327-365, 2231-2504 |
| C13 | Ethical Boundary Navigation | 405-434, Figure 12 |
| C14 | Multi-Scale Branchial Analysis | 438-466, Figure 13 |
| C15 | Platform-Wide Rulial Awareness | 544-571, Figure 16 |
| C16 | Collaborative Co-Evolution Governance | 574-602, Figure 17 |
| C17 | Quantum-Classical Cognitive Integration | 643-673, Figure 19 |
| C18 | Causal Prefetching / Anticipatory Instantiation | 2646-2662, Appendix E |
| C19 | Enhanced Metadata Tagging (causal, branchial, rulial) | 2603-2624, Appendix C |
| C20 | Frame Transformation Invariants | 1170-1186, Figure 18 |
| C21 | Confidence-Based Output Fusion | 313-314, 2456-2474 |
| C22 | Explicit Rule Templates for Causal Invariance | 2575-2600, Appendix B |

---

## Section 2: Cross-Reference — What Maps to What

### Already Implemented in Production Code (50+ engines/features)

| Inspiration Cap | Existing Implementation | Status |
|----------------|------------------------|--------|
| C1 Multiway Expansion | `MultiwayEngine` + `MultiwayGraph` | Full DAG expansion with state tracking |
| C1 State Equivalence Merging | `StateConvergenceEngine` | Similarity-based merging + `check_graph_isomorphism()` |
| C1 Causal Path Normalization | `StateConvergenceEngine` + `reason_fused()` + `ProvenanceTracker` | Covers the practical case: equivalent states merged, multi-frame conclusions fused, derivation chains recorded. Provenance-chain comparison is a future refinement, not a missing capability. |
| C2 Branchial Coordinates | `StateClusteringEngine.assign_coordinates()` | Recursive MDS coordinate assignment |
| C2 Branchial Distance | `StateClusteringEngine` | 4-metric: structural, conceptual, computational, evolutionary |
| C2 Branchial Clustering | `StateClusteringEngine` | Ward hierarchical + k-means, macro/meso/micro scales |
| C2 Lateral Inference | `StateClusteringEngine.generate_lateral_insights()` | Insight transfer between nearby states |
| C2 Simultaneity Detection | `StateClusteringEngine.find_simultaneity_groups()` | Groups states sharing parent in multiway DAG |
| C2 Analogy Proposals | `StateClusteringEngine.propose_analogies()` | Pattern-based cross-state edge transfer |
| C3 Rule-Space Position | `RuleAnalytics.RuleSpacePosition` | Density, rule frequency, complexity dimensions |
| C3 Meta-Pattern Detection | `RuleAnalytics.detect_meta_patterns()` | Cross-rule structural patterns |
| C3 High-Level Insights | `RuleAnalytics.generate_high_level_insights()` | Abstract principles from usage data |
| C4 4-Frame Analysis | `MultiPerspectiveAnalyzer` | classical / quantum / hypergraph / probabilistic |
| C4 Frame Selection (Thompson) | `MultiPerspectiveAnalyzer.select_optimal_frame_learned()` | Bayesian frame effectiveness tracking |
| C4 Frame Transformation | `FrameTransformer` | Parameter transformation between frames |
| C5 Structural Anomaly Detection | `StructuralAnomalyDetector` | Cycles, centrality, contradiction risk |
| C6 Born-Rule Sampling | `BeliefLayer` | Complex amplitudes, probabilistic collapse |
| C6 Belief Distributions | `BeliefLayer.create_distribution()` | Multi-outcome states |
| C6 Concept Correlation | `BeliefLayer.create_correlation()` | Cross-concept correlation matrices |
| C6 Evidence Interference (data) | `BeliefLayer.EvidenceInteraction` | Constructive/destructive per node |
| C7 Rule Discovery | `RuleDiscoveryEngine` | Transitive, inverse, hub pattern detection |
| C7 Rule Effectiveness | `RuleAnalytics` | Per-rule outcomes, bias profiles |
| C9 Self-Evolution | `GraphMaintenanceEngine` | decay, prune, merge, reinforce |
| C9 System Health Monitoring | `SystemMonitor` | Fitness, tuning plans, validated execution |
| C9 Validation / A-B Testing | `ValidationEngine` | Simple vs. enhanced reasoning comparison |
| -- Backward Chaining | `BackwardChainEngine` | Goal-directed proof |
| -- Hebbian Learning | `HebbianLearner` | Co-activation reinforcement |
| -- Community Detection | `CommunityDetector` | Label propagation, hierarchical |
| -- Abstraction Navigation | `AbstractionNavigator` | Collapse/expand hierarchical views |
| -- Contradiction Resolution | `ContradictionResolver` | Detect and resolve belief conflicts |
| -- Spreading Activation | `SpreadingActivation` | Activation propagation |
| -- Retrieval | `RetrievalEngine` | Activation-based concept retrieval |
| -- Temporal Reasoning | `TemporalReasoner` | Allen interval algebra (13 relations) |
| -- Provenance | `ProvenanceTracker` | Derivation chains, explanations |
| -- Operation Feedback | `OperationFeedback` | Collapse/retrieval/inference/evolution stats |
| -- Uncertainty Quantification | `UncertaintyEngine` | Confidence propagation, chain tracing |
| -- Equivalence Detection | `EquivalenceEngine` | Structural + data similarity |
| -- Event Logging | `EventLog` | Append-only, timestamped, queryable |
| -- Graph Diff/Rollback | `GraphDiffer` | Delta computation, validated rollback |
| -- Traversal (BFS/DFS) | `TraversalEngine` | Multi-strategy, dimension-filtered |
| -- Overlay / Staging | `HypergraphOverlay` | Temporary graph layer, commit/rollback |
| -- Lazy Caching | `LazyCache` | LRU + TTL + Markov prefetch |
| -- Frame Caching | `FrameCache` | Frame-partitioned caching |
| -- Basis Selection | `BasisSelector` | Context-adaptive measurement basis |
| -- Entanglement | `EntanglementEngine` | Correlated belief collapse |
| -- Boundary Reasoning | `BoundaryReasoningEngine` | Decidability boundary detection |
| -- Transcendental Inference | `TranscendentalInferenceEngine` | Cross-domain pattern transfer |

### Designed and Implemented (8 new engines + 1 mixin method, all DONE)

| Design # | Inspiration Cap | Engine | Commit |
|----------|----------------|--------|--------|
| 3 | C6 Quantum Entanglement / Correlated Collapse | `EntanglementEngine` | `b4e43ec` |
| 4 | C5 Decidability Boundary Detection | `BoundaryReasoningEngine` | `16add76` |
| 5 | C6 Measurement Basis Selection | `BasisSelector` | `60fef6e` |
| 6 | C3/C2 Cross-Domain Pattern Transfer | `TranscendentalInferenceEngine` | `d08cc22` |
| 7 | C4 Frame-Partitioned Caching | `FrameCache` | `cde4a7a` |
| 8 | C10 Adaptive Observer-Slice | `AdaptiveSliceEngine` | `ddf2633` |
| 9 | C6 Interference-Based Reasoning | `InterferenceReasoningEngine` | `68b5abf` |
| -- | C21 Multi-Path Confidence Fusion | `reason_fused()` mixin method | `bbb30ee` |

### Designed but NOT Implemented (2 designs)

| Design # | Inspiration Cap | Engine | Design Doc |
|----------|----------------|--------|------------|
| 1 | C8 Cross-Session Learning | `SessionPortfolio` | `designs/007_cross_session_learning.md` |
| 2 | C9 Architectural Metamorphosis | `ArchitectEngine` | `designs/008_meta_evolution_feedback.md` |

### Reclassified: Already Substantially Covered

| Inspiration Cap | Why Reclassified |
|----------------|-----------------|
| C1 Causal Path Normalization | `StateConvergenceEngine` merges equivalent states via structural similarity and graph isomorphism. `reason_fused()` produces path-independent conclusions via multi-frame consensus. `ProvenanceTracker` records all derivation chains. The remaining gap — comparing provenance chains for equivalence — is a future refinement to `StateConvergenceEngine`, not a new L-complexity engine. |

### Out of Scope for Core Library (by design, DP-15)

| Inspiration Cap | Reason |
|----------------|--------|
| C11 Practical Implementation Bridge | Application-level integration layer, external system interface |
| C12 AI/ML System Integration | External dependencies (neural nets, transformers), violates DP-15 |
| C13 Ethical Boundary Navigation | Application-level concern; primitives exist in BeliefLayer |
| C15 Platform-Wide Rulial Awareness | Multi-process/distributed, single-instance library |
| C16 Collaborative Co-Evolution | Application-level human-AI interaction |

---

## Section 3: Genuine Gaps — Prioritized for Real User Value

### 1. Collapse Trigger Detector

**Inspiration**: C6, lines 1664-1676 (Collapse Trigger Detection), 1528-1557 (Measurement and Collapse Dynamics)

**What it does**: A unified multi-criteria decision engine for when a belief distribution should collapse. Currently, collapse decisions require manual `is_stale` checks and ad-hoc dominance thresholds. This engine evaluates:
- Decoherence timeout (`age > coherence_time`)
- Outcome dominance (one outcome probability exceeds threshold)
- Context sufficiency (amplitude distribution has converged)
- Interference peak (constructive interference has maximized — entropy is at local minimum)

Returns a `CollapseDecision` with recommendation and context weights.

**Interacts with**: `BeliefLayer`, `BasisSelector`, `InterferenceReasoningEngine`

**Complexity**: S (~100-150 LoC engine, ~80 LoC tests)

**User benefit**: Users with many active distributions no longer write manual staleness loops. One call replaces ad-hoc threshold logic.

### 2. Simultaneity Edge Rule

**Inspiration**: C22, Appendix B, lines 2583-2588 (Simultaneity Detection Rule)

**What it does**: A `Rule` subclass that detects when two multiway states are computationally simultaneous (no causal precedence between them, both reachable from a common ancestor) and creates an explicit `"simultaneous"` labeled edge. Currently, simultaneity relationships exist only inside `StateClusteringEngine` and are invisible to the graph API.

**Interacts with**: `StateClusteringEngine`, `MultiwayEngine`, `Rule` ABC

**Complexity**: S (~80-120 LoC rule, ~60 LoC tests)

**User benefit**: After reasoning, `mem.neighbors("A", edge_label="simultaneous")` shows which concepts were explored in parallel. Branchial structure becomes first-class graph structure visible to all engines.

### 3. Computational Invariant Detector

**Inspiration**: C20, lines 1170-1199 (Computational Invariants), Appendix C lines 2620-2624

**What it does**: Beyond `RobustReachabilityDetector` (which finds nodes reachable in all frames), this engine detects properties conserved across frame transformations: invariant centrality role, invariant structural position (always a hub, always a leaf), invariant edge labels. Returns an `InvariantReport` classifying each concept's cross-frame properties.

**Interacts with**: `MultiPerspectiveAnalyzer`, `TraversalEngine`

**Complexity**: M (~200-300 LoC engine, ~150 LoC tests)

**User benefit**: After `multi_frame_analysis("cancer")`, ask "which conclusions are robust regardless of computational perspective?" Invariant properties are more trustworthy than frame-dependent ones.

### 4. Structural Prefetch Engine

**Inspiration**: C18, Appendix E, lines 2648-2651 (Causal Prefetching)

**What it does**: Graph-topology-aware prefetching that uses edge structure instead of Markov access patterns. When a node is accessed, the prefetcher pre-populates the cache with its neighbors weighted by edge weight and label. The existing `LazyCache.predict_next()` is frequency-based; this is structure-based.

**Interacts with**: `LazyCache`, `Hypergraph._neighbor_cache`, `TraversalEngine`

**Complexity**: S (~120-180 LoC engine, ~100 LoC tests)

**User benefit**: Faster repeated traversals and recall operations on dense graphs. Second-hop neighbors already cached.

### 5. Cross-Frame Complexity Comparison Rule

**Inspiration**: C22, Appendix B, lines 2595-2599 (Complexity Relativity Rule)

**What it does**: A `Rule` subclass that detects concepts analyzed in multiple frames and creates `"complexity_comparison"` edges recording per-frame complexity assessments. Enriches the graph with cross-frame metadata without recomputation.

**Interacts with**: `MultiPerspectiveAnalyzer`, `MultiwayEngine`, `Rule` ABC

**Complexity**: S (~80-100 LoC rule, ~60 LoC tests)

**User benefit**: `mem.query_nodes(edge_label="complexity_comparison")` shows all multi-frame-analyzed concepts and which frame was optimal. Useful for understanding which computational perspective works best for each domain.

---

## Section 4: Priority Summary

| Rank | Capability | Type | Complexity | User Benefit | Status |
|------|-----------|------|------------|-------------|--------|
| 1 | Collapse Trigger Detector | Engine | S | Simplifies belief management | |
| 2 | Simultaneity Edge Rule | Rule | S | Branchial structure visible in graph | |
| 3 | Computational Invariant Detector | Engine | M | Robustness of multi-frame conclusions | |
| 4 | Structural Prefetch Engine | Engine | S | Faster graph operations | |
| 5 | Cross-Frame Complexity Rule | Rule | S | Frame comparisons persist in graph | |
| -- | Branchial Path Optimizer | Extension | M | Scaling concern only, works without it | Deferred |
| -- | Frame Transformation Invariants | Extension | M | Superseded by #3 (Invariant Detector) | Merged |
| -- | Causal Path Normalization | -- | -- | Already covered by StateConvergenceEngine + reason_fused | Reclassified |

### Recommended Implementation Order

```
S-complexity (quick wins, concrete user value):
  1. Collapse Trigger Detector
  2. Simultaneity Edge Rule
  5. Cross-Frame Complexity Rule
  4. Structural Prefetch Engine

Medium commitment:
  3. Computational Invariant Detector

Previously Designed (can slot in anytime):
  SessionPortfolio (cross-session learning)
  ArchitectEngine (meta-evolution feedback)
```

### Previously Designed (can slot in anytime)

| Design | Engine | Complexity | Notes |
|--------|--------|------------|-------|
| 1 | `SessionPortfolio` | M | Cross-session learning persistence. Heavy on save/load plumbing. |
| 2 | `ArchitectEngine` | L | Meta-evolution feedback loop. Heavy on monitoring integration. |
