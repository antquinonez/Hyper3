from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class Community(_SimpleResultBase):
    """A single community detected in the hypergraph, with membership and modularity stats."""

    community_id: int
    member_ids: list[str] = field(default_factory=list)
    member_labels: list[str] = field(default_factory=list)
    size: int = 0
    internal_edges: int = 0
    external_edges: int = 0
    modularity_contribution: float = 0.0


@dataclass
class CommunityResult(_SimpleResultBase):
    """Aggregate result of community detection, listing all communities and overall metrics."""

    communities: list[Community] = field(default_factory=list)
    community_count: int = 0
    modularity: float = 0.0
    coverage: float = 0.0
    largest_community_size: int = 0
    avg_community_size: float = 0.0


@dataclass
class HierarchicalCommunityResult(_SimpleResultBase):
    communities: list[Community] = field(default_factory=list)
    community_count: int = 0
    dendrogram: list[list[float]] = field(default_factory=list)
    edge_labels: dict[int, int] = field(default_factory=dict)
    linkage_method: str = "average"


class CommunityDetector:
    """Identifies communities (clusters) in a hypergraph via label propagation and connected-components algorithms."""

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize with a reference to the hypergraph for community detection."""
        self._graph = graph

    def detect_label_propagation(
        self,
        *,
        max_iterations: int = 100,
        seed: int | None = None,
        edge_label: str | None = None,
        weighted_fallback: bool = True,
    ) -> CommunityResult:
        """Detect communities using label propagation; optionally retries with weighted propagation.

        Non-deterministic even with a fixed seed: the initial node iteration order
        depends on hash-based dict ordering, so community IDs, counts, and modularity
        may vary across process invocations. The structural partition (which nodes
        group together) is more stable than the specific IDs assigned.
        """
        if seed is not None:
            random.seed(seed)

        node_ids = [n.id for n in self._graph.nodes]
        if not node_ids:
            return CommunityResult()

        labels: dict[str, int] = {nid: i for i, nid in enumerate(node_ids)}

        neighbor_map = self._build_neighbor_map(edge_label)

        for _ in range(max_iterations):
            changed = False
            order = list(node_ids)
            random.shuffle(order)
            for nid in order:
                new_label = self._update_node_label(nid, labels, neighbor_map)
                if new_label is not None and new_label != labels[nid]:
                    labels[nid] = new_label
                    changed = True
            if not changed:
                break

        result = self._build_result(labels, neighbor_map)

        if weighted_fallback and result.modularity < 0:
            weighted = self.detect_weighted_label_propagation(
                max_iterations=max_iterations,
                seed=seed,
                edge_label=edge_label,
            )
            if weighted.modularity > result.modularity:
                return weighted

        return result

    def detect_weighted_label_propagation(
        self,
        *,
        max_iterations: int = 100,
        seed: int | None = None,
        edge_label: str | None = None,
    ) -> CommunityResult:
        """Detect communities using weighted label propagation."""
        if seed is not None:
            random.seed(seed)

        node_ids = [n.id for n in self._graph.nodes]
        if not node_ids:
            return CommunityResult()

        labels: dict[str, int] = {nid: i for i, nid in enumerate(node_ids)}
        neighbor_map = self._build_neighbor_map(edge_label)

        for _ in range(max_iterations):
            changed = False
            order = list(node_ids)
            random.shuffle(order)
            for nid in order:
                neighbors = neighbor_map.get(nid, [])
                if not neighbors:
                    continue
                label_weights: dict[int, float] = {}
                for nb_id, weight in neighbors:
                    nb_label = labels.get(nb_id, 0)
                    label_weights[nb_label] = label_weights.get(nb_label, 0.0) + weight
                if not label_weights:
                    continue
                max_weight = max(label_weights.values())
                best_labels = [l for l, w in label_weights.items() if w >= max_weight - 1e-9]
                new_label = random.choice(best_labels)
                if new_label != labels[nid]:
                    labels[nid] = new_label
                    changed = True
            if not changed:
                break

        return self._build_result(labels, neighbor_map)

    def detect_connected_components(self) -> CommunityResult:
        """Detect communities using structural connected components."""
        components = self._graph.connected_components()
        labels: dict[str, int] = {}
        for i, comp in enumerate(components):
            for nid in comp:
                labels[nid] = i

        neighbor_map = self._build_neighbor_map(None)
        return self._build_result(labels, neighbor_map)

    def detect_louvain(
        self,
        *,
        resolution: float = 1.0,
        max_passes: int = 10,
        seed: int | None = None,
        edge_label: str | None = None,
    ) -> CommunityResult:
        """Detect communities using the Louvain modularity maximization algorithm, returning community assignments and modularity score."""
        rng = random.Random(seed)

        node_ids = [n.id for n in self._graph.nodes]
        if not node_ids:
            return CommunityResult()

        neighbor_map = self._build_neighbor_map(edge_label)

        edge_weight: dict[frozenset[str], float] = {}
        for nid, neighbors in neighbor_map.items():
            for nb_id, w in neighbors:
                pair = frozenset({nid, nb_id})
                if pair not in edge_weight:
                    edge_weight[pair] = w

        cur_adj: dict[str, dict[str, float]] = {nid: {} for nid in node_ids}
        cur_deg: dict[str, float] = {nid: 0.0 for nid in node_ids}
        for pair, w in edge_weight.items():
            a, b = list(pair)
            cur_adj[a][b] = cur_adj[a].get(b, 0.0) + w
            cur_deg[a] += w
            cur_adj[b][a] = cur_adj[b].get(a, 0.0) + w
            cur_deg[b] += w

        m2 = sum(cur_deg[nid] for nid in node_ids)
        if m2 == 0.0:
            labels = {nid: i for i, nid in enumerate(node_ids)}
            return self._build_result(labels, neighbor_map)

        membership: dict[str, set[str]] = {nid: {nid} for nid in node_ids}
        cur_nodes = list(node_ids)
        self_loop: dict[str, float] = {nid: 0.0 for nid in node_ids}
        final_comm: dict[str, int] = {}

        for _pass in range(max_passes):
            comm: dict[str, int] = {n: i for i, n in enumerate(cur_nodes)}
            sigma_tot: dict[int, float] = {}
            sigma_in: dict[int, float] = {}
            for n in cur_nodes:
                c = comm[n]
                sigma_tot[c] = sigma_tot.get(c, 0.0) + cur_deg.get(n, 0.0)
            for n in cur_nodes:
                c = comm[n]
                for nb, w in cur_adj.get(n, {}).items():
                    if comm.get(nb) == c:
                        sigma_in[c] = sigma_in.get(c, 0.0) + w
                sl = self_loop.get(n, 0.0)
                if sl > 0:
                    sigma_in[c] = sigma_in.get(c, 0.0) + sl
            for c in sigma_in:
                sigma_in[c] /= 2.0

            for _iter in range(200):
                moved = False
                order = list(cur_nodes)
                rng.shuffle(order)
                for node in order:
                    k_i = cur_deg.get(node, 0.0)
                    if k_i == 0.0:
                        continue
                    c_i = comm[node]

                    k_i_to: dict[int, float] = {}
                    for nb, w in cur_adj.get(node, {}).items():
                        nb_c = comm.get(nb)
                        if nb_c is not None:
                            k_i_to[nb_c] = k_i_to.get(nb_c, 0.0) + w

                    k_i_self = k_i_to.pop(c_i, 0.0)

                    best_delta = 0.0
                    best_c = c_i
                    for target_c, k_i_c in k_i_to.items():
                        st_t = sigma_tot.get(target_c, 0.0)
                        si_t = sigma_in.get(target_c, 0.0)
                        delta = (si_t + 2.0 * k_i_c) / m2 - resolution * ((st_t + k_i) / m2) ** 2
                        delta -= si_t / m2 - resolution * (st_t / m2) ** 2 - resolution * (k_i / m2) ** 2
                        if delta > best_delta or (abs(delta - best_delta) < 1e-12 and target_c < best_c):
                            best_delta = delta
                            best_c = target_c

                    st_i = sigma_tot.get(c_i, 0.0)
                    si_i = sigma_in.get(c_i, 0.0)
                    stay_delta = (si_i + 2.0 * k_i_self) / m2 - resolution * ((st_i + k_i) / m2) ** 2
                    stay_delta -= si_i / m2 - resolution * (st_i / m2) ** 2 - resolution * (k_i / m2) ** 2
                    if stay_delta >= best_delta:
                        best_c = c_i

                    if best_c != c_i:
                        k_i_target = k_i_to.get(best_c, 0.0)
                        sigma_tot[c_i] = sigma_tot.get(c_i, 0.0) - k_i
                        sigma_tot[best_c] = sigma_tot.get(best_c, 0.0) + k_i
                        sigma_in[c_i] = sigma_in.get(c_i, 0.0) - k_i_self
                        sigma_in[best_c] = sigma_in.get(best_c, 0.0) + k_i_target
                        for nb, w in cur_adj.get(node, {}).items():
                            if comm.get(nb) == best_c and nb != node:
                                sigma_in[best_c] = sigma_in.get(best_c, 0.0) + w
                        comm[node] = best_c
                        moved = True

                if not moved:
                    break

            final_comm = dict(comm)

            comm_groups: dict[int, list[str]] = {}
            for n in cur_nodes:
                comm_groups.setdefault(comm[n], []).append(n)

            if len(comm_groups) == len(cur_nodes):
                break

            new_adj: dict[str, dict[str, float]] = {}
            new_deg: dict[str, float] = {}
            new_membership: dict[str, set[str]] = {}
            new_comm: dict[str, int] = {}
            sn_of: dict[int, str] = {}
            self_loop: dict[str, float] = {}

            for new_id, (old_c, members) in enumerate(comm_groups.items()):
                sn = f"__{new_id}"
                sn_of[old_c] = sn
                new_comm[sn] = new_id
                new_adj[sn] = {}
                new_deg[sn] = 0.0
                self_loop[sn] = 0.0
                merged: set[str] = set()
                for m in members:
                    merged |= membership.get(m, {m})
                new_membership[sn] = merged

            for node in cur_nodes:
                sn_src = sn_of[comm[node]]
                for nb, w in cur_adj.get(node, {}).items():
                    nb_comm = comm.get(nb)
                    if nb_comm is None:
                        continue
                    sn_tgt = sn_of.get(nb_comm)
                    if sn_tgt is None:
                        continue
                    if sn_src == sn_tgt:
                        self_loop[sn_src] += w
                    else:
                        new_adj[sn_src][sn_tgt] = new_adj[sn_src].get(sn_tgt, 0.0) + w
                        new_deg[sn_src] += w

            for sn in new_comm:
                new_deg[sn] += self_loop.get(sn, 0.0)

            cur_nodes = list(new_comm.keys())
            cur_adj = new_adj
            cur_deg = new_deg
            membership = new_membership
            self_loop = {sn: 0.0 for sn in cur_nodes}

            if len(comm_groups) <= 1:
                break

        final_labels: dict[str, int] = {}
        cid_map: dict[int, int] = {}
        next_cid = 0
        for sn in cur_nodes:
            c = final_comm.get(sn, 0)
            if c not in cid_map:
                cid_map[c] = next_cid
                next_cid += 1
            for orig_nid in membership[sn]:
                final_labels[orig_nid] = cid_map[c]

        return self._build_result(final_labels, neighbor_map)

    def detect_girvan_newman(
        self,
        *,
        n_communities: int = 2,
        edge_label: str | None = None,
    ) -> CommunityResult:
        """Detect communities using the Girvan-Newman edge-betweenness algorithm with optional level selection."""
        neighbor_map = self._build_neighbor_map(edge_label)
        adj: dict[str, dict[str, float]] = {}
        for nid, neighbors in neighbor_map.items():
            for nb_id, w in neighbors:
                adj.setdefault(nid, {})[nb_id] = w
        for n in self._graph.nodes:
            adj.setdefault(n.id, {})

        for edge in self._graph.edges:
            if edge_label and edge.label != edge_label:
                continue
            if not edge.target_ids:
                members = list(edge.node_ids)
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        adj.setdefault(members[i], {})[members[j]] = edge.weight
                        adj.setdefault(members[j], {})[members[i]] = edge.weight

        node_ids = [n.id for n in self._graph.nodes]
        if not node_ids:
            return CommunityResult()

        current_adj: dict[str, dict[str, float]] = {
            nid: dict(adj.get(nid, {})) for nid in node_ids
        }

        while True:
            labels = self._connected_labels(current_adj, node_ids)
            groups: dict[int, list[str]] = {}
            for nid, lab in labels.items():
                groups.setdefault(lab, []).append(nid)
            if len(groups) >= n_communities:
                break
            bridge = self._highest_betweenness_edge(current_adj, node_ids)
            if bridge is None:
                break
            a, b = bridge
            current_adj.get(a, {}).pop(b, None)
            current_adj.get(b, {}).pop(a, None)

        return self._build_result(labels, neighbor_map)

    @staticmethod
    def _connected_labels(
        adj: dict[str, dict[str, float]],
        node_ids: list[str],
    ) -> dict[str, int]:
        """Assign community labels to nodes via BFS over an adjacency map."""
        labels: dict[str, int] = {}
        visited: set[str] = set()
        label = 0
        for start in node_ids:
            if start in visited:
                continue
            queue = [start]
            visited.add(start)
            while queue:
                nid = queue.pop(0)
                labels[nid] = label
                for nb in adj.get(nid, {}):
                    if nb not in visited:
                        visited.add(nb)
                        queue.append(nb)
            label += 1
        return labels

    @staticmethod
    def _highest_betweenness_edge(
        adj: dict[str, dict[str, float]],
        node_ids: list[str],
    ) -> tuple[str, str] | None:
        """Return the edge with the highest betweenness centrality from an adjacency map."""
        edge_count: dict[frozenset[str], float] = defaultdict(float)
        for source in node_ids:
            dist: dict[str, float] = {source: 0.0}
            sigma: dict[str, float] = defaultdict(float)
            sigma[source] = 1.0
            pred: dict[str, list[str]] = defaultdict(list)
            queue = [source]
            while queue:
                nid = queue.pop(0)
                for nb in adj.get(nid, {}):
                    if nb not in dist:
                        dist[nb] = dist[nid] + 1
                        queue.append(nb)
                    if dist.get(nb) == dist[nid] + 1:
                        sigma[nb] += sigma[nid]
                        pred[nb].append(nid)

            delta: dict[str, float] = defaultdict(float)
            reverse_order = sorted(
                [n for n in dist if n != source],
                key=lambda n: dist[n],
                reverse=True,
            )
            for nid in reverse_order:
                for p in pred[nid]:
                    contrib = sigma[p] / sigma[nid] * (1.0 + delta[nid])
                    pair = frozenset({p, nid})
                    edge_count[pair] += contrib
                    delta[p] += contrib

        if not edge_count:
            return None
        best = max(edge_count, key=lambda k: edge_count[k])
        a, b = list(best)
        return (a, b)

    def detect_hyperlink_communities(
        self,
        *,
        cut_height: float | None = None,
        n_communities: int | None = None,
    ) -> HierarchicalCommunityResult:
        """Detect communities based on hyperlink (shared-edge) co-membership, grouping nodes that participate in the same hyperedges."""
        import numpy as np

        edges_list = list(self._graph.edges)
        if not edges_list:
            return HierarchicalCommunityResult()

        n_edges = len(edges_list)
        edge_members: list[frozenset[str]] = [frozenset(e.node_ids) for e in edges_list]

        node_to_edges: dict[str, list[int]] = defaultdict(list)
        for idx, members in enumerate(edge_members):
            for nid in members:
                node_to_edges[nid].append(idx)

        dist_matrix = np.ones((n_edges, n_edges), dtype=float)
        np.fill_diagonal(dist_matrix, 0.0)

        for edge_indices in node_to_edges.values():
            for i_pos in range(len(edge_indices)):
                for j_pos in range(i_pos + 1, len(edge_indices)):
                    ei = edge_indices[i_pos]
                    ej = edge_indices[j_pos]
                    if dist_matrix[ei, ej] < 1.0:
                        continue
                    intersection = len(edge_members[ei] & edge_members[ej])
                    union = len(edge_members[ei] | edge_members[ej])
                    if union > 0:
                        jaccard = intersection / union
                        dist_matrix[ei, ej] = 1.0 - jaccard
                        dist_matrix[ej, ei] = 1.0 - jaccard

        import scipy.cluster.hierarchy as sch
        import scipy.spatial.distance as ssd

        condensed = ssd.squareform(dist_matrix)
        dendrogram = sch.linkage(condensed, method="average")

        if cut_height is not None:
            labels_arr = sch.fcluster(dendrogram, t=cut_height, criterion="distance")
        elif n_communities is not None:
            labels_arr = sch.fcluster(dendrogram, t=n_communities, criterion="maxclust")
        else:
            labels_arr = sch.fcluster(dendrogram, t=2, criterion="maxclust")

        edge_labels_map: dict[int, int] = {}
        for idx, lab in enumerate(labels_arr):
            edge_labels_map[idx] = int(lab) - 1

        node_community: dict[str, set[int]] = defaultdict(set)
        for idx, members in enumerate(edge_members):
            for nid in members:
                node_community[nid].add(edge_labels_map[idx])

        node_ids = [n.id for n in self._graph.nodes]
        overlap_groups: dict[int, set[str]] = defaultdict(set)
        for nid in node_ids:
            if nid not in node_community or not node_community[nid]:
                continue
            for ec in sorted(node_community[nid]):
                overlap_groups[ec].add(nid)

        communities: list[Community] = []
        for cid in sorted(overlap_groups):
            members = list(overlap_groups[cid])
            if not members:
                continue
            member_lab: list[str] = []
            for nid in members:
                node = self._graph.get_node(nid)
                member_lab.append(node.label if node else nid[:8])
            communities.append(
                Community(
                    community_id=cid,
                    member_ids=members,
                    member_labels=member_lab,
                    size=len(members),
                )
            )

        communities.sort(key=lambda c: c.size, reverse=True)

        return HierarchicalCommunityResult(
            communities=communities,
            community_count=len(communities),
            dendrogram=dendrogram.tolist(),
            edge_labels=edge_labels_map,
            linkage_method="average",
        )

    def _build_neighbor_map(
        self,
        edge_label: str | None,
    ) -> dict[str, list[tuple[str, float]]]:
        """Build a map from node ID to list of (neighbor_id, weight) pairs."""
        neighbor_map: dict[str, list[tuple[str, float]]] = {}
        for node in self._graph.nodes:
            node_id = node.id
            for edge in self._graph.outgoing_edges(node_id):
                if edge_label and edge.label != edge_label:
                    continue
                for tgt in edge.target_ids:
                    if tgt != node_id:
                        neighbor_map.setdefault(node_id, []).append((tgt, edge.weight))
            for edge in self._graph.incoming_edges(node_id):
                if edge_label and edge.label != edge_label:
                    continue
                for src in edge.source_ids:
                    if src != node_id:
                        neighbor_map.setdefault(node_id, []).append((src, edge.weight))
        return neighbor_map

    def _update_node_label(
        self,
        nid: str,
        labels: dict[str, int],
        neighbor_map: dict[str, list[tuple[str, float]]],
    ) -> int | None:
        """Pick the most frequent label among neighbors for label propagation."""
        neighbors = neighbor_map.get(nid, [])
        if not neighbors:
            return None
        label_counts: dict[int, int] = {}
        for nb_id, _weight in neighbors:
            nb_label = labels.get(nb_id, 0)
            label_counts[nb_label] = label_counts.get(nb_label, 0) + 1
        if not label_counts:
            return None
        max_count = max(label_counts.values())
        best_labels = [l for l, c in label_counts.items() if c == max_count]
        return random.choice(best_labels)

    def _build_result(
        self,
        labels: dict[str, int],
        neighbor_map: dict[str, list[tuple[str, float]]],
    ) -> CommunityResult:
        """Assemble a CommunityResult from label-to-node-ID mapping with modularity and weight statistics."""
        communities_dict: dict[int, list[str]] = {}
        for nid, label in labels.items():
            communities_dict.setdefault(label, []).append(nid)

        edge_weight: dict[frozenset[str], float] = {}
        for nid, neighbors in neighbor_map.items():
            for nb_id, w in neighbors:
                pair = frozenset({nid, nb_id})
                if pair not in edge_weight:
                    edge_weight[pair] = w

        total_weight = sum(edge_weight.values())
        if total_weight == 0:
            total_weight = 1.0

        weighted_deg: dict[str, float] = {}
        for pair, w in edge_weight.items():
            a, b = list(pair)
            weighted_deg[a] = weighted_deg.get(a, 0.0) + w
            weighted_deg[b] = weighted_deg.get(b, 0.0) + w

        communities: list[Community] = []
        total_modularity = 0.0

        for cid, members in communities_dict.items():
            member_set = set(members)
            internal_weight = 0.0
            external_weight = 0.0
            community_degree = 0.0

            for nid in members:
                community_degree += weighted_deg.get(nid, 0.0)

            for pair, w in edge_weight.items():
                nodes = list(pair)
                in_a = nodes[0] in member_set
                in_b = nodes[1] in member_set
                if in_a and in_b:
                    internal_weight += w
                elif in_a or in_b:
                    external_weight += w

            e_ii = internal_weight / total_weight
            a_i = community_degree / (2 * total_weight)
            mod_contrib = e_ii - a_i * a_i
            total_modularity += mod_contrib

            member_labels: list[str] = []
            for nid in members:
                node = self._graph.get_node(nid)
                member_labels.append(node.label if node else nid[:8])

            communities.append(
                Community(
                    community_id=cid,
                    member_ids=members,
                    member_labels=member_labels,
                    size=len(members),
                    internal_edges=int(internal_weight),
                    external_edges=int(external_weight),
                    modularity_contribution=mod_contrib,
                )
            )

        communities.sort(key=lambda c: c.size, reverse=True)

        covered_nodes = sum(c.size for c in communities)
        total_internal = sum(c.internal_edges for c in communities)
        coverage = total_internal / total_weight if total_weight > 0 else 0.0
        coverage = max(0.0, min(1.0, coverage))
        total_modularity = max(-0.5, min(1.0, total_modularity))

        largest = communities[0].size if communities else 0
        avg_size = covered_nodes / len(communities) if communities else 0.0

        return CommunityResult(
            communities=communities,
            community_count=len(communities),
            modularity=total_modularity,
            coverage=coverage,
            largest_community_size=largest,
            avg_community_size=avg_size,
        )
