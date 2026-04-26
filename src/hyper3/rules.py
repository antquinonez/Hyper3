from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, Modality


@dataclass
class RuleMatch:
    rule_name: str
    bindings: dict[str, str]
    context: dict[str, Any] = field(default_factory=dict)


class Rule(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        ...

    @abstractmethod
    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        ...


class TransitiveRule(Rule):
    def __init__(self, *, edge_label: str | None = None, new_label: str = "") -> None:
        self._edge_label = edge_label
        self._new_label = new_label

    @property
    def name(self) -> str:
        return f"transitive({self._edge_label or '*'})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        edge_set: set[tuple[str, str]] = set()
        for edge in graph.edges:
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    edge_set.add((src, tgt))
        for nid_a in active_nodes:
            for e1 in graph.edges_for(nid_a):
                if self._edge_label and e1.label and e1.label != self._edge_label:
                    continue
                if nid_a not in e1.source_ids:
                    continue
                targets_b = e1.target_ids & active_nodes
                for nid_b in targets_b:
                    for e2 in graph.edges_for(nid_b):
                        if self._edge_label and e2.label and e2.label != self._edge_label:
                            continue
                        if nid_b not in e2.source_ids:
                            continue
                        targets_c = e2.target_ids & active_nodes
                        for nid_c in targets_c:
                            if nid_a == nid_c:
                                continue
                            if (nid_a, nid_c) in edge_set:
                                continue
                            matches.append(RuleMatch(
                                rule_name=self.name,
                                bindings={"A": nid_a, "B": nid_b, "C": nid_c},
                                context={"edge_ab": e1.id, "edge_bc": e2.id},
                            ))
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        a, c = match.bindings["A"], match.bindings["C"]
        label = self._new_label or "inferred"
        edge = Hyperedge(
            source_ids=frozenset({a}),
            target_ids=frozenset({c}),
            label=label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def _edge_exists(self, graph: Hypergraph, source: str, target: str) -> bool:
        for edge in graph.edges_for(source):
            if source in edge.source_ids and target in edge.target_ids:
                return True
        return False


class InverseRule(Rule):
    def __init__(self, *, edge_label: str, inverse_label: str) -> None:
        self._edge_label = edge_label
        self._inverse_label = inverse_label

    @property
    def name(self) -> str:
        return f"inverse({self._edge_label}->{self._inverse_label})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        for nid in active_nodes:
            for edge in graph.edges_for(nid):
                if edge.label != self._edge_label:
                    continue
                if nid not in edge.source_ids:
                    continue
                for target in edge.target_ids & active_nodes:
                    if self._inverse_exists(graph, target, nid):
                        continue
                    matches.append(RuleMatch(
                        rule_name=self.name,
                        bindings={"source": nid, "target": target},
                        context={"original_edge": edge.id},
                    ))
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        source, target = match.bindings["source"], match.bindings["target"]
        edge = Hyperedge(
            source_ids=frozenset({target}),
            target_ids=frozenset({source}),
            label=self._inverse_label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def _inverse_exists(self, graph: Hypergraph, source: str, target: str) -> bool:
        for edge in graph.edges_for(source):
            if edge.label == self._inverse_label and source in edge.source_ids and target in edge.target_ids:
                return True
        return False


class GeneralizationRule(Rule):
    def __init__(self, *, similarity_threshold: float = 0.8, label_prefix: str = "abstract_") -> None:
        self._threshold = similarity_threshold
        self._label_prefix = label_prefix

    @property
    def name(self) -> str:
        return "generalization"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        nodes = [graph.get_node(nid) for nid in active_nodes]
        nodes = [n for n in nodes if n is not None and n.data is not None]
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                sim = nodes[i].matches(nodes[j])
                if sim >= self._threshold:
                    if self._abstract_exists(graph, nodes[i], nodes[j]):
                        continue
                    matches.append(RuleMatch(
                        rule_name=self.name,
                        bindings={"A": nodes[i].id, "B": nodes[j].id},
                        context={
                            "similarity": sim,
                            "label_a": nodes[i].label,
                            "label_b": nodes[j].label,
                        },
                    ))
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        node_a = graph.get_node(match.bindings["A"])
        node_b = graph.get_node(match.bindings["B"])
        if not node_a or not node_b:
            return [], []
        abstract_label = f"{self._label_prefix}{node_a.label}_{node_b.label}"
        abstract_data = node_a.data
        shared_modalities = node_a.metadata.modality_tags & node_b.metadata.modality_tags
        abstract_node = Hypernode(
            label=abstract_label,
            data=abstract_data,
            metadata=Metadata(
                modality_tags=shared_modalities,
                custom={"rule": self.name, "abstract_of": [node_a.id, node_b.id]},
            ),
        )
        graph.add_node(abstract_node)
        edge_a = Hyperedge(
            source_ids=frozenset({abstract_node.id}),
            target_ids=frozenset({node_a.id, node_b.id}),
            label="generalizes",
            metadata=Metadata(custom={"rule": self.name, "inferred": True}),
        )
        graph.add_edge(edge_a)
        return [abstract_node.id], [edge_a.id]

    def _abstract_exists(self, graph: Hypergraph, a: Hypernode, b: Hypernode) -> bool:
        for edge in graph.edges_for(a.id):
            if edge.label == "generalizes" and b.id in edge.target_ids:
                return True
        return False


class AbductiveRule(Rule):
    def __init__(self, *, effect_label: str = "", cause_label: str = "possible_cause") -> None:
        self._effect_label = effect_label
        self._cause_label = cause_label

    @property
    def name(self) -> str:
        return f"abductive({self._effect_label or '*'})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        existing_pairs: set[tuple[str, str]] = set()
        for edge in graph.edges:
            if edge.label == self._cause_label and edge.metadata.custom.get("rule") == self.name:
                for src in edge.source_ids:
                    for tgt in edge.target_ids:
                        src_label = graph.get_node(src)
                        tgt_label = graph.get_node(tgt)
                        if src_label and tgt_label:
                            existing_pairs.add((src_label.label, tgt_label.label))
        for nid_b in active_nodes:
            node_b = graph.get_node(nid_b)
            if not node_b:
                continue
            incoming = [
                e for e in graph.edges_for(nid_b)
                if nid_b in e.target_ids
                and (not self._effect_label or e.label == self._effect_label)
            ]
            for edge in incoming:
                for nid_a in edge.source_ids & active_nodes:
                    node_a = graph.get_node(nid_a)
                    if not node_a:
                        continue
                    pair_key = (node_a.label, node_b.label)
                    if pair_key in existing_pairs:
                        continue
                    matches.append(RuleMatch(
                        rule_name=self.name,
                        bindings={"observed": nid_b, "potential_cause": nid_a},
                        context={"via_edge": edge.id, "edge_label": edge.label},
                    ))
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        observed_id = match.bindings["observed"]
        cause_id = match.bindings["potential_cause"]
        cause_node = graph.get_node(cause_id)
        hypothesis_node = Hypernode(
            label=f"hypothesis:{cause_node.label if cause_node is not None else cause_id}",
            data={"abduced_from": match.context},
            metadata=Metadata(
                modality_tags={Modality.CONCEPTUAL},
                custom={"rule": self.name, "inferred": True, "confidence": 0.5},
            ),
        )
        graph.add_node(hypothesis_node)
        edge = Hyperedge(
            source_ids=frozenset({hypothesis_node.id}),
            target_ids=frozenset({observed_id}),
            label=self._cause_label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True}),
        )
        graph.add_edge(edge)
        return [hypothesis_node.id], [edge.id]


class PropertyPropagationRule(Rule):
    def __init__(self, *, property_key: str, edge_label: str = "") -> None:
        self._property_key = property_key
        self._edge_label = edge_label

    @property
    def name(self) -> str:
        return f"propagate({self._property_key})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        for nid in active_nodes:
            node = graph.get_node(nid)
            if not node:
                continue
            if self._property_key not in node.metadata.custom:
                continue
            for edge in graph.edges_for(nid):
                if self._edge_label and edge.label != self._edge_label:
                    continue
                targets = edge.target_ids & active_nodes
                for target_id in targets:
                    target = graph.get_node(target_id)
                    if not target:
                        continue
                    if self._property_key in target.metadata.custom:
                        continue
                    matches.append(RuleMatch(
                        rule_name=self.name,
                        bindings={"source": nid, "target": target_id},
                        context={
                            "property_value": node.metadata.custom[self._property_key],
                            "via_edge": edge.id,
                        },
                    ))
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        target = graph.get_node(match.bindings["target"])
        if not target:
            return [], []
        target.metadata.custom[self._property_key] = match.context["property_value"]
        target.metadata.custom[f"{self._property_key}_inherited_from"] = match.bindings["source"]
        return [], []
