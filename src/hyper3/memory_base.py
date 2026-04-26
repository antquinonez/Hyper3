from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph, Hypernode
from hyper3.event_log import EventLog
from hyper3.cache import LazyCache
from hyper3.traversal import ObserverSlice, TraversalEngine
from hyper3.evolution import SelfEvolutionEngine
from hyper3.equivalence import EquivalenceEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.multiway_causal import CausalInvarianceEngine
from hyper3.quantum import QuantumCognitiveLayer
from hyper3.multiway import MultiwayEngine
from hyper3.rules import Rule
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.persistence import Serializer
from hyper3.multiway_branchial import BranchialSpace
from hyper3.multiway_rulial import RulialSpace
from hyper3.transfinite import TransfiniteReasoner
from hyper3.relativity import ComputationalRelativity
from hyper3.meta_cognitive import MetaCognitiveLayer
from hyper3.embedding import EmbeddingEngine
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.retrieval_engine import RetrievalEngine
from hyper3.temporal import TemporalReasoner
from hyper3.provenance import ProvenanceTracker
from hyper3.enrichment import LLMEnricher
from hyper3.feedback import OperationFeedback
from hyper3.constraints import BoundaryNavigator


class _MemoryBase:
    _graph: Hypergraph
    _log: EventLog
    _cache: LazyCache
    _traversal: TraversalEngine
    _observer: ObserverSlice
    _evolution: SelfEvolutionEngine
    _equivalence: EquivalenceEngine
    _decay_factor: float
    _evolve_interval: int
    _merge_threshold: float
    _decay_threshold: float
    _operation_count: int
    _multiway_engine: MultiwayEngine | None
    _causal_engine: CausalInvarianceEngine | None
    _quantum: QuantumCognitiveLayer
    _rules: list[Rule]
    _discovery: RuleDiscoveryEngine
    _serializer: Serializer
    _branchial: BranchialSpace | None
    _rulial: RulialSpace | None
    _transfinite: TransfiniteReasoner
    _relativity: ComputationalRelativity
    _meta: MetaCognitiveLayer
    _embedding_engine: EmbeddingEngine | None
    _activation: SpreadingActivation
    _retrieval: RetrievalEngine
    _temporal: TemporalReasoner
    _provenance: ProvenanceTracker
    _enricher: LLMEnricher
    _overlay: HypergraphOverlay | None
    _feedback: OperationFeedback
    _boundary_navigator: BoundaryNavigator | None

    def _find_node(self, label: str) -> Hypernode | None: ...
    def _node_label(self, node_id: str) -> str: ...
    def _maybe_evolve(self) -> None: ...
    def store(self, concept: str, data: Any = None, **kwargs: Any) -> Hypernode: ...
    def relate(self, source_concept: str, target_concept: str, **kwargs: Any) -> Any: ...
    def commit_inferences(self) -> dict[str, Any]: ...
