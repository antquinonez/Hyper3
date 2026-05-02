from __future__ import annotations

from typing import Any

from hyper3.abstraction import AbstractionNavigator
from hyper3.backward_chain import BackwardChainEngine
from hyper3.belief import BeliefLayer
from hyper3.belief_revision import ContradictionResolver
from hyper3.cache import LazyCache
from hyper3.community import CommunityDetector
from hyper3.constraints import BoundaryNavigator
from hyper3.embedding import EmbeddingEngine
from hyper3.enrichment import LLMEnricher
from hyper3.equivalence import EquivalenceEngine
from hyper3.event_log import EventLog
from hyper3.evolution import GraphMaintenanceEngine
from hyper3.feedback import OperationFeedback
from hyper3.graph_diff import GraphDiffer
from hyper3.hebbian import HebbianLearner
from hyper3.kernel import Hypergraph, Hypernode
from hyper3.multi_perspective import MultiPerspectiveAnalyzer
from hyper3.multiway import MultiwayEngine
from hyper3.multiway_causal import StateConvergenceEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.persistence import Serializer
from hyper3.provenance import ProvenanceTracker
from hyper3.results import (
    CommitResult,
    ConsensusReasonResult,
    DiscoverResult,
    EvolveResult,
    IterativeReasonResult,
    MemoryStats,
    ReasonResult,
    RollbackResult,
    TrainResult,
)
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.retrieval_engine import RetrievalEngine
from hyper3.rule_analytics import RuleAnalytics
from hyper3.rules import Rule
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.state_clustering import StateClusteringEngine
from hyper3.structural_anomaly import StructuralAnomalyDetector
from hyper3.structural_match import StructuralPatternEngine
from hyper3.system_monitor import SystemMonitor
from hyper3.temporal import TemporalReasoner
from hyper3.traversal import ObserverSlice, TraversalEngine
from hyper3.uncertainty import UncertaintyEngine


class _MemoryBase:
    """Shared type annotations for all HypergraphMemory mixins."""

    _graph: Hypergraph
    _log: EventLog
    _cache: LazyCache
    _traversal: TraversalEngine
    _observer: ObserverSlice
    _evolution: GraphMaintenanceEngine
    _equivalence: EquivalenceEngine
    _decay_factor: float
    _evolve_interval: int
    _merge_threshold: float
    _decay_threshold: float
    _operation_count: int
    _multiway_engine: MultiwayEngine | None
    _convergence_engine: StateConvergenceEngine | None
    _belief: BeliefLayer
    _rules: list[Rule]
    _discovery: RuleDiscoveryEngine
    _serializer: Serializer
    _state_clustering: StateClusteringEngine | None
    _rule_analytics: RuleAnalytics | None
    _anomaly_detector: StructuralAnomalyDetector
    _perspective: MultiPerspectiveAnalyzer
    _meta: SystemMonitor
    _embedding_engine: EmbeddingEngine | None
    _activation: SpreadingActivation
    _retrieval: RetrievalEngine
    _temporal: TemporalReasoner
    _provenance: ProvenanceTracker
    _enricher: LLMEnricher
    _overlay: HypergraphOverlay | None
    _feedback: OperationFeedback
    _boundary_navigator: BoundaryNavigator | None
    _backward_chain: BackwardChainEngine | None
    _hebbian: HebbianLearner | None
    _uncertainty_engine: UncertaintyEngine | None
    _structural_matcher: StructuralPatternEngine | None
    _belief_revision: ContradictionResolver | None
    _abstraction_nav: AbstractionNavigator | None
    _community_detector: CommunityDetector | None
    _graph_differ: GraphDiffer | None

    def _find_node(self, label: str) -> Hypernode | None:
        """Look up a node by label, checking cache, label index, and aliases."""
        ...

    def _node_label(self, node_id: str) -> str:
        """Return the human-readable label for a node ID, or a truncated ID fallback."""
        ...

    def _maybe_evolve(self) -> None:
        """Increment the operation counter and trigger evolution if the interval is reached."""
        ...

    def store(self, concept: str, data: Any = None, **kwargs: Any) -> Hypernode:
        """Store a concept node in the hypergraph."""
        ...

    def relate(self, source: str, target: str, **kwargs: Any) -> Any:
        """Create a directed edge between two concept nodes.

        Raises NodeNotFoundError or ConstraintViolationError on failure.
        """
        ...

    def commit_inferences(self) -> CommitResult:
        """Merge the current inference overlay into the base graph."""
        ...

    def reason(self, seed_concepts: set[str], rules: list[Rule] | None = None, **kwargs: Any) -> ReasonResult:
        """Expand the multiway DAG from seed concepts using inference rules."""
        ...

    def reason_iterative(
        self, seed_concepts: set[str], rules: list[Rule] | None = None, **kwargs: Any
    ) -> IterativeReasonResult:
        """Run multiple reasoning iterations until confidence or convergence is reached."""
        ...

    def reason_with_frame(
        self, seed_concepts: set[str], frame_name: str = "classical", rules: list[Rule] | None = None
    ) -> ReasonResult:
        """Run reasoning with parameters derived from a computational frame."""
        ...

    def reason_robust(self, seed_concepts: set[str], rules: list[Rule] | None = None) -> ConsensusReasonResult:
        """Find multi-frame invariants then reason, returning consensus results."""
        ...

    def reason_incremental(
        self, new_node_labels: set[str], rules: list[Rule] | None = None, **kwargs: Any
    ) -> ReasonResult:
        """Expand the existing multiway DAG from newly added nodes."""
        ...

    def evolve(self) -> EvolveResult:
        """Run a manual evolution cycle (decay, prune, merge, reinforce)."""
        ...

    def stats(self) -> MemoryStats:
        """Return a typed summary of graph, cache, quantum, evolution, and subsystem metrics."""
        ...

    def auto_discover_and_apply(self) -> DiscoverResult:
        """Discover graph patterns and add the resulting rules to the active set."""
        ...

    def train_retriever(self) -> TrainResult:
        """Train the learning-to-rank model from accumulated feedback."""
        ...

    def rollback_inferences(self) -> RollbackResult:
        """Discard the current inference overlay and retract provenance entries."""
        ...
