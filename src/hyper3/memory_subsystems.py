from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.cache import LazyCache
from hyper3.capabilities import CapabilityLevel
from hyper3.embedding import EmbeddingEngine, EmbeddingProvider, SimilarityResult
from hyper3.retrieval_activation import ActivationResult, SpreadingActivation
from hyper3.retrieval_engine import FeedbackStore, LearningToRank, RetrievalEngine, RetrievalResult
from hyper3.temporal import TemporalEvent, TemporalReasoner
from hyper3.provenance import Explanation, ProvenanceTracker
from hyper3.enrichment import ExtractionResult, LLMEnricher, LLMProvider
from hyper3.multiway import MultiwayEngine
from hyper3.multiway_branchial import BranchialSpace
from hyper3.multiway_rulial import RulialSpace
from hyper3.multiway_causal import CausalInvarianceEngine
from hyper3.quantum import QuantumCognitiveLayer
from hyper3.transfinite import TransfiniteReasoner
from hyper3.relativity import ComputationalRelativity, FrameAnalysis
from hyper3.meta_cognitive import MetaCognitiveLayer, MetamorphosisTrigger, MetamorphosisPlan
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.memory_base import _MemoryBase
from hyper3.results import TrainResult, TemporalMatch, IntrospectionReport, CognitiveStateInfo, GraphHealthInfo, EvolutionHealthInfo, DiscoveryHealthInfo, FeedbackSummaryResult, BiasProfileResult
from hyper3.feedback import OperationFeedback
from hyper3.validation import ValidationReport
from hyper3.backward_chain import BackwardChainEngine, BackwardChainResult
from hyper3.uncertainty import UncertaintyEngine, UncertaintyResult, ConfidenceScore, ConfidenceChain
from hyper3.structural_match import (
    StructuralPatternEngine,
    PatternTemplate,
    PatternNode,
    PatternEdge,
    StructuralMatchResult,
)
from hyper3.belief_revision import BeliefRevisionEngine, Contradiction, RevisionResult
from hyper3.abstraction import AbstractionNavigator, AbstractionSummary, AbstractionMapping, ExpandResult
from hyper3.community import CommunityDetector, CommunityResult
from hyper3.graph_diff import GraphDiffer, GraphDelta, GraphHistoryResult
from hyper3.hebbian import HebbianLearner, HebbianConfig, HebbianResult, HebbianUpdate


class SubsystemMixin(_MemoryBase):

    def set_embedding_provider(self, provider: EmbeddingProvider) -> None:
        """Set a custom embedding provider for semantic similarity.

        Args:
            provider: An EmbeddingProvider implementation.
        """
        self._embedding_engine = EmbeddingEngine(self._graph, provider=provider)
        self._retrieval._embedding = self._embedding_engine

    def enable_faiss(self, *, nlist: int = 100, nprobe: int = 10, use_gpu: bool = False) -> bool:
        """Enable FAISS-accelerated similarity search on the embedding engine.

        Args:
            nlist: Number of Voronoi cells for IVFFlat index (used when graph >= 1K nodes).
            nprobe: Number of cells to probe during search.
            use_gpu: Whether to use GPU-backed FAISS.

        Returns:
            True if FAISS was successfully enabled.
        """
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
            self._retrieval._embedding = self._embedding_engine
        result = self._embedding_engine.enable_faiss(nlist=nlist, nprobe=nprobe, use_gpu=use_gpu)
        self._log.record("enable_faiss", success=result)
        return result

    def find_similar(
        self, concept: str, *, top_k: int = 10, threshold: float | None = None
    ) -> list[SimilarityResult]:
        """Find semantically similar nodes to a concept using embeddings.

        Args:
            concept: Label of the query node.
            top_k: Maximum number of results.
            threshold: Minimum similarity score for results.

        Returns:
            List of SimilarityResult objects ranked by similarity.
        """
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        node = self._find_node(concept)
        if not node:
            return []
        results = self._embedding_engine.find_similar(node.id, top_k=top_k, threshold=threshold)
        self._log.record("find_similar", concept=concept, results=len(results))
        return results

    def analogy(
        self, a: str, b: str, c: str, *, top_k: int = 5
    ) -> list[tuple[str, float]]:
        """Solve an analogy problem: "a is to b as c is to ?".

        Uses vector arithmetic on embeddings to find the answer.

        Args:
            a: Label of the first concept.
            b: Label of the second concept.
            c: Label of the third concept.
            top_k: Maximum number of results.

        Returns:
            List of (label, score) tuples.
        """
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        node_a = self._find_node(a)
        node_b = self._find_node(b)
        node_c = self._find_node(c)
        if not node_a or not node_b or not node_c:
            return []
        results = self._embedding_engine.analogy(node_a.id, node_b.id, node_c.id, top_k=top_k)
        labeled = []
        for nid, score in results:
            node = self._graph.get_node(nid)
            label = node.label if node else nid[:8]
            labeled.append((label, score))
        return labeled

    def activate(self, concept: str, *, energy: float = 1.0, top_k: int = 10, iterations: int | None = None) -> list[ActivationResult]:
        """Perform spreading activation from a concept node.

        Args:
            concept: Label of the seed node.
            energy: Initial energy to inject.
            top_k: Maximum number of activated nodes to return.
            iterations: Number of spread iterations; None uses the engine default.

        Returns:
            List of ActivationResult objects sorted by activation level.
        """
        result = self._activation.associative_recall(concept, energy=energy, top_k=top_k, iterations=iterations)
        self._log.record("activate", concept=concept, results=len(result))
        return result

    def stimulate(self, concept: str, *, energy: float = 1.0) -> None:
        """Inject energy into a concept node for spreading activation.

        Args:
            concept: Label of the node to stimulate.
            energy: Amount of energy to inject.

        Raises:
            NodeNotFoundError: If the concept does not resolve to an existing node.
        """
        node = self._find_node(concept)
        if not node:
            from hyper3.exceptions import NodeNotFoundError
            raise NodeNotFoundError(concept)
        self._activation.stimulate(node.id, energy)

    def spread_activation(self, *, iterations: int | None = None) -> list[ActivationResult]:
        """Run one round of spreading activation and return activated nodes.

        Args:
            iterations: Number of spread iterations; None uses the engine default.

        Returns:
            List of ActivationResult objects sorted by activation level.
        """
        self._activation.spread(iterations)
        return self._activation.get_activated()

    def clear_activations(self) -> None:
        """Reset all spreading activation state."""
        self._activation.clear()

    def retrieve(self, concept: str, *, top_k: int = 10, iterations: int = 3, use_ltr: bool = False) -> list[RetrievalResult]:
        """Retrieve nodes relevant to a concept using RRF or learned-to-rank.

        Args:
            concept: Query concept label.
            top_k: Maximum number of results.
            iterations: Spreading activation iterations.
            use_ltr: If True, use the learned-to-rank model instead of RRF.

        Returns:
            List of RetrievalResult objects ranked by relevance.
        """
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        self._retrieval._embedding = self._embedding_engine
        results = self._retrieval.retrieve(concept, top_k=top_k, iterations=iterations, use_ltr=use_ltr)
        self._log.record("retrieve", concept=concept, results=len(results), method="rrf" if not use_ltr else "ltr")
        return results

    def record_feedback(self, query: str, results: list[RetrievalResult], relevant_labels: set[str]) -> int:
        """Record relevance feedback for a retrieval query.

        Args:
            query: The query string.
            results: The retrieval results being judged.
            relevant_labels: Set of labels deemed relevant by the user.

        Returns:
            The number of feedback entries recorded.
        """
        count = self._retrieval.record_feedback(query, results, relevant_labels)
        self._log.record("feedback", query=query, relevant=len(relevant_labels), total=count)
        return count

    def train_retriever(self) -> TrainResult:
        """Train the learning-to-rank model from accumulated feedback.

        Returns:
            TrainResult indicating whether training occurred and the learned weights.
        """
        report = self._retrieval.train_from_feedback()
        self._log.record("train_retriever", **report)
        if report.get("trained", False):
            return TrainResult(
                trained=True,
                weights=report.get("weights", {}),
                samples=report.get("samples", 0),
            )
        return TrainResult(reason=report.get("reason", ""))

    @property
    def feedback(self) -> FeedbackStore:
        """The raw feedback store for retrieval relevance judgments."""
        return self._retrieval.feedback

    @property
    def operation_feedback(self) -> OperationFeedback:
        """The operational feedback tracker for collapse, inference, and evolution outcomes."""
        return self._feedback

    def feedback_summary(self) -> FeedbackSummaryResult:
        """Compute a cross-operation feedback summary with correlations.

        Returns:
            FeedbackSummaryResult with per-operation metrics, overall health,
            fitness trend, and nodes appearing across multiple operation types.
        """
        return self._feedback.cross_operation_summary()

    @property
    def retrieval(self) -> RetrievalEngine:
        """The retrieval engine combining activation and semantic signals."""
        return self._retrieval

    def add_temporal_event(self, label: str, start: float, end: float, **metadata: Any) -> TemporalEvent:
        """Register a temporal event and store its node in the graph.

        Args:
            label: Event identifier.
            start: Start timestamp.
            end: End timestamp.
            **metadata: Additional metadata for the temporal event.

        Returns:
            The created TemporalEvent.
        """
        event = self._temporal.add_event(label, label, start, end, **metadata)
        self.store(label, data={"start": start, "end": end})
        self._log.record("temporal_event", label=label, start=start, end=end)
        return event

    def temporal_query(self, concept: str, *, relation: str = "overlapping", max_gap: float = 1.0) -> list[TemporalMatch]:
        """Query temporal events by their relationship to a reference event.

        Args:
            concept: Label of the reference event.
            relation: Allen interval relation (``"before"``, ``"after"``,
                ``"overlapping"``, ``"containing"``, ``"proximity"``).
            max_gap: Maximum gap for proximity queries.

        Returns:
            List of TemporalMatch with matching event labels, start/end times,
            and optional gap.
        """
        event = self._temporal.get_event(concept)
        if not event:
            return []
        if relation == "before":
            events = self._temporal.find_before(concept)
        elif relation == "after":
            events = self._temporal.find_after(concept)
        elif relation == "overlapping":
            events = self._temporal.find_overlapping(concept)
        elif relation == "containing":
            events = self._temporal.find_containing(concept)
        elif relation == "proximity":
            pairs = self._temporal.temporal_proximity(concept, max_gap=max_gap)
            return [
                TemporalMatch(label=e.label, start=e.interval.start, end=e.interval.end, gap=gap)
                for e, gap in pairs
            ]
        else:
            events = self._temporal.find_overlapping(concept)
        return [TemporalMatch(label=e.label, start=e.interval.start, end=e.interval.end) for e in events]

    def causal_chain(self, labels: list[str]) -> list[str]:
        """Return labels sorted into causal order based on temporal constraints."""
        return self._temporal.causal_order(labels)

    @property
    def temporal(self) -> TemporalReasoner:
        """The temporal reasoning subsystem."""
        return self._temporal

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set a custom LLM provider for text enrichment.

        Args:
            provider: An LLMProvider implementation.
        """
        self._enricher = LLMEnricher(llm=provider)

    def ingest(self, text: str, *, extract: bool = True) -> ExtractionResult:
        """Extract entities and relations from text and optionally store them.

        Args:
            text: Input text to process.
            extract: If True, store extracted entities as nodes and relations as edges.

        Returns:
            The ExtractionResult with entities and relations found.
        """
        result = self._enricher.extract(text)
        if extract:
            for entity in result.entities:
                self.store(
                    entity.label,
                    data={"type": entity.entity_type} if entity.entity_type else None,
                )
            for rel in result.relations:
                try:
                    self.relate(
                        rel.source_label,
                        rel.target_label,
                        label=rel.relation_label,
                        bidirectional=rel.bidirectional,
                    )
                except Exception:
                    pass
        self._log.record(
            "ingest",
            text_length=len(text),
            entities=len(result.entities),
            relations=len(result.relations),
        )
        return result

    def ingest_batch(
        self,
        texts: list[str],
        *,
        extract: bool = True,
        deduplicate: bool = True,
    ) -> list[ExtractionResult]:
        """Extract entities and relations from multiple texts.

        Args:
            texts: List of input texts to process.
            extract: If True, store extracted entities and relations in the graph.
            deduplicate: If True, skip entity nodes already seen in this batch.

        Returns:
            List of ExtractionResult objects, one per input text.
        """
        results: list[ExtractionResult] = []
        seen_entities: set[str] = set()
        for text in texts:
            result = self._enricher.extract(text)
            if extract:
                for entity in result.entities:
                    if deduplicate and entity.label in seen_entities:
                        continue
                    self.store(
                        entity.label,
                        data={"type": entity.entity_type} if entity.entity_type else None,
                    )
                    seen_entities.add(entity.label)
                for rel in result.relations:
                    try:
                        self.relate(
                            rel.source_label,
                            rel.target_label,
                            label=rel.relation_label,
                            bidirectional=rel.bidirectional,
                        )
                    except Exception:
                        pass
            results.append(result)
        self._log.record(
            "ingest_batch",
            texts=len(texts),
            total_entities=sum(len(r.entities) for r in results),
            total_relations=sum(len(r.relations) for r in results),
        )
        return results

    def explain(self, source: str, target: str, *, edge_label: str = "") -> Explanation | None:
        """Produce a recursive explanation for the edge between two concepts.

        Args:
            source: Label of the source node.
            target: Label of the target node.
            edge_label: If set, only explain edges with this label.

        Returns:
            An Explanation object, or None if no matching edge is found.
        """
        node_a = self._find_node(source)
        node_b = self._find_node(target)
        if not node_a or not node_b:
            return None
        for edge in self._graph.edges:
            if (node_a.id in edge.source_ids and node_b.id in edge.target_ids
                    and (not edge_label or edge.label == edge_label)):
                return self._provenance.explain(edge.id, graph=self._graph)
        return None

    def retract_inference(self, source: str, target: str, *, edge_label: str = "") -> list[str]:
        """Retract inferred edges between two concepts, cascading to dependent conclusions.

        Args:
            source: Label of the source node.
            target: Label of the target node.
            edge_label: If set, only retract edges with this label.

        Returns:
            List of retracted edge IDs.
        """
        node_a = self._find_node(source)
        node_b = self._find_node(target)
        if not node_a or not node_b:
            return []
        retracted: list[str] = []
        for edge in list(self._graph.edges):
            if (node_a.id in edge.source_ids and node_b.id in edge.target_ids
                    and (not edge_label or edge.label == edge_label)
                    and self._provenance.is_inferred(edge.id)):
                ids = self._provenance.retract(edge.id)
                for eid in ids:
                    self._graph.remove_edge(eid)
                    retracted.append(eid)
        self._log.record("retract", source=source, target=target, retracted=len(retracted))
        return retracted

    @property
    def provenance(self) -> ProvenanceTracker:
        """The provenance tracker for inference lineage."""
        return self._provenance

    @property
    def overlay(self) -> HypergraphOverlay | None:
        """The active inference overlay, or None if no overlay is in progress."""
        return self._overlay

    @property
    def embedding_engine(self) -> EmbeddingEngine | None:
        """The embedding engine, or None if no provider has been set."""
        return self._embedding_engine

    def enable_prefetch(self, enabled: bool = True) -> None:
        """Enable or disable Markov-model-based cache prefetching.

        Args:
            enabled: Whether to enable prefetching.
        """
        self._cache.enable_prefetch(enabled)

    def record_access(self, concept: str) -> None:
        """Record a concept access for the Markov prefetch model.

        Args:
            concept: Label of the accessed concept.
        """
        self._cache.record_access(f"store:{concept}")

    def predict_next_access(self, concept: str, *, top_k: int = 3) -> list[str]:
        """Predict which concepts are likely to be accessed next.

        Args:
            concept: Current concept label.
            top_k: Maximum number of predictions.

        Returns:
            List of predicted concept labels.
        """
        predicted_keys = self._cache.predict_next(f"store:{concept}", top_k=top_k)
        result: list[str] = []
        for key in predicted_keys:
            if key.startswith("store:"):
                label = key[6:]
                if self._graph.get_node_by_label(label):
                    result.append(label)
                    continue
            node = self._graph.get_node(key)
            result.append(node.label if node else key)
        return result

    def prefetch_neighbors(self, concept: str) -> int:
        """Prefetch a concept's neighbor data into the cache.

        Args:
            concept: Label of the node whose neighbors to prefetch.

        Returns:
            Number of neighbor entries prefetched.
        """
        node = self._find_node(concept)
        if not node:
            return 0
        neighbor_data: dict[str, dict] = {}
        for nid in self._graph.neighbors(node.id):
            n = self._graph.get_node(nid)
            if n:
                neighbor_data[nid] = {"label": n.label, "data": n.data}
        return self._cache.prefetch_neighbors(node.id, neighbor_data)

    @property
    def multiway(self) -> MultiwayEngine | None:
        """The multiway expansion engine, or None if not yet initialized."""
        return self._multiway_engine

    @property
    def quantum(self) -> QuantumCognitiveLayer:
        """The quantum cognitive layer for superposition and collapse."""
        return self._quantum

    @property
    def branchial(self) -> BranchialSpace | None:
        """The branchial space for multiway state coordinates, or None."""
        return self._branchial

    @property
    def rulial(self) -> RulialSpace:
        """The rulial space for rule universe tracking, lazily initialized."""
        if self._rulial is None:
            self._rulial = RulialSpace(self._graph)
        return self._rulial

    def compute_bias_profile(self) -> BiasProfileResult:
        """Analyze the system's computational biases from rule effectiveness data.

        Requires reasoning operations to have been run (so rule outcomes are
        recorded). Returns an empty profile if no rule data is available.

        Returns:
            BiasProfileResult with dominant/underused rules, reasoning style,
            position trajectory, and bias score.
        """
        return self.rulial.compute_bias_profile()

    @property
    def transfinite(self) -> TransfiniteReasoner:
        """The transfinite reasoner for self-referential and boundary analysis."""
        return self._transfinite

    @property
    def relativity(self) -> ComputationalRelativity:
        """The computational relativity engine for multi-frame analysis."""
        return self._relativity

    @property
    def meta(self) -> MetaCognitiveLayer:
        """The meta-cognitive layer for introspection and metamorphosis."""
        return self._meta

    @property
    def discovery(self) -> RuleDiscoveryEngine:
        """The rule discovery engine for pattern mining."""
        return self._discovery

    @property
    def cache(self) -> LazyCache:
        """The raw LRU cache with TTL and optional Markov prefetching."""
        return self._cache

    def introspect(self) -> IntrospectionReport:
        """Return a meta-cognitive introspection report for the current state."""
        raw = self._meta.introspect(self._rules)
        cs = raw.get("cognitive_state", {})
        gh = raw.get("graph_health", {})
        eh = raw.get("evolution_health", {})
        dh = raw.get("discovery_health", {})
        return IntrospectionReport(
            cognitive_state=CognitiveStateInfo(
                fitness=cs.get("fitness", 0.0),
                mode=cs.get("mode", ""),
                meta_level=cs.get("meta_level", 0),
                transcendental_yield=cs.get("transcendental_yield", 0),
            ),
            graph_health=GraphHealthInfo(
                nodes=gh.get("nodes", 0),
                edges=gh.get("edges", 0),
                avg_degree=gh.get("avg_degree", 0.0),
            ),
            evolution_health=EvolutionHealthInfo(
                merges=eh.get("merges", 0),
                prunes=eh.get("prunes", 0),
                refinements=eh.get("refinements", 0),
            ),
            discovery_health=DiscoveryHealthInfo(
                patterns=dh.get("patterns", 0),
                active_rules=dh.get("active_rules", 0),
            ),
            rulial_health=raw.get("rulial_health"),
            anti_patterns=raw.get("anti_patterns", []),
            recommendations=raw.get("recommendations", []),
        )

    def check_metamorphosis(self) -> list[MetamorphosisTrigger]:
        """Check whether any metamorphosis triggers fire (fitness, efficiency, staleness)."""
        return self._meta.check_metamorphosis_triggers()

    def propose_metamorphosis(self, triggers: list[MetamorphosisTrigger] | None = None) -> MetamorphosisPlan | None:
        """Propose a metamorphosis plan from the given or auto-detected triggers."""
        return self._meta.propose_metamorphosis(triggers)

    def execute_metamorphosis_validated(
        self,
        plan: MetamorphosisPlan,
        *,
        fitness_tolerance: float = 0.0,
    ) -> dict[str, Any]:
        """Execute a metamorphosis plan with snapshot, validation, and rollback.

        Requires a graph differ (created automatically on first capture_version
        call). If no differ is available, falls back to unvalidated execution.

        Args:
            plan: The metamorphosis plan to execute.
            fitness_tolerance: Minimum fitness improvement required to accept
                the metamorphosis. If 0, any non-degrading change is accepted.

        Returns:
            Dict with results, validated, rolled_back, fitness_before,
            fitness_after, and optional delta.
        """
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
            self._meta.set_differ(self._graph_differ)
        return self._meta.execute_metamorphosis_validated(
            plan, fitness_tolerance=fitness_tolerance,
        )

    def analyze_in_frame(self, concept: str, frame_name: str) -> FrameAnalysis:
        """Analyze a concept from a specific computational frame perspective."""
        return self._relativity.analyze_in_frame(concept, frame_name)

    def multi_frame_analysis(self, concept: str) -> dict[str, FrameAnalysis]:
        """Analyze a concept across all computational frames."""
        return self._relativity.multi_frame_analysis(concept)

    def select_optimal_frame(self, concept: str) -> tuple[str, FrameAnalysis]:
        """Select the best computational frame for reasoning about a concept."""
        return self._relativity.select_optimal_frame(concept)

    @property
    def enricher(self) -> LLMEnricher:
        """The text enrichment engine for entity and relation extraction."""
        return self._enricher

    def validate_reasoning(
        self,
        seed_concepts: set[str],
        rules: list[Any] | None = None,
    ) -> ValidationReport:
        """Run an A/B validation comparing simple vs enhanced reasoning.

        Args:
            seed_concepts: Labels of seed nodes.
            rules: Rules to apply; defaults to ``self._rules``.

        Returns:
            A ValidationReport with agreement metrics.
        """
        from hyper3.validation import ValidationEngine
        engine = ValidationEngine(self)
        return engine.run_comparison(seed_concepts, rules)

    def validate_comprehensive(
        self,
        test_cases: list[set[str]] | None = None,
    ) -> list[ValidationReport]:
        """Run the full validation suite across multiple test cases.

        Args:
            test_cases: Optional list of seed-concept sets. If None, uses defaults.

        Returns:
            List of ValidationReport objects, one per test case.
        """
        from hyper3.validation import ValidationEngine
        engine = ValidationEngine(self)
        return engine.run_validation_suite(test_cases)

    def detect_capability(self) -> CapabilityLevel:
        """Detect the current capability level of this memory instance."""
        from hyper3.capabilities import detect_capability_level
        return detect_capability_level(self)

    def prove(
        self,
        concept: str,
        *,
        known_facts: set[str] | None = None,
        edge_label: str | None = None,
        max_depth: int = 5,
    ) -> BackwardChainResult:
        """Attempt to prove a concept via backward chaining from known facts.

        Works backwards from the goal through inference rules to determine
        what premises are needed and which are already satisfied.

        Args:
            concept: Label of the node to prove.
            known_facts: Labels of nodes already established as true.
            edge_label: If set, only consider derivation chains using this edge label.
            max_depth: Maximum backward chaining depth.

        Returns:
            BackwardChainResult with achievability, missing premises, and proof tree.
        """
        if self._backward_chain is None:
            self._backward_chain = BackwardChainEngine(
                self._graph, self._rules, max_depth=max_depth,

            )
        return self._backward_chain.prove(
            concept, known_facts=known_facts, edge_label=edge_label,
        )
        return self._backward_chain.prove(
            target_concept, known_facts=known_facts, edge_label=edge_label,
        )

    def prove_batch(
        self,
        target_concepts: list[str],
        *,
        known_facts: set[str] | None = None,
        edge_label: str | None = None,
    ) -> list[BackwardChainResult]:
        """Prove multiple targets in sequence, accumulating proven facts.

        Args:
            target_concepts: Ordered list of concept labels to prove.
            known_facts: Initial set of established labels.
            edge_label: If set, constrain derivation chains to this edge label.

        Returns:
            List of BackwardChainResult objects, one per target.
        """
        if self._backward_chain is None:
            self._backward_chain = BackwardChainEngine(self._graph, self._rules)
        return self._backward_chain.prove_batch(
            target_concepts, known_facts=known_facts, edge_label=edge_label,
        )

    def hebbian_reinforce(self) -> HebbianResult:
        """Strengthen edges between co-activated nodes using Hebbian learning.

        Uses current spreading activation state to identify co-activated node
        pairs and strengthens connecting edges proportionally.

        Returns:
            HebbianResult with counts of strengthened and weakened edges.
        """
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        result = self._hebbian.reinforce_from_activation()
        self._log.record(
            "hebbian_reinforce",
            strengthened=result.edges_strengthened,
            weakened=result.edges_weakened,
        )
        return result

    def hebbian_reinforce_pair(
        self, source: str, target: str, *, strength: float = 1.0,
    ) -> HebbianUpdate | None:
        """Manually reinforce the connection between two concepts.

        Args:
            source: Label of the source node.
            target: Label of the target node.
            strength: Reinforcement strength multiplier.

        Returns:
            HebbianUpdate with old/new weight info, or None if no connecting edge.
        """
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        return self._hebbian.reinforce_pair(source, target, strength)

    def hebbian_decay_unused(self, *, threshold_access_count: int = 0) -> int:
        """Decay edges whose endpoints have low access counts.

        Args:
            threshold_access_count: Edges connected only to nodes at or below
                this access count are decayed.

        Returns:
            Number of edges decayed.
        """
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        updates = self._hebbian.decay_unused(threshold_access_count)
        return len(updates)

    def strongest_associations(
        self, concept: str, *, top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Return the strongest Hebbian associations from a concept.

        Args:
            concept: Label of the query node.
            top_k: Maximum number of results.

        Returns:
            List of (label, weight) tuples sorted by descending weight.
        """
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        return self._hebbian.get_strongest_associations(concept, top_k)

    def compute_confidence(self, concept: str) -> ConfidenceScore | None:
        """Compute the inference confidence for a concept node.

        Args:
            concept: Label of the node to evaluate.

        Returns:
            ConfidenceScore with confidence, depth, source, and contributing edges.
        """
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.compute_confidence(concept)

    def compute_all_confidences(self) -> UncertaintyResult:
        """Compute inference confidence for every node in the graph.

        Returns:
            UncertaintyResult with all node scores and aggregate statistics.
        """
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.compute_all_confidences()

    def flag_low_confidence(self, *, threshold: float = 0.3) -> list[ConfidenceScore]:
        """Flag nodes whose inference confidence falls below a threshold.

        Args:
            threshold: Minimum confidence to be considered reliable.

        Returns:
            List of ConfidenceScore objects below the threshold.
        """
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.flag_low_confidence(threshold)

    def trace_confidence_chain(
        self, source: str, target: str, *, max_depth: int = 10,
    ) -> ConfidenceChain | None:
        """Trace the highest-confidence inference chain between two concepts.

        Args:
            source: Label of the start node.
            target: Label of the end node.
            max_depth: Maximum chain length to explore.

        Returns:
            ConfidenceChain with depth, confidence, edges, and rule names, or None.
        """
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.trace_chain(source, target, max_depth)

    def match_structural_pattern(
        self,
        *,
        pattern_name: str = "custom",
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        max_matches: int = 100,
    ) -> StructuralMatchResult:
        """Match a structural pattern template against the graph.

        Args:
            pattern_name: Name for the pattern.
            nodes: List of dicts with keys ``role``, ``data_type``, ``label_pattern``, ``constraints``.
            edges: List of dicts with keys ``source_role``, ``target_role``, ``label``, ``min_weight``.
            max_matches: Maximum number of matches to return.

        Returns:
            StructuralMatchResult with all matched instances.
        """
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)

        p_nodes = [
            PatternNode(
                role=n.get("role", ""),
                data_type=n.get("data_type"),
                label_pattern=n.get("label_pattern"),
                constraints=n.get("constraints", {}),
            )
            for n in (nodes or [])
        ]
        p_edges = [
            PatternEdge(
                source_role=e.get("source_role", ""),
                target_role=e.get("target_role", ""),
                label=e.get("label"),
                min_weight=e.get("min_weight", 0.0),
            )
            for e in (edges or [])
        ]

        template = PatternTemplate(
            name=pattern_name, nodes=p_nodes, edges=p_edges,
        )
        return self._structural_matcher.match_pattern(template, max_matches=max_matches)

    def match_chains(
        self,
        *,
        edge_label: str | None = None,
        min_length: int = 2,
        max_length: int = 5,
        max_chains: int = 50,
    ) -> list[list[str]]:
        """Find chain patterns (linear sequences) in the graph.

        Args:
            edge_label: If set, only follow edges with this label.
            min_length: Minimum chain length in edges.
            max_length: Maximum chain length in edges.
            max_chains: Maximum number of chains to return.

        Returns:
            List of chains, each a list of node labels.
        """
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)
        chains = self._structural_matcher.match_chain(
            edge_label=edge_label,
            min_length=min_length,
            max_length=max_length,
            max_chains=max_chains,
        )
        labeled_chains: list[list[str]] = []
        for chain in chains:
            labeled: list[str] = []
            for nid in chain:
                node = self._graph.get_node(nid)
                labeled.append(node.label if node else nid[:8])
            labeled_chains.append(labeled)
        return labeled_chains

    def match_diamonds(
        self, *, edge_label: str | None = None, max_matches: int = 50,
    ) -> list[dict[str, Any]]:
        """Find diamond patterns (A->C, B->C, A and B share common upstream).

        Args:
            edge_label: If set, only consider edges with this label.
            max_matches: Maximum number of diamond patterns to return.

        Returns:
            List of dicts with source_a, source_b, converge labels and score.
        """
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)
        matches = self._structural_matcher.match_diamond(
            edge_label=edge_label, max_matches=max_matches,
        )
        results: list[dict[str, Any]] = []
        for m in matches:
            entry: dict[str, Any] = {"score": m.score}
            for role, nid in m.bindings.items():
                node = self._graph.get_node(nid)
                entry[role] = node.label if node else nid[:8]
            results.append(entry)
        return results

    def match_fan_out(
        self,
        *,
        edge_label: str | None = None,
        min_fan: int = 3,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Find nodes with high fan-out (many outgoing connections).

        Args:
            edge_label: If set, only count edges with this label.
            min_fan: Minimum number of outgoing connections to report.
            max_results: Maximum number of results.

        Returns:
            List of dicts with node label and target labels.
        """
        if self._structural_matcher is None:
            self._structural_matcher = StructuralPatternEngine(self._graph)
        fans = self._structural_matcher.match_fan_out(
            edge_label=edge_label, min_fan=min_fan, max_results=max_results,
        )
        results: list[dict[str, Any]] = []
        for nid, target_ids in fans:
            node = self._graph.get_node(nid)
            tgt_labels: list[str] = []
            for tid in target_ids:
                tn = self._graph.get_node(tid)
                tgt_labels.append(tn.label if tn else tid[:8])
            results.append({
                "node": node.label if node else nid[:8],
                "fan_out": len(target_ids),
                "targets": tgt_labels,
            })
        return results

    def detect_contradictions(self) -> list[Contradiction]:
        """Detect contradictory edges in the graph using negation mapping.

        Returns:
            List of Contradiction objects with edge IDs, labels, and severity.
        """
        if self._belief_revision is None:
            self._belief_revision = BeliefRevisionEngine(self._graph, self._provenance)
        return self._belief_revision.detect_contradictions()

    def revise_beliefs(self, *, strategy: str = "higher_confidence") -> RevisionResult:
        """Detect and resolve contradictions in the graph.

        Args:
            strategy: Resolution strategy. One of ``higher_confidence``,
                ``higher_weight``, ``observed_over_inferred``, ``newer``.

        Returns:
            RevisionResult with counts of contradictions found and edges revised.
        """
        if self._belief_revision is None:
            self._belief_revision = BeliefRevisionEngine(self._graph, self._provenance)
        result = self._belief_revision.revise(strategy=strategy)
        self._log.record(
            "revise_beliefs",
            contradictions=result.contradictions_detected,
            edges_removed=result.edges_removed_count,
        )
        return result

    def check_consistency(
        self, source: str, target: str,
    ) -> list[Contradiction]:
        """Check for contradictions between two specific concepts.

        Args:
            source: Label of the source node.
            target: Label of the target node.

        Returns:
            List of Contradiction objects between the two concepts.
        """
        if self._belief_revision is None:
            self._belief_revision = BeliefRevisionEngine(self._graph, self._provenance)
        return self._belief_revision.check_consistency(source, target)

    def collapse_subgraph(
        self,
        node_labels: set[str],
        *,
        summary_label: str | None = None,
        summary_data: Any = None,
        layer: str = "summary",
    ) -> AbstractionSummary | None:
        """Collapse a set of nodes into a single summary node.

        External connections are rewired to the summary node. Internal edges
        are removed. The mapping is stored for later expansion.

        Args:
            node_labels: Labels of nodes to collapse.
            summary_label: Label for the new summary node.
            summary_data: Optional data payload for the summary node.
            layer: Abstraction layer string (``detail``, ``intermediate``, ``summary``).

        Returns:
            AbstractionSummary, or None if no valid nodes found.
        """
        from hyper3.kernel import AbstractionLayer
        if self._abstraction_nav is None:
            self._abstraction_nav = AbstractionNavigator(self._graph)
        layer_enum = AbstractionLayer(layer)
        return self._abstraction_nav.collapse_subgraph(
            node_labels,
            summary_label=summary_label,
            summary_data=summary_data,
            layer=layer_enum,
        )

    def expand_summary(self, summary_label: str) -> ExpandResult | None:
        """Expand a previously collapsed summary node back into its constituents.

        Args:
            summary_label: Label of the summary node to expand.

        Returns:
            ExpandResult with expanded_nodes and expanded_edges, or None.
        """
        if self._abstraction_nav is None:
            self._abstraction_nav = AbstractionNavigator(self._graph)
        return self._abstraction_nav.expand_node(summary_label)

    def list_summaries(self) -> list[AbstractionMapping]:
        """List all summary nodes and their collapsed constituents.

        Returns:
            List of AbstractionMapping objects.
        """
        if self._abstraction_nav is None:
            self._abstraction_nav = AbstractionNavigator(self._graph)
        return self._abstraction_nav.list_summaries()

    def detect_communities(
        self,
        *,
        method: str = "label_propagation",
        edge_label: str | None = None,
        seed: int = 42,
    ) -> CommunityResult:
        """Detect communities (clusters) in the graph.

        Args:
            method: Detection method. ``label_propagation`` (default) or
                ``weighted_label_propagation`` or ``connected_components``.
            edge_label: If set, only consider edges with this label.
            seed: Random seed for reproducibility.

        Returns:
            CommunityResult with communities, modularity, and coverage.
        """
        if self._community_detector is None:
            self._community_detector = CommunityDetector(self._graph)

        if method == "weighted_label_propagation":
            return self._community_detector.detect_weighted_label_propagation(
                seed=seed, edge_label=edge_label,
            )
        elif method == "connected_components":
            return self._community_detector.detect_connected_components()
        else:
            return self._community_detector.detect_label_propagation(
                seed=seed, edge_label=edge_label,
            )

    def capture_version(self) -> dict[str, int]:
        """Capture the current graph state as a named version for later diffing.

        Returns:
            Dict with version_id, node_count, and edge_count.
        """
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
            self._meta.set_differ(self._graph_differ)
        version = self._graph_differ.capture()
        return {
            "version_id": version.version_id,
            "node_count": version.node_count,
            "edge_count": version.edge_count,
        }

    def diff_from_version(self, version_id: int) -> GraphDelta | None:
        """Compute the diff between a captured version and the current state.

        Args:
            version_id: The version to compare against.

        Returns:
            GraphDelta with all changes, or None if version not found.
        """
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
        return self._graph_differ.diff_from_version(version_id)

    def diff_between_versions(self, v1: int, v2: int) -> GraphDelta | None:
        """Compute the diff between two captured versions.

        Args:
            v1: First version ID.
            v2: Second version ID.

        Returns:
            GraphDelta with all changes, or None if either version not found.
        """
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
        return self._graph_differ.diff_between_versions(v1, v2)

    def version_history(self) -> GraphHistoryResult:
        """Return the full version history.

        Returns:
            GraphHistoryResult with versions list, total_versions, and current_version.
        """
        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
        return self._graph_differ.history

    @property
    def backward_chain(self) -> BackwardChainEngine | None:
        """The backward chaining engine, or None if not yet initialized."""
        return self._backward_chain

    @property
    def hebbian(self) -> HebbianLearner | None:
        """The Hebbian learning engine, or None if not yet initialized."""
        return self._hebbian

    @property
    def uncertainty(self) -> UncertaintyEngine | None:
        """The uncertainty engine, or None if not yet initialized."""
        return self._uncertainty_engine

    @property
    def structural_matcher(self) -> StructuralPatternEngine | None:
        """The structural pattern matcher, or None if not yet initialized."""
        return self._structural_matcher

    @property
    def belief_reviser(self) -> BeliefRevisionEngine | None:
        """The belief revision engine, or None if not yet initialized."""
        return self._belief_revision

    @property
    def abstraction(self) -> AbstractionNavigator | None:
        """The abstraction navigator, or None if not yet initialized."""
        return self._abstraction_nav

    @property
    def communities(self) -> CommunityDetector | None:
        """The community detector, or None if not yet initialized."""
        return self._community_detector

    @property
    def differ(self) -> GraphDiffer | None:
        """The graph differ, or None if not yet initialized."""
        return self._graph_differ
