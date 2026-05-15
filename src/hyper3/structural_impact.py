"""StructuralImpactEngine: blast-radius and change impact analysis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class ComponentChange(_SimpleResultBase):
    """Change in connected component structure after an operation."""

    component_count_before: int = 0
    component_count_after: int = 0
    bridged: bool = False
    new_component_created: bool = False


@dataclass
class CycleChange(_SimpleResultBase):
    """Cycle creation result after an edge addition."""

    cycle_created: bool = False
    cycle_length: int = 0
    cycle_path: list[str] = field(default_factory=list)


@dataclass
class CentralityShift(_SimpleResultBase):
    """Change in a node's degree centrality after an operation."""

    node_id: str = ""
    degree_before: float = 0.0
    degree_after: float = 0.0
    became_hub: bool = False
    hub_threshold: float = 0.0


@dataclass
class ImpactResult(_SimpleResultBase):
    """Complete structural impact assessment for a single operation."""

    operation: str = ""
    node_or_edge_id: str = ""
    component_change: ComponentChange = field(default_factory=ComponentChange)
    cycle_change: CycleChange = field(default_factory=CycleChange)
    centrality_shifts: list[CentralityShift] = field(default_factory=list)
    density_before: float = 0.0
    density_after: float = 0.0
    node_count_before: int = 0
    node_count_after: int = 0
    edge_count_before: int = 0
    edge_count_after: int = 0
    severity: str = "low"


class StructuralImpactEngine:
    """Assess the structural impact of graph modifications.

    Computes a lightweight blast-radius analysis before and after each
    ``add()`` or ``link()`` call, reporting whether the operation created
    a cycle, bridged components, changed centrality rankings, or created
    a hub node.

    Args:
        graph: The hypergraph being monitored.
        hub_degree_threshold: Centrality value above which a node is
            classified as a hub (default 0.8).
        track_cycles: Whether to run cycle detection (can be expensive).
        track_components: Whether to track component changes.
    """

    def __init__(
        self,
        graph: Hypergraph,
        *,
        hub_degree_threshold: float = 0.8,
        track_cycles: bool = True,
        track_components: bool = True,
    ) -> None:
        """Initialize the structural impact engine."""
        self._graph = graph
        self._hub_threshold = hub_degree_threshold
        self._track_cycles = track_cycles
        self._track_components = track_components
        self._pre_state: dict[str, Any] = {}
        self._history: list[ImpactResult] = []
        self._max_history = 100

    def before_snapshot(self) -> None:
        """Capture graph state before an add or link operation."""
        g = self._graph
        self._pre_state = {
            "node_count": g.node_count,
            "edge_count": g.edge_count,
            "density": g.density(),
        }
        if self._track_components:
            self._pre_state["component_count"] = len(g.connected_components())
        if self._track_cycles:
            self._pre_state["has_cycle"] = g.has_cycle()
        centrality = g.degree_centrality()
        self._pre_state["centrality"] = centrality

    def assess_add(self, node_id: str) -> ImpactResult:
        """Assess structural impact after adding a node.

        Args:
            node_id: The ID of the newly added node.

        Returns:
            ImpactResult describing what changed.
        """
        g = self._graph
        pre = self._pre_state
        nc_before = pre.get("node_count", 0)
        ec_before = pre.get("edge_count", 0)
        density_before = pre.get("density", 0.0)
        cc_before = pre.get("component_count", 0)

        nc_after = g.node_count
        ec_after = g.edge_count
        density_after = g.density()
        cc_after = len(g.connected_components()) if self._track_components else cc_before

        component_change = ComponentChange(
            component_count_before=cc_before,
            component_count_after=cc_after,
            new_component_created=cc_after > cc_before,
        )

        result = ImpactResult(
            operation="add",
            node_or_edge_id=node_id,
            component_change=component_change,
            density_before=density_before,
            density_after=density_after,
            node_count_before=nc_before,
            node_count_after=nc_after,
            edge_count_before=ec_before,
            edge_count_after=ec_after,
            severity="low",
        )

        self._record(result)
        return result

    def assess_link(
        self,
        source_id: str,
        target_id: str,
        edge_id: str,
    ) -> ImpactResult:
        """Assess structural impact after adding an edge.

        Args:
            source_id: ID of the source node.
            target_id: ID of the target node.
            edge_id: ID of the newly created edge.

        Returns:
            ImpactResult describing what changed.
        """
        g = self._graph
        pre = self._pre_state
        nc_before = pre.get("node_count", 0)
        ec_before = pre.get("edge_count", 0)
        density_before = pre.get("density", 0.0)
        cc_before = pre.get("component_count", 0)
        had_cycle = pre.get("has_cycle", False)
        pre_centrality: dict[str, float] = pre.get("centrality", {})

        nc_after = g.node_count
        ec_after = g.edge_count
        density_after = g.density()

        component_change = ComponentChange(component_count_before=cc_before)
        if self._track_components:
            cc_after = len(g.connected_components())
            component_change.component_count_after = cc_after
            component_change.bridged = cc_after < cc_before

        cycle_change = CycleChange()
        if self._track_cycles:
            has_cycle_now = g.has_cycle()
            if has_cycle_now and not had_cycle:
                cycle_change.cycle_created = True
                cycles = g.detect_cycles(max_cycles=5)
                if cycles:
                    shortest = min(cycles, key=len)
                    cycle_change.cycle_length = len(shortest)
                    cycle_change.cycle_path = list(shortest)

        centrality_shifts: list[CentralityShift] = []
        post_centrality = g.degree_centrality()
        for nid in (source_id, target_id):
            before_deg = pre_centrality.get(nid, 0.0)
            after_deg = post_centrality.get(nid, 0.0)
            became_hub = after_deg >= self._hub_threshold and before_deg < self._hub_threshold
            if abs(after_deg - before_deg) > 0.001 or became_hub:
                centrality_shifts.append(
                    CentralityShift(
                        node_id=nid,
                        degree_before=before_deg,
                        degree_after=after_deg,
                        became_hub=became_hub,
                        hub_threshold=self._hub_threshold,
                    )
                )

        severity = self._classify_severity(
            component_change, cycle_change, centrality_shifts,
            density_before, density_after,
        )

        result = ImpactResult(
            operation="link",
            node_or_edge_id=edge_id,
            component_change=component_change,
            cycle_change=cycle_change,
            centrality_shifts=centrality_shifts,
            density_before=density_before,
            density_after=density_after,
            node_count_before=nc_before,
            node_count_after=nc_after,
            edge_count_before=ec_before,
            edge_count_after=ec_after,
            severity=severity,
        )

        self._record(result)
        return result

    def _classify_severity(
        self,
        component_change: ComponentChange,
        cycle_change: CycleChange,
        centrality_shifts: list[CentralityShift],
        density_before: float,
        density_after: float,
    ) -> str:
        """Classify the impact severity as ``"low"``, ``"medium"``, ``"high"``, or ``"critical"``."""
        severity = "low"
        if cycle_change.cycle_created:
            severity = "medium"
        if density_after - density_before > 0.05:
            severity = "medium"
        if component_change.bridged:
            severity = "high"
        if component_change.bridged and cycle_change.cycle_created:
            severity = "high"
        if (
            component_change.bridged
            and cycle_change.cycle_created
            and any(s.became_hub for s in centrality_shifts)
        ):
            severity = "critical"
        return severity

    def get_history(self, *, limit: int = 50) -> list[ImpactResult]:
        """Return the most recent impact results.

        Args:
            limit: Maximum number of results to return.

        Returns:
            List of recent ImpactResult objects, newest first.
        """
        return list(reversed(self._history[-limit:]))

    def clear_history(self) -> None:
        """Clear all stored impact history."""
        self._history.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize engine configuration to a plain dict."""
        return {
            "hub_degree_threshold": self._hub_threshold,
            "track_cycles": self._track_cycles,
            "track_components": self._track_components,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> StructuralImpactEngine:
        """Restore an engine from a serialized config dict."""
        return cls(
            graph,
            hub_degree_threshold=float(data.get("hub_degree_threshold", 0.8)),
            track_cycles=bool(data.get("track_cycles", True)),
            track_components=bool(data.get("track_components", True)),
        )

    def _record(self, result: ImpactResult) -> None:
        """Append an impact result to the bounded history list."""
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
