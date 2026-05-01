from __future__ import annotations

from hyper3.cache import LazyCache
from hyper3.embedding import EmbeddingEngine, EmbeddingProvider, SimilarityResult
from hyper3.feedback import OperationFeedback
from hyper3.memory_base import _MemoryBase
from hyper3.results import FeedbackSummaryResult, TrainResult
from hyper3.retrieval_activation import ActivationResult, SpreadingActivation
from hyper3.retrieval_engine import FeedbackStore, RetrievalEngine, RetrievalResult


class RetrievalMixin(_MemoryBase):
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

    def find_similar(self, concept: str, *, top_k: int = 10, threshold: float | None = None) -> list[SimilarityResult]:
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        node = self._find_node(concept)
        if not node:
            return []
        results = self._embedding_engine.find_similar(node.id, top_k=top_k, threshold=threshold)
        self._log.record("find_similar", concept=concept, results=len(results))
        return results

    def analogy(self, a: str, b: str, c: str, *, top_k: int = 5) -> list[tuple[str, float]]:
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

    def activate(
        self, concept: str, *, energy: float = 1.0, top_k: int = 10, iterations: int | None = None
    ) -> list[ActivationResult]:
        result = self._activation.associative_recall(concept, energy=energy, top_k=top_k, iterations=iterations)
        self._log.record("activate", concept=concept, results=len(result))
        return result

    def stimulate(self, concept: str, *, energy: float = 1.0) -> None:
        node = self._find_node(concept)
        if not node:
            from hyper3.exceptions import NodeNotFoundError

            raise NodeNotFoundError(concept)
        self._activation.stimulate(node.id, energy)

    def spread_activation(self, *, iterations: int | None = None) -> list[ActivationResult]:
        self._activation.spread(iterations)
        return self._activation.get_activated()

    def clear_activations(self) -> None:
        self._activation.clear()

    def retrieve(
        self, concept: str, *, top_k: int = 10, iterations: int = 3, use_ltr: bool = False
    ) -> list[RetrievalResult]:
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

    def train_retriever(self) -> TrainResult:
        result = self._retrieval.train_from_feedback()
        self._log.record("train_retriever", trained=result.trained, samples=result.samples)
        return result

    @property
    def feedback(self) -> FeedbackStore:
        return self._retrieval.feedback

    @property
    def operation_feedback(self) -> OperationFeedback:
        return self._feedback

    def feedback_summary(self) -> FeedbackSummaryResult:
        return self._feedback.cross_operation_summary()

    @property
    def retrieval(self) -> RetrievalEngine:
        return self._retrieval

    @property
    def embedding_engine(self) -> EmbeddingEngine | None:
        return self._embedding_engine

    def enable_prefetch(self, enabled: bool = True) -> None:
        self._cache.enable_prefetch(enabled)

    def record_access(self, concept: str) -> None:
        self._cache.record_access(f"store:{concept}")

    def predict_next_access(self, concept: str, *, top_k: int = 3) -> list[str]:
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
    def cache(self) -> LazyCache:
        return self._cache

    def spread_hyperedge(
        self,
        concept: str,
        *,
        energy: float = 1.0,
        mode: str = "linear",
        iterations: int | None = None,
    ) -> list[ActivationResult]:
        node = self._find_node(concept)
        if not node:
            return []
        if self._activation is None:
            self._activation = SpreadingActivation(self._graph)
        self._activation.clear()
        self._activation.stimulate(node.id, energy)
        self._activation.spread_hyperedge(mode=mode, iterations=iterations)
        return self._activation.get_activated()
