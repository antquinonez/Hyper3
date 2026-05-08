from __future__ import annotations

import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from hyper3.belief import BeliefState, ConceptCorrelation, Outcome
from hyper3.results import _SimpleResultBase


@dataclass
class EntanglementLink(_SimpleResultBase):
    id: str = ""
    distribution_a_id: str = ""
    distribution_b_id: str = ""
    correlation_id: str = ""
    strength: float = 0.0
    created_at: float = 0.0


@dataclass
class EntanglementGroup(_SimpleResultBase):
    id: str = ""
    distribution_ids: frozenset[str] = frozenset()
    link_ids: frozenset[str] = frozenset()
    collapse_count: int = 0


@dataclass
class CorrelatedCollapseResult(_SimpleResultBase):
    collapsed_distributions: dict[str, str] = field(default_factory=dict)
    collapse_order: list[str] = field(default_factory=list)
    entanglement_group_id: str | None = None
    trigger_distribution_id: str = ""
    trigger_outcome_label: str = ""


@dataclass
class EntanglementReport(_SimpleResultBase):
    total_groups: int = 0
    total_links: int = 0
    total_collapses: int = 0
    active_links: list[EntanglementLink] = field(default_factory=list)
    active_groups: list[EntanglementGroup] = field(default_factory=list)


class EntanglementEngine:
    def __init__(self) -> None:
        self._links: dict[str, EntanglementLink] = {}
        self._groups: dict[str, EntanglementGroup] = {}
        self._dist_to_links: dict[str, set[str]] = defaultdict(set)
        self._dist_to_group: dict[str, str] = {}
        self._collapse_count: int = 0

    def register_link(
        self,
        dist_a_id: str,
        dist_b_id: str,
        correlation_id: str,
        strength: float,
    ) -> EntanglementLink:
        if dist_a_id == dist_b_id:
            return EntanglementLink()
        link = EntanglementLink(
            id=uuid.uuid4().hex[:12],
            distribution_a_id=dist_a_id,
            distribution_b_id=dist_b_id,
            correlation_id=correlation_id,
            strength=strength,
            created_at=time.time(),
        )
        self._links[link.id] = link
        self._dist_to_links[dist_a_id].add(link.id)
        self._dist_to_links[dist_b_id].add(link.id)
        self._update_groups_after_link(dist_a_id, dist_b_id, link.id)
        return link

    def find_group(self, distribution_id: str) -> EntanglementGroup | None:
        group_id = self._dist_to_group.get(distribution_id)
        if group_id is None:
            return None
        return self._groups.get(group_id)

    def find_entangled(self, distribution_id: str) -> set[str]:
        group = self.find_group(distribution_id)
        if group is None:
            return set()
        return set(group.distribution_ids) - {distribution_id}

    def compute_correlated_weights(
        self,
        target_qs: BeliefState,
        trigger_outcome_id: str,
        correlations: dict[str, ConceptCorrelation],
        link: EntanglementLink,
    ) -> dict[str, float]:
        corr = correlations.get(link.correlation_id)
        if corr is None:
            return {}
        weights: dict[str, float] = {}
        for outcome in target_qs.outcomes:
            key = (trigger_outcome_id, outcome.node_id)
            rev_key = (outcome.node_id, trigger_outcome_id)
            corr_value = corr.correlation_matrix.get(
                key, corr.correlation_matrix.get(rev_key, 0.0)
            )
            if corr_value >= 0:
                weights[outcome.node_id] = 1.0 + corr_value
            else:
                weights[outcome.node_id] = 1.0 / (1.0 + abs(corr_value))
        return weights

    def perform_correlated_collapse(
        self,
        trigger_dist_id: str,
        states: dict[str, BeliefState],
        correlations: dict[str, ConceptCorrelation],
        sample_fn: Callable[[str, dict[str, float] | None], Outcome | None],
    ) -> CorrelatedCollapseResult | None:
        group = self.find_group(trigger_dist_id)
        if group is None:
            return None

        collapsed: dict[str, str] = {}
        collapse_order: list[str] = []
        remaining = set(group.distribution_ids)

        trigger_outcome = sample_fn(trigger_dist_id, None)
        if trigger_outcome is None:
            return None
        collapsed[trigger_dist_id] = trigger_outcome.label
        collapse_order.append(trigger_dist_id)
        remaining.discard(trigger_dist_id)

        while remaining:
            best_dist: str | None = None
            best_strength = -1.0
            for dist_id in remaining:
                for collapsed_id in collapsed:
                    s = self._get_link_strength(dist_id, collapsed_id)
                    if s > best_strength:
                        best_strength = s
                        best_dist = dist_id
            if best_dist is None:
                break

            target_qs = states.get(best_dist)
            sampled = False
            if target_qs is not None:
                partner_id = self._strongest_partner(best_dist, collapsed)
                if partner_id:
                    link = self._get_link(best_dist, partner_id)
                    if link:
                        partner_outcome_label = collapsed.get(partner_id, "")
                        partner_qs = states.get(partner_id)
                        partner_outcome_id = self._label_to_outcome_id(
                            partner_qs, partner_outcome_label
                        )
                        if partner_outcome_id:
                            weights = self.compute_correlated_weights(
                                target_qs, partner_outcome_id, correlations, link
                            )
                            outcome = sample_fn(best_dist, weights)
                            if outcome is not None:
                                collapsed[best_dist] = outcome.label
                                collapse_order.append(best_dist)
                                sampled = True
            if not sampled:
                outcome = sample_fn(best_dist, None)
                if outcome is not None:
                    collapsed[best_dist] = outcome.label
                    collapse_order.append(best_dist)
                    sampled = True
            if not sampled:
                collapsed[best_dist] = ""
            remaining.discard(best_dist)

        self._collapse_count += 1

        return CorrelatedCollapseResult(
            collapsed_distributions=collapsed,
            collapse_order=collapse_order,
            entanglement_group_id=group.id,
            trigger_distribution_id=trigger_dist_id,
            trigger_outcome_label=trigger_outcome.label,
        )

    def remove_link(self, link_id: str) -> None:
        link = self._links.pop(link_id, None)
        if link is None:
            return
        self._dist_to_links[link.distribution_a_id].discard(link_id)
        self._dist_to_links[link.distribution_b_id].discard(link_id)
        if not self._dist_to_links[link.distribution_a_id]:
            del self._dist_to_links[link.distribution_a_id]
        if not self._dist_to_links[link.distribution_b_id]:
            del self._dist_to_links[link.distribution_b_id]
        self._rebuild_groups()

    def clear(self) -> None:
        self._links.clear()
        self._groups.clear()
        self._dist_to_links.clear()
        self._dist_to_group.clear()
        self._collapse_count = 0

    def report(self) -> EntanglementReport:
        return EntanglementReport(
            total_groups=len(self._groups),
            total_links=len(self._links),
            total_collapses=self._collapse_count,
            active_links=list(self._links.values()),
            active_groups=list(self._groups.values()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "links": [
                {
                    "id": l.id,
                    "distribution_a_id": l.distribution_a_id,
                    "distribution_b_id": l.distribution_b_id,
                    "correlation_id": l.correlation_id,
                    "strength": l.strength,
                    "created_at": l.created_at,
                }
                for l in self._links.values()
            ],
            "collapse_count": self._collapse_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntanglementEngine:
        engine = cls()
        for ld in data.get("links", []):
            link = EntanglementLink(
                id=ld["id"],
                distribution_a_id=ld["distribution_a_id"],
                distribution_b_id=ld["distribution_b_id"],
                correlation_id=ld["correlation_id"],
                strength=ld["strength"],
                created_at=ld.get("created_at", 0.0),
            )
            engine._links[link.id] = link
            engine._dist_to_links[link.distribution_a_id].add(link.id)
            engine._dist_to_links[link.distribution_b_id].add(link.id)
        for link in engine._links.values():
            engine._update_groups_after_link(
                link.distribution_a_id, link.distribution_b_id, link.id
            )
        engine._collapse_count = data.get("collapse_count", 0)
        return engine

    def _update_groups_after_link(
        self, dist_a_id: str, dist_b_id: str, link_id: str
    ) -> None:
        group_a_id = self._dist_to_group.get(dist_a_id)
        group_b_id = self._dist_to_group.get(dist_b_id)

        if group_a_id is not None and group_b_id is not None:
            if group_a_id == group_b_id:
                return
            group_a = self._groups[group_a_id]
            group_b = self._groups[group_b_id]
            merged = EntanglementGroup(
                id=group_a.id,
                distribution_ids=group_a.distribution_ids | group_b.distribution_ids,
                link_ids=group_a.link_ids | group_b.link_ids | frozenset({link_id}),
                collapse_count=group_a.collapse_count + group_b.collapse_count,
            )
            del self._groups[group_a_id]
            del self._groups[group_b_id]
            self._groups[merged.id] = merged
            for did in merged.distribution_ids:
                self._dist_to_group[did] = merged.id
        elif group_a_id is not None:
            group_a = self._groups[group_a_id]
            updated = EntanglementGroup(
                id=group_a.id,
                distribution_ids=group_a.distribution_ids | frozenset({dist_b_id}),
                link_ids=group_a.link_ids | frozenset({link_id}),
                collapse_count=group_a.collapse_count,
            )
            self._groups[group_a_id] = updated
            self._dist_to_group[dist_b_id] = group_a_id
        elif group_b_id is not None:
            group_b = self._groups[group_b_id]
            updated = EntanglementGroup(
                id=group_b.id,
                distribution_ids=group_b.distribution_ids | frozenset({dist_a_id}),
                link_ids=group_b.link_ids | frozenset({link_id}),
                collapse_count=group_b.collapse_count,
            )
            self._groups[group_b_id] = updated
            self._dist_to_group[dist_a_id] = group_b_id
        else:
            new_group = EntanglementGroup(
                id=uuid.uuid4().hex[:12],
                distribution_ids=frozenset({dist_a_id, dist_b_id}),
                link_ids=frozenset({link_id}),
            )
            self._groups[new_group.id] = new_group
            self._dist_to_group[dist_a_id] = new_group.id
            self._dist_to_group[dist_b_id] = new_group.id

    def _rebuild_groups(self) -> None:
        self._groups.clear()
        self._dist_to_group.clear()
        for link in self._links.values():
            self._update_groups_after_link(
                link.distribution_a_id, link.distribution_b_id, link.id
            )

    def _get_link_strength(self, dist_a_id: str, dist_b_id: str) -> float:
        for link_id in self._dist_to_links.get(dist_a_id, set()):
            link = self._links.get(link_id)
            if link and (
                link.distribution_a_id == dist_b_id or link.distribution_b_id == dist_b_id
            ):
                return link.strength
        return 0.0

    def _get_link(self, dist_a_id: str, dist_b_id: str) -> EntanglementLink | None:
        for link_id in self._dist_to_links.get(dist_a_id, set()):
            link = self._links.get(link_id)
            if link and (
                link.distribution_a_id == dist_b_id or link.distribution_b_id == dist_b_id
            ):
                return link
        return None

    def _strongest_partner(
        self, dist_id: str, collapsed: dict[str, str]
    ) -> str | None:
        best_partner: str | None = None
        best_strength = -1.0
        for collapsed_id in collapsed:
            s = self._get_link_strength(dist_id, collapsed_id)
            if s > best_strength:
                best_strength = s
                best_partner = collapsed_id
        return best_partner

    def _label_to_outcome_id(
        self, qs: BeliefState | None, label: str
    ) -> str | None:
        if qs is None:
            return None
        for outcome in qs.outcomes:
            if outcome.label == label or outcome.node_id == label:
                return outcome.node_id
        return None
