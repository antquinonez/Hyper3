from __future__ import annotations

from collections import deque

from hyper3.kernel_base import _GraphBase


class CentralityMixin(_GraphBase):

    def closeness_centrality(self) -> dict[str, float]:
        """Compute closeness centrality for every node.

        Closeness is defined as the reciprocal of the average shortest-path
        distance from a node to all other reachable nodes.  Uses BFS
        (unweighted) for distance computation.

        Returns:
            Dict mapping node ID to closeness centrality in [0, 1].
        """
        if not self._nodes:
            return {}
        n = len(self._nodes)
        result: dict[str, float] = {}
        for nid in self._nodes:
            dists = self._bfs_all_distances(nid)
            reachable = {k: v for k, v in dists.items() if k != nid and v >= 0}
            if not reachable:
                result[nid] = 0.0
                continue
            total_dist = sum(reachable.values())
            if total_dist == 0:
                result[nid] = 0.0
                continue
            result[nid] = len(reachable) / ((n - 1) * total_dist)
        return result

    def eigenvector_centrality(self, *, max_iter: int = 100, tol: float = 1e-06) -> dict[str, float]:
        """Compute eigenvector centrality via power iteration on the adjacency matrix.

        A node's score is proportional to the sum of its neighbors' scores.
        Values are normalized to unit L2 norm.

        Args:
            max_iter: Maximum number of power-iteration steps.
            tol: Convergence tolerance on L2 norm change.

        Returns:
            Dict mapping node ID to eigenvector centrality score.
        """
        import numpy as np

        A_sp, node_list = self.adjacency_matrix()
        n = len(node_list)
        if n == 0:
            return {}

        A = np.asarray(A_sp.toarray() if hasattr(A_sp, "toarray") else A_sp)
        x = np.ones(n) / n

        for _ in range(max_iter):
            x_new = A @ x
            norm = np.linalg.norm(x_new)
            if norm > 0:
                x_new = x_new / norm
            if np.linalg.norm(x_new - x) < tol:
                x = x_new
                break
            x = x_new

        return {nid: float(x[i]) for i, nid in enumerate(node_list)}

    def subhypergraph_centrality(self) -> dict[str, float]:
        """Compute subgraph centrality via the diagonal of the matrix exponential of A.

        Subgraph centrality (Estrada & Rodriguez-Velazquez 2005) counts
        the number of closed walks starting and ending at each node,
        weighted by ``1/k!`` for walk length *k*.  Computed as
        ``diag(expm(A))`` where A is the adjacency matrix.

        Returns:
            Dict mapping node ID to its subgraph centrality score.
        """
        import numpy as np
        from scipy.linalg import expm

        A_sp, node_list = self.adjacency_matrix()
        n = len(node_list)
        if n == 0:
            return {}

        A = np.asarray(A_sp.toarray() if hasattr(A_sp, "toarray") else A_sp)
        eA = expm(A)
        diag = np.diag(eA)
        return {nid: float(diag[i]) for i, nid in enumerate(node_list)}

    def core_periphery(self, *, num_iterations: int = 100) -> dict[str, float]:
        """Compute core-periphery scores using a relaxed optimization.

        Assigns each node a continuous score in [0, 1] where 1 indicates
        core membership.  Uses the Raghavan relaxation: iteratively update
        each node's score as the mean of its neighbors' scores, starting
        from degree-normalised initial values.

        Args:
            num_iterations: Number of relaxation iterations.

        Returns:
            Dict mapping node ID to its core-periphery score in [0, 1].
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return {}

        A_sp, _ = self.adjacency_matrix()
        A = np.asarray(A_sp.toarray() if hasattr(A_sp, "toarray") else A_sp)

        degrees = np.array(A.sum(axis=1)).flatten()
        max_deg = degrees.max() if degrees.max() > 0 else 1.0
        scores = degrees / max_deg

        for _ in range(num_iterations):
            new_scores = A @ scores
            row_sums = A.sum(axis=1).flatten()
            mask = row_sums > 0
            new_scores[mask] = new_scores[mask] / row_sums[mask]
            new_scores[~mask] = scores[~mask]
            scores = new_scores

        scores = np.clip(scores, 0.0, 1.0)
        return {nid: float(scores[i]) for i, nid in enumerate(node_list)}
    def degree_centrality(self) -> dict[str, float]:
        """Compute normalized degree centrality for every node.

        Returns:
            Dict mapping node ID to its degree centrality in [0, 1].
        """
        n = len(self._nodes)
        if n <= 1:
            return {nid: 1.0 for nid in self._nodes}
        result: dict[str, float] = {}
        for nid in self._nodes:
            degree = len(self.incident_edges(nid))
            result[nid] = degree / (n - 1)
        return result

    def betweenness_centrality(self, *, max_samples: int | None = None) -> dict[str, float]:
        """Compute betweenness centrality using Brandes' algorithm.

        Runs single-source BFS from every node (or a sampled subset),
        accumulating dependency scores.  Hyperedges are traversed as
        single hops. Edge weights are not used; this is a structural
        (unweighted) metric.

        Normalized by 1/((n-1)(n-2)) for directed graphs with n >= 3, so
        values are in [0, 1]. With ``max_samples``, normalization is
        1/max_samples and values can exceed 1.0 (raw pairwise dependency
        counts).

        Args:
            max_samples: If set, approximate using this many random
                source nodes instead of all nodes.

        Returns:
            Dict mapping node ID to its betweenness centrality score.
        """
        if not self._nodes:
            return {}
        node_ids = list(self._nodes.keys())
        n = len(node_ids)
        centrality: dict[str, float] = {nid: 0.0 for nid in node_ids}

        sources: list[str]
        if max_samples is not None and max_samples < n:
            import random as _rng

            sources = _rng.sample(node_ids, min(max_samples, n))
        else:
            sources = node_ids

        for s in sources:
            sigma, stack, delta = self._betweenness_bfs(s, node_ids)
            for w in stack:
                if w != s:
                    centrality[w] += delta[w]

        n = len(self._nodes)
        if max_samples is not None:
            scale = 1.0 / max_samples if max_samples > 0 else 1.0
        elif n >= 3:
            scale = 1.0 / ((n - 1) * (n - 2))
        else:
            scale = 1.0
        return {nid: c * scale for nid, c in centrality.items()}

    def _betweenness_bfs(
        self, source: str, node_ids: list[str]
    ) -> tuple[dict[str, float], list[str], dict[str, float]]:
        """BFS from *source* returning (delta, stack, sigma) for Brandes betweenness."""
        pred: dict[str, list[str]] = {}
        dist: dict[str, float] = {nid: -1.0 for nid in node_ids}
        sigma: dict[str, float] = {nid: 0.0 for nid in node_ids}
        dist[source] = 0.0
        sigma[source] = 1.0
        stack: list[str] = []
        queue: deque[str] = deque([source])

        while queue:
            v = queue.popleft()
            stack.append(v)
            for edge in self.outgoing_edges(v):
                for w in edge.target_ids:
                    if dist[w] < 0:
                        queue.append(w)
                        dist[w] = dist[v] + 1
                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        pred.setdefault(w, []).append(v)

        delta: dict[str, float] = {nid: 0.0 for nid in node_ids}
        for w in reversed(stack):
            for v in pred.get(w, []):
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
        return sigma, stack, delta

    def pagerank(self, *, alpha: float = 0.85, max_iterations: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute PageRank using the hypergraph transition matrix.

        Edge weights are used as transition probabilities: higher weight
        means a stronger endorsement. Values sum to 1.0.

        This degrades to standard PageRank when all edges are pairwise
        with equal weights.

        Args:
            alpha: Damping factor (teleportation probability).
            max_iterations: Maximum power-iteration steps.
            tol: Convergence tolerance on L1 norm change.

        Returns:
            Dict mapping node ID to its PageRank score.
        """
        if not self._nodes:
            return {}
        if not self._edges:
            n = len(self._nodes)
            return {nid: 1.0 / n for nid in self._nodes}

        node_ids = [n.id for n in self._nodes.values()]
        vertex_degree, outgoing = self._build_pagerank_transition(node_ids)
        n = len(node_ids)

        pr = self._pagerank_iterate([1.0 / n] * n, alpha, n, vertex_degree, outgoing, max_iterations, tol)

        return {nid: pr[i] for i, nid in enumerate(node_ids)}

    def _build_pagerank_transition(
        self, node_ids: list[str]
    ) -> tuple[list[float], list[list[tuple[int, float]]]]:
        """Build the incidence-based transition structure: vertex degrees and outgoing edge lists."""
        node_idx = {nid: i for i, nid in enumerate(node_ids)}
        n = len(node_ids)
        vertex_degree = [0.0] * n
        outgoing: list[list[tuple[int, float]]] = [[] for _ in range(n)]

        for edge in self._edges.values():
            src_list = [node_idx[s] for s in edge.source_ids if s in node_idx]
            tgt_list = [node_idx[t] for t in edge.target_ids if t in node_idx]
            edge_card = len(src_list) + len(tgt_list)
            if edge_card == 0:
                continue
            w = edge.weight / edge_card
            for si in src_list:
                vertex_degree[si] += edge.weight
                for ti in tgt_list:
                    outgoing[si].append((ti, w))
        return vertex_degree, outgoing

    def _pagerank_iterate(
        self,
        pr: list[float],
        alpha: float,
        n: int,
        vertex_degree: list[float],
        outgoing: list[list[tuple[int, float]]],
        max_iterations: int,
        tol: float,
    ) -> list[float]:
        """Power-iteration loop for PageRank until convergence or *max_iterations*."""
        for _ in range(max_iterations):
            new_pr = [alpha / n] * n
            for i in range(n):
                if vertex_degree[i] == 0:
                    continue
                contrib = (1 - alpha) * pr[i] / vertex_degree[i]
                for ti, w in outgoing[i]:
                    new_pr[ti] += contrib * w
            total = sum(new_pr)
            if total > 0:
                new_pr = [v / total for v in new_pr]
            diff = sum(abs(new_pr[i] - pr[i]) for i in range(n))
            pr = new_pr
            if diff < tol:
                break
        return pr

    def katz_centrality(self, *, alpha: float = 0.1, beta: float = 1.0, max_iter: int = 100, tol: float = 1e-06) -> dict[str, float]:
        """Compute Katz centrality using the adjacency matrix.

        Katz centrality measures influence by considering all walks from
        a node, attenuated by ``alpha`` per step.  Values are normalized
        to unit length.

        Args:
            alpha: Attenuation factor.  Must be less than 1/λ_max for
                convergence, where λ_max is the largest eigenvalue.
            beta: Constant added to each node's score.
            max_iter: Maximum power-iteration steps.
            tol: Convergence tolerance on L2 norm change.

        Returns:
            Dict mapping node ID to its Katz centrality score.
        """
        import numpy as np

        A_sp, node_list = self.adjacency_matrix()
        n = len(node_list)
        if n == 0:
            return {}

        A_dense = A_sp.toarray() if hasattr(A_sp, "toarray") else np.asarray(A_sp)
        x = np.ones(n) / n
        ones = np.ones(n)

        for _ in range(max_iter):
            x_new = alpha * (A_dense @ x) + beta * ones
            norm = np.linalg.norm(x_new)
            if norm > 0:
                x_new = x_new / norm
            if np.linalg.norm(x_new - x) < tol:
                x = x_new
                break
            x = x_new

        return {nid: float(x[i]) for i, nid in enumerate(node_list)}
