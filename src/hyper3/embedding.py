from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np

from hyper3.kernel import Hypergraph


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Return a unit-normalized embedding vector for the given text."""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of embedding vectors produced by this provider."""
        ...

    def embed_node(self, node_id: str, text: str) -> np.ndarray:
        """Embed a graph node, optionally using its structural context.

        Args:
            node_id: Unique identifier of the node in the graph.
            text: Textual representation to embed (typically the node label).

        Returns:
            Unit-normalized embedding vector for the node.
        """
        return self.embed(text)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts and return as a stacked matrix.

        Args:
            texts: List of strings to embed.

        Returns:
            2-D array of shape ``(len(texts), dimension())``.
        """
        return np.array([self.embed(t) for t in texts])


class HashEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 64, seed: int = 42) -> None:
        """Initialize the hash-based embedding provider.

        Args:
            dim: Dimensionality of embedding vectors.
            seed: Base random seed; the actual seed per text is derived from its hash.
        """
        self._dim = dim
        self._rng_seed = seed

    def dimension(self) -> int:
        """Return the configured embedding dimensionality."""
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        """Produce a deterministic, unit-normalized vector from the text's hash."""
        seed = hash(text) % (2**31)
        rng = np.random.RandomState(seed)
        vec = rng.randn(self._dim).astype(np.float64)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec


@dataclass
class SimilarityResult:
    node_a_id: str
    node_b_id: str
    label_a: str
    label_b: str
    similarity: float
    embedding_distance: float


class EmbeddingEngine:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        provider: EmbeddingProvider | None = None,
        similarity_threshold: float = 0.7,
        cache_embeddings: bool = True,
    ) -> None:
        """Initialize the embedding engine.

        Args:
            graph: The hypergraph whose nodes will be embedded.
            provider: Embedding provider; defaults to ``HashEmbeddingProvider``.
            similarity_threshold: Default cosine-similarity cutoff for search.
            cache_embeddings: Whether to cache computed embeddings in memory.
        """
        self._graph = graph
        self._provider = provider or HashEmbeddingProvider()
        self._similarity_threshold = similarity_threshold
        self._cache_embeddings = cache_embeddings
        self._embedding_cache: dict[str, np.ndarray] = {}
        self._faiss_index: Any = None
        self._faiss_id_map: dict[int, str] = {}
        self._faiss_nlist: int = 100
        self._faiss_nprobe: int = 10
        self._faiss_use_gpu: bool = False

    @property
    def provider(self) -> EmbeddingProvider:
        """The embedding provider used by this engine."""
        return self._provider

    @property
    def dimension(self) -> int:
        """Dimensionality of the embedding vectors."""
        return self._provider.dimension()

    def get_embedding(self, node_id: str) -> np.ndarray | None:
        """Compute or retrieve the cached embedding for a node.

        Args:
            node_id: ID of the target node.

        Returns:
            Unit-normalized embedding vector, or ``None`` if the node does not exist.
        """
        node = self._graph.get_node(node_id)
        if not node:
            return None
        if self._cache_embeddings and node_id in self._embedding_cache:
            return self._embedding_cache[node_id]
        text = node.label if node.label else str(node.data) if node.data is not None else node.id
        emb = self._provider.embed_node(node_id, text)
        if self._cache_embeddings:
            self._embedding_cache[node_id] = emb
        return emb

    def compute_similarity(self, node_a_id: str, node_b_id: str) -> float:
        """Compute the cosine similarity between two nodes' embeddings.

        Args:
            node_a_id: ID of the first node.
            node_b_id: ID of the second node.

        Returns:
            Cosine similarity in ``[-1, 1]``, or ``0.0`` if either node is missing.
        """
        emb_a = self.get_embedding(node_a_id)
        emb_b = self.get_embedding(node_b_id)
        if emb_a is None or emb_b is None:
            return 0.0
        return float(np.dot(emb_a, emb_b))

    def compute_distance(self, node_a_id: str, node_b_id: str) -> float:
        """Compute the Euclidean distance between two nodes' embeddings.

        Args:
            node_a_id: ID of the first node.
            node_b_id: ID of the second node.

        Returns:
            L2 distance, or ``float('inf')`` if either node is missing.
        """
        emb_a = self.get_embedding(node_a_id)
        emb_b = self.get_embedding(node_b_id)
        if emb_a is None or emb_b is None:
            return float("inf")
        return float(np.linalg.norm(emb_a - emb_b))

    def find_similar(
        self, node_id: str, *, top_k: int = 10, threshold: float | None = None
    ) -> list[SimilarityResult]:
        """Find nodes most similar to the given node by cosine similarity.

        Args:
            node_id: ID of the query node.
            top_k: Maximum number of results to return.
            threshold: Override the default similarity threshold. ``None`` uses
                the engine-level default.

        Returns:
            List of :class:`SimilarityResult` sorted by descending similarity.
        """
        target_emb = self.get_embedding(node_id)
        if target_emb is None:
            return []
        effective_threshold = threshold if threshold is not None else self._similarity_threshold
        target_node = self._graph.get_node(node_id)
        target_label = target_node.label if target_node else ""
        if self._faiss_index is not None:
            return self._find_similar_faiss(node_id, target_emb, target_label, top_k, effective_threshold)
        candidates: list[SimilarityResult] = []
        for node in self._graph.nodes:
            if node.id == node_id:
                continue
            emb = self.get_embedding(node.id)
            if emb is None:
                continue
            sim = float(np.dot(target_emb, emb))
            if sim >= effective_threshold:
                dist = float(np.linalg.norm(target_emb - emb))
                candidates.append(
                    SimilarityResult(
                        node_a_id=node_id,
                        node_b_id=node.id,
                        label_a=target_label,
                        label_b=node.label,
                        similarity=sim,
                        embedding_distance=dist,
                    )
                )
        candidates.sort(key=lambda r: r.similarity, reverse=True)
        return candidates[:top_k]

    def _find_similar_faiss(
        self,
        node_id: str,
        target_emb: np.ndarray,
        target_label: str,
        top_k: int,
        threshold: float,
    ) -> list[SimilarityResult]:
        """Execute a similarity search using the FAISS index.

        Args:
            node_id: ID of the query node.
            target_emb: Precomputed embedding of the query node.
            target_label: Label of the query node for result metadata.
            top_k: Maximum number of results.
            threshold: Minimum similarity score.

        Returns:
            Filtered and sorted list of :class:`SimilarityResult`.
        """
        hits = self._faiss_search(target_emb, top_k)
        results: list[SimilarityResult] = []
        for hit_id, sim in hits:
            if hit_id == node_id:
                continue
            if sim < threshold:
                continue
            node = self._graph.get_node(hit_id)
            if not node:
                continue
            dist = float(np.linalg.norm(target_emb - self.get_embedding(hit_id)))
            results.append(
                SimilarityResult(
                    node_a_id=node_id,
                    node_b_id=hit_id,
                    label_a=target_label,
                    label_b=node.label,
                    similarity=sim,
                    embedding_distance=dist,
                )
            )
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:top_k]

    def find_all_similar_pairs(
        self, *, threshold: float | None = None
    ) -> list[SimilarityResult]:
        """Find all node pairs whose similarity meets the threshold.

        Args:
            threshold: Override the default similarity threshold. ``None`` uses
                the engine-level default.

        Returns:
            List of :class:`SimilarityResult` for every qualifying pair,
            sorted by descending similarity.
        """
        effective_threshold = threshold if threshold is not None else self._similarity_threshold
        all_nodes = self._graph.nodes
        if not all_nodes:
            return []
        ids = [n.id for n in all_nodes]
        labels = [n.label for n in all_nodes]
        embeddings = []
        for nid in ids:
            emb = self.get_embedding(nid)
            if emb is None:
                emb = np.zeros(self._provider.dimension())
            embeddings.append(emb)
        mat = np.array(embeddings)
        sim_matrix = mat @ mat.T
        results: list[SimilarityResult] = []
        n = len(ids)
        for i in range(n):
            for j in range(i + 1, n):
                if sim_matrix[i, j] >= effective_threshold:
                    dist = float(np.linalg.norm(mat[i] - mat[j]))
                    results.append(
                        SimilarityResult(
                            node_a_id=ids[i],
                            node_b_id=ids[j],
                            label_a=labels[i],
                            label_b=labels[j],
                            similarity=float(sim_matrix[i, j]),
                            embedding_distance=dist,
                        )
                    )
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results

    def analogy(
        self, a: str, b: str, c: str, *, top_k: int = 5
    ) -> list[tuple[str, float]]:
        """Solve a word-analogy task: "a is to b as c is to ?".

        Computes the target vector as ``emb(c) + emb(b) - emb(a)`` and returns
        the closest nodes by cosine similarity.

        Args:
            a: Node ID playing the "a" role.
            b: Node ID playing the "b" role.
            c: Node ID playing the "c" role.
            top_k: Maximum number of results.

        Returns:
            List of ``(node_id, similarity)`` tuples sorted by descending
            similarity, excluding ``a``, ``b``, and ``c``.
        """
        emb_a = self.get_embedding(a)
        emb_b = self.get_embedding(b)
        emb_c = self.get_embedding(c)
        if emb_a is None or emb_b is None or emb_c is None:
            return []
        target = emb_c + emb_b - emb_a
        target_norm = np.linalg.norm(target)
        if target_norm > 0:
            target = target / target_norm
        exclude = {a, b, c}
        candidates: list[tuple[str, float]] = []
        for node in self._graph.nodes:
            if node.id in exclude:
                continue
            emb = self.get_embedding(node.id)
            if emb is None:
                continue
            sim = float(np.dot(target, emb))
            candidates.append((node.id, sim))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def invalidate_cache(self) -> None:
        """Clear the embedding cache and release any FAISS index."""
        self._embedding_cache.clear()
        self._faiss_index = None
        self._faiss_id_map = {}

    def precompute_all(self) -> int:
        """Compute embeddings for all graph nodes that are not yet cached.

        Returns:
            The number of newly computed embeddings.
        """
        count = 0
        for node in self._graph.nodes:
            if node.id not in self._embedding_cache:
                self.get_embedding(node.id)
                count += 1
        if self._faiss_index is not None:
            self._faiss_index = None
            self._faiss_id_map = {}
        return count

    def enable_faiss(self, *, nlist: int = 100, nprobe: int = 10, use_gpu: bool = False) -> bool:
        """Enable FAISS-accelerated similarity search.

        Args:
            nlist: Number of IVF cells (used when the graph has >= 1000 nodes).
            nprobe: Number of cells to probe at query time.
            use_gpu: Whether to move the index to GPU.

        Returns:
            ``True`` if FAISS was successfully enabled, ``False`` if the
            ``faiss`` package is not installed.
        """
        try:
            import faiss  # type: ignore[import-untyped]
        except ImportError:
            return False
        self._faiss_nlist = nlist
        self._faiss_nprobe = nprobe
        self._faiss_use_gpu = use_gpu
        self._faiss_index = None
        self._build_faiss_index()
        return True

    def _build_faiss_index(self) -> None:
        """Build (or rebuild) the FAISS index from current graph embeddings.

        Uses ``IndexFlatIP`` for graphs with fewer than 1000 nodes and
        ``IndexIVFFlat`` otherwise.
        """
        try:
            import faiss  # type: ignore[import-untyped]
        except ImportError:
            return
        nodes = self._graph.nodes
        dim = self._provider.dimension()
        if len(nodes) == 0:
            self._faiss_index = faiss.IndexFlatIP(dim)
            self._faiss_id_map = {}
            return
        ids = [n.id for n in nodes]
        embeddings = []
        for nid in ids:
            emb = self.get_embedding(nid)
            if emb is None:
                emb = np.zeros(dim)
            embeddings.append(emb)
        mat = np.array(embeddings, dtype=np.float32)
        nlist = min(self._faiss_nlist, len(nodes))
        if len(nodes) < 1000:
            index = faiss.IndexFlatIP(dim)
        else:
            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
            index.train(mat)
            index.nprobe = self._faiss_nprobe
        index.add(mat)
        self._faiss_index = index
        self._faiss_id_map: dict[int, str] = {i: nid for i, nid in enumerate(ids)}

    def _faiss_search(self, query_vec: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        """Search the FAISS index for the nearest neighbors of a query vector.

        Args:
            query_vec: Query embedding vector.
            top_k: Number of nearest neighbors to retrieve.

        Returns:
            List of ``(node_id, inner_product_score)`` tuples.
        """
        if self._faiss_index is None or self._faiss_index.ntotal == 0:
            return []
        q = query_vec.astype(np.float32).reshape(1, -1)
        distances, indices = self._faiss_index.search(q, min(top_k + 1, self._faiss_index.ntotal))
        results: list[tuple[str, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            results.append((self._faiss_id_map[idx], float(dist)))
        return results

    def add_to_faiss_index(self, node_id: str) -> bool:
        """Incrementally add a single node to the existing FAISS index.

        Args:
            node_id: ID of the node to add.

        Returns:
            ``True`` if the node was added, ``False`` if no index exists or
            the node could not be embedded.
        """
        if self._faiss_index is None:
            return False
        emb = self.get_embedding(node_id)
        if emb is None:
            return False
        vec = emb.astype(np.float32).reshape(1, -1)
        idx = self._faiss_index.ntotal
        self._faiss_index.add(vec)
        self._faiss_id_map[idx] = node_id
        return True
