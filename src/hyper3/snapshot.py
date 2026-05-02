from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hyper3.belief import (
    BeliefLayer,
    BeliefState,
    ConceptCorrelation,
    Outcome,
)
from hyper3.cache import LazyCache
from hyper3.feedback import OperationFeedback
from hyper3.kernel import Hypergraph
from hyper3.multi_perspective import MultiPerspectiveAnalyzer
from hyper3.multiway import MultiwayEngine, MultiwayState
from hyper3.multiway_branchial import (
    BranchialCluster,
    BranchialCoordinates,
    BranchialDistanceMetrics,
    BranchialSpace,
)
from hyper3.provenance import ProvenanceRecord, ProvenanceTracker
from hyper3.retrieval_engine import FeedbackRecord, RetrievalEngine
from hyper3.rule_analytics import (
    DetectedPattern,
    HighLevelInsight,
    RuleAnalytics,
    RuleSpacePosition,
)
from hyper3.rules import Rule
from hyper3.system_monitor import SystemHealthModel, SystemMonitor

SNAPSHOT_VERSION = 1


@dataclass
class SystemSnapshot:
    """Immutable cross-session snapshot of all subsystem state for save/restore operations."""

    version: int = SNAPSHOT_VERSION
    saved_at: float = 0.0

    belief_states: list[dict[str, Any]] = field(default_factory=list)
    belief_correlations: list[dict[str, Any]] = field(default_factory=list)
    belief_basis_stats: dict[str, dict[str, int]] = field(default_factory=dict)

    multiway_states: list[dict[str, Any]] = field(default_factory=list)
    multiway_root_id: str | None = None

    branchial_coordinates: list[dict[str, Any]] = field(default_factory=list)
    branchial_distance_cache: list[dict[str, Any]] = field(default_factory=list)
    branchial_clusters: list[dict[str, Any]] = field(default_factory=list)

    rule_analytics_position: dict[str, Any] = field(default_factory=dict)
    rule_analytics_position_history: list[dict[str, Any]] = field(default_factory=list)
    rule_analytics_rule_outcomes: dict[str, dict[str, int]] = field(default_factory=dict)
    rule_analytics_meta_patterns: list[dict[str, Any]] = field(default_factory=list)
    rule_analytics_insights: list[dict[str, Any]] = field(default_factory=list)
    rule_analytics_explored_rules: dict[str, int] = field(default_factory=dict)
    rule_analytics_total_applications: int = 0

    provenance_records: list[dict[str, Any]] = field(default_factory=list)
    provenance_dependents: dict[str, list[str]] = field(default_factory=dict)

    retrieval_feedback: list[dict[str, Any]] = field(default_factory=list)
    retrieval_ltr_weights: dict[str, float] = field(default_factory=dict)

    frame_outcomes: dict[str, dict[str, int]] = field(default_factory=dict)
    basis_stats: dict[str, dict[str, int]] = field(default_factory=dict)

    monitor_state: dict[str, Any] = field(default_factory=dict)
    meta_introspection_log: list[dict[str, Any]] = field(default_factory=list)
    meta_tuning_history: list[dict[str, Any]] = field(default_factory=list)

    cache_items: list[tuple[str, Any, float]] = field(default_factory=list)

    feedback_signals: list[dict[str, Any]] = field(default_factory=list)
    feedback_collapse_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    feedback_retrieval_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    feedback_inference_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    feedback_evolution_fitness: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot to a plain dict suitable for JSON encoding."""
        d: dict[str, Any] = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if f == "cache_items":
                d[f] = [[k, v, exp] for k, v, exp in val]
            else:
                d[f] = val
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemSnapshot:
        """Reconstruct a SystemSnapshot from a serialized dict."""
        legacy_map = {
            "quantum_states": "belief_states",
            "quantum_correlations": "belief_correlations",
            "quantum_basis_stats": "belief_basis_stats",
        }
        remapped = {}
        for k, v in data.items():
            remapped[legacy_map.get(k, k)] = v
        kwargs: dict[str, Any] = {}
        for f in cls.__dataclass_fields__:
            if f in remapped:
                val = remapped[f]
                if f == "cache_items":
                    val = [
                        (item[0], item[1], item[2])
                        for item in val
                        if isinstance(item, (list, tuple)) and len(item) >= 3
                    ]
                kwargs[f] = val
        return cls(**kwargs)


def _serialize_amplitude(amp: float | complex) -> Any:
    """Convert a possibly-complex amplitude to a JSON-safe value."""
    if isinstance(amp, complex):
        return [amp.real, amp.imag]
    return amp


def _deserialize_amplitude(data: Any) -> float | complex:
    """Reconstruct a float or complex amplitude from a serialized value."""
    if isinstance(data, list) and len(data) == 2:
        return complex(data[0], data[1])
    if isinstance(data, (int, float)):
        return float(data)
    return 0.0


def capture_snapshot(
    belief: BeliefLayer,
    multiway_engine: MultiwayEngine | None,
    branchial: BranchialSpace | None,
    rule_analytics: RuleAnalytics | None,
    provenance: ProvenanceTracker,
    retrieval: RetrievalEngine,
    perspective: MultiPerspectiveAnalyzer,
    meta: SystemMonitor,
    cache: LazyCache,
    feedback: OperationFeedback | None = None,
) -> SystemSnapshot:
    """Capture the full state of all subsystems into an immutable snapshot.

    Args:
        belief: Belief layer whose states and correlations to capture.
        multiway_engine: Optional multiway engine whose DAG to capture.
        branchial: Optional branchial space whose coordinates and clusters to capture.
        rule_analytics: Optional rule analytics engine whose position, history, and patterns to capture.
        provenance: Provenance tracker whose records to capture.
        retrieval: Retrieval engine whose feedback and LTR weights to capture.
        perspective: Computational perspective whose frame outcomes to capture.
        meta: System monitor whose state and history to capture.
        cache: LazyCache whose live items to capture.
        feedback: Optional operation feedback tracker whose signals and stats to capture.

    Returns:
        A :class:`SystemSnapshot` containing serialized copies of all subsystem state.
    """
    snap = SystemSnapshot(saved_at=time.time())
    _capture_belief(belief, snap)
    _capture_multiway(multiway_engine, snap)
    _capture_branchial(branchial, snap)
    _capture_rule_analytics(rule_analytics, snap)
    _capture_provenance(provenance, snap)
    _capture_retrieval(retrieval, snap)
    _capture_perspective(perspective, belief, snap)
    _capture_monitor(meta, snap)
    _capture_cache(cache, snap)
    _capture_feedback(feedback, snap)
    return snap


def _capture_belief(belief: BeliefLayer, snap: SystemSnapshot) -> None:
    for qs in belief._states.values():
        interps = [
            {
                "node_id": interp.node_id,
                "amplitude": _serialize_amplitude(interp.amplitude),
                "metadata": interp.metadata,
                "label": interp.label,
            }
            for interp in qs.outcomes
        ]
        snap.belief_states.append(
            {
                "id": qs.id,
                "outcomes": interps,
                "created_at": qs.created_at,
                "resolved": qs.resolved,
                "resolved_to": qs.resolved_to,
                "coherence_time": qs.coherence_time,
                "base_coherence_time": qs.base_coherence_time,
                "correlation_ids": qs.correlation_ids,
            }
        )

    for corr in belief._correlations.values():
        snap.belief_correlations.append(
            {
                "id": corr.id,
                "group_a_node_ids": sorted(corr.group_a_node_ids),
                "group_b_node_ids": sorted(corr.group_b_node_ids),
                "correlation_matrix": [[k[0], k[1], v] for k, v in corr.correlation_matrix.items()],
                "strength": corr.strength,
            }
        )

    snap.belief_basis_stats = dict(belief._basis_stats)


def _capture_multiway(multiway_engine: MultiwayEngine | None, snap: SystemSnapshot) -> None:
    if multiway_engine is None:
        return
    mw = multiway_engine.multiway
    root = mw.get_root()
    snap.multiway_root_id = root.id if root else None
    for state in mw.states:
        snap.multiway_states.append(
            {
                "id": state.id,
                "parent_id": state.parent_id,
                "active_node_ids": sorted(state.active_node_ids),
                "rule_applied": state.rule_applied,
                "match_bindings": state.match_bindings,
                "depth": state.depth,
                "produced_node_ids": state.produced_node_ids,
                "produced_edge_ids": state.produced_edge_ids,
                "children_ids": state.children_ids,
                "timestamp": state.timestamp,
            }
        )


def _capture_branchial(branchial: BranchialSpace | None, snap: SystemSnapshot) -> None:
    if branchial is None:
        return
    for sid, coords in branchial._coordinates.items():
        snap.branchial_coordinates.append(
            {
                "state_id": sid,
                "position": coords.position,
                "depth": coords.depth,
                "branch_index": coords.branch_index,
            }
        )
    for key, metrics in branchial._distance_cache.items():
        snap.branchial_distance_cache.append(
            {
                "key": list(key),
                "structural": metrics.structural,
                "conceptual": metrics.conceptual,
                "computational": metrics.computational,
                "evolutionary": metrics.evolutionary,
            }
        )
    for cluster in branchial._clusters:
        snap.branchial_clusters.append(
            {
                "id": cluster.id,
                "state_ids": sorted(cluster.state_ids),
                "label": cluster.label,
                "centroid_state_id": cluster.centroid.state_id if cluster.centroid else None,
                "centroid_position": cluster.centroid.position if cluster.centroid else [],
            }
        )


def _capture_rule_analytics(rule_analytics: RuleAnalytics | None, snap: SystemSnapshot) -> None:
    if rule_analytics is None:
        return
    pos = rule_analytics._position
    snap.rule_analytics_position = {
        "graph_activity_density": pos.graph_activity_density,
        "rule_application_frequency": pos.rule_application_frequency,
        "structural_complexity": pos.structural_complexity,
        "branchial_coordinates": pos.branchial_coordinates,
        "timestamp": pos.timestamp,
    }
    for hist_pos in rule_analytics._position_history:
        snap.rule_analytics_position_history.append(
            {
                "graph_activity_density": hist_pos.graph_activity_density,
                "rule_application_frequency": hist_pos.rule_application_frequency,
                "structural_complexity": hist_pos.structural_complexity,
                "branchial_coordinates": hist_pos.branchial_coordinates,
                "timestamp": hist_pos.timestamp,
            }
        )
    snap.rule_analytics_rule_outcomes = {k: dict(v) for k, v in rule_analytics._rule_outcomes.items()}
    for pat in rule_analytics._meta_patterns:
        snap.rule_analytics_meta_patterns.append(
            {
                "id": pat.id,
                "pattern_type": pat.pattern_type,
                "description": pat.description,
                "occurrence_count": pat.occurrence_count,
                "domains": sorted(pat.domains),
                "abstract_structure": pat.abstract_structure,
                "significance": pat.significance,
            }
        )
    for insight in rule_analytics._insights:
        snap.rule_analytics_insights.append(
            {
                "id": insight.id,
                "principle": insight.principle,
                "domain": insight.domain,
                "evidence": insight.evidence,
                "confidence": insight.confidence,
                "timestamp": insight.timestamp,
            }
        )
    snap.rule_analytics_explored_rules = dict(rule_analytics._explored_rules)
    snap.rule_analytics_total_applications = rule_analytics._total_applications


def _capture_provenance(provenance: ProvenanceTracker, snap: SystemSnapshot) -> None:
    for record in provenance._records.values():
        snap.provenance_records.append(
            {
                "edge_id": record.edge_id,
                "rule_name": record.rule_name,
                "input_edge_ids": record.input_edge_ids,
                "input_node_ids": record.input_node_ids,
                "depth": record.depth,
                "timestamp": record.timestamp,
                "metadata": record.metadata,
            }
        )
    for edge_id, dep_ids in provenance._edge_to_dependents.items():
        snap.provenance_dependents[edge_id] = sorted(dep_ids)


def _capture_retrieval(retrieval: RetrievalEngine, snap: SystemSnapshot) -> None:
    if hasattr(retrieval, "_feedback") and retrieval._feedback is not None:
        for rec in retrieval._feedback.records:
            snap.retrieval_feedback.append(
                {
                    "query": rec.query,
                    "node_id": rec.node_id,
                    "label": rec.label,
                    "relevant": rec.relevant,
                    "features": rec.features,
                }
            )
    if hasattr(retrieval, "_ltr") and retrieval._ltr is not None:
        snap.retrieval_ltr_weights = dict(retrieval._ltr.weights)


def _capture_perspective(perspective: MultiPerspectiveAnalyzer, belief: BeliefLayer, snap: SystemSnapshot) -> None:
    snap.frame_outcomes = {k: dict(v) for k, v in perspective._frame_outcomes.items()}
    snap.basis_stats = {k: dict(v) for k, v in belief._basis_stats.items()}


def _capture_monitor(meta: SystemMonitor, snap: SystemSnapshot) -> None:
    state = meta._state
    snap.monitor_state = {
        "architectural_fitness": state.architectural_fitness,
        "computational_efficiency": state.computational_efficiency,
        "rule_analytics_insight_count": state.rule_analytics_insight_count,
        "reasoning_activity_rate": state.reasoning_activity_rate,
        "reasoning_mode": state.reasoning_mode,
        "complexity_level": state.complexity_level,
        "timestamp": state.timestamp,
    }
    snap.meta_introspection_log = list(meta._introspection_log)
    for plan in meta._tuning_history:
        triggers = [
            {
                "trigger_type": t.trigger_type,
                "description": t.description,
                "urgency": t.urgency,
                "timestamp": t.timestamp,
            }
            for t in plan.triggers
        ]
        snap.meta_tuning_history.append(
            {
                "id": plan.id,
                "triggers": triggers,
                "actions": plan.actions,
                "expected_improvement": plan.expected_improvement,
                "risk_level": plan.risk_level,
            }
        )


def _capture_cache(cache: LazyCache, snap: SystemSnapshot) -> None:
    now = time.time()
    for key, (cached_at, value) in cache._cache.items():
        remaining_ttl = cache._ttl - (now - cached_at)
        if remaining_ttl > 0:
            snap.cache_items.append((key, value, remaining_ttl))


def _capture_feedback(feedback: OperationFeedback | None, snap: SystemSnapshot) -> None:
    if feedback is None:
        return
    for signal in feedback._signals:
        snap.feedback_signals.append(
            {
                "signal_type": signal.signal_type,
                "node_id": signal.node_id,
                "outcome": signal.outcome,
                "confidence": signal.confidence,
                "context": signal.context,
                "timestamp": signal.timestamp,
            }
        )
    snap.feedback_collapse_stats = {k: dict(v) for k, v in feedback._collapse_stats.items()}
    snap.feedback_retrieval_stats = {k: dict(v) for k, v in feedback._retrieval_stats.items()}
    snap.feedback_inference_stats = {k: dict(v) for k, v in feedback._inference_stats.items()}
    snap.feedback_evolution_fitness = list(feedback._evolution_fitness_history)


def restore_snapshot(
    snapshot: SystemSnapshot,
    graph: Hypergraph,
    belief: BeliefLayer,
    provenance: ProvenanceTracker,
    retrieval: RetrievalEngine,
    perspective: MultiPerspectiveAnalyzer,
    meta: SystemMonitor,
    cache: LazyCache,
    rules: list[Rule],
    feedback: OperationFeedback | None = None,
) -> tuple[
    MultiwayEngine | None,
    BranchialSpace | None,
    RuleAnalytics | None,
]:
    """Rebuild all subsystems from a previously captured snapshot.

    Clears and repopulates belief states/correlations, multiway DAG,
    branchial coordinates, rule_analytics position/history, provenance records,
    retrieval feedback/LTR weights, perspective frame outcomes, and
    system monitor state.

    Cache items are restored with their **original remaining TTL** by
    backdating the insertion timestamp: ``insert_time = now - (ttl -
    remaining_ttl)``.  This ensures items expire at the correct wall-clock
    time relative to the snapshot's capture moment rather than receiving a
    full fresh TTL.

    Args:
        snapshot: The snapshot to restore from.
        graph: Live hypergraph (unchanged — graph structure must be
            restored separately).
        belief: Belief layer to repopulate.
        provenance: Provenance tracker to repopulate.
        retrieval: Retrieval engine whose feedback/LTR state to restore.
        perspective: Computational perspective whose frame outcomes to
            restore.
        meta: System monitor whose state to restore.
        cache: LazyCache whose items to restore with correct TTL.
        rules: Current rule list (not modified).
        feedback: Optional operation feedback tracker to restore.

    Returns:
        Tuple of ``(multiway_engine, branchial, rule_analytics)`` — each may be
        ``None`` if the snapshot contained no data for that subsystem.
    """
    belief._states.clear()
    belief._correlations.clear()
    belief._basis_stats.clear()

    _restore_belief(snapshot, belief)
    multiway_engine = _restore_multiway(snapshot, graph)
    branchial = _restore_branchial(snapshot, graph, multiway_engine)
    rule_analytics = _restore_rule_analytics(snapshot, graph, multiway_engine)
    _restore_provenance(snapshot, provenance)
    _restore_retrieval(snapshot, retrieval)
    _restore_perspective(snapshot, perspective)
    _restore_monitor(snapshot, meta)
    _restore_cache(snapshot, cache)
    _restore_feedback(snapshot, feedback)

    return multiway_engine, branchial, rule_analytics


def _restore_belief(snapshot: SystemSnapshot, belief: BeliefLayer) -> None:
    for state_data in snapshot.belief_states:
        interps = [
            Outcome(
                node_id=idata["node_id"],
                amplitude=_deserialize_amplitude(idata["amplitude"]),
                metadata=idata.get("metadata", {}),
                label=idata.get("label", ""),
            )
            for idata in state_data.get("outcomes", state_data.get("interpretations", []))
        ]
        qs = BeliefState(
            id=state_data["id"],
            outcomes=interps,
            created_at=state_data.get("created_at", 0.0),
            resolved=state_data.get("resolved", state_data.get("collapsed", False)),
            resolved_to=state_data.get("resolved_to", state_data.get("collapsed_to")),
            coherence_time=state_data.get("coherence_time", 30.0),
            base_coherence_time=state_data.get("base_coherence_time", 30.0),
            correlation_ids=state_data.get("correlation_ids", []),
        )
        belief._states[qs.id] = qs

    for ent_data in snapshot.belief_correlations:
        corr_matrix = {}
        for item in ent_data.get("correlation_matrix", []):
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                corr_matrix[(item[0], item[1])] = item[2]
        corr = ConceptCorrelation(
            id=ent_data["id"],
            group_a_node_ids=frozenset(ent_data.get("group_a_node_ids", [])),
            group_b_node_ids=frozenset(ent_data.get("group_b_node_ids", [])),
            correlation_matrix=corr_matrix,
            strength=ent_data.get("strength", 0.0),
        )
        belief._correlations[corr.id] = corr

    belief._basis_stats.update(snapshot.belief_basis_stats)


def _restore_multiway(snapshot: SystemSnapshot, graph: Hypergraph) -> MultiwayEngine | None:
    if not snapshot.multiway_states:
        return None
    me = MultiwayEngine(graph)
    for state_data in snapshot.multiway_states:
        ms = MultiwayState(
            id=state_data["id"],
            parent_id=state_data.get("parent_id"),
            active_node_ids=frozenset(state_data.get("active_node_ids", [])),
            rule_applied=state_data.get("rule_applied"),
            match_bindings=state_data.get("match_bindings", {}),
            depth=state_data.get("depth", 0),
            produced_node_ids=state_data.get("produced_node_ids", []),
            produced_edge_ids=state_data.get("produced_edge_ids", []),
            children_ids=state_data.get("children_ids", []),
            timestamp=state_data.get("timestamp", 0.0),
        )
        me.multiway._states[ms.id] = ms
    root = me.multiway.get_state(snapshot.multiway_root_id) if snapshot.multiway_root_id else None
    if root:
        me.multiway._root = root
    me.multiway._leaves_cache = None
    return me


def _restore_branchial(snapshot: SystemSnapshot, graph: Hypergraph, multiway_engine: MultiwayEngine | None) -> BranchialSpace | None:
    if not snapshot.branchial_coordinates or multiway_engine is None:
        return None
    bs = BranchialSpace(graph, multiway_engine.multiway)
    for coord_data in snapshot.branchial_coordinates:
        bs._coordinates[coord_data["state_id"]] = BranchialCoordinates(
            state_id=coord_data["state_id"],
            position=coord_data.get("position", []),
            depth=coord_data.get("depth", 0),
            branch_index=coord_data.get("branch_index", 0),
        )
    for dist_data in snapshot.branchial_distance_cache:
        key = tuple(dist_data["key"])
        bs._distance_cache[key] = BranchialDistanceMetrics(
            structural=dist_data.get("structural", 0.0),
            conceptual=dist_data.get("conceptual", 0.0),
            computational=dist_data.get("computational", 0.0),
            evolutionary=dist_data.get("evolutionary", 0.0),
        )
    for cl_data in snapshot.branchial_clusters:
        centroid = None
        if cl_data.get("centroid_state_id"):
            centroid = BranchialCoordinates(
                state_id=cl_data["centroid_state_id"],
                position=cl_data.get("centroid_position", []),
            )
        bc = BranchialCluster(
            id=cl_data["id"],
            state_ids=set(cl_data.get("state_ids", [])),
            centroid=centroid,
            label=cl_data.get("label", ""),
        )
        bs._clusters.append(bc)
    return bs


def _restore_rule_analytics(snapshot: SystemSnapshot, graph: Hypergraph, multiway_engine: MultiwayEngine | None) -> RuleAnalytics | None:
    if not snapshot.rule_analytics_position:
        return None
    rs = RuleAnalytics(graph, multiway_engine)
    pos_data = snapshot.rule_analytics_position
    rs._position = RuleSpacePosition(
        graph_activity_density=pos_data.get("graph_activity_density", 0.0),
        rule_application_frequency=pos_data.get("rule_application_frequency", {}),
        structural_complexity=pos_data.get("structural_complexity", 0.0),
        branchial_coordinates=pos_data.get("branchial_coordinates", []),
        timestamp=pos_data.get("timestamp", 0.0),
    )
    for hist_data in snapshot.rule_analytics_position_history:
        rs._position_history.append(
            RuleSpacePosition(
                graph_activity_density=hist_data.get("graph_activity_density", 0.0),
                rule_application_frequency=hist_data.get("rule_application_frequency", {}),
                structural_complexity=hist_data.get("structural_complexity", 0.0),
                branchial_coordinates=hist_data.get("branchial_coordinates", []),
                timestamp=hist_data.get("timestamp", 0.0),
            )
        )
    rs._rule_outcomes = {k: dict(v) for k, v in snapshot.rule_analytics_rule_outcomes.items()}
    for pat_data in snapshot.rule_analytics_meta_patterns:
        rs._meta_patterns.append(
            DetectedPattern(
                id=pat_data["id"],
                pattern_type=pat_data.get("pattern_type", ""),
                description=pat_data.get("description", ""),
                occurrence_count=pat_data.get("occurrence_count", 0),
                domains=set(pat_data.get("domains", [])),
                abstract_structure=pat_data.get("abstract_structure", {}),
                significance=pat_data.get("significance", 0.0),
            )
        )
    for ins_data in snapshot.rule_analytics_insights:
        rs._insights.append(
            HighLevelInsight(
                id=ins_data["id"],
                principle=ins_data.get("principle", ""),
                domain=ins_data.get("domain", "meta"),
                evidence=ins_data.get("evidence", []),
                confidence=ins_data.get("confidence", 0.0),
                timestamp=ins_data.get("timestamp", 0.0),
            )
        )
    rs._explored_rules = dict(snapshot.rule_analytics_explored_rules)
    rs._total_applications = snapshot.rule_analytics_total_applications
    return rs


def _restore_provenance(snapshot: SystemSnapshot, provenance: ProvenanceTracker) -> None:
    provenance._records.clear()
    provenance._edge_to_dependents.clear()
    for rec_data in snapshot.provenance_records:
        record = ProvenanceRecord(
            edge_id=rec_data["edge_id"],
            rule_name=rec_data.get("rule_name", ""),
            input_edge_ids=rec_data.get("input_edge_ids", []),
            input_node_ids=rec_data.get("input_node_ids", []),
            depth=rec_data.get("depth", 0),
            timestamp=rec_data.get("timestamp", 0.0),
            metadata=rec_data.get("metadata", {}),
        )
        provenance._records[record.edge_id] = record
    for edge_id, dep_ids in snapshot.provenance_dependents.items():
        provenance._edge_to_dependents[edge_id] = set(dep_ids)


def _restore_retrieval(snapshot: SystemSnapshot, retrieval: RetrievalEngine) -> None:
    if hasattr(retrieval, "_feedback") and retrieval._feedback is not None:
        retrieval._feedback._records.clear()
        for fb_data in snapshot.retrieval_feedback:
            retrieval._feedback._records.append(
                FeedbackRecord(
                    query=fb_data["query"],
                    node_id=fb_data["node_id"],
                    label=fb_data["label"],
                    relevant=fb_data["relevant"],
                    features=fb_data.get("features", {}),
                )
            )
    if hasattr(retrieval, "_ltr") and retrieval._ltr is not None:
        for k, v in snapshot.retrieval_ltr_weights.items():
            retrieval._ltr._weights[k] = v


def _restore_perspective(snapshot: SystemSnapshot, perspective: MultiPerspectiveAnalyzer) -> None:
    perspective._frame_outcomes = {k: dict(v) for k, v in snapshot.frame_outcomes.items()}


def _restore_monitor(snapshot: SystemSnapshot, meta: SystemMonitor) -> None:
    meta_state = snapshot.monitor_state
    meta._state = SystemHealthModel(
        architectural_fitness=meta_state.get("architectural_fitness", 1.0),
        computational_efficiency=meta_state.get("computational_efficiency", {}),
        rule_analytics_insight_count=meta_state.get("rule_analytics_insight_count", 0),
        reasoning_activity_rate=meta_state.get("reasoning_activity_rate", 0.0),
        reasoning_mode=meta_state.get("reasoning_mode", "standard"),
        complexity_level=meta_state.get("complexity_level", 0),
        timestamp=meta_state.get("timestamp", 0.0),
    )
    meta._introspection_log = list(snapshot.meta_introspection_log)


def _restore_cache(snapshot: SystemSnapshot, cache: LazyCache) -> None:
    cache.clear()
    now = time.time()
    for key, value, remaining_ttl in snapshot.cache_items:
        insert_time = now - (cache._ttl - remaining_ttl)
        cache._cache[key] = (insert_time, value)


def _restore_feedback(snapshot: SystemSnapshot, feedback: OperationFeedback | None) -> None:
    if feedback is None:
        return
    from hyper3.feedback import FeedbackSignal

    feedback._signals.clear()
    for sig_data in snapshot.feedback_signals:
        feedback._signals.append(
            FeedbackSignal(
                signal_type=sig_data["signal_type"],
                node_id=sig_data["node_id"],
                outcome=sig_data["outcome"],
                confidence=sig_data.get("confidence", 0.0),
                context=sig_data.get("context", {}),
                timestamp=sig_data.get("timestamp", 0.0),
            )
        )
    feedback._collapse_stats = {k: dict(v) for k, v in snapshot.feedback_collapse_stats.items()}
    feedback._retrieval_stats = {k: dict(v) for k, v in snapshot.feedback_retrieval_stats.items()}
    feedback._inference_stats = {k: dict(v) for k, v in snapshot.feedback_inference_stats.items()}
    feedback._evolution_fitness_history = list(snapshot.feedback_evolution_fitness)


def save_state(
    path: str | Path,
    snapshot: SystemSnapshot,
) -> None:
    """Write a snapshot to a JSON file on disk.

    Args:
        path: Destination file path. Parent directories are created automatically.
        snapshot: The snapshot to persist.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snapshot.to_dict(), indent=2, default=_json_default))


def load_state(path: str | Path) -> SystemSnapshot:
    """Load a snapshot from a JSON file on disk.

    Args:
        path: Path to the JSON file produced by :func:`save_state`.

    Returns:
        A reconstructed :class:`SystemSnapshot`.
    """
    p = Path(path)
    data = json.loads(p.read_text())
    return SystemSnapshot.from_dict(data)


def _json_default(obj: Any) -> Any:
    """Fallback serializer for types that ``json.dumps`` cannot handle natively."""
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    if isinstance(obj, tuple):
        return list(obj)
    return str(obj)
