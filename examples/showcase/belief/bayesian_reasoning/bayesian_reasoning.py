"""
Bayesian Belief Updating for Incident Root Cause Analysis
==========================================================

Build a knowledge graph linking potential root causes to observable evidence
for a production outage, then perform sequential Bayesian updates as evidence
arrives using Hyper3's Bayesian subsystem (set_prior, update_belief, map_estimate,
bayes_factor, credible_set). Demonstrates prior specification, posterior
computation, MAP estimation, credible sets, Bayes factor comparison, and
information gain (KL divergence) ranking of evidence.

Run with:
    .venv/bin/python examples/showcase/belief/bayesian_reasoning/bayesian_reasoning.py
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


def _kl_bits(p: dict[str, float], q: dict[str, float]) -> float:
    kl = 0.0
    for k in p:
        pi, qi = p[k], q[k]
        if pi > 0 and qi > 0:
            kl += pi * math.log2(pi / qi)
    return kl


def _bayesian_update(
    prior: dict[str, float], evidence_name: str,
) -> dict[str, float]:
    lh = LIKELIHOODS[evidence_name]
    unnorm = {cause: prior[cause] * lh.get(cause, 0.01) for cause in prior}
    total = sum(unnorm.values())
    if total == 0:
        return {k: 1.0 / len(unnorm) for k in unnorm}
    return {k: v / total for k, v in unnorm.items()}


def print_distribution(dist: dict[str, float], title: str) -> None:
    print(f"\n  {title}")
    print(f"  {'Root Cause':25s} {'P(cause)':>10s}  Bar")
    print(f"  {'-' * 25} {'-' * 10}  {'-' * 30}")
    for cause, prob in sorted(dist.items(), key=lambda x: -x[1]):
        bar_len = int(prob * 50)
        print(f"  {cause:25s} {prob:10.4f}  {'#' * bar_len}")


def print_shift(
    prior: dict[str, float],
    posterior: dict[str, float],
    evidence_name: str,
) -> None:
    print(f"\n  Evidence observed: {evidence_name}")
    print(f"  {'Root Cause':25s} {'Prior':>10s} {'Posterior':>10s} {'Delta':>10s}")
    print(f"  {'-' * 25} {'-' * 10} {'-' * 10} {'-' * 10}")
    for cause in sorted(posterior, key=lambda k: posterior[k], reverse=True):
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

    print("\n" + "=" * 70)
    print("SECTION 2: Setting Prior Beliefs (Bayesian Prior)")
    print("=" * 70)

    prior_weights = [PRIORS[c] for c in ROOT_CAUSES]
    mem.add("outage_diagnosis", data={"type": "bayesian_analysis"})
    mem.bayes.set_prior("outage_diagnosis", outcomes=ROOT_CAUSES, weights=prior_weights)

    label_map: dict[str, str] = {}
    for label in ROOT_CAUSES:
        nid = mem.resolve_id(label)
        if nid:
            label_map[nid] = label

    prior = mem.bayes.get("outage_diagnosis")
    prior_dict: dict[str, float] = {}
    if prior:
        print("\n  Prior distribution (based on historical incident data):")
        print(f"  {'Root Cause':25s} {'Prior':>10s}  Bar")
        print(f"  {'-' * 25} {'-' * 10}  {'-' * 30}")
        for oid, prob in sorted(prior.outcomes.items(), key=lambda x: -x[1]):
            label = label_map.get(oid, oid[:12])
            prior_dict[label] = prob
            bar_len = int(prob * 50)
            print(f"  {label:25s} {prob:10.4f}  {'#' * bar_len}")

    top_prior = max(prior_dict, key=lambda k: prior_dict[k])
    print(f"\n  Highest prior: {top_prior} ({prior_dict[top_prior]:.4f})")

    prior_entropy = prior.entropy() if prior else 0.0
    max_entropy = math.log2(len(ROOT_CAUSES))
    print(f"  Prior entropy: {prior_entropy:.3f} bits (max {max_entropy:.3f})")
    print()

    print("=" * 70)
    print("SECTION 3: Sequential Evidence-Driven Updates")
    print("=" * 70)

    all_step_results: list[tuple[str, dict[str, float], float]] = []
    prev_dict = dict(prior_dict)

    for i, evidence_name in enumerate(OBSERVATION_ORDER, 1):
        result = mem.bayes.update(
            "outage_diagnosis",
            evidence=evidence_name,
            likelihoods=LIKELIHOODS[evidence_name],
        )

        current_dict: dict[str, float] = {}
        if result.posterior:
            for oid, prob in result.posterior.outcomes.items():
                label = label_map.get(oid, oid[:12])
                current_dict[label] = prob

        print(f"\n  --- Update {i}/{len(OBSERVATION_ORDER)} ---")
        print_shift(prev_dict, current_dict, evidence_name)
        if result.kl_divergence > 0:
            print(f"    KL divergence: {result.kl_divergence:.4f} bits")

        all_step_results.append((evidence_name, dict(current_dict), result.kl_divergence))
        prev_dict = dict(current_dict)

    print_distribution(prev_dict, "Final posterior distribution after all evidence:")
    print()

    print("=" * 70)
    print("SECTION 4: MAP Estimate and Credible Set")
    print("=" * 70)

    map_est = mem.bayes.map("outage_diagnosis")
    map_prob = prev_dict.get(map_est, 0.0) if map_est else 0.0
    print("\n  MAP (Maximum A Posteriori) estimate:")
    print(f"    {map_est}: P = {map_prob:.4f}")

    credible = mem.bayes.credible("outage_diagnosis", level=0.95)

    sorted_posterior = sorted(prev_dict.items(), key=lambda x: -x[1])
    print("\n  95% Credible set (highest posterior density):")
    print(f"  {'Root Cause':25s} {'P(cause|data)':>14s}  {'Cumulative':>12s}")
    print(f"  {'-' * 25} {'-' * 14}  {'-' * 12}")
    cumulative = 0.0
    for cause, prob in sorted_posterior:
        cumulative += prob
        in_set = "***" if cause in credible else ""
        print(f"  {cause:25s} {prob:14.4f}  {cumulative:12.4f} {in_set}")
    print(f"\n  Credible set coverage: {cumulative:.4f}")
    print(f"  Credible set size:     {len(credible)} / {len(ROOT_CAUSES)}")

    excluded = [(c, p) for c, p in sorted_posterior if c not in credible]
    if excluded:
        print("\n  Excluded from 95% credible set:")
        for cause, prob in excluded:
            print(f"    {cause:25s} {prob:.4f}")
    print()

    print("=" * 70)
    print("SECTION 5: Bayes Factor Comparison")
    print("=" * 70)

    sorted_post = sorted(prev_dict.items(), key=lambda x: -x[1])
    h1_name, h1_prob = sorted_post[0]
    h2_name, h2_prob = sorted_post[1]

    bf_top2 = mem.bayes.factor(
        "outage_diagnosis",
        hyp_a=h1_name,
        hyp_b=h2_name,
    )

    print("\n  Comparing top two hypotheses:")
    print(f"    H1: {h1_name} (posterior = {h1_prob:.4f})")
    print(f"    H2: {h2_name} (posterior = {h2_prob:.4f})")
    print(f"\n  Prior odds     P(H1)/P(H2):       {PRIORS[h1_name]/PRIORS[h2_name]:.4f}")
    print(f"  Posterior odds  P(H1|D)/P(H2|D):   {h1_prob/h2_prob:.4f}")
    if bf_top2 is not None:
        print(f"  Bayes factor   BF(H1,H2):          {bf_top2:.2f}")

    if bf_top2 is not None:
        if bf_top2 > 100:
            strength = "decisive"
        elif bf_top2 > 10:
            strength = "strong"
        elif bf_top2 > 3:
            strength = "substantial"
        else:
            strength = "weak"
        print(f"  Evidence strength: {strength}")
    print()

    print("  Full pairwise Bayes factor matrix (top cause vs all):")
    print(f"  {'Hypothesis':25s} {'BF':>10s} {'Strength':>12s}")
    print(f"  {'-' * 25} {'-' * 10} {'-' * 12}")
    for cause, prob in sorted_post[1:]:
        if prob > 0 and PRIORS[cause] > 0:
            bf = mem.bayes.factor(
                "outage_diagnosis",
                hyp_a=h1_name,
                hyp_b=cause,
            )
            if bf is not None:
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
        posterior = _bayesian_update(dict(prior_dict), evidence_name)
        ig = _kl_bits(posterior, prior_dict)
        ig_scores.append((evidence_name, ig))

    ig_scores.sort(key=lambda x: -x[1])

    print("\n  Information gain (KL divergence) of each evidence piece,")
    print("  measured independently against the prior distribution:")
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
    print(f"  {'Step':>4s}  {'Evidence':25s} {'Step KL':>10s} {'Cumulative':>12s}")
    print(f"  {'----'}  {'-' * 25} {'-' * 10} {'-' * 12}")
    for i, (ev_name, _, step_kl) in enumerate(all_step_results, 1):
        cumulative_kl += step_kl
        print(f"  {i:4d}  {ev_name:25s} {step_kl:10.4f} {cumulative_kl:12.4f}")

    final_entropy = -sum(
        p * math.log2(p) for p in prev_dict.values() if p > 0
    )
    print(f"\n  Entropy: prior {prior_entropy:.3f} -> posterior {final_entropy:.3f} bits")
    print(f"  Total information gained: {prior_entropy - final_entropy:.3f} bits")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Graph: {mem.size[0]} nodes, {mem.size[1]} edges")
    print(f"  Root causes analyzed: {len(ROOT_CAUSES)}")
    print(f"  Evidence observed:    {len(OBSERVATION_ORDER)}")
    print(f"  MAP root cause:       {map_est} (P = {map_prob:.4f})")
    print(f"  95% credible set:     {', '.join(credible)}")
    if bf_top2 is not None:
        print(f"  Bayes factor (H1/H2): {bf_top2:.2f} ({strength})")
    print(f"  Most informative:     {most_informative[0]} (KL = {most_informative[1]:.4f})")
    print(f"  Entropy reduction:    {prior_entropy:.3f} -> {final_entropy:.3f} bits")
    print()


if __name__ == "__main__":
    main()
