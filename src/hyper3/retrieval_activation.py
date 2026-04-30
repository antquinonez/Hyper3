from __future__ import annotations

from dataclasses import dataclass, field

from hyper3.kernel import Hypergraph


@dataclass
class ActivationResult:
    node_id: str
    label: str
    activation: float
    depth: int

    def __lt__(self, other: ActivationResult) -> bool:
        """Compare by activation level for sorting."""
        return self.activation < other.activation


@dataclass
class ActivationConfig:
    decay_factor: float = 0.85
    edge_weight_scale: float = 1.0
    label_rates: dict[str, float] = field(default_factory=dict)
    max_iterations: int = 5
    min_activation: float = 0.01
    activation_threshold: float = 0.1
    normalize_per_step: bool = True
    directional: bool = False


class SpreadingActivation:
    def __init__(self, graph: Hypergraph, *, config: ActivationConfig | None = None) -> None:
        """Initialize the spreading activation engine.

        Args:
            graph: The hypergraph to propagate energy through.
            config: Optional configuration; defaults are used if not provided.
        """
        self._graph = graph
        self._config = config or ActivationConfig()
        self._activations: dict[str, float] = {}
        self._depth_map: dict[str, int] = {}

    @property
    def config(self) -> ActivationConfig:
        """Return the activation configuration."""
        return self._config

    @property
    def activations(self) -> dict[str, float]:
        """Return a copy of the current activation levels keyed by node ID."""
        return dict(self._activations)

    def clear(self) -> None:
        """Reset all activations and depth tracking."""
        self._activations.clear()
        self._depth_map.clear()

    def stimulate(self, node_id: str, energy: float = 1.0) -> None:
        """Inject energy into a node, accumulating with any existing activation."""
        self._activations[node_id] = self._activations.get(node_id, 0.0) + energy
        if node_id not in self._depth_map:
            self._depth_map[node_id] = 0

    def stimulate_label(self, label: str, energy: float = 1.0) -> None:
        """Stimulate a node by its label."""
        node = self._graph.get_node_by_label(label)
        if node:
            self.stimulate(node.id, energy)

    def spread(self, iterations: int | None = None) -> dict[str, float]:
        """Spread activation energy across graph edges for the given number of iterations.

        Energy decays by ``decay_factor`` per hop and is split equally among
        neighbors. In directional mode, energy flows source→target at full
        rate and target→source at 0.3x rate. Tracks minimum depth per node.
        Normalizes to preserve max activation when ``normalize_per_step`` is True.
        """
        iters = iterations if iterations is not None else self._config.max_iterations
        for _ in range(iters):
            if not self._activations:
                break
            delta: dict[str, float] = {}
            delta_depth: dict[str, int] = {}
            current_max = max(self._activations.values()) if self._activations else 0.0
            for node_id, activation in list(self._activations.items()):
                edges = self._graph.incident_edges(node_id)
                for edge in edges:
                    rate = self._config.label_rates.get(edge.label, 1.0) * edge.weight * self._config.edge_weight_scale
                    if self._config.directional:
                        if node_id in edge.source_ids:
                            neighbors = edge.target_ids
                        else:
                            neighbors = edge.source_ids
                            rate *= 0.3
                    else:
                        neighbors = edge.node_ids - {node_id}
                    spread_energy = activation * rate * self._config.decay_factor
                    per_neighbor = spread_energy / len(neighbors) if neighbors else 0.0
                    for neighbor_id in neighbors:
                        delta[neighbor_id] = delta.get(neighbor_id, 0.0) + per_neighbor
                        current_depth = self._depth_map.get(node_id, 0)
                        existing_depth = self._depth_map.get(neighbor_id)
                        new_depth = current_depth + 1
                        if existing_depth is None or new_depth < existing_depth:
                            delta_depth[neighbor_id] = new_depth
            for nid, energy in delta.items():
                self._activations[nid] = self._activations.get(nid, 0.0) + energy
            for nid, depth in delta_depth.items():
                if nid not in self._depth_map or depth < self._depth_map[nid]:
                    self._depth_map[nid] = depth
            if self._config.normalize_per_step and current_max > 0:
                new_max = max(self._activations.values()) if self._activations else 0.0
                if new_max > 0:
                    scale = current_max / new_max
                    self._activations = {nid: a * scale for nid, a in self._activations.items()}
            self._activations = {nid: a for nid, a in self._activations.items() if a >= self._config.min_activation}
        return dict(self._activations)

    def get_activated(
        self,
        threshold: float | None = None,
        top_k: int | None = None,
    ) -> list[ActivationResult]:
        """Return activated nodes above threshold, sorted by activation descending.

        Each result includes the propagation depth (minimum hops from the
        seed node). Use ``top_k`` to limit the result count.
        """
        t = threshold if threshold is not None else self._config.activation_threshold
        results: list[ActivationResult] = []
        for nid, activation in self._activations.items():
            if activation < t:
                continue
            node = self._graph.get_node(nid)
            label = node.label if node else ""
            depth = self._depth_map.get(nid, 0)
            results.append(ActivationResult(node_id=nid, label=label, activation=activation, depth=depth))
        results.sort(key=lambda r: r.activation, reverse=True)
        if top_k is not None:
            results = results[:top_k]
        return results

    def stimulate_and_spread(
        self,
        seeds: dict[str, float],
        *,
        iterations: int | None = None,
    ) -> list[ActivationResult]:
        """Stimulate multiple seed nodes and spread, returning activated results.

        Args:
            seeds: Dict mapping node IDs or labels to initial energy values.
            iterations: Override for number of spread iterations.

        Returns:
            Sorted list of ActivationResult above threshold.
        """
        for key, energy in seeds.items():
            node = self._graph.get_node(key)
            if node:
                self.stimulate(node.id, energy)
            else:
                node = self._graph.get_node_by_label(key)
                if node:
                    self.stimulate(node.id, energy)
        self.spread(iterations)
        return self.get_activated()

    def associative_recall(
        self,
        concept: str,
        *,
        energy: float = 1.0,
        top_k: int = 10,
        iterations: int | None = None,
    ) -> list[ActivationResult]:
        """Recall concepts associated with the given seed via spreading activation.

        Args:
            concept: Label or ID of the seed concept.
            energy: Initial energy to inject.
            top_k: Maximum number of results to return.
            iterations: Override for spread iterations.

        Returns:
            Activated nodes (excluding the seed), sorted by activation.
        """
        seed_node = self._graph.get_node_by_label(concept)
        if not seed_node:
            seed_node = self._graph.get_node(concept)
        if not seed_node:
            return []
        self.stimulate(seed_node.id, energy)
        self.spread(iterations)
        results = self.get_activated(top_k=top_k * 2)
        results = [r for r in results if r.node_id != seed_node.id]
        return results[:top_k]

    def spread_hyperedge(
        self,
        *,
        mode: str = "linear",
        iterations: int | None = None,
    ) -> dict[str, float]:
        """Spread activation using hypergraph-native diffusion.

        Unlike :meth:`spread` which treats each (source, target) pair
        independently, this method treats each hyperedge as a unit.
        Activation flows through a hyperedge only if the edge's gate
        condition is met, controlled by ``mode``:

        - ``"linear"``: standard weighted propagation through all targets.
        - ``"and"``: activation flows through a hyperedge only if ALL
          source nodes of the edge are currently activated.
        - ``"or"``: activation flows if ANY source node is activated.
        - ``"majority"``: activation flows if more than half of source
          nodes are activated.

        Args:
            mode: Gate mode for n-ary edge activation flow.
            iterations: Number of diffusion iterations.

        Returns:
            Dict mapping node ID to activation level.
        """
        iters = iterations if iterations is not None else self._config.max_iterations
        threshold = self._config.min_activation

        for _ in range(iters):
            if not self._activations:
                break
            delta: dict[str, float] = {}
            delta_depth: dict[str, int] = {}

            for edge in self._graph.edges:
                if not edge.source_ids or not edge.target_ids:
                    continue
                rate = self._config.label_rates.get(edge.label, 1.0) * edge.weight * self._config.edge_weight_scale

                source_activations = [self._activations.get(sid, 0.0) for sid in edge.source_ids]
                activated_sources = sum(1 for a in source_activations if a > 0)

                if mode == "and":
                    if activated_sources < len(edge.source_ids):
                        continue
                    gate_energy = sum(source_activations) / len(edge.source_ids)
                elif mode == "or":
                    if activated_sources == 0:
                        continue
                    gate_energy = max(source_activations)
                elif mode == "majority":
                    if activated_sources <= len(edge.source_ids) // 2:
                        continue
                    gate_energy = sum(a for a in source_activations if a > 0) / max(activated_sources, 1)
                else:
                    gate_energy = sum(source_activations) / len(edge.source_ids)

                spread_energy = gate_energy * rate * self._config.decay_factor
                per_target = spread_energy / len(edge.target_ids)

                for tid in edge.target_ids:
                    delta[tid] = delta.get(tid, 0.0) + per_target
                    for sid in edge.source_ids:
                        if sid in self._depth_map:
                            new_depth = self._depth_map[sid] + 1
                            existing = delta_depth.get(tid)
                            if existing is None or new_depth < existing:
                                delta_depth[tid] = new_depth
                            break

            for nid, energy in delta.items():
                self._activations[nid] = self._activations.get(nid, 0.0) + energy
            for nid, depth in delta_depth.items():
                if nid not in self._depth_map or depth < self._depth_map[nid]:
                    self._depth_map[nid] = depth

            self._activations = {nid: a for nid, a in self._activations.items() if a >= threshold}

        return dict(self._activations)
