# Design 9: Probabilistic Causal Learning

**Status: Design**

**Effort**: H (~500 LoC new) | **Value**: M | **Risk**: M

## Problem

`CausalSequenceRule` creates causal edges from **known temporal intervals** via
Allen interval algebra. But most real knowledge doesn't come with timestamps.
When two concepts frequently co-activate (high activation energy correlation),
or when one consistently precedes the other in traversal paths, there may be a
latent causal relationship.

The inspiration document (Appendix B, Rule 3) calls for: "If event node A
consistently precedes event node B across contexts, instantiate a probabilistic
causal node." This design learns causal hypotheses from statistical co-occurrence
patterns in activation and traversal data, without requiring temporal annotations.

## Scope

A `CausalLearner` engine that observes co-activation patterns over time and
creates probabilistic causal hypotheses with confidence managed by Thompson
sampling. Wired into `ReasoningMixin` as an optional pre-reasoning step.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "A consistently precedes B across contexts" | Co-activation frequency + traversal order correlation |
| "Probabilistic causal node" | Causal hypothesis edge with confidence from Thompson sampling |
| "Causal inference from temporal patterns" | Statistical learning from activation patterns |

## Architecture

```
Layer 1: Engine    -- CausalLearner (new: causal_learner.py)
Layer 2: Mixin     -- extend ReasoningMixin (memory_reasoning.py)
Layer 3: Facade    -- expose via mem.learn_causal_patterns()
```

## Existing Code

- `SpreadingActivation` in `retrieval_activation.py`: activation energy per node.
- `CausalSequenceRule` in `rules_causal_sequence.py`: temporal-interval-based
  causal edge creation.
- `BeliefLayer` in `belief.py`: Born-rule sampling, confidence propagation.
- `Thompson sampling` in `multi_perspective.py` and `belief.py`: for adaptive
  parameter selection.
- `Hypergraph.find_paths()` in `kernel_paths.py`: path discovery.
- `UncertaintyEngine` in `uncertainty.py`: confidence propagation through chains.

## Design: Layer 1 -- CausalLearner

**New file**: `src/hyper3/causal_learner.py`

### Data Structures

```python
@dataclass
class CoActivationRecord(_SimpleResultBase):
    node_a_id: str = ""
    node_b_id: str = ""
    co_activation_count: int = 0
    a_before_b_count: int = 0
    b_before_a_count: int = 0
    total_observations: int = 0
    last_seen: float = 0.0

@dataclass
class CausalHypothesis(_SimpleResultBase):
    cause_id: str = ""
    effect_id: str = ""
    confidence: float = 0.0
    co_activation_frequency: float = 0.0
    precedence_ratio: float = 0.0
    path_correlation: float = 0.0
    observations: int = 0
    thompson_alpha: float = 1.0
    thompson_beta: float = 1.0

@dataclass
class CausalLearningResult(_SimpleResultBase):
    hypotheses_created: int = 0
    hypotheses_updated: int = 0
    hypotheses_pruned: int = 0
    total_observations: int = 0
    top_hypotheses: list[CausalHypothesis] = field(default_factory=list)
```

### Engine API

```python
class CausalLearner:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        min_observations: int = 5,
        min_precedence_ratio: float = 0.7,
        min_co_activation: float = 0.3,
        max_hypotheses: int = 100,
        pruning_threshold: float = 0.1,
    ) -> None: ...

    def observe_activation(self, activation_state: dict[str, float]) -> None: ...
    def observe_traversal(self, path: list[str]) -> None: ...
    def learn(self) -> CausalLearningResult: ...
    def get_hypotheses(self, *, concept: str | None = None) -> list[CausalHypothesis]: ...
    def get_hypothesis(self, cause: str, effect: str) -> CausalHypothesis | None: ...
    def prune(self) -> int: ...
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> CausalLearner: ...
```

### Observation Protocol

**Co-activation observation**: Called after each `spread_activation()` pass.
Receives a dict of `{node_id: energy}` for all nodes with non-zero energy.

```python
def observe_activation(self, activation_state: dict[str, float]) -> None:
    active_nodes = [nid for nid, energy in activation_state.items() if energy > 0.01]
    for i, a in enumerate(active_nodes):
        for b in active_nodes[i+1:]:
            record = self._get_or_create_record(a, b)
            record.co_activation_count += 1
            record.total_observations += 1
    self._activation_order.append(active_nodes)
```

**Traversal observation**: Called after each `find_paths()` or traversal.
Receives the ordered path (list of node IDs).

```python
def observe_traversal(self, path: list[str]) -> None:
    for i in range(len(path) - 1):
        a, b = path[i], path[i+1]
        record = self._get_or_create_record(a, b)
        record.a_before_b_count += 1
        record.total_observations += 1
```

### Learning Algorithm

```python
def learn(self) -> CausalLearningResult:
    created = 0
    updated = 0

    for (a, b), record in self._records.items():
        if record.total_observations < self._min_observations:
            continue

        co_activation_freq = record.co_activation_count / max(record.total_observations, 1)
        if co_activation_freq < self._min_co_activation:
            continue

        # Determine direction: does A precede B or B precede A?
        total_dir = record.a_before_b_count + record.b_before_a_count
        if total_dir == 0:
            continue
        a_first_ratio = record.a_before_b_count / total_dir

        cause, effect = (a, b) if a_first_ratio >= 0.5 else (b, a)
        precedence = max(a_first_ratio, 1.0 - a_first_ratio)

        if precedence < self._min_precedence_ratio:
            continue

        # Update or create hypothesis
        existing = self.get_hypothesis(cause, effect)
        if existing:
            # Thompson sampling update: success = hypothesis confirmed
            existing.thompson_alpha += 1
            existing.confidence = existing.thompson_alpha / (existing.thompson_alpha + existing.thompson_beta)
            existing.observations += 1
            existing.precedence_ratio = precedence
            existing.co_activation_frequency = co_activation_freq
            updated += 1
        else:
            hypothesis = CausalHypothesis(
                cause_id=cause,
                effect_id=effect,
                confidence=0.5,
                co_activation_frequency=co_activation_freq,
                precedence_ratio=precedence,
                observations=1,
                thompson_alpha=1.0,
                thompson_beta=1.0,
            )
            self._hypotheses[(cause, effect)] = hypothesis
            created += 1

    pruned = self.prune()
    return CausalLearningResult(
        hypotheses_created=created,
        hypotheses_updated=updated,
        hypotheses_pruned=pruned,
        total_observations=sum(r.total_observations for r in self._records.values()),
        top_hypotheses=sorted(self._hypotheses.values(),
                             key=lambda h: h.confidence, reverse=True)[:10],
    )
```

### Hypothesis Materialization

`learn()` does NOT create edges. It only updates internal hypothesis state.
To materialize hypotheses as graph edges, the mixin calls:

```python
def materialize_hypotheses(self, *, min_confidence: float = 0.5) -> list[str]:
    edge_ids = []
    for hyp in self._hypotheses.values():
        if hyp.confidence >= min_confidence:
            edge = Hyperedge(
                source_ids=frozenset({hyp.cause_id}),
                target_ids=frozenset({hyp.effect_id}),
                label="learned_causes",
                metadata=Metadata(custom={
                    "rule": "causal_learner",
                    "inferred": True,
                    "confidence": hyp.confidence,
                    "observations": hyp.observations,
                    "precedence_ratio": hyp.precedence_ratio,
                    "co_activation_frequency": hyp.co_activation_frequency,
                }),
            )
            self._graph.add_edge(edge)
            edge_ids.append(edge.id)
    return edge_ids
```

### Key Design Decisions

1. **Separate observation from learning**: Observations accumulate passively.
   Learning is triggered explicitly. This lets users control when hypotheses are
   updated.

2. **Separate learning from materialization**: Hypotheses live in the learner
   before becoming graph edges. This allows review before commit.

3. **Thompson sampling for confidence**: Rather than a fixed confidence formula,
   each hypothesis maintains Beta distribution parameters. Confidence is sampled,
   allowing exploration of uncertain hypotheses.

4. **Direction from precedence ratio**: The key insight is that causal direction
   comes from which node consistently appears first in traversals. If A appears
   before B in 80% of observed traversals, A is a plausible cause of B.

## Design: Layer 2 -- Mixin Wiring

### ReasoningMixin (memory_reasoning.py)

Add two methods:

```python
def learn_causal_patterns(self) -> CausalLearningResult:
    if self._causal_learner is None:
        self._causal_learner = CausalLearner(self._graph)
    return self._causal_learner.learn()

def commit_causal_hypotheses(self, *, min_confidence: float = 0.5) -> list[str]:
    if self._causal_learner is None:
        return []
    return self._causal_learner.materialize_hypotheses(min_confidence=min_confidence)
```

### Observation Hooks

Wire observation into existing operations:

```python
# In activate() / spread_activation():
if self._causal_learner is not None:
    self._causal_learner.observe_activation(activation_state)

# In find_paths():
if self._causal_learner is not None:
    for path in paths:
        self._causal_learner.observe_traversal(path)
```

## Design: Layer 3 -- Facade

```python
def learn_causal_patterns(self) -> CausalLearningResult:
    return ReasoningMixin.learn_causal_patterns(self)
```

## Challenge: Observation Bias

Nodes at the top of the graph (high in-degree) will naturally appear in more
traversals, creating spurious causal hypotheses. Mitigation: normalize
precedence ratios by each node's total traversal frequency. A node that appears
in 100 traversals and precedes B in 70 has a stronger signal than a node that
appears in 10 traversals and precedes B in 7, even though both have 0.7 ratio.

## Test Plan (~25 tests)

- Engine construction
- `observe_activation`: records co-activation pairs
- `observe_activation`: single node -> no pairs
- `observe_traversal`: records directed precedence
- `observe_traversal`: single-node path -> no records
- `learn`: below min_observations -> no hypotheses
- `learn`: sufficient observations with clear direction -> hypothesis created
- `learn`: bidirectional (equal precedence) -> no hypothesis
- `learn`: multiple observations update existing hypothesis
- `learn`: Thompson sampling increases confidence on repeated confirmation
- `learn`: pruning removes low-confidence hypotheses
- `get_hypotheses`: returns all hypotheses
- `get_hypotheses`: filtered by concept -> returns relevant only
- `get_hypothesis`: specific pair -> returns hypothesis or None
- `materialize_hypotheses`: creates edges for confident hypotheses
- `materialize_hypotheses`: min_confidence filter works
- `to_dict` / `from_dict`: round-trip serialization
- Integration: activation + learn + materialize produces causal edges
- Edge: no observations -> empty result
- Edge: all observations below thresholds -> no hypotheses
- Edge: max_hypotheses limits hypothesis count
- Precedence ratio computed correctly
- Co-activation frequency computed correctly
- Multiple learn calls accumulate observations
- Observation bias mitigation: high-frequency nodes don't dominate

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/causal_learner.py` | NEW | ~500 LoC |
| `tests/test_causal_learner.py` | NEW | ~450 LoC |
| `src/hyper3/memory_reasoning.py` | MODIFY | +30 LoC (learn + commit + hooks) |
| `src/hyper3/memory.py` | MODIFY | +8 LoC (shortcut) |
| `src/hyper3/memory_base.py` | MODIFY | +2 LoC (type declaration) |
| `src/hyper3/__init__.py` | MODIFY | +3 exports |

**Estimated total**: ~950 LoC new, ~40 LoC modified.
