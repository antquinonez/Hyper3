# Plan 002: Rename "branchial" namespace to StateClustering

## Summary

Replace the "branchial" terminology (from Wolfram's branchial space) with names
that describe what the code actually does: MDS coordinate assignment, k-means
clustering, and distance metrics on multiway expansion states.

## What the Code Actually Does

`BranchialSpace` (in `multiway_branchial.py`):
- Assigns coordinates to multiway states via multidimensional scaling (MDS)
- Computes pairwise distance metrics between states (structural, conceptual, computational)
- Clusters states using k-means on those coordinates
- Detects correlations between state pairs
- Generates lateral inference insights from nearby states
- Provides multi-scale analysis (macro/meso/micro clustering)
- Supports A* shortest path between states in coordinate space

`BranchialRelation` (in `multiway.py`):
- Records distance and shared features between sibling states during expansion
- Stores the Jaccard-like distance between two states via their common ancestor

The name "branchial" references Wolfram's branchial space (the space of
branching histories in a multiway system). The actual implementation is a
standard dimensionality-reduction + clustering + distance-metric pipeline on
multiway states.

## Proposed Renames

### Classes

| Current Name | Proposed Name | Rationale |
|---|---|---|
| `BranchialSpace` | `StateClusteringEngine` | Core engine that clusters multiway states |
| `BranchialCoordinates` | `StateCoordinates` | Position vector for a state in the clustered space |
| `BranchialCluster` | `StateCluster` | A cluster of multiway states |
| `BranchialCorrelation` | `StateCorrelation` | Correlation between two states' active-node sets |
| `BranchialDistanceMetrics` | `StateDistanceMetrics` | Distance metrics between two states |
| `BranchialRelation` | `StateRelation` | Relation between sibling states (distance, shared features) |
| `BranchialAnalysis` | `StateClusteringReport` | Summary result dataclass |

### Module

| Current | Proposed |
|---|---|
| `multiway_branchial.py` | `state_clustering.py` |
| `test_multiway_branchial.py` | `test_state_clustering.py` |

### Fields and variables

| Current | Proposed | Scope |
|---|---|---|
| `_branchial` | `_state_clustering` | Internal field on memory/mixin classes |
| `branchial` (property) | `state_clustering` | Public property on facade |
| `branchial_report` | `clustering_report` | Local variables in reasoning pipeline |
| `branchial=` (keyword arg) | `clustering=` | ReasonResult and similar constructors |
| `_branchial_relations` | `_state_relations` | MultiwayGraph internal field |
| `branchial_distance()` (on MultiwayGraph) | `jaccard_distance()` | Computes Jaccard distance between states |
| `get_branchial_relations()` | `get_state_relations()` | Accessor on MultiwayGraph |
| `_update_branchial()` | `_update_state_relations()` | Internal method on MultiwayGraph |
| `branchial_distance` (field on LateralInferenceInsight) | `state_distance` | Field name on result dataclass |

### On RuleSpacePosition (from plan 001)

| Current | Proposed | Rationale |
|---|---|---|
| `branchial_coordinates` (field) | `expansion_coordinates` | Distinguish from `StateCoordinates` dataclass; describes multiway expansion state |
| `_compute_branchial_coords()` | `_compute_expansion_coords()` | Private method in rule_analytics.py |
| `branchial_coordinates` (in snapshot) | `expansion_coordinates` | Snapshot field names |

### On SystemSnapshot (snapshot.py)

| Current | Proposed |
|---|---|
| `branchial_coordinates` | `state_coordinates` |
| `branchial_distance_cache` | `state_distance_cache` |
| `branchial_clusters` | `state_clusters` |

Note: The snapshot field names serialize to disk. Since this is pre-release with
no backward compatibility, direct rename is acceptable.

### In visualization.py

| Current | Proposed |
|---|---|
| `plot_branchial_space()` | `plot_state_clustering()` |
| `_extract_branchial_positions()` | `_extract_clustering_positions()` |
| `_draw_branchial_scatter()` | `_draw_clustering_scatter()` |
| `_draw_branchial_correlations()` | `_draw_clustering_correlations()` |

### String literals in docstrings/messages

- "branchial space" -> "state clustering space" or "clustering engine"
- "branchial coordinates" -> "state coordinates" (or "expansion coordinates" when on RuleSpacePosition)
- "branchial distance" -> "state distance" or "Jaccard distance"
- "branchial analysis" -> "clustering analysis"
- "Branchial Space Navigation" -> remove spec figure references, describe implementation

### Terms NOT changing (kept as-is)

- `SimultaneityGroup` — already implementation-reality language
- `MultiScaleAnalysis`, `ScaleLevel` — already descriptive
- `AnalogyProposal` — already descriptive
- `branchial_distance` in `LateralInferenceInsight` -> renamed to `state_distance`

## Files Requiring Changes (in order)

### Phase 1: Core module rename

1. **`src/hyper3/multiway_branchial.py` -> `src/hyper3/state_clustering.py`**
   - Rename file
   - Rename all 6 classes within
   - Update all docstrings
   - ~47 branchial references

2. **`src/hyper3/results.py`**
   - Rename `BranchialAnalysis` -> `StateClusteringReport`
   - Rename `branchial` field on `ReasonResult` -> `clustering`
   - Rename `branchial_distance` field on `LateralInferenceInsight` -> `state_distance`
   - Update docstrings
   - ~6 references

3. **`src/hyper3/__init__.py`**
   - Update imports from `multiway_branchial` -> `state_clustering`
   - Update all export names
   - ~8 references

### Phase 2: Engine consumers

4. **`src/hyper3/multiway.py`**
   - Rename `BranchialRelation` -> `StateRelation`
   - Rename `_branchial_relations` -> `_state_relations`
   - Rename `branchial_distance()` -> `jaccard_distance()`
   - Rename `get_branchial_relations()` -> `get_state_relations()`
   - Rename `_update_branchial()` -> `_update_state_relations()`
   - ~15 references

5. **`src/hyper3/rule_analytics.py`**
   - Rename `branchial_coordinates` field -> `expansion_coordinates`
   - Rename `_compute_branchial_coords()` -> `_compute_expansion_coords()`
   - Update docstrings
   - ~11 references

### Phase 3: Memory facade and mixins

6. **`src/hyper3/memory_base.py`**
   - Update import and type annotation
   - ~2 references

7. **`src/hyper3/memory.py`**
   - Update import and constructor
   - ~2 references

8. **`src/hyper3/memory_reasoning.py`**
   - Rename `_branchial` -> `_state_clustering`
   - Rename `branchial` property -> `state_clustering`
   - Rename `branchial_report` -> `clustering_report`
   - Rename `BranchialAnalysis` -> `StateClusteringReport`
   - Update `branchial=` keyword arg -> `clustering=`
   - ~22 references

9. **`src/hyper3/memory_belief.py`**
   - Update `_branchial` references -> `_state_clustering`
   - Update `branchial_distance` -> `state_distance`
   - ~6 references

10. **`src/hyper3/memory_persistence.py`**
    - Update `_branchial` -> `_state_clustering`
    - Update snapshot capture/restore variable names
    - ~4 references

11. **`src/hyper3/capabilities.py`**
    - Rename `_probe_branchial` -> `_probe_state_clustering`
    - Update field access
    - ~7 references

12. **`src/hyper3/snapshot.py`**
    - Update imports
    - Rename snapshot fields: `branchial_coordinates` -> `state_coordinates`, etc.
    - Rename `_capture_branchial` -> `_capture_state_clustering`
    - Rename `_restore_branchial` -> `_restore_state_clustering`
    - Update `expansion_coordinates` on rule analytics position
    - ~38 references

13. **`src/hyper3/visualization.py`**
    - Rename `plot_branchial_space` -> `plot_state_clustering`
    - Rename internal helpers
    - ~16 references

### Phase 4: Test files

14. **`tests/test_multiway_branchial.py` -> `tests/test_state_clustering.py`**
    - Rename file, update all class/method references
    - ~212 references

15. **`tests/test_visualization.py`** (~32 references)
16. **`tests/test_capabilities.py`** (~15 references)
17. **`tests/test_multiway.py`** (~7 references)
18. **`tests/test_memory.py`** (~6 references)
19. **`tests/test_rule_analytics.py`** (~5 references)
20. **`tests/test_snapshot.py`** (~2 references)
21. **`tests/test_system_monitor.py`** (~2 references)
22. **`tests/test_integration.py`** (~3 references)
23. **`tests/test_multiway_causal.py`** (~2 references)

### Phase 5: Examples and demos

24. **`demos/demo_full.py`** (~6 references)
25. **`demos/demo_multiway.py`** (~3 references)
26. **`demos/demo_integrated.py`** (~1 reference)
27. **`examples/advanced/10_multiway_lateral_insights.py`** (~15 references)
28. **`examples/comparison/10_multiway_lateral_insights.py`** (~2 references)

### Phase 6: Documentation

29. **`AGENTS.md`** (~14 references)
    - Update DP-12 title and description
    - Update Architecture section module listing
    - Update DP-2 example listing
    - Update Terminology Mapping table
    - Update Key Conventions (branchial-related)
    - Update File Layout section
    - Update Performance Indexes

## Execution Strategy

Same approach as plan 001: mechanical rename with validation after each phase.

### Phase ordering

1. Phase 1 (core module + results + __init__) — breaks all imports
2. Phase 2 (multiway.py + rule_analytics.py) — fixes engine-level consumers
3. Phase 3 (memory facade + mixins + snapshot + visualization + capabilities) — fixes all source
4. Run source-level validation: `python -c "from hyper3 import StateClusteringEngine"`
5. Phase 4 (tests) — run tests after completion
6. Phase 5 (examples/demos)
7. Phase 6 (AGENTS.md)

### Verification after each phase

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

## Risk Assessment

- **Low risk**: Mechanical rename, no algorithm changes
- **Medium risk**: Serialization key changes in snapshot.py break saved state files
- **High volume**: ~490 total references across ~29 files (largest rename in the project)
- **Estimated time**: 3-4 hours of careful find-and-replace

## Complexity Notes

This rename is significantly larger than the rulial rename (~380 refs) because:
1. `branchial` appears as field names on result dataclasses used in tests
2. `branchial_distance()` is a method on `MultiwayGraph` called from multiple places
3. `branchial_coordinates` appears on two different dataclasses with different rename targets
4. The visualization module has 4 public functions with `branchial` in their names
5. The snapshot module has 3 serialized fields plus restore logic

## Post-Rename Cleanup

After the rename, update this plan file to mark it complete, then update
`plans/001-rename-rulial.md` to note that `rule_analytics.py` still has
`_compute_expansion_coords()` referencing the old `branchial_coordinates` field
name on `RuleSpacePosition` (renamed to `expansion_coordinates` in this plan).
