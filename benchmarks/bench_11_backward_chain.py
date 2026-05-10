"""
Bench 11: Backward Chaining and Confidence Assessment
======================================================

Compares Hyper3's confidence assessment and proof-based reasoning against
simpler baselines for evaluating concept reliability.

Systems compared:
  1. Hyper3 UncertaintyEngine - provenance-depth confidence with chain tracing
  2. Edge count heuristic - shortest path length as inverse confidence
  3. Degree-based confidence - node degree as confidence proxy

Metrics:
  - Confidence calibration: alignment with ground-truth reliability
  - Chain depth: inference chain length for concept derivation
  - Low-confidence detection: flagging uncertain concepts
  - Batch proof: accumulative proving across targets

Run:
    .venv/bin/python benchmarks/bench_11_backward_chain.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyper3 import HypergraphMemory, Modality, TransitiveRule, InverseRule
from shared import (
    build_cs_knowledge_graph,
    build_nx_digraph,
    build_hyper3_memory,
    Timer,
    print_header,
    print_comparison_table,
)


CHAIN_CONCEPTS = [
    ("sorting", "algorithm"),
    ("bert", "deep_learning"),
    ("dropout", "regularization"),
    ("deadlock", "concurrency"),
    ("acid", "transaction"),
    ("object_detection", "computer_vision"),
    ("policy_gradient", "reinforcement_learning"),
    ("git", "version_control"),
    ("b_tree", "data_structure"),
    ("dns", "networking"),
]


def edge_count_confidence(mem: HypergraphMemory, source: str, target: str) -> float:
    path = mem.analyze.shortest_path(source, target)
    if not path or len(path) < 2:
        return 0.0
    return 1.0 / len(path)


def degree_confidence(mem: HypergraphMemory, concept: str) -> float:
    neighbors = mem.neighbors(concept, direction="any")
    return min(len(neighbors) / 10.0, 1.0)


def main() -> None:
    print_header("Bench 11: Confidence Assessment")

    nodes, edges = build_cs_knowledge_graph()
    mem = build_hyper3_memory(nodes, edges)

    mem.add_rules(
        TransitiveRule(edge_label="includes", new_label="indirectly_includes"),
        TransitiveRule(edge_label="is_a", new_label="indirectly_is_a"),
        TransitiveRule(edge_label="uses", new_label="indirectly_uses"),
        InverseRule(edge_label="includes", inverse_label="included_in"),
    )

    all_labels = {lbl for e in mem.edges() for lbl in e.source_labels + e.target_labels}
    mem.reason(all_labels, max_depth=3, max_total_states=500)

    print(f"\n  Graph: {len(nodes)} nodes, {len(edges)} edges (before reasoning)")
    print(f"  After reasoning: {mem.size[0]} nodes, {mem.size[1]} edges")

    print_header("Confidence Scores")
    with Timer() as t_conf:
        all_conf = mem.compute_all_confidences()
    print(f"  compute_all_confidences: {t_conf.elapsed*1000:.1f}ms")
    print(f"  Avg confidence: {all_conf.avg_confidence:.3f}")
    print(f"  Range: [{all_conf.min_confidence:.3f}, {all_conf.max_confidence:.3f}]")
    print(f"  High confidence (>0.8): {all_conf.high_confidence_count}")
    print(f"  Low confidence (<0.3): {all_conf.low_confidence_count}")

    test_concepts = [
        "algorithm", "neural_network", "transformer", "deadlock",
        "database", "dropout", "design_pattern", "http",
        "reinforcement_learning", "python",
    ]

    conf_data: list[list[str]] = []
    h3_time = 0.0
    deg_time = 0.0
    for concept in test_concepts:
        if not mem.has(concept):
            continue

        with Timer() as t:
            cs = mem.compute_confidence(concept)
        h3_time += t.elapsed

        with Timer() as t:
            deg = degree_confidence(mem, concept)
        deg_time += t.elapsed

        if cs:
            conf_data.append([
                concept,
                f"{cs.confidence:.3f}",
                str(cs.depth),
                cs.source,
                f"{deg:.3f}",
                str(len(cs.contributing_edges)),
            ])
        else:
            conf_data.append([concept, "N/A", "-", "-", f"{deg:.3f}", "-"])

    conf_headers = ["Concept", "H3 Confidence", "Depth", "Source", "Degree Conf", "Contrib Edges"]
    print_comparison_table(conf_headers, conf_data)
    print(f"  H3 time: {h3_time*1000:.1f}ms  |  Degree time: {deg_time*1000:.1f}ms")

    print_header("Confidence Chain Tracing")
    chain_data: list[list[str]] = []

    for source, target in CHAIN_CONCEPTS:
        if not mem.has(source) or not mem.has(target):
            continue

        with Timer() as t:
            chain = mem.trace_confidence_chain(source, target)
        h3_chain_time = t.elapsed

        with Timer():
            ec_conf = edge_count_confidence(mem, source, target)

        if chain:
            chain_data.append([
                f"{source} -> {target}",
                f"{chain.chain_confidence:.3f}",
                str(chain.chain_depth),
                str(len(chain.edges)),
                f"{ec_conf:.3f}",
            ])
        else:
            chain_data.append([
                f"{source} -> {target}",
                "no chain",
                "-",
                "-",
                f"{ec_conf:.3f}",
            ])

    chain_headers = ["Path", "Chain Confidence", "Depth", "Edges", "Path Inv Conf"]
    print_comparison_table(chain_headers, chain_data)

    print_header("Low-Confidence Detection")
    with Timer() as t_flag:
        flagged = mem.flag_low_confidence(threshold=0.3)

    print(f"  Flagged (confidence < 0.3): {len(flagged)} ({t_flag.elapsed*1000:.1f}ms)")
    for item in flagged[:10]:
        print(f"    {item.node_label}: confidence={item.confidence:.3f} depth={item.depth} source={item.source}")

    with Timer() as t_flag2:
        flagged_high = mem.flag_low_confidence(threshold=0.7)
    print(f"  Below 0.7: {len(flagged_high)} ({t_flag2.elapsed*1000:.1f}ms)")

    print_header("Backward Chaining (direct fact proving)")
    mem2 = HypergraphMemory(evolve_interval=0)
    mem2.add("A")
    mem2.add("B")
    mem2.add("C")
    mem2.add("D")
    mem2.add("E")
    mem2.link("A", "B", label="implies")
    mem2.link("B", "C", label="implies")
    mem2.link("C", "D", label="implies")
    mem2.link("D", "E", label="implies")
    mem2.add_rules(TransitiveRule(edge_label="implies", new_label="implies"))

    known = {"A"}
    targets = ["A", "B", "C", "D", "E"]
    chain_proof_data: list[list[str]] = []

    for target in targets:
        with Timer() as t:
            result = mem2.prove(target, known_facts=known)
        chain_proof_data.append([
            target,
            "Y" if result.achievable else "N",
            f"{result.confidence:.3f}",
            f"{result.satisfied_premises}/{result.total_premises_needed}",
            str(len(result.missing_premises)),
            f"{t.elapsed*1000:.1f}ms",
        ])

    proof_headers = ["Target", "Achievable", "Confidence", "Premises", "Missing", "Time"]
    print_comparison_table(proof_headers, chain_proof_data)

    print_header("Batch Proof Accumulation")
    with Timer() as t:
        batch_results = mem2.prove_batch(["A", "B", "C", "D", "E"], known_facts={"A"})

    proven = sum(1 for r in batch_results if r.achievable)
    print(f"  Proven: {proven}/5 ({t.elapsed*1000:.1f}ms)")
    for r in batch_results:
        print(f"    {r.goal_label}: achievable={r.achievable} confidence={r.confidence:.3f}")

    print_header("Summary")
    headers = ["Metric", "Value"]
    rows = [
        ["Avg confidence", f"{all_conf.avg_confidence:.3f}"],
        ["High confidence (>0.8)", str(all_conf.high_confidence_count)],
        ["Low confidence (<0.3)", str(all_conf.low_confidence_count)],
        ["Flagged at 0.3", str(len(flagged))],
        ["Flagged at 0.7", str(len(flagged_high))],
        ["Batch provable", f"{proven}/5"],
        ["All confidences time", f"{t_conf.elapsed*1000:.1f}ms"],
    ]
    print_comparison_table(headers, rows)

    print()
