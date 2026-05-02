from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from hyper3.kernel_base import _GraphBase
from hyper3.kernel_types import Hyperedge, Hypernode

if TYPE_CHECKING:
    from hyper3.kernel import Hypergraph


class TransformMixin(_GraphBase):

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
