"""Medical symptom timeline tracker using Hyper3's temporal reasoning.

Demonstrates Hyper3's native temporal APIs:
- mem.add_temporal_event() for registering symptom intervals
- mem.allen_relation() for Allen interval algebra (13 relations)
- mem.temporal_query() for finding overlapping/before/after events
- mem.temporal.detect_causal_chains() for causal chain detection
- N-ary hyperedges for doctor visits (visit observes multiple symptoms)

Run: .venv/bin/python examples/showcase/domain/medical_timeline/demo.py
"""

from datetime import datetime

from hyper3 import HypergraphMemory


class MedicalTimelineTracker:
    """Local-first medical symptom timeline tracker with temporal reasoning.

    Uses Hyper3's TemporalReasoner via mem.add_temporal_event(),
    mem.allen_relation(), and mem.temporal_query() to analyze symptom
    intervals using Allen's interval algebra.
    """

    def __init__(self) -> None:
        self.mem = HypergraphMemory(evolve_interval=0)

    @staticmethod
    def _iso_to_timestamp(iso_str: str) -> float:
        dt = datetime.fromisoformat(iso_str)
        return dt.timestamp()

    def add_symptom(self, name: str, start: str, end: str, **properties) -> str:
        """Add symptom with time interval using mem.add_temporal_event().

        Args:
            name: Symptom label.
            start: Start time (ISO format string).
            end: End time (ISO format string).
            **properties: Metadata (severity, etc.).

        Returns:
            Symptom label.
        """
        if not self.mem.has(name):
            start_ts = self._iso_to_timestamp(start)
            end_ts = self._iso_to_timestamp(end)
            if end_ts <= start_ts:
                raise ValueError(f"end must be after start for symptom '{name}'")
            data = {"start": start, "end": end, **properties}
            self.mem.add(name, data=data)
            self.mem.add_temporal_event(name, start=start_ts, end=end_ts, **properties)
        return name

    def add_visit(self, visit_id: str, symptoms: list[str], **properties) -> str:
        """Add doctor visit as n-ary hyperedge connecting to observed symptoms.

        Args:
            visit_id: Visit identifier.
            symptoms: List of symptom labels observed.
            **properties: Visit metadata (doctor, time, etc).

        Returns:
            Visit ID.
        """
        if not self.mem.has(visit_id):
            self.mem.add(visit_id, data=properties)

        for symptom in symptoms:
            if not self.mem.has(symptom):
                self.mem.add(symptom)

        self.mem.link_hyper(
            sources={visit_id},
            targets=set(symptoms),
            label="observes",
        )

        return visit_id

    def check_temporal_relation(self, symptom_a: str, symptom_b: str) -> str | None:
        """Check Allen interval relation between two symptoms.

        Uses mem.allen_relation() instead of manual interval comparison.

        Args:
            symptom_a: First symptom label.
            symptom_b: Second symptom label.

        Returns:
            Allen relation string (e.g., "overlaps", "before", "during")
            or None if nodes not found.
        """
        relation = self.mem.allen_relation(symptom_a, symptom_b)
        return relation.value if relation else None

    def find_overlapping_symptoms(self, symptom: str) -> list[str]:
        """Find all symptoms whose intervals overlap with target symptom.

        Uses mem.temporal_query(relation="overlapping") instead of
        manual iteration over all graph nodes.

        Args:
            symptom: Target symptom label.

        Returns:
            List of symptom labels that overlap with target.
        """
        matches = self.mem.temporal_query(symptom, relation="overlapping")
        return sorted({m.label for m in matches})

    def explain_temporal_relation(self, symptom_a: str, symptom_b: str) -> dict | None:
        """Explain WHY two symptoms have their temporal relation.

        Uses mem.allen_relation() for the relation computation.

        Args:
            symptom_a: First symptom label.
            symptom_b: Second symptom label.

        Returns:
            Dict with relation, intervals, reason, or None if not found.
        """
        relation = self.mem.allen_relation(symptom_a, symptom_b)
        if not relation:
            return None

        node_a = self.mem.engine.graph.get_node_by_label(symptom_a)
        node_b = self.mem.engine.graph.get_node_by_label(symptom_b)
        if not node_a or not node_b:
            return None

        event_a = self.mem.temporal.get_event(symptom_a)
        event_b = self.mem.temporal.get_event(symptom_b)
        if not event_a or not event_b:
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
            f"{symptom_a}_interval": f"[{event_a.interval.start}, {event_a.interval.end}]",
            f"{symptom_b}_interval": f"[{event_b.interval.start}, {event_b.interval.end}]",
            "reason": reason_map.get(relation.value, f"Relation is {relation.value}"),
        }

    def get_symptom_info(self, symptom: str) -> dict | None:
        node = self.mem.engine.graph.get_node_by_label(symptom)
        return node.data if node else None

    def find_all_temporal_relations(self) -> list[dict]:
        """Find all pairwise temporal relations using mem.temporal.infer_constraints().

        Returns:
            List of dicts with keys: symptom_a, symptom_b, relation.
        """
        constraints = self.mem.temporal.infer_constraints()
        relations = []
        for c in constraints:
            label_a = self._event_id_to_label(c.event_a_id)
            label_b = self._event_id_to_label(c.event_b_id)
            if label_a and label_b:
                relations.append({
                    "symptom_a": label_a,
                    "symptom_b": label_b,
                    "relation": c.relation.value,
                })
        return relations

    def get_temporal_relation_frequency(self) -> dict[str, int]:
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
        cooccurrence: dict[str, set[str]] = {}
        for edge in self.mem.engine.graph.edges:
            if edge.label != "observes":
                continue
            observed: list[str] = []
            for tid in edge.target_ids:
                node = self.mem.engine.graph.get_node(tid)
                if node is not None:
                    observed.append(node.label)
            for symptom in observed:
                cooccurrence.setdefault(symptom, set())
                for other in observed:
                    if other != symptom:
                        cooccurrence[symptom].add(other)
        return {k: sorted(v) for k, v in sorted(cooccurrence.items()) if v}

    def get_duration_analysis(self) -> dict:
        """Calculate duration statistics for all symptoms.

        Uses temporal events for accurate duration computation.

        Returns:
            Dict with min, max, avg, median durations in hours.
        """
        durations = []
        symptom_durations = {}

        for event in self.mem.temporal.events:
            duration_hours = event.interval.duration / 3600
            durations.append(duration_hours)
            symptom_durations[event.label] = round(duration_hours, 2)

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
            "symptom_durations": symptom_durations,
        }

    def get_overlap_matrix(self) -> list[dict]:
        """Find which symptom pairs have overlapping intervals.

        Uses mem.allen_relation() for relation classification.

        Returns:
            List of dicts with keys: symptom_a, symptom_b, overlap_hours.
        """
        overlaps = []
        events = self.mem.temporal.events
        for i, ev_a in enumerate(events):
            for j, ev_b in enumerate(events):
                if i >= j:
                    continue
                rel = ev_a.interval.relate_to(ev_b.interval)
                if rel and rel.value == "overlaps":
                    overlap_start = max(ev_a.interval.start, ev_b.interval.start)
                    overlap_end = min(ev_a.interval.end, ev_b.interval.end)
                    overlap_hours = (overlap_end - overlap_start) / 3600
                    overlaps.append({
                        "symptom_a": ev_a.label,
                        "symptom_b": ev_b.label,
                        "overlap_hours": round(overlap_hours, 2),
                    })
        return sorted(overlaps, key=lambda x: x["overlap_hours"], reverse=True)

    def detect_longer_causal_chains(self, min_length: int = 3) -> list[dict]:
        """Detect causal chains of specified minimum length.

        Uses mem.temporal.detect_causal_chains() for efficient enumeration.

        Args:
            min_length: Minimum chain length (default 3).

        Returns:
            List of dicts with chain, reason, length.
        """
        raw_chains = self.mem.temporal.detect_causal_chains(
            min_chain_length=min_length, max_chains=100
        )
        results = []
        for chain in raw_chains:
            labels = self._event_ids_to_labels(chain)
            if len(labels) >= min_length:
                reason_parts = [f"{labels[k]} -> {labels[k+1]}" for k in range(len(labels) - 1)]
                results.append({
                    "chain": labels,
                    "reason": ", ".join(reason_parts),
                    "length": len(labels),
                })
        return sorted(results, key=lambda x: x["length"], reverse=True)

    def _event_id_to_label(self, event_id: str) -> str:
        event = self.mem.temporal.get_event(event_id)
        if event:
            return event.label
        node = self.mem.engine.graph.get_node(event_id)
        return node.label if node else event_id

    def _event_ids_to_labels(self, event_ids: list[str]) -> list[str]:
        return [self._event_id_to_label(eid) for eid in event_ids]
