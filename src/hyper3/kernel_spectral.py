from __future__ import annotations

from typing import Any

from hyper3.kernel_base import _GraphBase
from hyper3.results import AdjacencyTensorResult, SpectralEmbeddingResult


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
        for nid, val in zip(node_list, fiedler, strict=True):
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
            r = float(np.sqrt(mean_deg_sq / mean_deg)) if mean_deg > 0 else 1.0

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

    def adjacency_tensor(
        self,
        *,
        order: int | None = None,
        dense: bool = False,
    ) -> AdjacencyTensorResult:
        """Compute the order-(k) adjacency tensor for a k-uniform hypergraph.

        For a k-uniform hypergraph (all edges of size k), the adjacency
        tensor T is a symmetric order-k tensor where
        T[i1, i2, ..., ik] = sum of weights of hyperedges containing all
        of {i1, i2, ..., ik}.

        Nonzero entries are returned in COO (coordinate) format.

        Args:
            order: Edge order (size minus 1). If None, uses the most
                common edge order in the graph.
            dense: If True, also build a dense numpy array.

        Returns:
            AdjacencyTensorResult with COO entries and optional dense array.
        """
        import numpy as np

        size_counts: dict[int, int] = {}
        for e in self._edges.values():
            s = len(e.node_ids)
            size_counts[s] = size_counts.get(s, 0) + 1

        if not size_counts:
            node_list = [n.id for n in self._nodes.values()]
            return AdjacencyTensorResult(n_nodes=len(node_list), node_ids=node_list)

        if order is None:  # noqa: SIM108
            k = max(size_counts, key=lambda s: size_counts[s])
        else:
            k = order + 1

        node_list = [n.id for n in self._nodes.values()]
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        n = len(node_list)

        entries: dict[tuple[int, ...], float] = {}
        for edge in self._edges.values():
            if len(edge.node_ids) != k:
                continue
            indices = sorted(node_idx[nid] for nid in edge.node_ids if nid in node_idx)
            if len(indices) != k:
                continue
            key = tuple(indices)
            entries[key] = entries.get(key, 0.0) + edge.weight

        if not entries:
            return AdjacencyTensorResult(
                order=k - 1, n_nodes=n, node_ids=node_list,
            )

        coords = np.array(list(entries.keys()), dtype=np.int32)
        values = np.array(list(entries.values()), dtype=np.float64)

        result = AdjacencyTensorResult(
            order=k - 1,
            n_nodes=n,
            n_nonzero=len(entries),
            coords=coords,
            values=values,
            node_ids=node_list,
        )

        if dense:
            shape = (n,) * k
            T = np.zeros(shape, dtype=np.float64)
            for idx_arr, val in zip(coords, values, strict=True):
                T[tuple(idx_arr)] += val
            result.dense_tensor = T

        return result

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

    def multiorder_laplacian(self, sigmas: dict[int, float]) -> Any:
        """Compute the multiorder Laplacian as a weighted sum of per-order Laplacians.

        For each edge order *d*, computes the order-*d* Laplacian from
        the incidence matrix of that order, then takes the weighted sum
        using the provided sigma weights.

        Args:
            sigmas: Mapping from edge order to weight.  For example
                ``{1: 1.0, 2: 0.5}`` weights pairwise edges at 1.0 and
                triple edges at 0.5.

        Returns:
            A numpy array of shape (n_nodes, n_nodes).
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return np.zeros((0, 0))

        L_total = np.zeros((n, n))
        for order, sigma in sigmas.items():
            H_ord, _, _ = self.incidence_matrix_by_order(order=order)
            if H_ord.shape[1] == 0:
                continue
            D_v = np.diag(np.asarray(H_ord.sum(axis=1)).flatten())
            L_ord = D_v - H_ord @ H_ord.T
            L_total += sigma * L_ord
        return L_total

    def multiorder_laplacian_eigenvalues(self, sigmas: dict[int, float]) -> Any:
        """Compute eigenvalues of the multiorder Laplacian.

        Args:
            sigmas: Mapping from edge order to weight.

        Returns:
            Sorted numpy array of eigenvalues.
        """
        import numpy as np

        L = np.asarray(self.multiorder_laplacian(sigmas))
        return np.sort(np.linalg.eigvalsh(L))

    def dual_random_walk_adjacency(self) -> tuple[Any, list[str], list[str]]:
        """Compute the dual random walk adjacency matrix (edge-edge adjacency).

        Two hyperedges are adjacent if they share at least one vertex.
        The dual adjacency is ``H^T @ H`` from the unsigned incidence
        matrix, with the diagonal (self-loops) removed.

        Returns:
            Tuple of (A_dual, edge_ids, edge_ids).
        """
        import numpy as np

        H, node_ids, edge_ids = self.incidence_matrix_unsigned()
        m = len(edge_ids)
        if m == 0:
            return np.zeros((0, 0)), [], []

        A_dual = H.T @ H
        np.fill_diagonal(A_dual, 0)
        return A_dual, edge_ids, edge_ids

    def random_walk(self, source: str, *, steps: int = 100) -> list[str]:
        """Simulate a single-node random walk on the hypergraph.

        Starting from ``source``, at each step the walker moves to a
        neighboring node with probability proportional to the transition
        matrix entry.  Uses the incidence-based transition matrix.

        Args:
            source: Starting node ID.
            steps: Number of walk steps.

        Returns:
            List of visited node IDs (length ``steps + 1``).
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0 or source not in self._nodes:
            return []

        P, node_list = self.transition_matrix()
        P_arr = np.asarray(P.todense())
        node_idx = {nid: i for i, nid in enumerate(node_list)}

        current = node_idx.get(source)
        if current is None:
            return [source]

        rng = np.random.RandomState()
        path = [source]
        for _ in range(steps):
            row = P_arr[current]
            if row.sum() == 0:
                break
            probs = row / row.sum()
            next_idx = rng.choice(len(probs), p=probs)
            path.append(node_list[next_idx])
            current = next_idx
        return path

    def random_walk_density(self, rho: list[float] | Any, *, steps: int = 10) -> Any:
        """Evolve a density vector via repeated transition matrix multiplication.

        Starting from density vector ``rho``, applies ``rho <- rho @ P``
        for ``steps`` iterations.  The result is the density distribution
        after ``steps`` steps of a random walk.

        Args:
            rho: Initial density vector (length n_nodes).  Can be a list
                or numpy array.
            steps: Number of walk steps.

        Returns:
            Numpy array of shape (n_nodes,) with the evolved density.
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return np.array([])

        P, _ = self.transition_matrix()
        P_arr = np.asarray(P.todense())
        rho_arr = np.asarray(rho, dtype=float).flatten()
        if len(rho_arr) != n:
            return rho_arr

        for _ in range(steps):
            rho_arr = rho_arr @ P_arr
        return rho_arr

    def stationary_state(self) -> tuple[list[str], list[float]]:
        """Compute the stationary distribution of the random walk.

        Returns:
            Tuple of (node_ids, stationary_probabilities).
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return [], []

        P, _ = self.transition_matrix()
        P_arr = np.asarray(P.todense())

        eigenvalues, eigenvectors = np.linalg.eig(P_arr.T)
        idx = np.argmin(np.abs(eigenvalues - 1.0))
        pi = np.real(eigenvectors[:, idx])
        pi = np.abs(pi)
        total = pi.sum()
        if total > 0:
            pi = pi / total
        return node_list, pi.tolist()

    def encapsulation_dag(self) -> list[tuple[str, str]]:
        edge_list = list(self._edges.values())
        result: list[tuple[str, str]] = []
        for i in range(len(edge_list)):
            for j in range(len(edge_list)):
                if i == j:
                    continue
                ni = edge_list[i].node_ids
                nj = edge_list[j].node_ids
                if ni < nj:
                    result.append((edge_list[i].id, edge_list[j].id))
        return result

    def simpliciality(self) -> float:
        edge_sets = [e.node_ids for e in self._edges.values()]
        if len(edge_sets) < 2:
            return 1.0
        containment_total = 0
        containment_satisfied = 0
        for i in range(len(edge_sets)):
            for j in range(len(edge_sets)):
                if i == j:
                    continue
                if edge_sets[i] < edge_sets[j]:
                    containment_total += 1
                    containment_satisfied += 1
        if containment_total == 0:
            return 1.0
        return containment_satisfied / containment_total

    def _build_simplex_index(self) -> dict[int, list[frozenset[str]]]:
        simplices: dict[int, set[frozenset[str]]] = {}
        for node_id in self._nodes:
            s = frozenset({node_id})
            simplices.setdefault(0, set()).add(s)
        for edge in self._edges.values():
            members = sorted(edge.node_ids)
            from itertools import combinations
            for k in range(1, len(members) + 1):
                for face in combinations(members, k):
                    dim = k - 1
                    simplices.setdefault(dim, set()).add(frozenset(face))
        return {dim: sorted(simplex_set, key=lambda s: sorted(s)) for dim, simplex_set in sorted(simplices.items())}

    def face_enumeration(self, simplex: frozenset[str]) -> dict[str, list[frozenset[str]]]:
        all_simplices: set[frozenset[str]] = set()
        for node_id in self._nodes:
            all_simplices.add(frozenset({node_id}))
        for edge in self._edges.values():
            members = sorted(edge.node_ids)
            from itertools import combinations
            for k in range(1, len(members) + 1):
                for face in combinations(members, k):
                    all_simplices.add(frozenset(face))
        faces: list[frozenset[str]] = []
        cofaces: list[frozenset[str]] = []
        for s in all_simplices:
            if s < simplex and s != simplex:
                faces.append(s)
            elif simplex < s and s != simplex:
                cofaces.append(s)
        return {"faces": sorted(faces, key=lambda s: (len(s), sorted(s))), "cofaces": sorted(cofaces, key=lambda s: (len(s), sorted(s)))}

    def boundary_operator(self, k: int) -> dict[frozenset[str], list[tuple[frozenset[str], int]]]:
        simplex_index = self._build_simplex_index()
        k_simplices = simplex_index.get(k, [])
        if not k_simplices or k == 0:
            return {}
        km1_simplices = simplex_index.get(k - 1, [])
        km1_lookup = {s: idx for idx, s in enumerate(km1_simplices)}
        result: dict[frozenset[str], list[tuple[frozenset[str], int]]] = {}
        for sigma in k_simplices:
            boundary: list[tuple[frozenset[str], int]] = []
            members = sorted(sigma)
            for i in range(len(members)):
                face = frozenset(members[:i] + members[i + 1:])
                if face in km1_lookup:
                    sign = (-1) ** i
                    boundary.append((face, sign))
            result[sigma] = boundary
        return result

    def hodge_matrix(self, k: int) -> tuple[Any, list[frozenset[str]], list[frozenset[str]]]:
        import numpy as np

        simplex_index = self._build_simplex_index()
        k_simplices = simplex_index.get(k, [])
        km1_simplices = simplex_index.get(k - 1, []) if k > 0 else []
        if not k_simplices:
            return np.zeros((0, 0)), [], []
        km1_lookup = {s: idx for idx, s in enumerate(km1_simplices)}
        n_km1 = len(km1_simplices)
        n_k = len(k_simplices)
        B = np.zeros((n_km1, n_k))
        for j, sigma in enumerate(k_simplices):
            members = sorted(sigma)
            for i in range(len(members)):
                face = frozenset(members[:i] + members[i + 1:])
                if face in km1_lookup:
                    B[km1_lookup[face], j] = (-1.0) ** i
        return B, k_simplices, km1_simplices

    def hodge_laplacian(self, k: int) -> Any:
        import numpy as np

        simplex_index = self._build_simplex_index()
        k_simplices = simplex_index.get(k, [])
        if not k_simplices:
            return np.zeros((0, 0))
        n_k = len(k_simplices)
        Bk, _, _ = self.hodge_matrix(k)
        if Bk.shape[0] == 0 and Bk.shape[1] == 0:
            return np.zeros((n_k, n_k))
        lower = Bk.T @ Bk if Bk.shape[0] > 0 else np.zeros((n_k, n_k))
        Bk1, _, _ = self.hodge_matrix(k + 1)
        upper = Bk1 @ Bk1.T if Bk1.shape[0] > 0 and Bk1.shape[1] > 0 else np.zeros((n_k, n_k))
        if lower.shape != (n_k, n_k):
            lower = np.zeros((n_k, n_k))
        if upper.shape != (n_k, n_k):
            upper = np.zeros((n_k, n_k))
        return lower + upper

    def betti_curve(self, max_dim: int | None = None) -> list[int]:
        import numpy as np

        simplex_index = self._build_simplex_index()
        if not simplex_index:
            return []
        max_d = max(simplex_index.keys()) if max_dim is None else min(max_dim, max(simplex_index.keys()))
        betti: list[int] = []
        for k in range(max_d + 1):
            L = self.hodge_laplacian(k)
            if L.shape[0] == 0:
                betti.append(0)
                continue
            eigenvalues = np.linalg.eigvalsh(L)
            betti.append(int(sum(1 for ev in eigenvalues if abs(ev) < 1e-10)))
        return betti

    def persistence_diagram(self) -> list[tuple[int, float, float | None]]:
        import numpy as np

        if not self._edges:
            return []
        edges_sorted = sorted(self._edges.values(), key=lambda e: e.weight)
        thresholds = sorted(set(e.weight for e in edges_sorted))
        node_ids = set(self._nodes.keys())
        prev_betti: list[int] = [len(node_ids)]
        result: list[tuple[int, float, float | None]] = []
        birth_map: dict[int, list[float]] = {0: [0.0] * len(node_ids)}

        for thresh in thresholds:
            active_edges = [e for e in edges_sorted if e.weight <= thresh]
            sub = self._subgraph_at_threshold(active_edges)
            components = sub.connected_components()
            curr_betti = [len(components)]
            simplexes = sub._build_simplex_index()
            max_d = max(simplexes.keys()) if simplexes else 0
            for k in range(1, max_d + 1):
                L = sub.hodge_laplacian(k)
                if L.shape[0] == 0:
                    curr_betti.append(0)
                else:
                    eigenvalues = np.linalg.eigvalsh(L)
                    curr_betti.append(int(sum(1 for ev in eigenvalues if abs(ev) < 1e-10)))
            for dim in range(max(len(prev_betti), len(curr_betti))):
                pb = prev_betti[dim] if dim < len(prev_betti) else 0
                cb = curr_betti[dim] if dim < len(curr_betti) else 0
                if cb > pb:
                    for _ in range(cb - pb):
                        birth_map.setdefault(dim, []).append(thresh)
                elif cb < pb:
                    for _ in range(pb - cb):
                        births = birth_map.get(dim, [])
                        if births:
                            b = births.pop()
                            result.append((dim, b, thresh))
            prev_betti = curr_betti

        for dim, births in birth_map.items():
            result.extend((dim, b, None) for b in births)
        return sorted(result, key=lambda x: (x[0], x[1]))

    def _subgraph_at_threshold(self, active_edges: list[Any]) -> Any:
        from hyper3.kernel import Hypergraph
        from hyper3.kernel_types import Hyperedge, Hypernode

        sub = Hypergraph()
        for node in self._nodes.values():
            sub.add_node(Hypernode(id=node.id, label=node.label))
        for edge in active_edges:
            sub.add_edge(Hyperedge(
                source_ids=edge.source_ids,
                target_ids=edge.target_ids,
                weight=edge.weight,
            ))
        return sub
