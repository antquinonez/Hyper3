from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import networkx as nx

from hyper3.exceptions import NodeNotFoundError


class Modality(Enum):
    TEXTUAL = "textual"
    CONCEPTUAL = "conceptual"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    SENSORY = "sensory"
    ABSTRACT = "abstract"


class AbstractionLayer(Enum):
    DETAIL = "detail"
    INTERMEDIATE = "intermediate"
    SUMMARY = "summary"


@dataclass
class Metadata:
    temporal_tags: dict[str, Any] = field(default_factory=dict)
    modality_tags: set[Modality] = field(default_factory=set)
    abstraction_layer: AbstractionLayer = AbstractionLayer.INTERMEDIATE
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypernode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    label: str = ""
    data: Any = None
    metadata: Metadata = field(default_factory=Metadata)
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    weight: float = 1.0

    def touch(self, now: float) -> None:
        self.access_count += 1
        self.last_accessed = now

    @property
    def is_active(self) -> bool:
        return self.access_count > 0

    def matches(self, other: Hypernode) -> float:
        if self.data is None or other.data is None:
            return 0.0
        if self.data == other.data:
            return 1.0
        if isinstance(self.data, (str, int, float, bool)) and self.data == other.data:
            return 1.0
        if isinstance(self.data, dict) and isinstance(other.data, dict):
            shared = set(self.data.keys()) & set(other.data.keys())
            if not shared:
                return 0.0
            matches = sum(1 for k in shared if self.data[k] == other.data[k])
            return matches / len(shared)
        return 0.0


@dataclass
class Hyperedge:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_ids: frozenset[str] = field(default_factory=frozenset)
    target_ids: frozenset[str] = field(default_factory=frozenset)
    label: str = ""
    data: Any = None
    metadata: Metadata = field(default_factory=Metadata)
    weight: float = 1.0

    @property
    def node_ids(self) -> frozenset[str]:
        return self.source_ids | self.target_ids


class Hypergraph:
    def __init__(self) -> None:
        self._nodes: dict[str, Hypernode] = {}
        self._edges: dict[str, Hyperedge] = {}
        self._node_to_edges: dict[str, set[str]] = {}
        self._dimension_index: dict[str, set[str]] = {}
        self._label_index: dict[str, str] = {}
        self._neighbor_cache: dict[str, list[str]] | None = None
        self._batch_mode: bool = False
        self._cache_invalidated_in_batch: bool = False

    def add_node(self, node: Hypernode) -> Hypernode:
        if node.id in self._nodes:
            return self._nodes[node.id]
        self._nodes[node.id] = node
        self._node_to_edges[node.id] = set()
        if node.label:
            self._label_index[node.label] = node.id
        for modality in node.metadata.modality_tags:
            self._dimension_index.setdefault(modality.value, set()).add(node.id)
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return node

    def get_node(self, node_id: str) -> Hypernode | None:
        return self._nodes.get(node_id)

    def get_node_by_label(self, label: str) -> Hypernode | None:
        nid = self._label_index.get(label)
        if nid:
            return self._nodes.get(nid)
        return None

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        edge_ids_to_remove = list(self._node_to_edges.get(node_id, set()))
        for edge_id in edge_ids_to_remove:
            self.remove_edge(edge_id)
        node = self._nodes[node_id]
        if node.label:
            self._label_index.pop(node.label, None)
        del self._nodes[node_id]
        del self._node_to_edges[node_id]
        for dim_set in self._dimension_index.values():
            dim_set.discard(node_id)
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return True

    def add_edge(self, edge: Hyperedge) -> Hyperedge:
        if edge.id in self._edges:
            return self._edges[edge.id]
        for nid in edge.node_ids:
            if nid not in self._nodes:
                raise NodeNotFoundError(nid)
            self._node_to_edges[nid].add(edge.id)
        self._edges[edge.id] = edge
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return edge

    def get_edge(self, edge_id: str) -> Hyperedge | None:
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        if edge_id not in self._edges:
            return False
        edge = self._edges[edge_id]
        for nid in edge.node_ids:
            if nid in self._node_to_edges:
                self._node_to_edges[nid].discard(edge_id)
        del self._edges[edge_id]
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return True

    def edges_for(self, node_id: str) -> list[Hyperedge]:
        edge_ids = self._node_to_edges.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def neighbors(self, node_id: str) -> list[str]:
        if self._neighbor_cache is None:
            self._neighbor_cache = {}
            for nid in self._nodes:
                nbrs: set[str] = set()
                for edge in self.edges_for(nid):
                    nbrs.update(edge.node_ids)
                nbrs.discard(nid)
                self._neighbor_cache[nid] = list(nbrs)
        return self._neighbor_cache.get(node_id, [])

    def begin_batch(self) -> None:
        self._batch_mode = True
        self._cache_invalidated_in_batch = False

    def end_batch(self) -> None:
        self._batch_mode = False
        if self._cache_invalidated_in_batch:
            self._neighbor_cache = None
            self._cache_invalidated_in_batch = False

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        *,
        edge_label: str | None = None,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> list[list[str]]:
        if source_id not in self._nodes or target_id not in self._nodes:
            return []
        paths: list[list[str]] = []
        self._find_paths_dfs(source_id, target_id, edge_label, max_depth, max_paths, [source_id], set(), paths)
        return paths

    def _find_paths_dfs(
        self,
        current: str,
        target: str,
        edge_label: str | None,
        max_depth: int,
        max_paths: int,
        path: list[str],
        visited: set[str],
        results: list[list[str]],
    ) -> None:
        if len(results) >= max_paths:
            return
        if current == target:
            results.append(list(path))
            return
        if len(path) > max_depth:
            return
        visited.add(current)
        for edge in self.edges_for(current):
            if edge_label is not None and edge.label != edge_label:
                continue
            for next_id in edge.target_ids:
                if next_id not in visited:
                    path.append(next_id)
                    self._find_paths_dfs(next_id, target, edge_label, max_depth, max_paths, path, visited, results)
                    path.pop()
        visited.discard(current)

    def pattern_match(
        self,
        *,
        edge_label: str | None = None,
        source_label: str | None = None,
        target_label: str | None = None,
        limit: int = 100,
    ) -> list[tuple[Hyperedge, dict[str, str]]]:
        results: list[tuple[Hyperedge, dict[str, str]]] = []
        for edge in self._edges.values():
            if edge_label is not None and edge.label != edge_label:
                continue
            source_match = False
            target_match = False
            source_labels: set[str] = set()
            target_labels: set[str] = set()
            for sid in edge.source_ids:
                node = self._nodes.get(sid)
                if node:
                    source_labels.add(node.label)
            for tid in edge.target_ids:
                node = self._nodes.get(tid)
                if node:
                    target_labels.add(node.label)
            if source_label is not None:
                source_match = source_label in source_labels
            else:
                source_match = True
            if target_label is not None:
                target_match = target_label in target_labels
            else:
                target_match = True
            if source_match and target_match:
                bindings: dict[str, str] = {}
                bindings["source_label"] = next(iter(source_labels)) if source_labels else ""
                bindings["target_label"] = next(iter(target_labels)) if target_labels else ""
                results.append((edge, bindings))
                if len(results) >= limit:
                    break
        return results

    def subgraph(self, node_ids: set[str]) -> Hypergraph:
        result = Hypergraph()
        id_set = node_ids & set(self._nodes.keys())
        for nid in id_set:
            node = self._nodes[nid]
            result.add_node(Hypernode(
                id=node.id,
                label=node.label,
                data=node.data,
                metadata=Metadata(
                    temporal_tags=dict(node.metadata.temporal_tags),
                    modality_tags=set(node.metadata.modality_tags),
                    abstraction_layer=node.metadata.abstraction_layer,
                    custom=dict(node.metadata.custom),
                ),
                access_count=node.access_count,
                created_at=node.created_at,
                last_accessed=node.last_accessed,
                weight=node.weight,
            ))
        for edge in self._edges.values():
            if edge.source_ids <= id_set and edge.target_ids <= id_set:
                result.add_edge(Hyperedge(
                    id=edge.id,
                    source_ids=frozenset(edge.source_ids),
                    target_ids=frozenset(edge.target_ids),
                    label=edge.label,
                    data=edge.data,
                    metadata=Metadata(
                        temporal_tags=dict(edge.metadata.temporal_tags),
                        modality_tags=set(edge.metadata.modality_tags),
                        abstraction_layer=edge.metadata.abstraction_layer,
                        custom=dict(edge.metadata.custom),
                    ),
                    weight=edge.weight,
                ))
        return result

    def to_networkx(self) -> nx.DiGraph:
        G = nx.DiGraph()
        for node in self._nodes.values():
            G.add_node(node.id, label=node.label, weight=node.weight, data=node.data)
        for edge in self._edges.values():
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    G.add_edge(src, tgt, label=edge.label, weight=edge.weight, edge_id=edge.id)
        return G

    def _to_networkx_inverted_weights(self) -> nx.DiGraph:
        G = self.to_networkx()
        for u, v, data in G.edges(data=True):
            w = data.get("weight", 1.0)
            data["cost"] = 1.0 / max(w, 1e-9)
        return G

    def degree_centrality(self) -> dict[str, float]:
        n = len(self._nodes)
        if n <= 1:
            return {nid: 1.0 for nid in self._nodes}
        result: dict[str, float] = {}
        for nid in self._nodes:
            degree = len(self.edges_for(nid))
            result[nid] = degree / (n - 1)
        return result

    def betweenness_centrality(self) -> dict[str, float]:
        G = self._to_networkx_inverted_weights()
        if G.number_of_nodes() == 0:
            return {}
        return dict(nx.betweenness_centrality(G, weight="cost"))

    def connected_components(self) -> list[set[str]]:
        G = self.to_networkx()
        if G.number_of_nodes() == 0:
            return []
        return [set(c) for c in nx.weakly_connected_components(G)]

    def has_cycle(self) -> bool:
        G = self.to_networkx()
        if G.number_of_nodes() == 0:
            return False
        try:
            nx.find_cycle(G)
            return True
        except nx.NetworkXNoCycle:
            return False

    def detect_cycles(self, max_cycles: int = 10) -> list[list[str]]:
        G = self.to_networkx()
        if G.number_of_nodes() == 0:
            return []
        cycles: list[list[str]] = []
        try:
            for cycle in nx.simple_cycles(G):
                cycles.append(cycle)
                if len(cycles) >= max_cycles:
                    break
        except Exception:
            pass
        return cycles

    def shortest_path(self, source_id: str, target_id: str, weighted: bool = True) -> list[str] | None:
        if weighted:
            G = self._to_networkx_inverted_weights()
            weight_attr = "cost"
        else:
            G = self.to_networkx()
            weight_attr = None
        if source_id not in G or target_id not in G:
            return None
        try:
            if weight_attr:
                return nx.dijkstra_path(G, source_id, target_id, weight=weight_attr)
            return nx.shortest_path(G, source_id, target_id)
        except nx.NetworkXNoPath:
            return None

    def node_degree(self, node_id: str) -> int:
        return len(self.edges_for(node_id))

    def degree_distribution(self) -> dict[int, int]:
        dist: dict[int, int] = {}
        for nid in self._nodes:
            d = len(self.edges_for(nid))
            dist[d] = dist.get(d, 0) + 1
        return dist

    def query_dimension(self, modality: Modality) -> list[Hypernode]:
        node_ids = self._dimension_index.get(modality.value, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def merge_node(self, primary_id: str, secondary_id: str) -> Hypernode | None:
        primary = self._nodes.get(primary_id)
        secondary = self._nodes.get(secondary_id)
        if not primary or not secondary:
            return None
        primary.access_count += secondary.access_count
        primary.weight = max(primary.weight, secondary.weight)
        if primary.label and secondary.label and primary.label != secondary.label:
            if not primary.metadata.custom.get("aliases"):
                primary.metadata.custom["aliases"] = []
            if secondary.label not in primary.metadata.custom["aliases"]:
                primary.metadata.custom["aliases"].append(secondary.label)
        if secondary.label and secondary.label in self._label_index:
            del self._label_index[secondary.label]
        for modality in secondary.metadata.modality_tags:
            primary.metadata.modality_tags.add(modality)
        edges_to_rewire = list(self._node_to_edges.get(secondary_id, set()))
        for edge_id in edges_to_rewire:
            edge = self._edges.get(edge_id)
            if not edge:
                continue
            new_source = (edge.source_ids - {secondary_id}) | {primary_id}
            new_target = (edge.target_ids - {secondary_id}) | {primary_id}
            edge.source_ids = frozenset(new_source)
            edge.target_ids = frozenset(new_target)
            self._node_to_edges[primary_id].add(edge_id)
        self._node_to_edges[secondary_id].clear()
        self.remove_node(secondary_id)
        return primary

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def nodes(self) -> list[Hypernode]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Hyperedge]:
        return list(self._edges.values())
