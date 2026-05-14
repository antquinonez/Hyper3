# Design 5: Feedback-Driven Structural Evolution

**Status: Design**

**Effort**: M (~300 LoC new) | **Value**: M | **Risk**: L

## Problem

`GraphMaintenanceEngine.evolve()` uses simple operation-count triggers and
weight-based decay/prune/merge. `evolve_with_feedback()` extends this with
fitness-trend detection from `OperationFeedback`, but the evolution loop does
not consume richer signals:

- **Rule effectiveness** from `RuleAnalytics` -- poorly-performing rules should
  trigger pruning of their inferred edges
- **Retrieval relevance** from `RetrievalEngine` -- concepts never retrieved
  should decay faster
- **Activation patterns** from `SpreadingActivation` -- concepts never activated
  are candidates for aggressive pruning
- **Slice success** from `AdaptiveSliceEngine` -- regions where slices
  consistently fail indicate structural gaps

The inspiration document (Appendix F) describes: "Track interaction frequency,
contextual relevance scores, computational efficiency indicators" to drive
evolution. This design enriches the evolution feedback loop with these signals.

## Scope

Extend `GraphMaintenanceEngine` with a `FeedbackAwareEvolution` wrapper that
consumes multi-source feedback to make smarter evolution decisions. No new
engine -- this wraps the existing evolution pipeline.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Interaction frequency metrics" | Activation counts from `SpreadingActivation` |
| "Contextual relevance scores" | Retrieval relevance from `RetrievalEngine` |
| "Computational efficiency indicators" | Cache hit ratios, rule effectiveness |
| "Self-evolution decision protocols" | `FeedbackAwareEvolution.evolve()` |

## Architecture

```
Layer 1: Engine    -- FeedbackAwareEvolution (new: evolution_feedback.py)
Layer 2: Mixin     -- extend CoreMixin (memory_core.py)
Layer 3: Facade    -- enhance mem.evolve_with_feedback() (already exists)
```

## Existing Code

- `GraphMaintenanceEngine` in `evolution.py`: `evolve() -> EvolveResult`,
  `decay()`, `prune()`, `merge()`, `reinforce()`.
- `EvolveResult` in `evolution.py`: typed result with decayed/pruned/merged/reinforced counts.
- `EvolutionMetrics` in `evolution.py`: accumulated metrics.
- `OperationFeedback` in `feedback.py`: `cross_operation_summary()`,
  `record_signal()`, `FeedbackSignal`.
- `RuleAnalytics` in `rule_analytics.py`: rule effectiveness tracking.
- `SpreadingActivation` in `retrieval_activation.py`: activation state.
- `AdaptiveSliceEngine` in `adaptive_slice.py`: slice success history.
- `evolve_with_feedback()` in `memory_core.py`: existing fitness-trend-aware
  evolution (partial implementation of this concept).

## Design: Layer 1 -- FeedbackAwareEvolution

**New file**: `src/hyper3/evolution_feedback.py`

### Data Structures

```python
@dataclass
class EvolutionSignals(_SimpleResultBase):
    low_activation_nodes: list[str] = field(default_factory=list)
    low_relevance_nodes: list[str] = field(default_factory=list)
    low_effectiveness_rules: list[str] = field(default_factory=list)
    high_failure_regions: list[str] = field(default_factory=list)
    fitness_trend: str = "stable"  # "improving" | "stable" | "declining"
    fitness_value: float = 0.0

@dataclass
class FeedbackEvolveResult(_SimpleResultBase):
    base_result: EvolveResult | None = None
    extra_pruned: int = 0
    extra_reinforced: int = 0
    rule_demotions: int = 0
    signals: EvolutionSignals | None = None
```

### Engine API

```python
class FeedbackAwareEvolution:
    def __init__(self, evolution: GraphMaintenanceEngine) -> None: ...

    def collect_signals(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        rule_analytics: RuleAnalytics | None = None,
        feedback: OperationFeedback | None = None,
        adaptive_slice: AdaptiveSliceEngine | None = None,
    ) -> EvolutionSignals: ...

    def evolve(
        self,
        graph: Hypergraph,
        signals: EvolutionSignals,
    ) -> FeedbackEvolveResult: ...
```

### Signal Collection

```python
def collect_signals(self, graph, *, activation=None, rule_analytics=None,
                    feedback=None, adaptive_slice=None) -> EvolutionSignals:
    signals = EvolutionSignals()

    # 1. Low-activation nodes (never reached by spreading activation)
    if activation:
        for node in graph.nodes:
            energy = activation.get_energy(node.id)
            if energy is not None and energy < 0.01:
                signals.low_activation_nodes.append(node.id)

    # 2. Low-relevance nodes (never retrieved)
    if feedback:
        summary = feedback.cross_operation_summary()
        if summary:
            signals.low_relevance_nodes = summary.get("low_relevance_nodes", [])

    # 3. Low-effectiveness rules
    if rule_analytics:
        report = rule_analytics.report()
        if report:
            for entry in report.rule_effectiveness:
                if entry.effectiveness < 0.2:
                    signals.low_effectiveness_rules.append(entry.rule_name)

    # 4. Fitness trend from OperationFeedback
    if feedback:
        # ... extract trend from feedback signals

    return signals
```

### Enhanced Evolution

```python
def evolve(self, graph, signals) -> FeedbackEvolveResult:
    # 1. Run standard evolution
    base = self._evolution.evolve()

    extra_pruned = 0
    extra_reinforced = 0
    rule_demotions = 0

    # 2. Aggressive pruning for low-activation nodes
    if signals.fitness_trend == "declining":
        for node_id in signals.low_activation_nodes:
            node = graph.get_node(node_id)
            if node and node.weight < 0.5:
                graph.remove_node(node_id)
                extra_pruned += 1

    # 3. Reinforce high-activation, high-relevance nodes
    for node_id in signals.low_relevance_nodes:
        pass  # these are candidates for pruning, not reinforcement
    # Reinforce the complement: nodes with high activation but not in low_relevance
    if signals.fitness_trend in ("stable", "improving"):
        if signals.low_activation_nodes:
            all_nodes = {n.id for n in graph.nodes}
            active_nodes = all_nodes - set(signals.low_activation_nodes)
            top_active = sorted(active_nodes)[:3]  # reinforce top 3
            for nid in top_active:
                self._evolution.reinforce(nid, graph)
                extra_reinforced += 1

    # 4. Prune edges from low-effectiveness rules
    for rule_name in signals.low_effectiveness_rules:
        for edge in list(graph.edges):
            if edge.metadata.custom.get("rule") == rule_name:
                graph.remove_edge(edge.id)
                rule_demotions += 1

    return FeedbackEvolveResult(
        base_result=base,
        extra_pruned=extra_pruned,
        extra_reinforced=extra_reinforced,
        rule_demotions=rule_demotions,
        signals=signals,
    )
```

### Key Design Decisions

1. **Wrapper, not replacement**: `FeedbackAwareEvolution` wraps the existing
   `GraphMaintenanceEngine`, calling its `evolve()` first, then applying
   feedback-driven adjustments. This preserves backward compatibility.

2. **Optional signal sources**: All signal sources are optional `None` parameters.
   If no `activation` is provided, low-activation pruning is skipped. This allows
   incremental adoption.

3. **No new state**: The engine doesn't maintain its own state. It reads from
   existing subsystems and applies immediate actions.

## Design: Layer 2 -- Mixin Wiring

### CoreMixin (memory_core.py)

Enhance `evolve_with_feedback()` to use the new engine:

```python
def evolve_with_feedback(self) -> EvolveResult | FeedbackEvolveResult:
    if self._feedback_aware is None:
        return self.evolve()
    signals = self._feedback_aware.collect_signals(
        self._graph,
        activation=self._activation,
        rule_analytics=self._rule_analytics if hasattr(self, '_rule_analytics') else None,
        feedback=self._feedback,
        adaptive_slice=self._adaptive_slice if hasattr(self, '_adaptive_slice') else None,
    )
    return self._feedback_aware.evolve(self._graph, signals)
```

## Design: Layer 3 -- Facade

No facade changes needed -- `evolve_with_feedback()` already exists as a public
method. The enhanced version returns `FeedbackEvolveResult` (which extends the
existing return type).

## Test Plan (~20 tests)

- `FeedbackAwareEvolution` construction
- `collect_signals`: no signal sources -> empty signals
- `collect_signals`: with activation -> low_activation_nodes populated
- `collect_signals`: with rule analytics -> low_effectiveness_rules populated
- `collect_signals`: with feedback -> fitness_trend extracted
- `evolve`: no signals -> runs base evolution only
- `evolve`: declining fitness -> aggressive pruning of low-activation nodes
- `evolve`: stable fitness -> reinforces top active nodes
- `evolve`: low-effectiveness rules -> prunes their inferred edges
- `FeedbackEvolveResult` contains base_result
- Integration: `mem.evolve_with_feedback()` returns FeedbackEvolveResult
- Edge: empty graph
- Edge: all nodes high-activation -> no extra pruning
- Edge: no rules applied -> no rule demotions
- `EvolutionSignals` fields populated correctly
- `collect_signals` doesn't modify any source state
- Rule demotion removes edges with matching rule metadata
- Reinforcement actually increases node weight
- Pruning actually removes nodes from graph
- Round-trip: collect signals -> evolve -> verify graph state matches result

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/evolution_feedback.py` | NEW | ~300 LoC |
| `tests/test_evolution_feedback.py` | NEW | ~350 LoC |
| `src/hyper3/memory_core.py` | MODIFY | +20 LoC (enhanced evolve_with_feedback) |
| `src/hyper3/memory_base.py` | MODIFY | +2 LoC (type declaration) |
| `src/hyper3/__init__.py` | MODIFY | +3 exports |

**Estimated total**: ~650 LoC new, ~22 LoC modified.
