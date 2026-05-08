from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class _SimpleResultBase:
    """Base class for all result dataclasses, providing dict-like bracket access, ``keys()``, ``items()``, and ``get()`` alongside standard attribute access."""

    def __getitem__(self, key: str) -> Any:
        """Return the value of a dataclass field by name (``result["field"]``)."""
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        """Check whether a non-private field exists and is non-None (``"field" in result``)."""
        if not hasattr(self, key) or key.startswith("_"):
            return False
        val = getattr(self, key)
        if isinstance(val, (int, float, bool)):
            return True
        return val is not None

    def get(self, key: str, default: Any = None) -> Any:
        """Return field value or *default* when the field is ``None`` or absent."""
        if not hasattr(self, key) or key.startswith("_"):
            return default
        val = getattr(self, key, default)
        return default if val is None else val

    def keys(self) -> list[str]:
        """Return a list of public dataclass field names."""
        return [k for k in getattr(self, "__dataclass_fields__", {}) if not k.startswith("_")]

    def items(self) -> list[tuple[str, Any]]:
        """Return ``(field, value)`` pairs for every public dataclass field."""
        return [(k, getattr(self, k)) for k in self.keys()]


@dataclass
class ExpansionInfo(_SimpleResultBase):
    """Summary of a single multiway expansion step: states created, rules applied, and nodes/edges produced."""
    states_created: int = 0
    rules_applied: int = 0
    nodes_produced: int = 0
    edges_produced: int = 0
    branches: int = 0
    max_depth: int = 0


@dataclass
class ReasonResult(_SimpleResultBase):
    """Aggregated result of a reasoning pass: expansion statistics, state convergence, clustering/rule-analytics analysis, overlay state, and per-node confidence."""
    expansion: ExpansionInfo | None = None
    state_convergence: MergeReport | None = None
    clustering: StateClusteringReport | None = None
    rule_analytics: RuleAnalyticsReport | None = None
    multiway_leaves: int = 0
    overlay: dict[str, int] | None = None
    confidence: dict[str, float] | None = None
    auto_distributions: list[dict[str, Any]] | None = None
    frame_config: dict[str, Any] | None = None
    error: str | None = None
    states_created: int = 0


@dataclass
class IterativeReasonResult(_SimpleResultBase):
    """Result of iterative reasoning over multiple rounds, with per-iteration details and cumulative edge production."""
    iterations: int = 0
    total_edges_produced: int = 0
    iteration_details: list[ReasonResult] = field(default_factory=list)
    error: str | None = None
    states_created: int = 0


@dataclass
class ConsensusReasonResult(_SimpleResultBase):
    """Result of consensus reasoning across multiple computational frames, reporting nodes/edges invariant under all frames."""
    invariant_nodes: int = 0
    invariant_edges: int = 0
    confidence: float = 0.0
    frame_count: int = 0
    frame_unique_counts: dict[str, int] = field(default_factory=dict)
    reasoning: ReasonResult = field(default_factory=ReasonResult)
    error: str | None = None


@dataclass
class FrameContribution(_SimpleResultBase):
    """Per-frame contribution metrics in fused multi-frame reasoning."""
    frame_name: str = ""
    edges_produced: int = 0
    avg_confidence: float = 0.0
    information_loss: float = 0.0
    unique_edges: int = 0


@dataclass
class FusedReasonResult(_SimpleResultBase):
    """Result of multi-frame fused reasoning with per-frame breakdown, agreement ratio, and fusion strategy."""
    frame_count: int = 0
    fused_edges: int = 0
    fused_confidence: float = 0.0
    agreement_ratio: float = 0.0
    frame_contributions: list[FrameContribution] = field(default_factory=list)
    per_frame_results: dict[str, ReasonResult] = field(default_factory=dict)
    best_frame: str = ""
    fusion_strategy: str = ""
    error: str | None = None


@dataclass
class MergeReport(_SimpleResultBase):
    """Report from state convergence: number of merges, states before/after, and total reduction."""
    merges_performed: int = 0
    states_before: int = 0
    states_after: int = 0
    reduction: int = 0


@dataclass
class EvolveResult(_SimpleResultBase):
    """Result of a graph maintenance cycle: counts of decayed, pruned, merged, reinforced, and suppressed elements."""
    decayed: int = 0
    pruned: int = 0
    merged: int = 0
    reinforced: int = 0
    suppressed: int = 0
    node_count: int = 0
    edge_count: int = 0
    convergence: MergeReport | None = None


@dataclass
class StateClusteringReport(_SimpleResultBase):
    """Summary of state clustering report: states mapped, cluster/correlation counts, and average cluster size."""
    states_mapped: int = 0
    clusters: int = 0
    correlations: int = 0
    simultaneity_groups: int = 0
    avg_cluster_size: float = 0.0
    avg_correlation_strength: float = 0.0
    multi_scale_available: bool = True


@dataclass
class RuleAnalyticsReport(_SimpleResultBase):
    """Rule analytics report: activity density, structural complexity, spectral entropy, rule diversity, and effectiveness tracking."""
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
    """Summary of multi-perspective analysis: available computational frames, transformations computed, and per-frame effectiveness."""
    available_frames: list[str] = field(default_factory=list)
    transformations_computed: int = 0
    frame_effectiveness: dict[str, float] = field(default_factory=dict)


@dataclass
class AnomalyAnalysis(_SimpleResultBase):
    """Structural anomaly detection summary: counts of mapped regions classified as low_risk, boundary, or anomalous."""
    mapped_regions: int = 0
    low_risk: int = 0
    boundary: int = 0
    anomalous: int = 0
    reasoning_history: int = 0


@dataclass
class DiscoveryAnalysis(_SimpleResultBase):
    """Result of rule discovery analysis: total and new patterns found, active rules, and breakdowns by edge label and pattern type."""
    total_patterns: int = 0
    new_patterns: int = 0
    active_rules: int = 0
    edge_labels: dict[str, int] = field(default_factory=dict)
    pattern_types: dict[str, int] = field(default_factory=dict)


@dataclass
class LateralInferenceInsight(_SimpleResultBase):
    """Insight from lateral inference between two clustering states: novel elements, complementary nodes, transferable patterns, and state distance."""
    source_state: str = ""
    lateral_state: str = ""
    rule_used: str | None = None
    novel_in_source: list[str] = field(default_factory=list)
    novel_in_lateral: list[str] = field(default_factory=list)
    complementary_nodes: list[str] = field(default_factory=list)
    transferable_patterns: list[str] = field(default_factory=list)
    state_distance: float = 0.0
    semantic_novelty_scores: dict[str, float] | None = None


@dataclass
class RuleNeighborhoodResult(_SimpleResultBase):
    """Result of exploring the rule neighborhood around the current rule set: explored rules, diversity, coverage, and unexplored regions."""
    explored_rules: list[str] = field(default_factory=list)
    rule_diversity: int = 0
    graph_activity_density: float = 0.0
    coverage: float = 0.0
    unexplored: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class TemporalConsistencyResult(_SimpleResultBase):
    """Result of checking temporal consistency between two edges: whether they are consistent, the Allen relation, and interval endpoints."""
    consistent: bool = True
    relation: str = ""
    edge_a_interval_start: float = 0.0
    edge_a_interval_end: float = 0.0
    edge_b_interval_start: float = 0.0
    edge_b_interval_end: float = 0.0
    reason: str = ""


@dataclass
class TemporalInconsistency(_SimpleResultBase):
    """Record of a temporal inconsistency between two events: the actual vs. expected Allen relation."""
    event_a: str = ""
    event_b: str = ""
    actual_relation: str = ""
    expected_relation: str = ""


@dataclass
class EvolutionStats(_SimpleResultBase):
    """Cumulative evolution statistics: total merges, prunes, and refinements performed."""
    merges: int = 0
    prunes: int = 0
    refinements: int = 0


@dataclass
class MonitorStats(_SimpleResultBase):
    """System monitor statistics: architectural fitness, reasoning mode, meta level, and operation counts."""
    architectural_fitness: float = 0.0
    reasoning_mode: str = ""
    meta_level: int = 0
    introspections: int = 0
    metamorphoses: int = 0
    rule_analytics_insight_count: float = 0.0


@dataclass
class MemoryStats(_SimpleResultBase):
    """Comprehensive memory subsystem statistics: graph size, log/cache/operation counts, multiway/belief/overlay state, evolution stats, and monitor stats."""
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
    rule_analytics: RuleAnalyticsReport | None = None
    monitor_stats: MonitorStats = field(default_factory=MonitorStats)
    multi_edge_count: int = 0


@dataclass
class DiscoverResult(_SimpleResultBase):
    """Result of rule discovery: total patterns found, new rules added, and detailed discovery analysis."""
    total_patterns: int = 0
    new_rules_added: int = 0
    analysis: DiscoveryAnalysis | None = None


@dataclass
class TrainResult(_SimpleResultBase):
    """Result of training a retrieval/ranking model: whether training occurred, learned weights, sample count, and reason."""
    trained: bool = False
    weights: dict[str, float] = field(default_factory=dict)
    samples: int = 0
    reason: str = ""


@dataclass
class CommitResult(_SimpleResultBase):
    """Result of committing an overlay: counts of nodes and edges merged into the base graph."""
    committed_nodes: int = 0
    committed_edges: int = 0


@dataclass
class RollbackResult(_SimpleResultBase):
    """Result of rolling back an overlay: counts of nodes and edges discarded."""
    rolled_back_nodes: int = 0
    rolled_back_edges: int = 0


@dataclass
class DerivationInfo(_SimpleResultBase):
    """Provenance record for an inferred edge: the rule name, variable bindings, and context used during inference."""
    rule: str = ""
    bindings: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternMatchInfo(_SimpleResultBase):
    """Details of a pattern match: the matched edge ID, label, resolved source/target labels, and variable bindings."""
    edge_id: str = ""
    label: str = ""
    source_labels: list[str] = field(default_factory=list)
    target_labels: list[str] = field(default_factory=list)
    bindings: dict[str, str] = field(default_factory=dict)


@dataclass
class SubgraphNode(_SimpleResultBase):
    """Lightweight representation of a node in a subgraph result, carrying ID and label."""
    id: str = ""
    label: str = ""


@dataclass
class SubgraphEdge(_SimpleResultBase):
    """Lightweight representation of an edge in a subgraph result, carrying ID, label, resolved source/target labels, and weight."""
    id: str = ""
    label: str = ""
    source_labels: list[str] = field(default_factory=list)
    target_labels: list[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class SubgraphResult(_SimpleResultBase):
    """Extracted subgraph with resolved label-based node and edge representations and counts."""
    nodes: list[SubgraphNode] = field(default_factory=list)
    edges: list[SubgraphEdge] = field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


@dataclass
class TemporalMatch(_SimpleResultBase):
    """A temporal pattern match: the matched label, interval [start, end], and optional gap to the next event."""
    label: str = ""
    start: float = 0.0
    end: float = 0.0
    gap: float | None = None


@dataclass
class ImportResult(_SimpleResultBase):
    """Result of importing data into the graph: counts of nodes and edges added."""
    nodes: int = 0
    edges: int = 0


@dataclass
class HealthInfo(_SimpleResultBase):
    """System-level health metrics: architectural fitness, reasoning mode, meta level, and rule analytics insight count."""
    fitness: float = 0.0
    mode: str = ""
    meta_level: int = 0
    rule_analytics_insight_count: int = 0


@dataclass
class GraphHealthInfo(_SimpleResultBase):
    """Graph structural health metrics: node/edge counts and average degree."""
    nodes: int = 0
    edges: int = 0
    avg_degree: float = 0.0


@dataclass
class EvolutionHealthInfo(_SimpleResultBase):
    """Evolution subsystem health metrics: cumulative merges, prunes, and refinements."""
    merges: int = 0
    prunes: int = 0
    refinements: int = 0


@dataclass
class DiscoveryHealthInfo(_SimpleResultBase):
    """Rule discovery subsystem health metrics: discovered patterns and active rule count."""
    patterns: int = 0
    active_rules: int = 0


@dataclass
class HealthReport(_SimpleResultBase):
    """Comprehensive system health report aggregating system, graph, evolution, discovery, and rule-analytics health with recommendations."""
    system_health: HealthInfo = field(default_factory=HealthInfo)
    graph_health: GraphHealthInfo = field(default_factory=GraphHealthInfo)
    evolution_health: EvolutionHealthInfo = field(default_factory=EvolutionHealthInfo)
    discovery_health: DiscoveryHealthInfo = field(default_factory=DiscoveryHealthInfo)
    rule_analytics_health: RuleAnalyticsReport | None = None
    anti_patterns: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class CorrelatedNodeInfo(_SimpleResultBase):
    """Cross-operation correlation info for a node: positive signal rate, signal count, and contributing signal types."""
    positive_rate: float = 0.0
    signal_count: int = 0
    signal_types: list[str] = field(default_factory=list)


@dataclass
class FeedbackSummaryResult(_SimpleResultBase):
    """Aggregate feedback across sampling, retrieval, inference, and evolution operations with overall health and correlated nodes."""
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
    """Reasoning bias profile: dominant and underused rules, reasoning style, position trajectory, and average effectiveness."""
    dominant_rules: list[str] = field(default_factory=list)
    underused_rules: list[str] = field(default_factory=list)
    reasoning_style: str = "unknown"
    position_trajectory: str = "no_data"
    bias_score: float = 0.0
    average_effectiveness: float = 0.0
    rule_count: int = 0


@dataclass
class TuningResult(_SimpleResultBase):
    """Result of an auto-tuning or metamorphosis operation: actions taken, fitness before/after, improvement, and optional rollback state."""
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
    """Descriptive summary of a graph: node/edge counts, type and label distributions, degree statistics, isolated nodes, components, and density."""
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
    """One level of the s-persistence filtration: the s value, s-connected components, component count, and largest component size."""
    s: int = 1
    components: list[frozenset[str]] = field(default_factory=list)
    num_components: int = 0
    largest_component_size: int = 0


@dataclass
class SPersistenceResult(_SimpleResultBase):
    """Complete s-persistence filtration: list of SPersistenceLevel entries from s=1 to max_s, with total edge count."""
    levels: list[SPersistenceLevel] = field(default_factory=list)
    max_s: int = 1
    total_edges: int = 0


@dataclass
class HyperedgeSimilarityResult(_SimpleResultBase):
    """Result of hyperedge similarity search: the query edge ID, ranked list of similar (edge_id, score) pairs, and the metric used."""
    query_edge_id: str = ""
    similar_edges: list[tuple[str, float]] = field(default_factory=list)
    metric: str = "jaccard"


@dataclass
class HypergraphCutResult(_SimpleResultBase):
    """Result of a hypergraph partitioning cut: the partitions, raw cut value, and normalized cut value."""
    partitions: list[frozenset[str]] = field(default_factory=list)
    cut_value: float = 0.0
    normalized_cut_value: float = 0.0


@dataclass
class SpectralEmbeddingResult(_SimpleResultBase):
    """Result of spectral embedding computation: node IDs, embedding vectors, eigenvalues, and requested dimensions."""
    node_ids: list[str] = field(default_factory=list)
    embeddings: Any = None
    eigenvalues: Any = None
    dimensions: int = 0


@dataclass
class AdjacencyTensorResult(_SimpleResultBase):
    """Result of adjacency tensor construction for a k-uniform hypergraph.

    Stores nonzero entries in COO (coordinate) format.
    T[coords[i]] = values[i] for each nonzero entry.
    """
    order: int = 0
    n_nodes: int = 0
    n_nonzero: int = 0
    coords: Any = None
    values: Any = None
    node_ids: list[str] = field(default_factory=list)
    dense_tensor: Any = None


@dataclass
class LabeledEdge(_SimpleResultBase):
    """A hyperedge with source and target labels resolved from internal IDs."""
    id: str = ""
    label: str = ""
    source_labels: list[str] = field(default_factory=list)
    target_labels: list[str] = field(default_factory=list)
    weight: float = 1.0
    source_cardinality: int = 1
    target_cardinality: int = 1


@dataclass
class NodeInfo(_SimpleResultBase):
    """Typed snapshot of a node's label, data, weight, and access count."""
    label: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    access_count: int = 0


@dataclass
class EdgeInfo(_SimpleResultBase):
    """Typed snapshot of an edge's label, source/target labels, weight, and data."""
    id: str = ""
    label: str = ""
    source: str | list[str] = ""
    target: str | list[str] = ""
    weight: float = 1.0
    is_hyperedge: bool = False
    data: dict[str, Any] | None = None


@dataclass
class SearchHit(_SimpleResultBase):
    """A search result hit with concept label, score, and optional data."""
    label: str = ""
    score: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)
    activation: float | None = None
    similarity: float | None = None
    rrf_score: float | None = None
    activation_rank: int | None = None
    similarity_rank: int | None = None


@dataclass
class ActivationHit(_SimpleResultBase):
    """An activation-spreading hit with concept label and activation score."""
    label: str = ""
    energy: float = 0.0


@dataclass
class BulkResult(_SimpleResultBase):
    """Result of bulk node/edge construction via :meth:`add_all`."""
    nodes_added: int = 0
    edges_added: int = 0
    nodes_skipped: int = 0
    edges_skipped: int = 0


@dataclass
class AnomalyReport(_SimpleResultBase):
    """Structural anomaly detection report for a concept."""
    concept: str = ""
    status: str = "low_risk"
    score: float = 0.0
    indicators: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def top_k(scores: dict[str, float], k: int = 10) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda x: -x[1])[:k]


def to_dataframe(scores: dict[str, float]) -> Any:
    try:
        import pandas as pd
        return pd.DataFrame([{"label": k, "score": v} for k, v in scores.items()])
    except ImportError as exc:
        raise ImportError("pandas is required for to_dataframe(). Install with: pip install pandas") from exc
