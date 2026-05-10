from __future__ import annotations

from collections import deque
from typing import Any

import networkx as nx

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

        Divergence from NetworkX:
            Uses incidence-based transition P = D_v⁻¹ H W D_e⁻¹ H^T
            (Zhou et al. 2007), not the adjacency-based transition
            used by ``nx.pagerank``. Rankings typically agree but
            per-node values differ.

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

    def eigenvector_centrality_numpy(self) -> dict[str, float]:
        """Compute eigenvector centrality using numpy eigendecomposition.

        Faster than power iteration for small graphs.  Uses the
        eigenvector corresponding to the largest eigenvalue of the
        adjacency matrix.

        Returns:
            Dict mapping node ID to eigenvector centrality score.
        """
        import numpy as np

        A_sp, node_list = self.adjacency_matrix()
        n = len(node_list)
        if n == 0:
            return {}

        A = np.asarray(A_sp.toarray() if hasattr(A_sp, "toarray") else A_sp)
        eigenvalues, eigenvectors = np.linalg.eig(A)
        idx = np.argmax(np.real(eigenvalues))
        vec = np.real(eigenvectors[:, idx])
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return {nid: float(vec[i]) for i, nid in enumerate(node_list)}

    def katz_centrality_solve(self, *, alpha: float = 0.1, beta: float = 1.0) -> dict[str, float]:
        """Compute Katz centrality via direct matrix solve (I - alpha*A)^{-1} * beta * 1.

        Unlike the power-iteration version, this solves the linear system
        directly.  More accurate but O(n^3).

        Divergence from NetworkX:
            Operates on the incidence Laplacian rather than the adjacency
            matrix. Rankings typically agree with ``nx.katz_centrality``
            but absolute values differ.

        Args:
            alpha: Attenuation factor.
            beta: Constant added to each node.

        Returns:
            Dict mapping node ID to Katz centrality score.
        """
        import numpy as np

        A_sp, node_list = self.adjacency_matrix()
        n = len(node_list)
        if n == 0:
            return {}

        A = np.asarray(A_sp.toarray() if hasattr(A_sp, "toarray") else A_sp)
        I = np.eye(n)
        ones = np.ones(n)

        x = np.linalg.solve(I - alpha * A, beta * ones)
        norm = np.linalg.norm(x)
        if norm > 0:
            x = x / norm
        return {nid: float(x[i]) for i, nid in enumerate(node_list)}

    def h_eigenvector_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute hypergraph h-eigenvector centrality using tensor power iteration on the hyperedge incidence structure."""
        import numpy as np

        if not self._nodes:
            return {}
        node_list = list(self._nodes.keys())
        n = len(node_list)
        node_idx = {nid: i for i, nid in enumerate(node_list)}

        max_order = 1
        edge_members: list[list[int]] = []
        for edge in self._edges.values():
            members = [node_idx[nid] for nid in edge.node_ids if nid in node_idx]
            if len(members) >= 2:
                edge_members.append(members)
                if len(members) > max_order:
                    max_order = len(members)

        if not edge_members:
            return {nid: 1.0 / n for nid in node_list}

        x = np.ones(n) / n
        exp = max_order - 1

        for _ in range(max_iter):
            new_x = np.zeros(n)
            for members in edge_members:
                prod_all = np.prod(x[members])
                for node_i in members:
                    new_x[node_i] += prod_all / x[node_i] if x[node_i] > 0 else 0.0
            if exp > 1:
                mask = new_x > 0
                new_x[mask] = np.power(new_x[mask], 1.0 / exp)
            s = np.sum(np.abs(new_x))
            if s > 0:
                new_x = new_x / s
            if np.linalg.norm(new_x - x) < tol:
                x = new_x
                break
            x = new_x

        return {nid: float(x[i]) for i, nid in enumerate(node_list)}

    def z_eigenvector_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute hypergraph z-eigenvector centrality using normalized tensor power iteration."""
        import numpy as np

        if not self._nodes:
            return {}
        node_list = list(self._nodes.keys())
        n = len(node_list)
        node_idx = {nid: i for i, nid in enumerate(node_list)}

        edge_members: list[list[int]] = []
        for edge in self._edges.values():
            members = [node_idx[nid] for nid in edge.node_ids if nid in node_idx]
            if len(members) >= 2:
                edge_members.append(members)

        if not edge_members:
            return {nid: 1.0 / n for nid in node_list}

        x = np.ones(n) / n

        for _ in range(max_iter):
            new_x = np.zeros(n)
            for members in edge_members:
                prod_all = np.prod(x[members])
                for node_i in members:
                    new_x[node_i] += prod_all / x[node_i] if x[node_i] > 0 else 0.0
            s = np.sum(np.abs(new_x))
            if s > 0:
                new_x = new_x / s
            if np.linalg.norm(new_x - x) < tol:
                x = new_x
                break
            x = new_x

        return {nid: float(x[i]) for i, nid in enumerate(node_list)}

    def c_eigenvector_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Alias for eigenvector_centrality (standard co-occurrence matrix eigenvector centrality)."""
        return self.eigenvector_centrality(max_iter=max_iter, tol=tol)

    def node_edge_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> tuple[dict[str, float], dict[str, float]]:
        """Compute joint node-edge centrality using the bipartite incidence structure. Returns (node_centrality, edge_centrality) dicts."""
        import numpy as np

        if not self._nodes:
            return {}, {}

        node_list = list(self._nodes.keys())
        edge_list = list(self._edges.keys())
        n = len(node_list)
        m = len(edge_list)
        node_idx = {nid: i for i, nid in enumerate(node_list)}

        if m == 0:
            return {nid: 1.0 / n for nid in node_list}, {}

        from scipy import sparse as sp

        rows: list[int] = []
        cols: list[int] = []
        for j, eid in enumerate(edge_list):
            edge = self._edges[eid]
            for nid in edge.node_ids:
                if nid in node_idx:
                    rows.append(node_idx[nid])
                    cols.append(j)
        I_mat = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, m))

        x = np.ones(n) / n
        y = np.ones(m) / m

        for _ in range(max_iter):
            y_sq = y ** 2
            Iy2 = np.asarray(I_mat @ y_sq).flatten()
            u = np.sqrt(np.abs(x) * np.sqrt(np.abs(Iy2)))

            x_sq = x ** 2
            Itx2 = np.asarray(I_mat.T @ x_sq).flatten()
            v = np.sqrt(np.abs(y) * np.sqrt(np.abs(Itx2)))

            u_sum = np.sum(np.abs(u))
            v_sum = np.sum(np.abs(v))
            if u_sum > 0:
                u = u / u_sum
            if v_sum > 0:
                v = v / v_sum

            err = np.linalg.norm(u - x) + np.linalg.norm(v - y)
            x, y = u, v
            if err < tol:
                break

        node_cent = {nid: float(x[i]) for i, nid in enumerate(node_list)}
        edge_cent = {eid: float(y[j]) for j, eid in enumerate(edge_list)}
        return node_cent, edge_cent

    def _s_line_graph(self, s: int) -> Any:
        """Build an s-line graph where each hyperedge becomes a node and edges connect hyperedges sharing at least s vertices. Delegates to networkx."""
        lg = nx.Graph()
        edge_ids = list(self._edges.keys())
        for eid in edge_ids:
            lg.add_node(eid)

        for nid in self._nodes:
            incident = self.incident_edges(nid)
            for i in range(len(incident)):
                for j in range(i + 1, len(incident)):
                    e1 = incident[i]
                    e2 = incident[j]
                    overlap = len(e1.node_ids & e2.node_ids)
                    if overlap >= s:
                        lg.add_edge(e1.id, e2.id)
        return lg

    def _bipartite_projection(self) -> Any:
        """Build a bipartite graph with N:-prefixed real nodes and E:-prefixed edge nodes. Delegates to networkx."""
        bp = nx.Graph()
        node_prefix = "N:"
        edge_prefix = "E:"
        for nid in self._nodes:
            bp.add_node(f"{node_prefix}{nid}", bipartite=0)
        for eid, edge in self._edges.items():
            bp.add_node(f"{edge_prefix}{eid}", bipartite=1)
            for nid in edge.node_ids:
                if nid in self._nodes:
                    bp.add_edge(f"{edge_prefix}{eid}", f"{node_prefix}{nid}")
        return bp, node_prefix, edge_prefix

    def s_walk_betweenness(self, *, s: int = 1, kind: str = "edges") -> dict[str, float]:
        """Compute s-walk betweenness centrality. When kind="edges", operates on the s-line graph (edges as nodes). When kind="nodes", operates on the bipartite projection (N:/E: prefixed). Note: the node variant computes centrality on a bipartite graph where edge-entities inflate path lengths, so results differ from standard node betweenness. Delegates to networkx."""
        if kind == "edges":
            lg = self._s_line_graph(s)
            if lg.number_of_nodes() == 0:
                return {}
            bc = nx.betweenness_centrality(lg, normalized=True)
            return {eid: v for eid, v in bc.items()}
        else:
            bp, npre, epre = self._bipartite_projection()
            if bp.number_of_nodes() == 0:
                return {}
            bc = nx.betweenness_centrality(bp, normalized=True)
            return {k[len(npre):]: v for k, v in bc.items() if k.startswith(npre)}

    def s_walk_closeness(self, *, s: int = 1, kind: str = "edges") -> dict[str, float]:
        """Compute s-walk closeness centrality. Same kind parameter and bipartite-projection caveat as s_walk_betweenness. Delegates to networkx."""
        if kind == "edges":
            lg = self._s_line_graph(s)
            if lg.number_of_nodes() == 0:
                return {}
            cc = nx.closeness_centrality(lg)
            return {eid: v for eid, v in cc.items()}
        else:
            bp, npre, epre = self._bipartite_projection()
            if bp.number_of_nodes() == 0:
                return {}
            cc = nx.closeness_centrality(bp)
            return {k[len(npre):]: v for k, v in cc.items() if k.startswith(npre)}

    def harmonic_centrality(self, *, source: str | None = None) -> dict[str, float]:
        """Compute harmonic centrality for all or a subset of nodes. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.harmonic_centrality(G, nbunch=source)
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}

    def information_centrality(self) -> dict[str, float]:
        """Compute information centrality for all nodes. Requires a connected graph. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.information_centrality(G)
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}

    def load_centrality(self) -> dict[str, float]:
        """Compute load centrality (normalized) for all nodes. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.load_centrality(G, normalized=True)
        if not isinstance(nx_result, dict):
            return {}
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}

    def current_flow_betweenness_centrality(self, *, weight: str | None = None) -> dict[str, float]:
        """Compute current-flow betweenness centrality. Requires a connected graph. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.current_flow_betweenness_centrality(G, weight=weight)
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}

    def current_flow_closeness_centrality(self) -> dict[str, float]:
        """Compute current-flow closeness centrality. Requires a connected graph. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.current_flow_closeness_centrality(G)
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}

    def approximate_current_flow_betweenness_centrality(self, *, seed: int | None = None) -> dict[str, float]:
        """Compute approximate current-flow betweenness centrality. Requires a connected graph. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.approximate_current_flow_betweenness_centrality(G, seed=seed)
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}

    def percolation_centrality(self, percolation_attribute: str) -> dict[str, float]:
        """Compute percolation centrality using a node data attribute as the percolation state. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx.set_node_attributes(G, self._node_data_attr(percolation_attribute), percolation_attribute)
        nx_result = nx.percolation_centrality(G, percolation_attribute)
        return {nid: float(v) for nid, v in nx_result.items() if nid in self._nodes}

    def voterank(self, *, number_of_nodes: int | None = None) -> list[str]:
        """Return a ranked list of influential nodes using VoteRank. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return [nid for nid in nx.voterank(G, number_of_nodes=number_of_nodes) if nid in self._nodes]
