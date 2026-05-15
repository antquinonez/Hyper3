"""SimilarityMixin: hyperedge similarity metrics."""
from __future__ import annotations

import networkx as nx

from hyper3.kernel_base import _GraphBase
from hyper3.results import HyperedgeSimilarityResult


class SimilarityMixin(_GraphBase):
    """Node and hyperedge similarity measures.

    Provides hyperedge similarity via node-set overlap (Jaccard,
    Sorensen-Dice, overlap coefficient) and node similarity via SimRank
    and PANTHER approximation.
    """

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

    def simrank_similarity(self, *, source: str | None = None, importance_factor: float = 0.9, max_iterations: int = 100) -> dict[str, dict[str, float]] | dict[str, float]:
        """Compute SimRank node similarity. When source is given, returns a flat dict; otherwise returns a nested dict. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result: dict[str, dict[str, float]] = nx.simrank_similarity(G, source=source, importance_factor=importance_factor, max_iterations=max_iterations)  # type: ignore[assignment]
        if source is not None:
            flat: dict[str, float] = nx_result  # type: ignore[assignment]
            return {nid: float(v) for nid, v in flat.items() if nid in self._nodes}
        return {k: {nid: float(v) for nid, v in inner.items() if nid in self._nodes} for k, inner in nx_result.items() if k in self._nodes}

    def panther_similarity(self, source: str, *, k: int = 5, path_length: int = 5, seed: int | None = None) -> dict[str, float]:
        """Compute approximate top-k node similarity to a source node using the PANTER algorithm. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.panther_similarity(G, source, k=k, path_length=path_length, seed=seed)
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}
