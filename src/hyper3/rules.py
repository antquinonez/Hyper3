"""Rule ABC with concrete implementations for pattern-matching inference."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, Modality


@dataclass
class RuleMatch:
    """A single match found by a rule, binding node IDs to named roles."""

    rule_name: str
    bindings: dict[str, str]
    context: dict[str, Any] = field(default_factory=dict)


class Rule(ABC):
    """Abstract base class for inference rules.

    Subclasses implement ``find_matches`` to discover pattern instances in the
    graph and ``apply`` to materialize new edges (or nodes) for a given match.
    The multiway engine calls these two phases separately so that matches can be
    scored, deduplicated, and explored across many branches before commit.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the human-readable name of this rule."""
        ...

    @abstractmethod
    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find all rule matches in the graph among active nodes.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs that may participate in matches.

        Returns:
            A list of ``RuleMatch`` objects describing each match.
        """
        ...

    @abstractmethod
    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Apply a matched rule to the graph, mutating it in place.

        Args:
            graph: The hypergraph to modify.
            match: The previously found match to materialize.

        Returns:
            A tuple of (new_node_ids, new_edge_ids) created by this application.
        """
        ...

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Return a confidence score in [0, 1] for the given match."""
        return 1.0

    def find_derivation(self, target_node_id: str, graph: Hypergraph) -> list[RuleMatch]:
        """Find matches that could derive the target node via this rule.

        Args:
            target_node_id: The node to explain or derive.
            graph: The hypergraph to search.

        Returns:
            A list of ``RuleMatch`` objects whose application would produce
            edges incident to *target_node_id*.
        """
        return []

    def to_dict(self) -> dict[str, Any]:
        """Serialize this rule to a JSON-compatible dictionary."""
        return {"rule_type": self.__class__.__name__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        """Deserialize a rule from a dictionary produced by ``to_dict``.

        Args:
            data: Dictionary with at least a ``rule_type`` key.

        Returns:
            The reconstructed ``Rule`` instance.

        Raises:
            ValueError: If *rule_type* is unknown.
        """
        rule_type = data.get("rule_type", "")
        if rule_type == "AnalogicalReasoningRule":
            from hyper3.rules_analogy import AnalogicalReasoningRule
            return AnalogicalReasoningRule._from_dict(data)
        if rule_type == "DecompositionRule":
            from hyper3.rules_decomposition import DecompositionRule
            return DecompositionRule._from_dict(data)
        if rule_type == "InductiveGeneralizationRule":
            from hyper3.rules_inductive import InductiveGeneralizationRule
            return InductiveGeneralizationRule._from_dict(data)
        rule_classes: dict[str, type[Rule]] = {
            "TransitiveRule": TransitiveRule,
            "InverseRule": InverseRule,
            "GeneralizationRule": GeneralizationRule,
            "AbductiveRule": AbductiveRule,
            "PropertyPropagationRule": PropertyPropagationRule,
            "StructuralProjectionRule": StructuralProjectionRule,
            "HubInferenceRule": HubInferenceRule,
            "ContextualSubstitutionRule": ContextualSubstitutionRule,
        }
        target_cls = rule_classes.get(rule_type)
        if target_cls is not None:
            from_cls: Any = target_cls
            return from_cls._from_dict(data)
        raise ValueError(f"Unknown rule type: {rule_type}")


class TransitiveRule(Rule):
    """Detect two-hop chains A-[label]->B-[label]->C and infer a direct edge A->C.

    This is the graph-theoretic transitive closure applied to edges of a
    specific label.  By default, inferred edges receive the label
    ``"inferred"``; set ``new_label`` equal to ``edge_label`` to enable
    multi-hop chaining at deeper reasoning depths.
    """

    def __init__(self, *, edge_label: str | None = None, new_label: str = "") -> None:
        """Initialize the transitive rule.

        Args:
            edge_label: Only match edges with this label. ``None`` matches all.
            new_label: Label for inferred edges. Defaults to ``"inferred"``.
                Set to the same value as ``edge_label`` to enable multi-hop
                chaining (e.g. ``TransitiveRule(edge_label="causes",
                new_label="causes")``).
        """
        self._edge_label = edge_label
        self._new_label = new_label

    @property
    def name(self) -> str:
        """Return ``"transitive(<label>)"``."""
        return f"transitive({self._edge_label or '*'})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find two-hop chains A→B→C among active nodes where A→C does not yet exist.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate in matches.

        Returns:
            Matches with bindings ``{A, B, C}`` and context keys
            ``edge_ab`` and ``edge_bc``.
        """
        edge_set = self._build_edge_set(graph)
        return self._find_transitive_chains(graph, active_nodes, edge_set)

    def _build_edge_set(self, graph: Hypergraph) -> set[tuple[str, str]]:
        """Pre-build a set of (source, target) pairs for O(1) edge-existence checks."""
        edge_set: set[tuple[str, str]] = set()
        for edge in graph.edges:
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    edge_set.add((src, tgt))
        return edge_set

    def _find_transitive_chains(self, graph: Hypergraph, active_nodes: frozenset[str], edge_set: set[tuple[str, str]]) -> list[RuleMatch]:
        """Find transitive chains matching the configured edge label."""
        matches: list[RuleMatch] = []
        for nid_a in active_nodes:
            for e1 in graph.outgoing_edges(nid_a):
                if self._edge_label and e1.label != self._edge_label:
                    continue
                for nid_b in e1.target_ids & active_nodes:
                    matches.extend(self._find_second_hop(graph, nid_a, nid_b, active_nodes, edge_set, e1.id))
        return matches

    def _find_second_hop(self, graph: Hypergraph, nid_a: str, nid_b: str, active_nodes: frozenset[str], edge_set: set[tuple[str, str]], e1_id: str) -> list[RuleMatch]:
        """Find second-hop targets for a given intermediate node."""
        results: list[RuleMatch] = []
        for e2 in graph.outgoing_edges(nid_b):
            if self._edge_label and e2.label != self._edge_label:
                continue
            for nid_c in e2.target_ids & active_nodes:
                if nid_a == nid_c:
                    continue
                if (nid_a, nid_c) in edge_set:
                    continue
                results.append(
                    RuleMatch(
                        rule_name=self.name,
                        bindings={"A": nid_a, "B": nid_b, "C": nid_c},
                        context={"edge_ab": e1_id, "edge_bc": e2.id},
                    )
                )
        return results

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create an inferred edge from A to C.

        A live existence check is performed immediately before adding the edge
        so that sibling matches applied to the same shared graph in the same
        expansion round cannot produce duplicate edges.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``A`` and ``C`` bindings.

        Returns:
            ``( [], [new_edge_id] )`` or ``( [], [] )`` when the edge already exists.
        """
        a, c = match.bindings["A"], match.bindings["C"]
        label = self._new_label or "inferred"
        if self._edge_exists(graph, a, c):
            return [], []
        edge = Hyperedge(
            source_ids=frozenset({a}),
            target_ids=frozenset({c}),
            label=label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.9}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def _edge_exists(self, graph: Hypergraph, source: str, target: str) -> bool:
        """Check whether a direct edge from *source* to *target* exists."""
        return any(source in edge.source_ids and target in edge.target_ids for edge in graph.incident_edges(source))

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score a transitive match as the product of constituent edge weights and confidences."""
        edge_ab = graph.get_edge(match.context.get("edge_ab", ""))
        edge_bc = graph.get_edge(match.context.get("edge_bc", ""))
        w_ab = edge_ab.weight if edge_ab else 1.0
        w_bc = edge_bc.weight if edge_bc else 1.0
        conf_ab = edge_ab.metadata.custom.get("confidence", 1.0) if edge_ab else 1.0
        conf_bc = edge_bc.metadata.custom.get("confidence", 1.0) if edge_bc else 1.0
        return min(w_ab * w_bc * conf_ab * conf_bc, 1.0)

    def find_derivation(self, target_node_id: str, graph: Hypergraph) -> list[RuleMatch]:
        """Find two-hop chains A→B→target that could derive the target via transitivity.

        Args:
            target_node_id: The node whose derivation is sought.
            graph: The hypergraph to search.

        Returns:
            Matches with bindings ``{A, B, C}`` where ``C`` is *target_node_id*.
        """
        edge_set = self._build_edge_set(graph)
        incoming_to_c = [e for e in graph.incident_edges(target_node_id) if target_node_id in e.target_ids]
        return self._scan_derivation_chains(graph, target_node_id, incoming_to_c, edge_set)

    def _scan_derivation_chains(self, graph: Hypergraph, target_node_id: str, incoming_to_c: list, edge_set: set[tuple[str, str]]) -> list[RuleMatch]:
        """Scan for derivation chains through intermediate nodes."""
        derivations: list[RuleMatch] = []
        for e_bc in incoming_to_c:
            if self._edge_label and e_bc.label and e_bc.label != self._edge_label:
                continue
            for nid_b in e_bc.source_ids:
                derivations.extend(self._scan_first_hop(graph, target_node_id, nid_b, e_bc.id, edge_set))
        return derivations

    def _scan_first_hop(self, graph: Hypergraph, target_node_id: str, nid_b: str, e_bc_id: str, edge_set: set[tuple[str, str]]) -> list[RuleMatch]:
        """Scan for first-hop edges from active nodes."""
        results: list[RuleMatch] = []
        incoming_to_b = [e for e in graph.incident_edges(nid_b) if nid_b in e.target_ids]
        for e_ab in incoming_to_b:
            if self._edge_label and e_ab.label and e_ab.label != self._edge_label:
                continue
            for nid_a in e_ab.source_ids:
                if nid_a == target_node_id:
                    continue
                if (nid_a, target_node_id) in edge_set:
                    continue
                results.append(
                    RuleMatch(
                        rule_name=self.name,
                        bindings={"A": nid_a, "B": nid_b, "C": target_node_id},
                        context={"edge_ab": e_ab.id, "edge_bc": e_bc_id},
                    )
                )
        return results

    def to_dict(self) -> dict[str, Any]:
        """Serialize the transitive rule configuration."""
        return {"rule_type": "TransitiveRule", "edge_label": self._edge_label, "new_label": self._new_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> TransitiveRule:
        """Reconstruct a ``TransitiveRule`` from serialized data."""
        return cls(edge_label=data.get("edge_label"), new_label=data.get("new_label", ""))


class InverseRule(Rule):
    """Detect forward edges and infer the corresponding reverse edge.

    For every edge with ``edge_label`` from S to T, this rule infers an edge
    with ``inverse_label`` from T back to S (if it does not already exist).
    Useful for bidirectional relationships like ``parent_of``/``child_of``.
    """

    def __init__(self, *, edge_label: str, inverse_label: str) -> None:
        """Initialize the inverse rule.

        Args:
            edge_label: Label of forward edges to match.
            inverse_label: Label to assign to inferred inverse edges.
        """
        self._edge_label = edge_label
        self._inverse_label = inverse_label

    @property
    def name(self) -> str:
        """Return ``"inverse(<edge_label>-><inverse_label>)"``."""
        return f"inverse({self._edge_label}->{self._inverse_label})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find forward edges whose inverse does not yet exist.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{source, target}`` and context key
            ``original_edge``.
        """
        matches: list[RuleMatch] = []
        for nid in active_nodes:
            for edge in graph.outgoing_edges(nid):
                if edge.label != self._edge_label:
                    continue
                for target in edge.target_ids & active_nodes:
                    if self._inverse_exists(graph, target, nid):
                        continue
                    matches.append(
                        RuleMatch(
                            rule_name=self.name,
                            bindings={"source": nid, "target": target},
                            context={"original_edge": edge.id},
                        )
                    )
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create an inverse edge from target back to source.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``source`` and ``target`` bindings.

        Returns:
            ``( [], [new_edge_id] )`` or ``( [], [] )`` if the edge already exists.
        """
        source, target = match.bindings["source"], match.bindings["target"]
        if self._inverse_exists(graph, target, source):
            return [], []
        edge = Hyperedge(
            source_ids=frozenset({target}),
            target_ids=frozenset({source}),
            label=self._inverse_label,
            metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.9}),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def _inverse_exists(self, graph: Hypergraph, source: str, target: str) -> bool:
        """Check whether an inverse edge from *source* to *target* already exists."""
        for edge in graph.incident_edges(source):
            if edge.label == self._inverse_label and source in edge.source_ids and target in edge.target_ids:
                return True
        return False

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score an inverse match using the original edge weight and confidence."""
        edge = graph.get_edge(match.context.get("original_edge", ""))
        w = edge.weight if edge else 1.0
        conf = edge.metadata.custom.get("confidence", 1.0) if edge else 1.0
        return min(w * conf, 1.0)

    def find_derivation(self, target_node_id: str, graph: Hypergraph) -> list[RuleMatch]:
        """Find forward edges from *target_node_id* whose inverse could be inferred.

        Args:
            target_node_id: The node whose derivation is sought.
            graph: The hypergraph to search.

        Returns:
            Matches with bindings ``{source, target}``.
        """
        derivations: list[RuleMatch] = []
        outgoing = [e for e in graph.incident_edges(target_node_id) if target_node_id in e.source_ids]
        for edge in outgoing:
            if edge.label != self._edge_label:
                continue
            derivations.extend(
                RuleMatch(
                    rule_name=self.name,
                    bindings={"source": source_of_inverse, "target": target_node_id},
                    context={"original_edge": edge.id},
                )
                for source_of_inverse in edge.target_ids
                if not self._inverse_exists(graph, source_of_inverse, target_node_id)
            )
        return derivations

    def to_dict(self) -> dict[str, Any]:
        """Serialize the inverse rule configuration."""
        return {"rule_type": "InverseRule", "edge_label": self._edge_label, "inverse_label": self._inverse_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> InverseRule:
        """Reconstruct an ``InverseRule`` from serialized data."""
        return cls(edge_label=data["edge_label"], inverse_label=data["inverse_label"])


class GeneralizationRule(Rule):
    """Detect pairs of data-similar nodes and create an abstract summary node.

    When two nodes exceed the similarity threshold and share no existing
    ``"generalizes"`` link, this rule creates an abstract node connected to
    both via a single hyperedge, enabling higher-level reasoning over
    categories.
    """

    def __init__(self, *, similarity_threshold: float = 0.8, label_prefix: str = "abstract_") -> None:
        """Initialize the generalization rule.

        Args:
            similarity_threshold: Minimum data similarity for two nodes to be
                candidates for abstraction.
            label_prefix: Prefix for generated abstract node labels.
        """
        self._threshold = similarity_threshold
        self._label_prefix = label_prefix

    @property
    def name(self) -> str:
        """Return ``"generalization"``."""
        return "generalization"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find pairs of similar nodes that share no existing abstraction.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{A, B}`` and context keys
            ``similarity``, ``label_a``, ``label_b``.
        """
        matches: list[RuleMatch] = []
        nodes = [graph.get_node(nid) for nid in active_nodes]
        nodes = [n for n in nodes if n is not None and n.data is not None]
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                sim = nodes[i].matches(nodes[j])
                if sim >= self._threshold:
                    if self._abstract_exists(graph, nodes[i], nodes[j]):
                        continue
                    matches.append(
                        RuleMatch(
                            rule_name=self.name,
                            bindings={"A": nodes[i].id, "B": nodes[j].id},
                            context={
                                "similarity": sim,
                                "label_a": nodes[i].label,
                                "label_b": nodes[j].label,
                            },
                        )
                    )
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create an abstract node linked to both original nodes via a ``"generalizes"`` edge.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``A`` and ``B`` bindings.

        Returns:
            ``( [abstract_node_id], [edge_id] )``.
        """
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
        """Check whether a ``"generalizes"`` edge already links *a* to *b*."""
        return any(edge.label == "generalizes" and b.id in edge.target_ids for edge in graph.incident_edges(a.id))

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score a generalization match by the similarity stored in context."""
        return match.context.get("similarity", 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the generalization rule configuration."""
        return {
            "rule_type": "GeneralizationRule",
            "similarity_threshold": self._threshold,
            "label_prefix": self._label_prefix,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> GeneralizationRule:
        """Reconstruct a ``GeneralizationRule`` from serialized data."""
        return cls(
            similarity_threshold=data.get("similarity_threshold", 0.8),
            label_prefix=data.get("label_prefix", "abstract_"),
        )


class AbductiveRule(Rule):
    """Perform abductive reasoning: propose a hypothesis node for observed effects.

    When a node B has an incoming edge from A, this rule creates a hypothesis
    node representing a possible causal explanation and links it to B with a
    ``cause_label`` edge.  Confidence is set conservatively (0.5) since
    abduction produces plausible but unverified explanations.
    """

    def __init__(self, *, effect_label: str = "", cause_label: str = "possible_cause") -> None:
        """Initialize the abductive rule.

        Args:
            effect_label: Only match incoming edges with this label. Empty
                string matches all.
            cause_label: Label for the inferred cause edge.
        """
        self._effect_label = effect_label
        self._cause_label = cause_label

    @property
    def name(self) -> str:
        """Return ``"abductive(<effect_label>)"``."""
        return f"abductive({self._effect_label or '*'})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find observed-effect nodes with incoming edges from potential causes.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{observed, potential_cause}`` and context
            keys ``via_edge`` and ``edge_label``.
        """
        matches: list[RuleMatch] = []
        existing_pairs = self._build_existing_pairs(graph)
        for nid_b in active_nodes:
            matches.extend(self._find_causes_for_effect(graph, nid_b, active_nodes, existing_pairs))
        return matches

    def _build_existing_pairs(self, graph: Hypergraph) -> set[tuple[str, str]]:
        """Build a set of existing source-target pairs for duplicate filtering."""
        existing_pairs: set[tuple[str, str]] = set()
        for edge in graph.edges:
            if edge.label == self._cause_label and edge.metadata.custom.get("rule") == self.name:
                for src in edge.source_ids:
                    for tgt in edge.target_ids:
                        src_node = graph.get_node(src)
                        tgt_node = graph.get_node(tgt)
                        if src_node and tgt_node:
                            existing_pairs.add((src_node.label, tgt_node.label))
        return existing_pairs

    def _find_causes_for_effect(self, graph: Hypergraph, nid_b: str, active_nodes: frozenset[str], existing_pairs: set[tuple[str, str]]) -> list[RuleMatch]:
        """Find candidate causes that could explain an observed effect."""
        node_b = graph.get_node(nid_b)
        if not node_b:
            return []
        results: list[RuleMatch] = []
        incoming = [
            e
            for e in graph.incident_edges(nid_b)
            if nid_b in e.target_ids and (not self._effect_label or e.label == self._effect_label)
        ]
        for edge in incoming:
            for nid_a in edge.source_ids & active_nodes:
                node_a = graph.get_node(nid_a)
                if not node_a:
                    continue
                pair_key = (node_a.label, node_b.label)
                if pair_key in existing_pairs:
                    continue
                results.append(
                    RuleMatch(
                        rule_name=self.name,
                        bindings={"observed": nid_b, "potential_cause": nid_a},
                        context={"via_edge": edge.id, "edge_label": edge.label},
                    )
                )
        return results

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create a hypothesis node and link it to the observed node.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``observed`` and ``potential_cause`` bindings.

        Returns:
            ``( [hypothesis_node_id], [edge_id] )``.
        """
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
        """Score an abductive hypothesis match using the supporting evidence edge.

        Looks up the ``via_edge`` from match context and returns
        ``edge.weight * 0.6 * confidence``, clamped to ``[0.1, 1.0]``.
        Falls back to ``0.3`` if no edge is found.
        """
        via_edge_id = match.context.get("via_edge")
        if via_edge_id:
            edge = graph.get_edge(via_edge_id)
            if edge:
                conf = edge.metadata.custom.get("confidence", 1.0)
                return min(max(edge.weight * 0.6 * conf, 0.1), 1.0)
        return 0.3

    def to_dict(self) -> dict[str, Any]:
        """Serialize the abductive rule configuration."""
        return {"rule_type": "AbductiveRule", "effect_label": self._effect_label, "cause_label": self._cause_label}

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AbductiveRule:
        """Reconstruct an ``AbductiveRule`` from serialized data."""
        return cls(effect_label=data.get("effect_label", ""), cause_label=data.get("cause_label", "possible_cause"))


class PropertyPropagationRule(Rule):
    """Copy a named metadata property from source nodes to their edge neighbors.

    For each node that carries ``property_key`` in its metadata, the rule
    finds neighbors reachable via outgoing edges and propagates the property
    value to any neighbor that lacks it.  No new edges are created; existing
    node metadata is updated in place.
    """

    def __init__(self, *, property_key: str, edge_label: str | None = None) -> None:
        """Initialize the property propagation rule.

        Args:
            property_key: Metadata key to propagate from source to target nodes.
            edge_label: Only propagate along edges with this label. ``None``
                matches all edges.
        """
        self._property_key = property_key
        self._edge_label = edge_label

    @property
    def name(self) -> str:
        """Return ``"propagate(<property_key>)"``."""
        return f"propagate({self._property_key})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find nodes that carry the property and neighbors that lack it.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{source, target}`` and context keys
            ``property_value`` and ``via_edge``.
        """
        matches: list[RuleMatch] = []
        for nid in active_nodes:
            node = graph.get_node(nid)
            if not node:
                continue
            if self._property_key not in node.metadata.custom:
                continue
            for edge in graph.incident_edges(nid):
                if self._edge_label and edge.label != self._edge_label:
                    continue
                if nid not in edge.source_ids:
                    continue
                targets = edge.target_ids & active_nodes
                for target_id in targets:
                    target = graph.get_node(target_id)
                    if not target:
                        continue
                    if self._property_key in target.metadata.custom:
                        continue
                    matches.append(
                        RuleMatch(
                            rule_name=self.name,
                            bindings={"source": nid, "target": target_id},
                            context={
                                "property_value": node.metadata.custom[self._property_key],
                                "via_edge": edge.id,
                            },
                        )
                    )
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Copy the property value from source to target node metadata.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``source`` and ``target`` bindings.

        Returns:
            ``( [], [] )`` — no new nodes or edges are created.
        """
        target = graph.get_node(match.bindings["target"])
        if not target:
            return [], []
        target.metadata.custom[self._property_key] = match.context["property_value"]
        target.metadata.custom[f"{self._property_key}_inherited_from"] = match.bindings["source"]
        return [], []

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score a property propagation match using edge weight and value specificity.

        Looks up ``via_edge`` from match context and computes a specificity
        factor from ``property_value``: numeric values scale by magnitude,
        strings scale by length. Returns ``edge.weight * 0.7 * specificity``,
        clamped to ``[0.1, 1.0]``. Falls back to ``0.4`` if no edge is found.
        """
        via_edge_id = match.context.get("via_edge")
        prop_val = match.context.get("property_value")
        if via_edge_id:
            edge = graph.get_edge(via_edge_id)
            if edge:
                specificity = 0.5
                if isinstance(prop_val, (int, float)):
                    specificity = min(abs(prop_val) * 0.1, 0.5) + 0.5
                elif isinstance(prop_val, str):
                    specificity = min(len(prop_val) * 0.05, 0.5) + 0.5
                return min(max(edge.weight * 0.7 * specificity, 0.1), 1.0)
        return 0.4

    def to_dict(self) -> dict[str, Any]:
        """Serialize the property propagation rule configuration."""
        return {
            "rule_type": "PropertyPropagationRule",
            "property_key": self._property_key,
            "edge_label": self._edge_label,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> PropertyPropagationRule:
        """Reconstruct a ``PropertyPropagationRule`` from serialized data."""
        return cls(property_key=data["property_key"], edge_label=data.get("edge_label"))


class StructuralProjectionRule(Rule):
    """Perform analogical reasoning via embedding arithmetic (A:B :: C:D).

    Given node embeddings, the rule computes ``vec(B) - vec(A) + vec(C)`` and
    finds the node D whose embedding is most similar to the result.  If the
    similarity exceeds the threshold, an edge mirroring the A-to-B relationship
    is created from C to D.  Requires an external embedding engine set via
    ``set_embedding_engine``.
    """

    def __init__(self, *, edge_label: str | None = None, similarity_threshold: float = 0.7) -> None:
        """Initialize the analogical reasoning rule.

        Args:
            edge_label: Only consider edges with this label. ``None``
                matches all edges.
            similarity_threshold: Minimum embedding cosine similarity for
                candidate D in the analogy A:B :: C:D.
        """
        self._edge_label = edge_label
        self._threshold = similarity_threshold
        self._embedding_engine = None

    def set_embedding_engine(self, engine: Any) -> None:
        """Attach an embedding engine for computing node-vector representations.

        Args:
            engine: An object with a ``get_embedding(node_id)`` method.
        """
        self._embedding_engine = engine

    @property
    def name(self) -> str:
        """Return ``"analogical(<edge_label>)"``."""
        return f"analogical({self._edge_label or '*'})"

    def _cosine_sim(self, a: Any, b: Any) -> float:
        """Compute the cosine similarity between two vectors."""
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find analogical patterns A:B :: C:D using embedding arithmetic.

        Requires a configured embedding engine. Returns empty list if none
        is set or fewer than four nodes have embeddings.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{A, B, C, D}`` and context keys
            ``analogy_score`` and ``edge_ab``.
        """
        if self._embedding_engine is None:
            return []
        emb_data = self._prepare_embedding_data(active_nodes)
        if emb_data is None:
            return []
        normed, active_list, node_to_idx, active_with_emb = emb_data
        seen_analogies: set[tuple[str, str, str, str]] = set()
        matches: list[RuleMatch] = []
        for nid_a in active_with_emb:
            matches.extend(self._compute_analogy_scores(graph, nid_a, active_with_emb, normed, active_list, node_to_idx, seen_analogies))
        return matches

    def _prepare_embedding_data(self, active_nodes: frozenset[str]) -> tuple[Any, list[str], dict[str, int], frozenset[str]] | None:
        """Prepare embedding vectors for nodes involved in pattern matching."""
        if self._embedding_engine is None:
            return None
        emb_map: dict[str, Any] = {}
        for nid in active_nodes:
            e = self._embedding_engine.get_embedding(nid)
            if e is not None:
                emb_map[nid] = e
        active_with_emb = frozenset(emb_map.keys())
        if len(active_with_emb) < 4:
            return None
        active_list = list(active_with_emb)
        emb_matrix = np.array([emb_map[nid] for nid in active_list])
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normed = emb_matrix / norms
        node_to_idx = {nid: i for i, nid in enumerate(active_list)}
        return normed, active_list, node_to_idx, active_with_emb

    def _compute_analogy_scores(self, graph: Hypergraph, nid_a: str, active_with_emb: frozenset[str], normed: Any, active_list: list[str], node_to_idx: dict[str, int], seen_analogies: set[tuple[str, str, str, str]]) -> list[RuleMatch]:
        """Compute analogy scores between source and target substructures."""
        results: list[RuleMatch] = []
        idx_a = node_to_idx[nid_a]
        for e1 in graph.incident_edges(nid_a):
            if self._edge_label and e1.label != self._edge_label:
                continue
            if nid_a not in e1.source_ids:
                continue
            for nid_b in e1.target_ids & active_with_emb:
                idx_b = node_to_idx[nid_b]
                analogy_vec = normed[idx_b] - normed[idx_a]
                results.extend(self._find_analogy_targets(nid_a, nid_b, analogy_vec, e1.id, active_with_emb, normed, active_list, node_to_idx, seen_analogies))
        return results

    def _find_analogy_targets(self, nid_a: str, nid_b: str, analogy_vec: Any, e1_id: str, active_with_emb: frozenset[str], normed: Any, active_list: list[str], node_to_idx: dict[str, int], seen_analogies: set[tuple[str, str, str, str]]) -> list[RuleMatch]:
        """Find candidate target substructures for analogical projection."""
        results: list[RuleMatch] = []
        for nid_c in active_with_emb:
            if nid_c in (nid_a, nid_b):
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
                    results.append(
                        RuleMatch(
                            rule_name=self.name,
                            bindings={"A": nid_a, "B": nid_b, "C": nid_c, "D": nid_d},
                            context={"analogy_score": sim, "edge_ab": e1_id},
                        )
                    )
                break
        return results

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create an analogical edge from C to D mirroring the A-to-B relationship.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``A``, ``B``, ``C``, ``D`` bindings.

        Returns:
            ``( [], [new_edge_id] )``.
        """
        c_id, d_id = match.bindings["C"], match.bindings["D"]
        edge_ab = graph.get_edge(match.context.get("edge_ab", ""))
        label = edge_ab.label if edge_ab else "analogous"
        if any(
            e.label == label and c_id in e.source_ids and d_id in e.target_ids
            for e in graph.incident_edges(c_id)
        ):
            return [], []
        a_node = graph.get_node(match.bindings["A"])
        b_node = graph.get_node(match.bindings["B"])
        c_node = graph.get_node(c_id)
        d_node = graph.get_node(d_id)
        confidence = match.context.get("analogy_score", 0.7)
        edge = Hyperedge(
            source_ids=frozenset({c_id}),
            target_ids=frozenset({d_id}),
            label=label,
            metadata=Metadata(
                custom={
                    "rule": self.name,
                    "inferred": True,
                    "confidence": confidence,
                    "analogy": f"{a_node.label if a_node else 'A'}:{b_node.label if b_node else 'B'}::{c_node.label if c_node else 'C'}:{d_node.label if d_node else 'D'}",
                }
            ),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score an analogy match by the embedding similarity stored in context."""
        return match.context.get("analogy_score", 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the analogical reasoning rule configuration."""
        return {
            "rule_type": "StructuralProjectionRule",
            "edge_label": self._edge_label,
            "similarity_threshold": self._threshold,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> StructuralProjectionRule:
        """Reconstruct an ``StructuralProjectionRule`` from serialized data."""
        return cls(edge_label=data.get("edge_label"), similarity_threshold=data.get("similarity_threshold", 0.7))


class HubInferenceRule(Rule):
    """Infer causal-style edges from frequent co-occurrence patterns.

    The rule counts how often each source-target pair appears together across
    labeled edges.  Pairs exceeding ``min_support`` and ``confidence_threshold``
    (conditional probability) receive a new edge with ``causes_label``,
    capturing the intuition that frequent co-occurrence suggests a causal link.
    """

    def __init__(
        self, *, min_support: int = 2, confidence_threshold: float = 0.6, causes_label: str = "causes"
    ) -> None:
        """Initialize the hub inference rule.

        Args:
            min_support: Minimum co-occurrence count for a source-target pair.
            confidence_threshold: Minimum conditional probability
                P(target|source) to infer an edge.
            causes_label: Label for inferred edges.
        """
        self._min_support = min_support
        self._confidence_threshold = confidence_threshold
        self._causes_label = causes_label

    @property
    def name(self) -> str:
        """Return ``"hub_inference(<causes_label>)"``."""
        return f"hub_inference({self._causes_label})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find source-target pairs exceeding minimum support and confidence.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{cause, effect}`` and context keys
            ``support`` and ``confidence``.
        """
        matches: list[RuleMatch] = []
        edge_pairs, source_totals = self._build_pair_counts(graph, active_nodes)
        for (src, tgt), pair_count in edge_pairs.items():
            total_from_src = source_totals.get(src, 0)
            if total_from_src == 0:
                continue
            support = pair_count
            confidence = pair_count / total_from_src
            if support >= self._min_support and confidence >= self._confidence_threshold and not self._existing_cause_edge(graph, src, tgt):
                matches.append(
                    RuleMatch(
                        rule_name=self.name,
                        bindings={"cause": src, "effect": tgt},
                        context={"support": support, "confidence": confidence},
                    )
                )
        return matches

    def _build_pair_counts(self, graph: Hypergraph, active_nodes: frozenset[str]) -> tuple[dict[tuple[str, str], int], dict[str, int]]:
        """Count co-occurrence of node pairs across hub edges."""
        edge_pairs: dict[tuple[str, str], int] = {}
        source_totals: dict[str, int] = {}
        for edge in graph.edges:
            if not edge.label:
                continue
            active_srcs = [s for s in edge.source_ids if s in active_nodes]
            for src in active_srcs:
                source_totals[src] = source_totals.get(src, 0) + 1
            for src in active_srcs:
                for tgt in edge.target_ids:
                    if tgt not in active_nodes or tgt == src:
                        continue
                    pair = (src, tgt)
                    edge_pairs[pair] = edge_pairs.get(pair, 0) + 1
        return edge_pairs, source_totals

    def _existing_cause_edge(self, graph: Hypergraph, src: str, tgt: str) -> bool:
        """Check whether a cause edge already exists between two nodes."""
        return any(e.label == self._causes_label and tgt in e.target_ids for e in graph.incident_edges(src))

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create a ``"causes"`` edge from cause to effect.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``cause`` and ``effect`` bindings.

        Returns:
            ``( [], [new_edge_id] )``.
        """
        cause_id, effect_id = match.bindings["cause"], match.bindings["effect"]
        confidence = match.context["confidence"]
        edge = Hyperedge(
            source_ids=frozenset({cause_id}),
            target_ids=frozenset({effect_id}),
            label=self._causes_label,
            metadata=Metadata(
                custom={
                    "rule": self.name,
                    "inferred": True,
                    "confidence": confidence,
                    "support": match.context["support"],
                }
            ),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score a causal match by its confidence value."""
        return match.context.get("confidence", 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the hub inference rule configuration."""
        return {
            "rule_type": "HubInferenceRule",
            "min_support": self._min_support,
            "confidence_threshold": self._confidence_threshold,
            "causes_label": self._causes_label,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> HubInferenceRule:
        """Reconstruct a ``HubInferenceRule`` from serialized data."""
        return cls(
            min_support=data.get("min_support", 2),
            confidence_threshold=data.get("confidence_threshold", 0.6),
            causes_label=data.get("causes_label", "causes"),
        )


class ContextualSubstitutionRule(Rule):
    """Detect data-similar node pairs and create bidirectional substitution edges.

    When two nodes exceed the similarity threshold and lack an existing
    substitution link, this rule creates edges in both directions labeled
    ``substitution_label``, indicating that either node can serve as a
    stand-in for the other in reasoning.
    """

    def __init__(self, *, similarity_threshold: float = 0.8, substitution_label: str = "substitutes_for") -> None:
        """Initialize the contextual substitution rule.

        Args:
            similarity_threshold: Minimum data similarity for two nodes to be
                substitution candidates.
            substitution_label: Label for bidirectional substitution edges.
        """
        self._threshold = similarity_threshold
        self._label = substitution_label

    @property
    def name(self) -> str:
        """Return ``"substitution(<label>)"``."""
        return f"substitution({self._label})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find pairs of similar nodes without an existing substitution edge.

        Args:
            graph: The hypergraph to search.
            active_nodes: Node IDs eligible to participate.

        Returns:
            Matches with bindings ``{A, B}`` and context key ``similarity``.
        """
        matches: list[RuleMatch] = []
        nodes = [graph.get_node(nid) for nid in active_nodes]
        nodes = [n for n in nodes if n is not None]
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                sim = nodes[i].matches(nodes[j])
                if sim >= self._threshold:
                    if self._substitution_exists(graph, nodes[i].id, nodes[j].id):
                        continue
                    matches.append(
                        RuleMatch(
                            rule_name=self.name,
                            bindings={"A": nodes[i].id, "B": nodes[j].id},
                            context={"similarity": sim},
                        )
                    )
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create bidirectional substitution edges between A and B.

        Args:
            graph: The hypergraph to modify.
            match: A match with ``A`` and ``B`` bindings.

        Returns:
            ``( [], [edge_ab_id, edge_ba_id] )``.
        """
        a_id, b_id = match.bindings["A"], match.bindings["B"]
        if self._substitution_exists(graph, a_id, b_id):
            return [], []
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
        """Check whether a substitution edge already exists."""
        for edge in graph.incident_edges(a_id):
            if edge.label != self._label:
                continue
            if a_id in edge.source_ids and b_id in edge.target_ids:
                return True
            if b_id in edge.source_ids and a_id in edge.target_ids:
                return True
        return False

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Score a substitution match by the similarity stored in context."""
        return match.context.get("similarity", 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the contextual substitution rule configuration."""
        return {
            "rule_type": "ContextualSubstitutionRule",
            "similarity_threshold": self._threshold,
            "substitution_label": self._label,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ContextualSubstitutionRule:
        """Reconstruct a ``ContextualSubstitutionRule`` from serialized data."""
        return cls(
            similarity_threshold=data.get("similarity_threshold", 0.8),
            substitution_label=data.get("substitution_label", "substitutes_for"),
        )
