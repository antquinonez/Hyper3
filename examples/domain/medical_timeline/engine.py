"""Medical symptom timeline tracker using Hyper3's temporal reasoning.

Demonstrates Hyper3's unique capabilities:
- TemporalReasoner with Allen interval algebra (13 relations)
- N-ary hyperedges for doctor visits (visit observes multiple symptoms)
- Pure temporal reasoning (NO transitive relationships)
- Explainable results with Allen algebra terminology

Run: .venv/bin/python examples/domain/medical_timeline/demo.py
"""

from datetime import datetime

from hyper3 import HypergraphMemory
from hyper3.temporal import TimeInterval


class MedicalTimelineTracker:
    """Local-first medical symptom timeline tracker with temporal reasoning.

    Uses Hyper3's TemporalReasoner to analyze symptom intervals
    using Allen's interval algebra (before, after, overlaps, during, etc.).
    """

    def __init__(self):
        """Initialize tracker with HypergraphMemory."""
        self.mem = HypergraphMemory(evolve_interval=0)

    @staticmethod
    def _iso_to_timestamp(iso_str: str) -> float:
        """Convert ISO datetime string to timestamp (float)."""
        dt = datetime.fromisoformat(iso_str)
        return dt.timestamp()

    def _get_interval(self, symptom: str) -> TimeInterval | None:
        """Get TimeInterval for a symptom node."""
        node = self.mem.graph.get_node_by_label(symptom)
        if not node:
            return None
        if "start" not in node.data or "end" not in node.data:
            return None
        try:
            start_ts = self._iso_to_timestamp(node.data["start"])
            end_ts = self._iso_to_timestamp(node.data["end"])
            return TimeInterval(start=start_ts, end=end_ts)
        except (ValueError, TypeError):
            return None

    def add_symptom(self, name: str, start: str, end: str, **properties) -> str:
        """Add symptom with time interval.

        Args:
            name: Symptom label.
            start: Start time (ISO format string).
            end: End time (ISO format string).
            **properties: Metadata (severity, etc.).

        Returns:
            Symptom label.
        """
        if not self.mem.has_node(name):
            data = {"start": start, "end": end, **properties}
            self.mem.store(name, data=data)
        return name

    def add_visit(self, visit_id: str, symptoms: list[str], **properties) -> str:
        """Add doctor visit as n-ary hyperedge connecting to observed symptoms.

        Args:
            visit_id: Visit identifier.
            symptoms: List of symptom labels observed.
            **properties: Visit metadata (doctor, time, etc.).

        Returns:
            Visit ID.
        """
        if not self.mem.has_node(visit_id):
            self.mem.store(visit_id, data=properties)

        for symptom in symptoms:
            if not self.mem.has_node(symptom):
                self.mem.store(symptom)

        self.mem.relate_hyperedge(
            sources={visit_id},
            targets=set(symptoms),
            label="observes"
        )

        return visit_id

    def check_temporal_relation(self, symptom_a: str, symptom_b: str) -> str | None:
        """Check Allen interval relation between two symptoms.

        Args:
            symptom_a: First symptom label.
            symptom_b: Second symptom label.

        Returns:
            Allen relation string (e.g., "OVERLAPS", "BEFORE", "DURING")
            or None if nodes not found.
        """
        interval_a = self._get_interval(symptom_a)
        interval_b = self._get_interval(symptom_b)

        if not interval_a or not interval_b:
            return None

        try:
            relation = interval_a.relate_to(interval_b)
            return relation.value if relation else None
        except Exception:
            return None

    def find_overlapping_symptoms(self, symptom: str) -> list[str]:
        """Find all symptoms whose intervals overlap with target symptom.

        Args:
            symptom: Target symptom label.

        Returns:
            List of symptom labels that overlap with target.
        """
        overlapping = []
        target_interval = self._get_interval(symptom)

        if not target_interval:
            return overlapping

        for node in self.mem.graph.nodes:
            if node.label == symptom:
                continue
            if "start" not in node.data or "end" not in node.data:
                continue

            other_interval = self._get_interval(node.label)
            if not other_interval:
                continue

            try:
                rel = target_interval.relate_to(other_interval)
                if rel and rel.value in (
                    "overlaps", "overlapped_by", "contains",
                    "during", "starts", "finishes", "equals"
                ):
                    overlapping.append(node.label)
            except Exception:
                continue

        return overlapping

    def detect_causal_chains(self) -> list[dict]:
        """Detect potential causal chains: A before B, B before C.

        Returns:
            List of dicts with keys: chain, reason.
        """
        chains = []
        symptoms = [n for n in self.mem.graph.nodes if "start" in n.data and "end" in n.data]

        for i, sym_a in enumerate(symptoms):
            for j, sym_b in enumerate(symptoms):
                if i >= j:
                    continue
                try:
                    interval_a = self._get_interval(sym_a.label)
                    interval_b = self._get_interval(sym_b.label)
                    if not interval_a or not interval_b:
                        continue
                    rel_ab = interval_a.relate_to(interval_b)
                    if not rel_ab or rel_ab.value != "before":
                        continue

                    for sym_c in symptoms:
                        if sym_c.label in (sym_a.label, sym_b.label):
                            continue
                        interval_c = self._get_interval(sym_c.label)
                        if not interval_c:
                            continue
                        try:
                            rel_bc = interval_b.relate_to(interval_c)
                            if rel_bc and rel_bc.value == "before":
                                chains.append({
                                    "chain": [sym_a.label, sym_b.label, sym_c.label],
                                    "reason": f"{sym_a.label} ends before {sym_b.label} starts, "
                                              f"{sym_b.label} ends before {sym_c.label} starts"
                                })
                        except Exception:
                            continue
                except Exception:
                    continue

        return chains

    def explain_temporal_relation(self, symptom_a: str, symptom_b: str) -> dict | None:
        """Explain WHY two symptoms have their temporal relation.

        Args:
            symptom_a: First symptom label.
            symptom_b: Second symptom label.

        Returns:
            Dict with relation, intervals, reason, or None if not found.
        """
        interval_a = self._get_interval(symptom_a)
        interval_b = self._get_interval(symptom_b)

        if not interval_a or not interval_b:
            return None

        try:
            relation = interval_a.relate_to(interval_b)

            if not relation:
                return None

            reason_map = {
                "before": f"{symptom_a} ends before {symptom_b} starts",
                "after": f"{symptom_a} starts after {symptom_b} ends",
                "overlaps": f"{symptom_a} starts before {symptom_b} and ends after {symptom_b} starts",
                "overlapped_by": f"{symptom_a} starts after {symptom_b} and ends before {symptom_b} ends",
                "contains": f"{symptom_a} starts before {symptom_b} and ends after {symptom_b} ends",
                "during": f"{symptom_a} starts after {symptom_b} and ends before {symptom_b} ends",
                "starts": f"{symptom_a} starts when {symptom_b} starts and ends before {symptom_b} ends",
                "started_by": f"{symptom_a} starts when {symptom_b} starts and ends after {symptom_b} ends",
                "finishes": f"{symptom_a} starts after {symptom_b} starts and ends when {symptom_b} ends",
                "finished_by": f"{symptom_a} starts before {symptom_b} starts and ends when {symptom_b} ends",
                "equals": f"{symptom_a} and {symptom_b} have identical intervals",
                "meets": f"{symptom_a} ends when {symptom_b} starts",
                "met_by": f"{symptom_a} starts when {symptom_b} ends",
            }

            return {
                "relation": relation.value,
                "allen_relation": relation.value,
                f"{symptom_a}_interval": f"[{interval_a.start}, {interval_a.end}]",
                f"{symptom_b}_interval": f"[{interval_b.start}, {interval_b.end}]",
                "reason": reason_map.get(relation.value, f"Relation is {relation.value}"),
            }
        except Exception:
            return None

    def get_symptom_info(self, symptom: str) -> dict | None:
        """Get symptom metadata (interval, severity, etc.).

        Args:
            symptom: Symptom label.

        Returns:
            Dict with symptom data, or None if not found.
        """
        node = self.mem.graph.get_node_by_label(symptom)
        return node.data if node else None
