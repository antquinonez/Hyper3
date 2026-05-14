# Design 3: Cross-Modality Fusion Engine

**Status: Design**

**Effort**: H (~600 LoC new) | **Value**: H | **Risk**: M

## Problem

Hyper3 nodes and edges carry `Modality` tags (`TEXTUAL`, `CONCEPTUAL`, `TEMPORAL`,
`CAUSAL`, `SENSORY`, `ABSTRACT`), but these tags are passive metadata. You can
filter by modality via `SliceConfig(modalities={...})`, but you cannot:

1. **Query across multiple modalities simultaneously** with per-modality weighting
2. **Synthesize insights** that emerge only from cross-modality correlations
3. **Detect modality gaps** — concepts richly connected in one modality but
   sparse in another

The inspiration document (Figure 10) describes: "Unified hypergraph structure ->
textual + temporal + causal + conceptual + sensory -> holistic integrated insights."
Appendix C defines modality tagging guidelines. This design materializes those
cross-modality queries as a first-class engine.

## Scope

A `ModalityFusionEngine` that queries the graph across multiple modalities,
weights results by modality relevance, detects modality gaps, and produces
fused relevance rankings. Wired into `AnalyticsMixin` via a namespace method.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Unified hypergraph -> multiple dimensions -> holistic insights" | Multi-modality weighted query returning `FusionResult` |
| "Cross-modality integration" | Per-modality subgraph extraction + Reciprocal Rank Fusion |
| "Modality tagging" | Existing `Modality` enum on `Metadata.modality_tags` |

## Architecture

```
Layer 1: Engine    -- ModalityFusionEngine (new: modality_fusion.py)
Layer 2: Mixin     -- extend AnalyticsMixin (memory_analytics.py)
Layer 3: Facade    -- expose via AnalyzeNamespace (no new namespace needed)
```

## Existing Code

- `Modality` enum in `kernel_types.py`: `TEXTUAL`, `CONCEPTUAL`, `TEMPORAL`,
  `CAUSAL`, `SENSORY`, `ABSTRACT`.
- `Metadata.modality_tags: set[Modality]` on every node and edge.
- `SliceConfig(modalities=...)` in `traversal.py` -- filters by modality.
- `ObserverSlice` in `traversal.py` -- applies `SliceConfig`.
- `SpreadingActivation` in `retrieval_activation.py` -- activation-based retrieval.
- `RetrievalEngine` in `retrieval_engine.py` -- RRF fusion of activation + semantic.
- `MultiPerspectiveAnalyzer` in `multi_perspective.py` -- multi-frame fusion.
- `Hypergraph.incident_edges(node)`, `outgoing_edges(node)` -- edge access.

## Design: Layer 1 -- ModalityFusionEngine

**New file**: `src/hyper3/modality_fusion.py`

### Data Structures

All result dataclasses extend `_SimpleResultBase` (from `results.py`).

```python
@dataclass
class ModalityProfile(_SimpleResultBase):
    node_id: str = ""
    per_modality_score: dict[str, float] = field(default_factory=dict)
    modality_coverage: dict[str, int] = field(default_factory=dict)
    fused_score: float = 0.0
    dominant_modality: str = ""
    gap_modalities: list[str] = field(default_factory=list)

@dataclass
class ModalityGap(_SimpleResultBase):
    concept: str = ""
    rich_modalities: list[str] = field(default_factory=list)
    gap_modalities: list[str] = field(default_factory=list)
    coverage_ratio: float = 0.0

@dataclass
class FusionResult(_SimpleResultBase):
    query_modalities: list[str] = field(default_factory=list)
    modality_weights: dict[str, float] = field(default_factory=dict)
    ranked_concepts: list[ModalityProfile] = field(default_factory=list)
    cross_modality_edges: int = 0
    gaps: list[ModalityGap] = field(default_factory=list)
    total_candidates: int = 0
```

### Engine API

```python
class ModalityFusionEngine:
    def __init__(self, graph: Hypergraph) -> None: ...

    def fuse(
        self,
        seed_id: str,
        *,
        modalities: set[Modality] | None = None,
        weights: dict[str, float] | None = None,
        max_depth: int = 3,
        max_concepts: int = 50,
        rrf_k: int = 60,
    ) -> FusionResult: ...

    def detect_gaps(
        self,
        concept_ids: list[str],
        *,
        expected_modalities: set[Modality] | None = None,
    ) -> list[ModalityGap]: ...

    def modality_coverage(self, concept_id: str) -> ModalityProfile: ...

    def cross_modality_edges(self, concept_id: str) -> int: ...

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> ModalityFusionEngine: ...
```

### Fusion Algorithm

For each requested modality, extract a per-modality subgraph and compute
independent relevance scores, then fuse via Reciprocal Rank Fusion (reusing
the same RRF formula from `RetrievalEngine`):

```
RRF_score(concept) = sum over modalities M of: weight(M) * 1 / (k + rank_M(concept))
```

Per-modality scoring uses weighted degree centrality restricted to edges whose
`metadata.modality_tags` include that modality:

```
score_M(node) = sum(e.weight for e in incident_edges(node) if M in e.metadata.modality_tags
                     or any(M in get_node(n).metadata.modality_tags for n in e.node_ids))
```

An edge is "cross-modality" if its source and target nodes have non-overlapping
modality tags (e.g., a CAUSAL node connected to a TEMPORAL node).

### Gap Detection

For each concept, compute which modalities have incident edges and which don't.
A `ModalityGap` is reported when a concept has edges in some modalities but is
completely absent from others. `coverage_ratio = rich_modalities / total_modalities`.

### Key Design Decisions

1. **Edge modality from node tags, not edge tags**: Most edges don't have explicit
   modality tags. We infer edge modality from the modality tags of the nodes it
   connects. An edge connecting a CAUSAL node to a CONCEPTUAL node is cross-modality
   for both CAUSAL and CONCEPTUAL.

2. **RRF fusion, not weighted average**: RRF handles the case where a concept is
   highly relevant in one modality but absent from another -- it still gets ranked
   by its best-performing modality, with bonus for multi-modality presence.

3. **No modification to existing SliceConfig**: The fusion engine does not change
   how `SliceConfig` works. It's a parallel query path that happens to use modality
   metadata.

## Design: Layer 2 -- Mixin Wiring

### AnalyticsMixin (memory_analytics.py)

Add one method:

```python
def cross_modality(
    self,
    concept: str,
    *,
    modalities: set[str] | None = None,
    weights: dict[str, float] | None = None,
    max_depth: int = 3,
    max_concepts: int = 50,
) -> FusionResult:
    concept_id = self._resolve(concept)
    mod_set = {Modality(m) for m in modalities} if modalities else None
    return self._modality_fusion.fuse(
        concept_id,
        modalities=mod_set,
        weights=weights,
        max_depth=max_depth,
        max_concepts=max_concepts,
    )
```

Lazy initialization of `_modality_fusion` follows DP-3.

### AnalyzeNamespace

Add passthrough to the mixin method. The namespace already exists at `mem.analyze`.

## Design: Layer 3 -- Facade

No additional facade methods needed -- accessed via `mem.analyze.cross_modality(...)`.

## Challenge: Sparse Modality Tags

Most existing Hyper3 graphs don't have modality tags on nodes. The engine handles
this gracefully: nodes with no modality tags are treated as having `{CONCEPTUAL}`
(the default modality for untagged knowledge). This prevents the engine from
returning empty results on untagged graphs.

## Test Plan (~25 tests)

- Engine construction
- `fuse`: no modality tags -> treats all as CONCEPTUAL
- `fuse`: single modality -> returns concepts reachable via that modality
- `fuse`: multiple modalities -> RRF fusion combines per-modality rankings
- `fuse`: custom weights -> higher-weighted modality dominates
- `fuse`: seed with no edges -> empty result
- `fuse`: `max_concepts` limits output
- `fuse`: cross-modality edges counted correctly
- `modality_coverage`: node with edges in 3 modalities
- `modality_coverage`: node with no edges
- `modality_coverage`: node with no modality tags -> CONCEPTUAL default
- `detect_gaps`: node present in CAUSAL but absent from TEMPORAL
- `detect_gaps`: node present in all modalities -> no gaps
- `detect_gaps`: expected_modalities parameter filters
- `cross_modality_edges`: edge between different-modality nodes
- `cross_modality_edges`: edge between same-modality nodes -> 0
- `to_dict` / `from_dict`: round-trip serialization
- Integration: `mem.analyze.cross_modality("concept")` returns FusionResult
- Integration: fusion after adding modality-tagged nodes
- Edge: empty graph
- Edge: all nodes same modality
- Edge: mixed tagged and untagged nodes
- RRF: concept present in multiple modalities ranks higher than single-modality
- RRF: k parameter affects score distribution
- Modality string conversion: "causal" -> Modality.CAUSAL

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/modality_fusion.py` | NEW | ~400 LoC |
| `tests/test_modality_fusion.py` | NEW | ~450 LoC |
| `src/hyper3/memory_analytics.py` | MODIFY | +30 LoC (cross_modality method) |
| `src/hyper3/memory_base.py` | MODIFY | +2 LoC (_modality_fusion type declaration) |
| `src/hyper3/__init__.py` | MODIFY | +3 exports |

**Estimated total**: ~880 LoC new, ~32 LoC modified.
