from __future__ import annotations

from dataclasses import dataclass, field

from hyper3.embedding import EmbeddingEngine
from hyper3.kernel import Hypergraph
from hyper3.results import TrainResult
from hyper3.retrieval_activation import SpreadingActivation


@dataclass
class RetrievalResult:
    """A retrieved node with combined activation, similarity, and RRF fusion scores."""

    node_id: str
    label: str
    activation: float
    similarity: float
    rrf_score: float
    activation_rank: int
    similarity_rank: int

    def __lt__(self, other: RetrievalResult) -> bool:
        """Compare by RRF score for sorting."""
        return self.rrf_score < other.rrf_score


@dataclass
class FeedbackRecord:
    """A single relevance judgment linking a query to a result node."""

    query: str
    node_id: str
    label: str
    relevant: bool
    features: dict[str, float] = field(default_factory=dict)


class FeedbackStore:
    """Accumulates relevance judgments for training the learning-to-rank model."""

    def __init__(self) -> None:
        """Initialize an empty feedback store."""
        self._records: list[FeedbackRecord] = []

    def record(
        self, query: str, node_id: str, label: str, relevant: bool, features: dict[str, float] | None = None
    ) -> None:
        """Store a relevance judgment for a query-result pair.

        Args:
            query: The query string.
            node_id: Node ID of the result.
            label: Label of the result node.
            relevant: Whether the result was judged relevant.
            features: Optional feature vector for learning-to-rank.
        """
        self._records.append(
            FeedbackRecord(
                query=query,
                node_id=node_id,
                label=label,
                relevant=relevant,
                features=features or {},
            )
        )

    @property
    def records(self) -> list[FeedbackRecord]:
        """Return a copy of all stored feedback records."""
        return list(self._records)

    @property
    def size(self) -> int:
        """Return the number of stored feedback records."""
        return len(self._records)

    def clear(self) -> None:
        """Remove all stored feedback records."""
        self._records.clear()

    def relevant_labels_for(self, query: str) -> set[str]:
        """Return the set of labels marked relevant for a given query."""
        return {r.label for r in self._records if r.query == query and r.relevant}

    def irrelevant_labels_for(self, query: str) -> set[str]:
        """Return the set of labels marked irrelevant for a given query."""
        return {r.label for r in self._records if r.query == query and not r.relevant}


class LearningToRank:
    """Weighted linear ranker trained on relevance feedback via gradient descent."""

    def __init__(self, feature_names: list[str] | None = None) -> None:
        """Initialize the ranker with uniform feature weights.

        Args:
            feature_names: Names of features to weight. Defaults to
                ["activation", "similarity", "degree", "inverse_depth"].
        """
        self._feature_names = feature_names or ["activation", "similarity", "degree", "inverse_depth"]
        self._weights: dict[str, float] = {f: 1.0 / len(self._feature_names) for f in self._feature_names}

    @property
    def weights(self) -> dict[str, float]:
        """Return a copy of the current feature weights."""
        return dict(self._weights)

    def score(self, features: dict[str, float]) -> float:
        """Compute a weighted linear score from the given feature dict."""
        total = 0.0
        for name, weight in self._weights.items():
            total += weight * features.get(name, 0.0)
        return total

    def train(self, records: list[FeedbackRecord], learning_rate: float = 0.1, epochs: int = 50) -> TrainResult:
        """Train feature weights via gradient descent on feedback records.

        Args:
            records: Labeled feedback records with features.
            learning_rate: Step size for gradient updates.
            epochs: Number of training passes.

        Returns:
            TrainResult with training status and final weights.
        """
        if not records:
            return TrainResult(reason="no records")

        for _ in range(epochs):
            gradients = {f: 0.0 for f in self._feature_names}
            for rec in records:
                predicted = self.score(rec.features)
                target = 1.0 if rec.relevant else 0.0
                error = predicted - target
                for fname in self._feature_names:
                    gradients[fname] += error * rec.features.get(fname, 0.0)
            for fname in self._feature_names:
                self._weights[fname] -= learning_rate * gradients[fname] / max(len(records), 1)

        total = sum(abs(w) for w in self._weights.values())
        if total > 0:
            self._weights = {k: v / total for k, v in self._weights.items()}

        return TrainResult(trained=True, weights=dict(self._weights), samples=len(records))


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists using Reciprocal Rank Fusion.

    Args:
        ranked_lists: Each list contains (item_id, score) tuples in rank order.
        k: RRF smoothing constant.

    Returns:
        Fused list of (item_id, rrf_score) sorted descending.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (item_id, _) in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return results


class RetrievalEngine:
    """Combines spreading activation and semantic similarity via Reciprocal Rank Fusion for concept retrieval."""

    def __init__(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        embedding: EmbeddingEngine | None = None,
        rrf_k: int = 60,
    ) -> None:
        """Initialize the retrieval engine.

        Args:
            graph: The hypergraph to search over.
            activation: Optional pre-configured spreading activation engine.
            embedding: Optional embedding engine for semantic similarity.
            rrf_k: RRF smoothing constant.
        """
        self._graph = graph
        self._activation = activation or SpreadingActivation(graph)
        self._embedding = embedding
        self._rrf_k = rrf_k
        self._feedback = FeedbackStore()
        self._ltr = LearningToRank()

    @property
    def feedback(self) -> FeedbackStore:
        """Return the feedback store for recording relevance judgments."""
        return self._feedback

    @property
    def ltr(self) -> LearningToRank:
        """Return the learning-to-rank model."""
        return self._ltr

    def retrieve(
        self,
        concept: str,
        *,
        top_k: int = 10,
        iterations: int = 3,
        use_ltr: bool = False,
    ) -> list[RetrievalResult]:
        """Retrieve nodes related to a concept using activation and/or semantic signals.

        Args:
            concept: Label or ID of the seed concept.
            top_k: Maximum number of results.
            iterations: Number of spreading activation iterations.
            use_ltr: Use the learned-to-rank model if enough feedback exists.

        Returns:
            Ranked list of RetrievalResult with combined scores.
        """
        seed_node = self._graph.get_node_by_label(concept) or self._graph.get_node(concept)
        if not seed_node:
            return []

        self._activation.clear()
        self._activation.stimulate(seed_node.id)
        self._activation.spread(iterations)

        activated = self._activation.get_activated(top_k=top_k * 3)
        activation_list: list[tuple[str, float]] = [
            (r.node_id, r.activation) for r in activated if r.node_id != seed_node.id
        ]
        activation_ranked = sorted(activation_list, key=lambda x: x[1], reverse=True)

        similarity_ranked: list[tuple[str, float]] = []
        if self._embedding:
            similar = self._embedding.find_similar(seed_node.id, top_k=top_k * 3, threshold=-1.0)
            similarity_ranked = [(r.node_b_id, r.similarity) for r in similar]

        if use_ltr and self._feedback.size >= 5:
            return self._rank_with_ltr(seed_node.id, concept, activation_ranked, similarity_ranked, top_k)

        lists_to_fuse = [activation_ranked]
        if similarity_ranked:
            lists_to_fuse.append(similarity_ranked)

        fused = reciprocal_rank_fusion(lists_to_fuse, k=self._rrf_k)

        act_rank_map = {nid: rank for rank, (nid, _) in enumerate(activation_ranked, start=1)}
        sim_rank_map = {nid: rank for rank, (nid, _) in enumerate(similarity_ranked, start=1)}
        act_score_map = dict(activation_ranked)
        sim_score_map = dict(similarity_ranked)

        results: list[RetrievalResult] = []
        for nid, rrf_score in fused[:top_k]:
            node = self._graph.get_node(nid)
            label = node.label if node else ""
            results.append(
                RetrievalResult(
                    node_id=nid,
                    label=label,
                    activation=act_score_map.get(nid, 0.0),
                    similarity=sim_score_map.get(nid, 0.0),
                    rrf_score=rrf_score,
                    activation_rank=act_rank_map.get(nid, len(activation_ranked) + 1),
                    similarity_rank=sim_rank_map.get(nid, len(similarity_ranked) + 1),
                )
            )
        return results

    def _rank_with_ltr(
        self,
        seed_id: str,
        concept: str,
        activation_ranked: list[tuple[str, float]],
        similarity_ranked: list[tuple[str, float]],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Re-rank candidates using the learned-to-rank model.

        Args:
            seed_id: ID of the seed node.
            concept: Label or ID of the seed (for path lookup).
            activation_ranked: Activation-scored candidates.
            similarity_ranked: Similarity-scored candidates.
            top_k: Maximum results to return.

        Returns:
            LTR-scored RetrievalResult list.
        """
        act_score_map = dict(activation_ranked)
        sim_score_map = dict(similarity_ranked)
        all_ids = set(act_score_map.keys()) | set(sim_score_map.keys())

        max_act = max(act_score_map.values()) if act_score_map else 1.0
        max_sim = max(sim_score_map.values()) if sim_score_map else 1.0

        scored: list[tuple[float, RetrievalResult]] = []
        for nid in all_ids:
            if nid == seed_id:
                continue
            node = self._graph.get_node(nid)
            label = node.label if node else ""
            act_norm = act_score_map.get(nid, 0.0) / max(max_act, 1e-9)
            sim_norm = sim_score_map.get(nid, 0.0) / max(max_sim, 1e-9)
            degree = len(self._graph.neighbors(nid))
            degree_norm = degree / max(self._graph.node_count, 1)
            seed_node = self._graph.get_node_by_label(concept)
            if not seed_node:
                seed_node = self._graph.get_node(concept)
            depth = self._graph.shortest_path(seed_node.id, nid) if seed_node else None
            inverse_depth = 1.0 / max(len(depth) - 1, 1) if depth else 0.0
            features = {
                "activation": act_norm,
                "similarity": sim_norm,
                "degree": degree_norm,
                "inverse_depth": inverse_depth,
            }
            ltr_score = self._ltr.score(features)
            r = RetrievalResult(
                node_id=nid,
                label=label,
                activation=act_score_map.get(nid, 0.0),
                similarity=sim_score_map.get(nid, 0.0),
                rrf_score=ltr_score,
                activation_rank=0,
                similarity_rank=0,
            )
            scored.append((ltr_score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def record_feedback(
        self,
        query: str,
        results: list[RetrievalResult] | list,
        relevant_labels: set[str],
    ) -> int:
        """Record relevance feedback for a set of retrieval results.

        Args:
            query: The query that produced the results.
            results: The results to judge (RetrievalResult or SearchHit).
            relevant_labels: Labels that should be considered relevant.

        Returns:
            Number of feedback records stored.
        """
        max_act = max((r.activation for r in results if getattr(r, 'activation', None) is not None), default=1.0)
        max_sim = max((r.similarity for r in results if getattr(r, 'similarity', None) is not None), default=1.0)
        count = 0
        for r in results:
            relevant = r.label in relevant_labels
            seed_node = self._graph.get_node_by_label(query) or self._graph.get_node(query)
            found = self._graph.get_node_by_label(r.label)
            node_id = getattr(r, 'node_id', None) or (found.id if found else None)
            depth_path = self._graph.shortest_path(seed_node.id, node_id) if seed_node and node_id else None
            inverse_depth = 1.0 / max(len(depth_path) - 1, 1) if depth_path else 0.0
            activation = getattr(r, 'activation', 0.0) or 0.0
            similarity = getattr(r, 'similarity', 0.0) or 0.0
            features = {
                "activation": activation / max(max_act, 1e-9),
                "similarity": similarity / max(max_sim, 1e-9),
                "degree": len(self._graph.neighbors(node_id)) / max(self._graph.node_count, 1) if node_id else 0.0,
                "inverse_depth": inverse_depth,
            }
            self._feedback.record(query, node_id or r.label, r.label, relevant, features)
            count += 1
        return count

    def train_from_feedback(self) -> TrainResult:
        """Train the learning-to-rank model from accumulated feedback.

        Returns:
            TrainResult from LearningToRank.train().
        """
        return self._ltr.train(self._feedback.records)
