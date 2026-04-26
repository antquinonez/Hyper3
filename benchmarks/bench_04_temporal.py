"""
Bench 4: Temporal Reasoning
============================

Compares Hyper3's Allen interval algebra implementation against
simpler baseline approaches for temporal relation detection,
causal chain detection, and constraint checking.

Systems compared:
  1. Hyper3 TemporalReasoner (full Allen algebra, 13 relations)
  2. Simple overlap check (before/after/overlap only)
  3. Manual date-range comparison (what most code does)

Metrics:
  - Relation accuracy: correct Allen relations identified
  - Chain detection: causal chains found
  - Constraint violation detection
  - Time

Ground truth: manually verified temporal relations for a project schedule.

Run:
    .venv/bin/python benchmarks/bench_04_temporal.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyper3 import TemporalReasoner, AllenRelation, Hypergraph
from shared import Timer, print_header, print_comparison_table


def simple_overlap(start1: float, end1: float, start2: float, end2: float) -> str:
    if end1 <= start2:
        return "before"
    if start1 >= end2:
        return "after"
    if start1 == start2 and end1 == end2:
        return "equals"
    if start1 <= start2 and end1 >= end2:
        return "contains"
    if start1 >= start2 and end1 <= end2:
        return "during"
    return "overlaps"


def manual_date_check(events: list[tuple[str, float, float]], query: str) -> list[str]:
    results = []
    for name, s, e in events:
        rel = simple_overlap(events[0][1], events[0][2], s, e)
        if query == "overlapping" and rel not in ("before", "after"):
            results.append(name)
        elif query == "before" and rel == "before":
            results.append(name)
        elif query == "after" and rel == "after":
            results.append(name)
    return results


EVENTS = [
    ("requirements", 0, 3),
    ("design", 2, 6),
    ("prototype", 5, 8),
    ("backend_dev", 6, 14),
    ("frontend_dev", 8, 13),
    ("integration", 13, 16),
    ("testing", 14, 18),
    ("staging", 17, 19),
    ("uat", 18, 21),
    ("deployment", 20, 22),
    ("monitoring", 21, 26),
    ("handoff", 24, 26),
]

ALLEN_RELATION_COUNT = 13

GROUND_TRUTH_PAIRS: dict[tuple[str, str], str] = {
    ("requirements", "design"): "overlaps",
    ("requirements", "prototype"): "before",
    ("design", "prototype"): "overlaps",
    ("design", "backend_dev"): "overlaps",
    ("prototype", "backend_dev"): "overlaps",
    ("backend_dev", "frontend_dev"): "overlaps",
    ("backend_dev", "integration"): "before",
    ("frontend_dev", "integration"): "before",
    ("integration", "testing"): "overlaps",
    ("testing", "staging"): "overlaps",
    ("staging", "uat"): "overlaps",
    ("uat", "deployment"): "before",
    ("deployment", "monitoring"): "overlaps",
    ("monitoring", "handoff"): "overlaps",
    ("requirements", "deployment"): "before",
    ("backend_dev", "testing"): "overlaps",
}


def main() -> None:
    print_header("Bench 4: Temporal Reasoning")

    print(f"\n  Events: {len(EVENTS)}")
    print(f"  Ground truth pairs: {len(GROUND_TRUTH_PAIRS)}")

    # --- Setup Hyper3 ---
    tr = TemporalReasoner(Hypergraph())
    for name, start, end in EVENTS:
        tr.add_event(name, label=name, start=start, end=end)

    # --- Setup baseline ---
    event_dict = {name: (s, e) for name, s, e in EVENTS}

    # --- Allen Relation Accuracy ---
    print_header("Allen Relation Accuracy")

    h3_correct = 0
    baseline_correct = 0
    total = 0
    h3_time = 0.0
    bl_time = 0.0

    relation_detail: list[list[str]] = []

    for (a_name, b_name), true_rel in GROUND_TRUTH_PAIRS.items():
        a_event = tr.get_event(a_name)
        b_event = tr.get_event(b_name)
        if not a_event or not b_event:
            continue

        total += 1

        with Timer() as t_h3:
            h3_rel = a_event.interval.relate_to(b_event.interval)
        h3_time += t_h3.elapsed

        with Timer() as t_bl:
            bl_rel = simple_overlap(
                a_event.interval.start, a_event.interval.end,
                b_event.interval.start, b_event.interval.end,
            )
        bl_time += t_bl.elapsed

        h3_match = h3_rel.value == true_rel
        bl_match = bl_rel == true_rel

        if h3_match:
            h3_correct += 1
        if bl_match:
            baseline_correct += 1

        relation_detail.append([
            f"{a_name} -> {b_name}",
            true_rel,
            h3_rel.value,
            "Y" if h3_match else "N",
            bl_rel,
            "Y" if bl_match else "N",
        ])

    detail_headers = ["Pair", "Truth", "H3", "H3?", "Simple", "Simple?"]
    print_comparison_table(detail_headers, relation_detail)

    h3_acc = h3_correct / total if total > 0 else 0
    bl_acc = baseline_correct / total if total > 0 else 0

    print(f"\n  H3 accuracy: {h3_correct}/{total} ({h3_acc:.1%})  time: {h3_time*1000:.1f}ms")
    print(f"  Simple accuracy: {baseline_correct}/{total} ({bl_acc:.1%})  time: {bl_time*1000:.1f}ms")

    # --- Relation Granularity ---
    print_header("Relation Granularity")
    all_h3_rels: set[str] = set()
    all_bl_rels: set[str] = set()
    for i, (name_a, s_a, e_a) in enumerate(EVENTS):
        for j, (name_b, s_b, e_b) in enumerate(EVENTS):
            if i == j:
                continue
            a_ev = tr.get_event(name_a)
            b_ev = tr.get_event(name_b)
            if a_ev and b_ev:
                all_h3_rels.add(a_ev.interval.relate_to(b_ev.interval).value)
            all_bl_rels.add(simple_overlap(s_a, e_a, s_b, e_b))

    print(f"  Allen algebra produces: {len(all_h3_rels)} distinct relations")
    print(f"    Relations: {sorted(all_h3_rels)}")
    print(f"  Simple overlap produces: {len(all_bl_rels)} distinct relations")
    print(f"    Relations: {sorted(all_bl_rels)}")
    print(f"  Allen algebra supports {ALLEN_RELATION_COUNT} relations total")
    print(f"  Information loss from simplification: {ALLEN_RELATION_COUNT - len(all_bl_rels)} relations indistinguishable")

    # --- Causal Chain Detection ---
    print_header("Causal Chain Detection")
    with Timer() as t_h3:
        h3_chains = tr.detect_causal_chains(min_chain_length=3)

    bl_chains: list[list[str]] = []
    with Timer() as t_bl:
        sorted_events = sorted(EVENTS, key=lambda x: x[1])
        current_chain = [sorted_events[0][0]]
        for i in range(1, len(sorted_events)):
            prev_end = sorted_events[i-1][2]
            curr_start = sorted_events[i][1]
            if curr_start <= prev_end:
                current_chain.append(sorted_events[i][0])
            else:
                if len(current_chain) >= 3:
                    bl_chains.append(current_chain[:])
                current_chain = [sorted_events[i][0]]
        if len(current_chain) >= 3:
            bl_chains.append(current_chain[:])

    print(f"  H3 chains found: {len(h3_chains)} ({t_h3.elapsed*1000:.1f}ms)")
    for i, chain in enumerate(h3_chains[:5]):
        labels = []
        for eid in chain:
            evt = tr.get_event(eid)
            labels.append(evt.label if evt else eid[:8])
        print(f"    Chain {i+1}: {' -> '.join(labels)}")

    print(f"  Simple chains found: {len(bl_chains)} ({t_bl.elapsed*1000:.1f}ms)")
    for i, chain in enumerate(bl_chains[:5]):
        print(f"    Chain {i+1}: {' -> '.join(chain)}")

    # --- Constraint Checking ---
    print_header("Constraint Checking")
    tr.add_constraint("requirements", "design", AllenRelation.OVERLAPS)
    tr.add_constraint("testing", "deployment", AllenRelation.BEFORE)
    tr.add_constraint("deployment", "monitoring", AllenRelation.OVERLAPS)
    tr.add_constraint("requirements", "deployment", AllenRelation.BEFORE)

    with Timer() as t_h3:
        constraint_results = tr.check_constraint_consistency()

    print(f"  Constraints checked: {len(tr.constraints)}")
    print(f"  Time: {t_h3.elapsed*1000:.1f}ms")
    for cr in constraint_results:
        print(f"    {cr['from']} {cr['expected']} {cr['to']}: actual={cr['actual']}  consistent={cr['consistent']}")

    # --- Summary ---
    print_header("Summary")
    headers = ["System", "Accuracy", "Relations", "Chains", "Time"]
    rows = [
        ["Hyper3 Allen", f"{h3_acc:.1%}", str(len(all_h3_rels)), str(len(h3_chains)), f"{h3_time*1000:.1f}ms"],
        ["Simple overlap", f"{bl_acc:.1%}", str(len(all_bl_rels)), str(len(bl_chains)), f"{bl_time*1000:.1f}ms"],
    ]
    print_comparison_table(headers, rows)

    print()


if __name__ == "__main__":
    main()
