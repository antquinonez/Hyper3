# Progress Tracker: Addressing Key Weaknesses

## Status Legend
- [x] Completed
- [ ] Not started

---

## Issue 001: Rename transfinite.py → structural_anomaly.py

### Module rename
- [x] Create `src/hyper3/structural_anomaly.py` with all renames and updated docstrings
- [x] Convert `src/hyper3/transfinite.py` to backward-compat shim

### Class/dataclass renames
- [x] `TransfiniteReasoner` → `StructuralAnomalyDetector`
- [x] `TransfiniteResult` → `AnomalyDetectionResult`
- [x] `PartialProof` → `ExplorationReport`
- [x] `UNDECIDABLE_PATTERNS` → `ANOMALY_PATTERNS`
- [x] `BoundaryIndicator` fields: `diagonalization_risk` → `contradiction_risk`, `known_undecidable_similarity` → `structural_anomaly_score`, `self_reference` → `cyclic_structure`, `universal_quantification` → `high_centrality`
- [x] Internal methods: `_assess_diagonalization` → `_detect_label_contradictions`, `_detect_self_reference` → `_detect_cycles`, `_detect_universal_quantification` → `_detect_high_centrality`, `_compare_to_known` → `_compute_structural_risk`, `_transfinite_approach` → `_anomaly_aware_approach`, `_build_partial_proof` → `_build_exploration_report`
- [x] Updated docstrings to describe actual algorithms
- [x] Updated insight strings (removed "Godel-like", "Cantor-style")

### Import updates
- [x] `src/hyper3/__init__.py`
- [x] `src/hyper3/memory_base.py`
- [x] `src/hyper3/memory.py`
- [x] `src/hyper3/memory_quantum.py` (new `detect_structural_anomalies` + backward-compat `reason_transfinite`)
- [x] `src/hyper3/memory_subsystems.py` (new `structural_anomaly` property + backward-compat `transfinite`)
- [x] `src/hyper3/memory_persistence.py`

### Backward compatibility
- [x] `BoundaryIndicator` supports both old field names (`self_reference`, etc.) and new names (`cyclic_structure`, etc.) via properties and `__init__` kwargs
- [x] `StructuralAnomalyDetector` has backward-compat method aliases (`_detect_self_reference`, etc.)
- [x] `transfinite.py` shim re-exports all old names
- [x] Status strings updated to `"low_risk"` / `"boundary"` / `"anomalous"` (backward-compat property `decidability_status` preserved)

---

## Issue 002: Rename relativity.py → multi_perspective.py

### Module rename
- [x] Create `src/hyper3/multi_perspective.py` with all renames and updated docstrings
- [x] Convert `src/hyper3/relativity.py` to backward-compat shim

### Class/method renames
- [x] `ComputationalRelativity` → `MultiPerspectiveAnalyzer`
- [x] `FrameMetrics` → `StructuralMetrics`
- [x] `compute_curvature` → `compute_local_clustering`
- [x] `compute_frame_dragging` → `compute_perspective_overlap`
- [x] `compute_redshift` → `compute_information_dissipation`
- [x] `compute_frame_metrics` → `compute_structural_metrics`
- [x] Updated docstrings to describe actual algorithms

### Import updates
- [x] `src/hyper3/__init__.py`
- [x] `src/hyper3/memory_base.py`
- [x] `src/hyper3/memory.py`
- [x] `src/hyper3/memory_subsystems.py`
- [x] `src/hyper3/memory_reasoning.py`
- [x] `src/hyper3/memory_persistence.py`
- [x] `src/hyper3/snapshot.py`

### Backward compatibility
- [x] `MultiPerspectiveAnalyzer` has backward-compat method aliases (`compute_curvature`, etc.)
- [x] `relativity.py` shim re-exports all old names
- [x] `StructuralMetrics` keeps same field names (`curvature`, `frame_dragging`, `redshift`)

---

## Issue 003: Add hypergraph primitives to kernel.py

- [x] `incidence_matrix()` — directed node-edge incidence matrix (sources +1, targets -1)
- [x] `hypergraph_laplacian()` — L = D_v - H W D_e^{-1} H^T
- [x] `outgoing_edges(node_id)` — edges where node is in source_ids
- [x] `incoming_edges(node_id)` — edges where node is in target_ids
- [x] `out_neighbors(node_id)` — target IDs of outgoing edges
- [x] `in_neighbors(node_id)` — source IDs of incoming edges
- [x] All existing tests pass

---

## Issue 004: Cross-cutting terminology cleanup

### Phase 1: High-severity renames (completed previously)
- [x] `multiway_rulial.py`: `TranscendentalInsight` → `HighLevelInsight` (with backward-compat alias)
- [x] `multiway_rulial.py`: `generate_transcendental_insights` → `generate_high_level_insights` (with backward-compat alias)
- [x] `memory_quantum.py`: `reason_transfinite` → `detect_structural_anomalies` (with backward-compat alias)
- [x] `memory_quantum.py`: Updated docstrings for `map_boundaries`
- [x] `memory_subsystems.py`: `transfinite` property → `structural_anomaly` property (with backward-compat alias)
- [x] `__init__.py`: Added `HighLevelInsight` export alongside `TranscendentalInsight`
- [x] Updated docstrings for renamed methods in structural_anomaly.py

### Phase 2: Medium-severity renames (this pass)
- [x] `RulialPosition.computational_density` → `graph_activity_density`
- [x] `RulialPosition.causal_graph_complexity` → `structural_complexity`
- [x] `RulialAnalysis.computational_density` → `graph_activity_density`
- [x] `RulialAnalysis.causal_complexity` → `structural_complexity`
- [x] `RuleNeighborhoodResult.computational_density` → `graph_activity_density`
- [x] Removed `conservative_extension` (always True) from structural_anomaly.py boundary results
- [x] Removed `StructuralMetrics.curvature` / `frame_dragging` / `redshift` backward-compat properties
- [x] `QuantumEntanglement` → `ConceptCorrelation` across all files
- [x] `BranchialEntanglement` → `BranchialCorrelation` across all files
- [x] `EntanglementError` → `CorrelationError`
- [x] `entangle()` → `correlate()` in CognitiveMemory
- [x] `collapse_entangled()` → `collapse_correlated()`
- [x] `create_entanglement()` → `create_correlation()`
- [x] `detect_entanglements()` → `detect_correlations()`
- [x] `entanglement_ids` → `correlation_ids` on QuantumState
- [x] `entanglements` property → `correlations` (both quantum and branchial)
- [x] Updated `BranchialAnalysis.entanglements` → `correlations`, `avg_entanglement_correlation` → `avg_correlation_strength`
- [x] Updated snapshot serialization: `quantum_entanglements` → `quantum_correlations`
- [x] Updated all test files (9 test files, 82 references)
- [x] Updated all demos and examples (4 files)
- [x] Updated AGENTS.md Terminology Mapping table with all new renames

---

## Documentation Updates

- [x] Updated `AGENTS.md` DP-13 section (transfinite → structural anomaly)
- [x] Updated `AGENTS.md` Architecture section
- [x] Updated `AGENTS.md` File Layout table
- [x] Updated `AGENTS.md` Extracted Modules section
- [x] Added Terminology Mapping table to `AGENTS.md`

---

## Validation

- [x] Full test suite: **1354 passed**
- [x] Type checker: **0 errors, 0 warnings, 0 informations**
