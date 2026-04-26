from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph


@dataclass
class FeedbackSignal:
    signal_type: str
    node_id: str
    outcome: bool
    confidence: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


class OperationFeedback:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._signals: list[FeedbackSignal] = []
        self._collapse_stats: dict[str, dict[str, int]] = {}
        self._retrieval_stats: dict[str, dict[str, int]] = {}
        self._inference_stats: dict[str, dict[str, int]] = {}
        self._evolution_fitness_history: list[float] = []

    def record_collapse_outcome(
        self, qs_id: str, selected_node_id: str, correct: bool | None = None,
    ) -> None:
        stats = self._collapse_stats.setdefault(qs_id, {"correct": 0, "incorrect": 0, "unknown": 0})
        if correct is True:
            stats["correct"] += 1
        elif correct is False:
            stats["incorrect"] += 1
        else:
            stats["unknown"] += 1
        self._signals.append(FeedbackSignal(
            signal_type="collapse",
            node_id=selected_node_id,
            outcome=correct is True,
            confidence=1.0 if correct is not None else 0.5,
            context={"qs_id": qs_id},
            timestamp=time.time(),
        ))

    def record_retrieval_outcome(
        self, query: str, relevant_ids: set[str], irrelevant_ids: set[str],
    ) -> None:
        stats = self._retrieval_stats.setdefault(query, {"relevant": 0, "irrelevant": 0})
        stats["relevant"] += len(relevant_ids)
        stats["irrelevant"] += len(irrelevant_ids)
        for nid in relevant_ids:
            self._signals.append(FeedbackSignal(
                signal_type="retrieval_relevant",
                node_id=nid,
                outcome=True,
                context={"query": query},
                timestamp=time.time(),
            ))
        for nid in irrelevant_ids:
            self._signals.append(FeedbackSignal(
                signal_type="retrieval_irrelevant",
                node_id=nid,
                outcome=False,
                context={"query": query},
                timestamp=time.time(),
            ))

    def record_inference_outcome(self, edge_id: str, accepted: bool) -> None:
        key = edge_id
        stats = self._inference_stats.setdefault(key, {"accepted": 0, "rejected": 0})
        if accepted:
            stats["accepted"] += 1
        else:
            stats["rejected"] += 1
        self._signals.append(FeedbackSignal(
            signal_type="inference",
            node_id=edge_id,
            outcome=accepted,
            timestamp=time.time(),
        ))

    def record_evolution_outcome(self, fitness: float) -> None:
        self._evolution_fitness_history.append(fitness)
        self._signals.append(FeedbackSignal(
            signal_type="evolution",
            node_id="",
            outcome=fitness > 0.5,
            confidence=fitness,
            timestamp=time.time(),
        ))

    def get_reinforced_nodes(self, min_signals: int = 2) -> set[str]:
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
        return list(self._signals)

    @property
    def signal_count(self) -> int:
        return len(self._signals)

    def collapse_accuracy(self) -> float:
        total_correct = sum(s.get("correct", 0) for s in self._collapse_stats.values())
        total_incorrect = sum(s.get("incorrect", 0) for s in self._collapse_stats.values())
        total = total_correct + total_incorrect
        if total == 0:
            return 0.5
        return total_correct / total

    def retrieval_precision(self) -> float:
        total_relevant = sum(s.get("relevant", 0) for s in self._retrieval_stats.values())
        total_irrelevant = sum(s.get("irrelevant", 0) for s in self._retrieval_stats.values())
        total = total_relevant + total_irrelevant
        if total == 0:
            return 0.5
        return total_relevant / total

    def inference_acceptance_rate(self) -> float:
        total_accepted = sum(s.get("accepted", 0) for s in self._inference_stats.values())
        total_rejected = sum(s.get("rejected", 0) for s in self._inference_stats.values())
        total = total_accepted + total_rejected
        if total == 0:
            return 0.5
        return total_accepted / total
