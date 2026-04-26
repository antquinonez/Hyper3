from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hyper3.retrieval_activation import ActivationResult, SpreadingActivation
from hyper3.embedding import EmbeddingEngine
from hyper3.kernel import Hypergraph


@dataclass
class RetrievalResult:
    node_id: str
    label: str
    activation: float
    similarity: float
    rrf_score: float
    activation_rank: int
    similarity_rank: int

    def __lt__(self, other: RetrievalResult) -> bool:
        return self.rrf_score < other.rrf_score


@dataclass
class FeedbackRecord:
    query: str
    node_id: str
    label: str
    relevant: bool
    features: dict[str, float] = field(default_factory=dict)


class FeedbackStore:
    def __init__(self) -> None:
        self._records: list[FeedbackRecord] = []

    def record(self, query: str, node_id: str, label: str, relevant: bool, features: dict[str, float] | None = None) -> None:
        self._records.append(FeedbackRecord(
            query=query, node_id=node_id, label=label, relevant=relevant,
            features=features or {},
        ))

    @property
    def records(self) -> list[FeedbackRecord]:
        return list(self._records)

    @property
    def size(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()

    def relevant_labels_for(self, query: str) -> set[str]:
        return {r.label for r in self._records if r.query == query and r.relevant}

    def irrelevant_labels_for(self, query: str) -> set[str]:
        return {r.label for r in self._records if r.query == query and not r.relevant}


class LearningToRank:
    def __init__(self, feature_names: list[str] | None = None) -> None:
        self._feature_names = feature_names or ["activation", "similarity", "degree", "inverse_depth"]
        self._weights: dict[str, float] = {f: 1.0 / len(self._feature_names) for f in self._feature_names}

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._weights)

    def score(self, features: dict[str, float]) -> float:
        total = 0.0
        for name, weight in self._weights.items():
            total += weight * features.get(name, 0.0)
        return total

    def train(self, records: list[FeedbackRecord], learning_rate: float = 0.1, epochs: int = 50) -> dict[str, Any]:
        if not records:
            return {"trained": False, "reason": "no records"}

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

        return {"trained": True, "weights": dict(self._weights), "samples": len(records)}


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (item_id, _) in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return results


class RetrievalEngine:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        embedding: EmbeddingEngine | None = None,
        rrf_k: int = 60,
    ) -> None:
        self._graph = graph
        self._activation = activation or SpreadingActivation(graph)
        self._embedding = embedding
        self._rrf_k = rrf_k
        self._feedback = FeedbackStore()
        self._ltr = LearningToRank()

    @property
    def feedback(self) -> FeedbackStore:
        return self._feedback

    @property
    def ltr(self) -> LearningToRank:
        return self._ltr

    def retrieve(
        self,
        concept: str,
        *,
        top_k: int = 10,
        iterations: int = 3,
        use_ltr: bool = False,
    ) -> list[RetrievalResult]:
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
            for node in self._graph.nodes:
                if node.id == seed_node.id:
                    continue
                sim = self._embedding.compute_similarity(seed_node.id, node.id)
                similarity_ranked.append((node.id, sim))
            similarity_ranked.sort(key=lambda x: x[1], reverse=True)

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
            results.append(RetrievalResult(
                node_id=nid,
                label=label,
                activation=act_score_map.get(nid, 0.0),
                similarity=sim_score_map.get(nid, 0.0),
                rrf_score=rrf_score,
                activation_rank=act_rank_map.get(nid, len(activation_ranked) + 1),
                similarity_rank=sim_rank_map.get(nid, len(similarity_ranked) + 1),
            ))
        return results

    def _rank_with_ltr(
        self,
        seed_id: str,
        concept: str,
        activation_ranked: list[tuple[str, float]],
        similarity_ranked: list[tuple[str, float]],
        top_k: int,
    ) -> list[RetrievalResult]:
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
            features = {
                "activation": act_norm,
                "similarity": sim_norm,
                "degree": degree_norm,
                "inverse_depth": 1.0,
            }
            ltr_score = self._ltr.score(features)
            r = RetrievalResult(
                node_id=nid, label=label,
                activation=act_score_map.get(nid, 0.0),
                similarity=sim_score_map.get(nid, 0.0),
                rrf_score=ltr_score,
                activation_rank=0, similarity_rank=0,
            )
            scored.append((ltr_score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def record_feedback(
        self,
        query: str,
        results: list[RetrievalResult],
        relevant_labels: set[str],
    ) -> int:
        max_act = max((r.activation for r in results), default=1.0)
        max_sim = max((r.similarity for r in results), default=1.0)
        count = 0
        for r in results:
            relevant = r.label in relevant_labels
            features = {
                "activation": r.activation / max(max_act, 1e-9),
                "similarity": r.similarity / max(max_sim, 1e-9),
                "degree": len(self._graph.neighbors(r.node_id)) / max(self._graph.node_count, 1),
                "inverse_depth": 1.0,
            }
            self._feedback.record(query, r.node_id, r.label, relevant, features)
            count += 1
        return count

    def train_from_feedback(self) -> dict[str, Any]:
        return self._ltr.train(self._feedback.records)
