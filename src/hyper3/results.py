from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class _ResultBase:
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        if not hasattr(self, key) or key.startswith('_'):
            return False
        val = getattr(self, key)
        if isinstance(val, (int, float, bool)):
            return True
        return val is not None

    def get(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, key) or key.startswith('_'):
            return default
        return getattr(self, key, default)


class _SimpleResultBase:
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) and not key.startswith('_')

    def get(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, key) or key.startswith('_'):
            return default
        return getattr(self, key, default)


@dataclass
class ExpansionInfo(_SimpleResultBase):
    states_created: int = 0
    rules_applied: int = 0
    nodes_produced: int = 0
    edges_produced: int = 0
    branches: int = 0
    max_depth: int = 0


@dataclass
class ReasonResult(_ResultBase):
    expansion: ExpansionInfo | None = None
    causal_invariance: dict[str, Any] | None = None
    branchial: dict[str, Any] | None = None
    rulial: dict[str, Any] | None = None
    multiway_leaves: int = 0
    overlay: dict[str, int] | None = None
    confidence: dict[str, float] | None = None
    auto_superpositions: list[dict[str, Any]] | None = None
    frame_config: dict[str, Any] | None = None
    error: str | None = None
    states_created: int = 0


@dataclass
class IterativeReasonResult(_ResultBase):
    iterations: int = 0
    total_edges_produced: int = 0
    iteration_details: list[ReasonResult] = field(default_factory=list)
    error: str | None = None
    states_created: int = 0


@dataclass
class ConsensusReasonResult(_ResultBase):
    invariant_nodes: int = 0
    invariant_edges: int = 0
    confidence: float = 0.0
    frame_count: int = 0
    frame_unique_counts: dict[str, int] = field(default_factory=dict)
    reasoning: ReasonResult = field(default_factory=ReasonResult)
    error: str | None = None


@dataclass
class EvolveResult(_SimpleResultBase):
    decayed: int = 0
    pruned: int = 0
    merged: int = 0
    node_count: int = 0
    edge_count: int = 0
    causal: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolutionStats(_SimpleResultBase):
    merges: int = 0
    prunes: int = 0
    refinements: int = 0


@dataclass
class MetaCognitiveStats(_SimpleResultBase):
    architectural_fitness: float = 0.0
    reasoning_mode: str = ""
    meta_level: int = 0
    introspections: int = 0
    metamorphoses: int = 0
    transcendental_yield: float = 0.0


@dataclass
class MemoryStats(_SimpleResultBase):
    nodes: int = 0
    edges: int = 0
    log_size: int = 0
    cache_size: int = 0
    operations: int = 0
    multiway_states: int = 0
    quantum_active: int = 0
    quantum_collapsed: int = 0
    evolution: EvolutionStats = field(default_factory=EvolutionStats)
    discovered_patterns: int = 0
    cycles: bool = False
    components: int = 0
    active_rules: int = 0
    overlay_active: bool = False
    overlay_edges: int = 0
    rulial: dict[str, Any] = field(default_factory=dict)
    meta_cognitive: MetaCognitiveStats = field(default_factory=MetaCognitiveStats)


@dataclass
class DiscoverResult(_SimpleResultBase):
    total_patterns: int = 0
    new_rules_added: int = 0
    analysis: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainResult(_ResultBase):
    trained: bool = False
    weights: dict[str, float] = field(default_factory=dict)
    samples: int = 0
    reason: str = ""


@dataclass
class CommitResult(_SimpleResultBase):
    committed_nodes: int = 0
    committed_edges: int = 0


@dataclass
class RollbackResult(_SimpleResultBase):
    rolled_back_nodes: int = 0
    rolled_back_edges: int = 0
