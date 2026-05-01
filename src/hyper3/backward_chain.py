from __future__ import annotations

from dataclasses import dataclass, field

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase
from hyper3.rules import Rule, RuleMatch


@dataclass
class ProofStep(_SimpleResultBase):
    """A single step in a backward-chaining proof, recording the rule, target, premises, and confidence."""

    rule_name: str
    target_id: str
    required_premises: list[str]
    match: RuleMatch
    confidence: float = 1.0


@dataclass
class ProofTree(_SimpleResultBase):
    """A proof tree rooted at a goal node, tracking achievement status, steps, and unresolved premises."""

    goal_id: str
    goal_label: str
    achieved: bool = False
    steps: list[ProofStep] = field(default_factory=list)
    unresolved_premises: list[str] = field(default_factory=list)
    depth: int = 0
    confidence: float = 0.0


@dataclass
class BackwardChainResult(_SimpleResultBase):
    """Result of backward-chaining proof attempt, with proof tree, missing premises, and alternative plans."""

    goal_id: str = ""
    goal_label: str = ""
    achievable: bool = False
    proof_tree: ProofTree | None = None
    total_premises_needed: int = 0
    satisfied_premises: int = 0
    missing_premises: list[str] = field(default_factory=list)
    alternative_plans: list[ProofTree] = field(default_factory=list)
    confidence: float = 0.0


class BackwardChainEngine:
    """Goal-directed reasoning engine that proves targets by chaining backward through inference rules."""

    def __init__(
        self,
        graph: Hypergraph,
        rules: list[Rule],
        *,
        max_depth: int = 5,
        max_alternatives: int = 3,
    ) -> None:
        self._graph = graph
        self._rules = rules
        self._max_depth = max_depth
        self._max_alternatives = max_alternatives

    def prove(
        self,
        target_label: str,
        *,
        known_facts: set[str] | None = None,
        edge_label: str | None = None,
    ) -> BackwardChainResult:
        """Attempt to prove *target_label* from *known_facts* by chaining backward through rules."""
        target = self._graph.get_node_by_label(target_label)
        if not target:
            return BackwardChainResult(goal_id="", goal_label=target_label)

        known = known_facts or set()
        known_ids: set[str] = set()
        for lbl in known:
            node = self._graph.get_node_by_label(lbl)
            if node:
                known_ids.add(node.id)

        tree = self._build_proof_tree(
            target.id,
            known_ids,
            edge_label,
            depth=0,
            visited=set(),
        )

        alternatives: list[ProofTree] = []
        if tree.achieved:
            alternatives = self._find_alternative_proofs(
                target.id,
                known_ids,
                edge_label,
                exclude_steps=tree.steps,
            )

        all_premises = set()
        for step in tree.steps:
            all_premises.update(step.required_premises)
        missing = [pid for pid in all_premises if pid not in known_ids]
        missing_labels: list[str] = []
        for pid in missing:
            node = self._graph.get_node(pid)
            missing_labels.append(node.label if node else pid[:8])
        satisfied = len(all_premises) - len(missing)

        return BackwardChainResult(
            goal_id=target.id,
            goal_label=target_label,
            achievable=tree.achieved,
            proof_tree=tree,
            total_premises_needed=len(all_premises),
            satisfied_premises=satisfied,
            missing_premises=missing_labels,
            alternative_plans=alternatives,
            confidence=tree.confidence,
        )

    def prove_batch(
        self,
        target_labels: list[str],
        *,
        known_facts: set[str] | None = None,
        edge_label: str | None = None,
    ) -> list[BackwardChainResult]:
        """Prove multiple targets sequentially, accumulating proven facts."""
        results: list[BackwardChainResult] = []
        known = known_facts or set()
        for label in target_labels:
            result = self.prove(label, known_facts=known, edge_label=edge_label)
            results.append(result)
            if result.achievable:
                proven_labels = set()
                for step in result.proof_tree.steps if result.proof_tree else []:
                    node = self._graph.get_node(step.target_id)
                    if node:
                        proven_labels.add(node.label)
                known = known | proven_labels
        return results

    def _build_proof_tree(
        self,
        target_id: str,
        known_ids: set[str],
        edge_label: str | None,
        depth: int,
        visited: set[str],
    ) -> ProofTree:
        """Recursively build a proof tree for *target_id*."""
        target_node = self._graph.get_node(target_id)
        goal_label = target_node.label if target_node else target_id[:8]

        if target_id in known_ids:
            return ProofTree(
                goal_id=target_id,
                goal_label=goal_label,
                achieved=True,
                confidence=1.0,
                depth=depth,
            )

        if depth >= self._max_depth or target_id in visited:
            return ProofTree(
                goal_id=target_id,
                goal_label=goal_label,
                achieved=False,
                unresolved_premises=[target_id],
                depth=depth,
            )

        visited = visited | {target_id}

        best_tree: ProofTree | None = None
        best_conf = 0.0

        for rule in self._rules:
            derivations = rule.find_derivation(target_id, self._graph)
            for derivation in derivations:
                if edge_label and derivation.context.get("edge_label") != edge_label:
                    continue
                tree, combined_conf = self._evaluate_derivation(
                    derivation, target_id, goal_label, known_ids,
                    edge_label, depth, visited, rule,
                )
                if combined_conf > best_conf:
                    best_conf = combined_conf
                    best_tree = tree

        if best_tree:
            return best_tree

        return ProofTree(
            goal_id=target_id,
            goal_label=goal_label,
            achieved=False,
            unresolved_premises=[target_id],
            depth=depth,
        )

    def _evaluate_derivation(
        self,
        derivation: RuleMatch,
        target_id: str,
        goal_label: str,
        known_ids: set[str],
        edge_label: str | None,
        depth: int,
        visited: set[str],
        rule: Rule,
    ) -> tuple[ProofTree, float]:
        """Evaluate a single rule derivation and build a sub-proof tree."""
        premise_ids = set(derivation.bindings.values())
        all_premises_satisfied = True
        sub_trees: list[ProofTree] = []
        sub_confidences: list[float] = []
        unresolved: list[str] = []

        for pid in premise_ids:
            sub = self._build_proof_tree(
                pid,
                known_ids,
                edge_label,
                depth + 1,
                visited,
            )
            sub_trees.append(sub)
            sub_confidences.append(sub.confidence)
            if not sub.achieved:
                all_premises_satisfied = False
                unresolved.extend(sub.unresolved_premises)

        rule_score = rule.score_match(derivation, self._graph)
        combined_conf = rule_score
        if sub_confidences:
            combined_conf *= min(sub_confidences)

        step = ProofStep(
            rule_name=rule.name,
            target_id=target_id,
            required_premises=list(premise_ids),
            match=derivation,
            confidence=combined_conf,
        )

        steps_flat: list[ProofStep] = [step]
        for st in sub_trees:
            steps_flat.extend(st.steps)

        tree = ProofTree(
            goal_id=target_id,
            goal_label=goal_label,
            achieved=all_premises_satisfied,
            steps=steps_flat,
            unresolved_premises=unresolved if not all_premises_satisfied else [],
            depth=depth,
            confidence=combined_conf,
        )
        return tree, combined_conf

    def _find_alternative_proofs(
        self,
        target_id: str,
        known_ids: set[str],
        edge_label: str | None,
        exclude_steps: list[ProofStep],
    ) -> list[ProofTree]:
        """Search for alternative proof paths excluding already-found steps."""
        exclude_rule_targets: set[tuple[str, str]] = set()
        for step in exclude_steps:
            exclude_rule_targets.add((step.rule_name, step.target_id))

        alternatives: list[ProofTree] = []
        for rule in self._rules:
            derivations = rule.find_derivation(target_id, self._graph)
            for derivation in derivations:
                if (rule.name, target_id) in exclude_rule_targets:
                    continue
                if edge_label and derivation.context.get("edge_label") != edge_label:
                    continue

                premise_ids = set(derivation.bindings.values())
                all_satisfied = all(pid in known_ids for pid in premise_ids)

                rule_score = rule.score_match(derivation, self._graph)
                step = ProofStep(
                    rule_name=rule.name,
                    target_id=target_id,
                    required_premises=list(premise_ids),
                    match=derivation,
                    confidence=rule_score,
                )

                target_node = self._graph.get_node(target_id)
                tree = ProofTree(
                    goal_id=target_id,
                    goal_label=target_node.label if target_node else target_id[:8],
                    achieved=all_satisfied,
                    steps=[step],
                    confidence=rule_score,
                )
                alternatives.append(tree)

                if len(alternatives) >= self._max_alternatives:
                    return alternatives

        alternatives.sort(key=lambda t: t.confidence, reverse=True)
        return alternatives[: self._max_alternatives]
