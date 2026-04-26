"""
Evaluation Runner
=================

Runs all benchmarks sequentially and prints a final summary.

Usage:
    .venv/bin/python benchmarks/run_all.py [bench_number ...]

Examples:
    .venv/bin/python benchmarks/run_all.py              # run all
    .venv/bin/python benchmarks/run_all.py 0 1 5        # run benches 0, 1, 5
"""

from __future__ import annotations

import importlib
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

BENCHMARKS = [
    ("bench_00_microbenchmarks", "Performance Microbenchmarks"),
    ("bench_01_retrieval", "Retrieval Quality (RRF vs BFS/PPR/RWR)"),
    ("bench_02_inference", "Transitive Inference (Rules vs BFS Closure/Warshall)"),
    ("bench_03_analytics", "Graph Analytics (Hyper3 vs raw networkx)"),
    ("bench_04_temporal", "Temporal Reasoning (Allen Algebra vs Simple Overlap)"),
    ("bench_05_activation", "Spreading Activation (vs PPR/RWR/BFS)"),
    ("bench_06_evolution", "Self-Evolution (Decay/Prune/Merge vs Baselines)"),
    ("bench_07_enrichment", "Text Enrichment (RegexExtractor vs Simple Regex)"),
    ("bench_08_scalability", "Scalability (Hyper3 vs networkx at scale)"),
    ("bench_09_retrieval_feedback", "Retrieval Quality with Feedback Learning"),
]


def main() -> None:
    args = sys.argv[1:]
    if args:
        indices = [int(a) - 1 for a in args if a.isdigit()]
        selected = [(BENCHMARKS[i], i) for i in indices if 0 <= i < len(BENCHMARKS)]
    else:
        selected = [(b, i) for i, b in enumerate(BENCHMARKS)]

    print("=" * 70)
    print("  Hyper3 Benchmark Suite")
    print("=" * 70)
    print(f"  Benchmarks to run: {len(selected)}")
    print()

    results: list[tuple[str, bool, float, str]] = []

    bench_dir = os.path.dirname(os.path.abspath(__file__))
    if bench_dir not in sys.path:
        sys.path.insert(0, bench_dir)

    for (module_name, description), idx in selected:
        bench_path = os.path.join(bench_dir, f"{module_name}.py")
        print(f"\n{'=' * 70}")
        print(f"  [{idx + 1}/{len(selected)}] {description}")
        print(f"  File: {module_name}.py")
        print(f"{'=' * 70}")

        start = time.perf_counter()
        try:
            mod = importlib.import_module(module_name)
            mod.main()
            elapsed = time.perf_counter() - start
            results.append((description, True, elapsed, ""))
        except Exception as e:
            elapsed = time.perf_counter() - start
            results.append((description, False, elapsed, str(e)))

    print("\n" + "=" * 70)
    print("  Benchmark Summary")
    print("=" * 70)
    for desc, ok, elapsed, err in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {desc} ({elapsed:.1f}s)")
        if not ok:
            print(f"         Error: {err[:100]}")
    total = sum(t for _, _, t, _ in results)
    passed = sum(1 for _, ok, _, _ in results if ok)
    print(f"\n  Total: {passed}/{len(results)} passed in {total:.1f}s")
    print()


if __name__ == "__main__":
    main()
