from __future__ import annotations

from hyper3.kernel_base import _GraphBase


class ClusteringMixin(_GraphBase):

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
