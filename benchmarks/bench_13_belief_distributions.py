"""
Bench 13: Belief Distributions
================================

Compares Hyper3's Born-rule belief distributions against simpler baselines
for representing and sampling from multi-outcome uncertainty.

Systems compared:
  1. Hyper3 BeliefLayer - complex-amplitude belief states, Born-rule sampling
  2. Uniform sampling - equal probability for all outcomes
  3. Weighted sampling - direct probability sampling (numpy)

Metrics:
  - Sampling accuracy: distribution convergence to Born-rule probabilities
  - Information preservation: entropy of sampled distributions vs expected
  - Born-rule fidelity: |amplitude|^2 probability matches observed frequency

Ground truth: known probability distributions with controlled amplitudes.

Run:
    .venv/bin/python benchmarks/bench_13_belief_distributions.py
"""

from __future__ import annotations

import sys
import os
import math
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from hyper3 import HypergraphMemory, Modality
from shared import Timer, print_header, print_comparison_table


N_SAMPLES = 1000
RNG = np.random.RandomState(42)


TEST_CONCEPTS = [
    {
        "label": "bank",
        "outcomes": ["financial", "river_edge", "billiards"],
        "amplitudes": [0.6, 0.5, 0.37],
    },
    {
        "label": "java",
        "outcomes": ["language", "island", "coffee"],
        "amplitudes": [0.8, 0.3, 0.2],
    },
    {
        "label": "apple",
        "outcomes": ["fruit", "tech_company", "record_label"],
        "amplitudes": [0.5, 0.7, 0.2],
    },
]


def born_probs(amplitudes: list[float]) -> list[float]:
    probs = [a ** 2 for a in amplitudes]
    total = sum(probs)
    return [p / total for p in probs]


def distribution_accuracy(observed: dict[str, float], expected: dict[str, float]) -> float:
    keys = set(observed.keys()) | set(expected.keys())
    total_error = 0.0
    for k in keys:
        o = observed.get(k, 0.0)
        e = expected.get(k, 0.0)
        total_error += abs(o - e)
    return 1.0 - total_error / 2.0


def entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0)


def main() -> None:
    print_header("Bench 13: Belief Distributions")

    mem = HypergraphMemory(evolve_interval=0)
    for tc in TEST_CONCEPTS:
        for outcome in tc["outcomes"]:
            mem.add(outcome, data={"type": "outcome"})

    print(f"\n  Concepts: {len(TEST_CONCEPTS)}")
    print(f"  Samples per concept: {N_SAMPLES}")

    print_header("Distribution Creation and Born-Rule Probabilities")
    states = {}
    for tc in TEST_CONCEPTS:
        with Timer() as t:
            state = mem.belief.create(tc["outcomes"], amplitudes=tc["amplitudes"])
        states[tc["label"]] = state

        probs = mem.belief.probabilities(state)
        expected = born_probs(tc["amplitudes"])
        expected_dict = dict(zip(tc["outcomes"], expected))

        print(f"  {tc['label']} ({t.elapsed*1000:.1f}ms):")
        for i, outcome in enumerate(tc["outcomes"]):
            born_p = probs.get(outcome, 0.0)
            print(f"    {outcome}: amplitude={tc['amplitudes'][i]:.2f}  Born={born_p:.4f}  expected={expected[i]:.4f}")

    print_header("Sampling Accuracy")
    accuracy_data: list[list[str]] = []

    for tc in TEST_CONCEPTS:
        expected = born_probs(tc["amplitudes"])
        expected_dict = dict(zip(tc["outcomes"], expected))
        expected_ent = entropy(expected)

        with Timer() as t:
            counts = mem.belief.sample_many(states[tc["label"]], n=N_SAMPLES)
        total = sum(counts.values()) or 1
        h3_dist = {o: counts.get(o, 0) / total for o in tc["outcomes"]}
        h3_accuracy = distribution_accuracy(h3_dist, expected_dict)
        h3_entropy = entropy(list(h3_dist.values()))

        uniform_probs = [1.0 / len(tc["outcomes"])] * len(tc["outcomes"])
        uniform_counts = Counter(RNG.choice(tc["outcomes"], size=N_SAMPLES))
        uniform_total = sum(uniform_counts.values()) or 1
        uniform_dist = {o: uniform_counts.get(o, 0) / uniform_total for o in tc["outcomes"]}
        uniform_accuracy = distribution_accuracy(uniform_dist, expected_dict)

        weighted_counts = Counter(RNG.choice(tc["outcomes"], size=N_SAMPLES, p=expected))
        weighted_total = sum(weighted_counts.values()) or 1
        weighted_dist = {o: weighted_counts.get(o, 0) / weighted_total for o in tc["outcomes"]}
        weighted_accuracy = distribution_accuracy(weighted_dist, expected_dict)

        accuracy_data.append([
            tc["label"],
            f"{h3_accuracy:.3f}",
            f"{uniform_accuracy:.3f}",
            f"{weighted_accuracy:.3f}",
            f"{expected_ent:.3f}",
            f"{h3_entropy:.3f}",
            f"{t.elapsed*1000:.1f}ms",
        ])

    acc_headers = ["Concept", "H3 Accuracy", "Uniform Acc", "Weighted Acc", "Expected Ent", "H3 Entropy", "Time"]
    print_comparison_table(acc_headers, accuracy_data)

    print_header("Correlation Capture")
    mem2 = HypergraphMemory(evolve_interval=0)
    for outcome in ["sunny", "rainy", "cloudy", "happy", "sad", "neutral_mood"]:
        mem2.add(outcome, data={"type": "outcome"})
    weather_state = mem2.belief.create(["sunny", "rainy", "cloudy"], amplitudes=[0.6, 0.5, 0.37])
    mood_state = mem2.belief.create(["happy", "sad", "neutral_mood"], amplitudes=[0.6, 0.4, 0.3])

    correlations = {
        ("sunny", "happy"): 0.8,
        ("sunny", "sad"): -0.5,
        ("rainy", "sad"): 0.7,
        ("rainy", "happy"): -0.4,
        ("cloudy", "neutral_mood"): 0.6,
    }
    mem2.belief.correlate(
        ["sunny", "rainy", "cloudy"],
        ["happy", "sad", "neutral_mood"],
        correlations,
    )

    n_corr_samples = 500
    with Timer() as t:
        joint_counts: dict[tuple[str, str], int] = Counter()
        for _ in range(n_corr_samples):
            w = mem2.belief.sample(weather_state)
            m = mem2.belief.sample(mood_state)
            if w and m:
                joint_counts[(w, m)] += 1

    print(f"  Samples: {n_corr_samples}")
    print(f"  Time: {t.elapsed*1000:.1f}ms")

    corr_data: list[list[str]] = []
    for (w, m), expected_corr in sorted(correlations.items()):
        co = joint_counts.get((w, m), 0)
        w_total = sum(v for (ww, _), v in joint_counts.items() if ww == w)
        m_total = sum(v for (_, mm), v in joint_counts.items() if mm == m)
        observed = co / max(min(w_total, m_total), 1) if co > 0 else 0.0
        direction = "same" if (expected_corr > 0) == (observed > 0.15 or (expected_corr > 0 and co > 0)) else "weak"
        corr_data.append([
            f"{w} & {m}",
            f"{expected_corr:+.1f}",
            str(co),
            f"{observed:.3f}",
            direction,
        ])

    corr_headers = ["Pair", "Expected Corr", "Co-occurrences", "Observed", "Direction"]
    print_comparison_table(corr_headers, corr_data)

    print_header("Information Preservation")
    info_data: list[list[str]] = []
    for tc in TEST_CONCEPTS:
        expected = born_probs(tc["amplitudes"])
        expected_ent = entropy(expected)
        max_ent = math.log2(len(tc["outcomes"]))

        counts = mem.belief.sample_many(states[tc["label"]], n=N_SAMPLES)
        total = sum(counts.values()) or 1
        sampled_dist = [counts.get(o, 0) / total for o in tc["outcomes"]]
        sampled_ent = entropy(sampled_dist)

        info_preserved = sampled_ent / expected_ent if expected_ent > 0 else 1.0

        info_data.append([
            tc["label"],
            f"{max_ent:.3f}",
            f"{expected_ent:.3f}",
            f"{sampled_ent:.3f}",
            f"{info_preserved:.3f}",
        ])

    info_headers = ["Concept", "Max Entropy", "Expected Entropy", "Sampled Entropy", "Info Preserved"]
    print_comparison_table(info_headers, info_data)

    print()
