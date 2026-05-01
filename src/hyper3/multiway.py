from __future__ import annotations

import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.rules import Rule, RuleMatch


@dataclass
class MultiwayState:
    """A single node in the multiway expansion DAG representing one computational state."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: str | None = None
    active_node_ids: frozenset[str] = frozenset()
    rule_applied: str | None = None
    match_bindings: dict[str, str] = field(default_factory=dict)
    depth: int = 0
    produced_node_ids: list[str] = field(default_factory=list)
    produced_edge_ids: list[str] = field(default_factory=list)
    children_ids: list[str] = field(default_factory=list)
    timestamp: float = 0.0

    @property
    def is_root(self) -> bool:
        """Return True if this state has no parent."""
        return self.parent_id is None

    @property
    def is_leaf(self) -> bool:
        """Return True if this state has no children."""
        return len(self.children_ids) == 0


@dataclass
class BranchialRelation:
    """Recorded relationship between two sibling states in the multiway graph."""

    state_a_id: str
    state_b_id: str
    distance: float
    common_ancestor_id: str


class MultiwayGraph:
    """DAG of computational states produced by multiway rule expansion."""

    def __init__(self) -> None:
        """Initialize an empty multiway graph."""
        self._states: dict[str, MultiwayState] = {}
        self._branchial_relations: list[BranchialRelation] = []
        self._root: MultiwayState | None = None
        self._leaves_cache: list[MultiwayState] | None = None

    def add_state(self, state: MultiwayState) -> MultiwayState:
        """Register a state and link it to its parent if one exists.

        Args:
            state: The multiway state to add.

        Returns:
            The added state.
        """
        self._states[state.id] = state
        if state.parent_id is not None and state.parent_id in self._states:
            parent = self._states[state.parent_id]
            if state.id not in parent.children_ids:
                parent.children_ids.append(state.id)
                self._leaves_cache = None
        else:
            self._root = state
        if state.parent_id is not None:
            self._update_branchial(state)
        return state

    def get_state(self, state_id: str) -> MultiwayState | None:
        """Look up a state by its ID."""
        return self._states.get(state_id)

    def get_children(self, state_id: str) -> list[MultiwayState]:
        """Return the immediate children of a state."""
        state = self._states.get(state_id)
        if not state:
            return []
        return [self._states[cid] for cid in state.children_ids if cid in self._states]

    def get_siblings(self, state_id: str) -> list[MultiwayState]:
        """Return all children of the same parent, excluding the given state."""
        state = self._states.get(state_id)
        if not state or not state.parent_id:
            return []
        parent = self._states.get(state.parent_id)
        if not parent:
            return []
        return [self._states[cid] for cid in parent.children_ids if cid in self._states and cid != state_id]

    def get_ancestors(self, state_id: str) -> list[MultiwayState]:
        """Walk from the given state to the root, collecting all ancestors."""
        chain: list[MultiwayState] = []
        current = self._states.get(state_id)
        while current and current.parent_id:
            parent = self._states.get(current.parent_id)
            if parent:
                chain.append(parent)
            current = parent
        return chain

    def get_root(self) -> MultiwayState | None:
        """Return the root state of the multiway graph."""
        return self._root

    def get_leaves(self) -> list[MultiwayState]:
        """Return all leaf states (states with no children), using a lazy cache."""
        if self._leaves_cache is None:
            self._leaves_cache = [s for s in self._states.values() if s.is_leaf]
        return self._leaves_cache

    def get_simultaneous_states(self, state_id: str) -> list[MultiwayState]:
        """Return sibling states that share the same parent."""
        siblings = self.get_siblings(state_id)
        return siblings

    def find_common_ancestor(self, state_a_id: str, state_b_id: str) -> str | None:
        """Find the nearest common ancestor of two states.

        Args:
            state_a_id: ID of the first state.
            state_b_id: ID of the second state.

        Returns:
            The common ancestor state ID, or None if none exists.
        """
        ancestors_a = {s.id for s in self.get_ancestors(state_a_id)}
        ancestors_a.add(state_a_id)
        current = self._states.get(state_b_id)
        while current:
            if current.id in ancestors_a:
                return current.id
            current = self._states.get(current.parent_id) if current.parent_id else None
        return None

    def branchial_distance(self, state_a_id: str, state_b_id: str) -> float:
        """Compute the branchial distance between two states via their common ancestor."""
        if state_a_id == state_b_id:
            return 0.0
        ancestor_id = self.find_common_ancestor(state_a_id, state_b_id)
        if ancestor_id is None:
            return float("inf")
        dist_a = self._depth_from(ancestor_id, state_a_id)
        dist_b = self._depth_from(ancestor_id, state_b_id)
        return dist_a + dist_b

    def get_branchial_relations(self) -> list[BranchialRelation]:
        """Return all recorded branchial relations between sibling states."""
        return list(self._branchial_relations)

    @property
    def state_count(self) -> int:
        """Return the total number of states in the graph."""
        return len(self._states)

    @property
    def states(self) -> list[MultiwayState]:
        """Return all states as a list."""
        return list(self._states.values())

    def _depth_from(self, ancestor_id: str, descendant_id: str) -> int:
        """Count the number of edges from a descendant up to an ancestor."""
        depth = 0
        current = self._states.get(descendant_id)
        while current and current.id != ancestor_id:
            depth += 1
            current = self._states.get(current.parent_id) if current.parent_id else None
        return depth if current else float("inf")  # type: ignore[return-value]

    def _update_branchial(self, new_state: MultiwayState) -> None:
        """Create branchial relations between a new state and its siblings."""
        siblings = self.get_siblings(new_state.id)
        for sibling in siblings:
            distance = self.branchial_distance(new_state.id, sibling.id)
            self._branchial_relations.append(
                BranchialRelation(
                    state_a_id=new_state.id,
                    state_b_id=sibling.id,
                    distance=distance,
                    common_ancestor_id=new_state.parent_id or "",
                )
            )


@dataclass
class ExpansionReport:
    """Summary statistics from a multiway expansion pass."""

    states_created: int = 0
    rules_applied: int = 0
    nodes_produced: int = 0
    edges_produced: int = 0
    branches: int = 0
    max_depth_reached: int = 0
    confidence_map: dict[str, float] = field(default_factory=dict)


class MultiwayEngine:
    """Drives multiway expansion by applying inference rules to a hypergraph in breadth-first layers."""

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize the engine with a base hypergraph.

        Args:
            graph: The hypergraph on which multiway expansion operates.
        """
        self._graph = graph
        self._multiway = MultiwayGraph()
        self._rulial: Any | None = None

    def set_rulial(self, rulial: Any) -> None:
        """Attach a RulialSpace for rule-effectiveness-aware ordering."""
        self._rulial = rulial

    def _sort_rules_by_effectiveness(self, rules: list[Rule]) -> list[Rule]:
        """Sort rules by descending rulial priority when available."""
        if not self._rulial:
            return rules
        rulial = self._rulial
        return sorted(rules, key=lambda r: rulial.get_rule_priority(r.name), reverse=True)

    @property
    def multiway(self) -> MultiwayGraph:
        """Return the underlying multiway state graph."""
        return self._multiway

    @property
    def graph(self) -> Hypergraph:
        """Return the base hypergraph."""
        return self._graph

    def expand(
        self,
        seed_node_ids: set[str],
        rules: list[Rule],
        *,
        max_depth: int = 3,
        max_branches_per_state: int = 10,
        max_total_states: int = 100,
        overlay: Any | None = None,
        confidence_decay: float = 0.9,
    ) -> ExpansionReport:
        """Expand the multiway graph breadth-first from seed nodes.

        Args:
            seed_node_ids: Starting node IDs for expansion.
            rules: Rules to apply at each state.
            max_depth: Maximum expansion depth.
            max_branches_per_state: Maximum child branches per state.
            max_total_states: Hard cap on total states created.
            overlay: Optional overlay graph for inference edges.
            confidence_decay: Multiplicative decay per depth level.

        Returns:
            An ExpansionReport summarizing the expansion.
        """
        report = ExpansionReport()
        root = MultiwayState(
            active_node_ids=frozenset(seed_node_ids),
            depth=0,
            timestamp=time.time(),
        )
        self._multiway.add_state(root)
        report.states_created = 1

        frontier: list[str] = [root.id]

        for _ in range(max_depth):
            next_frontier: list[str] = []
            for state_id in frontier:
                if report.states_created >= max_total_states:
                    break
                state = self._multiway.get_state(state_id)
                if not state:
                    continue
                new_states = self._expand_state(
                    state,
                    rules,
                    max_branches_per_state,
                    report,
                    overlay=overlay,
                    confidence_decay=confidence_decay,
                )
                next_frontier.extend(new_states)
                report.states_created += len(new_states)
            frontier = next_frontier
            if not frontier:
                break
            report.max_depth_reached += 1

        report.branches = sum(1 for s in self._multiway.states if s.is_leaf)
        return report

    def expand_lazy(
        self,
        seed_node_ids: set[str],
        rules: list[Rule],
        *,
        max_depth: int = 3,
        max_branches_per_state: int = 10,
        max_total_states: int = 100,
        overlay: Any | None = None,
        confidence_decay: float = 0.9,
    ) -> Generator[tuple[str, int, int], None, None]:
        """Expand lazily, yielding (state_id, depth, sibling_count) tuples.

        Yields states ordered by confidence priority rather than strict BFS.
        Useful for interactive or streaming consumers.

        Args:
            seed_node_ids: Starting node IDs for expansion.
            rules: Rules to apply at each state.
            max_depth: Maximum expansion depth.
            max_branches_per_state: Maximum child branches per state.
            max_total_states: Hard cap on total states created.
            overlay: Optional overlay graph for inference edges.
            confidence_decay: Multiplicative decay per depth level.

        Yields:
            Tuples of (new_state_id, depth, sibling_count).
        """
        root = MultiwayState(
            active_node_ids=frozenset(seed_node_ids),
            depth=0,
            timestamp=time.time(),
        )
        self._multiway.add_state(root)
        yield (root.id, 0, 0)

        frontier: list[tuple[float, str]] = [(1.0, root.id)]
        total_created = 1

        for depth in range(max_depth):
            if total_created >= max_total_states:
                break
            next_frontier: list[tuple[float, str]] = []
            for _, state_id in frontier:
                if total_created >= max_total_states:
                    break
                state = self._multiway.get_state(state_id)
                if not state:
                    continue
                remaining = max_total_states - total_created
                capped_branches = min(max_branches_per_state, remaining)
                new_states = self._expand_state(
                    state,
                    rules,
                    capped_branches,
                    ExpansionReport(),
                    overlay=overlay,
                    confidence_decay=confidence_decay,
                )
                for new_id in new_states:
                    total_created += 1
                    new_state = self._multiway.get_state(new_id)
                    priority = 1.0
                    if new_state:
                        produced_edges = [self._graph.get_edge(eid) for eid in new_state.produced_edge_ids]
                        produced_edges = [e for e in produced_edges if e is not None]
                        if produced_edges:
                            conf = produced_edges[0].metadata.custom.get("confidence", 1.0)
                            priority = conf
                    next_frontier.append((priority, new_id))
                    yield (new_id, depth + 1, len(new_states))
            next_frontier.sort(key=lambda x: x[0], reverse=True)
            frontier = next_frontier
            if not frontier:
                break

    def expand_from_labels(
        self,
        labels: set[str],
        rules: list[Rule],
        **kwargs: Any,
    ) -> ExpansionReport:
        """Expand using node labels instead of IDs.

        Args:
            labels: Labels of seed nodes.
            rules: Rules to apply.
            **kwargs: Forwarded to expand().

        Returns:
            An ExpansionReport summarizing the expansion.
        """
        node_ids: set[str] = set()
        for node in self._graph.nodes:
            if node.label in labels:
                node_ids.add(node.id)
        return self.expand(node_ids, rules, **kwargs)

    def expand_incremental(
        self,
        new_node_ids: set[str],
        new_edge_ids: set[str],
        rules: list[Rule],
        *,
        max_depth: int = 2,
        max_branches_per_state: int = 10,
        max_total_states: int = 50,
    ) -> ExpansionReport:
        """Continue expansion from leaves affected by new nodes or edges.

        Args:
            new_node_ids: Recently added node IDs.
            new_edge_ids: Recently added edge IDs.
            rules: Rules to apply.
            max_depth: Maximum additional expansion depth.
            max_branches_per_state: Branching cap per state.
            max_total_states: Hard cap on total new states.

        Returns:
            An ExpansionReport for the incremental expansion.
        """
        report = ExpansionReport()
        affected_leaves: list[str] = [
            leaf.id
            for leaf in self._multiway.get_leaves()
            if new_node_ids & leaf.active_node_ids or new_edge_ids & set(leaf.produced_edge_ids)
        ]
        if not affected_leaves:
            for leaf in self._multiway.get_leaves():
                affected_leaves.append(leaf.id)
                if len(affected_leaves) >= 5:
                    break
        frontier: list[str] = affected_leaves
        for _ in range(max_depth):
            next_frontier: list[str] = []
            for state_id in frontier:
                if report.states_created >= max_total_states:
                    break
                state = self._multiway.get_state(state_id)
                if not state:
                    continue
                new_states = self._expand_state(state, rules, max_branches_per_state, report)
                next_frontier.extend(new_states)
                report.states_created += len(new_states)
            frontier = next_frontier
            if not frontier:
                break
            report.max_depth_reached += 1
        report.branches = sum(1 for s in self._multiway.states if s.is_leaf)
        return report

    def find_convergent_states(self) -> list[tuple[str, str, float]]:
        """Find leaf state pairs with overlapping active nodes (Jaccard > 0.5).

        Returns:
            List of (state_a_id, state_b_id, similarity_score) tuples.
        """
        leaves = self._multiway.get_leaves()
        convergences: list[tuple[str, str, float]] = []
        for i in range(len(leaves)):
            for j in range(i + 1, len(leaves)):
                a, b = leaves[i], leaves[j]
                if a.active_node_ids == b.active_node_ids:
                    convergences.append((a.id, b.id, 1.0))
                    continue
                overlap = len(a.active_node_ids & b.active_node_ids)
                total = len(a.active_node_ids | b.active_node_ids)
                if total > 0 and overlap / total > 0.5:
                    convergences.append((a.id, b.id, overlap / total))
        return convergences

    def get_lateral_insights(self, state_id: str) -> list[dict[str, Any]]:
        """Compare a state to its siblings to find novel produced nodes.

        Args:
            state_id: The state to compare against its simultaneous siblings.

        Returns:
            List of insight dicts with novel node and branchial distance info.
        """
        simultaneous = self._multiway.get_simultaneous_states(state_id)
        insights: list[dict[str, Any]] = []
        current = self._multiway.get_state(state_id)
        if not current:
            return insights
        for sibling in simultaneous:
            new_in_current = set(current.produced_node_ids) - set(sibling.produced_node_ids)
            new_in_sibling = set(sibling.produced_node_ids) - set(current.produced_node_ids)
            if new_in_current or new_in_sibling:
                insights.append(
                    {
                        "source_state": state_id,
                        "lateral_state": sibling.id,
                        "rule_used": sibling.rule_applied,
                        "novel_in_source": list(new_in_current),
                        "novel_in_lateral": list(new_in_sibling),
                        "branchial_distance": self._multiway.branchial_distance(state_id, sibling.id),
                    }
                )
        return insights

    def _apply_single_match(
        self,
        state: MultiwayState,
        rule: Rule,
        match: RuleMatch,
        target_graph: Any,
        report: ExpansionReport,
        overlay: Any | None = None,
        confidence_decay: float = 0.9,
    ) -> str:
        new_nodes, new_edges = rule.apply(target_graph, match)
        new_active = state.active_node_ids | frozenset(new_nodes)
        child = MultiwayState(
            parent_id=state.id,
            active_node_ids=new_active,
            rule_applied=rule.name,
            match_bindings=match.bindings,
            depth=state.depth + 1,
            produced_node_ids=new_nodes,
            produced_edge_ids=new_edges,
            timestamp=time.time(),
        )
        self._multiway.add_state(child)
        report.rules_applied += 1
        report.nodes_produced += len(new_nodes)
        report.edges_produced += len(new_edges)
        if overlay is not None and hasattr(overlay, "set_confidence"):
            parent_conf = 1.0
            for eid in state.produced_edge_ids:
                if hasattr(overlay, "get_confidence"):
                    parent_conf = min(parent_conf, overlay.get_confidence(eid))
            for eid in new_edges:
                overlay.set_confidence(eid, parent_conf * confidence_decay)
            report.confidence_map.update({eid: overlay.get_confidence(eid) for eid in new_edges})
        return child.id

    def _expand_state(
        self,
        state: MultiwayState,
        rules: list[Rule],
        max_branches: int,
        report: ExpansionReport,
        overlay: Any | None = None,
        confidence_decay: float = 0.9,
    ) -> list[str]:
        """Apply all matching rules to a state and create child states.

        Args:
            state: The multiway state to expand.
            rules: Candidate rules.
            max_branches: Maximum number of matches to apply.
            report: Report to accumulate statistics into.
            overlay: Optional overlay for confidence tracking.
            confidence_decay: Multiplicative confidence decay factor.

        Returns:
            List of newly created child state IDs.
        """
        target_graph = overlay if overlay is not None else self._graph
        sorted_rules = self._sort_rules_by_effectiveness(rules)
        all_matches: list[tuple[Rule, RuleMatch]] = []
        for rule in sorted_rules:
            matches = rule.find_matches(target_graph, state.active_node_ids)
            for match in matches:
                all_matches.append((rule, match))
                if len(all_matches) >= max_branches:
                    break
            if len(all_matches) >= max_branches:
                break

        if not all_matches:
            return []

        new_state_ids: list[str] = []
        for rule, match in all_matches:
            child_id = self._apply_single_match(
                state, rule, match, target_graph, report, overlay, confidence_decay
            )
            new_state_ids.append(child_id)
        return new_state_ids
