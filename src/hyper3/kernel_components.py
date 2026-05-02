from __future__ import annotations

from typing import Any

from hyper3.kernel_base import _GraphBase
from hyper3.results import SPersistenceLevel, SPersistenceResult


class ComponentMixin(_GraphBase):

    def connected_components(self, *, s: int = 1) -> list[set[str]]:
        """Find connected components using hyperedge-native union-find.

        Two nodes are in the same component if they share a hyperedge
        (or, for ``s > 1``, if they are connected through a chain of
        hyperedges with pairwise overlap >= ``s``).

        Args:
            s: Minimum vertex overlap between consecutive hyperedges
                required for connectivity.  ``s=1`` (default) treats
                any shared vertex as a connection, matching standard
                weakly-connected components on pairwise graphs.

        Returns:
            List of sets, each containing the node IDs of one component.
        """
        if not self._nodes:
            return []

        if s <= 1:
            return self._connected_components_basic()

        return self._connected_components_s(s)

    def _connected_components_basic(self) -> list[set[str]]:
        """Fast union-find: two nodes are connected if they share a hyperedge."""
        parent: dict[str, str] = {nid: nid for nid in self._nodes}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for edge in self._edges.values():
            all_ids = list(edge.source_ids | edge.target_ids)
            for i in range(1, len(all_ids)):
                union(all_ids[0], all_ids[i])

        components: dict[str, set[str]] = {}
        for nid in self._nodes:
            root = find(nid)
            components.setdefault(root, set()).add(nid)
        return list(components.values())

    def _connected_components_s(self, s: int) -> list[set[str]]:
        """s-connected components: build s-line graph on hyperedges, then find components."""
        edge_list = list(self._edges.values())
        if not edge_list:
            return [{nid} for nid in self._nodes]

        edge_node_sets = [e.source_ids | e.target_ids for e in edge_list]
        m = len(edge_list)

        edge_parent = list(range(m))

        def find(x: int) -> int:
            while edge_parent[x] != x:
                edge_parent[x] = edge_parent[edge_parent[x]]
                x = edge_parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                edge_parent[ra] = rb

        self._union_s_adjacent_edges(m, edge_node_sets, s, find, union)

        edge_components: dict[int, set[int]] = {}
        for i in range(m):
            root = find(i)
            edge_components.setdefault(root, set()).add(i)

        return self._build_node_components_from_edge_groups(edge_components, edge_node_sets)

    def _union_s_adjacent_edges(
        self,
        m: int,
        edge_node_sets: list[frozenset[str]],
        s: int,
        find: Any,
        union: Any,
    ) -> None:
        """Union-find merge edges whose vertex overlap >= *s*."""
        for i in range(m):
            for j in range(i + 1, m):
                if len(edge_node_sets[i] & edge_node_sets[j]) >= s:
                    union(i, j)

    def _build_node_components_from_edge_groups(
        self,
        edge_components: dict[int, set[int]],
        edge_node_sets: list[frozenset[str]],
    ) -> list[set[str]]:
        """Convert edge-component groups to node-component sets, adding isolated nodes."""
        node_components: list[set[str]] = []
        for comp_edge_indices in edge_components.values():
            node_set: set[str] = set()
            for idx in comp_edge_indices:
                node_set.update(edge_node_sets[idx])
            node_components.append(node_set)

        covered: set[str] = set()
        for comp in node_components:
            covered.update(comp)
        isolated = set(self._nodes.keys()) - covered
        node_components.extend({nid} for nid in isolated)

        return node_components

    def s_connected_components(self, s: int = 1) -> list[set[str]]:
        """Compute s-connected components on the hyperedge overlap graph.

        Two hyperedges are s-adjacent if they share at least ``s`` vertices.
        Components are the connected groups of hyperedges under this
        relation, projected back to their constituent vertex sets.

        Args:
            s: Minimum vertex overlap for adjacency.

        Returns:
            List of sets of node IDs.
        """
        return self._connected_components_s(s)

    def s_persistence(self, *, max_s: int | None = None) -> SPersistenceResult:
        """Compute the s-persistence filtration of s-connected components.

        Iterates ``s`` from 1 upward, computing s-connected components
        at each level.  Components split as ``s`` increases, revealing
        multi-resolution structure.

        Args:
            max_s: Maximum s value to compute.  Defaults to the maximum
                pairwise overlap between any two hyperedges.

        Returns:
            SPersistenceResult with list of SPersistenceLevel entries.
        """
        edge_list = list(self._edges.values())
        if not edge_list:
            if self._nodes:
                return SPersistenceResult(
                    levels=[
                        SPersistenceLevel(
                            s=1,
                            components=[frozenset(self._nodes.keys())],
                            num_components=1,
                            largest_component_size=len(self._nodes),
                        )
                    ],
                    max_s=1,
                    total_edges=0,
                )
            return SPersistenceResult()

        edge_node_sets = [e.source_ids | e.target_ids for e in edge_list]

        overlaps, max_overlap = self._compute_edge_overlaps(edge_node_sets)

        effective_max = max_s if max_s is not None else max_overlap
        if effective_max < 1:
            effective_max = 1

        levels = [
            self._compute_s_level(s_val, len(edge_list), overlaps, edge_node_sets)
            for s_val in range(1, effective_max + 1)
        ]

        return SPersistenceResult(
            levels=levels,
            max_s=effective_max,
            total_edges=len(edge_list),
        )

    def _compute_edge_overlaps(
        self, edge_node_sets: list[frozenset[str]]
    ) -> tuple[dict[tuple[int, int], int], int]:
        """Compute pairwise vertex-intersection sizes and the maximum overlap."""
        m = len(edge_node_sets)
        overlaps: dict[tuple[int, int], int] = {}
        max_overlap = 0
        for i in range(m):
            for j in range(i + 1, m):
                ov = len(edge_node_sets[i] & edge_node_sets[j])
                if ov > 0:
                    overlaps[(i, j)] = ov
                    max_overlap = max(max_overlap, ov)
        return overlaps, max_overlap

    def _compute_s_level(
        self,
        s_val: int,
        m: int,
        overlaps: dict[tuple[int, int], int],
        edge_node_sets: list[frozenset[str]],
    ) -> SPersistenceLevel:
        """Compute s-connected components for a single s value."""
        edge_components = self._union_overlapping_edges(m, overlaps, s_val)
        node_sets = self._build_node_components_from_edge_groups(edge_components, edge_node_sets)
        node_components = [frozenset(ns) for ns in node_sets]

        return SPersistenceLevel(
            s=s_val,
            components=node_components,
            num_components=len(node_components),
            largest_component_size=max(len(c) for c in node_components) if node_components else 0,
        )

    def _union_overlapping_edges(
        self,
        m: int,
        overlaps: dict[tuple[int, int], int],
        s_val: int,
    ) -> dict[int, set[int]]:
        """Union-find on edges with overlap >= *s_val*, returning edge-component groups."""
        edge_parent = list(range(m))

        def find(x: int) -> int:
            while edge_parent[x] != x:
                edge_parent[x] = edge_parent[edge_parent[x]]
                x = edge_parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                edge_parent[ra] = rb

        for (i, j), ov in overlaps.items():
            if ov >= s_val:
                union(i, j)

        edge_components: dict[int, set[int]] = {}
        for i in range(m):
            root = find(i)
            edge_components.setdefault(root, set()).add(i)
        return edge_components

    def is_connected(self) -> bool:
        """Return True if all nodes belong to a single connected component."""
        components = self.connected_components()
        return len(components) == 1

    def largest_connected_component(self) -> set[str]:
        """Return the node IDs of the largest connected component.

        Returns an empty set for a graph with no nodes.
        """
        components = self.connected_components()
        if not components:
            return set()
        return max(components, key=len)

    def component_of(self, node_id: str) -> set[str]:
        """Return the connected component containing the given node.

        Args:
            node_id: The ID of the node to look up.

        Returns:
            Set of node IDs in the same component, or an empty set if
            the node is not in the graph.
        """
        for comp in self.connected_components():
            if node_id in comp:
                return comp
        return set()
