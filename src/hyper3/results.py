from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class _SimpleResultBase:
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

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
        val = getattr(self, key, default)
        return default if val is None else val

    def keys(self) -> list[str]:
        return [k for k in getattr(self, '__dataclass_fields__', {}) if not k.startswith('_')]

    def items(self) -> list[tuple[str, Any]]:
        return [(k, getattr(self, k)) for k in self.keys()]


@dataclass
class ExpansionInfo(_SimpleResultBase):
    states_created: int = 0
    rules_applied: int = 0
    nodes_produced: int = 0
    edges_produced: int = 0
    branches: int = 0
    max_depth: int = 0


@dataclass
class ReasonResult(_SimpleResultBase):
    expansion: ExpansionInfo | None = None
    state_convergence: MergeReport | None = None
    branchial: BranchialAnalysis | None = None
    rulial: RulialAnalysis | None = None
    multiway_leaves: int = 0
    overlay: dict[str, int] | None = None
    confidence: dict[str, float] | None = None
    auto_distributions: list[dict[str, Any]] | None = None
    frame_config: dict[str, Any] | None = None
    error: str | None = None
    states_created: int = 0


@dataclass
class IterativeReasonResult(_SimpleResultBase):
    iterations: int = 0
    total_edges_produced: int = 0
    iteration_details: list[ReasonResult] = field(default_factory=list)
    error: str | None = None
    states_created: int = 0


@dataclass
class ConsensusReasonResult(_SimpleResultBase):
    invariant_nodes: int = 0
    invariant_edges: int = 0
    confidence: float = 0.0
    frame_count: int = 0
    frame_unique_counts: dict[str, int] = field(default_factory=dict)
    reasoning: ReasonResult = field(default_factory=ReasonResult)
    error: str | None = None


@dataclass
class MergeReport(_SimpleResultBase):
    merges_performed: int = 0
    states_before: int = 0
    states_after: int = 0
    reduction: int = 0


@dataclass
class EvolveResult(_SimpleResultBase):
    decayed: int = 0
    pruned: int = 0
    merged: int = 0
    reinforced: int = 0
    suppressed: int = 0
    node_count: int = 0
    edge_count: int = 0
    convergence: MergeReport | None = None


@dataclass
class BranchialAnalysis(_SimpleResultBase):
    states_mapped: int = 0
    clusters: int = 0
    correlations: int = 0
    simultaneity_groups: int = 0
    avg_cluster_size: float = 0.0
    avg_correlation_strength: float = 0.0
    multi_scale_available: bool = True


@dataclass
class RulialAnalysis(_SimpleResultBase):
    graph_activity_density: float = 0.0
    structural_complexity: float = 0.0
    spectral_entropy: float = 0.0
    rule_diversity: int = 0
    total_applications: int = 0
    rule_effectiveness: dict[str, dict[str, float]] = field(default_factory=dict)
    meta_patterns: int = 0
    high_level_insights: int = 0
    position_history_length: int = 0


@dataclass
class PerspectiveAnalysis(_SimpleResultBase):
    available_frames: list[str] = field(default_factory=list)
    transformations_computed: int = 0
    frame_effectiveness: dict[str, float] = field(default_factory=dict)


@dataclass
class AnomalyAnalysis(_SimpleResultBase):
    mapped_regions: int = 0
    low_risk: int = 0
    boundary: int = 0
    anomalous: int = 0
    reasoning_history: int = 0


@dataclass
class DiscoveryAnalysis(_SimpleResultBase):
    total_patterns: int = 0
    new_patterns: int = 0
    active_rules: int = 0
    edge_labels: dict[str, int] = field(default_factory=dict)
    pattern_types: dict[str, int] = field(default_factory=dict)


@dataclass
class LateralInferenceInsight(_SimpleResultBase):
    source_state: str = ""
    lateral_state: str = ""
    rule_used: str | None = None
    novel_in_source: list[str] = field(default_factory=list)
    novel_in_lateral: list[str] = field(default_factory=list)
    complementary_nodes: list[str] = field(default_factory=list)
    transferable_patterns: list[str] = field(default_factory=list)
    branchial_distance: float = 0.0
    semantic_novelty_scores: dict[str, float] | None = None


@dataclass
class RuleNeighborhoodResult(_SimpleResultBase):
    explored_rules: list[str] = field(default_factory=list)
    rule_diversity: int = 0
    graph_activity_density: float = 0.0
    coverage: float = 0.0
    unexplored: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class TemporalConsistencyResult(_SimpleResultBase):
    consistent: bool = True
    relation: str = ""
    edge_a_interval_start: float = 0.0
    edge_a_interval_end: float = 0.0
    edge_b_interval_start: float = 0.0
    edge_b_interval_end: float = 0.0
    reason: str = ""


@dataclass
class TemporalInconsistency(_SimpleResultBase):
    event_a: str = ""
    event_b: str = ""
    actual_relation: str = ""
    expected_relation: str = ""


@dataclass
class EvolutionStats(_SimpleResultBase):
    merges: int = 0
    prunes: int = 0
    refinements: int = 0


@dataclass
class MonitorStats(_SimpleResultBase):
    architectural_fitness: float = 0.0
    reasoning_mode: str = ""
    meta_level: int = 0
    introspections: int = 0
    metamorphoses: int = 0
    rulial_insight_count: float = 0.0


@dataclass
class MemoryStats(_SimpleResultBase):
    nodes: int = 0
    edges: int = 0
    log_size: int = 0
    cache_size: int = 0
    operations: int = 0
    multiway_states: int = 0
    belief_active: int = 0
    belief_resolved: int = 0
    evolution: EvolutionStats = field(default_factory=EvolutionStats)
    discovered_patterns: int = 0
    cycles: bool = False
    components: int = 0
    active_rules: int = 0
    overlay_active: bool = False
    overlay_edges: int = 0
    rulial: RulialAnalysis | None = None
    monitor_stats: MonitorStats = field(default_factory=MonitorStats)
    multi_edge_count: int = 0


@dataclass
class DiscoverResult(_SimpleResultBase):
    total_patterns: int = 0
    new_rules_added: int = 0
    analysis: DiscoveryAnalysis | None = None


@dataclass
class TrainResult(_SimpleResultBase):
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
class HealthInfo(_SimpleResultBase):
    fitness: float = 0.0
    mode: str = ""
    meta_level: int = 0
    rulial_insight_count: int = 0


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
class HealthReport(_SimpleResultBase):
    system_health: HealthInfo = field(default_factory=HealthInfo)
    graph_health: GraphHealthInfo = field(default_factory=GraphHealthInfo)
    evolution_health: EvolutionHealthInfo = field(default_factory=EvolutionHealthInfo)
    discovery_health: DiscoveryHealthInfo = field(default_factory=DiscoveryHealthInfo)
    rulial_health: RulialAnalysis | None = None
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


@dataclass
class TuningResult(_SimpleResultBase):
    results: dict[str, Any] = field(default_factory=dict)
    validated: bool = False
    rolled_back: bool = False
    fitness_before: float = 0.0
    fitness_after: float = 0.0
    improvement: float = 0.0
    actions_taken: int = 0
    delta: Any = None


@dataclass
class GraphDescription(_SimpleResultBase):
    node_count: int = 0
    edge_count: int = 0
    node_types: dict[str, int] = field(default_factory=dict)
    edge_labels: dict[str, int] = field(default_factory=dict)
    degree_min: int = 0
    degree_max: int = 0
    degree_mean: float = 0.0
    degree_median: float = 0.0
    isolated_nodes: int = 0
    components: int = 0
    density: float = 0.0


@dataclass
class SPersistenceLevel(_SimpleResultBase):
    s: int = 1
    components: list[frozenset[str]] = field(default_factory=list)
    num_components: int = 0
    largest_component_size: int = 0


@dataclass
class SPersistenceResult(_SimpleResultBase):
    levels: list[SPersistenceLevel] = field(default_factory=list)
    max_s: int = 1
    total_edges: int = 0


@dataclass
class HyperedgeSimilarityResult(_SimpleResultBase):
    query_edge_id: str = ""
    similar_edges: list[tuple[str, float]] = field(default_factory=list)
    metric: str = "jaccard"


@dataclass
class HypergraphCutResult(_SimpleResultBase):
    partitions: list[frozenset[str]] = field(default_factory=list)
    cut_value: float = 0.0
    normalized_cut_value: float = 0.0


@dataclass
class SpectralEmbeddingResult(_SimpleResultBase):
    node_ids: list[str] = field(default_factory=list)
    embeddings: Any = None
    eigenvalues: Any = None
    dimensions: int = 0


def top_k(scores: dict[str, float], k: int = 10) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda x: -x[1])[:k]
