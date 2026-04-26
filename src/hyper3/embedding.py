from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np

from hyper3.kernel import Hypergraph


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        ...

    @abstractmethod
    def dimension(self) -> int:
        ...

    def embed_node(self, node_id: str, text: str) -> np.ndarray:
        return self.embed(text)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return np.array([self.embed(t) for t in texts])


class HashEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 64, seed: int = 42) -> None:
        self._dim = dim
        self._rng_seed = seed

    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> np.ndarray:
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
        return self._provider

    @property
    def dimension(self) -> int:
        return self._provider.dimension()

    def get_embedding(self, node_id: str) -> np.ndarray | None:
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
        emb_a = self.get_embedding(node_a_id)
        emb_b = self.get_embedding(node_b_id)
        if emb_a is None or emb_b is None:
            return 0.0
        return float(np.dot(emb_a, emb_b))

    def compute_distance(self, node_a_id: str, node_b_id: str) -> float:
        emb_a = self.get_embedding(node_a_id)
        emb_b = self.get_embedding(node_b_id)
        if emb_a is None or emb_b is None:
            return float("inf")
        return float(np.linalg.norm(emb_a - emb_b))

    def find_similar(
        self, node_id: str, *, top_k: int = 10, threshold: float | None = None
    ) -> list[SimilarityResult]:
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
        self._embedding_cache.clear()
        self._faiss_index = None
        self._faiss_id_map = {}

    def precompute_all(self) -> int:
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
