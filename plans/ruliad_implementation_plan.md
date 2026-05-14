# Implementation Plan: Non-Standalone Designs

This document covers the implementation sequence for the 7 non-standalone
designs from the Ruliad inspiration batch. Standalone rules (032, 033, 038) are
implemented directly -- they only need a Rule subclass, test file, __init__.py
export, and rules.py registry entry.

## Shared Infrastructure Changes

These files are modified by multiple designs. Changes must be coordinated.

### memory_base.py
Add type declarations for new engines:
```python
_modality_fusion: ModalityFusionEngine | None
_context_compression: ContextCompressionEngine | None
_feedback_aware: FeedbackAwareEvolution | None
_consistency_verifier: ConsistencyVerifier | None
_causal_learner: CausalLearner | None
```

### memory.py
Add imports and facade shortcut methods:
```python
# New imports
from hyper3.modality_fusion import ModalityFusionEngine
from hyper3.context_compression import ContextCompressionEngine
from hyper3.evolution_feedback import FeedbackAwareEvolution
from hyper3.consistency import ConsistencyVerifier
from hyper3.causal_learner import CausalLearner

# Shortcut methods (follow existing pattern)
def compress_context(self, *, strategy="auto") -> CompressionResult: ...
def learn_causal_patterns(self) -> CausalLearningResult: ...
```

### __init__.py
Add exports for all new public classes.

## Implementation Phases

### Phase 1: Standalone Rules (no dependencies, parallel)
These have NO mixin/facade changes. Just engine + test + export + registry.

- [ ] 032: Analogical Reasoning Rule
  - NEW: `src/hyper3/rules_analogy.py`
  - NEW: `tests/test_rules_analogy.py`
  - MODIFY: `src/hyper3/rules.py` (+1 in from_dict registry)
  - MODIFY: `src/hyper3/__init__.py` (+1 export)

- [ ] 033: Pattern-Based Inductive Generalization
  - NEW: `src/hyper3/rules_inductive.py`
  - NEW: `tests/test_rules_inductive.py`
  - MODIFY: `src/hyper3/rules.py` (+1 in from_dict registry)
  - MODIFY: `src/hyper3/__init__.py` (+1 export)

- [ ] 038: Conceptual Decomposition Rule
  - NEW: `src/hyper3/rules_decomposition.py`
  - NEW: `tests/test_rules_decomposition.py`
  - MODIFY: `src/hyper3/rules.py` (+1 in from_dict registry)
  - MODIFY: `src/hyper3/__init__.py` (+1 export)

### Phase 2: Low-Effort Non-Standalone (minimal mixin changes)

- [ ] 037: Adaptive Slice Traversal Wiring
  - MODIFY: `src/hyper3/memory_core.py` (+30 LoC: adaptive flag in recall)
  - MODIFY: `src/hyper3/memory_structural.py` (+10 LoC: lazy init of AdaptiveSliceEngine)
  - MODIFY: `tests/test_adaptive_slice.py` (+80 LoC: wiring tests)
  - Integration points:
    - `CoreMixin.recall()` gets `adaptive` kwarg
    - On adaptive=True with no config: call `self._adaptive_slice.recommend(concept_id)`
    - After traversal: call `self._adaptive_slice.record_outcome(...)`
    - Lazy init: `AdaptiveSliceEngine` already has `_adaptive_slice` in memory_base

- [ ] 041: Context-Aware Cache Eviction
  - MODIFY: `src/hyper3/cache.py` (+120 LoC: context-aware eviction policy)
  - MODIFY: `tests/test_cache.py` (+150 LoC: context-aware tests)
  - MODIFY: `src/hyper3/memory_structural.py` (+10 LoC: context update hook)
  - MODIFY: `src/hyper3/memory.py` (+5 LoC: constructor option)
  - Integration points:
    - `LazyCache` gets `context_aware` constructor flag
    - `set()` gets optional `context_tags` parameter
    - `set_active_context()` method added
    - `_evict_for_capacity()` uses context tags
    - `recall()` / `activate()` call `_update_cache_context(concept)`

### Phase 3: Medium-Effort Non-Standalone (new engine + mixin method)

- [ ] 034: Cross-Modality Fusion Engine
  - NEW: `src/hyper3/modality_fusion.py` (~400 LoC)
  - NEW: `tests/test_modality_fusion.py` (~450 LoC)
  - MODIFY: `src/hyper3/memory_analytics.py` (+30 LoC: cross_modality method)
  - MODIFY: `src/hyper3/memory_base.py` (+1 type declaration)
  - MODIFY: `src/hyper3/__init__.py` (+3 exports)
  - Integration points:
    - `AnalyticsMixin.cross_modality(concept, modalities, weights, ...)` -> `FusionResult`
    - Lazy init `_modality_fusion` in AnalyticsMixin
    - `AnalyzeNamespace` gets passthrough (check namespaces.py for existing pattern)

- [ ] 035: Context Compression Engine
  - NEW: `src/hyper3/context_compression.py` (~350 LoC)
  - NEW: `tests/test_context_compression.py` (~400 LoC)
  - MODIFY: `src/hyper3/memory_structural.py` (+25 LoC: compress_context method)
  - MODIFY: `src/hyper3/memory_base.py` (+1 type declaration)
  - MODIFY: `src/hyper3/memory.py` (+8 LoC: shortcut)
  - MODIFY: `src/hyper3/__init__.py` (+3 exports)
  - Integration points:
    - `StructuralMixin.compress_context(strategy="auto")` -> `CompressionResult`
    - Uses `EquivalenceEngine` for candidate discovery
    - Uses `CommunityDetector` for cluster detection
    - Lazy init `_context_compression`

- [ ] 036: Feedback-Driven Structural Evolution
  - NEW: `src/hyper3/evolution_feedback.py` (~300 LoC)
  - NEW: `tests/test_evolution_feedback.py` (~350 LoC)
  - MODIFY: `src/hyper3/memory_core.py` (+20 LoC: enhanced evolve_with_feedback)
  - MODIFY: `src/hyper3/memory_base.py` (+1 type declaration)
  - MODIFY: `src/hyper3/__init__.py` (+3 exports)
  - Integration points:
    - Enhances existing `evolve_with_feedback()` in CoreMixin
    - Wraps `GraphMaintenanceEngine`, calls `evolve()` first
    - Then applies feedback-driven adjustments
    - Reads from existing `_activation`, `_rule_analytics`, `_feedback`, `_adaptive_slice`

- [ ] 039: Consistency Verification Layer
  - NEW: `src/hyper3/consistency.py` (~400 LoC)
  - NEW: `tests/test_consistency.py` (~400 LoC)
  - MODIFY: `src/hyper3/system_monitor.py` (+15 LoC: verify_invariants)
  - MODIFY: `src/hyper3/__init__.py` (+4 exports)
  - Integration points:
    - `SystemMonitor.verify_invariants(repair=False)` -> `VerificationResult`
    - `MonitorNamespace` gets passthrough
    - 7 invariant checks on graph structure
    - Optional repair mode

### Phase 4: High-Effort Non-Standalone

- [ ] 040: Probabilistic Causal Learning
  - NEW: `src/hyper3/causal_learner.py` (~500 LoC)
  - NEW: `tests/test_causal_learner.py` (~450 LoC)
  - MODIFY: `src/hyper3/memory_reasoning.py` (+30 LoC: learn + commit + hooks)
  - MODIFY: `src/hyper3/memory.py` (+8 LoC: shortcut)
  - MODIFY: `src/hyper3/memory_base.py` (+1 type declaration)
  - MODIFY: `src/hyper3/__init__.py` (+3 exports)
  - Integration points:
    - `ReasoningMixin.learn_causal_patterns()` -> `CausalLearningResult`
    - `ReasoningMixin.commit_causal_hypotheses()` -> `list[str]`
    - Observation hooks in `activate()` and `find_paths()`
    - Uses `SpreadingActivation` state for co-activation detection

## Validation After Each Phase

After completing each phase:
```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

## File Conflict Map

Files modified by multiple designs (coordinate changes):

| File | Designs | Changes |
|------|---------|---------|
| `rules.py` | 032, 033, 038 | +3 entries in `from_dict` registry |
| `__init__.py` | all | +exports (batch at end of each phase) |
| `memory_base.py` | 034, 035, 036, 040 | +type declarations |
| `memory.py` | 035, 040, 041 | +imports, +shortcut methods |
| `memory_core.py` | 036, 037 | evolve_with_feedback enhancement, adaptive recall |
| `memory_analytics.py` | 034 | cross_modality method |
| `memory_reasoning.py` | 040 | learn_causal + commit + hooks |
| `memory_structural.py` | 035, 041, 037 | compress_context, cache context, adaptive slice |
| `system_monitor.py` | 039 | verify_invariants |
| `cache.py` | 041 | context-aware eviction |

## Implementation Order Summary

```
Phase 1 (standalone rules, parallel):
  032 -> test 032 -> 033 -> test 033 -> 038 -> test 038

Phase 2 (low-effort wiring):
  037 -> test 037 -> 041 -> test 041

Phase 3 (medium-effort engines):
  034 -> test 034 -> 035 -> test 035 -> 036 -> test 036 -> 039 -> test 039

Phase 4 (high-effort):
  040 -> test 040

Final: batch exports, full test suite, pyright, ruff, docstrings
```
