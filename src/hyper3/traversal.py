from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from hyper3.kernel import Hypergraph, Hypernode, Modality, AbstractionLayer


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
            for _neg_priority, nid in processed:
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
