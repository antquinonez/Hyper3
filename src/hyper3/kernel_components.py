from __future__ import annotations

from typing import Any

from hyper3.kernel_base import _GraphBase
from hyper3.results import SPersistenceLevel, SPersistenceResult


class ComponentMixin(_GraphBase):

    def strongly_connected_components(self) -> list[set[str]]:
        """Find strongly connected components using Kosaraju's algorithm.

        A strongly connected component is a maximal set of nodes where
        every node is reachable from every other node via directed edges.

        Returns:
            List of sets, each containing the node IDs of one SCC.
        """
        if not self._nodes:
            return []

        node_ids = list(self._nodes.keys())

        finish_order: list[str] = []
        visited: set[str] = set()
        for nid in node_ids:
            if nid not in visited:
                self._kosaraju_dfs_forward(nid, visited, finish_order)

        reverse_map = self._build_reverse_adjacency()
        visited.clear()
        components: list[set[str]] = []
        for nid in reversed(finish_order):
            if nid not in visited:
                comp: set[str] = set()
                self._kosaraju_dfs_reverse(nid, visited, reverse_map, comp)
                components.append(comp)
        return components

    def _kosaraju_dfs_forward(self, node: str, visited: set[str], finish_order: list[str]) -> None:
        stack = [(node, False)]
        while stack:
            current, processed = stack.pop()
            if processed:
                finish_order.append(current)
                continue
            if current in visited:
                continue
            visited.add(current)
            stack.append((current, True))
            for edge in self.outgoing_edges(current):
                for tgt in edge.target_ids:
                    if tgt not in visited:
                        stack.append((tgt, False))

    def _kosaraju_dfs_reverse(self, node: str, visited: set[str], reverse_map: dict[str, list[str]], comp: set[str]) -> None:
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            comp.add(current)
            for pred in reverse_map.get(current, []):
                if pred not in visited:
                    stack.append(pred)

    def _build_reverse_adjacency(self) -> dict[str, list[str]]:
        reverse: dict[str, list[str]] = {}
        for edge in self._edges.values():
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    reverse.setdefault(tgt, []).append(src)
        return reverse

    def biconnected_components(self) -> list[set[str]]:
        """Find biconnected components using Hopcroft-Tarjan algorithm.

        A biconnected component is a maximal subgraph that remains
        connected after removing any single node.  Operates on the
        undirected projection (ignoring edge direction).

        Returns:
            List of sets, each containing the node IDs of one biconnected
            component.  Individual edges form their own components.
        """
        if not self._nodes:
            return []

        node_ids = list(self._nodes.keys())
        visited: set[str] = set()
        disc: dict[str, int] = {}
        low: dict[str, int] = {}
        parent: dict[str, str | None] = {}
        timer = [0]
        components: list[set[str]] = []
        edge_stack: list[tuple[str, str]] = []

        for nid in node_ids:
            if nid not in visited:
                self._biconnected_dfs(nid, visited, disc, low, parent, timer, edge_stack, components)

        remaining_edges = list(edge_stack)
        if remaining_edges:
            comp: set[str] = set()
            for u, v in remaining_edges:
                comp.add(u)
                comp.add(v)
            components.append(comp)

        return components

    def _biconnected_dfs(
        self,
        u: str,
        visited: set[str],
        disc: dict[str, int],
        low: dict[str, int],
        parent: dict[str, str | None],
        timer: list[int],
        edge_stack: list[tuple[str, str]],
        components: list[set[str]],
    ) -> None:
        visited.add(u)
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        children = 0

        for edge in self.incident_edges(u):
            for v in edge.node_ids:
                if v == u:
                    continue
                edge_tuple = (min(u, v), max(u, v))
                if v not in visited:
                    parent[v] = u
                    children += 1
                    edge_stack.append(edge_tuple)
                    self._biconnected_dfs(v, visited, disc, low, parent, timer, edge_stack, components)
                    low[u] = min(low[u], low[v])

                    if (parent.get(u) is None and children > 1) or (parent.get(u) is not None and low[v] >= disc[u]):
                        comp: set[str] = set()
                        while edge_stack:
                            e = edge_stack.pop()
                            comp.add(e[0])
                            comp.add(e[1])
                            if e == edge_tuple:
                                break
                        components.append(comp)
                elif parent.get(u) != v and disc.get(v, float("inf")) < disc[u]:
                    low[u] = min(low[u], disc[v])
                    edge_stack.append(edge_tuple)

    def articulation_points(self) -> set[str]:
        """Find articulation points (cut vertices) in the undirected graph.

        An articulation point is a node whose removal increases the number
        of connected components.

        Returns:
            Set of node IDs that are articulation points.
        """
        if not self._nodes:
            return set()

        node_ids = list(self._nodes.keys())
        visited: set[str] = set()
        disc: dict[str, int] = {}
        low: dict[str, int] = {}
        parent: dict[str, str | None] = {}
        ap: set[str] = set()
        timer = [0]

        for nid in node_ids:
            if nid not in visited:
                self._articulation_dfs(nid, visited, disc, low, parent, ap, timer)

        return ap

    def _articulation_dfs(
        self,
        u: str,
        visited: set[str],
        disc: dict[str, int],
        low: dict[str, int],
        parent: dict[str, str | None],
        ap: set[str],
        timer: list[int],
    ) -> None:
        visited.add(u)
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        children = 0

        for edge in self.incident_edges(u):
            for v in edge.node_ids:
                if v == u:
                    continue
                if v not in visited:
                    parent[v] = u
                    children += 1
                    self._articulation_dfs(v, visited, disc, low, parent, ap, timer)
                    low[u] = min(low[u], low[v])
                    if parent.get(u) is None and children > 1:
                        ap.add(u)
                    if parent.get(u) is not None and low[v] >= disc[u]:
                        ap.add(u)
                elif parent.get(u) != v:
                    low[u] = min(low[u], disc[v])

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

    def greedy_modularity_communities(self) -> list[set[str]]:
        """Find communities using greedy modularity maximization (Clauset-Newman-Moore).

        Starting with each node in its own community, iteratively merges
        the pair of communities that yields the largest increase in
        modularity, stopping when no merge improves modularity.

        Uses the undirected projection (ignoring edge direction).
        Modularity is defined as:
            Q = (1/2m) * sum_{ij} [A_{ij} - k_i*k_j/(2m)] * delta(c_i, c_j)

        Returns:
            List of sets, each containing the node IDs of one community.
        """
        if not self._nodes:
            return []

        node_ids = list(self._nodes.keys())
        n = len(node_ids)
        node_idx = {nid: i for i, nid in enumerate(node_ids)}

        A: list[dict[int, float]] = [{} for _ in range(n)]
        degrees = [0.0] * n
        m_total = 0.0

        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(len(members)):
                    if i != j:
                        ii = node_idx.get(members[i])
                        jj = node_idx.get(members[j])
                        if ii is not None and jj is not None:
                            A[ii][jj] = A[ii].get(jj, 0.0) + edge.weight
                            degrees[ii] += edge.weight
                            m_total += edge.weight

        if m_total == 0:
            return [set(node_ids)]

        community: list[int] = list(range(n))
        comm_nodes: list[set[int]] = [{i} for i in range(n)]

        delta_q: dict[tuple[int, int], float] = {}
        for i in range(n):
            for j in A[i]:
                if i < j:
                    e_ij = A[i].get(j, 0.0) + A[j].get(i, 0.0)
                    delta_q[(i, j)] = e_ij / (2.0 * m_total) - degrees[i] * degrees[j] / (2.0 * m_total * m_total)

        active = set(range(n))

        while len(active) > 1 and delta_q:
            best_pair = max(delta_q, key=delta_q.get)
            best_dq = delta_q[best_pair]
            if best_dq <= 0:
                break

            ci, cj = best_pair
            if ci not in active or cj not in active:
                del delta_q[best_pair]
                continue

            comm_nodes[ci] = comm_nodes[ci] | comm_nodes[cj]
            comm_nodes[cj] = set()
            active.discard(cj)
            for k in list(active):
                if k == ci:
                    continue
                key_ik = (min(ci, k), max(ci, k))
                key_jk = (min(cj, k), max(cj, k))
                dq_ik = delta_q.get(key_ik, 0.0)
                dq_jk = delta_q.get(key_jk, 0.0)
                delta_q[key_ik] = dq_ik + dq_jk
                if key_jk in delta_q:
                    del delta_q[key_jk]

            for k in list(active):
                if k == ci:
                    continue
                key = (min(ci, k), max(ci, k))
                if key not in delta_q:
                    e_ck = 0.0
                    for node in comm_nodes[ci]:
                        e_ck += A[node].get(k, 0.0) + A[k].get(node, 0.0)
                    deg_c = sum(degrees[node] for node in comm_nodes[ci])
                    delta_q[key] = e_ck / (2.0 * m_total) - deg_c * degrees[k] / (2.0 * m_total * m_total)

            del delta_q[best_pair]

        return [comm_nodes[c] for c in active if comm_nodes[c]]
