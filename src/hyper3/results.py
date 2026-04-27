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
    reinforced: int = 0
    suppressed: int = 0
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
    multi_edge_count: int = 0


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


@dataclass
class BackwardChainResult(_ResultBase):
    goal_id: str = ""
    goal_label: str = ""
    achievable: bool = False
    total_premises_needed: int = 0
    satisfied_premises: int = 0
    missing_premises: list = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class HebbianResult(_SimpleResultBase):
    edges_strengthened: int = 0
    edges_weakened: int = 0
    total_co_activations: int = 0
    avg_weight_change: float = 0.0


@dataclass
class RevisionResult(_SimpleResultBase):
    contradictions_detected: int = 0
    edges_revised: int = 0
    edges_removed_count: int = 0
    edges_kept_count: int = 0


@dataclass
class CommunityResult(_SimpleResultBase):
    community_count: int = 0
    modularity: float = 0.0
    coverage: float = 0.0
    largest_community_size: int = 0
    avg_community_size: float = 0.0


@dataclass
class GraphDeltaResult(_SimpleResultBase):
    total_changes: int = 0
    node_count_before: int = 0
    node_count_after: int = 0
    edge_count_before: int = 0
    edge_count_after: int = 0
    nodes_added: int = 0
    nodes_removed: int = 0
    edges_added: int = 0
    edges_removed: int = 0


@dataclass
class DerivationInfo(_SimpleResultBase):
    rule: str = ""
    bindings: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternMatchInfo(_SimpleResultBase):
    edge_id: str = ""
    label: str = ""
    source_labels: list[str] = field(default_factory=list)
    target_labels: list[str] = field(default_factory=list)
    bindings: dict[str, str] = field(default_factory=dict)


@dataclass
class SubgraphNode(_SimpleResultBase):
    id: str = ""
    label: str = ""


@dataclass
class SubgraphEdge(_SimpleResultBase):
    id: str = ""
    label: str = ""
    source_labels: list[str] = field(default_factory=list)
    target_labels: list[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class SubgraphResult(_SimpleResultBase):
    nodes: list[SubgraphNode] = field(default_factory=list)
    edges: list[SubgraphEdge] = field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


@dataclass
class TemporalMatch(_SimpleResultBase):
    label: str = ""
    start: float = 0.0
    end: float = 0.0
    gap: float | None = None


@dataclass
class ImportResult(_SimpleResultBase):
    nodes: int = 0
    edges: int = 0


@dataclass
class CognitiveStateInfo(_SimpleResultBase):
    fitness: float = 0.0
    mode: str = ""
    meta_level: int = 0
    transcendental_yield: int = 0


@dataclass
class GraphHealthInfo(_SimpleResultBase):
    nodes: int = 0
    edges: int = 0
    avg_degree: float = 0.0


@dataclass
class EvolutionHealthInfo(_SimpleResultBase):
    merges: int = 0
    prunes: int = 0
    refinements: int = 0


@dataclass
class DiscoveryHealthInfo(_SimpleResultBase):
    patterns: int = 0
    active_rules: int = 0


@dataclass
class IntrospectionReport(_SimpleResultBase):
    cognitive_state: CognitiveStateInfo = field(default_factory=CognitiveStateInfo)
    graph_health: GraphHealthInfo = field(default_factory=GraphHealthInfo)
    evolution_health: EvolutionHealthInfo = field(default_factory=EvolutionHealthInfo)
    discovery_health: DiscoveryHealthInfo = field(default_factory=DiscoveryHealthInfo)
    rulial_health: dict[str, Any] | None = None
    anti_patterns: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class CorrelatedNodeInfo(_SimpleResultBase):
    positive_rate: float = 0.0
    signal_count: int = 0
    signal_types: list[str] = field(default_factory=list)


@dataclass
class FeedbackSummaryResult(_SimpleResultBase):
    collapse_accuracy: float = 0.5
    retrieval_precision: float = 0.5
    inference_acceptance_rate: float = 0.5
    fitness_trend: str = "insufficient_data"
    overall_health: float = 0.5
    signal_type_distribution: dict[str, int] = field(default_factory=dict)
    total_signals: int = 0
    correlated_nodes: dict[str, CorrelatedNodeInfo] = field(default_factory=dict)


@dataclass
class BiasProfileResult(_SimpleResultBase):
    dominant_rules: list[str] = field(default_factory=list)
    underused_rules: list[str] = field(default_factory=list)
    reasoning_style: str = "unknown"
    position_trajectory: str = "no_data"
    bias_score: float = 0.0
    average_effectiveness: float = 0.0
    rule_count: int = 0
