"""RetrievalMixin: spreading activation, semantic search, RRF retrieval."""
from __future__ import annotations

from hyper3.cache import LazyCache
from hyper3.embedding import EmbeddingEngine, EmbeddingProvider
from hyper3.embedding_graph import SemanticEdgeBuilder
from hyper3.feedback import OperationFeedback
from hyper3.layered_graph import LayerStack
from hyper3.memory_base import _MemoryBase
from hyper3.results import FeedbackSummaryResult, TrainResult
from hyper3.retrieval_activation import ActivationResult, SpreadingActivation
from hyper3.retrieval_engine import FeedbackStore, RetrievalEngine


class RetrievalMixin(_MemoryBase):
    """Spreading activation, semantic retrieval, embedding management, and caching.

    Provides spreading activation (stimulate, spread, clear), semantic
    similarity search via pluggable embedding providers, FAISS-accelerated
    search, analogy queries, Reciprocal Rank Fusion retrieval with
    learning-to-rank feedback, Markov-model prefetching, hyperedge diffusion,
    and cross-operation feedback summaries.
    """

    def set_embedding_provider(self, provider: EmbeddingProvider) -> None:
        """Set a custom embedding provider for semantic similarity."""
        self._embedding_engine = EmbeddingEngine(self._graph, provider=provider)
        self._retrieval._embedding = self._embedding_engine

    def enable_faiss(self, *, nlist: int = 100, nprobe: int = 10, use_gpu: bool = False) -> bool:
        """Enable FAISS-based fast similarity search."""
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
            self._retrieval._embedding = self._embedding_engine
        result = self._embedding_engine.enable_faiss(nlist=nlist, nprobe=nprobe, use_gpu=use_gpu)
        self._log.record("enable_faiss", success=result)
        return result

    def analogy(self, a: str, b: str, c: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        """Perform vector-arithmetic analogy (a is to b as c is to ?)."""
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
        """Activate a concept with a given energy level."""
        result = self._activation.associative_recall(concept, energy=energy, top_k=top_k, iterations=iterations)
        self._log.record("activate", concept=concept, results=len(result))
        return result

    def clear_activations(self) -> None:
        """Clear all activation values."""
        self._activation.clear()

    def build_semantic_layer(self, *, top_k: int = 10, threshold: float = 0.7) -> int:
        """Build a semantic edge layer from embedding similarity.

        Creates a secondary graph with ``semantic_sim`` edges weighted by
        cosine similarity. Replaces the current activation engine with one
        that traverses both structural and semantic edges.

        Returns the number of semantic edges created.
        """
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
            self._retrieval._embedding = self._embedding_engine
        if self._semantic_builder is None:
            self._semantic_builder = SemanticEdgeBuilder(self._graph, self._embedding_engine)
        self._semantic_builder.build(top_k=top_k, threshold=threshold)
        layer = self._semantic_builder.layer
        assert layer is not None
        self._stack.register("semantic", layer, weight=1.0, derived=True)
        self._activation = SpreadingActivation(self._stack)  # type: ignore[arg-type]
        self._search_engine = None
        self._log.record("build_semantic_layer", edges=layer.edge_count)
        return layer.edge_count

    def semantic_layer_dirty(self) -> bool:
        """Return True if the semantic layer needs rebuilding."""
        return self._stack.layer_dirty("semantic")

    @property
    def semantic_layer(self) -> LayerStack:
        """Return the layer stack."""
        return self._stack

    def record_feedback(self, query: str, results: list, relevant_labels: set[str]) -> int:
        """Record relevance feedback for a retrieval result.

        Accepts both RetrievalResult and SearchHit objects.
        """
        count = self._retrieval.record_feedback(query, results, relevant_labels)
        self._log.record("feedback", query=query, relevant=len(relevant_labels), total=count)
        return count

    def train_retriever(self) -> TrainResult:
        """Train the retrieval ranker from collected feedback."""
        result = self._retrieval.train_from_feedback()
        self._log.record("train_retriever", trained=result.trained, samples=result.samples)
        return result

    @property
    def feedback(self) -> FeedbackStore:
        """Return the operation feedback tracker."""
        return self._retrieval.feedback

    @property
    def operation_feedback(self) -> OperationFeedback:
        """Lazily initialize and return the operation feedback engine."""
        return self._feedback

    def feedback_summary(self) -> FeedbackSummaryResult:
        """Return aggregate feedback across all operation types."""
        return self._feedback.cross_operation_summary()

    @property
    def retrieval(self) -> RetrievalEngine:
        """Lazily initialize and return the retrieval engine."""
        return self._retrieval

    @property
    def embedding_engine(self) -> EmbeddingEngine | None:
        """Lazily initialize and return the embedding engine."""
        return self._embedding_engine

    def enable_prefetch(self, enabled: bool = True) -> None:
        """Enable Markov-model prefetching for cache warming."""
        self._cache.enable_prefetch(enabled)

    def record_access(self, concept: str) -> None:
        """Record a concept access for prefetch training."""
        self._cache.record_access(f"store:{concept}")

    def predict_next_access(self, concept: str, *, top_k: int = 3) -> list[str]:
        """Predict the next concept likely to be accessed."""
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
        """Prefetch neighbors of a concept into the cache."""
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
        """Return the lazy cache instance."""
        return self._cache

    def spread_hyperedge(
        self,
        concept: str,
        *,
        energy: float = 1.0,
        mode: str = "linear",
        iterations: int | None = None,
    ) -> list[ActivationResult]:
        """Run hyperedge-aware spreading activation with gate modes."""
        node = self._find_node(concept)
        if not node:
            return []
        if self._activation is None:
            self._activation = SpreadingActivation(self._graph)
        self._activation.clear()
        self._activation.stimulate(node.id, energy)
        self._activation.spread_hyperedge(mode=mode, iterations=iterations)
        return self._activation.get_activated()
