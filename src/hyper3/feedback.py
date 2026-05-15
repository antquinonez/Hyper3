"""OperationFeedback: outcome tracking across sampling, retrieval, inference."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import CorrelatedNodeInfo, FeedbackSummaryResult


@dataclass
class FeedbackSignal:
    """A single recorded outcome from a graph operation."""

    signal_type: str
    node_id: str
    outcome: bool
    confidence: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


class OperationFeedback:
    """Track outcomes of collapse, retrieval, inference, and evolution operations."""

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize with an empty signal history.

        Args:
            graph: The hypergraph this feedback is associated with.
        """
        self._graph = graph
        self._signals: list[FeedbackSignal] = []
        self._collapse_stats: dict[str, dict[str, int]] = {}
        self._retrieval_stats: dict[str, dict[str, int]] = {}
        self._inference_stats: dict[str, dict[str, int]] = {}
        self._evolution_fitness_history: list[float] = []

    def record_collapse_outcome(
        self,
        qs_id: str,
        selected_node_id: str,
        correct: bool | None = None,
    ) -> None:
        """Record the outcome of a quantum collapse.

        Args:
            qs_id: ID of the quantum state that was collapsed.
            selected_node_id: ID of the node selected by the collapse.
            correct: ``True`` if the collapse was correct, ``False`` if incorrect,
                or ``None`` if unknown.
        """
        stats = self._collapse_stats.setdefault(qs_id, {"correct": 0, "incorrect": 0, "unknown": 0})
        if correct is True:
            stats["correct"] += 1
        elif correct is False:
            stats["incorrect"] += 1
        else:
            stats["unknown"] += 1
        self._signals.append(
            FeedbackSignal(
                signal_type="collapse",
                node_id=selected_node_id,
                outcome=correct is True,
                confidence=1.0 if correct is not None else 0.5,
                context={"qs_id": qs_id},
                timestamp=time.time(),
            )
        )

    def record_retrieval_outcome(
        self,
        query: str,
        relevant_ids: set[str],
        irrelevant_ids: set[str],
    ) -> None:
        """Record which retrieved nodes were relevant or irrelevant for a query.

        Args:
            query: The query string or identifier.
            relevant_ids: Set of node IDs judged relevant.
            irrelevant_ids: Set of node IDs judged irrelevant.
        """
        stats = self._retrieval_stats.setdefault(query, {"relevant": 0, "irrelevant": 0})
        stats["relevant"] += len(relevant_ids)
        stats["irrelevant"] += len(irrelevant_ids)
        for nid in relevant_ids:
            self._signals.append(
                FeedbackSignal(
                    signal_type="retrieval_relevant",
                    node_id=nid,
                    outcome=True,
                    context={"query": query},
                    timestamp=time.time(),
                )
            )
        for nid in irrelevant_ids:
            self._signals.append(
                FeedbackSignal(
                    signal_type="retrieval_irrelevant",
                    node_id=nid,
                    outcome=False,
                    context={"query": query},
                    timestamp=time.time(),
                )
            )

    def record_inference_outcome(self, edge_id: str, accepted: bool) -> None:
        """Record whether an inferred edge was accepted or rejected.

        Args:
            edge_id: ID of the inferred edge.
            accepted: ``True`` if accepted, ``False`` if rejected.
        """
        key = edge_id
        stats = self._inference_stats.setdefault(key, {"accepted": 0, "rejected": 0})
        if accepted:
            stats["accepted"] += 1
        else:
            stats["rejected"] += 1
        self._signals.append(
            FeedbackSignal(
                signal_type="inference",
                node_id=edge_id,
                outcome=accepted,
                timestamp=time.time(),
            )
        )

    def record_evolution_outcome(self, fitness: float) -> None:
        """Record an evolution cycle fitness measurement.

        Args:
            fitness: The fitness score produced by the evolution cycle.
        """
        self._evolution_fitness_history.append(fitness)
        self._signals.append(
            FeedbackSignal(
                signal_type="evolution",
                node_id="",
                outcome=fitness > 0.5,
                confidence=fitness,
                timestamp=time.time(),
            )
        )

    def get_reinforced_nodes(self, min_signals: int = 2) -> set[str]:
        """Return node IDs with a majority of positive outcome signals.

        Args:
            min_signals: Minimum number of signals required to consider a node.

        Returns:
            Set of node IDs with a positive rate above 50%.
        """
        node_outcomes: dict[str, list[bool]] = {}
        for signal in self._signals:
            if signal.signal_type in ("retrieval_relevant", "collapse"):
                node_outcomes.setdefault(signal.node_id, []).append(signal.outcome)
        reinforced: set[str] = set()
        for nid, outcomes in node_outcomes.items():
            if len(outcomes) >= min_signals:
                positive_rate = sum(1 for o in outcomes if o) / len(outcomes)
                if positive_rate > 0.5:
                    reinforced.add(nid)
        return reinforced

    def get_suppressed_nodes(self, min_signals: int = 2) -> set[str]:
        """Return node IDs that have been marked irrelevant enough times.

        Args:
            min_signals: Minimum number of irrelevant signals required.

        Returns:
            Set of node IDs meeting the suppression threshold.
        """
        node_outcomes: dict[str, list[bool]] = {}
        for signal in self._signals:
            if signal.signal_type == "retrieval_irrelevant":
                node_outcomes.setdefault(signal.node_id, []).append(True)
        suppressed: set[str] = set()
        for nid, outcomes in node_outcomes.items():
            if len(outcomes) >= min_signals:
                suppressed.add(nid)
        return suppressed

    def get_fitness_trend(self) -> str:
        """Analyze recent evolution fitness values for a trend.

        Returns:
            One of ``"improving"``, ``"declining"``, ``"stable"``, or
            ``"insufficient_data"``.
        """
        if len(self._evolution_fitness_history) < 2:
            return "insufficient_data"
        recent = self._evolution_fitness_history[-5:]
        slope = (recent[-1] - recent[0]) / len(recent)
        if slope > 0.02:
            return "improving"
        if slope < -0.02:
            return "declining"
        return "stable"

    @property
    def signals(self) -> list[FeedbackSignal]:
        """Copy of all recorded feedback signals."""
        return list(self._signals)

    @property
    def signal_count(self) -> int:
        """Total number of recorded feedback signals."""
        return len(self._signals)

    def collapse_accuracy(self) -> float:
        """Compute the fraction of collapse outcomes that were correct.

        Returns:
            Accuracy in [0, 1], or 0.5 if no outcomes recorded.
        """
        total_correct = sum(s.get("correct", 0) for s in self._collapse_stats.values())
        total_incorrect = sum(s.get("incorrect", 0) for s in self._collapse_stats.values())
        total = total_correct + total_incorrect
        if total == 0:
            return 0.5
        return total_correct / total

    def retrieval_precision(self) -> float:
        """Compute the fraction of retrieval results that were relevant.

        Returns:
            Precision in [0, 1], or 0.5 if no outcomes recorded.
        """
        total_relevant = sum(s.get("relevant", 0) for s in self._retrieval_stats.values())
        total_irrelevant = sum(s.get("irrelevant", 0) for s in self._retrieval_stats.values())
        total = total_relevant + total_irrelevant
        if total == 0:
            return 0.5
        return total_relevant / total

    def inference_acceptance_rate(self) -> float:
        """Compute the fraction of inferred edges that were accepted.

        Returns:
            Acceptance rate in [0, 1], or 0.5 if no outcomes recorded.
        """
        total_accepted = sum(s.get("accepted", 0) for s in self._inference_stats.values())
        total_rejected = sum(s.get("rejected", 0) for s in self._inference_stats.values())
        total = total_accepted + total_rejected
        if total == 0:
            return 0.5
        return total_accepted / total

    def cross_operation_summary(self) -> FeedbackSummaryResult:
        """Compute aggregate metrics across all operation types.

        Returns:
            FeedbackSummaryResult with per-operation metrics, overall health,
            and cross-operation correlations.
        """
        collapse_acc = self.collapse_accuracy()
        retrieval_prec = self.retrieval_precision()
        inference_acc = self.inference_acceptance_rate()
        trend = self.get_fitness_trend()

        health = (collapse_acc + retrieval_prec + inference_acc) / 3.0

        type_counts: dict[str, int] = {}
        for signal in self._signals:
            base_type = signal.signal_type.split("_")[0]
            type_counts[base_type] = type_counts.get(base_type, 0) + 1

        positive_by_node: dict[str, int] = {}
        total_by_node: dict[str, int] = {}
        for signal in self._signals:
            if signal.node_id:
                total_by_node[signal.node_id] = total_by_node.get(signal.node_id, 0) + 1
                if signal.outcome:
                    positive_by_node[signal.node_id] = positive_by_node.get(signal.node_id, 0) + 1

        multi_signal_nodes = {nid for nid, count in total_by_node.items() if count >= 3}
        correlated_nodes: dict[str, CorrelatedNodeInfo] = {}
        for nid in multi_signal_nodes:
            pos = positive_by_node.get(nid, 0)
            total = total_by_node[nid]
            correlated_nodes[nid] = CorrelatedNodeInfo(
                positive_rate=pos / total,
                signal_count=total,
                signal_types=list({s.signal_type.split("_")[0] for s in self._signals if s.node_id == nid}),
            )

        return FeedbackSummaryResult(
            collapse_accuracy=collapse_acc,
            retrieval_precision=retrieval_prec,
            inference_acceptance_rate=inference_acc,
            fitness_trend=trend,
            overall_health=health,
            signal_type_distribution=type_counts,
            total_signals=len(self._signals),
            correlated_nodes=correlated_nodes,
        )
