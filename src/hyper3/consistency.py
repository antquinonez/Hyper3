"""ConsistencyVerifier: graph integrity validation and repair."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from hyper3.results import _SimpleResultBase

if TYPE_CHECKING:
    from hyper3.kernel import Hypergraph


@dataclass
class Violation(_SimpleResultBase):
    """A single invariant violation: which invariant failed, which entity is affected, severity, and repairability."""

    invariant: str = ""
    node_id: str | None = None
    edge_id: str | None = None
    description: str = ""
    severity: str = "warning"
    repairable: bool = False
    repaired: bool = False


@dataclass
class VerificationResult(_SimpleResultBase):
    """Aggregated result of a consistency verification pass: counts of invariants checked, passed, violations found, and repairs applied."""

    invariant_count: int = 0
    passed: int = 0
    violations: list[Violation] = field(default_factory=list)
    repaired_count: int = 0
    elapsed_ms: float = 0.0


@dataclass
class InvariantConfig(_SimpleResultBase):
    """Configuration for which invariants to check and whether to auto-repair violations."""

    check_positive_weights: bool = True
    check_no_orphans: bool = True
    check_no_self_loops: bool = True
    check_label_index: bool = True
    check_edge_integrity: bool = True
    check_no_duplicate_edges: bool = True
    check_cache_consistency: bool = False
    repair: bool = False


_INVARIANT_NAMES = [
    "check_positive_weights",
    "check_no_orphans",
    "check_no_self_loops",
    "check_label_index",
    "check_edge_integrity",
    "check_no_duplicate_edges",
    "check_cache_consistency",
]


class ConsistencyVerifier:
    """Verifies graph structural invariants and optionally repairs violations.

    Checks a configurable set of invariants (positive weights, no orphans,
    no self-loops, label index integrity, edge integrity, no duplicate edges,
    cache consistency) and reports violations. When ``config.repair`` is
    ``True``, repairable violations are fixed automatically.

    Args:
        graph: The hypergraph to verify.
        config: Invariant configuration. When ``None``, uses defaults
            (all checks enabled except cache consistency, no auto-repair).
    """

    def __init__(self, graph: Hypergraph, *, config: InvariantConfig | None = None) -> None:
        """Initialize with a graph and optional invariant configuration.

        Args:
            graph: The hypergraph to verify.
            config: Invariant configuration. When ``None``, uses defaults
                (all checks enabled except cache consistency, no auto-repair).
        """
        self._graph = graph
        self._config = config or InvariantConfig()

    @property
    def config(self) -> InvariantConfig:
        """The current invariant configuration."""
        return self._config

    @config.setter
    def config(self, value: InvariantConfig) -> None:
        """Replace the invariant configuration."""
        self._config = value

    def _get_enabled_invariants(self) -> list[str]:
        """Return the names of all enabled invariant checks."""
        return [name for name in _INVARIANT_NAMES if getattr(self._config, name, False)]

    def verify(self) -> VerificationResult:
        """Run all enabled invariant checks and return aggregated results.

        When ``config.repair`` is ``True``, repairable violations are
        automatically fixed after all checks complete.

        Returns:
            VerificationResult with violation list, pass/repair counts, and elapsed time.
        """
        start = time.perf_counter()
        enabled = self._get_enabled_invariants()
        all_violations: list[Violation] = []
        for invariant_name in enabled:
            violations = self.verify_invariant(invariant_name)
            all_violations.extend(violations)

        repaired = 0
        if self._config.repair:
            repairable = [v for v in all_violations if v.repairable]
            repaired = self.repair(repairable)

        failed_invariants = {v.invariant for v in all_violations}
        passed = len(enabled) - len(failed_invariants)
        elapsed = (time.perf_counter() - start) * 1000.0

        return VerificationResult(
            invariant_count=len(enabled),
            passed=passed,
            violations=all_violations,
            repaired_count=repaired,
            elapsed_ms=elapsed,
        )

    def verify_invariant(self, name: str) -> list[Violation]:
        """Run a single named invariant check.

        Args:
            name: One of the invariant names (e.g. ``"check_positive_weights"``).

        Returns:
            List of Violation objects for this invariant. Empty if no violations.

        Raises:
            ValueError: If the invariant name is not recognized.
        """
        dispatch = {
            "check_positive_weights": self._check_positive_weights,
            "check_no_orphans": self._check_no_orphans,
            "check_no_self_loops": self._check_no_self_loops,
            "check_label_index": self._check_label_index,
            "check_edge_integrity": self._check_edge_integrity,
            "check_no_duplicate_edges": self._check_no_duplicate_edges,
            "check_cache_consistency": self._check_cache_consistency,
        }
        checker = dispatch.get(name)
        if checker is None:
            raise ValueError(f"Unknown invariant: {name}")
        return checker()

    def repair(self, violations: list[Violation]) -> int:
        """Attempt to repair the given violations in-place.

        Only violations with ``repairable=True`` are processed. Each
        successful repair sets ``violation.repaired = True``.

        Args:
            violations: Violations to repair.

        Returns:
            The number of successfully repaired violations.
        """
        repaired = 0
        grouped: dict[str, list[Violation]] = {}
        for v in violations:
            if not v.repairable:
                continue
            grouped.setdefault(v.invariant, []).append(v)

        for invariant_name, group in grouped.items():
            repaired += self._repair_group(invariant_name, group)
        return repaired

    def _repair_group(self, invariant_name: str, violations: list[Violation]) -> int:
        """Apply repairs for a specific invariant type."""
        if invariant_name == "check_positive_weights":
            return self._repair_positive_weights(violations)
        if invariant_name == "check_no_self_loops":
            return self._repair_self_loops(violations)
        if invariant_name == "check_label_index":
            return self._repair_label_index(violations)
        if invariant_name == "check_edge_integrity":
            return self._repair_edge_integrity(violations)
        if invariant_name == "check_no_duplicate_edges":
            return self._repair_duplicate_edges(violations)
        if invariant_name == "check_cache_consistency":
            return self._repair_cache_consistency(violations)
        return 0

    def _check_positive_weights(self) -> list[Violation]:
        """Detect edges with weight <= 0."""
        return [
            Violation(
                invariant="check_positive_weights",
                edge_id=edge.id,
                description=f"Edge {edge.id} has weight {edge.weight}",
                severity="error",
                repairable=True,
            )
            for edge in self._graph.edges
            if edge.weight <= 0
        ]

    def _check_no_orphans(self) -> list[Violation]:
        """Detect nodes with zero incident edges."""
        return [
            Violation(
                invariant="check_no_orphans",
                node_id=node.id,
                description=f"Node {node.id} ({node.label or 'unlabeled'}) has no incident edges",
                severity="warning",
                repairable=False,
            )
            for node in self._graph.nodes
            if len(self._graph.incident_edges(node.id)) == 0
        ]

    def _check_no_self_loops(self) -> list[Violation]:
        """Detect edges where source_ids and target_ids overlap."""
        violations: list[Violation] = []
        for edge in self._graph.edges:
            overlap = edge.source_ids & edge.target_ids
            if overlap:
                violations.append(
                    Violation(
                        invariant="check_no_self_loops",
                        edge_id=edge.id,
                        description=f"Edge {edge.id} has self-loop nodes: {overlap}",
                        severity="warning",
                        repairable=True,
                    )
                )
        return violations

    def _check_label_index(self) -> list[Violation]:
        """Detect stale or missing entries in the label index."""
        violations: list[Violation] = []
        index = self._graph._label_index

        for label, nid in list(index.items()):
            node = self._graph.get_node(nid)
            if node is None:
                violations.append(
                    Violation(
                        invariant="check_label_index",
                        description=f"Label '{label}' maps to nonexistent node {nid}",
                        severity="error",
                        repairable=True,
                    )
                )
            elif node.label != label:
                violations.append(
                    Violation(
                        invariant="check_label_index",
                        node_id=nid,
                        description=f"Node {nid} label is '{node.label}' but index has '{label}'",
                        severity="error",
                        repairable=True,
                    )
                )

        violations.extend(
            Violation(
                invariant="check_label_index",
                node_id=node.id,
                description=f"Node {node.id} label '{node.label}' missing from index",
                severity="error",
                repairable=True,
            )
            for node in self._graph.nodes
            if node.label and node.label not in index
        )

        return violations

    def _check_edge_integrity(self) -> list[Violation]:
        """Detect edges referencing nonexistent nodes."""
        violations: list[Violation] = []
        for edge in self._graph.edges:
            for nid in edge.source_ids | edge.target_ids:
                if self._graph.get_node(nid) is None:
                    violations.append(
                        Violation(
                            invariant="check_edge_integrity",
                            edge_id=edge.id,
                            description=f"Edge {edge.id} references nonexistent node {nid}",
                            severity="error",
                            repairable=True,
                        )
                    )
                    break
        return violations

    def _check_no_duplicate_edges(self) -> list[Violation]:
        """Detect edges with identical source_ids, target_ids, and label."""
        violations: list[Violation] = []
        seen: dict[tuple[frozenset[str], frozenset[str], str], list[tuple[str, float]]] = {}
        for edge in self._graph.edges:
            key = (edge.source_ids, edge.target_ids, edge.label)
            seen.setdefault(key, []).append((edge.id, edge.weight))

        for key, entries in seen.items():
            if len(entries) > 1:
                for eid, w in entries:
                    violations.append(
                        Violation(
                            invariant="check_no_duplicate_edges",
                            edge_id=eid,
                            description=f"Duplicate edge {eid} (weight={w}) with key ({key[0]}, {key[1]}, '{key[2]}')",
                            severity="warning",
                            repairable=True,
                        )
                    )
        return violations

    def _check_cache_consistency(self) -> list[Violation]:
        """Detect stale neighbor cache entries."""
        cache = self._graph._neighbor_cache
        if cache is None:
            return []

        violations: list[Violation] = []
        actual_neighbors: dict[str, set[str]] = {}
        for node in self._graph.nodes:
            actual_neighbors[node.id] = set(self._graph.neighbors(node.id))

        cached_ids = set(cache.keys())
        actual_ids = set(actual_neighbors.keys())

        violations = [
            Violation(
                invariant="check_cache_consistency",
                node_id=nid,
                description=f"Cache contains stale entry for nonexistent node {nid}",
                severity="info",
                repairable=True,
            )
            for nid in cached_ids - actual_ids
        ]

        violations.extend(
            Violation(
                invariant="check_cache_consistency",
                node_id=nid,
                description=f"Cache missing entry for node {nid} with neighbors",
                severity="info",
                repairable=True,
            )
            for nid in actual_ids - cached_ids
            if actual_neighbors[nid]
        )

        for nid in cached_ids & actual_ids:
            cached_set = set(cache[nid])
            if cached_set != actual_neighbors[nid]:
                violations.append(
                    Violation(
                        invariant="check_cache_consistency",
                        node_id=nid,
                        description=f"Cache mismatch for node {nid}",
                        severity="info",
                        repairable=True,
                    )
                )

        return violations

    def _repair_positive_weights(self, violations: list[Violation]) -> int:
        """Set weight to 1.0 for each violated edge."""
        repaired = 0
        for v in violations:
            edge = self._graph.get_edge(v.edge_id) if v.edge_id else None
            if edge:
                edge.weight = 1.0
                v.repaired = True
                repaired += 1
        return repaired

    def _repair_self_loops(self, violations: list[Violation]) -> int:
        """Remove self-loop edges."""
        repaired = 0
        for v in violations:
            if v.edge_id and self._graph.remove_edge(v.edge_id):
                v.repaired = True
                repaired += 1
        return repaired

    def _repair_label_index(self, violations: list[Violation]) -> int:
        """Rebuild the label index from scratch."""
        index = self._graph._label_index
        index.clear()
        for node in self._graph.nodes:
            if node.label:
                index[node.label] = node.id
        for v in violations:
            v.repaired = True
        return len(violations)

    def _repair_edge_integrity(self, violations: list[Violation]) -> int:
        """Remove edges that reference nonexistent nodes."""
        repaired = 0
        seen: set[str] = set()
        for v in violations:
            if v.edge_id and v.edge_id not in seen:
                seen.add(v.edge_id)
                if self._graph.remove_edge(v.edge_id):
                    v.repaired = True
                    repaired += 1
        return repaired

    def _repair_duplicate_edges(self, violations: list[Violation]) -> int:
        """Keep the highest-weight edge among duplicates, remove the rest."""
        groups: dict[tuple[frozenset[str], frozenset[str], str], list[Violation]] = {}
        for v in violations:
            edge = self._graph.get_edge(v.edge_id) if v.edge_id else None
            if edge is None:
                continue
            key = (edge.source_ids, edge.target_ids, edge.label)
            groups.setdefault(key, []).append(v)

        repaired = 0
        for group in groups.values():
            if len(group) <= 1:
                continue
            def _weight(v: Violation) -> float:
                """Return the edge weight for a violation, used as the sort key."""
                e = self._graph.get_edge(v.edge_id) if v.edge_id else None
                return e.weight if e is not None else 0.0

            group.sort(key=_weight, reverse=True)
            for v in group[1:]:
                if v.edge_id and self._graph.remove_edge(v.edge_id):
                    v.repaired = True
                    repaired += 1
        return repaired

    def _repair_cache_consistency(self, violations: list[Violation]) -> int:
        """Invalidate the neighbor cache."""
        self._graph._neighbor_cache = None
        for v in violations:
            v.repaired = True
        return len(violations)
