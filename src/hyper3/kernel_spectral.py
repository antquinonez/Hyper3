from __future__ import annotations

from typing import Any

from hyper3.kernel_base import _GraphBase
from hyper3.results import SpectralEmbeddingResult


class SpectralMixin(_GraphBase):

    def algebraic_connectivity(self) -> float:
        """Compute the algebraic connectivity (Fiedler value) of the hypergraph.

        The algebraic connectivity is the second-smallest eigenvalue of the
        hypergraph Laplacian.  It is zero when the graph is disconnected and
        positive when connected.  Larger values indicate greater connectivity.

        Returns:
            The Fiedler value.  Returns 0.0 for graphs with fewer than 2 nodes.
        """
        import numpy as np

        n = len(self._nodes)
        if n < 2:
            return 0.0

        L = np.asarray(self.hypergraph_laplacian())
        eigs = np.sort(np.linalg.eigvalsh(L))
        return float(eigs[1]) if len(eigs) >= 2 else 0.0

    def fiedler_vector(self) -> tuple[list[str], list[float]]:
        """Compute the Fiedler vector of the hypergraph Laplacian.

        The Fiedler vector is the eigenvector corresponding to the
        second-smallest eigenvalue (algebraic connectivity) of the
        Laplacian.  It is used for spectral bisection: nodes with
        positive entries go to one partition, negative to the other.

        Returns:
            Tuple of (node_ids, fiedler_values).  Returns empty lists
            for graphs with fewer than 2 nodes.
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n < 2:
            return [], []

        L = np.asarray(self.hypergraph_laplacian())
        eigenvalues, eigenvectors = np.linalg.eigh(L)
        idx = np.argsort(eigenvalues)
        fiedler = eigenvectors[:, idx[1]] if n >= 2 else np.zeros(n)
        return node_list, fiedler.tolist()

    def spectral_bisection(self) -> list[set[str]]:
        """Partition nodes into two sets using the Fiedler vector.

        Splits nodes by the sign of their entry in the Fiedler vector
        (the eigenvector for the second-smallest Laplacian eigenvalue).
        Nodes with non-negative entries go to partition 0; negative to 1.

        Returns:
            List of two sets of node IDs.  Returns a single set containing
            all nodes for graphs with fewer than 2 nodes.
        """
        node_list, fiedler = self.fiedler_vector()
        if len(node_list) < 2:
            return [set(self._nodes.keys())]

        part_a: set[str] = set()
        part_b: set[str] = set()
        for nid, val in zip(node_list, fiedler):
            if val >= 0:
                part_a.add(nid)
            else:
                part_b.add(nid)
        result = [part_a]
        if part_b:
            result.append(part_b)
        return result

    def spectral_bipartivity(self) -> float:
        """Compute spectral bipartivity from Laplacian eigenvalues.

        Uses the formula based on the eigenvalue spectrum of the adjacency
        matrix: ``sum(exp(-lambda_k)) / sum(exp(lambda_k))`` where lambda_k
        are the adjacency eigenvalues.  Values close to 1.0 indicate strong
        bipartite structure.

        Returns:
            Bipartivity score in (0, 1].  Returns 1.0 for graphs with
            fewer than 2 nodes or no edges.
        """
        import numpy as np

        n = len(self._nodes)
        if n < 2 or not self._edges:
            return 1.0

        A_sp, _ = self.adjacency_matrix()
        A = np.asarray(A_sp.toarray() if hasattr(A_sp, "toarray") else A_sp)
        eigs = np.linalg.eigvalsh(A)
        sum_neg = sum(np.exp(-e) for e in eigs)
        sum_pos = sum(np.exp(e) for e in eigs)
        return float(sum_neg / sum_pos) if sum_pos > 0 else 1.0

    def bethe_hessian_matrix(self, *, r: float | None = None) -> tuple[Any, list[str]]:
        """Compute the Bethe-Hessian matrix H(r) = (r-1)I - rA + D.

        Used for spectral clustering in sparse graphs.  The parameter
        ``r`` controls the trade-off between degree and adjacency
        information.  A common choice is ``r = sqrt(sum(d_i^2) / sum(d_i))``
        where d_i are node degrees.

        Args:
            r: Regularization parameter.  Defaults to ``sqrt(mean(degree^2) / mean(degree))``.

        Returns:
            Tuple of (H, node_id_list).
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return np.zeros((0, 0)), []

        A_sp, _ = self.adjacency_matrix()
        A = np.asarray(A_sp.toarray() if hasattr(A_sp, "toarray") else A_sp)
        degrees = np.array(A.sum(axis=1)).flatten()

        if r is None:
            mean_deg = degrees.mean() if degrees.mean() > 0 else 1.0
            mean_deg_sq = (degrees**2).mean() if n > 0 else 1.0
            r = np.sqrt(mean_deg_sq / mean_deg) if mean_deg > 0 else 1.0

        H = (r - 1.0) * np.eye(n) - r * A + np.diag(degrees)
        return H, node_list

    def incidence_matrix(self) -> tuple[Any, list[str], list[str]]:
        """Return the node-edge incidence matrix H.

        H[i, j] = 1 if node i participates in edge j, 0 otherwise.
        For directed hyperedges, source nodes get +1 and target nodes
        get -1, distinguishing direction.

        Returns:
            Tuple of (H, node_ids, edge_ids) where H is a numpy array
            of shape (n_nodes, n_edges), node_ids lists row indices,
            and edge_ids lists column indices.
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        edge_list = [e.id for e in self._edges.values()]
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        H = np.zeros((len(node_list), len(edge_list)))
        for j, edge in enumerate(self._edges.values()):
            for src in edge.source_ids:
                if src in node_idx:
                    H[node_idx[src], j] = 1.0
            for tgt in edge.target_ids:
                if tgt in node_idx:
                    H[node_idx[tgt], j] = -1.0
        return H, node_list, edge_list

    def incidence_matrix_unsigned(self) -> tuple[Any, list[str], list[str]]:
        """Return the unsigned incidence matrix H (all entries positive).

        H[i, j] = 1 if node i participates in edge j (source or target).

        Returns:
            Tuple of (H, node_ids, edge_ids).
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        edge_list = [e.id for e in self._edges.values()]
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        H = np.zeros((len(node_list), len(edge_list)))
        for j, edge in enumerate(self._edges.values()):
            for nid in edge.node_ids:
                if nid in node_idx:
                    H[node_idx[nid], j] = 1.0
        return H, node_list, edge_list

    def hypergraph_laplacian(self) -> Any:
        """Compute the hypergraph Laplacian L = D_v - H W D_e^{-1} H^T.

        Where:
        - H is the incidence matrix (unsigned, all positive entries)
        - W is a diagonal matrix of edge weights
        - D_v is the node degree matrix
        - D_e is the edge degree matrix (|source_ids| + |target_ids| for each edge)

        For the unsigned version used in spectral clustering, all
        incidence entries are positive (1.0).

        Returns:
            A numpy array of shape (n_nodes, n_nodes) representing
            the hypergraph Laplacian.  Returns a zero matrix if the
            graph has no edges.
        """
        import numpy as np

        if not self._edges:
            n = len(self._nodes)
            return np.zeros((n, n))

        node_list = [n.id for n in self._nodes.values()]
        edge_list = list(self._edges.values())
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        n = len(node_list)
        m = len(edge_list)

        H = np.zeros((n, m))
        W = np.zeros((m, m))
        for j, edge in enumerate(edge_list):
            for nid in edge.node_ids:
                if nid in node_idx:
                    H[node_idx[nid], j] = 1.0
            W[j, j] = edge.weight

        edge_degrees = np.array([len(edge.source_ids) + len(edge.target_ids) for edge in edge_list], dtype=float)
        D_e_inv = np.diag(np.where(edge_degrees > 0, 1.0 / edge_degrees, 0.0))

        D_v = np.diag(H @ W @ np.ones(m))
        L = D_v - H @ W @ D_e_inv @ H.T
        return L

    def adjacency_matrix(self) -> tuple[Any, list[str]]:
        """Compute the co-occurrence adjacency matrix A = H H^T - diag.

        A[i, j] counts the number of hyperedges containing both node i
        and node j (excluding self-loops on the diagonal).

        Returns:
            Tuple of (sparse adjacency matrix, node_id_list).
        """
        import numpy as np
        import scipy.sparse as sp

        H, node_list, _ = self.incidence_matrix_unsigned()
        n = len(node_list)
        if n == 0:
            return sp.csr_matrix((0, 0)), []

        H_sp = sp.csr_matrix(H)
        A = H_sp @ H_sp.T
        degrees = np.array(A.diagonal())
        D = sp.diags(degrees)
        A = A - D
        return A.tocsr(), node_list

    def normalized_laplacian(self) -> tuple[Any, list[str]]:
        """Compute the normalized hypergraph Laplacian L_norm = D_v^{-1/2} L D_v^{-1/2}.

        Where L is the unnormalized hypergraph Laplacian and D_v is the
        node degree matrix.

        Returns:
            Tuple of (L_norm, node_id_list).  Returns a zero matrix
            for graphs with no nodes.
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return np.zeros((0, 0)), []

        L = self.hypergraph_laplacian()

        H, _, _ = self.incidence_matrix_unsigned()
        edge_list = list(self._edges.values())
        if edge_list:
            W = np.array([e.weight for e in edge_list])
            D_v = H @ W
        else:
            D_v = np.zeros(n)

        D_v_inv_sqrt = np.zeros_like(D_v)
        nonzero = D_v > 0
        D_v_inv_sqrt[nonzero] = 1.0 / np.sqrt(D_v[nonzero])
        D_inv_sqrt = np.diag(D_v_inv_sqrt)
        L_norm = D_inv_sqrt @ L @ D_inv_sqrt
        return L_norm, node_list

    def spectral_embedding(self, *, dimensions: int = 8) -> SpectralEmbeddingResult:
        """Compute spectral embeddings from the normalized hypergraph Laplacian.

        Returns the bottom-``dimensions`` eigenvectors of:
            L_norm = I - D_v^{-1/2} H W D_e^{-1} H^T D_v^{-1/2}

        Args:
            dimensions: Number of embedding dimensions (eigenvectors).

        Returns:
            SpectralEmbeddingResult with embeddings, node IDs, and eigenvalues.
        """
        import numpy as np

        if not self._nodes or not self._edges:
            n = len(self._nodes)
            node_ids = [nd.id for nd in self._nodes.values()]
            return SpectralEmbeddingResult(
                node_ids=node_ids,
                embeddings=np.zeros((n, min(dimensions, max(n, 1)))),
                eigenvalues=np.zeros(max(dimensions, 1)),
                dimensions=dimensions,
            )

        H, node_list, edge_list = self.incidence_matrix_unsigned()
        node_ids = node_list
        n = len(node_ids)
        k = min(dimensions, n - 1)
        if k <= 0:
            return SpectralEmbeddingResult(
                node_ids=node_ids,
                embeddings=np.zeros((n, 1)),
                eigenvalues=np.zeros(1),
                dimensions=dimensions,
            )

        m = len(edge_list)
        W = np.zeros(m)
        for j, edge in enumerate(self._edges.values()):
            W[j] = edge.weight

        edge_map = self._edges
        D_e = np.array(
            [len(edge_map[eid].source_ids) + len(edge_map[eid].target_ids) for eid in edge_list], dtype=float
        )
        D_e_inv = np.where(D_e > 0, 1.0 / D_e, 0.0)

        D_v = H @ W
        D_v_inv_sqrt = np.where(D_v > 0, 1.0 / np.sqrt(D_v), 0.0)

        import scipy.sparse as sp
        import scipy.sparse.linalg as sla

        H_sp = sp.csr_matrix(H)
        W_sp = sp.diags(W)
        De_inv_sp = sp.diags(D_e_inv)
        Dv_inv_sqrt_sp = sp.diags(D_v_inv_sqrt)

        M = Dv_inv_sqrt_sp @ H_sp @ W_sp @ De_inv_sp @ H_sp.T @ Dv_inv_sqrt_sp

        try:
            eigenvalues, eigenvectors = sla.eigsh(M, k=k, which="LM")
            idx = np.argsort(-eigenvalues)
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]
        except Exception:
            eigenvalues = np.zeros(k)
            eigenvectors = np.zeros((n, k))

        return SpectralEmbeddingResult(
            node_ids=node_ids,
            embeddings=eigenvectors,
            eigenvalues=eigenvalues,
            dimensions=dimensions,
        )

    def transition_matrix(self) -> tuple[Any, list[str]]:
        """Compute the random walk transition matrix P = D_v^{-1} H W D_e^{-1} H^T.

        P[i, j] is the probability of transitioning from node i to node j
        in one step of a random walk on the hypergraph.

        Returns:
            Tuple of (P as scipy sparse matrix, node_id_list).
        """
        import numpy as np
        import scipy.sparse as sp

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0 or not self._edges:
            return sp.csr_matrix((0, 0)), node_list

        H, _, _ = self.incidence_matrix_unsigned()
        edge_list = list(self._edges.values())
        m = len(edge_list)

        W = np.array([e.weight for e in edge_list])
        D_e = np.array([len(e.source_ids) + len(e.target_ids) for e in edge_list], dtype=float)
        D_e_inv = np.where(D_e > 0, 1.0 / D_e, 0.0)

        H_sp = sp.csr_matrix(H)
        W_sp = sp.diags(W)
        De_inv_sp = sp.diags(D_e_inv)

        M = H_sp @ W_sp @ De_inv_sp @ H_sp.T
        D_v = np.array(M.sum(axis=1)).flatten()
        D_v_inv = np.where(D_v > 0, 1.0 / D_v, 0.0)

        P = sp.diags(D_v_inv) @ M
        return P.tocsr(), node_list

    def incidence_matrix_by_order(self, *, order: int) -> tuple[Any, list[str], list[str]]:
        """Return the incidence matrix filtered to edges of a specific order.

        Edge order is ``|node_ids| - 1``.  For example, pairwise edges have
        order 1 and 3-node edges have order 2.

        Args:
            order: The edge order to filter by.

        Returns:
            Tuple of (H_filtered, node_ids, edge_ids).
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        n = len(node_list)

        filtered_edges = [e for e in self._edges.values() if len(e.node_ids) - 1 == order]
        edge_ids = [e.id for e in filtered_edges]
        m = len(filtered_edges)

        if m == 0:
            return np.zeros((n, 0)), node_list, edge_ids

        H = np.zeros((n, m))
        for j, edge in enumerate(filtered_edges):
            for nid in edge.node_ids:
                if nid in node_idx:
                    H[node_idx[nid], j] = 1.0
        return H, node_list, edge_ids
