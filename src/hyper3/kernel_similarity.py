from __future__ import annotations

from hyper3.kernel_base import _GraphBase
from hyper3.results import HyperedgeSimilarityResult


class SimilarityMixin(_GraphBase):

    def hyperedge_similarity(
        self,
        edge_id: str,
        *,
        metric: str = "jaccard",
        top_k: int | None = None,
    ) -> HyperedgeSimilarityResult:
        """Find hyperedges similar to a query hyperedge by node-set overlap.

        Args:
            edge_id: ID of the query hyperedge.
            metric: Similarity metric: ``"jaccard"``, ``"sorensen_dice"``,
                or ``"overlap_coefficient"``.
            top_k: If set, return only the top-k most similar edges.

        Returns:
            HyperedgeSimilarityResult with sorted similar edges.
        """
        query = self._edges.get(edge_id)
        if not query:
            return HyperedgeSimilarityResult(query_edge_id=edge_id, metric=metric)
        query_nodes = query.source_ids | query.target_ids
        if not query_nodes:
            return HyperedgeSimilarityResult(query_edge_id=edge_id, metric=metric)

        scores = self._compute_similarity_scores(query_nodes, edge_id, metric)

        scores.sort(key=lambda x: -x[1])
        if top_k is not None:
            scores = scores[:top_k]
        return HyperedgeSimilarityResult(
            query_edge_id=edge_id,
            similar_edges=scores,
            metric=metric,
        )

    def _compute_similarity_scores(
        self,
        query_nodes: frozenset[str],
        exclude_edge_id: str,
        metric: str,
    ) -> list[tuple[str, float]]:
        """Score every edge against *query_nodes* using the chosen similarity metric."""
        scores: list[tuple[str, float]] = []
        for eid, edge in self._edges.items():
            if eid == exclude_edge_id:
                continue
            edge_nodes = edge.source_ids | edge.target_ids
            if not edge_nodes:
                continue
            intersection = len(query_nodes & edge_nodes)
            if intersection == 0:
                continue
            if metric == "jaccard":
                score = intersection / len(query_nodes | edge_nodes)
            elif metric == "sorensen_dice":
                score = 2.0 * intersection / (len(query_nodes) + len(edge_nodes))
            elif metric == "overlap_coefficient":
                score = intersection / min(len(query_nodes), len(edge_nodes))
            else:
                score = intersection / len(query_nodes | edge_nodes)
            scores.append((eid, score))
        return scores
