from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.event_log import EventLog
from hyper3.equivalence import EquivalenceEngine
from hyper3.cache import LazyCache
from hyper3.traversal import ObserverSlice, TraversalEngine
from hyper3.evolution import SelfEvolutionEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.multiway_causal import CausalInvarianceEngine
from hyper3.quantum import QuantumCognitiveLayer
from hyper3.multiway import ExpansionReport, MultiwayEngine
from hyper3.rules import Rule
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.persistence import Serializer
from hyper3.multiway_branchial import BranchialSpace
from hyper3.multiway_rulial import RulialSpace
from hyper3.structural_anomaly import StructuralAnomalyDetector
from hyper3.multi_perspective import MultiPerspectiveAnalyzer
from hyper3.meta_cognitive import MetaCognitiveLayer
from hyper3.embedding import EmbeddingEngine
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.retrieval_engine import RetrievalEngine
from hyper3.temporal import TemporalReasoner
from hyper3.provenance import ProvenanceTracker
from hyper3.enrichment import LLMEnricher
from hyper3.feedback import OperationFeedback
from hyper3.constraints import BoundaryNavigator
from hyper3.backward_chain import BackwardChainEngine
from hyper3.hebbian import HebbianLearner
from hyper3.uncertainty import UncertaintyEngine
from hyper3.structural_match import StructuralPatternEngine
from hyper3.belief_revision import BeliefRevisionEngine
from hyper3.abstraction import AbstractionNavigator
from hyper3.community import CommunityDetector
from hyper3.graph_diff import GraphDiffer
from hyper3.memory_core import CoreMixin
from hyper3.memory_reasoning import ReasoningMixin
from hyper3.memory_quantum import QuantumMixin
from hyper3.memory_analytics import AnalyticsMixin
from hyper3.memory_persistence import PersistenceMixin
from hyper3.memory_subsystems import SubsystemMixin


class CognitiveMemory(
    CoreMixin,
    ReasoningMixin,
    QuantumMixin,
    AnalyticsMixin,
    PersistenceMixin,
    SubsystemMixin,
):
    def __init__(
        self,
        *,
        cache_max_size: int = 2048,
        cache_ttl: float = 600.0,
        merge_threshold: float = 0.8,
        decay_factor: float = 0.95,
        decay_threshold: float = 0.1,
        evolve_interval: int = 10,
    ) -> None:
        """Initialize the cognitive memory with all subsystems.

        Args:
            cache_max_size: Maximum number of entries in the LRU cache.
            cache_ttl: Time-to-live in seconds for cache entries.
            merge_threshold: Similarity threshold for node merging and equivalence detection.
            decay_factor: Multiplier applied to node weights during evolution decay.
            decay_threshold: Nodes below this weight are pruned during evolution.
            evolve_interval: Number of operations between automatic evolution cycles.
                Set to 0 to disable auto-evolution.
        """
        self._graph = Hypergraph()
        self._log = EventLog()
        self._cache = LazyCache(max_size=cache_max_size, ttl=cache_ttl)
        self._traversal = TraversalEngine(self._graph)
        self._observer = ObserverSlice(self._graph)
        self._evolution = SelfEvolutionEngine(
            self._graph,
            decay_threshold=decay_threshold,
            merge_threshold=merge_threshold,
        )
        self._equivalence = EquivalenceEngine(self._graph, threshold=merge_threshold)
        self._decay_factor = decay_factor
        self._evolve_interval = evolve_interval
        self._merge_threshold = merge_threshold
        self._decay_threshold = decay_threshold
        self._operation_count = 0
        self._multiway_engine: MultiwayEngine | None = None
        self._causal_engine: CausalInvarianceEngine | None = None
        self._quantum = QuantumCognitiveLayer(self._graph)
        self._rules: list[Rule] = []
        self._discovery = RuleDiscoveryEngine(self._graph)
        self._serializer = Serializer()
        self._branchial: BranchialSpace | None = None
        self._rulial: RulialSpace | None = None
        self._anomaly_detector = StructuralAnomalyDetector(self._graph)
        self._perspective = MultiPerspectiveAnalyzer(self._graph)
        self._meta = MetaCognitiveLayer(
            self._graph, self._evolution, self._log, self._discovery,
        )
        self._embedding_engine: EmbeddingEngine | None = None
        self._activation = SpreadingActivation(self._graph)
        self._retrieval = RetrievalEngine(self._graph, activation=self._activation)
        self._temporal = TemporalReasoner(self._graph)
        self._provenance = ProvenanceTracker()
        self._enricher = LLMEnricher()
        self._overlay: HypergraphOverlay | None = None
        self._feedback = OperationFeedback(self._graph)
        self._boundary_navigator: BoundaryNavigator | None = None
        self._backward_chain: BackwardChainEngine | None = None
        self._hebbian: HebbianLearner | None = None
        self._uncertainty_engine: UncertaintyEngine | None = None
        self._structural_matcher: StructuralPatternEngine | None = None
        self._belief_revision: BeliefRevisionEngine | None = None
        self._abstraction_nav: AbstractionNavigator | None = None
        self._community_detector: CommunityDetector | None = None
        self._graph_differ: GraphDiffer | None = None
