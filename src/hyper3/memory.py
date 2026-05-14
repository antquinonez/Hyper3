from __future__ import annotations

from typing import Any

from hyper3.abstraction import AbstractionNavigator
from hyper3.adaptive_slice import AdaptiveSliceEngine
from hyper3.backward_chain import BackwardChainEngine
from hyper3.basis_selector import BasisSelector
from hyper3.belief import BeliefLayer
from hyper3.belief_revision import ContradictionResolver
from hyper3.boundary_reasoning import BoundaryReasoningEngine
from hyper3.cache import LazyCache
from hyper3.collapse_trigger import CollapseTriggerEngine
from hyper3.community import CommunityDetector
from hyper3.constraints import BoundaryNavigator
from hyper3.embedding import EmbeddingEngine
from hyper3.embedding_graph import SemanticEdgeBuilder
from hyper3.enrichment import LLMEnricher
from hyper3.equivalence import EquivalenceEngine
from hyper3.event_log import EventLog
from hyper3.evolution import GraphMaintenanceEngine
from hyper3.feedback import OperationFeedback
from hyper3.graph_diff import GraphDiffer
from hyper3.hebbian import HebbianLearner
from hyper3.interference_reasoning import InterferenceReasoningEngine
from hyper3.invariant_detector import InvariantDetector
from hyper3.kernel import Hypergraph
from hyper3.layered_graph import LayerStack
from hyper3.memory_analytics import AnalyticsMixin
from hyper3.memory_bayesian import BayesianMixin
from hyper3.memory_belief import BeliefMixin
from hyper3.memory_cognitive import CognitiveMixin
from hyper3.memory_core import CoreMixin
from hyper3.memory_monitoring import MonitoringMixin
from hyper3.memory_persistence import PersistenceMixin
from hyper3.memory_provenance import ProvenanceMixin
from hyper3.memory_reasoning import ReasoningMixin
from hyper3.memory_retrieval import RetrievalMixin
from hyper3.memory_structural import StructuralMixin
from hyper3.memory_temporal import TemporalMixin
from hyper3.multi_perspective import MultiPerspectiveAnalyzer
from hyper3.multiway import MultiwayEngine
from hyper3.multiway_causal import StateConvergenceEngine
from hyper3.namespaces import (
    AnalyzeNamespace,
    BayesNamespace,
    BeliefNamespace,
    CognitiveNamespace,
    EngineAccessor,
    MonitorNamespace,
    ReasonNamespace,
    SearchNamespace,
    TemporalNamespace,
)
from hyper3.overlay import HypergraphOverlay
from hyper3.persistence import Serializer
from hyper3.provenance import ProvenanceTracker
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.retrieval_engine import RetrievalEngine
from hyper3.rule_analytics import RuleAnalytics
from hyper3.rules import Rule
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.search_engine import SearchEngine
from hyper3.state_clustering import StateClusteringEngine
from hyper3.structural_anomaly import StructuralAnomalyDetector
from hyper3.structural_match import StructuralPatternEngine
from hyper3.structural_prefetch import StructuralPrefetchEngine
from hyper3.system_monitor import SystemMonitor
from hyper3.temporal import TemporalReasoner
from hyper3.transcendental import TranscendentalInferenceEngine
from hyper3.traversal import ObserverSlice, TraversalEngine
from hyper3.uncertainty import UncertaintyEngine


class HypergraphMemory(
    CoreMixin,
    ReasoningMixin,
    BeliefMixin,
    BayesianMixin,
    AnalyticsMixin,
    PersistenceMixin,
    RetrievalMixin,
    TemporalMixin,
    ProvenanceMixin,
    CognitiveMixin,
    StructuralMixin,
    MonitoringMixin,
):
    """Unified facade for the Hyper3 self-evolving hypergraph knowledge graph.

    Composes from twelve focused mixins, each providing a coherent domain of
    functionality:

    - **CoreMixin**: store, recall, relate, query, evolve, ensure, node lookup
    - **ReasoningMixin**: multiway expansion, iterative/incremental reasoning,
      overlay commit/rollback, rule management, bias profiling
    - **BeliefMixin**: Born-rule distributions, sampling, correlations,
      lateral insights, structural anomaly detection
    - **BayesianMixin**: prior setting, belief updating, MAP estimates,
      Bayes factors, credible sets
    - **AnalyticsMixin**: paths, centrality, cycles, components, pattern
      matching, spectral embedding, hypergraph algorithms
    - **PersistenceMixin**: save/load, JSON/edgelist import/export,
      snapshots, stats
    - **RetrievalMixin**: spreading activation, semantic similarity,
      embedding providers, FAISS, learning-to-rank, prefetch
    - **TemporalMixin**: Allen interval algebra, causal chains, text
      ingestion, LLM enrichment
    - **ProvenanceMixin**: inference explanation, retraction, overlay access
    - **CognitiveMixin**: backward chaining, Hebbian learning, uncertainty
      quantification, confidence propagation
    - **StructuralMixin**: structural pattern matching, community detection,
      belief revision, abstraction collapse/expand, graph diff
    - **MonitoringMixin**: introspection, metamorphosis, multi-frame analysis,
      reasoning validation, capability detection
    """

    _PUBLIC_API = frozenset({
        "add", "link", "link_hyper", "add_all", "ensure", "find",
        "get", "set", "has", "info", "size",
        "centrality", "paths", "communities", "anomalies",
        "similar", "edges",
        "describe", "prove", "introspect", "activate",
        "evolve",
        "save", "load",
        "export_json", "import_json", "export_edgelist", "import_edgelist",
        "load_records",
        "ingest", "ingest_batch", "set_llm_provider",
        "neighbors", "query_nodes", "query_hyperedges",
        "node_label", "node_data", "resolve_id",
        "add_rules", "spread_hyperedge",
        "explain", "retract_inference",
        "reason", "belief", "bayes", "search", "analyze",
        "temporal", "monitor", "cognitive", "engine",
        "graph", "log", "cache", "rules",
        "recall_adaptive", "record_slice_outcome",
        "should_collapse", "collapse_report", "detect_invariants",
    })

    def __dir__(self) -> list[str]:
        """Return sorted list of public API attribute names."""
        return sorted(self._PUBLIC_API)

    def __contains__(self, concept: object) -> bool:
        """Check whether a concept label exists in the graph (``"x" in mem``)."""
        if not isinstance(concept, str):
            return False
        return self.has(concept)

    def __init__(
        self,
        *,
        rules: list[Rule] | None = None,
        cache_max_size: int = 2048,
        cache_ttl: float = 600.0,
        merge_threshold: float = 0.8,
        decay_factor: float = 0.95,
        decay_threshold: float = 0.1,
        evolve_interval: int = 0,
    ) -> None:
        """Initialize the hypergraph memory with all subsystems.

        Args:
            rules: Initial inference rules for reasoning. Can also be added
                later via :meth:`add_rules`.
            cache_max_size: Maximum number of entries in the LRU cache.
            cache_ttl: Time-to-live in seconds for cache entries.
            merge_threshold: Similarity threshold for node merging and equivalence detection.
            decay_factor: Multiplier applied to node weights during evolution decay.
            decay_threshold: Nodes below this weight are pruned during evolution.
            evolve_interval: Number of operations between automatic evolution cycles.
                Set to a positive value to enable auto-evolution. Default is 0
                (disabled) for deterministic behavior. Production usage should
                set a positive interval (e.g. 10 or 50).
        """
        self._graph = Hypergraph()
        self._log = EventLog()
        self._cache = LazyCache(max_size=cache_max_size, ttl=cache_ttl)
        self._traversal = TraversalEngine(self._graph)
        self._observer = ObserverSlice(self._graph)
        self._evolution = GraphMaintenanceEngine(
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
        self._convergence_engine: StateConvergenceEngine | None = None
        self._belief = BeliefLayer(self._graph)
        self._rules: list[Rule] = list(rules) if rules else []
        self._discovery = RuleDiscoveryEngine(self._graph)
        self._serializer = Serializer()
        self._state_clustering: StateClusteringEngine | None = None
        self._rule_analytics: RuleAnalytics | None = None
        self._anomaly_detector = StructuralAnomalyDetector(self._graph)
        self._perspective = MultiPerspectiveAnalyzer(self._graph)
        self._meta = SystemMonitor(
            self._graph,
            self._evolution,
            self._log,
            self._discovery,
        )
        self._embedding_engine: EmbeddingEngine | None = None
        self._activation = SpreadingActivation(self._graph)
        self._retrieval = RetrievalEngine(self._graph, activation=self._activation)
        self._semantic_builder: SemanticEdgeBuilder | None = None
        self._stack: LayerStack = LayerStack(self._graph)
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
        self._belief_revision: ContradictionResolver | None = None
        self._abstraction_nav: AbstractionNavigator | None = None
        self._community_detector: CommunityDetector | None = None
        self._graph_differ: GraphDiffer | None = None
        self._basis_selector: BasisSelector | None = None
        self._boundary_reasoning: BoundaryReasoningEngine | None = None
        self._transcendental: TranscendentalInferenceEngine | None = None
        self._adaptive_slice: AdaptiveSliceEngine | None = None
        self._interference_engine: InterferenceReasoningEngine | None = None
        self._collapse_trigger: CollapseTriggerEngine | None = None
        self._invariant_detector: InvariantDetector | None = None
        self._prefetch: StructuralPrefetchEngine | None = None
        self._ns_reason: ReasonNamespace | None = None
        self._ns_belief: BeliefNamespace | None = None
        self._ns_bayes: BayesNamespace | None = None
        self._ns_search: SearchNamespace | None = None
        self._ns_analyze: AnalyzeNamespace | None = None
        self._ns_temporal: TemporalNamespace | None = None
        self._ns_monitor: MonitorNamespace | None = None
        self._ns_cognitive: CognitiveNamespace | None = None
        self._ns_engine: EngineAccessor | None = None
        self._search_engine: SearchEngine | None = None

    @property
    def reason(self) -> ReasonNamespace:
        """Lazy-initialized property returning the reasoning namespace."""
        if self._ns_reason is None:
            self._ns_reason = ReasonNamespace(self)
        return self._ns_reason

    @property
    def belief(self) -> BeliefNamespace:
        """Lazy-initialized property returning the belief namespace."""
        if self._ns_belief is None:
            self._ns_belief = BeliefNamespace(self)
        return self._ns_belief

    @property
    def bayes(self) -> BayesNamespace:
        """Lazy-initialized property returning the Bayesian namespace."""
        if self._ns_bayes is None:
            self._ns_bayes = BayesNamespace(self)
        return self._ns_bayes

    @property
    def search(self) -> SearchNamespace:
        """Lazy-initialized property returning the search namespace."""
        if self._ns_search is None:
            self._ns_search = SearchNamespace(self)
        return self._ns_search

    @property
    def analyze(self) -> AnalyzeNamespace:
        """Lazy-initialized property returning the analytics namespace."""
        if self._ns_analyze is None:
            self._ns_analyze = AnalyzeNamespace(self)
        return self._ns_analyze

    @property
    def temporal(self) -> TemporalNamespace:
        """Lazy-initialized property returning the temporal namespace."""
        if self._ns_temporal is None:
            self._ns_temporal = TemporalNamespace(self)
        return self._ns_temporal

    @property
    def monitor(self) -> MonitorNamespace:
        """Lazy-initialized property returning the system monitor namespace."""
        if self._ns_monitor is None:
            self._ns_monitor = MonitorNamespace(self)
        return self._ns_monitor

    @property
    def cognitive(self) -> CognitiveNamespace:
        """Lazy-initialized property returning the cognitive namespace."""
        if self._ns_cognitive is None:
            self._ns_cognitive = CognitiveNamespace(self)
        return self._ns_cognitive

    @property
    def engine(self) -> EngineAccessor:
        """Lazy-initialized property returning the engine accessor."""
        if self._ns_engine is None:
            self._ns_engine = EngineAccessor(self)
        return self._ns_engine

    @property
    def search_engine(self) -> SearchEngine:
        """Lazy-initialized property returning the structured search engine."""
        if self._search_engine is None:
            if self._embedding_engine is None:
                self._embedding_engine = EmbeddingEngine(self._graph)
                self._retrieval._embedding = self._embedding_engine
            self._search_engine = SearchEngine(
                self._graph,
                activation=self._activation,
                embedding=self._embedding_engine,
                feedback_store=self._retrieval.feedback,
                ltr=self._retrieval.ltr,
            )
        return self._search_engine

    def centrality(self, method, *, top_k=None, **kwargs) -> Any:
        """Shortcut delegate to analyze.centrality()."""
        return self.analyze.centrality(method, top_k=top_k, **kwargs)

    def paths(self, source, target, *, label=None, max_depth=5, max_paths=10) -> list[list[str]]:
        """Shortcut delegate to analyze.paths()."""
        return self.analyze.paths(source, target, label=label, max_depth=max_depth, max_paths=max_paths)

    def communities(self, **kwargs) -> Any:
        """Shortcut delegate to analyze.communities()."""
        return self.analyze.communities(**kwargs)

    def anomalies(self, concept, **kwargs) -> Any:
        """Shortcut delegate to analyze.anomalies()."""
        return self.analyze.anomalies(concept, **kwargs)

    def similar(self, concept, **kwargs) -> Any:
        """Shortcut delegate to search.similar()."""
        return self.search.similar(concept, **kwargs)

    def edges(self, **kwargs) -> Any:
        """Shortcut delegate to analyze.edges()."""
        return self.analyze.edges(**kwargs)

    def describe(self) -> Any:
        """Shortcut delegate to analyze.describe()."""
        return self.analyze.describe()

    # Shortcuts below call the mixin directly (e.g. CognitiveMixin.prove(self, ...))
    # instead of going through the namespace (e.g. self.cognitive.prove(...)) because
    # the namespace calls self._mem.prove() which would recurse back to this shortcut.
    def prove(self, concept: str, *, facts: set[str] | None = None, depth: int = 5,
              known_facts: set[str] | None = None, max_depth: int | None = None,
              edge_label: str | None = None) -> Any:
        """Shortcut for backward chaining proof via cognitive.prove().

        Args:
            concept: Target concept to prove.
            facts: Known fact labels (alias for known_facts).
            depth: Maximum proof depth (alias for max_depth).
            known_facts: Known fact labels (overrides facts if both given).
            max_depth: Maximum proof depth (overrides depth if both given).
            edge_label: Restrict proof traversal to edges with this label.

        Returns:
            BackwardChainResult with proof tree and status.
        """
        kf = known_facts if known_facts is not None else facts
        md = max_depth if max_depth is not None else depth
        return CognitiveMixin.prove(self, concept, known_facts=kf, max_depth=md, edge_label=edge_label)

    def introspect(self) -> Any:
        """Shortcut for system health introspection via monitor.health().

        Returns:
            HealthReport with system and graph health metrics.
        """
        return MonitoringMixin.introspect(self)

    def activate(self, concept: str, *, energy: float = 1.0, top_k: int = 10) -> list:
        """Shortcut for spreading activation via search.activate().

        Args:
            concept: Source concept label to activate.
            energy: Initial activation energy.
            top_k: Maximum results to return.

        Returns:
            List of ActivationResult objects with label and activation level.
        """
        return RetrievalMixin.activate(self, concept, energy=energy, top_k=top_k)

    @property
    def frame_cache_stats(self) -> Any:
        """Return frame cache statistics, or None if the cache has not been initialized."""
        if self._perspective._frame_cache is None:
            return None
        return self._perspective._frame_cache.stats()

    def invalidate_frame_cache(self, frame=None) -> int:
        """Invalidate frame cache entries. Pass a frame name for targeted invalidation, or clear everything."""
        fc = self._perspective._frame_cache
        if fc is None:
            return 0
        if frame is not None:
            return fc.invalidate_frame(frame)
        s = fc.stats()
        fc.clear()
        return s.total_entries
