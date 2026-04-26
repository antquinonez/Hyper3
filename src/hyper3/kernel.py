from __future__ import annotations

import heapq
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generator

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

    def add_node(self, node: Hypernode) -> Hypernode:
        if node.id in self._nodes:
            return self._nodes[node.id]
        self._nodes[node.id] = node
        self._node_to_edges[node.id] = set()
        if node.label:
            self._label_index[node.label] = node.id
        for modality in node.metadata.modality_tags:
            self._dimension_index.setdefault(modality.value, set()).add(node.id)
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
        pairs: list[tuple[str, str, float]] = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                score = nodes[i].matches(nodes[j])
                if score >= self._threshold:
                    pairs.append((nodes[i].id, nodes[j].id, score))
        pairs.sort(key=lambda p: p[2], reverse=True)
        return pairs

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

    def get(self, key: str) -> Any | None:
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
