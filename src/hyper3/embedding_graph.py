from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from hyper3.embedding import EmbeddingProvider
from hyper3.kernel import Hypergraph


class RandomWalkEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        graph: Hypergraph,
        *,
        dim: int = 64,
        walk_length: int = 30,
        num_walks: int = 10,
        window_size: int = 5,
        neg_samples: int = 5,
        learning_rate: float = 0.025,
        epochs: int = 5,
        seed: int = 42,
    ) -> None:
        self._graph = graph
        self._dim = dim
        self._walk_length = walk_length
        self._num_walks = num_walks
        self._window_size = window_size
        self._neg_samples = neg_samples
        self._learning_rate = learning_rate
        self._epochs = epochs
        self._rng = np.random.RandomState(seed)
        self._embeddings: dict[str, np.ndarray] = {}
        self._dirty: set[str] = set()
        self._trained = False
        self._node_list: list[str] = []
        self._neg_sampling_probs: np.ndarray | None = None

    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        return np.zeros(self._dim)

    def embed_node(self, node_id: str, text: str) -> np.ndarray:
        if not self._trained or node_id in self._dirty:
            self._train()
        return self._embeddings.get(node_id, np.zeros(self._dim))

    def mark_dirty(self, node_ids: set[str] | None = None) -> None:
        if node_ids is None:
            self._dirty = set(self._embeddings.keys())
            self._trained = False
        else:
            self._dirty.update(node_ids)

    def retrain(self) -> None:
        self._trained = False
        self._embeddings.clear()
        self._dirty.clear()
        self._train()

    def _train(self) -> None:
        nodes = list(self._graph.nodes)
        if len(nodes) < 2:
            for n in nodes:
                self._embeddings[n.id] = self._rng.randn(self._dim).astype(np.float64)
                norm = np.linalg.norm(self._embeddings[n.id])
                if norm > 0:
                    self._embeddings[n.id] /= norm
            self._trained = True
            self._dirty.clear()
            return

        self._node_list = [n.id for n in nodes]
        node_idx = {nid: i for i, nid in enumerate(self._node_list)}
        n_nodes = len(self._node_list)

        degree_counts = np.ones(n_nodes, dtype=np.float64)
        for node in nodes:
            degree = len(self._graph.edges_for(node.id))
            degree_counts[node_idx[node.id]] = max(degree, 1)
        self._neg_sampling_probs = degree_counts ** 0.75
        self._neg_sampling_probs /= self._neg_sampling_probs.sum()

        w_in: dict[int, np.ndarray] = {}
        w_out: dict[int, np.ndarray] = {}
        scale = (2.0 / self._dim) ** 0.5
        for idx in range(n_nodes):
            w_in[idx] = self._rng.randn(self._dim).astype(np.float64) * scale
            w_out[idx] = np.zeros(self._dim, dtype=np.float64)

        walks = self._generate_walks()

        for _epoch in range(self._epochs):
            lr = self._learning_rate * (1.0 - _epoch / self._epochs)
            lr = max(lr, self._learning_rate * 0.01)
            self._rng.shuffle(walks)
            for walk in walks:
                indices = [node_idx[nid] for nid in walk if nid in node_idx]
                for pos, target_idx in enumerate(indices):
                    win_start = max(0, pos - self._window_size)
                    win_end = min(len(indices), pos + self._window_size + 1)
                    for ctx_pos in range(win_start, win_end):
                        if ctx_pos == pos:
                            continue
                        ctx_idx = indices[ctx_pos]
                        self._sgns_update(
                            w_in, w_out, target_idx, ctx_idx,
                            n_nodes, lr,
                        )

        for idx, nid in enumerate(self._node_list):
            vec = w_in[idx].copy()
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            self._embeddings[nid] = vec

        self._trained = True
        self._dirty.clear()

    def _generate_walks(self) -> list[list[str]]:
        walks: list[list[str]] = []
        nodes = list(self._graph.nodes)
        for _ in range(self._num_walks):
            indices = list(range(len(nodes)))
            self._rng.shuffle(indices)
            for idx in indices:
                node = nodes[idx]
                walk = self._single_walk(node.id, self._walk_length)
                if len(walk) > 1:
                    walks.append(walk)
        return walks

    def _single_walk(self, start_id: str, length: int) -> list[str]:
        walk = [start_id]
        current = start_id
        for _ in range(length - 1):
            edges = self._graph.edges_for(current)
            if not edges:
                break
            edge = edges[self._rng.randint(len(edges))]
            if current in edge.source_ids:
                candidates = list(edge.target_ids)
            elif current in edge.target_ids:
                candidates = list(edge.source_ids)
            else:
                candidates = list(edge.node_ids - {current})
            if not candidates:
                break
            next_id = candidates[self._rng.randint(len(candidates))]
            walk.append(next_id)
            current = next_id
        return walk

    def _sgns_update(
        self,
        w_in: dict[int, np.ndarray],
        w_out: dict[int, np.ndarray],
        target_idx: int,
        context_idx: int,
        n_nodes: int,
        lr: float,
    ) -> None:
        target_vec = w_in[target_idx].copy()
        neu1e = np.zeros_like(target_vec)

        dot = float(np.dot(target_vec, w_out[context_idx]))
        dot = max(-6.0, min(6.0, dot))
        sig = 1.0 / (1.0 + np.exp(-dot))
        g = (1.0 - sig) * lr
        neu1e += g * w_out[context_idx]
        w_out[context_idx] = w_out[context_idx] + g * target_vec

        neg_indices = self._rng.choice(
            n_nodes, size=self._neg_samples,
            p=self._neg_sampling_probs,
        )
        for neg_idx in neg_indices:
            if neg_idx == context_idx:
                continue
            neg_idx = int(neg_idx)
            dot_neg = float(np.dot(target_vec, w_out[neg_idx]))
            dot_neg = max(-6.0, min(6.0, dot_neg))
            sig_neg = 1.0 / (1.0 + np.exp(-dot_neg))
            g_neg = -sig_neg * lr
            neu1e += g_neg * w_out[neg_idx]
            w_out[neg_idx] = w_out[neg_idx] + g_neg * target_vec

        w_in[target_idx] = target_vec + neu1e


class NeighborhoodFingerprintProvider(EmbeddingProvider):
    def __init__(
        self,
        graph: Hypergraph,
        *,
        dim: int = 64,
        seed: int = 42,
    ) -> None:
        self._graph = graph
        self._dim = dim
        self._rng = np.random.RandomState(seed)
        self._cache: dict[str, np.ndarray] = {}
        self._label_weights: dict[str, float] = {}
        self._idf_cache: dict[str, float] = {}
        self._projection: np.ndarray | None = None
        self._projection = self._rng.randn(1024, self._dim).astype(np.float64) / (1024 ** 0.5)

    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        return np.zeros(self._dim)

    def embed_node(self, node_id: str, text: str) -> np.ndarray:
        if node_id in self._cache:
            return self._cache[node_id]
        vec = self._compute_fingerprint(node_id)
        self._cache[node_id] = vec
        return vec

    def invalidate(self, node_ids: set[str] | None = None) -> None:
        if node_ids is None:
            self._cache.clear()
            self._label_weights.clear()
            self._idf_cache.clear()
        else:
            for nid in node_ids:
                self._cache.pop(nid, None)
            self._idf_cache.clear()

    def _compute_fingerprint(self, node_id: str) -> np.ndarray:
        self._ensure_idf()
        sparse = np.zeros(1024, dtype=np.float64)

        edges = self._graph.edges_for(node_id)
        for edge in edges:
            is_source = node_id in edge.source_ids
            direction = 1.0 if is_source else -1.0
            label_idf = self._idf_cache.get(edge.label, 1.0)
            feature_idx = self._hash_feature(edge.label, "outgoing" if is_source else "incoming")
            sparse[feature_idx] += direction * edge.weight * label_idf

            if is_source:
                for tid in edge.target_ids:
                    tn = self._graph.get_node(tid)
                    if tn:
                        neighbor_feat = self._hash_feature(f"neighbor:{tn.label}", "1hop")
                        sparse[neighbor_feat] += edge.weight * 0.5
            else:
                for sid in edge.source_ids:
                    sn = self._graph.get_node(sid)
                    if sn:
                        neighbor_feat = self._hash_feature(f"neighbor:{sn.label}", "1hop")
                        sparse[neighbor_feat] += edge.weight * 0.5

        two_hop_edges: list[Any] = []
        for edge in edges:
            if node_id in edge.source_ids:
                neighbors = edge.target_ids
            else:
                neighbors = edge.source_ids
            for nid in neighbors:
                for e2 in self._graph.edges_for(nid):
                    if e2.id != edge.id:
                        two_hop_edges.append(e2)

        for e2 in two_hop_edges:
            label_idf = self._idf_cache.get(e2.label, 1.0)
            feature_idx = self._hash_feature(e2.label, "2hop")
            sparse[feature_idx] += e2.weight * label_idf * 0.3

        node = self._graph.get_node(node_id)
        if node:
            for tag in node.metadata.modality_tags:
                tag_feat = self._hash_feature(f"modality:{tag.value}", "meta")
                sparse[tag_feat] += 1.0
            if node.metadata.abstraction_layer:
                layer_feat = self._hash_feature(
                    f"layer:{node.metadata.abstraction_layer.value}", "meta"
                )
                sparse[layer_feat] += 1.0

        if self._projection is not None:
            result = sparse @ self._projection
        else:
            result = sparse[: self._dim]

        norm = np.linalg.norm(result)
        if norm > 0:
            result /= norm
        return result

    def _hash_feature(self, feature: str, category: str) -> int:
        h = int(hashlib.md5(f"{category}:{feature}".encode()).hexdigest(), 16) % (2**31)
        rng = np.random.RandomState(h)
        return int(rng.randint(0, 1024))

    def _ensure_idf(self) -> None:
        if self._idf_cache:
            return
        label_doc_count: dict[str, int] = {}
        n_nodes = self._graph.node_count
        if n_nodes == 0:
            return
        for node in self._graph.nodes:
            seen_labels: set[str] = set()
            for edge in self._graph.edges_for(node.id):
                if edge.label not in seen_labels:
                    label_doc_count[edge.label] = label_doc_count.get(edge.label, 0) + 1
                    seen_labels.add(edge.label)
        for label, count in label_doc_count.items():
            self._idf_cache[label] = np.log(n_nodes / (1 + count)) + 1.0


class CompositeEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        providers: list[EmbeddingProvider],
        *,
        weights: list[float] | None = None,
        target_dim: int | None = None,
        graph: Hypergraph | None = None,
    ) -> None:
        self._providers = providers
        self._weights = weights or [1.0] * len(providers)
        total_w = sum(self._weights)
        self._weights = [w / total_w for w in self._weights]
        self._target_dim = target_dim
        self._projection: np.ndarray | None = None
        self._graph = graph
        if not providers:
            self._total_dim = 0
        else:
            self._total_dim = sum(p.dimension() for p in providers)

    def dimension(self) -> int:
        if self._target_dim is not None:
            return self._target_dim
        return self._total_dim if self._total_dim > 0 else 64

    def embed(self, text: str) -> np.ndarray:
        parts: list[np.ndarray] = []
        for provider, weight in zip(self._providers, self._weights):
            vec = provider.embed(text)
            parts.append(vec * weight)
        if not parts:
            return np.zeros(self.dimension())
        combined = np.concatenate(parts)
        if self._projection is not None:
            combined = combined @ self._projection
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm
        return combined

    def embed_node(self, node_id: str, text: str) -> np.ndarray:
        parts: list[np.ndarray] = []
        for provider, weight in zip(self._providers, self._weights):
            if hasattr(provider, "embed_node"):
                vec = provider.embed_node(node_id, text)
            else:
                vec = provider.embed(text)
            parts.append(vec * weight)
        if not parts:
            return np.zeros(self.dimension())
        combined = np.concatenate(parts)
        if self._projection is not None:
            combined = combined @ self._projection
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm
        return combined

    def fit_projection(self, node_ids: list[str] | None = None) -> None:
        if self._target_dim is None or self._target_dim >= self._total_dim:
            return
        graph = self._graph
        if graph is None:
            return
        ids = node_ids or [n.id for n in graph.nodes]
        if len(ids) < self._target_dim:
            return
        matrix: list[np.ndarray] = []
        for nid in ids:
            node = graph.get_node(nid)
            label = node.label if node else ""
            parts: list[np.ndarray] = []
            for provider, weight in zip(self._providers, self._weights):
                if hasattr(provider, "embed_node"):
                    vec = provider.embed_node(nid, label)
                else:
                    vec = provider.embed(label)
                parts.append(vec * weight)
            matrix.append(np.concatenate(parts))
        mat = np.array(matrix)
        centered = mat - mat.mean(axis=0)
        cov = centered.T @ centered / max(len(centered) - 1, 1)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        top_indices = np.argsort(eigenvalues)[::-1][: self._target_dim]
        self._projection = eigenvectors[:, top_indices]
