from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from hyper3.embedding import EmbeddingProvider
from hyper3.kernel import Hypergraph


class RandomWalkEmbeddingProvider(EmbeddingProvider):
    """Node2Vec-style skip-gram embedding provider that learns vectors from random walks over graph structure."""

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
        """Initialize the random-walk embedding provider.

        Args:
            graph: The hypergraph to learn embeddings from.
            dim: Dimensionality of the embedding vectors.
            walk_length: Number of steps per random walk.
            num_walks: Number of walks to generate per node.
            window_size: Skip-gram context window size.
            neg_samples: Number of negative samples per positive pair.
            learning_rate: Initial learning rate for SGD.
            epochs: Number of training passes over all walks.
            seed: Random seed for reproducibility.
        """
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
        """Return the configured embedding dimensionality."""
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        """Return a zero vector; this provider requires graph structure, not text."""
        return np.zeros(self._dim)

    def embed_node(self, node_id: str, text: str) -> np.ndarray:
        """Return the learned embedding for a node, retraining if necessary.

        Args:
            node_id: ID of the node in the graph.
            text: Ignored; the embedding is derived from graph structure.

        Returns:
            Unit-normalized embedding vector for the node.
        """
        if not self._trained or node_id in self._dirty:
            self._train()
        return self._embeddings.get(node_id, np.zeros(self._dim))

    def mark_dirty(self, node_ids: set[str] | None = None) -> None:
        """Mark nodes as needing re-embedding.

        Args:
            node_ids: Set of node IDs to retrain. ``None`` marks all nodes
                and forces a full retrain on next access.
        """
        if node_ids is None:
            self._dirty = set(self._embeddings.keys())
            self._trained = False
        else:
            self._dirty.update(node_ids)

    def retrain(self) -> None:
        """Discard all embeddings and retrain from scratch."""
        self._trained = False
        self._embeddings.clear()
        self._dirty.clear()
        self._train()

    def _train(self) -> None:
        """Run the Node2Vec-style training loop.

        Generates random walks, then optimizes skip-gram with negative
        sampling (SGNS) over all walks for the configured number of epochs.
        """
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

        self._init_neg_sampling_probs(nodes, node_idx, n_nodes)
        w_in, w_out = self._init_weights(n_nodes)

        walks = self._generate_walks()
        self._run_epochs(w_in, w_out, walks, node_idx, n_nodes)
        self._finalize_embeddings(w_in)

        self._trained = True
        self._dirty.clear()

    def _init_neg_sampling_probs(
        self,
        nodes: list[Any],
        node_idx: dict[str, int],
        n_nodes: int,
    ) -> None:
        """Initialize negative sampling probability distribution."""
        degree_counts = np.ones(n_nodes, dtype=np.float64)
        for node in nodes:
            degree = len(self._graph.incident_edges(node.id))
            degree_counts[node_idx[node.id]] = max(degree, 1)
        self._neg_sampling_probs = degree_counts**0.75
        self._neg_sampling_probs /= self._neg_sampling_probs.sum()

    def _init_weights(
        self, n_nodes: int
    ) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
        """Initialize embedding weight matrices."""
        w_in: dict[int, np.ndarray] = {}
        w_out: dict[int, np.ndarray] = {}
        scale = (2.0 / self._dim) ** 0.5
        for idx in range(n_nodes):
            w_in[idx] = self._rng.randn(self._dim).astype(np.float64) * scale
            w_out[idx] = np.zeros(self._dim, dtype=np.float64)
        return w_in, w_out

    def _run_epochs(
        self,
        w_in: dict[int, np.ndarray],
        w_out: dict[int, np.ndarray],
        walks: list[list[str]],
        node_idx: dict[str, int],
        n_nodes: int,
    ) -> None:
        """Run training epochs of skip-gram with negative sampling."""
        for _epoch in range(self._epochs):
            lr = self._learning_rate * (1.0 - _epoch / self._epochs)
            lr = max(lr, self._learning_rate * 0.01)
            self._rng.shuffle(walks)
            for walk in walks:
                indices = [node_idx[nid] for nid in walk if nid in node_idx]
                self._process_walk(w_in, w_out, indices, n_nodes, lr)

    def _process_walk(
        self,
        w_in: dict[int, np.ndarray],
        w_out: dict[int, np.ndarray],
        indices: list[int],
        n_nodes: int,
        lr: float,
    ) -> None:
        """Process a single random walk for skip-gram training."""
        for pos, target_idx in enumerate(indices):
            win_start = max(0, pos - self._window_size)
            win_end = min(len(indices), pos + self._window_size + 1)
            for ctx_pos in range(win_start, win_end):
                if ctx_pos == pos:
                    continue
                ctx_idx = indices[ctx_pos]
                self._sgns_update(
                    w_in,
                    w_out,
                    target_idx,
                    ctx_idx,
                    n_nodes,
                    lr,
                )

    def _finalize_embeddings(self, w_in: dict[int, np.ndarray]) -> None:
        """Average context and target embeddings into final vectors."""
        for idx, nid in enumerate(self._node_list):
            vec = w_in[idx].copy()
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            self._embeddings[nid] = vec

    def _generate_walks(self) -> list[list[str]]:
        """Generate random walks starting from every node.

        Returns:
            List of walks, where each walk is a list of node IDs.
        """
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
        """Perform a single random walk from the given start node.

        Args:
            start_id: ID of the node to start from.
            length: Maximum number of steps in the walk.

        Returns:
            List of node IDs visited during the walk.
        """
        walk = [start_id]
        current = start_id
        for _ in range(length - 1):
            edges = self._graph.incident_edges(current)
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
        """Perform a single skip-gram with negative sampling (SGNS) update.

        Args:
            w_in: Input (target) weight vectors keyed by node index.
            w_out: Output (context) weight vectors keyed by node index.
            target_idx: Index of the target (center) node.
            context_idx: Index of the positive context node.
            n_nodes: Total number of nodes (for negative sampling).
            lr: Current learning rate.
        """
        target_vec = w_in[target_idx].copy()
        neu1e = np.zeros_like(target_vec)

        dot = float(np.dot(target_vec, w_out[context_idx]))
        dot = max(-6.0, min(6.0, dot))
        sig = 1.0 / (1.0 + np.exp(-dot))
        g = (1.0 - sig) * lr
        neu1e += g * w_out[context_idx]
        w_out[context_idx] = w_out[context_idx] + g * target_vec

        neg_indices = self._rng.choice(
            n_nodes,
            size=self._neg_samples,
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
    """TF-IDF-weighted neighborhood fingerprint provider using 1-hop/2-hop edge labels and random projection."""

    def __init__(
        self,
        graph: Hypergraph,
        *,
        dim: int = 64,
        seed: int = 42,
    ) -> None:
        """Initialize the neighborhood fingerprint embedding provider.

        Args:
            graph: The hypergraph whose structure determines embeddings.
            dim: Dimensionality of the output embedding vectors.
            seed: Random seed for the random projection matrix.
        """
        self._graph = graph
        self._dim = dim
        self._rng = np.random.RandomState(seed)
        self._cache: dict[str, np.ndarray] = {}
        self._label_weights: dict[str, float] = {}
        self._idf_cache: dict[str, float] = {}
        self._projection: np.ndarray | None = None
        self._projection = self._rng.randn(1024, self._dim).astype(np.float64) / (1024**0.5)

    def dimension(self) -> int:
        """Return the configured embedding dimensionality."""
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        """Return a zero vector; this provider requires graph structure, not text."""
        return np.zeros(self._dim)

    def embed_node(self, node_id: str, text: str) -> np.ndarray:
        """Compute a TF-IDF-weighted neighborhood fingerprint for a node.

        Args:
            node_id: ID of the node in the graph.
            text: Ignored; the embedding is derived from graph structure.

        Returns:
            Unit-normalized embedding vector for the node.
        """
        if node_id in self._cache:
            return self._cache[node_id]
        vec = self._compute_fingerprint(node_id)
        self._cache[node_id] = vec
        return vec

    def invalidate(self, node_ids: set[str] | None = None) -> None:
        """Clear cached fingerprints so they are recomputed on next access.

        Args:
            node_ids: Specific nodes to invalidate. ``None`` clears all caches.
        """
        if node_ids is None:
            self._cache.clear()
            self._label_weights.clear()
            self._idf_cache.clear()
        else:
            for nid in node_ids:
                self._cache.pop(nid, None)
            self._idf_cache.clear()

    def _compute_fingerprint(self, node_id: str) -> np.ndarray:
        """Build a sparse structural fingerprint and project it to the target dimension.

        The fingerprint encodes 1-hop and 2-hop edge labels with TF-IDF
        weighting, directionality, and node metadata tags, then applies a
        random projection to the target dimension.

        Args:
            node_id: ID of the node to fingerprint.

        Returns:
            Unit-normalized embedding vector.
        """
        self._ensure_idf()
        sparse = np.zeros(1024, dtype=np.float64)

        edges = self._graph.incident_edges(node_id)
        self._accumulate_1hop_features(sparse, edges, node_id)
        self._accumulate_2hop_features(sparse, edges, node_id)
        self._accumulate_node_metadata(sparse, node_id)

        result = sparse @ self._projection if self._projection is not None else sparse[: self._dim]

        norm = np.linalg.norm(result)
        if norm > 0:
            result /= norm
        return result

    def _accumulate_1hop_features(
        self,
        sparse: np.ndarray,
        edges: list[Any],
        node_id: str,
    ) -> None:
        """Accumulate 1-hop edge label features into the fingerprint."""
        for edge in edges:
            is_source = node_id in edge.source_ids
            direction = 1.0 if is_source else -1.0
            label_idf = self._idf_cache.get(edge.label, 1.0)
            feature_idx = self._hash_feature(edge.label, "outgoing" if is_source else "incoming")
            sparse[feature_idx] += direction * edge.weight * label_idf

            peer_ids = edge.target_ids if is_source else edge.source_ids
            for pid in peer_ids:
                peer = self._graph.get_node(pid)
                if peer:
                    neighbor_feat = self._hash_feature(f"neighbor:{peer.label}", "1hop")
                    sparse[neighbor_feat] += edge.weight * 0.5

    def _accumulate_2hop_features(
        self,
        sparse: np.ndarray,
        edges: list[Any],
        node_id: str,
    ) -> None:
        """Accumulate 2-hop edge label features into the fingerprint."""
        two_hop_edges: list[Any] = []
        for edge in edges:
            neighbors = edge.target_ids if node_id in edge.source_ids else edge.source_ids
            two_hop_edges.extend(
                e2
                for nid in neighbors
                for e2 in self._graph.incident_edges(nid)
                if e2.id != edge.id
            )

        for e2 in two_hop_edges:
            label_idf = self._idf_cache.get(e2.label, 1.0)
            feature_idx = self._hash_feature(e2.label, "2hop")
            sparse[feature_idx] += e2.weight * label_idf * 0.3

    def _accumulate_node_metadata(
        self,
        sparse: np.ndarray,
        node_id: str,
    ) -> None:
        """Accumulate node metadata features into the fingerprint."""
        node = self._graph.get_node(node_id)
        if not node:
            return
        for tag in node.metadata.modality_tags:
            tag_feat = self._hash_feature(f"modality:{tag.value}", "meta")
            sparse[tag_feat] += 1.0
        if node.metadata.abstraction_layer:
            layer_feat = self._hash_feature(f"layer:{node.metadata.abstraction_layer.value}", "meta")
            sparse[layer_feat] += 1.0

    def _hash_feature(self, feature: str, category: str) -> int:
        """Deterministically map a feature string and category to a sparse bucket index.

        Args:
            feature: Feature description string.
            category: Category namespace for the feature.

        Returns:
            Integer index in ``[0, 1024)``.
        """
        h = int(hashlib.md5(f"{category}:{feature}".encode()).hexdigest(), 16) % (2**31)
        rng = np.random.RandomState(h)
        return int(rng.randint(0, 1024))

    def _ensure_idf(self) -> None:
        """Compute and cache inverse-document-frequency weights for edge labels.

        IDF is computed as ``log(N / (1 + doc_count)) + 1.0`` where *N* is the
        total number of nodes and *doc_count* is the number of nodes incident
        to at least one edge with the given label.
        """
        if self._idf_cache:
            return
        label_doc_count: dict[str, int] = {}
        n_nodes = self._graph.node_count
        if n_nodes == 0:
            return
        for node in self._graph.nodes:
            seen_labels: set[str] = set()
            for edge in self._graph.incident_edges(node.id):
                if edge.label not in seen_labels:
                    label_doc_count[edge.label] = label_doc_count.get(edge.label, 0) + 1
                    seen_labels.add(edge.label)
        for label, count in label_doc_count.items():
            self._idf_cache[label] = np.log(n_nodes / (1 + count)) + 1.0


class CompositeEmbeddingProvider(EmbeddingProvider):
    """Combines multiple embedding providers via weighted concatenation with optional PCA dimensionality reduction."""

    def __init__(
        self,
        providers: list[EmbeddingProvider],
        *,
        weights: list[float] | None = None,
        target_dim: int | None = None,
        graph: Hypergraph | None = None,
    ) -> None:
        """Initialize the composite embedding provider.

        Args:
            providers: Ordered list of embedding providers to combine.
            weights: Per-provider weights; normalized to sum to 1. Defaults to
                equal weights.
            target_dim: Desired output dimensionality. If smaller than the
                sum of provider dimensions, call :meth:`fit_projection` to
                learn a PCA projection.
            graph: Hypergraph reference needed for :meth:`fit_projection`.
        """
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
        """Return the effective output dimensionality.

        If ``target_dim`` was set at construction, returns that value.
        Otherwise returns the sum of all provider dimensions (or 64 as a
        fallback when no providers are configured).
        """
        if self._target_dim is not None:
            return self._target_dim
        return self._total_dim if self._total_dim > 0 else 64

    def embed(self, text: str) -> np.ndarray:
        """Combine text embeddings from all providers into a single vector.

        Provider outputs are concatenated (weighted), optionally projected
        via PCA, then L2-normalized.

        Args:
            text: Text to embed.

        Returns:
            Unit-normalized combined embedding vector.
        """
        parts: list[np.ndarray] = []
        for provider, weight in zip(self._providers, self._weights, strict=False):
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
        """Combine node embeddings from all providers into a single vector.

        Providers that support ``embed_node`` are called with the node ID;
        others fall back to ``embed(text)``.  Outputs are concatenated
        (weighted), optionally projected via PCA, then L2-normalized.

        Args:
            node_id: ID of the node in the graph.
            text: Textual representation (typically the node label).

        Returns:
            Unit-normalized combined embedding vector.
        """
        parts: list[np.ndarray] = []
        for provider, weight in zip(self._providers, self._weights, strict=False):
            vec = provider.embed_node(node_id, text) if hasattr(provider, "embed_node") else provider.embed(text)
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
        """Learn a PCA projection to reduce the combined embedding to ``target_dim``.

        Computes combined embeddings for all (or specified) nodes, then derives
        a projection matrix from the top principal components.

        Args:
            node_ids: Subset of node IDs to use for fitting. ``None`` uses all
                nodes in the graph.
        """
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
            for provider, weight in zip(self._providers, self._weights, strict=False):
                vec = provider.embed_node(nid, label) if hasattr(provider, "embed_node") else provider.embed(label)
                parts.append(vec * weight)
            matrix.append(np.concatenate(parts))
        mat = np.array(matrix)
        centered = mat - mat.mean(axis=0)
        cov = centered.T @ centered / max(len(centered) - 1, 1)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        top_indices = np.argsort(eigenvalues)[::-1][: self._target_dim]
        self._projection = eigenvectors[:, top_indices]


class SemanticEdgeBuilder:
    """Builds a secondary Hypergraph whose edges encode embedding-derived semantic similarity.

    For each node in the primary graph, computes the top-k most similar
    nodes via ``EmbeddingEngine.find_similar()`` and creates directed edges
    with ``label="semantic_sim"`` and ``weight=cosine_similarity``.

    The resulting graph can be combined with the primary graph via
    ``LayeredGraph`` so that ``SpreadingActivation`` traverses both
    structural and semantic edges.
    """

    def __init__(self, graph: Hypergraph, embedding: Any) -> None:
        self._graph = graph
        self._embedding = embedding
        self._layer: Hypergraph | None = None
        self._build_node_count: int = 0
        self._build_edge_count: int = 0

    @property
    def layer(self) -> Hypergraph | None:
        return self._layer

    def is_dirty(self) -> bool:
        if self._layer is None:
            return False
        return (
            self._graph.node_count != self._build_node_count
            or self._graph.edge_count != self._build_edge_count
        )

    def build(self, *, top_k: int = 10, threshold: float = 0.7) -> Hypergraph:
        from hyper3.kernel_types import Hyperedge, Hypernode

        self._layer = Hypergraph()
        for node in self._graph.nodes:
            self._layer.add_node(Hypernode(id=node.id, label=node.label))
        for node in self._graph.nodes:
            similar = self._embedding.find_similar(node.id, top_k=top_k, threshold=threshold)
            for result in similar:
                edge = Hyperedge(
                    source_ids=frozenset({node.id}),
                    target_ids=frozenset({result.node_b_id}),
                    label="semantic_sim",
                    weight=max(result.similarity, 0.0),
                )
                self._layer.add_edge(edge)
        self._build_node_count = self._graph.node_count
        self._build_edge_count = self._graph.edge_count
        return self._layer

    def rebuild(self, *, top_k: int = 10, threshold: float = 0.7) -> Hypergraph:
        return self.build(top_k=top_k, threshold=threshold)
