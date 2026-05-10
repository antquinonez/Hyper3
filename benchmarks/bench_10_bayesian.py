"""
Bench 10: Bayesian Reasoning
=============================

Compares Hyper3's Bayesian updating against simpler baselines for
posterior convergence, MAP estimation accuracy, and evidence strength.

Systems compared:
  1. Hyper3 BayesianMixin - full Bayesian posterior updating with priors
  2. Naive frequency counting - simple observed frequency as probability
  3. Flat prior (uniform) - no prior information, Laplace smoothing

Metrics:
  - Posterior accuracy: KL divergence from true distribution
  - MAP estimation: correctness of most-likely hypothesis
  - Convergence speed: observations needed to reach stable posterior
  - Bayes factor strength: correct identification of strong vs weak evidence

Ground truth: simulated diagnostic scenario with known true probabilities.

Run:
    .venv/bin/python benchmarks/bench_10_bayesian.py
"""

from __future__ import annotations

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyper3 import HypergraphMemory, Modality
from shared import Timer, print_header, print_comparison_table


DIAGNOSTIC_SCENARIO = [
    ("condition_A", 0.02, {"high_fever": 0.9, "cough": 0.7, "fatigue": 0.6}),
    ("condition_B", 0.05, {"high_fever": 0.3, "cough": 0.8, "rash": 0.9}),
    ("condition_C", 0.15, {"fatigue": 0.5, "headache": 0.6, "nausea": 0.4}),
    ("condition_D", 0.40, {"headache": 0.3, "fatigue": 0.4, "dizziness": 0.2}),
    ("condition_E", 0.38, {"fatigue": 0.2, "rash": 0.1, "cough": 0.1}),
]

CONDITIONS = [c for c, _, _ in DIAGNOSTIC_SCENARIO]
SYMPTOMS = ["high_fever", "cough", "fatigue", "rash", "headache", "nausea", "dizziness"]


def kl_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p.keys()) | set(q.keys())
    kl = 0.0
    for k in keys:
        pk = p.get(k, 1e-10)
        qk = q.get(k, 1e-10)
        if pk > 1e-10 and qk > 1e-10:
            kl += pk * math.log(pk / qk)
    return max(0.0, kl)


def naive_frequency(
    observations: list[tuple[str, str]],
    labels: list[str],
) -> dict[str, float]:
    counts: dict[str, int] = {l: 0 for l in labels}
    for label, obs in observations:
        if obs == "present":
            counts[label] = counts.get(label, 0) + 1
    total = sum(counts.values()) or 1
    return {l: c / total for l, c in counts.items()}


def laplace_smoothing(
    observations: list[tuple[str, str]],
    labels: list[str],
) -> dict[str, float]:
    counts: dict[str, int] = {l: 1 for l in labels}
    for label, obs in observations:
        if obs == "present":
            counts[label] = counts.get(label, 0) + 1
    total = sum(counts.values())
    return {l: c / total for l, c in counts.items()}


def build_diagnostic_graph(mem: HypergraphMemory) -> None:
    for label, _, _ in DIAGNOSTIC_SCENARIO:
        mem.add(label, data={"type": "condition"})
    for symptom in SYMPTOMS:
        mem.add(symptom, data={"type": "symptom"})
    for label, _, symptoms in DIAGNOSTIC_SCENARIO:
        for symptom, likelihood in symptoms.items():
            mem.link(label, symptom, label="causes", weight=likelihood * 5.0)


def init_priors(mem: HypergraphMemory) -> None:
    for label, prior, _ in DIAGNOSTIC_SCENARIO:
        mem.set_prior(label, outcomes=CONDITIONS, weights=[
            prior if c == label else (1.0 - prior) / (len(CONDITIONS) - 1)
            for c in CONDITIONS
        ])


def apply_evidence(mem: HypergraphMemory, symptoms: set[str]) -> None:
    for symptom in symptoms:
        for c_label, _, symptom_probs in DIAGNOSTIC_SCENARIO:
            likelihood = symptom_probs.get(symptom, 0.1)
            likelihoods = {c: likelihood if c == c_label else (1.0 - likelihood) / (len(CONDITIONS) - 1) for c in CONDITIONS}
            mem.update_belief(c_label, evidence_name=symptom, likelihoods=likelihoods)


def compute_true_posteriors(present_symptoms: set[str]) -> dict[str, float]:
    posteriors: dict[str, float] = {}
    for label, prior, symptom_probs in DIAGNOSTIC_SCENARIO:
        post = prior
        for s in present_symptoms:
            if s in symptom_probs:
                post *= symptom_probs[s]
            else:
                post *= (1.0 - 0.3)
        for s in SYMPTOMS:
            if s not in present_symptoms and s in symptom_probs:
                post *= (1.0 - symptom_probs[s])
        posteriors[label] = post
    total = sum(posteriors.values()) or 1.0
    return {k: v / total for k, v in posteriors.items()}


def get_h3_posteriors(mem: HypergraphMemory) -> dict[str, float]:
    posteriors: dict[str, float] = {}
    for label in CONDITIONS:
        belief = mem.get_belief(label)
        if belief and belief.outcomes:
            node_id = mem.resolve_id(label)
            if node_id and node_id in belief.outcomes:
                posteriors[label] = belief.outcomes[node_id]
            else:
                posteriors[label] = sum(belief.outcomes.values()) / len(belief.outcomes)
        else:
            posteriors[label] = 0.0
    total = sum(posteriors.values()) or 1.0
    return {k: v / total for k, v in posteriors.items()}


def main() -> None:
    print_header("Bench 10: Bayesian Reasoning")

    mem = HypergraphMemory(evolve_interval=0)
    build_diagnostic_graph(mem)
    init_priors(mem)

    print(f"\n  Conditions: {len(DIAGNOSTIC_SCENARIO)}")
    print(f"  Symptoms: {len(SYMPTOMS)}")

    test_cases = [
        {"high_fever", "cough"},
        {"fatigue", "headache"},
        {"rash", "high_fever"},
        {"nausea", "dizziness"},
        {"fatigue", "cough", "rash"},
    ]

    print_header("Bayesian Posterior Updating")
    bayes_kl_list: list[float] = []
    naive_kl_list: list[float] = []
    laplace_kl_list: list[float] = []
    bayes_map_correct: list[float] = []
    naive_map_correct: list[float] = []
    laplace_map_correct: list[float] = []
    bayes_time = 0.0

    for symptoms in test_cases:
        true_post = compute_true_posteriors(symptoms)
        true_map = max(true_post, key=true_post.get)

        observations = []
        for s in SYMPTOMS:
            obs = "present" if s in symptoms else "absent"
            for c_label in CONDITIONS:
                observations.append((c_label, obs))

        mem2 = HypergraphMemory(evolve_interval=0)
        build_diagnostic_graph(mem2)
        init_priors(mem2)

        with Timer() as t:
            apply_evidence(mem2, symptoms)
        bayes_time += t.elapsed

        h3_posteriors = get_h3_posteriors(mem2)
        h3_kl = kl_divergence(true_post, h3_posteriors)
        h3_map = max(h3_posteriors, key=h3_posteriors.get)
        bayes_kl_list.append(h3_kl)
        bayes_map_correct.append(1.0 if h3_map == true_map else 0.0)

        naive_post = naive_frequency(observations, CONDITIONS)
        naive_kl = kl_divergence(true_post, naive_post)
        naive_map = max(naive_post, key=naive_post.get)
        naive_kl_list.append(naive_kl)
        naive_map_correct.append(1.0 if naive_map == true_map else 0.0)

        laplace_post = laplace_smoothing(observations, CONDITIONS)
        laplace_kl = kl_divergence(true_post, laplace_post)
        laplace_map = max(laplace_post, key=laplace_post.get)
        laplace_kl_list.append(laplace_kl)
        laplace_map_correct.append(1.0 if laplace_map == true_map else 0.0)

    def avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    headers = ["System", "Avg KL Divergence", "MAP Accuracy", "Time"]
    rows = [
        ["Hyper3 Bayesian", f"{avg(bayes_kl_list):.4f}", f"{avg(bayes_map_correct):.1%}", f"{bayes_time*1000:.1f}ms"],
        ["Naive frequency", f"{avg(naive_kl_list):.4f}", f"{avg(naive_map_correct):.1%}", "-"],
        ["Laplace smoothing", f"{avg(laplace_kl_list):.4f}", f"{avg(laplace_map_correct):.1%}", "-"],
    ]
    print_comparison_table(headers, rows)

    print_header("MAP Estimation Accuracy")
    for symptoms in test_cases:
        true_post = compute_true_posteriors(symptoms)
        true_map = max(true_post, key=true_post.get)
        mem3 = HypergraphMemory(evolve_interval=0)
        build_diagnostic_graph(mem3)
        init_priors(mem3)
        apply_evidence(mem3, symptoms)

        h3_map_label = mem3.map_estimate(true_map)
        print(f"  Symptoms: {symptoms}")
        print(f"    True MAP: {true_map}")
        print(f"    H3 MAP estimate: {h3_map_label}")
        print(f"    True posterior: {', '.join(f'{k}={v:.3f}' for k, v in sorted(true_post.items(), key=lambda x: -x[1]))}")
        print()

    print_header("Convergence Speed")
    convergence_data: list[list[str]] = []
    for n_obs in [1, 2, 3, 5, 10]:
        sym_set = {"high_fever", "cough", "fatigue"} if n_obs >= 3 else {"high_fever", "cough"}
        true_post = compute_true_posteriors(sym_set)
        true_map = max(true_post, key=true_post.get)
        mem4 = HypergraphMemory(evolve_interval=0)
        build_diagnostic_graph(mem4)
        init_priors(mem4)

        for _ in range(n_obs):
            apply_evidence(mem4, sym_set)

        posteriors = get_h3_posteriors(mem4)
        kl = kl_divergence(true_post, posteriors)
        h3_map = max(posteriors, key=posteriors.get)
        convergence_data.append([
            str(n_obs),
            f"{kl:.4f}",
            "Y" if h3_map == true_map else "N",
            f"{posteriors[true_map]:.3f}",
        ])

    conv_headers = ["Observations", "KL Divergence", "MAP Correct", "True MAP Posterior"]
    print_comparison_table(conv_headers, convergence_data)

    print_header("Bayes Factor Strength")
    mem5 = HypergraphMemory(evolve_interval=0)
    build_diagnostic_graph(mem5)
    init_priors(mem5)
    apply_evidence(mem5, {"high_fever", "cough", "rash"})

    bf_data: list[list[str]] = []
    for i in range(len(CONDITIONS)):
        for j in range(i + 1, len(CONDITIONS)):
            bf = mem5.bayes_factor(
                CONDITIONS[i],
                hypothesis_a=CONDITIONS[i],
                hypothesis_b=CONDITIONS[j],
            )
            if bf is not None:
                strength = "strong" if abs(math.log10(max(bf, 1e-10))) > 1 else "weak"
                bf_data.append([f"{CONDITIONS[i]} vs {CONDITIONS[j]}", f"{bf:.2f}", strength])

    bf_headers = ["Comparison", "Bayes Factor", "Strength"]
    print_comparison_table(bf_headers, bf_data)

    print()


if __name__ == "__main__":
    main()
