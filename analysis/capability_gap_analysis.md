# Capability Gap Analysis: Inspiration Document vs. Codebase

Analysis date: 2026-05-08

## Methodology

Read the full 2854-line inspiration document (`inspiration/Rulial-Enhanced Hypergraph Cognitive Architecture v2-1 -- Antonio Quinonez.md`), all 9 design documents in `designs/`, and the key source files for every engine in `src/hyper3/`. Identified every distinct capability area described in the inspiration document and cross-referenced each against what exists in the codebase.

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

### Already Implemented in Production Code (40+ engines/features)

| Inspiration Cap | Existing Implementation | Status |
|----------------|------------------------|--------|
| C1 Multiway Expansion | `MultiwayEngine` + `MultiwayGraph` | Full DAG expansion with state tracking |
| C1 State Equivalence Merging | `StateConvergenceEngine` | Similarity-based merging + `check_graph_isomorphism()` |
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

### Designed and Implemented (6 new engines + 1 mixin method, all DONE)

| Design # | Inspiration Cap | Engine | Commit |
|----------|----------------|--------|--------|
| 3 | C6 Quantum Entanglement / Correlated Collapse | `EntanglementEngine` | `b4e43ec` |
| 4 | C5 Decidability Boundary Detection | `BoundaryReasoningEngine` | `16add76` |
| 5 | C6 Measurement Basis Selection | `BasisSelector` | `60fef6e` |
| 6 | C3/C2 Cross-Domain Pattern Transfer | `TranscendentalInferenceEngine` | `d08cc22` |
| 7 | C4 Frame-Partitioned Caching | `FrameCache` | `cde4a7a` |
| 8 | C10 Adaptive Observer-Slice Feedback Loop | `AdaptiveSliceEngine` | pending |
| -- | C21 Multi-Path Confidence Fusion | `reason_fused()` mixin method | `bbb30ee` |

### Designed but NOT Implemented (2 designs)

| Design # | Inspiration Cap | Engine | Design Doc |
|----------|----------------|--------|------------|
| 1 | C8 Cross-Session Learning | `SessionPortfolio` | `designs/007_cross_session_learning.md` |
| 2 | C9 Architectural Metamorphosis | `ArchitectEngine` | `designs/008_meta_evolution_feedback.md` |

### Out of Scope for Core Library (by design, DP-15)

| Inspiration Cap | Reason |
|----------------|--------|
| C11 Practical Implementation Bridge | Application-level integration layer, external system interface |
| C12 AI/ML System Integration | External dependencies (neural nets, transformers), violates DP-15 |
| C13 Ethical Boundary Navigation | Application-level concern; primitives exist in BeliefLayer |
| C15 Platform-Wide Rulial Awareness | Multi-process/distributed, single-instance library |
| C16 Collaborative Co-Evolution | Application-level human-AI interaction |

---

## Section 3: Unimplemented Capabilities — Prioritized Analysis

After eliminating everything that is implemented, designed, or out of scope, **8 genuine gaps** remain.

### 1. Causal Path Normalization Engine

**What it does**: Detects when different multiway reasoning paths produce equivalent *causal histories* (not just similar state node sets) and normalizes them to a canonical form. Currently, `StateConvergenceEngine` merges states with similar node/edge overlaps, but two paths can produce identical conclusions via structurally different derivation chains that are NOT recognized as equivalent.

**Interacts with**: `StateConvergenceEngine`, `ProvenanceTracker`, `MultiwayEngine`, `EventLog`

**New engine or extension**: New engine. `StateConvergenceEngine` does structural similarity (Jaccard overlap of node/edge sets). Causal normalization requires comparing *derivation trees* (provenance chains) — a fundamentally different operation.

**Complexity**: L (~400-500 LoC engine, ~300 LoC tests)

**Why it matters**: This is the #1 claim in the inspiration document and the differentiating feature of the architecture. Without it, the system can reach identical conclusions via two paths and treat them as different knowledge. The `ProvenanceTracker` already records everything needed as input.

### 2. Interference-Based Reasoning Engine

**What it does**: Systematically analyzes constructive and destructive interference patterns across the belief layer, uses interference maxima as collapse triggers, and generates insights from interference structure. The `EvidenceInteraction` dataclass already tracks constructive/destructive amplitudes per node, but this data is never used to trigger sampling decisions, detect graph-wide interference patterns, or inform reasoning strategy.

**Interacts with**: `BeliefLayer`, `EntanglementEngine`, `BasisSelector`, `TranscendentalInferenceEngine`

**New engine or extension**: New engine.

**Complexity**: M (~250-350 LoC engine, ~200 LoC tests)

**Why it matters**: This is what makes the quantum cognitive effects genuinely quantum-inspired rather than just fancy probability distributions. The inspiration doc dedicates ~250 lines (1484-1742) to interference patterns. Currently the implementation only uses Born-rule sampling.

### 3. Adaptive Observer Slice Engine

**Status**: DONE. Implemented as `AdaptiveSliceEngine` in `adaptive_slice.py` with Thompson sampling over a 100-cell grid (5 depths x 5 nodes x 4 weights). Wired into `CoreMixin` via `recall_adaptive()` and `record_slice_outcome()`. 24 unit tests in `test_adaptive_slice.py`. Exports in `__init__.py`.

### 4. Computational Density Mapper

**Status**: MOSTLY EXISTS. `RuleAnalytics` already has `compute_density_map()`, `identify_frontiers()`, `explore_rule_neighborhood()`, and position history tracking. No new engine needed.

### 5. Branchial Path Optimizer

**What it does**: Finds efficient navigation routes through branchial space and dynamically reorganizes coordinates as the multiway graph grows. Currently `StateClusteringEngine.assign_coordinates()` computes coordinates once and never updates.

**Interacts with**: `StateClusteringEngine`, `MultiwayEngine`, `LazyCache`

**New engine or extension**: Extension of `StateClusteringEngine`.

**Complexity**: M (~200-300 LoC extension, ~150 LoC tests)

**Why it matters**: Without path optimization, branchial navigation is undirected. Becomes important for large multiway graphs.

### 6. Multi-Path Confidence Fusion

**Status**: DONE. Implemented as `reason_fused()` in `memory_reasoning.py` with `FusedReasonResult` and `FrameContribution` result types. 10 tests in `test_memory.py::TestReasonFused`. Supports weighted, majority, and union fusion strategies. Runs reasoning through multiple frames sequentially (cumulative), collects confidence maps, and fuses edges.

### 7. Causal Prefetcher

**What it does**: Predicts which nodes/edges will be needed next based on causal patterns and pre-warms the cache. `LazyCache` has Markov prefetching but doesn't use causal structure.

**Interacts with**: `LazyCache`, `RuleAnalytics`, `TraversalEngine`

**New engine or extension**: Extension of `LazyCache`.

**Complexity**: S (~80-100 LoC extension, ~60 LoC tests)

**Why it matters**: Performance optimization only. Worth doing after profiling reveals cache-miss bottlenecks.

### 8. Frame Transformation Invariants

**What it does**: Detects properties conserved across frame transformations (analogous to conservation laws in physics). `FrameTransformer` transforms parameters but doesn't identify what is preserved.

**Interacts with**: `FrameTransformer`, `MultiPerspectiveAnalyzer`, `FrameCache`

**New engine or extension**: Extension of `FrameTransformer`.

**Complexity**: M (~150-200 LoC, ~100 LoC tests)

**Why it matters**: Most theoretical gap. Practical value unclear — existing heuristics work well without explicit invariant tracking.

---

## Section 4: Priority Summary

| Rank | Capability | New Engine? | Complexity | Value | Status |
|------|-----------|-------------|------------|-------|--------|
| 1 | Causal Path Normalization | Yes | L | Core architecture claim. Path-independent reasoning. | |
| 2 | Interference-Based Reasoning | Yes | M | Genuinely novel quantum-inspired capability. | |
| 3 | Adaptive Observer Slice | Yes | S-M | Closes usage-to-view feedback loop. | DONE (AdaptiveSliceEngine) |
| 4 | Computational Density Mapper | Extends RuleAnalytics | S | Completes computational self-location. | DONE (already in RuleAnalytics) |
| 5 | Multi-Path Confidence Fusion | Mixin wiring | S | Extracts complementary value from all frames. | DONE (reason_fused) |
| 6 | Branchial Path Optimizer | Extends StateClustering | M | Scales branchial navigation. | |
| 7 | Causal Prefetcher | Extends LazyCache | S | Performance optimization only. | |
| 8 | Frame Transformation Invariants | Extends FrameTransformer | M | Theoretical. Practical value unclear. | |

### Recommended Implementation Order

```
DONE:
  4. Computational Density Mapper (already in RuleAnalytics)
  5. Multi-Path Confidence Fusion (reason_fused in memory_reasoning.py)
  3. Adaptive Observer Slice (AdaptiveSliceEngine in adaptive_slice.py)

Next — Novel engines (new capabilities):
  2. Interference-Based Reasoning

Large commitment:
  1. Causal Path Normalization

Optimization/Theoretical (defer):
  6. Branchial Path Optimizer
  7. Causal Prefetcher
  8. Frame Transformation Invariants
```

### Previously Designed (can slot in anytime)

| Design | Engine | Complexity | Notes |
|--------|--------|------------|-------|
| 1 | `SessionPortfolio` | M | Cross-session learning persistence. Heavy on save/load plumbing. |
| 2 | `ArchitectEngine` | L | Meta-evolution feedback loop. Heavy on monitoring integration. |
