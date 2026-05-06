from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from hyper3.kernel_base import _GraphBase
from hyper3.kernel_types import Hyperedge, Hypernode

if TYPE_CHECKING:
    from hyper3.kernel import Hypergraph


class TransformMixin(_GraphBase):

    def clique_projection(self) -> Any:
        """Expand every hyperedge into a clique of pairwise edges.

        For each hyperedge containing nodes {v1, v2, ..., vk}, creates
        pairwise edges (vi, vj) for every pair.  The result is a standard
        pairwise graph with the same vertex set.

        Returns:
            A new Hypergraph containing only pairwise edges.
        """
        from itertools import combinations

        from hyper3.kernel import Hypergraph

        result = Hypergraph()
        for node in self._nodes.values():
            result.add_node(Hypernode(id=node.id, label=node.label, data=dict(node.data) if node.data else None, weight=node.weight))
        for edge in self._edges.values():
            members = sorted(edge.node_ids)
            for u, v in combinations(members, 2):
                result.add_edge(
                    Hyperedge(
                        source_ids=frozenset({u}),
                        target_ids=frozenset({v}),
                        label=edge.label,
                        weight=edge.weight,
                    )
                )
        return result

    def to_networkx(self) -> nx.DiGraph:
        """Convert the hypergraph to a networkx DiGraph.

        Hyperedges are expanded into pairwise directed edges between every
        source and every target node.

        Returns:
            A networkx DiGraph with node/edge attributes preserved.
        """
        G = nx.DiGraph()
        for node in self._nodes.values():
            G.add_node(node.id, label=node.label, weight=node.weight, data=node.data)
        for edge in self._edges.values():
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    G.add_edge(src, tgt, label=edge.label, weight=edge.weight, edge_id=edge.id)
        return G

    def _to_networkx_inverted_weights(self) -> nx.DiGraph:
        """Convert to a networkx DiGraph with cost = 1/weight on each edge."""
        G = self.to_networkx()
        for _u, _v, data in G.edges(data=True):
            w = data.get("weight", 1.0)
            data["cost"] = 1.0 / max(w, 1e-9)
        return G

    def to_dual(self) -> Hypergraph:
        """Compute the dual hypergraph where edges become nodes and nodes become edges.

        Each hyperedge in the original graph becomes a dual node.  Each
        original node with at least one incident edge becomes a dual
        hyperedge connecting the dual nodes corresponding to those
        incident edges.

        Returns:
            A new Hypergraph representing the dual.
        """
        from hyper3.kernel import Hypergraph

        dual = Hypergraph()
        edge_list = list(self._edges.values())
        edge_to_dual_id: dict[str, str] = {}

        for i, edge in enumerate(edge_list):
            dual_node = Hypernode(label=f"e{i}")
            dual.add_node(dual_node)
            edge_to_dual_id[edge.id] = dual_node.id

        for i, node in enumerate(self._nodes.values()):
            incident = self.incident_edges(node.id)
            if not incident:
                continue
            dual_node_ids = frozenset(
                edge_to_dual_id[e.id] for e in incident if e.id in edge_to_dual_id
            )
            if not dual_node_ids:
                continue
            dual.add_edge(
                Hyperedge(
                    source_ids=dual_node_ids,
                    target_ids=frozenset(),
                    label=f"v{i}",
                )
            )

        return dual

    def to_line_graph(self) -> Any:
        """Compute the line graph where edges sharing vertices are connected.

        Each hyperedge becomes a node.  Two nodes are connected if
        their hyperedges share at least one vertex.

        Returns:
            A networkx Graph where nodes are edge IDs.
        """
        G = nx.Graph()
        edge_list = list(self._edges.values())
        for edge in edge_list:
            G.add_node(edge.id, label=edge.label)
        for i in range(len(edge_list)):
            nodes_i = edge_list[i].node_ids
            for j in range(i + 1, len(edge_list)):
                if nodes_i & edge_list[j].node_ids:
                    G.add_edge(edge_list[i].id, edge_list[j].id)
        return G

    def to_directed_line_graph(self) -> nx.DiGraph:
        G = nx.DiGraph()
        edge_list = list(self._edges.values())
        for edge in edge_list:
            G.add_node(edge.id, label=edge.label)
        for i in range(len(edge_list)):
            targets_i = edge_list[i].target_ids
            for j in range(len(edge_list)):
                if i == j:
                    continue
                if targets_i & edge_list[j].source_ids:
                    G.add_edge(edge_list[i].id, edge_list[j].id)
        return G

    def to_bipartite_graph(self) -> Any:
        """Convert to a bipartite networkx Graph with vertex and edge nodes.

        Nodes with ``bipartite=0`` represent hypergraph vertices;
        nodes with ``bipartite=1`` represent hyperedges.  An edge
        connects a vertex to every hyperedge it participates in.

        Returns:
            A networkx Graph with ``bipartite`` and ``label`` attributes.
        """
        G = nx.Graph()
        for node in self._nodes.values():
            G.add_node(node.id, bipartite=0, label=node.label)
        for edge in self._edges.values():
            G.add_node(edge.id, bipartite=1, label=edge.label)
            for nid in edge.node_ids:
                if nid in self._nodes:
                    G.add_edge(nid, edge.id)
        return G

    def simplicial_complex(self) -> list[frozenset[str]]:
        """Build an abstract simplicial complex from the hypergraph.

        Each hyperedge's vertex set becomes a simplex.  All faces
        (subsets) of each simplex are included, ensuring downward
        closure.

        Returns:
            Sorted list of frozensets (simplexes), from smallest to
            largest cardinality.
        """
        simplices: set[frozenset[str]] = set()
        for edge in self._edges.values():
            members = edge.source_ids | edge.target_ids
            members_list = sorted(members)
            from itertools import combinations
            for k in range(1, len(members_list) + 1):
                for face in combinations(members_list, k):
                    simplices.add(frozenset(face))
        for nid in self._nodes:
            simplices.add(frozenset({nid}))
        return sorted(simplices, key=lambda s: (len(s), sorted(s)))

    def bipartite_projected_graph(self, *, onto: int = 0) -> Any:
        """Project the bipartite vertex-edge graph onto one bipartite set.

        Two vertices in set ``onto`` are connected if they share at
        least one neighbor in the other set.

        Args:
            onto: The bipartite set to project onto (0 = vertices,
                1 = hyperedges).

        Returns:
            A networkx Graph with weighted edges (weight = number of
            shared neighbors).
        """
        B = self.to_bipartite_graph()
        top_nodes = {n for n, d in B.nodes(data=True) if d.get("bipartite") == onto}
        bottom_nodes = set(B.nodes) - top_nodes
        projected = nx.Graph()
        projected.add_nodes_from(top_nodes)
        top_list = sorted(top_nodes)
        for i in range(len(top_list)):
            neighbors_i = set(B.neighbors(top_list[i])) & bottom_nodes
            for j in range(i + 1, len(top_list)):
                neighbors_j = set(B.neighbors(top_list[j])) & bottom_nodes
                shared = neighbors_i & neighbors_j
                if shared:
                    projected.add_edge(top_list[i], top_list[j], weight=len(shared))
        return projected

    def bipartite_weighted_projection(self, *, onto: int = 0) -> dict[tuple[str, str], float]:
        """Compute a weighted projection of the bipartite graph.

        Uses Jaccard-weighted similarity: for each pair of nodes in set
        ``onto``, the weight is ``|N(u) & N(v)| / |N(u) | N(v)|``.

        Args:
            onto: The bipartite set to project onto (0 = vertices,
                1 = hyperedges).

        Returns:
            Dict mapping (node_id_a, node_id_b) pairs to Jaccard
            similarity scores.
        """
        B = self.to_bipartite_graph()
        top_nodes = {n for n, d in B.nodes(data=True) if d.get("bipartite") == onto}
        bottom_nodes = set(B.nodes) - top_nodes
        result: dict[tuple[str, str], float] = {}
        top_list = sorted(top_nodes)
        for i in range(len(top_list)):
            neighbors_i = set(B.neighbors(top_list[i])) & bottom_nodes
            for j in range(i + 1, len(top_list)):
                neighbors_j = set(B.neighbors(top_list[j])) & bottom_nodes
                intersection = len(neighbors_i & neighbors_j)
                union = len(neighbors_i | neighbors_j)
                if intersection > 0 and union > 0:
                    result[(top_list[i], top_list[j])] = intersection / union
        return result
