from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

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

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return 1.0

    def find_derivation(self, target_node_id: str, graph: Hypergraph) -> list[RuleMatch]:
        return []

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": self.__class__.__name__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        rule_type = data.get("rule_type", "")
        rule_classes: dict[str, type[Rule]] = {
            "TransitiveRule": TransitiveRule,
            "InverseRule": InverseRule,
            "GeneralizationRule": GeneralizationRule,
            "AbductiveRule": AbductiveRule,
            "PropertyPropagationRule": PropertyPropagationRule,
            "AnalogicalReasoningRule": AnalogicalReasoningRule,
            "CausalInferenceRule": CausalInferenceRule,
            "ContextualSubstitutionRule": ContextualSubstitutionRule,
        }
        target_cls = rule_classes.get(rule_type)
        if target_cls is not None:
            from_cls: Any = target_cls
            return from_cls._from_dict(data)
        raise ValueError(f"Unknown rule type: {rule_type}")


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
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.9}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def _edge_exists(self, graph: Hypergraph, source: str, target: str) -> bool:
        for edge in graph.edges_for(source):
            if source in edge.source_ids and target in edge.target_ids:
                return True
        return False

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        edge_ab = graph.get_edge(match.context.get("edge_ab", ""))
        edge_bc = graph.get_edge(match.context.get("edge_bc", ""))
        w_ab = edge_ab.weight if edge_ab else 1.0
        w_bc = edge_bc.weight if edge_bc else 1.0
        conf_ab = edge_ab.metadata.custom.get("confidence", 1.0) if edge_ab else 1.0
        conf_bc = edge_bc.metadata.custom.get("confidence", 1.0) if edge_bc else 1.0
        return w_ab * w_bc * conf_ab * conf_bc

    def find_derivation(self, target_node_id: str, graph: Hypergraph) -> list[RuleMatch]:
        derivations: list[RuleMatch] = []
        edge_set: set[tuple[str, str]] = set()
        for edge in graph.edges:
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    edge_set.add((src, tgt))
        incoming_to_c = [e for e in graph.edges_for(target_node_id) if target_node_id in e.target_ids]
        for e_bc in incoming_to_c:
            if self._edge_label and e_bc.label and e_bc.label != self._edge_label:
                continue
            for nid_b in e_bc.source_ids:
                incoming_to_b = [e for e in graph.edges_for(nid_b) if nid_b in e.target_ids]
                for e_ab in incoming_to_b:
                    if self._edge_label and e_ab.label and e_ab.label != self._edge_label:
                        continue
                    for nid_a in e_ab.source_ids:
                        if nid_a == target_node_id:
                            continue
                        if (nid_a, target_node_id) in edge_set:
                            continue
                        derivations.append(RuleMatch(
                            rule_name=self.name,
                            bindings={"A": nid_a, "B": nid_b, "C": target_node_id},
                            context={"edge_ab": e_ab.id, "edge_bc": e_bc.id},
                        ))
        return derivations

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "TransitiveRule", "edge_label": self._edge_label, "new_label": self._new_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> TransitiveRule:
        return cls(edge_label=data.get("edge_label"), new_label=data.get("new_label", ""))


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
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.9}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def _inverse_exists(self, graph: Hypergraph, source: str, target: str) -> bool:
        for edge in graph.edges_for(source):
            if edge.label == self._inverse_label and source in edge.source_ids and target in edge.target_ids:
                return True
        return False

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        edge = graph.get_edge(match.context.get("original_edge", ""))
        w = edge.weight if edge else 1.0
        conf = edge.metadata.custom.get("confidence", 1.0) if edge else 1.0
        return w * conf

    def find_derivation(self, target_node_id: str, graph: Hypergraph) -> list[RuleMatch]:
        derivations: list[RuleMatch] = []
        outgoing = [e for e in graph.edges_for(target_node_id) if target_node_id in e.source_ids]
        for edge in outgoing:
            if edge.label != self._edge_label:
                continue
            for source_of_inverse in edge.target_ids:
                if not self._inverse_exists(graph, source_of_inverse, target_node_id):
                    derivations.append(RuleMatch(
                        rule_name=self.name,
                        bindings={"source": source_of_inverse, "target": target_node_id},
                        context={"original_edge": edge.id},
                    ))
        return derivations

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "InverseRule", "edge_label": self._edge_label, "inverse_label": self._inverse_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> InverseRule:
        return cls(edge_label=data["edge_label"], inverse_label=data["inverse_label"])


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
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.8}),
        )
        graph.add_edge(edge_a)
        return [abstract_node.id], [edge_a.id]

    def _abstract_exists(self, graph: Hypergraph, a: Hypernode, b: Hypernode) -> bool:
        for edge in graph.edges_for(a.id):
            if edge.label == "generalizes" and b.id in edge.target_ids:
                return True
        return False

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return match.context.get("similarity", 0.5)

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "GeneralizationRule", "similarity_threshold": self._threshold, "label_prefix": self._label_prefix}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> GeneralizationRule:
        return cls(similarity_threshold=data.get("similarity_threshold", 0.8), label_prefix=data.get("label_prefix", "abstract_"))


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
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.5}),
        )
        graph.add_edge(edge)
        return [hypothesis_node.id], [edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return 0.5

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "AbductiveRule", "effect_label": self._effect_label, "cause_label": self._cause_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AbductiveRule:
        return cls(effect_label=data.get("effect_label", ""), cause_label=data.get("cause_label", "possible_cause"))


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

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return 0.7

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "PropertyPropagationRule", "property_key": self._property_key, "edge_label": self._edge_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> PropertyPropagationRule:
        return cls(property_key=data["property_key"], edge_label=data.get("edge_label", ""))


class AnalogicalReasoningRule(Rule):
    def __init__(self, *, edge_label: str = "", similarity_threshold: float = 0.7) -> None:
        self._edge_label = edge_label
        self._threshold = similarity_threshold
        self._embedding_engine = None

    def set_embedding_engine(self, engine: Any) -> None:
        self._embedding_engine = engine

    @property
    def name(self) -> str:
        return f"analogical({self._edge_label or '*'})"

    def _cosine_sim(self, a: Any, b: Any) -> float:
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        if self._embedding_engine is None:
            return []
        matches: list[RuleMatch] = []
        emb_map: dict[str, Any] = {}
        for nid in active_nodes:
            e = self._embedding_engine.get_embedding(nid)
            if e is not None:
                emb_map[nid] = e
        active_with_emb = frozenset(emb_map.keys())
        if len(active_with_emb) < 4:
            return matches
        active_list = list(active_with_emb)
        emb_matrix = np.array([emb_map[nid] for nid in active_list])
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normed = emb_matrix / norms
        node_to_idx = {nid: i for i, nid in enumerate(active_list)}
        seen_analogies: set[tuple[str, str, str, str]] = set()
        for nid_a in active_with_emb:
            for e1 in graph.edges_for(nid_a):
                if self._edge_label and e1.label and e1.label != self._edge_label:
                    continue
                if nid_a not in e1.source_ids:
                    continue
                targets_b = e1.target_ids & active_with_emb
                for nid_b in targets_b:
                    idx_a = node_to_idx[nid_a]
                    idx_b = node_to_idx[nid_b]
                    analogy_vec = normed[idx_b] - normed[idx_a]
                    for nid_c in active_with_emb:
                        if nid_c == nid_a or nid_c == nid_b:
                            continue
                        idx_c = node_to_idx[nid_c]
                        target_vec = analogy_vec + normed[idx_c]
                        target_norm = np.linalg.norm(target_vec)
                        if target_norm == 0:
                            continue
                        target_normed = target_vec / target_norm
                        sims = normed @ target_normed
                        for i_cand in np.argsort(-sims):
                            nid_d = active_list[i_cand]
                            if nid_d in (nid_a, nid_b, nid_c):
                                continue
                            sim = float(sims[i_cand])
                            if sim < self._threshold:
                                break
                            key = (nid_a, nid_b, nid_c, nid_d)
                            if key not in seen_analogies:
                                seen_analogies.add(key)
                                matches.append(RuleMatch(
                                    rule_name=self.name,
                                    bindings={"A": nid_a, "B": nid_b, "C": nid_c, "D": nid_d},
                                    context={"analogy_score": sim, "edge_ab": e1.id},
                                ))
                            break
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        c_id, d_id = match.bindings["C"], match.bindings["D"]
        a_node = graph.get_node(match.bindings["A"])
        b_node = graph.get_node(match.bindings["B"])
        c_node = graph.get_node(c_id)
        d_node = graph.get_node(d_id)
        edge_ab = graph.get_edge(match.context.get("edge_ab", ""))
        label = edge_ab.label if edge_ab else "analogous"
        confidence = match.context.get("analogy_score", 0.7)
        edge = Hyperedge(
            source_ids=frozenset({c_id}),
            target_ids=frozenset({d_id}),
            label=label,
            metadata=Metadata(custom={
                "rule": self.name, "inferred": True, "confidence": confidence,
                "analogy": f"{a_node.label if a_node else 'A'}:{b_node.label if b_node else 'B'}::{c_node.label if c_node else 'C'}:{d_node.label if d_node else 'D'}",
            }),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return match.context.get("analogy_score", 0.5)

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "AnalogicalReasoningRule", "edge_label": self._edge_label, "similarity_threshold": self._threshold}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AnalogicalReasoningRule:
        return cls(edge_label=data.get("edge_label", ""), similarity_threshold=data.get("similarity_threshold", 0.7))


class CausalInferenceRule(Rule):
    def __init__(self, *, min_support: int = 2, confidence_threshold: float = 0.6, causes_label: str = "causes") -> None:
        self._min_support = min_support
        self._confidence_threshold = confidence_threshold
        self._causes_label = causes_label

    @property
    def name(self) -> str:
        return f"causal_inference({self._causes_label})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        edge_pairs: dict[tuple[str, str], int] = {}
        for edge in graph.edges:
            if not edge.label:
                continue
            for src in edge.source_ids:
                if src not in active_nodes:
                    continue
                for tgt in edge.target_ids:
                    if tgt not in active_nodes or tgt == src:
                        continue
                    pair = (src, tgt)
                    edge_pairs[pair] = edge_pairs.get(pair, 0) + 1
        source_totals: dict[str, int] = {}
        for edge in graph.edges:
            for src in edge.source_ids:
                if src in active_nodes:
                    source_totals[src] = source_totals.get(src, 0) + 1
        for (src, tgt), pair_count in edge_pairs.items():
            total_from_src = source_totals.get(src, 0)
            if total_from_src == 0:
                continue
            support = pair_count
            confidence = pair_count / total_from_src
            if support >= self._min_support and confidence >= self._confidence_threshold:
                existing = False
                for e in graph.edges_for(src):
                    if e.label == self._causes_label and tgt in e.target_ids:
                        existing = True
                        break
                if not existing:
                    matches.append(RuleMatch(
                        rule_name=self.name,
                        bindings={"cause": src, "effect": tgt},
                        context={"support": support, "confidence": confidence},
                    ))
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        cause_id, effect_id = match.bindings["cause"], match.bindings["effect"]
        confidence = match.context["confidence"]
        edge = Hyperedge(
            source_ids=frozenset({cause_id}),
            target_ids=frozenset({effect_id}),
            label=self._causes_label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": confidence, "support": match.context["support"]}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return match.context.get("confidence", 0.5)

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "CausalInferenceRule", "min_support": self._min_support, "confidence_threshold": self._confidence_threshold, "causes_label": self._causes_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> CausalInferenceRule:
        return cls(min_support=data.get("min_support", 2), confidence_threshold=data.get("confidence_threshold", 0.6), causes_label=data.get("causes_label", "causes"))


class ContextualSubstitutionRule(Rule):
    def __init__(self, *, similarity_threshold: float = 0.8, substitution_label: str = "substitutes_for") -> None:
        self._threshold = similarity_threshold
        self._label = substitution_label

    @property
    def name(self) -> str:
        return f"substitution({self._label})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        nodes = [graph.get_node(nid) for nid in active_nodes]
        nodes = [n for n in nodes if n is not None]
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                sim = nodes[i].matches(nodes[j])
                if sim >= self._threshold:
                    if self._substitution_exists(graph, nodes[i].id, nodes[j].id):
                        continue
                    matches.append(RuleMatch(
                        rule_name=self.name,
                        bindings={"A": nodes[i].id, "B": nodes[j].id},
                        context={"similarity": sim},
                    ))
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        a_id, b_id = match.bindings["A"], match.bindings["B"]
        confidence = match.context["similarity"]
        edge_ab = Hyperedge(
            source_ids=frozenset({a_id}),
            target_ids=frozenset({b_id}),
            label=self._label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": confidence}),
        )
        edge_ba = Hyperedge(
            source_ids=frozenset({b_id}),
            target_ids=frozenset({a_id}),
            label=self._label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": confidence}),
        )
        graph.add_edge(edge_ab)
        graph.add_edge(edge_ba)
        return [], [edge_ab.id, edge_ba.id]

    def _substitution_exists(self, graph: Hypergraph, a_id: str, b_id: str) -> bool:
        for edge in graph.edges_for(a_id):
            if edge.label == self._label and b_id in edge.target_ids:
                return True
        return False

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return match.context.get("similarity", 0.5)

    def to_dict(self) -> dict[str, Any]:
        return {"rule_type": "ContextualSubstitutionRule", "similarity_threshold": self._threshold, "substitution_label": self._label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ContextualSubstitutionRule:
        return cls(similarity_threshold=data.get("similarity_threshold", 0.8), substitution_label=data.get("substitution_label", "substitutes_for"))
