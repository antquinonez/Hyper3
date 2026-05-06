"""
Equivalence: Community Detection
==================================
Cross-validates H3 community detection against NX, XGI, and HGX.

- Girvan-Newman vs NX community.girvan_newman
- Spectral clustering vs HGX HySC
- Hyperlink communities vs HGX hyperlink_communities
"""

from __future__ import annotations

import numpy as np
from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("community_detection")

    _test_girvan_newman_nx(t)
    _test_spectral_clustering_hgx(t)
    _test_hyperlink_communities_hgx(t)

    return t


def _test_girvan_newman_nx(t: EquivRunner) -> None:
    import networkx as nx
    from networkx.algorithms.community import girvan_newman

    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode
    from hyper3.community import CommunityDetector

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(8)]
    for n in nodes:
        g.add_node(n)
    pairs = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (3, 4)]
    for i, j in pairs:
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id, nodes[j].id}), target_ids=frozenset()))

    det = CommunityDetector(g)
    h3_result = det.detect_girvan_newman(n_communities=2)
    t.check("gn/h3_count", h3_result.community_count == 2,
            f"H3 communities={h3_result.community_count}")
    t.check("gn/h3_all_nodes", sum(c.size for c in h3_result.communities) == 8)

    G = nx.Graph()
    G.add_nodes_from(range(8))
    for i, j in pairs:
        G.add_edge(i, j)
    nx_communities = tuple(girvan_newman(G))
    first_split = nx_communities[0]
    nx_count = len(first_split)
    t.check("gn/nx_count", nx_count == 2, f"NX communities={nx_count}")

    nx_sizes = sorted(len(c) for c in first_split)
    h3_sizes = sorted(c.size for c in h3_result.communities)
    t.check("gn/sizes_match", nx_sizes == h3_sizes,
            f"NX sizes={nx_sizes}, H3 sizes={h3_sizes}")


def _test_spectral_clustering_hgx(t: EquivRunner) -> None:
    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(10)]
    for n in nodes:
        g.add_node(n)
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5),
             (5, 6), (6, 7), (7, 8), (8, 9), (0, 4), (5, 9)]
    for i, j in edges:
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))

    h3_clusters = g.spectral_clustering(k=2)
    t.check("sc/h3_count", len(h3_clusters) == 2, f"H3 clusters={len(h3_clusters)}")
    t.check("sc/h3_covers", sum(len(c) for c in h3_clusters) == 10)
    t.check("sc/h3_disjoint", len(set().union(*h3_clusters)) == 10)

    h3_3 = g.spectral_clustering(k=3)
    t.check("sc/h3_k3_count", len(h3_3) == 3, f"H3 k=3 clusters={len(h3_3)}")
    t.check("sc/h3_k3_covers", sum(len(c) for c in h3_3) == 10)

    import xgi
    H = xgi.Hypergraph(edges)
    xgi_clusters = xgi.spectral_clustering(H, k=2)
    t.check("sc/xgi_type", isinstance(xgi_clusters, dict))
    xgi_labels = set(xgi_clusters.values())
    t.check("sc/xgi_k_groups", len(xgi_labels) == 2, f"XGI groups={len(xgi_labels)}")

    h3_labels_set = set()
    node_id_to_idx = {n.id: i for i, n in enumerate(nodes)}
    for ci, cluster in enumerate(h3_clusters):
        for nid in cluster:
            h3_labels_set.add((node_id_to_idx[nid], ci))
    xgi_labels_set = set(xgi_clusters.items())
    h3_assignments = {idx: ci for idx, ci in h3_labels_set}
    xgi_assignments = dict(xgi_labels_set)
    agree = sum(1 for i in range(10) if h3_assignments.get(i) == xgi_assignments.get(i))
    disagree = 10 - agree
    agree_after_flip = sum(1 for i in range(10) if h3_assignments.get(i) != xgi_assignments.get(i))
    max_agree = max(agree, agree_after_flip)
    t.check("sc/agreement", max_agree >= 7,
            f"agreement={max_agree}/10")


def _test_hyperlink_communities_hgx(t: EquivRunner) -> None:
    import scipy.cluster.hierarchy as sch
    import scipy.spatial.distance as ssd

    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode
    from hyper3.community import CommunityDetector

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(6)]
    for n in nodes:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id, nodes[3].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id, nodes[4].id, nodes[5].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[4].id, nodes[5].id}), target_ids=frozenset()))

    det = CommunityDetector(g)
    h3_result = det.detect_hyperlink_communities(n_communities=2)
    t.check("hc/h3_has_communities", h3_result.community_count > 0)
    t.check("hc/h3_has_dendrogram", len(h3_result.dendrogram) > 0)
    t.check("hc/h3_has_edge_labels", len(h3_result.edge_labels) == 5)

    edge_sets = [frozenset({0, 1, 2}), frozenset({1, 2, 3}), frozenset({3, 4, 5}),
                 frozenset({0, 1}), frozenset({4, 5})]
    n_edges = 5
    adj: dict[int, list[int]] = {i: [] for i in range(6)}
    for idx, es in enumerate(edge_sets):
        for n in es:
            adj[n].append(idx)

    dist_matrix = np.ones((n_edges, n_edges))
    np.fill_diagonal(dist_matrix, 0.0)
    for edge_indices in adj.values():
        for i_pos in range(len(edge_indices)):
            for j_pos in range(i_pos + 1, len(edge_indices)):
                ei, ej = edge_indices[i_pos], edge_indices[j_pos]
                intersection = len(edge_sets[ei] & edge_sets[ej])
                union = len(edge_sets[ei] | edge_sets[ej])
                if union > 0:
                    dist_matrix[ei, ej] = 1.0 - intersection / union
                    dist_matrix[ej, ei] = 1.0 - intersection / union

    condensed = ssd.squareform(dist_matrix)
    ref_dendrogram = sch.linkage(condensed, method="average")
    t.check("hc/ref_dendrogram_shape", ref_dendrogram.shape[0] == 4)

    t.check("hc/dendrogram_match", np.allclose(h3_result.dendrogram, ref_dendrogram, atol=1e-10),
            f"H3 dendrogram differs from reference")


if __name__ == "__main__":
    t = run()
    t.print_report()
