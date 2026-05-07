"""
Bayesian Belief Updating for Incident Root Cause Analysis
==========================================================

Build a knowledge graph linking potential root causes to observable evidence
for a production outage, then perform sequential Bayesian updates as evidence
arrives. Demonstrates prior specification, posterior computation, MAP
estimation, credible sets, Bayes factor comparison, and information gain
(KL divergence) ranking of evidence.

Run with:
    .venv/bin/python examples/showcase/bayesian_reasoning/14_bayesian_reasoning.py
"""

from __future__ import annotations

import math

from hyper3 import HypergraphMemory


ROOT_CAUSES: list[str] = [
    "database_overload",
    "network_partition",
    "config_error",
    "memory_leak",
    "dns_failure",
    "auth_service_down",
]

EVIDENCE_NODES: list[str] = [
    "high_cpu",
    "db_slow_queries",
    "intermittent_503s",
    "config_diff_detected",
    "memory_growth_trend",
    "dns_timeout_logs",
    "auth_latency_spike",
    "network_packet_loss",
]

LIKELIHOODS: dict[str, dict[str, float]] = {
    "high_cpu": {
        "database_overload": 0.85,
        "network_partition": 0.30,
        "config_error": 0.15,
        "memory_leak": 0.90,
        "dns_failure": 0.10,
        "auth_service_down": 0.20,
    },
    "db_slow_queries": {
        "database_overload": 0.95,
        "network_partition": 0.25,
        "config_error": 0.30,
        "memory_leak": 0.40,
        "dns_failure": 0.05,
        "auth_service_down": 0.15,
    },
    "intermittent_503s": {
        "database_overload": 0.70,
        "network_partition": 0.80,
        "config_error": 0.45,
        "memory_leak": 0.35,
        "dns_failure": 0.60,
        "auth_service_down": 0.75,
    },
    "config_diff_detected": {
        "database_overload": 0.10,
        "network_partition": 0.05,
        "config_error": 0.95,
        "memory_leak": 0.05,
        "dns_failure": 0.10,
        "auth_service_down": 0.10,
    },
    "memory_growth_trend": {
        "database_overload": 0.30,
        "network_partition": 0.05,
        "config_error": 0.10,
        "memory_leak": 0.92,
        "dns_failure": 0.02,
        "auth_service_down": 0.08,
    },
    "dns_timeout_logs": {
        "database_overload": 0.15,
        "network_partition": 0.40,
        "config_error": 0.20,
        "memory_leak": 0.05,
        "dns_failure": 0.95,
        "auth_service_down": 0.25,
    },
    "auth_latency_spike": {
        "database_overload": 0.20,
        "network_partition": 0.35,
        "config_error": 0.15,
        "memory_leak": 0.10,
        "dns_failure": 0.20,
        "auth_service_down": 0.93,
    },
    "network_packet_loss": {
        "database_overload": 0.25,
        "network_partition": 0.90,
        "config_error": 0.10,
        "memory_leak": 0.05,
        "dns_failure": 0.30,
        "auth_service_down": 0.40,
    },
}

PRIORS: dict[str, float] = {
    "database_overload": 0.30,
    "network_partition": 0.20,
    "config_error": 0.15,
    "memory_leak": 0.10,
    "dns_failure": 0.10,
    "auth_service_down": 0.15,
}

OBSERVATION_ORDER: list[str] = [
    "intermittent_503s",
    "high_cpu",
    "db_slow_queries",
    "memory_growth_trend",
    "network_packet_loss",
    "config_diff_detected",
]


def normalize(dist: dict[str, float]) -> dict[str, float]:
    total = sum(dist.values())
    if total == 0:
        return {k: 1.0 / len(dist) for k in dist}
    return {k: v / total for k, v in dist.items()}


def bayesian_update(
    prior: dict[str, float],
    evidence_name: str,
) -> dict[str, float]:
    likelihood = LIKELIHOODS[evidence_name]
    unnormalized = {
        cause: prior[cause] * likelihood.get(cause, 0.01) for cause in prior
    }
    return normalize(unnormalized)


def kl_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    kl = 0.0
    for k in p:
        pi = p[k]
        qi = q[k]
        if pi > 0 and qi > 0:
            kl += pi * math.log(pi / qi)
    return kl


def information_gain(
    prior: dict[str, float],
    evidence_name: str,
) -> float:
    posterior = bayesian_update(prior, evidence_name)
    return kl_divergence(posterior, prior)


def print_distribution(dist: dict[str, float], title: str) -> None:
    print(f"\n  {title}")
    print(f"  {'Root Cause':25s} {'P(cause)':>10s}  Bar")
    print(f"  {'-' * 25} {'-' * 10}  {'-' * 30}")
    sorted_items = sorted(dist.items(), key=lambda x: -x[1])
    for cause, prob in sorted_items:
        bar_len = int(prob * 50)
        bar = "#" * bar_len
        print(f"  {cause:25s} {prob:10.4f}  {bar}")


def print_shift(
    prior: dict[str, float],
    posterior: dict[str, float],
    evidence_name: str,
) -> None:
    print(f"\n  Evidence observed: {evidence_name}")
    print(f"  {'Root Cause':25s} {'Prior':>10s} {'Posterior':>10s} {'Delta':>10s}")
    print(f"  {'-' * 25} {'-' * 10} {'-' * 10} {'-' * 10}")
    sorted_items = sorted(posterior.items(), key=lambda x: -x[1])
    for cause in [c for c, _ in sorted_items]:
        p_before = prior[cause]
        p_after = posterior[cause]
        delta = p_after - p_before
        sign = "+" if delta >= 0 else ""
        print(f"  {cause:25s} {p_before:10.4f} {p_after:10.4f} {sign}{delta:10.4f}")


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building the Knowledge Graph")
    print("=" * 70)

    for cause in ROOT_CAUSES:
        mem.add(cause, data={"type": "root_cause", "prior": PRIORS[cause]})

    for evidence in EVIDENCE_NODES:
        mem.add(evidence, data={"type": "evidence"})

    edge_count = 0
    for evidence, cause_likelihoods in LIKELIHOODS.items():
        for cause, lh in cause_likelihoods.items():
            weight = round(lh * 10.0, 1)
            mem.link(evidence, cause, label="indicates", weight=weight)
            edge_count += 1

    print(f"  Root cause nodes:  {len(ROOT_CAUSES)}")
    print(f"  Evidence nodes:    {len(EVIDENCE_NODES)}")
    print(f"  Indicator edges:   {edge_count}")
    print(f"  Total graph nodes: {mem.size[0]}")
    print(f"  Total graph edges: {mem.size[1]}")

    print("\n  Evidence-to-cause connectivity:")
    for evidence in EVIDENCE_NODES:
        neighbors = mem.neighbors(evidence, edge_label="indicates", direction="out")
        print(f"    {evidence:25s} -> {len(neighbors)} causes")

    print("=" * 70)
    print("SECTION 2: Setting Prior Beliefs")
    print("=" * 70)

    prior = dict(PRIORS)
    assert abs(sum(prior.values()) - 1.0) < 1e-9, "Priors must sum to 1.0"

    print("\n  Prior distribution (based on historical incident data):")
    print(f"  {'Root Cause':25s} {'Prior':>10s}  Bar")
    print(f"  {'-' * 25} {'-' * 10}  {'-' * 30}")
    sorted_prior = sorted(prior.items(), key=lambda x: -x[1])
    for cause, prob in sorted_prior:
        bar_len = int(prob * 50)
        print(f"  {cause:25s} {prob:10.4f}  {'#' * bar_len}")

    top_prior = max(prior, key=prior.get)
    print(f"\n  Highest prior: {top_prior} ({prior[top_prior]:.4f})")

    entropy = -sum(p * math.log2(p) for p in prior.values() if p > 0)
    max_entropy = math.log2(len(ROOT_CAUSES))
    print(f"  Prior entropy: {entropy:.3f} bits (max {max_entropy:.3f})")
    print()

    print("=" * 70)
    print("SECTION 3: Sequential Evidence-Driven Updates")
    print("=" * 70)

    current = dict(prior)
    all_posteriors: list[tuple[str, dict[str, float]]] = []

    for i, evidence_name in enumerate(OBSERVATION_ORDER, 1):
        pre_update = dict(current)
        current = bayesian_update(current, evidence_name)
        all_posteriors.append((evidence_name, dict(current)))

        print(f"\n  --- Update {i}/{len(OBSERVATION_ORDER)} ---")
        print_shift(pre_update, current, evidence_name)

    print_distribution(current, "Final posterior distribution after all evidence:")
    print()

    print("=" * 70)
    print("SECTION 4: MAP Estimate and Credible Set")
    print("=" * 70)

    sorted_posterior = sorted(current.items(), key=lambda x: -x[1])
    map_cause, map_prob = sorted_posterior[0]
    print(f"\n  MAP (Maximum A Posteriori) estimate:")
    print(f"    {map_cause}: P = {map_prob:.4f}")

    print(f"\n  95% Credible set (highest posterior density):")
    cumulative = 0.0
    credible_members: list[tuple[str, float]] = []
    for cause, prob in sorted_posterior:
        credible_members.append((cause, prob))
        cumulative += prob
        if cumulative >= 0.95:
            break

    print(f"  {'Root Cause':25s} {'P(cause|data)':>14s}  {'Cumulative':>12s}")
    print(f"  {'-' * 25} {'-' * 14}  {'-' * 12}")
    running = 0.0
    for cause, prob in credible_members:
        running += prob
        in_set = "***" if (cause, prob) in credible_members else ""
        print(f"  {cause:25s} {prob:14.4f}  {running:12.4f} {in_set}")
    print(f"\n  Credible set coverage: {cumulative:.4f}")
    print(f"  Credible set size:     {len(credible_members)} / {len(ROOT_CAUSES)}")

    excluded = [
        (c, p) for c, p in sorted_posterior if (c, p) not in credible_members
    ]
    if excluded:
        print(f"\n  Excluded from 95% credible set:")
        for cause, prob in excluded:
            print(f"    {cause:25s} {prob:.4f}")
    print()

    print("=" * 70)
    print("SECTION 5: Bayes Factor Comparison")
    print("=" * 70)

    h1_name, h1_prob = sorted_posterior[0]
    h2_name, h2_prob = sorted_posterior[1]
    prior_odds = prior[h1_name] / prior[h2_name]
    posterior_odds = h1_prob / h2_prob
    bayes_factor = posterior_odds / prior_odds

    print(f"\n  Comparing top two hypotheses:")
    print(f"    H1: {h1_name} (posterior = {h1_prob:.4f})")
    print(f"    H2: {h2_name} (posterior = {h2_prob:.4f})")
    print(f"\n  Prior odds     P(H1)/P(H2):       {prior_odds:.4f}")
    print(f"  Posterior odds  P(H1|D)/P(H2|D):   {posterior_odds:.4f}")
    print(f"  Bayes factor   BF(H1,H2):          {bayes_factor:.2f}")

    if bayes_factor > 100:
        strength = "decisive"
    elif bayes_factor > 10:
        strength = "strong"
    elif bayes_factor > 3:
        strength = "substantial"
    else:
        strength = "weak"
    print(f"  Evidence strength: {strength}")
    print()

    print("  Full pairwise Bayes factor matrix (top cause vs all):")
    print(f"  {'Hypothesis':25s} {'BF':>10s} {'Strength':>12s}")
    print(f"  {'-' * 25} {'-' * 10} {'-' * 12}")
    for cause, prob in sorted_posterior[1:]:
        if prob > 0 and prior[cause] > 0:
            po = h1_prob / prob
            ppo = prior[h1_name] / prior[cause]
            bf = po / ppo
            if bf > 100:
                s = "decisive"
            elif bf > 10:
                s = "strong"
            elif bf > 3:
                s = "substantial"
            else:
                s = "weak"
            print(f"  {cause:25s} {bf:10.2f} {s:>12s}")
    print()

    print("=" * 70)
    print("SECTION 6: Information Gain Analysis")
    print("=" * 70)

    ig_scores: list[tuple[str, float]] = []
    for evidence_name in OBSERVATION_ORDER:
        ig = information_gain(prior, evidence_name)
        ig_scores.append((evidence_name, ig))

    ig_scores.sort(key=lambda x: -x[1])

    print(f"\n  Information gain (KL divergence) of each evidence piece,")
    print(f"  measured independently against the prior distribution:")
    print(f"\n  {'Evidence':25s} {'KL(posterior||prior)':>22s}  Bar")
    print(f"  {'-' * 25} {'-' * 22}  {'-' * 30}")
    max_ig = max(ig for _, ig in ig_scores) if ig_scores else 1.0
    for evidence_name, ig in ig_scores:
        bar_len = int(ig / max_ig * 40) if max_ig > 0 else 0
        print(f"  {evidence_name:25s} {ig:22.4f}  {'#' * bar_len}")

    most_informative = ig_scores[0]
    print(f"\n  Most informative evidence: {most_informative[0]}")
    print(f"  KL divergence:             {most_informative[1]:.4f} bits")

    print("\n  Cumulative information gain across sequential updates:")
    cumulative_kl = 0.0
    running_prior = dict(prior)
    print(f"  {'Step':>4s}  {'Evidence':25s} {'Step KL':>10s} {'Cumulative':>12s}")
    print(f"  {'----'}  {'-' * 25} {'-' * 10} {'-' * 12}")
    for i, (evidence_name, posterior) in enumerate(all_posteriors, 1):
        step_kl = kl_divergence(posterior, running_prior)
        cumulative_kl += step_kl
        print(f"  {i:4d}  {evidence_name:25s} {step_kl:10.4f} {cumulative_kl:12.4f}")
        running_prior = dict(posterior)

    final_entropy = -sum(
        p * math.log2(p) for p in current.values() if p > 0
    )
    print(f"\n  Entropy: prior {entropy:.3f} -> posterior {final_entropy:.3f} bits")
    print(f"  Total information gained: {entropy - final_entropy:.3f} bits")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Graph: {mem.size[0]} nodes, {mem.size[1]} edges")
    print(f"  Root causes analyzed: {len(ROOT_CAUSES)}")
    print(f"  Evidence observed:    {len(OBSERVATION_ORDER)}")
    print(f"  MAP root cause:       {map_cause} (P = {map_prob:.4f})")
    print(f"  95% credible set:     {', '.join(c for c, _ in credible_members)}")
    print(f"  Bayes factor (H1/H2): {bayes_factor:.2f} ({strength})")
    print(f"  Most informative:     {most_informative[0]} (KL = {most_informative[1]:.4f})")
    print(f"  Entropy reduction:    {entropy:.3f} -> {final_entropy:.3f} bits")
    print()


if __name__ == "__main__":
    main()
