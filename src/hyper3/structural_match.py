from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class PatternNode(_SimpleResultBase):
    """A node role template within a structural pattern."""

    role: str
    data_type: str | None = None
    label_pattern: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternEdge(_SimpleResultBase):
    """An edge template connecting two node roles in a pattern."""

    source_role: str
    target_role: str
    label: str | None = None
    min_weight: float = 0.0


@dataclass
class PatternTemplate(_SimpleResultBase):
    """A reusable subgraph pattern defined by node roles and edge constraints."""

    name: str
    nodes: list[PatternNode] = field(default_factory=list)
    edges: list[PatternEdge] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuralMatch(_SimpleResultBase):
    """A single instantiation of a pattern template against graph nodes."""

    pattern_name: str
    bindings: dict[str, str]
    matched_edges: list[str] = field(default_factory=list)
    matched_nodes: list[str] = field(default_factory=list)
    score: float = 1.0


@dataclass
class StructuralMatchResult(_SimpleResultBase):
    """Aggregate result of matching a pattern template against the graph."""

    pattern_name: str
    matches: list[StructuralMatch] = field(default_factory=list)
    total_match_count: int = 0
    unique_nodes_matched: int = 0
    unique_edges_matched: int = 0


class StructuralPatternEngine:
    """Finds structural patterns (chains, diamonds, fan-outs, arbitrary templates)
    in a hypergraph via role-based subgraph matching."""

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize with a reference to the hypergraph for structural pattern searches."""
        self._graph = graph

    def _extend_from_source(
        self,
        src_id: str,
        bindings: dict[str, str],
        pedge: PatternEdge,
        next_bindings: list[dict[str, str]],
    ) -> None:
        """Extend pattern bindings by following outgoing edges from a source role."""
        for e in self._graph.incident_edges(src_id):
            if pedge.label and e.label != pedge.label:
                continue
            if e.weight < pedge.min_weight:
                continue
            for tid in e.target_ids:
                new_b = dict(bindings)
                new_b[pedge.target_role] = tid
                next_bindings.append(new_b)

    def _extend_from_target(
        self,
        tgt_id: str,
        bindings: dict[str, str],
        pedge: PatternEdge,
        next_bindings: list[dict[str, str]],
    ) -> None:
        """Extend pattern bindings by following incoming edges to a target role."""
        for e in self._graph.edges:
            if tgt_id not in e.target_ids:
                continue
            if pedge.label and e.label != pedge.label:
                continue
            if e.weight < pedge.min_weight:
                continue
            for sid in e.source_ids:
                new_b = dict(bindings)
                new_b[pedge.source_role] = sid
                next_bindings.append(new_b)

    def _extend_bindings_for_edge(
        self,
        pedge: PatternEdge,
        binding_queue: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Update bindings with the node/edge of a matched edge."""
        next_bindings: list[dict[str, str]] = []
        for bindings in binding_queue:
            src_id = bindings.get(pedge.source_role)
            tgt_id = bindings.get(pedge.target_role)
            if src_id and tgt_id:
                if self._edge_exists(src_id, tgt_id, pedge.label, pedge.min_weight):
                    next_bindings.append(bindings)
            elif src_id:
                self._extend_from_source(src_id, bindings, pedge, next_bindings)
            elif tgt_id:
                self._extend_from_target(tgt_id, bindings, pedge, next_bindings)
            else:
                next_bindings.extend(binding_queue)
                return next_bindings
        return next_bindings

    def match_pattern(
        self,
        pattern: PatternTemplate,
        *,
        max_matches: int = 100,
    ) -> StructuralMatchResult:
        """Match an arbitrary pattern template against the graph."""
        if not pattern.nodes or not pattern.edges:
            return StructuralMatchResult(pattern_name=pattern.name)

        first_edge = pattern.edges[0]
        candidates = self._find_edge_candidates(first_edge)
        matches: list[StructuralMatch] = []

        for _edge, initial_bindings in candidates:
            binding_queue: list[dict[str, str]] = [initial_bindings]
            for pedge in pattern.edges[1:]:
                binding_queue = self._extend_bindings_for_edge(pedge, binding_queue)
                if not binding_queue:
                    break

            for bindings in binding_queue:
                if self._validate_node_constraints(bindings, pattern):
                    score = self._score_match(bindings, pattern)
                    matched_edges = self._collect_matched_edges(bindings, pattern)
                    matched_nodes = list(set(bindings.values()))
                    matches.append(
                        StructuralMatch(
                            pattern_name=pattern.name,
                            bindings=dict(bindings),
                            matched_edges=matched_edges,
                            matched_nodes=matched_nodes,
                            score=score,
                        )
                    )
                    if len(matches) >= max_matches:
                        break

            if len(matches) >= max_matches:
                break

        all_nodes: set[str] = set()
        all_edges: set[str] = set()
        for m in matches:
            all_nodes.update(m.matched_nodes)
            all_edges.update(m.matched_edges)

        return StructuralMatchResult(
            pattern_name=pattern.name,
            matches=matches,
            total_match_count=len(matches),
            unique_nodes_matched=len(all_nodes),
            unique_edges_matched=len(all_edges),
        )

    def match_chain(
        self,
        *,
        edge_label: str | None = None,
        min_length: int = 2,
        max_length: int = 5,
        max_chains: int = 50,
    ) -> list[list[str]]:
        """Find linear chains of the given length."""
        chains: list[list[str]] = []
        all_targets: set[str] = set()
        for edge in self._graph.edges:
            all_targets.update(edge.target_ids)
        nodes_with_no_incoming: list[str] = [
            node.id for node in self._graph.nodes if node.id not in all_targets
        ]

        seeds = nodes_with_no_incoming if nodes_with_no_incoming else [n.id for n in self._graph.nodes]

        for seed in seeds:
            self._find_chains_dfs(
                seed,
                edge_label,
                min_length,
                max_length,
                [seed],
                set(),
                chains,
                max_chains,
            )
            if len(chains) >= max_chains:
                break

        return chains[:max_chains]

    def match_fan_out(
        self,
        *,
        edge_label: str | None = None,
        min_fan: int = 3,
        max_results: int = 50,
    ) -> list[tuple[str, list[str]]]:
        """Find hub nodes with at least *min_targets* outgoing edges."""
        fan_outs: list[tuple[str, list[str]]] = []
        for node in self._graph.nodes:
            targets: list[str] = []
            for edge in self._graph.incident_edges(node.id):
                if edge_label and edge.label != edge_label:
                    continue
                targets.extend(edge.target_ids)
            unique_targets = list(set(targets))
            if len(unique_targets) >= min_fan:
                fan_outs.append((node.id, unique_targets))
                if len(fan_outs) >= max_results:
                    break
        fan_outs.sort(key=lambda x: len(x[1]), reverse=True)
        return fan_outs

    def _build_source_target_maps(
        self,
        edge_label: str | None,
    ) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        """Pre-compute maps of source/target roles to candidate node IDs."""
        source_to_targets: dict[str, set[str]] = {}
        for edge in self._graph.edges:
            if edge_label and edge.label != edge_label:
                continue
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    source_to_targets.setdefault(src, set()).add(tgt)
        target_to_sources: dict[str, set[str]] = {}
        for src, tgts in source_to_targets.items():
            for tgt in tgts:
                target_to_sources.setdefault(tgt, set()).add(src)
        return source_to_targets, target_to_sources

    def _find_diamond_matches(
        self,
        source_to_targets: dict[str, set[str]],
        target_to_sources: dict[str, set[str]],
        max_matches: int,
    ) -> list[StructuralMatch]:
        """Find diamond patterns (two source nodes sharing two target nodes)."""
        matches: list[StructuralMatch] = []
        seen: set[frozenset[str]] = set()
        for tgt, sources in target_to_sources.items():
            if len(sources) < 2:
                continue
            src_list = sorted(sources)
            for i in range(len(src_list)):
                for j in range(i + 1, len(src_list)):
                    a, b = src_list[i], src_list[j]
                    a_targets = source_to_targets.get(a, set())
                    b_targets = source_to_targets.get(b, set())
                    common = a_targets & b_targets
                    if len(common) >= 1:
                        key = frozenset({a, b, tgt})
                        if key not in seen:
                            seen.add(key)
                            self._graph.get_node(a)
                            self._graph.get_node(b)
                            self._graph.get_node(tgt)
                            matches.append(
                                StructuralMatch(
                                    pattern_name="diamond",
                                    bindings={
                                        "source_a": a,
                                        "source_b": b,
                                        "converge": tgt,
                                    },
                                    matched_nodes=[a, b, tgt],
                                    score=min(
                                        len(a_targets & b_targets) / max(len(a_targets | b_targets), 1),
                                        1.0,
                                    ),
                                )
                            )
                            if len(matches) >= max_matches:
                                return matches
        return matches

    def match_diamond(
        self,
        *,
        edge_label: str | None = None,
        max_matches: int = 50,
    ) -> list[StructuralMatch]:
        """Find convergence patterns (two paths merging into one node)."""
        source_to_targets, target_to_sources = self._build_source_target_maps(edge_label)
        return self._find_diamond_matches(source_to_targets, target_to_sources, max_matches)

    def _find_edge_candidates(
        self,
        pattern_edge: PatternEdge,
    ) -> list[tuple[Hyperedge, dict[str, str]]]:
        """Collect edges matching source/target role constraints."""
        candidates: list[tuple[Hyperedge, dict[str, str]]] = []
        for edge in self._graph.edges:
            if pattern_edge.label and edge.label != pattern_edge.label:
                continue
            if edge.weight < pattern_edge.min_weight:
                continue
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    bindings: dict[str, str] = {
                        pattern_edge.source_role: src,
                        pattern_edge.target_role: tgt,
                    }
                    candidates.append((edge, bindings))
        return candidates

    def _edge_exists(
        self,
        src_id: str,
        tgt_id: str,
        label: str | None,
        min_weight: float,
    ) -> bool:
        """Check whether an edge exists between two nodes with the given label."""
        for edge in self._graph.incident_edges(src_id):
            if label and edge.label != label:
                continue
            if edge.weight < min_weight:
                continue
            if tgt_id in edge.target_ids:
                return True
        return False

    def _validate_node_constraints(
        self,
        bindings: dict[str, str],
        pattern: PatternTemplate,
    ) -> bool:
        """Filter bindings by node data-type and label-pattern constraints."""
        for pnode in pattern.nodes:
            node_id = bindings.get(pnode.role)
            if not node_id:
                continue
            node = self._graph.get_node(node_id)
            if not node:
                return False
            if pnode.data_type:
                data_type = type(node.data).__name__ if node.data is not None else "NoneType"
                if data_type != pnode.data_type:
                    return False
            if pnode.label_pattern:
                import re

                if not re.search(pnode.label_pattern, node.label):
                    return False
            for key, value in pnode.constraints.items():
                if isinstance(node.data, dict) and node.data.get(key) != value:
                    return False
        return True

    def _score_match(
        self,
        bindings: dict[str, str],
        pattern: PatternTemplate,
    ) -> float:
        """Compute a match quality score based on edge weights and binding coverage."""
        total_weight = 0.0
        count = 0
        for pedge in pattern.edges:
            src_id = bindings.get(pedge.source_role)
            tgt_id = bindings.get(pedge.target_role)
            if src_id and tgt_id:
                for edge in self._graph.incident_edges(src_id):
                    if tgt_id in edge.target_ids and (not pedge.label or edge.label == pedge.label):
                        total_weight += edge.weight
                        count += 1
                        break
        return total_weight / max(count, 1)

    def _collect_matched_edges(
        self,
        bindings: dict[str, str],
        pattern: PatternTemplate,
    ) -> list[str]:
        """Collect edge objects for all bindings in a match."""
        matched: list[str] = []
        for pedge in pattern.edges:
            src_id = bindings.get(pedge.source_role)
            tgt_id = bindings.get(pedge.target_role)
            if src_id and tgt_id:
                for edge in self._graph.incident_edges(src_id):
                    if tgt_id in edge.target_ids and (not pedge.label or edge.label == pedge.label):
                        matched.append(edge.id)
                        break
        return matched

    def _find_chains_dfs(
        self,
        current: str,
        edge_label: str | None,
        min_length: int,
        max_length: int,
        path: list[str],
        visited: set[str],
        results: list[list[str]],
        max_chains: int,
    ) -> None:
        """DFS helper that extends chains through outgoing edges."""
        if len(results) >= max_chains:
            return
        if len(path) - 1 >= max_length:
            return
        if len(path) - 1 >= min_length:
            results.append(list(path))
        visited.add(current)
        for edge in self._graph.incident_edges(current):
            if edge_label and edge.label != edge_label:
                continue
            for nxt in edge.target_ids:
                if nxt not in visited:
                    path.append(nxt)
                    self._find_chains_dfs(
                        nxt,
                        edge_label,
                        min_length,
                        max_length,
                        path,
                        visited,
                        results,
                        max_chains,
                    )
                    path.pop()
        visited.discard(current)
