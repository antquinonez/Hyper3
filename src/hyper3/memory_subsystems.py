from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.cache import LazyCache
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
from hyper3.relativity import ComputationalRelativity
from hyper3.meta_cognitive import MetaCognitiveLayer
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.memory_base import _MemoryBase


class SubsystemMixin(_MemoryBase):

    def set_embedding_provider(self, provider: EmbeddingProvider) -> None:
        self._embedding_engine = EmbeddingEngine(self._graph, provider=provider)
        self._retrieval._embedding = self._embedding_engine

    def enable_faiss(self, *, nlist: int = 100, nprobe: int = 10, use_gpu: bool = False) -> bool:
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
            self._retrieval._embedding = self._embedding_engine
        result = self._embedding_engine.enable_faiss(nlist=nlist, nprobe=nprobe, use_gpu=use_gpu)
        self._log.record("enable_faiss", success=result)
        return result

    def find_similar(
        self, concept: str, *, top_k: int = 10, threshold: float | None = None
    ) -> list[SimilarityResult]:
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
        result = self._activation.associative_recall(concept, energy=energy, top_k=top_k, iterations=iterations)
        self._log.record("activate", concept=concept, results=len(result))
        return result

    def stimulate(self, concept: str, energy: float = 1.0) -> None:
        node = self._find_node(concept)
        if node:
            self._activation.stimulate(node.id, energy)

    def spread_activation(self, *, iterations: int | None = None) -> list[ActivationResult]:
        self._activation.spread(iterations)
        return self._activation.get_activated()

    def clear_activations(self) -> None:
        self._activation.clear()

    def retrieve(self, concept: str, *, top_k: int = 10, iterations: int = 3, use_ltr: bool = False) -> list[RetrievalResult]:
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        self._retrieval._embedding = self._embedding_engine
        results = self._retrieval.retrieve(concept, top_k=top_k, iterations=iterations, use_ltr=use_ltr)
        self._log.record("retrieve", concept=concept, results=len(results), method="rrf" if not use_ltr else "ltr")
        return results

    def record_feedback(self, query: str, results: list[RetrievalResult], relevant_labels: set[str]) -> int:
        count = self._retrieval.record_feedback(query, results, relevant_labels)
        self._log.record("feedback", query=query, relevant=len(relevant_labels), total=count)
        return count

    def train_retriever(self) -> dict[str, Any]:
        report = self._retrieval.train_from_feedback()
        self._log.record("train_retriever", **report)
        return report

    @property
    def feedback(self) -> FeedbackStore:
        return self._retrieval.feedback

    @property
    def retrieval(self) -> RetrievalEngine:
        return self._retrieval

    def add_temporal_event(self, label: str, start: float, end: float, **metadata: Any) -> TemporalEvent:
        event = self._temporal.add_event(label, label, start, end, **metadata)
        self.store(label, data={"start": start, "end": end})
        self._log.record("temporal_event", label=label, start=start, end=end)
        return event

    def temporal_query(self, label: str, *, relation: str = "overlapping", max_gap: float = 1.0) -> list[dict]:
        event = self._temporal.get_event(label)
        if not event:
            return []
        if relation == "before":
            events = self._temporal.find_before(label)
        elif relation == "after":
            events = self._temporal.find_after(label)
        elif relation == "overlapping":
            events = self._temporal.find_overlapping(label)
        elif relation == "containing":
            events = self._temporal.find_containing(label)
        elif relation == "proximity":
            pairs = self._temporal.temporal_proximity(label, max_gap=max_gap)
            return [
                {"label": e.label, "start": e.interval.start, "end": e.interval.end, "gap": gap}
                for e, gap in pairs
            ]
        else:
            events = self._temporal.find_overlapping(label)
        return [{"label": e.label, "start": e.interval.start, "end": e.interval.end} for e in events]

    def causal_chain(self, labels: list[str]) -> list[str]:
        return self._temporal.causal_order(labels)

    @property
    def temporal(self) -> TemporalReasoner:
        return self._temporal

    def set_llm_provider(self, provider: LLMProvider) -> None:
        self._enricher = LLMEnricher(llm=provider)

    def ingest(self, text: str, *, extract: bool = True) -> ExtractionResult:
        result = self._enricher.extract(text)
        if extract:
            for entity in result.entities:
                self.store(
                    entity.label,
                    data={"type": entity.entity_type} if entity.entity_type else None,
                )
            for rel in result.relations:
                self.relate(
                    rel.source_label,
                    rel.target_label,
                    label=rel.relation_label,
                    bidirectional=rel.bidirectional,
                )
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
                    self.relate(
                        rel.source_label,
                        rel.target_label,
                        label=rel.relation_label,
                        bidirectional=rel.bidirectional,
                    )
            results.append(result)
        self._log.record(
            "ingest_batch",
            texts=len(texts),
            total_entities=sum(len(r.entities) for r in results),
            total_relations=sum(len(r.relations) for r in results),
        )
        return results

    def explain(self, concept_a: str, concept_b: str, edge_label: str = "") -> Explanation | None:
        node_a = self._find_node(concept_a)
        node_b = self._find_node(concept_b)
        if not node_a or not node_b:
            return None
        for edge in self._graph.edges:
            if (node_a.id in edge.source_ids and node_b.id in edge.target_ids
                    and (not edge_label or edge.label == edge_label)):
                return self._provenance.explain(edge.id, graph=self._graph)
        return None

    def retract_inference(self, concept_a: str, concept_b: str, edge_label: str = "") -> list[str]:
        node_a = self._find_node(concept_a)
        node_b = self._find_node(concept_b)
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
        self._log.record("retract", source=concept_a, target=concept_b, retracted=len(retracted))
        return retracted

    @property
    def provenance(self) -> ProvenanceTracker:
        return self._provenance

    @property
    def overlay(self) -> HypergraphOverlay | None:
        return self._overlay

    @property
    def embedding_engine(self) -> EmbeddingEngine | None:
        return self._embedding_engine

    def enable_prefetch(self, enabled: bool = True) -> None:
        self._cache.enable_prefetch(enabled)

    def record_access(self, concept: str) -> None:
        self._cache.record_access(f"store:{concept}")

    def predict_next_access(self, concept: str, top_k: int = 3) -> list[str]:
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
        return self._multiway_engine

    @property
    def quantum(self) -> QuantumCognitiveLayer:
        return self._quantum

    @property
    def branchial(self) -> BranchialSpace | None:
        return self._branchial

    @property
    def rulial(self) -> RulialSpace:
        if self._rulial is None:
            self._rulial = RulialSpace(self._graph)
        return self._rulial

    @property
    def transfinite(self) -> TransfiniteReasoner:
        return self._transfinite

    @property
    def relativity(self) -> ComputationalRelativity:
        return self._relativity

    @property
    def meta(self) -> MetaCognitiveLayer:
        return self._meta

    @property
    def discovery(self) -> RuleDiscoveryEngine:
        return self._discovery

    @property
    def cache(self) -> LazyCache:
        return self._cache

    def introspect(self) -> dict[str, Any]:
        return self._meta.introspect(self._rules)

    def check_metamorphosis(self) -> list[Any]:
        """Check whether any metamorphosis triggers fire (fitness, efficiency, staleness)."""
        return self._meta.check_metamorphosis_triggers()

    def propose_metamorphosis(self, triggers: list[Any] | None = None) -> Any:
        """Propose a metamorphosis plan from the given or auto-detected triggers."""
        return self._meta.propose_metamorphosis(triggers)

    def analyze_in_frame(self, concept: str, frame_name: str) -> Any:
        """Analyze a concept from a specific computational frame perspective."""
        return self._relativity.analyze_in_frame(concept, frame_name)

    def multi_frame_analysis(self, concept: str) -> Any:
        """Analyze a concept across all computational frames."""
        return self._relativity.multi_frame_analysis(concept)

    def select_optimal_frame(self, concept: str) -> Any:
        """Select the best computational frame for reasoning about a concept."""
        return self._relativity.select_optimal_frame(concept)

    @property
    def enricher(self) -> LLMEnricher:
        return self._enricher

    def validate_reasoning(
        self,
        seed_concepts: set[str],
        rules: list[Any] | None = None,
    ) -> Any:
        from hyper3.validation import ValidationEngine
        engine = ValidationEngine(self)
        return engine.run_comparison(seed_concepts, rules)

    def validate_comprehensive(
        self,
        test_cases: list[set[str]] | None = None,
    ) -> list[Any]:
        from hyper3.validation import ValidationEngine
        engine = ValidationEngine(self)
        return engine.run_validation_suite(test_cases)

    def detect_capability(self):
        from hyper3.capabilities import detect_capability_level
        return detect_capability_level(self)
