from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from hyper3.kernel_base import _GraphBase
from hyper3.kernel_types import Hyperedge, Hypernode, Modality

if TYPE_CHECKING:
    from hyper3.kernel import Hypergraph


class QueryMixin(_GraphBase):

    def incident_edges(self, node_id: str) -> list[Hyperedge]:
        """Return all edges incident to the given node (both source and target).

        This returns edges where the node appears in ``source_ids`` OR
        ``target_ids``.  For directed traversal, use ``outgoing_edges()`` or
        ``incoming_edges()`` instead.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges referencing the node.
        """
        edge_ids = self._node_to_edges.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def edges_for(self, node_id: str) -> list[Hyperedge]:
        """Alias for ``incident_edges``. Prefer ``incident_edges`` for clarity."""
        return self.incident_edges(node_id)

    def outgoing_edges(self, node_id: str) -> list[Hyperedge]:
        """Return edges where node_id is in source_ids.

        Unlike ``incident_edges`` which returns all edges touching a node,
        this only returns edges where the node is a source.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges where node_id appears in source_ids.
        """
        edge_ids = self._outgoing_edge_index.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def incoming_edges(self, node_id: str) -> list[Hyperedge]:
        """Return edges where node_id is in target_ids.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges where node_id appears in target_ids.
        """
        edge_ids = self._incoming_edge_index.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def neighbors(self, node_id: str) -> list[str]:
        """Return IDs of all nodes sharing an edge with the given node.

        Results are cached and lazily built; the cache is invalidated on
        any structural mutation outside batch mode.

        Args:
            node_id: The ID of the node.

        Returns:
            List of neighboring node IDs (excluding the node itself).
        """
        if self._neighbor_cache is None:
            self._neighbor_cache = {}
            for nid in self._nodes:
                nbrs: set[str] = set()
                for edge in self.incident_edges(nid):
                    nbrs.update(edge.node_ids)
                nbrs.discard(nid)
                self._neighbor_cache[nid] = list(nbrs)
        return self._neighbor_cache.get(node_id, [])

    def out_neighbors(self, node_id: str) -> list[str]:
        """Return target IDs of outgoing edges.

        For pairwise edges (singleton source/target), this is the direct
        successor set.  For hyperedges, this includes all target IDs of
        edges where node_id is a source.

        Args:
            node_id: The ID of the node.

        Returns:
            List of unique target node IDs from outgoing edges.
        """
        seen: set[str] = set()
        result: list[str] = []
        for edge in self.outgoing_edges(node_id):
            for tgt in edge.target_ids:
                if tgt not in seen and tgt != node_id:
                    seen.add(tgt)
                    result.append(tgt)
        return result

    def in_neighbors(self, node_id: str) -> list[str]:
        """Return source IDs of incoming edges.

        Args:
            node_id: The ID of the node.

        Returns:
            List of unique source node IDs from incoming edges.
        """
        seen: set[str] = set()
        result: list[str] = []
        for edge in self.incoming_edges(node_id):
            for src in edge.source_ids:
                if src not in seen and src != node_id:
                    seen.add(src)
                    result.append(src)
        return result

    def star(self, node_id: str) -> list[Hyperedge]:
        """Return all edges incident to a node.

        Alias for :meth:`incident_edges`. Named after the ``star(v)``
        operator in hypergraph theory: the set of hyperedges containing
        vertex ``v``.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges incident to the node.
        """
        return self.incident_edges(node_id)

    def hyperedge_neighbors(self, node_id: str) -> dict[str, list[Hyperedge]]:
        """Return co-participating nodes grouped by shared hyperedges.

        For each neighbor that shares at least one hyperedge with
        ``node_id``, returns the list of shared hyperedges.

        Args:
            node_id: The ID of the node.

        Returns:
            Dict mapping neighbor node ID to the list of hyperedges
            shared between that neighbor and ``node_id``.
        """
        result: dict[str, list[Hyperedge]] = {}
        for edge in self.incident_edges(node_id):
            for nid in edge.node_ids:
                if nid == node_id:
                    continue
                result.setdefault(nid, []).append(edge)
        return result

    def hyperedge_cocoverage(self, node_id: str) -> dict[str, int]:
        """Return the number of shared hyperedges for each neighbor.

        Args:
            node_id: The ID of the node.

        Returns:
            Dict mapping neighbor node ID to the count of shared hyperedges.
        """
        return {nid: len(edges) for nid, edges in self.hyperedge_neighbors(node_id).items()}

    def node_degree(self, node_id: str) -> int:
        """Return the number of edges connected to a node.

        Args:
            node_id: The ID of the node.

        Returns:
            Edge count for the node.
        """
        return len(self.incident_edges(node_id))

    def degree_distribution(self) -> dict[int, int]:
        """Compute the degree distribution across all nodes.

        Returns:
            Dict mapping degree value to the number of nodes with that degree.
        """
        dist: dict[int, int] = {}
        for nid in self._nodes:
            d = len(self.incident_edges(nid))
            dist[d] = dist.get(d, 0) + 1
        return dist

    def query_dimension(self, modality: Modality) -> list[Hypernode]:
        """Return all nodes tagged with the given modality.

        Args:
            modality: The modality to filter by.

        Returns:
            List of hypernodes matching the modality.
        """
        node_ids = self._dimension_index.get(modality.value, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    @property
    def labeled_edges(self) -> list[dict[str, Any]]:
        """Return all edges with source/target resolved to labels.

        Unlike :attr:`edges` which exposes raw ``frozenset`` IDs, this
        property translates every edge into a dict with human-readable
        ``source_labels`` and ``target_labels`` keyed by node labels.

        Returns:
            List of dicts, each with keys ``id``, ``label``,
            ``source_labels``, ``target_labels``, ``weight``, ``data``.
        """
        results: list[dict[str, Any]] = []
        for edge in self._edges.values():
            src_labels: list[str] = []
            for sid in edge.source_ids:
                node = self._nodes.get(sid)
                if node:
                    src_labels.append(node.label)
            tgt_labels: list[str] = []
            for tid in edge.target_ids:
                node = self._nodes.get(tid)
                if node:
                    tgt_labels.append(node.label)
            results.append(
                {
                    "id": edge.id,
                    "label": edge.label,
                    "source_labels": src_labels,
                    "target_labels": tgt_labels,
                    "weight": edge.weight,
                    "data": edge.data,
                }
            )
        return results

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return len(self._edges)

    @property
    def nodes(self) -> list[Hypernode]:
        """All nodes in the graph."""
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Hyperedge]:
        """All edges in the graph."""
        return list(self._edges.values())

    def density(self) -> float:
        """Compute graph density as edge_count / (n * (n-1)).

        Returns 0.0 for graphs with fewer than 2 nodes.
        """
        n = len(self._nodes)
        if n <= 1:
            return 0.0
        return len(self._edges) / (n * (n - 1))

    def unique_edge_sizes(self) -> list[int]:
        """Return sorted list of distinct edge cardinalities (|source ∪ target|)."""
        sizes: set[int] = set()
        for edge in self._edges.values():
            sizes.add(len(edge.node_ids))
        return sorted(sizes)

    def max_edge_order(self) -> int:
        """Return the maximum edge order (max |node_ids| - 1) across all edges.

        Returns 0 for graphs with no edges.  Pairwise edges have order 1.
        """
        if not self._edges:
            return 0
        return max(len(e.node_ids) for e in self._edges.values()) - 1

    def hash(self) -> str:
        """Compute a deterministic SHA-256 hash of the graph state.

        Serializes node labels, data, and edges in sorted order for a
        canonical, reproducible fingerprint.

        Returns:
            Hex-encoded SHA-256 digest string.
        """
        import hashlib
        import json

        node_entries = sorted(
            ((n.label or "", n.weight, sorted(n.data.items()) if n.data else []) for n in self._nodes.values()),
        )
        edge_entries = sorted(
            (
                sorted(e.source_ids),
                sorted(e.target_ids),
                e.label or "",
                e.weight,
            )
            for e in self._edges.values()
        )
        blob = json.dumps({"nodes": node_entries, "edges": edge_entries}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def degree_correlation(self) -> float:
        """Compute Pearson correlation between degrees of nodes sharing edges.

        For each edge, computes the degree of each participating node,
        then calculates the Pearson correlation coefficient across all
        (degree_u, degree_v) pairs.  Positive values indicate assortative
        mixing (high-degree nodes connect to other high-degree nodes).

        Returns:
            Pearson correlation coefficient in [-1, 1].  Returns 0.0 if
            there are fewer than 2 data points.
        """
        import numpy as np

        if not self._edges:
            return 0.0

        degree_map = {nid: len(self.incident_edges(nid)) for nid in self._nodes}
        x_list: list[float] = []
        y_list: list[float] = []

        for edge in self._edges.values():
            members = sorted(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    x_list.append(float(degree_map.get(members[i], 0)))
                    y_list.append(float(degree_map.get(members[j], 0)))

        if len(x_list) < 2:
            return 0.0

        x = np.array(x_list)
        y = np.array(y_list)
        corr = np.corrcoef(x, y)[0, 1]
        return float(corr) if not np.isnan(corr) else 0.0

    def degree_assortativity(self) -> float:
        """Compute Newman degree assortativity coefficient.

        For each directed edge (u -> v), records (deg(u), deg(v)).  For
        undirected edges (bidirectional), each direction contributes one
        pair.  Returns the Pearson correlation of these (source_degree,
        target_degree) pairs, matching ``nx.degree_assortativity_coefficient``.

        Returns:
            Pearson correlation in [-1, 1].  Returns 0.0 if there are
            fewer than 2 data points.
        """
        import numpy as np

        if not self._edges:
            return 0.0

        degree_map = {nid: len(self.incident_edges(nid)) for nid in self._nodes}
        src_degs: list[float] = []
        tgt_degs: list[float] = []

        for edge in self._edges.values():
            for s in edge.source_ids:
                for t in edge.target_ids:
                    src_degs.append(float(degree_map.get(s, 0)))
                    tgt_degs.append(float(degree_map.get(t, 0)))

        if len(src_degs) < 2:
            return 0.0

        corr = np.corrcoef(src_degs, tgt_degs)[0, 1]
        return float(corr) if not np.isnan(corr) else 0.0

    def subhypergraph_by_order(self, orders: set[int]) -> Hypergraph:
        """Return a new Hypergraph containing only edges of the specified orders (order = |node_ids| - 1). All nodes are preserved."""
        from hyper3.kernel import Hypergraph

        result = Hypergraph()
        for node in self._nodes.values():
            result.add_node(Hypernode(id=node.id, label=node.label, data=dict(node.data) if node.data else None, weight=node.weight))
        for edge in self._edges.values():
            edge_order = len(edge.node_ids) - 1
            if edge_order in orders:
                result.add_edge(Hyperedge(source_ids=frozenset(edge.source_ids), target_ids=frozenset(edge.target_ids), label=edge.label, weight=edge.weight))
        return result

    def attribute_assortativity(self, attribute: str) -> float:
        """Compute assortativity coefficient for a node data attribute. Only nodes with the attribute participate. Delegates to networkx via pairwise clique projection."""
        G = self._pairwise_undirected_nx()
        node_attrs = self._node_data_attr(attribute)
        nx.set_node_attributes(G, node_attrs, attribute)
        nodes_with_attr = {n for n in G.nodes if n in node_attrs}
        if len(nodes_with_attr) < 2:
            return 0.0
        subG = G.subgraph(nodes_with_attr)
        return float(nx.attribute_assortativity_coefficient(subG, attribute))

    def _pairwise_undirected_nx(self) -> nx.Graph:
        """Build an undirected networkx Graph from the hypergraph via clique expansion (each hyperedge becomes a complete pairwise subgraph). No weights or labels are preserved."""
        G = nx.Graph()
        for nid in self._nodes:
            G.add_node(nid)
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    G.add_edge(members[i], members[j])
        return G

    def average_neighbor_degree(self, nodes: set[str] | None = None) -> dict[str, float]:
        """Compute the average degree of each node neighbors. Delegates to networkx via pairwise clique projection. Note: degrees are inflated for nodes in large hyperedges due to clique expansion."""
        G = self._pairwise_undirected_nx()
        nx_result = nx.average_neighbor_degree(G, nodes=nodes)
        return {nid: v for nid, v in nx_result.items() if nid in self._nodes}

    def average_degree_connectivity(self) -> dict[int, float]:
        """Compute the average degree connectivity (average neighbor degree for each degree value). Delegates to networkx via pairwise clique projection. Note: degrees are inflated for nodes in large hyperedges due to clique expansion."""
        G = self._pairwise_undirected_nx()
        return {int(k): float(v) for k, v in nx.average_degree_connectivity(G).items()}

    def rich_club_coefficient(self) -> dict[int, float]:
        """Compute the rich-club coefficient for each degree. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return {int(k): float(v) for k, v in nx.rich_club_coefficient(G).items()}

    def onion_layers(self) -> dict[str, int]:
        """Compute onion decomposition layers for each node. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return {nid: int(v) for nid, v in nx.onion_layers(G).items() if nid in self._nodes}

    def wiener_index(self) -> float:
        """Compute the Wiener index (sum of all shortest-path lengths). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return float(nx.wiener_index(G))

    def s_metric(self) -> float:
        """Compute the s-metric (sum of deg(u)*deg(v) over edges). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return float(nx.s_metric(G))

    def node_connectivity(self) -> int:
        """Compute the minimum number of nodes whose removal disconnects the graph. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return int(nx.node_connectivity(G))

    def edge_connectivity(self) -> int:
        """Compute the minimum number of edges whose removal disconnects the graph. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return int(nx.edge_connectivity(G))
