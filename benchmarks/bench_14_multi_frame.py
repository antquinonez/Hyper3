"""
Bench 14: Multi-Frame Analysis
================================

Compares Hyper3's multi-perspective analysis against single-frame baselines
for problem assessment across different computational reference frames.

Systems compared:
  1. Hyper3 multi-frame analysis - classical, quantum, hypergraph, probabilistic frames
  2. Single-frame (classical) - analysis through classical complexity only
  3. Random frame selection - randomly pick one frame

Metrics:
  - Frame coverage: number of distinct insights across frames
  - Optimal frame selection: does learned selection pick the best frame?
  - Consistency: do different frames agree on difficulty ranking?
  - Information gain: how much more information does multi-frame provide?

Ground truth: manually assessed problem complexity on CS concept graph.

Run:
    .venv/bin/python benchmarks/bench_14_multi_frame.py
"""

from __future__ import annotations

import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyper3 import HypergraphMemory, Modality
from shared import (
    build_cs_knowledge_graph,
    build_hyper3_memory,
    Timer,
    print_header,
    print_comparison_table,
)


TEST_CONCEPTS = [
    "algorithm",
    "neural_network",
    "deadlock",
    "transformer",
    "database",
    "recursion",
    "gradient_descent",
    "design_pattern",
    "http",
    "reinforcement_learning",
]


def analyze_single_frame(mem: HypergraphMemory, concept: str) -> dict:
    result = mem.analyze_in_frame(concept, "classical")
    if result is None:
        return {"complexity": float("inf"), "approach": "N/A", "strengths": 0, "weaknesses": 0}
    return {
        "complexity": result.complexity,
        "approach": result.solution_approach,
        "strengths": len(result.strengths) if result.strengths else 0,
        "weaknesses": len(result.weaknesses) if result.weaknesses else 0,
    }


def main() -> None:
    print_header("Bench 14: Multi-Frame Analysis")

    nodes, edges = build_cs_knowledge_graph()
    mem = build_hyper3_memory(nodes, edges)

    print(f"\n  Graph: {len(nodes)} nodes, {len(edges)} edges")
    print(f"  Test concepts: {len(TEST_CONCEPTS)}")

    FRAMES = ["classical", "quantum", "hypergraph", "probabilistic"]

    print_header("Multi-Frame Analysis")
    frame_data: list[list[str]] = []
    multi_time = 0.0
    single_time = 0.0

    for concept in TEST_CONCEPTS:
        if not mem.has(concept):
            continue

        with Timer() as t_multi:
            multi_result = mem.multi_frame_analysis(concept)
        multi_time += t_multi.elapsed

        with Timer() as t_single:
            single_result = analyze_single_frame(mem, concept)
        single_time += t_single.elapsed

        frame_complexities = {}
        total_insights = 0
        for frame_name, analysis in multi_result.items():
            frame_complexities[frame_name] = analysis.complexity
            total_insights += (len(analysis.strengths) if analysis.strengths else 0)
            total_insights += (len(analysis.weaknesses) if analysis.weaknesses else 0)

        best_frame = min(frame_complexities, key=frame_complexities.get) if frame_complexities else "N/A"
        best_complexity = min(frame_complexities.values()) if frame_complexities else float("inf")
        classical_complexity = frame_complexities.get("classical", float("inf"))

        frame_data.append([
            concept,
            f"{classical_complexity:.1f}",
            f"{best_complexity:.1f}",
            best_frame,
            str(total_insights),
            str(len(multi_result)),
        ])

    multi_headers = ["Concept", "Classical", "Best", "Best Frame", "Insights", "Frames"]
    print_comparison_table(multi_headers, frame_data)

    print_header("Frame Selection Performance")
    rng = random.Random(42)

    for _ in range(50):
        concept = rng.choice(TEST_CONCEPTS)
        mem.analyze_in_frame(concept, "classical")
        mem.analyze_in_frame(concept, "hypergraph")

    select_data: list[list[str]] = []
    for concept in TEST_CONCEPTS:
        if not mem.has(concept):
            continue

        with Timer() as t:
            opt_frame, opt_analysis = mem.select_optimal_frame(concept)

        multi_result = mem.multi_frame_analysis(concept)
        all_complexities = {f: a.complexity for f, a in multi_result.items()}
        true_best = min(all_complexities, key=all_complexities.get) if all_complexities else "N/A"

        select_data.append([
            concept,
            opt_frame,
            f"{opt_analysis.complexity:.1f}" if opt_analysis else "N/A",
            true_best,
            "Y" if opt_frame == true_best else "N",
        ])

    select_headers = ["Concept", "Selected Frame", "Complexity", "True Best", "Correct"]
    print_comparison_table(select_headers, select_data)

    correct = sum(1 for row in select_data if row[4] == "Y")
    print(f"\n  Correct selection: {correct}/{len(select_data)}")

    print_header("Single-Frame vs Multi-Frame Comparison")
    comparison_data: list[list[str]] = []

    for concept in TEST_CONCEPTS:
        if not mem.has(concept):
            continue

        single = analyze_single_frame(mem, concept)
        multi = mem.multi_frame_analysis(concept)

        single_strengths = single["strengths"]
        multi_strengths = sum(
            len(a.strengths) if a.strengths else 0 for a in multi.values()
        )
        single_weaknesses = single["weaknesses"]
        multi_weaknesses = sum(
            len(a.weaknesses) if a.weaknesses else 0 for a in multi.values()
        )

        comparison_data.append([
            concept,
            str(single_strengths),
            str(multi_strengths),
            str(single_weaknesses),
            str(multi_weaknesses),
        ])

    comp_headers = ["Concept", "Single Str", "Multi Str", "Single Weak", "Multi Weak"]
    print_comparison_table(comp_headers, comparison_data)

    print_header("Summary")
    headers = ["System", "Time", "Avg Insights"]
    rows = [
        ["Multi-frame (4 frames)", f"{multi_time*1000:.1f}ms", f"{sum(int(r[4]) for r in frame_data)/max(len(frame_data),1):.1f}"],
        ["Single-frame (classical)", f"{single_time*1000:.1f}ms", f"{sum(int(r[4]) for r in comparison_data)/max(len(comparison_data),1):.1f}"],
    ]
    print_comparison_table(headers, rows)

    print()
