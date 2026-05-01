# Design: SubsystemMixin Decomposition

**Date:** 2026-04-30
**Status:** Draft
**Scope:** Replace the monolithic `SubsystemMixin` (1,352 lines) with 6 domain-focused mixins and redistribute orphan properties to existing mixins.

---

## 1. Problem

`SubsystemMixin` in `memory_subsystems.py` is a catch-all that handles 20 distinct engine interactions across unrelated domains. At 1,352 lines and ~45 methods/properties, it is more than double the size of any other mixin and the single largest DP-1 violation in the codebase.

**Current state:**
- 1 file, 1 class, 1,352 lines
- 45 methods and properties
- 20 distinct engine interactions
- 29 internal field accesses (`self._*`)
- 5 cross-mixin calls (`self.store()`, `self.relate()`)

## 2. Design Goals

1. Each new mixin owns a **coherent domain** with 2-5 related engines
2. Each new mixin is **independently testable**
3. Orphan properties (engines created in other mixins but exposed in SubsystemMixin) move to their **natural home**
4. The facade class (`HypergraphMemory`) simply **extends its inheritance list**
5. **No behavioral changes** — pure structural refactoring
6. No new public API; all existing method signatures unchanged

## 3. New Mixin Architecture

### 3.1 Overview

| # | Module | Mixin | Primary Engines | Est. Lines |
|---|--------|-------|-----------------|------------|
| 1 | `memory_retrieval.py` | `RetrievalMixin` | `EmbeddingEngine`, `SpreadingActivation`, `RetrievalEngine`, `OperationFeedback`, `LazyCache` | ~300 |
| 2 | `memory_temporal.py` | `TemporalMixin` | `TemporalReasoner`, `LLMEnricher` | ~150 |
| 3 | `memory_provenance.py` | `ProvenanceMixin` | `ProvenanceTracker`, `HypergraphOverlay` | ~60 |
| 4 | `memory_cognitive.py` | `CognitiveMixin` | `BackwardChainEngine`, `HebbianLearner`, `UncertaintyEngine` | ~190 |
| 5 | `memory_structural.py` | `StructuralMixin` | `StructuralPatternEngine`, `CommunityDetector`, `ContradictionResolver`, `AbstractionNavigator`, `GraphDiffer` | ~300 |
| 6 | `memory_monitoring.py` | `MonitoringMixin` | `SystemMonitor`, `MultiPerspectiveAnalyzer` | ~150 |

### 3.2 Orphan Property Reassignment

Properties currently in `SubsystemMixin` that logically belong to existing mixins:

| Property/Method | New Home | Rationale |
|----------------|----------|-----------|
| `belief` (prop) | `BeliefMixin` | Directly exposes `_belief`, owned by `BeliefMixin` |
| `multiway` (prop) | `ReasoningMixin` | Engine created in `_ensure_multiway()` inside `ReasoningMixin` |
| `branchial` (prop) | `ReasoningMixin` | Created alongside multiway engine |
| `rulial` (prop) | `ReasoningMixin` | Same cluster init |
| `compute_bias_profile()` | `ReasoningMixin` | Delegates to `self.rulial` |
| `s_persistence()` | `AnalyticsMixin` | Graph analysis method, peers with centrality/paths |
| `hyperedge_similarity()` | `AnalyticsMixin` | Graph analysis method |
| `spectral_embedding()` | `AnalyticsMixin` | Graph analysis method |

### 3.3 Updated Facade Inheritance

```python
# Before (7 mixins)
class HypergraphMemory(CoreMixin, ReasoningMixin, BeliefMixin, BayesianMixin,
                       AnalyticsMixin, PersistenceMixin, SubsystemMixin):

# After (12 mixins)
class HypergraphMemory(CoreMixin, ReasoningMixin, BeliefMixin, BayesianMixin,
                       AnalyticsMixin, PersistenceMixin,
                       RetrievalMixin, TemporalMixin, ProvenanceMixin,
                       CognitiveMixin, StructuralMixin, MonitoringMixin):
```

## 4. Detailed Method Assignment

### 4.1 RetrievalMixin (`memory_retrieval.py`)

**Domain**: Semantic search, spreading activation, retrieval, relevance feedback.

**State (from `_MemoryBase`):**
```
_embedding_engine: EmbeddingEngine | None
_activation: SpreadingActivation
_retrieval: RetrievalEngine
_feedback: OperationFeedback
```

**Methods moved from `SubsystemMixin`:**

| Method | Line | Notes |
|--------|------|-------|
| `set_embedding_provider(provider)` | 51 | Sets `_embedding_engine`, wires to `_retrieval` |
| `enable_faiss(*, nlist, nprobe, use_gpu)` | 60 | Lazy inits `_embedding_engine` |
| `find_similar(concept, *, top_k, threshold)` | 78 | Lazy inits `_embedding_engine`, label→ID |
| `analogy(a, b, c, *, top_k)` | 98 | Lazy inits `_embedding_engine`, ID→label |
| `activate(concept, *, energy, top_k, iterations)` | 127 | Delegates to `_activation` |
| `stimulate(concept, *, energy)` | 145 | Label→ID, raises `NodeNotFoundError` |
| `spread_activation(*, iterations)` | 162 | Delegates to `_activation` |
| `clear_activations()` | 174 | Delegates to `_activation` |
| `retrieve(concept, *, top_k, iterations, use_ltr)` | 178 | Wires embedding to retrieval |
| `record_feedback(query, results, relevant_labels)` | 199 | Delegates to `_retrieval` |
| `train_retriever()` | 214 | Delegates to `_retrieval` |
| `feedback_summary()` | 234 | Delegates to `_feedback` |
| `spread_hyperedge(concept, *, energy, mode, iterations)` | 1325 | N-ary edge activation |
| `enable_prefetch(enabled)` | 466 | Delegates to `_cache` |
| `record_access(concept)` | 474 | Label→cache-key mapping |
| `predict_next_access(concept, *, top_k)` | 482 | Cache key→label mapping |
| `prefetch_neighbors(concept)` | 504 | Label→ID, delegates to `_cache` |

**Properties moved:**
- `embedding_engine` (line 462)
- `feedback` (line 224) — returns `_retrieval.feedback`
- `operation_feedback` (line 230) — returns `_feedback`
- `retrieval` (line 243) — returns `_retrieval`
- `cache` (line 578) — returns `_cache`

**Cross-mixin calls:** None. All operations are self-contained within retrieval and cache engines.

**Design note:** Cache/prefetch methods are placed here rather than in `MonitoringMixin` because the cache is primarily used for retrieval acceleration (prefetching neighbor data, Markov-model access prediction). The `cache` property and all cache-management methods live in a single mixin to avoid split ownership.

---

### 4.2 TemporalMixin (`memory_temporal.py`)

**Domain**: Temporal reasoning (Allen interval algebra) and text ingestion.

**State (from `_MemoryBase`):**
```
_temporal: TemporalReasoner
_enricher: LLMEnricher
```

**Methods moved from `SubsystemMixin`:**

| Method | Line | Notes |
|--------|------|-------|
| `add_temporal_event(label, start, end, **metadata)` | 248 | Calls `self.store()` (CoreMixin) |
| `temporal_query(concept, *, relation, max_gap)` | 265 | Dispatches by relation type |
| `causal_chain(labels)` | 300 | Delegates to `_temporal` |
| `set_llm_provider(provider)` | 309 | Replaces `_enricher` |
| `ingest(text, *, extract)` | 317 | Calls `self.store()` + `self.relate()` (CoreMixin) |
| `ingest_batch(texts, *, extract, deduplicate)` | 350 | Calls `self.store()` + `self.relate()` (CoreMixin) |

**Properties moved:**
- `temporal` (line 304)
- `enricher` (line 635)

**Cross-mixin calls:**
- `add_temporal_event` calls `self.store()` (CoreMixin)
- `ingest` and `ingest_batch` call `self.store()` and `self.relate()` (CoreMixin)

These are standard cross-mixin calls via shared `_MemoryBase` methods. No special handling needed.

---

### 4.3 ProvenanceMixin (`memory_provenance.py`)

**Domain**: Inference lineage, explanation, and overlay access.

**State (from `_MemoryBase`):**
```
_provenance: ProvenanceTracker
_overlay: HypergraphOverlay | None
```

**Methods moved from `SubsystemMixin`:**

| Method | Line | Notes |
|--------|------|-------|
| `explain(source, target, *, edge_label)` | 397 | Finds edge, delegates to `_provenance` |
| `retract_inference(source, target, *, edge_label)` | 421 | Cascading retraction |

**Properties moved:**
- `provenance` (line 451)
- `overlay` (line 456)

**Cross-mixin calls:** None. Operates purely on `_provenance` and `_graph`.

**Note:** This is the smallest mixin (4 items, ~60 lines). It is kept separate because provenance/explanation is a distinct domain that should not be absorbed into `ReasoningMixin` (already 624 lines) or mixed with unrelated concerns.

---

### 4.4 CognitiveMixin (`memory_cognitive.py`)

**Domain**: Goal-directed reasoning, co-activation learning, uncertainty quantification.

**State (from `_MemoryBase`):**
```
_backward_chain: BackwardChainEngine | None
_hebbian: HebbianLearner | None
_uncertainty_engine: UncertaintyEngine | None
```

All three follow DP-3 (lazy initialization on first use).

**Methods moved from `SubsystemMixin`:**

| Method | Line | Notes |
|--------|------|-------|
| `prove(concept, *, known_facts, edge_label, max_depth)` | 681 | Lazy inits `_backward_chain` |
| `prove_batch(target_concepts, *, known_facts, edge_label)` | 715 | Lazy inits `_backward_chain` |
| `hebbian_reinforce()` | 740 | Lazy inits `_hebbian`, logs |
| `hebbian_reinforce_pair(source, target, *, strength)` | 759 | Lazy inits `_hebbian` |
| `hebbian_decay_unused(*, threshold_access_count)` | 780 | Lazy inits `_hebbian` |
| `strongest_associations(concept, *, top_k)` | 795 | Lazy inits `_hebbian` |
| `compute_confidence(concept)` | 814 | Lazy inits `_uncertainty_engine` |
| `compute_all_confidences()` | 827 | Lazy inits `_uncertainty_engine` |
| `flag_low_confidence(*, threshold)` | 837 | Lazy inits `_uncertainty_engine` |
| `trace_confidence_chain(source, target, *, max_depth)` | 850 | Lazy inits `_uncertainty_engine` |

**Properties moved:**
- `backward_chain` (line 1218)
- `hebbian` (line 1223)
- `uncertainty` (line 1228)

**Cross-mixin calls:** None. All operations delegate to lazily-initialized engines.

---

### 4.5 StructuralMixin (`memory_structural.py`)

**Domain**: Pattern matching, community detection, belief revision, abstraction, graph versioning.

**State (from `_MemoryBase`):**
```
_structural_matcher: StructuralPatternEngine | None
_community_detector: CommunityDetector | None
_belief_revision: ContradictionResolver | None
_abstraction_nav: AbstractionNavigator | None
_graph_differ: GraphDiffer | None
```

All five follow DP-3 (lazy initialization on first use).

**Methods moved from `SubsystemMixin`:**

| Method | Line | Notes |
|--------|------|-------|
| `match_structural_pattern(*, pattern_name, nodes, edges, max_matches)` | 871 | Lazy inits `_structural_matcher` |
| `match_chains(*, edge_label, min_length, max_length, max_chains)` | 919 | Lazy inits, ID→label translation |
| `match_diamonds(*, edge_label, max_matches)` | 955 | Lazy inits, returns dicts |
| `match_fan_out(*, edge_label, min_fan, max_results)` | 985 | Lazy inits, returns dicts |
| `detect_communities(*, method, edge_label, seed)` | 1130 | Lazy inits `_community_detector` |
| `detect_contradictions()` | 1025 | Lazy inits `_belief_revision` |
| `revise_beliefs(*, strategy)` | 1035 | Lazy inits `_belief_revision`, logs |
| `check_consistency(source, target)` | 1055 | Lazy inits `_belief_revision` |
| `collapse_subgraph(node_labels, *, summary_label, summary_data, layer)` | 1073 | Lazy inits `_abstraction_nav` |
| `expand_summary(summary_label)` | 1107 | Lazy inits `_abstraction_nav` |
| `list_summaries()` | 1120 | Lazy inits `_abstraction_nav` |
| `capture_version()` | 1164 | Lazy inits `_graph_differ`, wires to `_meta` |
| `diff_from_version(version_id)` | 1180 | Lazy inits `_graph_differ` |
| `diff_between_versions(v1, v2)` | 1193 | Lazy inits `_graph_differ` |
| `version_history()` | 1207 | Lazy inits `_graph_differ` |

**Properties moved:**
- `structural_matcher` (line 1233)
- `communities` (line 1248)
- `belief_reviser` (line 1238)
- `abstraction` (line 1243)
- `differ` (line 1253)

**Cross-mixin calls:**
- `capture_version` wires `_graph_differ` to `self._meta` (cross-subsystem wiring, acceptable in facade layer)

---

### 4.6 MonitoringMixin (`memory_monitoring.py`)

**Domain**: System introspection, tuning, multi-frame analysis, validation, capability detection.

**State (from `_MemoryBase`):**
```
_meta: SystemMonitor
_perspective: MultiPerspectiveAnalyzer
_anomaly_detector: StructuralAnomalyDetector
_discovery: RuleDiscoveryEngine
```

**Methods moved from `SubsystemMixin`:**

| Method | Line | Notes |
|--------|------|-------|
| `introspect()` | 582 | Delegates to `_meta` |
| `check_metamorphosis()` | 586 | Delegates to `_meta` |
| `propose_tuning(triggers)` | 590 | Delegates to `_meta` |
| `execute_tuning_validated(plan, *, fitness_tolerance)` | 594 | Lazy inits `_graph_differ` |
| `analyze_in_frame(concept, frame_name)` | 622 | Delegates to `_perspective` |
| `multi_frame_analysis(concept)` | 626 | Delegates to `_perspective` |
| `select_optimal_frame(concept)` | 630 | Delegates to `_perspective` |
| `validate_reasoning(seed_concepts, rules)` | 639 | Creates `ValidationEngine` on demand |
| `validate_comprehensive(test_cases)` | 658 | Creates `ValidationEngine` on demand |
| `detect_capability()` | 675 | Creates `detect_capability_level` on demand |

**Properties moved:**
- `meta` (line 568)
- `perspective` (line 563)
- `structural_anomaly` (line 558)
- `discovery` (line 573)

---

## 5. `_MemoryBase` Changes

The `_MemoryBase` class already declares all lazy-initialized fields. No field additions are needed — the fields are already there:

```python
class _MemoryBase:
    # Already declared (lines 52-94):
    _embedding_engine: EmbeddingEngine | None
    _activation: SpreadingActivation
    _retrieval: RetrievalEngine
    _feedback: OperationFeedback
    _temporal: TemporalReasoner
    _enricher: LLMEnricher
    _provenance: ProvenanceTracker
    _overlay: HypergraphOverlay | None
    _backward_chain: BackwardChainEngine | None
    _hebbian: HebbianLearner | None
    _uncertainty_engine: UncertaintyEngine | None
    _structural_matcher: StructuralPatternEngine | None
    _belief_revision: ContradictionResolver | None
    _abstraction_nav: AbstractionNavigator | None
    _community_detector: CommunityDetector | None
    _graph_differ: GraphDiffer | None
    _meta: SystemMonitor
    _perspective: MultiPerspectiveAnalyzer
    _anomaly_detector: StructuralAnomalyDetector
    _discovery: RuleDiscoveryEngine
    _cache: LazyCache
```

## 6. Orphan Property Reassignment Details

### 6.1 BeliefMixin additions

Add to `memory_belief.py`:

```python
@property
def belief(self) -> BeliefLayer:
    return self._belief
```

### 6.2 ReasoningMixin additions

Add to `memory_reasoning.py`:

```python
@property
def multiway(self) -> MultiwayEngine | None:
    return self._multiway_engine

@property
def branchial(self) -> BranchialSpace | None:
    return self._branchial

@property
def rulial(self) -> RulialSpace:
    if self._rulial is None:
        self._rulial = RulialSpace(self._graph)
    return self._rulial

def compute_bias_profile(self) -> BiasProfileResult:
    return self.rulial.compute_bias_profile()
```

This also resolves Issue #6 from the architectural review: the dual init path for `_rulial`. With the property in `ReasoningMixin`, `_ensure_multiway()` creates the wired version during reasoning, and the property provides a standalone fallback. Since `ReasoningMixin` owns `_ensure_multiway()`, it now owns both init paths.

**Intentional ordering:** If `mem.rulial` is accessed before `reason()` is called, the property creates a bare `RulialSpace(self._graph)`. When `reason()` is later called, `_ensure_multiway()` overwrites it with a version wired to the `MultiwayEngine`. The bare instance is read-only-safe (it only needs the graph), so data loss from the overwrite is not a concern — the bare instance would have only accumulated passive rule-frequency data that the wired version also computes during reasoning.

### 6.3 AnalyticsMixin additions

Add to `memory_analytics.py`:

```python
def s_persistence(self, *, max_s=None):
    return self._graph.s_persistence(max_s=max_s)

def hyperedge_similarity(self, concept, *, metric="jaccard", top_k=None):
    # ... existing implementation from SubsystemMixin ...

def spectral_embedding(self, *, dimensions=8):
    # ... existing implementation from SubsystemMixin ...
```

These three are graph analysis methods that peer naturally with `paths()`, `centrality()`, `cycles()`, and `components()` already in `AnalyticsMixin`.

## 7. Implementation Steps

### Phase 1: Create new mixin modules (non-breaking)

1. Create `memory_retrieval.py` with `RetrievalMixin(_MemoryBase)`
2. Create `memory_temporal.py` with `TemporalMixin(_MemoryBase)`
3. Create `memory_provenance.py` with `ProvenanceMixin(_MemoryBase)`
4. Create `memory_cognitive.py` with `CognitiveMixin(_MemoryBase)`
5. Create `memory_structural.py` with `StructuralMixin(_MemoryBase)`
6. Create `memory_monitoring.py` with `MonitoringMixin(_MemoryBase)`

Each module:
- Extends `_MemoryBase`
- Contains only the methods and properties listed above
- Has its own imports for engine types and result types
- Preserves exact method signatures and docstrings

### Phase 2: Reassign orphans (non-breaking)

7. Add `belief` property to `BeliefMixin`
8. Add `multiway`, `branchial`, `rulial`, `compute_bias_profile` to `ReasoningMixin`
9. Add `s_persistence`, `hyperedge_similarity`, `spectral_embedding` to `AnalyticsMixin`

### Phase 3: Switch the facade (breaking if incomplete)

10. **Dry-run import check** — verify all 6 new modules import cleanly before switching:
    ```bash
    .venv/bin/python -c "from hyper3.memory_retrieval import RetrievalMixin; \
                         from hyper3.memory_temporal import TemporalMixin; \
                         from hyper3.memory_provenance import ProvenanceMixin; \
                         from hyper3.memory_cognitive import CognitiveMixin; \
                         from hyper3.memory_structural import StructuralMixin; \
                         from hyper3.memory_monitoring import MonitoringMixin"
    ```
11. **MRO collision check** — verify zero duplicate method/property names across the 6 new mixins:
    ```bash
    grep -h 'def \|@property' src/hyper3/memory_retrieval.py src/hyper3/memory_temporal.py \
         src/hyper3/memory_provenance.py src/hyper3/memory_cognitive.py \
         src/hyper3/memory_structural.py src/hyper3/memory_monitoring.py | sort | uniq -d
    ```
    If any duplicates appear, resolve before proceeding (Python MRO would silently pick the first in the inheritance list).
12. Update `HypergraphMemory` inheritance: remove `SubsystemMixin`, add the 6 new mixins
13. Run full test suite: `.venv/bin/python -m pytest tests/ -q --tb=short`
14. Run type checker: `.venv/bin/pyright src/hyper3/`
15. Run linter: `.venv/bin/ruff check src/hyper3/ tests/`

### Phase 4: Cleanup

14. Delete `memory_subsystems.py`
15. Remove `SubsystemMixin` from imports in `memory.py`
16. Update `AGENTS.md`:
    - Architecture section: replace `SubsystemMixin` entry with 6 new modules
    - File Layout section: add 6 new modules, remove `memory_subsystems.py`
    - DP-1 example: update mixin list
    - Known API Gaps: remove Issue #6 (rulial dual init) if resolved
17. Update `__init__.py` if `SubsystemMixin` is exported

## 8. Size Comparison

| Mixin | Before (lines) | After (lines) |
|-------|----------------|---------------|
| SubsystemMixin | 1,352 | **deleted** |
| RetrievalMixin | — | ~300 |
| TemporalMixin | — | ~150 |
| ProvenanceMixin | — | ~60 |
| CognitiveMixin | — | ~190 |
| StructuralMixin | — | ~300 |
| MonitoringMixin | — | ~150 |
| BeliefMixin | 257 | 257 + ~3 |
| ReasoningMixin | 624 | 624 + ~20 |
| AnalyticsMixin | 332 | 332 + ~50 |
| **Total new code** | | **~1,300** (vs 1,352 old) |

The ~50-line reduction comes from eliminating duplicate lazy-init blocks (each field has one canonical init site) and removing the module-level import burden. The reduction is modest because each new file carries its own imports and docstrings — the primary benefit is domain cohesion, not line savings.

## 9. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| MRO conflict in facade | Low | 12 mixins all extend `_MemoryBase`; no diamond except through the single base. Phase 3 includes a collision check step. |
| Missed method during migration | Low | Grep-based method inventory completed; test suite covers all paths |
| Cross-mixin call breaks | Low | Only 5 cross-mixin calls identified (`self.store`, `self.relate`); these are standard in the codebase |
| Import cycle | None | All new modules import from `_MemoryBase` (upward) and engine modules (sideways); no downward imports |
| Test regression | Low | 2,129 existing tests with 0 skips; any breakage will be caught immediately |

## 10. Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/hyper3/memory_retrieval.py` | **Create** | `RetrievalMixin` |
| `src/hyper3/memory_temporal.py` | **Create** | `TemporalMixin` |
| `src/hyper3/memory_provenance.py` | **Create** | `ProvenanceMixin` |
| `src/hyper3/memory_cognitive.py` | **Create** | `CognitiveMixin` |
| `src/hyper3/memory_structural.py` | **Create** | `StructuralMixin` |
| `src/hyper3/memory_monitoring.py` | **Create** | `MonitoringMixin` |
| `src/hyper3/memory_subsystems.py` | **Delete** | Replaced by 6 new modules |
| `src/hyper3/memory_belief.py` | **Edit** | Add `belief` property |
| `src/hyper3/memory_reasoning.py` | **Edit** | Add `multiway`, `branchial`, `rulial` props + `compute_bias_profile` |
| `src/hyper3/memory_analytics.py` | **Edit** | Add `s_persistence`, `hyperedge_similarity`, `spectral_embedding` |
| `src/hyper3/memory.py` | **Edit** | Update facade inheritance list |
| `src/hyper3/__init__.py` | **Edit** | Replace `SubsystemMixin` export with 6 new mixins |
| `AGENTS.md` | **Edit** | Update architecture, file layout, DP-1 example |

## 11. Testing Strategy

No new tests are required for the refactoring itself (all existing tests must pass unchanged). However, if desired:

- **Per-mixin unit tests**: Create `test_memory_retrieval.py`, `test_memory_temporal.py`, etc. that instantiate the mixin in isolation via a test harness class that extends `_MemoryBase`.
- **Smoke tests**: One test per new mixin that verifies the mixin's methods are accessible on the facade.
- **Integration tests**: The existing `test_memory.py` (138 tests) and `test_memory_api.py` (51 tests) already exercise the facade end-to-end.

## 12. Review Notes

Incorporated from design review (2026-04-30):

- **Cache ownership** (review point #3/#4): Moved `enable_prefetch`, `record_access`, `predict_next_access`, `prefetch_neighbors`, and the `cache` property from `MonitoringMixin` into `RetrievalMixin`. Cache is primarily a retrieval acceleration tool; split ownership would be confusing.
- **MRO collision check** (review point #1): Added verification step to Phase 3 that greps for duplicate method/property names across all 6 new modules before switching the facade.
- **`_rulial` dual init** (review point #2): Added explicit documentation that the standalone `RulialSpace(self._graph)` fallback is safe and that `_ensure_multiway()` overwrites it with a wired version when reasoning starts.
- **Dry-run imports** (review point #6): Added Phase 3 step that imports all 6 new modules before modifying the facade, catching circular dependencies early.
- **Size estimates** (review point #7): Revised from ~1,160 to ~1,300 total lines. The primary benefit is domain cohesion, not line savings.
