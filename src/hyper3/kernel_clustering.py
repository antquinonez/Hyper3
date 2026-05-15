"""ClusteringMixin: clustering coefficient, spectral clustering, transitivity."""
from __future__ import annotations

from hyper3.kernel_base import _GraphBase


class ClusteringMixin(_GraphBase):
    """Clustering coefficients and spectral clustering for hypergraphs.

    Computes local and average clustering coefficients, transitivity,
    square clustering, triangle counts, and spectral clustering via
    Laplacian eigenvectors and k-means.
    """

    def clustering_coefficient(self, node_id: str) -> float:
        """Compute the local clustering coefficient for a node.

        Measures the fraction of the node's neighbor pairs that are
        themselves connected.  Returns 0.0 for nodes with fewer than
        2 neighbors.

        Args:
            node_id: The ID of the node.

        Returns:
            Clustering coefficient in [0, 1].
        """
        nbrs = self.neighbors(node_id)
        k = len(nbrs)
        if k < 2:
            return 0.0
        pairs_with_edge = 0
        for i in range(len(nbrs)):
            u_nbrs = set(self.neighbors(nbrs[i]))
            for j in range(i + 1, len(nbrs)):
                if nbrs[j] in u_nbrs:
                    pairs_with_edge += 1
        return 2.0 * pairs_with_edge / (k * (k - 1))

    def average_clustering_coefficient(self) -> float:
        """Compute the mean clustering coefficient across all nodes with degree >= 2.

        Returns 0.0 if no node has degree >= 2.
        """
        coeffs = [
            self.clustering_coefficient(nid)
            for nid in self._nodes
            if len(self.incident_edges(nid)) >= 2
        ]
        if not coeffs:
            return 0.0
        return sum(coeffs) / len(coeffs)

    def transitivity(self) -> float:
        """Compute the global clustering coefficient (transitivity).

        Defined as ``3 * num_triangles / num_triads`` where a triad is a
        connected triple of nodes and a triangle is a triad where all
        three edges exist.

        Returns:
            Transitivity in [0, 1].  Returns 0.0 for graphs with fewer
            than 3 nodes or no triads.
        """
        node_ids = list(self._nodes.keys())
        n = len(node_ids)
        if n < 3:
            return 0.0

        triangles = 0
        triads = 0
        for i in range(n):
            nbrs_i = set(self.neighbors(node_ids[i]))
            for j in range(i + 1, n):
                if node_ids[j] not in nbrs_i:
                    continue
                nbrs_j = set(self.neighbors(node_ids[j]))
                shared = nbrs_i & nbrs_j
                common = nbrs_j
                for k in range(j + 1, n):
                    if node_ids[k] in shared:
                        triangles += 1
                    if node_ids[k] in common:
                        triads += 1

        if triads == 0:
            return 0.0
        return triangles / triads

    def square_clustering(self, node_id: str) -> float:
        """Compute the square clustering coefficient for a node.

        Uses the Lind-Gonzalez-Herrmann (2005) formulation: the fraction
        of possible squares that exist at the node.  Equivalent to
        ``nx.square_clustering`` on the undirected projection.

        Returns:
            Square clustering coefficient in [0, 1].  Returns 0.0 for
            nodes with fewer than 2 neighbors.
        """
        v_nbrs = set(self.neighbors(node_id))
        v_deg_m1 = len(v_nbrs) - 1
        if v_deg_m1 <= 0:
            return 0.0

        nbr_adj: dict[str, set[str]] = {}
        for u in v_nbrs:
            nbr_adj[u] = set(self.neighbors(u))

        uw_degrees = 0
        uw_count = len(v_nbrs) * v_deg_m1
        triangles = 0
        squares = 0

        for u in v_nbrs:
            u_nbrs = nbr_adj[u]
            uw_degrees += len(u_nbrs) * v_deg_m1
            p2 = len(u_nbrs & v_nbrs)
            triangles += p2
            squares += p2 * (p2 - 1)

        two_hop: set[str] = set()
        for u in v_nbrs:
            two_hop |= nbr_adj[u]
        two_hop -= v_nbrs
        two_hop.discard(node_id)
        for x in two_hop:
            x_nbrs = set(self.neighbors(x))
            p2 = len(v_nbrs & x_nbrs)
            squares += p2 * (p2 - 1)

        squares //= 2
        potential = uw_degrees - uw_count - triangles - squares
        return squares / potential if potential > 0 else 0.0

    def triangles(self, node_id: str) -> int:
        """Count the number of triangles containing the given node.

        A triangle is three mutually-connected nodes.  Uses the
        undirected projection (ignoring edge direction).

        Returns:
            Number of triangles.  Returns 0 for nodes with fewer than
            2 neighbors.
        """
        nbrs = self.neighbors(node_id)
        if len(nbrs) < 2:
            return 0

        count = 0
        for i in range(len(nbrs)):
            nbr_i_set = set(self.neighbors(nbrs[i]))
            for j in range(i + 1, len(nbrs)):
                if nbrs[j] in nbr_i_set:
                    count += 1
        return count

    def spectral_clustering(self, k: int = 2) -> list[set[str]]:
        """Partition nodes into k clusters using spectral embedding + k-means.

        Uses the bottom-k eigenvectors of the normalized Laplacian as
        features and runs k-means with 20 random restarts.

        Args:
            k: Number of clusters.

        Returns:
            List of sets, each containing the node IDs of one cluster.
            Returns a single cluster containing all nodes if k <= 1 or
            eigendecomposition fails.
        """
        import numpy as np
        import scipy.sparse as sp
        import scipy.sparse.linalg as sla

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return []

        L_norm, _ = self.normalized_laplacian()
        n_clusters = min(k, n)
        n_eigenvectors = min(n_clusters, n)
        if n_eigenvectors <= 0:
            return []

        try:
            if n_eigenvectors < n:
                eigenvalues, eigenvectors = sla.eigsh(sp.csr_matrix(L_norm), k=n_eigenvectors, which="SM")
            else:
                eigenvalues, eigenvectors = np.linalg.eigh(L_norm)
                eigenvectors = eigenvectors[:, :n_eigenvectors]
        except Exception:
            return [set(node_list)]

        if n_clusters == 1:
            return [set(node_list)]

        best_labels: np.ndarray | None = None
        best_wcss = float("inf")
        rng = np.random.RandomState(42)

        for _ in range(20):
            indices = rng.choice(n, n_clusters, replace=False)
            centroids = eigenvectors[indices].copy()

            for _ in range(100):
                dists = np.linalg.norm(eigenvectors[:, None, :] - centroids[None, :, :], axis=2)
                labels = np.argmin(dists, axis=1)
                new_centroids = np.zeros_like(centroids)
                for c in range(n_clusters):
                    members = eigenvectors[labels == c]
                    if len(members) > 0:
                        new_centroids[c] = members.mean(axis=0)
                    else:
                        new_centroids[c] = eigenvectors[rng.randint(n)]
                if np.allclose(centroids, new_centroids):
                    break
                centroids = new_centroids

            wcss = sum(
                np.sum((eigenvectors[labels == c] - centroids[c]) ** 2)
                for c in range(n_clusters)
            )
            if wcss < best_wcss:
                best_wcss = wcss
                best_labels = labels.copy()

        clusters: list[set[str]] = [set() for _ in range(n_clusters)]
        if best_labels is not None:
            for i, label in enumerate(best_labels):
                clusters[label].add(node_list[i])
        else:
            clusters[0] = set(node_list)
        return clusters
