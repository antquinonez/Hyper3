"""Medical symptom timeline tracker using Hyper3's temporal reasoning.

Demonstrates Hyper3's unique capabilities:
- TemporalReasoner with Allen interval algebra (13 relations)
- N-ary hyperedges for doctor visits (visit observes multiple symptoms)
- Pure temporal reasoning (NO transitive relationships)
- Explainable results with Allen algebra terminology

Run: .venv/bin/python examples/showcase/medical_timeline/demo.py
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

    def find_all_temporal_relations(self) -> list[dict]:
        """Find all pairwise temporal relations between all symptoms.

        Returns:
            List of dicts with keys: symptom_a, symptom_b, relation.
        """
        relations = []
        symptoms = [n for n in self.mem.graph.nodes if "start" in n.data and "end" in n.data]

        for i, sym_a in enumerate(symptoms):
            for j, sym_b in enumerate(symptoms):
                if i >= j:
                    continue
                interval_a = self._get_interval(sym_a.label)
                interval_b = self._get_interval(sym_b.label)
                if not interval_a or not interval_b:
                    continue
                try:
                    rel = interval_a.relate_to(interval_b)
                    if rel and rel.value:
                        relations.append({
                            "symptom_a": sym_a.label,
                            "symptom_b": sym_b.label,
                            "relation": rel.value
                        })
                except Exception:
                    continue

        return relations

    def get_temporal_relation_frequency(self) -> dict[str, int]:
        """Count frequency of each Allen relation type.

        Returns:
            Dict mapping relation name to count.
        """
        relations = self.find_all_temporal_relations()
        frequency = {}
        for rel in relations:
            r = rel["relation"]
            frequency[r] = frequency.get(r, 0) + 1
        return dict(sorted(frequency.items(), key=lambda x: x[1], reverse=True))

    def get_symptom_cooccurrence(self) -> dict[str, list[str]]:
        """Find which symptoms appear together in the same visits.

        Returns:
            Dict mapping symptom to list of symptoms that co-occur in visits.
        """
        cooccurrence = {}

        symptoms = [n.label for n in self.mem.graph.nodes if "start" in n.data]

        for symptom in symptoms:
            cooccurring = []
            for node in self.mem.graph.nodes:
                if node.label.startswith("visit_"):
                    edges = self.mem.graph.incident_edges(node.id)
                    for edge in edges:
                        if edge.label == "observes":
                            observed = []
                            for tid in edge.target_ids:
                                n = self.mem.graph.get_node(tid)
                                if n:
                                    observed.append(n.label)
                            if symptom in observed and len(observed) > 1:
                                for other in observed:
                                    if other != symptom and other not in cooccurring:
                                        cooccurring.append(other)
            cooccurrence[symptom] = cooccurring

        return {k: v for k, v in cooccurrence.items() if v}

    def get_duration_analysis(self) -> dict:
        """Calculate duration statistics for all symptoms.

        Returns:
            Dict with min, max, avg, median durations in hours.
        """
        durations = []
        symptom_durations = {}

        for node in self.mem.graph.nodes:
            if "start" not in node.data or "end" not in node.data:
                continue
            interval = self._get_interval(node.label)
            if interval:
                duration_hours = (interval.end - interval.start) / 3600
                durations.append(duration_hours)
                symptom_durations[node.label] = round(duration_hours, 2)

        if not durations:
            return {}

        durations_sorted = sorted(durations)
        n = len(durations)
        avg = sum(durations) / n
        median = durations_sorted[n // 2] if n % 2 else (durations_sorted[n // 2 - 1] + durations_sorted[n // 2]) / 2

        return {
            "min_hours": round(min(durations), 2),
            "max_hours": round(max(durations), 2),
            "avg_hours": round(avg, 2),
            "median_hours": round(median, 2),
            "symptom_durations": symptom_durations
        }

    def get_overlap_matrix(self) -> list[dict]:
        """Find which symptom pairs have overlapping intervals.

        Returns:
            List of dicts with keys: symptom_a, symptom_b, overlap_hours.
        """
        overlaps = []
        symptoms = [n for n in self.mem.graph.nodes if "start" in n.data and "end" in n.data]

        for i, sym_a in enumerate(symptoms):
            for j, sym_b in enumerate(symptoms):
                if i >= j:
                    continue
                interval_a = self._get_interval(sym_a.label)
                interval_b = self._get_interval(sym_b.label)
                if not interval_a or not interval_b:
                    continue

                try:
                    rel = interval_a.relate_to(interval_b)
                    if rel and rel.value == "overlaps":
                        overlap_start = max(interval_a.start, interval_b.start)
                        overlap_end = min(interval_a.end, interval_b.end)
                        overlap_hours = (overlap_end - overlap_start) / 3600
                        overlaps.append({
                            "symptom_a": sym_a.label,
                            "symptom_b": sym_b.label,
                            "overlap_hours": round(overlap_hours, 2)
                        })
                except Exception:
                    continue

        return sorted(overlaps, key=lambda x: x["overlap_hours"], reverse=True)

    def detect_longer_causal_chains(self, min_length: int = 3) -> list[dict]:
        """Detect causal chains of specified minimum length.

        Args:
            min_length: Minimum chain length (default 3).

        Returns:
            List of dicts with chain, reason, length.
        """
        chains = []
        symptoms = [n for n in self.mem.graph.nodes if "start" in n.data and "end" in n.data]
        n = len(symptoms)

        if n < min_length:
            return chains

        visited_chains = {}

        def dfs(current_chain: list, last_idx: int):
            if len(current_chain) >= min_length:
                key = tuple(current_chain)
                if key not in visited_chains:
                    visited_chains[key] = True
                    reason_parts = []
                    for k in range(len(current_chain) - 1):
                        sym_a = current_chain[k]
                        sym_b = current_chain[k + 1]
                        reason_parts.append(f"{sym_a} → {sym_b}")
                    chains.append({
                        "chain": current_chain,
                        "reason": ", ".join(reason_parts),
                        "length": len(current_chain)
                    })

            for next_idx in range(last_idx + 1, n):
                sym_current = current_chain[-1]
                sym_next = symptoms[next_idx].label

                interval_current = self._get_interval(sym_current)
                interval_next = self._get_interval(sym_next)

                if not interval_current or not interval_next:
                    continue

                try:
                    rel = interval_current.relate_to(interval_next)
                    if rel and rel.value == "before":
                        dfs(current_chain + [sym_next], next_idx)
                except Exception:
                    continue

        for start_idx in range(n):
            dfs([symptoms[start_idx].label], start_idx)

        return sorted(chains, key=lambda x: x["length"], reverse=True)
