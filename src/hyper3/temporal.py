from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


class AllenRelation(Enum):
    BEFORE = "before"
    AFTER = "after"
    MEETS = "meets"
    MET_BY = "met_by"
    OVERLAPS = "overlaps"
    OVERLAPPED_BY = "overlapped_by"
    CONTAINS = "contains"
    DURING = "during"
    STARTS = "starts"
    STARTED_BY = "started_by"
    FINISHES = "finishes"
    FINISHED_BY = "finished_by"
    EQUALS = "equals"


INVERSE_RELATIONS: dict[AllenRelation, AllenRelation] = {
    AllenRelation.BEFORE: AllenRelation.AFTER,
    AllenRelation.AFTER: AllenRelation.BEFORE,
    AllenRelation.MEETS: AllenRelation.MET_BY,
    AllenRelation.MET_BY: AllenRelation.MEETS,
    AllenRelation.OVERLAPS: AllenRelation.OVERLAPPED_BY,
    AllenRelation.OVERLAPPED_BY: AllenRelation.OVERLAPS,
    AllenRelation.CONTAINS: AllenRelation.DURING,
    AllenRelation.DURING: AllenRelation.CONTAINS,
    AllenRelation.STARTS: AllenRelation.STARTED_BY,
    AllenRelation.STARTED_BY: AllenRelation.STARTS,
    AllenRelation.FINISHES: AllenRelation.FINISHED_BY,
    AllenRelation.FINISHED_BY: AllenRelation.FINISHES,
    AllenRelation.EQUALS: AllenRelation.EQUALS,
}


@dataclass
class TimeInterval:
    start: float
    end: float

    def __post_init__(self):
        """Validate that the interval end is not before the start."""
        import math

        if math.isnan(self.start) or math.isnan(self.end):
            raise ValueError(f"Interval bounds must be finite numbers, got start={self.start}, end={self.end}")
        if self.end < self.start:
            raise ValueError(f"Interval end ({self.end}) must be >= start ({self.start})")

    @property
    def duration(self) -> float:
        """Return the length of the interval."""
        return self.end - self.start

    @staticmethod
    def _check_point_relations(a_s: float, a_e: float, b_s: float, b_e: float) -> AllenRelation | None:
        if a_s == b_s and a_e == b_e:
            return AllenRelation.EQUALS
        if a_e == b_s:
            return AllenRelation.MEETS
        if a_s == b_e:
            return AllenRelation.MET_BY
        if a_e < b_s:
            return AllenRelation.BEFORE
        if a_s > b_e:
            return AllenRelation.AFTER
        return None

    @staticmethod
    def _check_endpoint_shared(a_s: float, a_e: float, b_s: float, b_e: float) -> AllenRelation | None:
        if a_s == b_s:
            if a_e < b_e:
                return AllenRelation.STARTS
            return AllenRelation.STARTED_BY
        if a_e == b_e:
            if a_s < b_s:
                return AllenRelation.FINISHED_BY
            return AllenRelation.FINISHES
        return None

    @staticmethod
    def _check_containment(a_s: float, a_e: float, b_s: float, b_e: float) -> AllenRelation | None:
        if a_s < b_s and a_e > b_e:
            return AllenRelation.CONTAINS
        if a_s > b_s and a_e < b_e:
            return AllenRelation.DURING
        return None

    @staticmethod
    def _check_overlap(a_s: float, a_e: float, b_s: float, b_e: float) -> AllenRelation | None:
        if a_s < b_s and a_e > b_s and a_e < b_e:
            return AllenRelation.OVERLAPS
        if a_s > b_s and a_s < b_e and a_e > b_e:
            return AllenRelation.OVERLAPPED_BY
        return None

    def relate_to(self, other: TimeInterval) -> AllenRelation:
        """Classify the Allen interval relation between this interval and another.

        Args:
            other: The interval to compare against.

        Returns:
            The AllenRelation describing how self relates to other.
        """
        a_s, a_e = self.start, self.end
        b_s, b_e = other.start, other.end

        return (
            TimeInterval._check_point_relations(a_s, a_e, b_s, b_e)
            or TimeInterval._check_endpoint_shared(a_s, a_e, b_s, b_e)
            or TimeInterval._check_containment(a_s, a_e, b_s, b_e)
            or TimeInterval._check_overlap(a_s, a_e, b_s, b_e)
            or AllenRelation.EQUALS
        )

    def overlaps_interval(self, other: TimeInterval) -> bool:
        """Return True if this interval overlaps with other (open-ended comparison)."""
        return self.start < other.end and other.start < self.end

    def contains_point(self, t: float) -> bool:
        """Return True if time point t falls within this closed interval."""
        return self.start <= t <= self.end


@dataclass
class TemporalEvent(_SimpleResultBase):
    event_id: str
    label: str
    interval: TimeInterval
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalConstraint(_SimpleResultBase):
    event_a_id: str
    event_b_id: str
    relation: AllenRelation
    confidence: float = 1.0

    @property
    def inverse(self) -> TemporalConstraint:
        return TemporalConstraint(
            event_a_id=self.event_b_id,
            event_b_id=self.event_a_id,
            relation=INVERSE_RELATIONS[self.relation],
            confidence=self.confidence,
        )


def _dfs_causal_paths(
    node: str,
    adj: dict[str, set[str]],
    memo: dict[str, list[list[str]]],
    all_chains: list[list[str]],
    max_chains: int,
) -> list[list[str]]:
    """Recursively enumerate all paths starting from node."""
    if node in memo:
        return memo[node]
    paths: list[list[str]] = [[node]]
    for nxt in adj.get(node, set()):
        if len(all_chains) >= max_chains:
            break
        for sub in _dfs_causal_paths(nxt, adj, memo, all_chains, max_chains):
            if len(all_chains) >= max_chains:
                break
            paths.append([node] + sub)
    memo[node] = paths
    return paths


def _deduplicate_chains(chains: list[list[str]]) -> list[list[str]]:
    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for chain in chains:
        key = tuple(chain)
        if key not in seen:
            seen.add(key)
            unique.append(chain)
    return unique


class TemporalReasoner:
    def __init__(self, graph: Hypergraph) -> None:
        """Initialize the reasoner with a hypergraph.

        Args:
            graph: The hypergraph whose nodes map to temporal events.
        """
        self._graph = graph
        self._events: dict[str, TemporalEvent] = {}
        self._constraints: list[TemporalConstraint] = []

    def add_event(
        self,
        event_id: str,
        label: str,
        start: float,
        end: float,
        **metadata: Any,
    ) -> TemporalEvent:
        """Register a temporal event with the given time interval.

        Args:
            event_id: Unique identifier for the event.
            label: Human-readable label (typically matches a hypernode label).
            start: Start time of the event.
            end: End time of the event.
            **metadata: Additional metadata stored on the event.

        Returns:
            The created TemporalEvent.
        """
        interval = TimeInterval(start=start, end=end)
        event = TemporalEvent(
            event_id=event_id,
            label=label,
            interval=interval,
            metadata=metadata,
        )
        self._events[event_id] = event
        return event

    def get_event(self, event_id: str) -> TemporalEvent | None:
        """Look up an event by ID, returning None if not found."""
        return self._events.get(event_id)

    def add_constraint(
        self,
        event_a_id: str,
        event_b_id: str,
        relation: AllenRelation,
        confidence: float = 1.0,
    ) -> TemporalConstraint:
        """Add an explicit temporal constraint between two events.

        Args:
            event_a_id: First event ID.
            event_b_id: Second event ID.
            relation: The required Allen relation from A to B.
            confidence: Confidence score for the constraint.

        Returns:
            The created TemporalConstraint.
        """
        constraint = TemporalConstraint(
            event_a_id=event_a_id,
            event_b_id=event_b_id,
            relation=relation,
            confidence=confidence,
        )
        self._constraints.append(constraint)
        return constraint

    def infer_constraints(self) -> list[TemporalConstraint]:
        """Compute pairwise Allen relations for all registered events."""
        inferred: list[TemporalConstraint] = []
        event_ids = list(self._events.keys())
        for i in range(len(event_ids)):
            for j in range(i + 1, len(event_ids)):
                a_id = event_ids[i]
                b_id = event_ids[j]
                a = self._events[a_id]
                b = self._events[b_id]
                rel = a.interval.relate_to(b.interval)
                inferred.append(
                    TemporalConstraint(
                        event_a_id=a_id,
                        event_b_id=b_id,
                        relation=rel,
                    )
                )
        return inferred

    def find_before(self, event_id: str) -> list[TemporalEvent]:
        """Return all events that occur entirely before the given event."""
        target = self._events.get(event_id)
        if not target:
            return []
        return [
            ev
            for ev in self._events.values()
            if ev.event_id != event_id and ev.interval.relate_to(target.interval) == AllenRelation.BEFORE
        ]

    def find_after(self, event_id: str) -> list[TemporalEvent]:
        """Return all events that occur entirely after the given event."""
        target = self._events.get(event_id)
        if not target:
            return []
        return [
            ev
            for ev in self._events.values()
            if ev.event_id != event_id and ev.interval.relate_to(target.interval) == AllenRelation.AFTER
        ]

    def find_overlapping(self, event_id: str) -> list[TemporalEvent]:
        """Return all events that temporally overlap with the given event."""
        target = self._events.get(event_id)
        if not target:
            return []
        overlapping_relations = {
            AllenRelation.OVERLAPS,
            AllenRelation.OVERLAPPED_BY,
            AllenRelation.CONTAINS,
            AllenRelation.DURING,
            AllenRelation.STARTS,
            AllenRelation.STARTED_BY,
            AllenRelation.FINISHES,
            AllenRelation.FINISHED_BY,
            AllenRelation.EQUALS,
        }
        return [
            ev
            for ev in self._events.values()
            if ev.event_id != event_id and ev.interval.relate_to(target.interval) in overlapping_relations
        ]

    def find_containing(self, event_id: str) -> list[TemporalEvent]:
        """Return all events whose intervals fully contain the given event's interval."""
        target = self._events.get(event_id)
        if not target:
            return []
        return [
            ev
            for ev in self._events.values()
            if ev.event_id != event_id and ev.interval.relate_to(target.interval) == AllenRelation.CONTAINS
        ]

    def causal_order(self, event_ids: list[str]) -> list[str]:
        """Sort the given event IDs by start time.

        Args:
            event_ids: Event IDs to order.

        Returns:
            The event IDs sorted chronologically by start time.
        """
        events = [(eid, self._events[eid]) for eid in event_ids if eid in self._events]
        events.sort(key=lambda x: x[1].interval.start)
        return [eid for eid, _ in events]

    def _build_causal_adjacency(self) -> dict[str, set[str]]:
        adj: dict[str, set[str]] = {eid: set() for eid in self._events}
        for a_id, a in self._events.items():
            for b_id, b in self._events.items():
                if a_id == b_id:
                    continue
                rel = a.interval.relate_to(b.interval)
                if rel in (AllenRelation.BEFORE, AllenRelation.MEETS):
                    adj[a_id].add(b_id)
        return adj

    def _enumerate_chains(
        self, adj: dict[str, set[str]], min_chain_length: int, max_chains: int
    ) -> list[list[str]]:
        all_chains: list[list[str]] = []
        memo: dict[str, list[list[str]]] = {}

        for eid in self._events:
            if len(all_chains) >= max_chains:
                break
            for path in _dfs_causal_paths(eid, adj, memo, all_chains, max_chains):
                if len(all_chains) >= max_chains:
                    break
                if len(path) >= min_chain_length:
                    all_chains.append(path)

        return _deduplicate_chains(all_chains)

    def detect_causal_chains(self, *, min_chain_length: int = 3, max_chains: int = 1000) -> list[list[str]]:
        """Find all BEFORE/MEETS chains among registered events.

        Args:
            min_chain_length: Minimum number of events in a chain.
            max_chains: Stop searching after this many chains are found.

        Returns:
            List of chains, each a list of event IDs in causal order.
        """
        adj = self._build_causal_adjacency()
        return self._enumerate_chains(adj, min_chain_length, max_chains)

    def temporal_proximity(self, event_id: str, max_gap: float = 1.0) -> list[tuple[TemporalEvent, float]]:
        """Find events within a temporal gap of the given event.

        Args:
            event_id: The reference event.
            max_gap: Maximum allowed temporal gap between intervals.

        Returns:
            List of (event, gap) pairs sorted by gap ascending.
        """
        target = self._events.get(event_id)
        if not target:
            return []
        results: list[tuple[TemporalEvent, float]] = []
        for ev in self._events.values():
            if ev.event_id == event_id:
                continue
            gap = max(
                0.0,
                max(target.interval.start, ev.interval.start) - min(target.interval.end, ev.interval.end),
            )
            if gap <= max_gap:
                results.append((ev, gap))
        results.sort(key=lambda x: x[1])
        return results

    def edge_temporal_consistency(self, edge_a_id: str, edge_b_id: str, graph: Any) -> dict[str, Any]:
        """Check temporal consistency between two edges.

        Collects *all* temporal events matching each node label (not just
        the first) so that duplicate labels across nodes are handled
        correctly.  Aggregates the events per edge into a span
        [min(start), max(end)] and then tests the Allen relation between
        the two spans.

        Args:
            edge_a_id: First edge ID.
            edge_b_id: Second edge ID.
            graph: Graph object providing ``get_edge`` and ``get_node``.

        Returns:
            Dict with ``"consistent"`` (bool), ``"relation"``, and interval
            details for both edges.
        """
        edge_a = graph.get_edge(edge_a_id)
        edge_b = graph.get_edge(edge_b_id)
        if not edge_a or not edge_b:
            return {"consistent": True, "reason": "edge_not_found"}

        events_by_label: dict[str, list[Any]] = {}
        for e in self._events.values():
            events_by_label.setdefault(e.label, []).append(e)

        a_nodes = list(edge_a.source_ids | edge_a.target_ids)
        b_nodes = list(edge_b.source_ids | edge_b.target_ids)

        a_events = [ev for nid in a_nodes for ev in events_by_label.get(self._node_label(nid, graph), [])]
        b_events = [ev for nid in b_nodes for ev in events_by_label.get(self._node_label(nid, graph), [])]

        if not a_events or not b_events:
            return {"consistent": True, "reason": "no_temporal_data"}

        a_interval = TimeInterval(
            start=min(e.interval.start for e in a_events),
            end=max(e.interval.end for e in a_events),
        )
        b_interval = TimeInterval(
            start=min(e.interval.start for e in b_events),
            end=max(e.interval.end for e in b_events),
        )

        relation = a_interval.relate_to(b_interval)
        inconsistent = relation in {
            AllenRelation.AFTER,
            AllenRelation.STARTED_BY,
        }

        return {
            "consistent": not inconsistent,
            "relation": relation.value if hasattr(relation, "value") else str(relation),
            "edge_a_interval": {"start": a_interval.start, "end": a_interval.end},
            "edge_b_interval": {"start": b_interval.start, "end": b_interval.end},
        }

    def _node_label(self, node_id: str, graph: Any) -> str:
        """Resolve a node ID to its label, returning empty string if not found."""
        node = graph.get_node(node_id)
        return node.label if node else ""

    def check_constraint_consistency(self) -> list[dict[str, Any]]:
        """Verify that all explicitly added constraints match the actual interval relations.

        Returns:
            List of inconsistency dicts with event labels and actual vs expected relations.
        """
        inconsistencies: list[dict[str, Any]] = []
        events = list(self._events.values())
        if len(events) < 2:
            return inconsistencies

        constraints_by_source: dict[str, list[TemporalConstraint]] = {}
        for c in self._constraints:
            constraints_by_source.setdefault(c.event_a_id, []).append(c)

        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                a, b = events[i], events[j]
                if not a.interval or not b.interval:
                    continue
                relation = a.interval.relate_to(b.interval)
                for constraint in constraints_by_source.get(a.event_id, []):
                    if constraint.event_b_id == b.event_id:
                        allowed = constraint.relation
                        if relation != allowed:
                            inconsistencies.append(
                                {
                                    "event_a": a.label,
                                    "event_b": b.label,
                                    "actual_relation": relation.value if hasattr(relation, "value") else str(relation),
                                    "expected_relation": allowed.value if hasattr(allowed, "value") else str(allowed),
                                }
                            )
        return inconsistencies

    def get_event_for_node(self, node_id: str, graph: Any) -> TemporalEvent | None:
        """Look up the temporal event whose label matches a graph node's label."""
        node = graph.get_node(node_id)
        if not node:
            return None
        events_by_label = {e.label: e for e in self._events.values()}
        return events_by_label.get(node.label)

    @property
    def events(self) -> list[TemporalEvent]:
        """Return all registered events."""
        return list(self._events.values())

    @property
    def constraints(self) -> list[TemporalConstraint]:
        """Return all registered constraints."""
        return list(self._constraints)
