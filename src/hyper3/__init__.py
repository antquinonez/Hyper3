from hyper3.exceptions import (
    CollapseError,
    ConstraintViolationError,
    EdgeNotFoundError,
    EntanglementError,
    Hyper3Error,
    InferenceError,
    NodeNotFoundError,
    QuantumStateNotFoundError,
    RuleApplicationError,
    SerializationError,
    StateNotFoundError,
    TemporalConstraintError,
)
from hyper3.kernel import (
    AbstractionLayer,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
    Modality,
)
from hyper3.event_log import EventLog
from hyper3.equivalence import EquivalenceEngine
from hyper3.cache import LazyCache
from hyper3.traversal import TraversalEngine, SliceConfig, ObserverSlice
from hyper3.evolution import EvolutionMetrics, SelfEvolutionEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.memory import CognitiveMemory
from hyper3.rules import (
    AbductiveRule,
    AnalogicalReasoningRule,
    CausalInferenceRule,
    ContextualSubstitutionRule,
    GeneralizationRule,
    InverseRule,
    PropertyPropagationRule,
    Rule,
    RuleMatch,
    TransitiveRule,
)
from hyper3.multiway import (
    BranchialRelation,
    ExpansionReport,
    MultiwayEngine,
    MultiwayGraph,
    MultiwayState,
)
from hyper3.multiway_causal import (
    CausalInvarianceEngine,
    CausalInvariant,
)
from hyper3.quantum import (
    CollapseTrigger,
    Interpretation,
    InterferencePattern,
    MeasurementBasis,
    PotentialFieldConfig,
    QuantumCognitiveLayer,
    QuantumEntanglement,
    QuantumState,
)
from hyper3.persistence import Serializer
from hyper3.rules_discovery import DiscoveredRule, RuleDiscoveryEngine
from hyper3.multiway_branchial import (
    AnalogyProposal,
    BranchialCluster,
    BranchialCoordinates,
    BranchialDistanceMetrics,
    BranchialEntanglement,
    BranchialSpace,
    MultiScaleAnalysis,
    ScaleLevel,
    SimultaneityGroup,
)
from hyper3.multiway_rulial import (
    HighLevelInsight,
    MetaComputationalPattern,
    RulialPosition,
    RulialSpace,
)
from hyper3.structural_anomaly import (
    AnomalyDetectionResult,
    Axiom,
    AxiomSet,
    BoundaryIndicator,
    BoundaryRegion,
    ExplorationReport,
    StructuralAnomalyDetector,
)

from hyper3.frame_transform import (
    FrameTransformer,
    TransformedConfig,
)
from hyper3.multi_perspective import (
    ComputationalFrame,
    ConsensusResult,
    DisagreementRegion,
    FrameAnalysis,
    FrameTransformation,
    InvariantDetector,
    InvariantSet,
    MultiPerspectiveAnalyzer,
    ProblemFeatures,
    StructuralMetrics,
)

from hyper3.meta_cognitive import (
    CognitiveStateModel,
    MetaCognitiveLayer,
    MetamorphosisPlan,
    MetamorphosisTrigger,
)
from hyper3 import visualization
from hyper3.embedding import (
    EmbeddingEngine,
    EmbeddingProvider,
    HashEmbeddingProvider,
    SimilarityResult,
)
from hyper3.embedding_graph import (
    CompositeEmbeddingProvider,
    NeighborhoodFingerprintProvider,
    RandomWalkEmbeddingProvider,
)
from hyper3.retrieval_activation import (
    ActivationConfig,
    ActivationResult,
    SpreadingActivation,
)
from hyper3.retrieval_engine import (
    FeedbackRecord,
    FeedbackStore,
    LearningToRank,
    RetrievalEngine,
    RetrievalResult,
)
from hyper3.provenance import (
    Explanation,
    ProvenanceRecord,
    ProvenanceTracker,
)
from hyper3.temporal import (
    AllenRelation,
    TemporalConstraint,
    TemporalEvent,
    TemporalReasoner,
    TimeInterval,
)
from hyper3.enrichment import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    LLMEnricher,
    LLMProvider,
    RegexExtractor,
)
from hyper3.capabilities import (
    CapabilityLevel,
    detect_capability_level,
    require_capability,
)
from hyper3.constraints import (
    BoundaryNavigator,
    ConstraintCheck,
    NoSelfLoopConstraint,
    ProvenanceDepthConstraint,
    WeightInflationConstraint,
)
from hyper3.feedback import (
    FeedbackSignal,
    OperationFeedback,
)
from hyper3.snapshot import CognitiveSnapshot
from hyper3.validation import (
    AgreementMetrics,
    ReasoningSummary,
    ValidationEngine,
    ValidationReport,
)
from hyper3.results import (
    BiasProfileResult,
    BranchialAnalysis,
    CausalEnforceReport,
    CommitResult,
    ConsensusReasonResult,
    CorrelatedNodeInfo,
    DerivationInfo,
    DiscoverResult,
    DiscoveryAnalysis,
    EvolveResult,
    EvolutionStats,
    ExpansionInfo,
    FeedbackSummaryResult,
    ImportResult,
    IntrospectionReport,
    IterativeReasonResult,
    LateralInferenceInsight,
    MemoryStats,
    MetaCognitiveStats,
    MetamorphosisResult,
    PatternMatchInfo,
    ReasonResult,
    AnomalyAnalysis,
    PerspectiveAnalysis,
    RollbackResult,
    RuleNeighborhoodResult,
    RulialAnalysis,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResult,
    TemporalConsistencyResult,
    TemporalInconsistency,
    TemporalMatch,
    TrainResult,
)
from hyper3.backward_chain import (
    BackwardChainEngine,
    BackwardChainResult,
    ProofStep,
    ProofTree,
)
from hyper3.hebbian import (
    HebbianConfig,
    HebbianLearner,
    HebbianResult,
    HebbianUpdate,
)
from hyper3.uncertainty import (
    ConfidenceChain,
    ConfidenceScore,
    UncertaintyEngine,
    UncertaintyResult,
)
from hyper3.structural_match import (
    PatternEdge,
    PatternNode,
    PatternTemplate,
    StructuralMatch,
    StructuralMatchResult,
    StructuralPatternEngine,
)
from hyper3.belief_revision import (
    BeliefRevisionEngine,
    Contradiction,
    RevisionAction,
    RevisionPlan,
    RevisionResult,
)
from hyper3.abstraction import (
    AbstractionMapping,
    AbstractionNavigator,
    AbstractionSummary,
)
from hyper3.community import (
    Community,
    CommunityDetector,
    CommunityResult,
)
from hyper3.graph_diff import (
    EdgeDelta,
    GraphDelta,
    GraphDiffer,
    GraphHistoryResult,
    GraphVersion,
    NodeDelta,
)
