"""
NetworkX Comparison: Temporal Reasoning
========================================
Parallels Hyper3's intermediate/22_temporal_reasoning.py.

Implements Allen interval algebra (13 relations) from scratch using
plain Python and NetworkX, since no competing framework provides it.
Creates events with time intervals, computes Allen relations, detects
causal chains, and checks temporal consistency.

Hyper3 has TemporalReasoner with full Allen algebra, add_temporal_event(),
allen_relation(), temporal_query(), causal_chain(), and temporal
consistency checking built in.

Run: .venv/bin/python examples/comparison/nx_08_temporal.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import networkx as nx


class AllenRelation(Enum):
    EQUALS = "equals"
    PRECEDES = "precedes"
    PRECEDED_BY = "preceded_by"
    MEETS = "meets"
    MET_BY = "met_by"
    OVERLAPS = "overlaps"
    OVERLAPPED_BY = "overlapped_by"
    STARTS = "starts"
    STARTED_BY = "started_by"
    FINISHES = "finishes"
    FINISHED_BY = "finished_by"
    DURING = "during"
    CONTAINS = "contains"


@dataclass
class TimeInterval:
    start: float
    end: float

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError(f"start ({self.start}) must be < end ({self.end})")

    @property
    def duration(self) -> float:
        return self.end - self.start

    def relate_to(self, other: TimeInterval) -> AllenRelation:
        if abs(self.start - other.start) < 1e-10 and abs(self.end - other.end) < 1e-10:
            return AllenRelation.EQUALS
        if abs(self.end - other.start) < 1e-10:
            return AllenRelation.MEETS
        if abs(self.start - other.end) < 1e-10:
            return AllenRelation.MET_BY
        if abs(self.start - other.start) < 1e-10:
            if self.end < other.end:
                return AllenRelation.STARTS
            if self.end > other.end:
                return AllenRelation.STARTED_BY
        if abs(self.end - other.end) < 1e-10:
            if self.start > other.start:
                return AllenRelation.FINISHES
            if self.start < other.start:
                return AllenRelation.FINISHED_BY
        if self.end <= other.start:
            return AllenRelation.PRECEDES
        if self.start >= other.end:
            return AllenRelation.PRECEDED_BY
        if self.start < other.start < self.end <= other.end:
            return AllenRelation.OVERLAPS
        if other.start < self.start < other.end <= self.end:
            return AllenRelation.OVERLAPPED_BY
        if other.start < self.start and self.end < other.end:
            return AllenRelation.DURING
        if self.start < other.start and other.end < self.end:
            return AllenRelation.CONTAINS
        return AllenRelation.PRECEDES


def main() -> None:
    print("=" * 70)
    print("SECTION 1: DEFINE TEMPORAL EVENTS")
    print("=" * 70)

    events = {
        "outbreak_detected": TimeInterval(0.0, 1.0),
        "quarantine_issued": TimeInterval(1.0, 3.0),
        "supply_disruption": TimeInterval(2.0, 5.0),
        "vaccine_development": TimeInterval(3.0, 8.0),
        "travel_ban": TimeInterval(1.5, 4.0),
        "economic_impact": TimeInterval(4.0, 10.0),
        "recovery_begins": TimeInterval(8.0, 15.0),
        "second_wave": TimeInterval(12.0, 14.0),
        "herd_immunity": TimeInterval(14.0, 20.0),
    }

    print(f"events defined: {len(events)}")
    print(f"\n{'event':>22} {'start':>8} {'end':>8} {'duration':>10}")
    print("-" * 52)
    for name in sorted(events):
        iv = events[name]
        print(f"{name:>22} {iv.start:>8.1f} {iv.end:>8.1f} {iv.duration:>10.1f}")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.add_temporal_event(name, start=t, end=t) on a HypergraphMemory")

    print()
    print("=" * 70)
    print("SECTION 2: BUILD CAUSAL NETWORK IN NETWORKX")
    print("=" * 70)

    G = nx.DiGraph()
    for name in events:
        G.add_node(name, interval=events[name])

    causal_edges = [
        ("outbreak_detected", "quarantine_issued", "causes"),
        ("outbreak_detected", "travel_ban", "causes"),
        ("quarantine_issued", "supply_disruption", "causes"),
        ("travel_ban", "economic_impact", "causes"),
        ("supply_disruption", "economic_impact", "contributes_to"),
        ("vaccine_development", "recovery_begins", "enables"),
        ("economic_impact", "recovery_begins", "delays"),
        ("recovery_begins", "herd_immunity", "enables"),
        ("second_wave", "recovery_begins", "interrupts"),
    ]
    for src, tgt, label in causal_edges:
        G.add_edge(src, tgt, label=label)

    print(f"nodes: {G.number_of_nodes()}, edges: {G.number_of_edges()}")
    print("\ncausal edges:")
    for u, v, data in G.edges(data=True):
        print(f"  {u} -[{data['label']}]-> {v}")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.link(src, tgt, label='causes') with temporal events already stored")

    print()
    print("=" * 70)
    print("SECTION 3: ALLEN INTERVAL RELATIONS")
    print("=" * 70)

    print("\n(manual implementation of Allen's 13 interval relations)")
    test_pairs = [
        ("outbreak_detected", "quarantine_issued"),
        ("quarantine_issued", "travel_ban"),
        ("supply_disruption", "economic_impact"),
        ("recovery_begins", "second_wave"),
        ("vaccine_development", "recovery_begins"),
    ]
    print(f"\n{'event_a':>22} {'event_b':>22} {'relation':>15}")
    print("-" * 62)
    for a, b in test_pairs:
        rel = events[a].relate_to(events[b])
        print(f"{a:>22} {b:>22} {rel.value:>15}")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.allen_relation(a, b)  -> AllenRelation enum")
    print("No framework other than Hyper3 provides Allen interval algebra natively.")

    print()
    print("=" * 70)
    print("SECTION 4: CAUSAL CHAIN DETECTION")
    print("=" * 70)

    print("\n(traverse causal edges following temporal ordering)")
    sources = [n for n in G.nodes if G.in_degree(n) == 0]
    sinks = [n for n in G.nodes if G.out_degree(n) == 0]
    chains = []
    for src in sources:
        for sink in sinks:
            if src != sink:
                for path in nx.all_simple_paths(G, src, sink):
                    if len(path) >= 3:
                        chains.append(path)
    for node in G.nodes:
        for path in nx.all_simple_paths(G, node, [s for s in sinks if s != node]):
            if len(path) >= 3 and path not in chains:
                chains.append(path)

    chains.sort(key=lambda c: len(c), reverse=True)
    print(f"\ncausal chains found: {len(chains)}")
    for i, chain in enumerate(chains):
        print(f"  chain {i+1}: {' -> '.join(chain)}")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.temporal.detect_causal_chains()  -> list of node_id lists")

    print()
    print("=" * 70)
    print("SECTION 5: TEMPORAL CONSISTENCY CHECK")
    print("=" * 70)

    print("\n(check that causes precede effects temporally)")
    inconsistencies = []
    for u, v, data in G.edges(data=True):
        iv_u = events[u]
        iv_v = events[v]
        if data["label"] == "causes" and iv_u.start > iv_v.start:
            inconsistencies.append(
                f"{u} (start={iv_u.start}) causes {v} (start={iv_v.start}) "
                f"but effect starts first"
            )

    print(f"\ntemporal consistency: {'consistent' if not inconsistencies else 'inconsistent'}")
    if inconsistencies:
        for inc in inconsistencies:
            print(f"  inconsistency: {inc}")
    else:
        print("  no temporal contradictions detected")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.temporal.check_constraint_consistency()  -> list of inconsistency strings")

    print()
    print("=" * 70)
    print("SECTION 6: TEMPORAL PROXIMITY QUERY")
    print("=" * 70)

    print("\n(find events overlapping or adjacent to a reference event)")
    reference = "supply_disruption"
    ref_iv = events[reference]
    nearby = []
    for name, iv in events.items():
        if name == reference:
            continue
        rel = ref_iv.relate_to(iv)
        if rel in (
            AllenRelation.OVERLAPS,
            AllenRelation.OVERLAPPED_BY,
            AllenRelation.MEETS,
            AllenRelation.MET_BY,
            AllenRelation.DURING,
            AllenRelation.CONTAINS,
            AllenRelation.EQUALS,
        ):
            nearby.append((name, rel.value))

    print(f"\nevents temporally overlapping/adjacent to '{reference}':")
    for name, rel in sorted(nearby):
        print(f"  {name}: {rel}")

    print()
    print("=" * 70)
    print("SECTION 7: WHAT HYPER3 HAS THAT NETWORKX LACKS")
    print("=" * 70)
    print("""
Hyper3 temporal features not available in any competing framework:
  - TemporalReasoner: built-in temporal reasoning subsystem
  - add_temporal_event(): attach time intervals to graph nodes
  - allen_relation(): compute any of the 13 Allen interval relations
    between two events with a single method call
  - temporal_query(): find events by temporal criteria (overlapping,
    during, before, after, etc.)
  - detect_causal_chains(): automatically find chronological paths
    through causally-linked events
  - check_constraint_consistency(): verify temporal ordering of
    cause-effect relationships
  - Integration with reasoning: combine temporal knowledge with
    inference rules (e.g., TransitiveRule on temporal edges)
  - Integration with provenance: trace when and how conclusions
    were derived, with temporal context
""")


if __name__ == "__main__":
    main()
