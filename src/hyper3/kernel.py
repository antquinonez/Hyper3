from __future__ import annotations

import heapq
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generator

import networkx as nx

from hyper3.exceptions import EdgeNotFoundError, NodeNotFoundError


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
        # Hyper3 edge weights represent importance (higher = stronger).
        # NetworkX treats weights as costs (higher = farther). Invert
        # so that important edges have low cost and are preferred by
        # shortest-path and centrality algorithms.
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


class EventLog:
    def __init__(self) -> None:
        self._log: list[dict[str, Any]] = []

    def record(self, event_type: str, **details: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details,
        }
        self._log.append(entry)
        return entry

    def query(
        self,
        event_type: str | None = None,
        since: float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        results = self._log
        if event_type is not None:
            results = [e for e in results if e["event_type"] == event_type]
        if since is not None:
            results = [e for e in results if e["timestamp"] >= since]
        if limit is not None:
            results = results[-limit:]
        return list(results)

    @property
    def size(self) -> int:
        return len(self._log)


class EquivalenceEngine:
    def __init__(self, graph: Hypergraph, *, threshold: float = 0.8) -> None:
        self._graph = graph
        self._threshold = threshold

    def find_equivalences(self) -> list[tuple[str, str, float]]:
        nodes = self._graph.nodes
        blocks: dict[str, list[Hypernode]] = {}
        for node in nodes:
            key = self._blocking_key(node)
            blocks.setdefault(key, []).append(node)
        pairs: list[tuple[str, str, float]] = []
        for block_nodes in blocks.values():
            if len(block_nodes) < 2:
                continue
            for i in range(len(block_nodes)):
                for j in range(i + 1, len(block_nodes)):
                    score = self._similarity(block_nodes[i], block_nodes[j])
                    if score >= self._threshold:
                        pairs.append((block_nodes[i].id, block_nodes[j].id, score))
        pairs.sort(key=lambda p: p[2], reverse=True)
        return pairs

    def _blocking_key(self, node: Hypernode) -> str:
        if node.data is None:
            return "none"
        if isinstance(node.data, dict):
            return f"dict:{','.join(sorted(node.data.keys())[:5])}"
        return type(node.data).__name__

    def _similarity(self, node_a: Hypernode, node_b: Hypernode) -> float:
        data_sim = node_a.matches(node_b)
        if data_sim >= self._threshold:
            return data_sim
        struct_sim = self._structural_similarity(node_a, node_b)
        combined = 0.4 * data_sim + 0.6 * struct_sim
        return max(data_sim, combined)

    def _structural_similarity(self, node_a: Hypernode, node_b: Hypernode) -> float:
        neighbors_a: set[str] = set()
        for edge in self._graph.edges_for(node_a.id):
            neighbors_a.update(edge.target_ids | edge.source_ids)
        neighbors_a.discard(node_a.id)
        neighbors_b: set[str] = set()
        for edge in self._graph.edges_for(node_b.id):
            neighbors_b.update(edge.target_ids | edge.source_ids)
        neighbors_b.discard(node_b.id)
        if not neighbors_a and not neighbors_b:
            return 1.0
        if not neighbors_a or not neighbors_b:
            return 0.0
        overlap = len(neighbors_a & neighbors_b)
        union = len(neighbors_a | neighbors_b)
        return overlap / union

    def merge_equivalences(self) -> list[str]:
        merged: list[str] = []
        used: set[str] = set()
        for primary_id, secondary_id, score in self.find_equivalences():
            if primary_id in used or secondary_id in used:
                continue
            result = self._graph.merge_node(primary_id, secondary_id)
            if result is not None:
                merged.append(secondary_id)
                used.add(secondary_id)
        return merged


class LazyCache:
    def __init__(self, *, max_size: int = 1024, ttl: float = 300.0) -> None:
        self._max_size = max_size
        self._ttl = ttl
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._access_history: list[str] = []
        self._transition_counts: dict[str, dict[str, int]] = {}
        self._prefetch_enabled: bool = False
        self._max_history: int = 1000

    def enable_prefetch(self, enabled: bool = True) -> None:
        self._prefetch_enabled = enabled

    def record_access(self, key: str) -> None:
        if self._access_history:
            prev = self._access_history[-1]
            if prev not in self._transition_counts:
                self._transition_counts[prev] = {}
            self._transition_counts[prev][key] = self._transition_counts[prev].get(key, 0) + 1
        self._access_history.append(key)
        if len(self._access_history) > self._max_history:
            self._access_history = self._access_history[-self._max_history:]

    def predict_next(self, current_key: str, top_k: int = 3) -> list[str]:
        transitions = self._transition_counts.get(current_key, {})
        if not transitions:
            return []
        sorted_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)
        return [k for k, _ in sorted_transitions[:top_k]]

    def prefetch_neighbors(self, key: str, values: dict[str, Any]) -> int:
        added = 0
        for k, v in values.items():
            if k not in self._cache:
                self.put(k, v)
                added += 1
        return added

    @property
    def prefetch_enabled(self) -> bool:
        return self._prefetch_enabled

    def get(self, key: str) -> Any | None:
        if self._prefetch_enabled:
            self.record_access(key)
        if key not in self._cache:
            return None
        cached_at, value = self._cache[key]
        if time.time() - cached_at > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def put(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (time.time(), value)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    def evict_expired(self) -> int:
        now = time.time()
        expired = [k for k, (t, _) in self._cache.items() if now - t > self._ttl]
        for k in expired:
            del self._cache[k]
        return len(expired)

    @property
    def size(self) -> int:
        return len(self._cache)


class TraversalEngine:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph

    def traverse_breadth_first(
        self, start_id: str, *, max_depth: int = 5, max_nodes: int = 100
    ) -> list[Hypernode]:
        visited: set[str] = set()
        result: list[Hypernode] = []
        frontier: list[str] = [start_id]
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: list[str] = []
            for nid in frontier:
                if nid in visited or len(result) >= max_nodes:
                    continue
                visited.add(nid)
                node = self._graph.get_node(nid)
                if node:
                    node.touch(time.time())
                    result.append(node)
                next_frontier.extend(
                    n for n in self._graph.neighbors(nid) if n not in visited
                )
            frontier = next_frontier
        return result

    def traverse_depth_first(
        self, start_id: str, *, max_depth: int = 5, max_nodes: int = 100
    ) -> list[Hypernode]:
        visited: set[str] = set()
        result: list[Hypernode] = []

        def _dfs(nid: str, depth: int) -> None:
            if nid in visited or depth > max_depth or len(result) >= max_nodes:
                return
            visited.add(nid)
            node = self._graph.get_node(nid)
            if node:
                node.touch(time.time())
                result.append(node)
            for neighbor_id in self._graph.neighbors(nid):
                _dfs(neighbor_id, depth + 1)

        _dfs(start_id, 0)
        return result

    def traverse_dimension(
        self,
        start_id: str,
        modality: Modality,
        *,
        max_depth: int = 5,
        max_nodes: int = 100,
    ) -> list[Hypernode]:
        visited: set[str] = set()
        result: list[Hypernode] = []
        frontier: list[str] = [start_id]
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: list[str] = []
            for nid in frontier:
                if nid in visited or len(result) >= max_nodes:
                    continue
                visited.add(nid)
                node = self._graph.get_node(nid)
                if node and modality in node.metadata.modality_tags:
                    node.touch(time.time())
                    result.append(node)
                next_frontier.extend(
                    n for n in self._graph.neighbors(nid) if n not in visited
                )
            frontier = next_frontier
        return result

    def traverse_adaptive(
        self,
        start_id: str,
        *,
        predicate: Callable[[Hypernode], bool] | None = None,
        max_depth: int = 5,
        max_nodes: int = 100,
    ) -> list[Hypernode]:
        visited: set[str] = set()
        result: list[Hypernode] = []
        frontier: list[tuple[float, str]] = [(-1.0, start_id)]
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: list[tuple[float, str]] = []
            processed: list[tuple[float, str]] = []
            while frontier:
                processed.append(heapq.heappop(frontier))
            for neg_priority, nid in processed:
                if nid in visited or len(result) >= max_nodes:
                    continue
                visited.add(nid)
                node = self._graph.get_node(nid)
                if node:
                    node.touch(time.time())
                    if predicate is None or predicate(node):
                        result.append(node)
                for neighbor_id in self._graph.neighbors(nid):
                    if neighbor_id not in visited:
                        neighbor = self._graph.get_node(neighbor_id)
                        priority = neighbor.weight if neighbor else 1.0
                        heapq.heappush(next_frontier, (-priority, neighbor_id))
            frontier = next_frontier
        return result


@dataclass
class SliceConfig:
    max_nodes: int = 50
    max_depth: int = 3
    modalities: set[Modality] | None = None
    abstraction_layers: set[AbstractionLayer] | None = None
    min_weight: float = 0.0
    predicate: Callable[[Hypernode], bool] | None = None


class ObserverSlice:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._config = SliceConfig()

    def configure(self, **kwargs: Any) -> SliceConfig:
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        return self._config

    @property
    def config(self) -> SliceConfig:
        return self._config

    def narrow(self, start_id: str, *, max_depth: int = 2, max_nodes: int = 10) -> list[Hypernode]:
        self._config.max_depth = max_depth
        self._config.max_nodes = max_nodes
        return self.apply(start_id)

    def broaden(self, start_id: str, *, max_depth: int = 6, max_nodes: int = 200) -> list[Hypernode]:
        self._config.max_depth = max_depth
        self._config.max_nodes = max_nodes
        return self.apply(start_id)

    def apply(self, start_id: str) -> list[Hypernode]:
        engine = TraversalEngine(self._graph)

        def _filter(node: Hypernode) -> bool:
            if self._config.modalities and not (
                node.metadata.modality_tags & self._config.modalities
            ):
                return False
            if self._config.abstraction_layers and node.metadata.abstraction_layer not in self._config.abstraction_layers:
                return False
            if node.weight < self._config.min_weight:
                return False
            if self._config.predicate and not self._config.predicate(node):
                return False
            return True

        return engine.traverse_adaptive(
            start_id,
            predicate=_filter,
            max_depth=self._config.max_depth,
            max_nodes=self._config.max_nodes,
        )


@dataclass
class EvolutionMetrics:
    total_merges: int = 0
    total_prunes: int = 0
    total_decay_events: int = 0
    total_refinements: int = 0


class SelfEvolutionEngine:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        decay_threshold: float = 0.1,
        prune_access_count: int = 0,
        merge_threshold: float = 0.8,
    ) -> None:
        self._graph = graph
        self._equivalence = EquivalenceEngine(graph, threshold=merge_threshold)
        self._decay_threshold = decay_threshold
        self._prune_access_count = prune_access_count
        self._metrics = EvolutionMetrics()

    @property
    def metrics(self) -> EvolutionMetrics:
        return self._metrics

    def decay_weights(self, factor: float = 0.95) -> int:
        decayed = 0
        for node in self._graph.nodes:
            old_weight = node.weight
            node.weight *= factor
            if old_weight > self._decay_threshold and node.weight <= self._decay_threshold:
                decayed += 1
                self._metrics.total_decay_events += 1
        return decayed

    def prune_dead_nodes(self) -> list[str]:
        pruned: list[str] = []
        to_remove = [
            node.id
            for node in self._graph.nodes
            if node.weight <= self._decay_threshold
            and node.access_count <= self._prune_access_count
        ]
        for nid in to_remove:
            self._graph.remove_node(nid)
            pruned.append(nid)
        self._metrics.total_prunes += len(pruned)
        return pruned

    def merge_equivalences(self) -> list[str]:
        merged = self._equivalence.merge_equivalences()
        self._metrics.total_merges += len(merged)
        return merged

    def reinforce(self, node_id: str, boost: float = 1.1) -> None:
        node = self._graph.get_node(node_id)
        if node:
            node.weight = min(node.weight * boost, 100.0)

    def evolve(self) -> dict[str, Any]:
        decayed = self.decay_weights()
        pruned = self.prune_dead_nodes()
        merged = self.merge_equivalences()
        self._metrics.total_refinements += 1
        return {
            "decayed": decayed,
            "pruned": len(pruned),
            "merged": len(merged),
            "node_count": self._graph.node_count,
            "edge_count": self._graph.edge_count,
        }
