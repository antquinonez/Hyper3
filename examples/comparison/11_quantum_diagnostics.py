"""
Managing Competing Hypotheses Under Uncertainty (Standard Library Reimplementation)
====================================================================================

Reimplements Hyper3's quantum diagnostics example using numpy and scipy.
This is an honest comparison: the "quantum" operations reduce to simple
probability operations.

What each operation actually is:
  - Superposition = weighted probability distribution (numpy array)
  - Collapse = np.random.choice with weights
  - Correlation = correlation matrix lookup
  - Interference = constructive/destructive amplitude comparison
  - Density matrix / Von Neumann entropy = scipy.linalg

Run with:
    .venv/bin/python examples/comparison/11_quantum_diagnostics.py
"""

from __future__ import annotations

import numpy as np
from scipy import linalg as sla


def build_incident_graph() -> tuple[dict, list, list, list, list]:
    root_causes = {
        "db_connection_pool_exhaustion": {
            "category": "infrastructure",
            "severity": "high",
            "mttr_min": 15,
            "frequency": "monthly",
        },
        "dns_resolution_failure": {
            "category": "network",
            "severity": "critical",
            "mttr_min": 30,
            "frequency": "quarterly",
        },
        "certificate_expiry": {
            "category": "security",
            "severity": "critical",
            "mttr_min": 60,
            "frequency": "yearly",
        },
        "memory_leak_api": {
            "category": "application",
            "severity": "high",
            "mttr_min": 20,
            "frequency": "weekly",
        },
        "kafka_partition_rebalance": {
            "category": "infrastructure",
            "severity": "medium",
            "mttr_min": 10,
            "frequency": "weekly",
        },
        "deploy_bad_config": {
            "category": "deployment",
            "severity": "high",
            "mttr_min": 5,
            "frequency": "daily",
        },
    }

    symptoms = {
        "error_rate_spike": {"type": "symptom", "metric": "errors/sec", "observed": True},
        "latency_increase": {"type": "symptom", "metric": "p99_ms", "observed": True},
        "connection_timeouts": {"type": "symptom", "metric": "timeout_count", "observed": True},
        "memory_pressure": {"type": "symptom", "metric": "heap_used_pct", "observed": True},
        "cpu_throttling": {"type": "symptom", "metric": "cpu_pct", "observed": False},
        "ssl_handshake_failures": {"type": "symptom", "metric": "ssl_errors", "observed": True},
        "service_restart_loop": {"type": "symptom", "metric": "restart_count", "observed": False},
        "queue_backlog": {"type": "symptom", "metric": "queue_depth", "observed": True},
        "partial_outage": {"type": "symptom", "metric": "availability_pct", "observed": True},
    }

    evidence = {
        "log_connection_refused": {"source": "app_logs", "timestamp": "T+0m", "confidence": 0.85},
        "log_ssl_cert_invalid": {"source": "app_logs", "timestamp": "T+1m", "confidence": 0.92},
        "metric_db_pool_active_95pct": {"source": "metrics", "timestamp": "T+2m", "confidence": 0.78},
        "metric_dns_timeout_5s": {"source": "metrics", "timestamp": "T+3m", "confidence": 0.60},
        "metric_heap_growth_trend": {"source": "metrics", "timestamp": "T+5m", "confidence": 0.70},
        "metric_kafka_consumer_lag": {"source": "metrics", "timestamp": "T+4m", "confidence": 0.55},
        "alert_circuit_breaker_open": {"source": "alerts", "timestamp": "T+2m", "confidence": 0.90},
        "alert_ssl_expiry_0_days": {"source": "alerts", "timestamp": "T+1m", "confidence": 0.95},
        "deploy_last_commit_config_change": {"source": "ci_cd", "timestamp": "T-5m", "confidence": 0.88},
        "log_dns_resolution_slow": {"source": "app_logs", "timestamp": "T+3m", "confidence": 0.65},
        "metric_gc_pause_increase": {"source": "metrics", "timestamp": "T+6m", "confidence": 0.50},
        "log_kafka_rebalance_event": {"source": "kafka_logs", "timestamp": "T+4m", "confidence": 0.75},
        "evidence_recent_deploy_rollback": {"source": "deploy_logs", "timestamp": "T-3m", "confidence": 0.40},
        "evidence_no_dns_issues_other_services": {"source": "monitoring", "timestamp": "T+5m", "confidence": 0.80},
    }

    cause_symptom_links = [
        ("db_connection_pool_exhaustion", ["connection_timeouts", "error_rate_spike", "partial_outage", "queue_backlog"]),
        ("dns_resolution_failure", ["connection_timeouts", "latency_increase", "error_rate_spike", "partial_outage"]),
        ("certificate_expiry", ["ssl_handshake_failures", "connection_timeouts", "error_rate_spike", "partial_outage"]),
        ("memory_leak_api", ["memory_pressure", "latency_increase", "error_rate_spike", "cpu_throttling", "service_restart_loop"]),
        ("kafka_partition_rebalance", ["queue_backlog", "latency_increase", "partial_outage"]),
        ("deploy_bad_config", ["error_rate_spike", "service_restart_loop", "partial_outage", "connection_timeouts"]),
    ]

    evidence_cause_links = [
        ("log_connection_refused", ["db_connection_pool_exhaustion", "certificate_expiry"]),
        ("log_ssl_cert_invalid", ["certificate_expiry"]),
        ("metric_db_pool_active_95pct", ["db_connection_pool_exhaustion"]),
        ("metric_dns_timeout_5s", ["dns_resolution_failure"]),
        ("metric_heap_growth_trend", ["memory_leak_api"]),
        ("metric_kafka_consumer_lag", ["kafka_partition_rebalance"]),
        ("alert_circuit_breaker_open", ["db_connection_pool_exhaustion", "dns_resolution_failure", "deploy_bad_config"]),
        ("alert_ssl_expiry_0_days", ["certificate_expiry"]),
        ("deploy_last_commit_config_change", ["deploy_bad_config"]),
        ("log_dns_resolution_slow", ["dns_resolution_failure"]),
        ("metric_gc_pause_increase", ["memory_leak_api"]),
        ("log_kafka_rebalance_event", ["kafka_partition_rebalance"]),
        ("evidence_recent_deploy_rollback", ["deploy_bad_config"]),
        ("evidence_no_dns_issues_other_services", ["dns_resolution_failure"]),
    ]

    return root_causes, symptoms, evidence, cause_symptom_links, evidence_cause_links


def shannon_entropy(probs: np.ndarray) -> float:
    p = probs[probs > 0]
    return float(-np.sum(p * np.log2(p)))


def von_neumann_entropy(rho: np.ndarray) -> float:
    eigenvalues = np.real(sla.eigvalsh(rho))
    eigenvalues = eigenvalues[eigenvalues > 1e-15]
    return float(-np.sum(eigenvalues * np.log2(eigenvalues)))


def section_1_build_graph() -> list[str]:
    print("=" * 70)
    print("SECTION 1: Building the Incident Knowledge Graph")
    print("=" * 70)
    root_causes, symptoms, evidence, csl, ecl = build_incident_graph()
    print(f"  Root cause hypotheses: {len(root_causes)}")
    print(f"  Symptom nodes: {len(symptoms)}")
    print(f"  Evidence nodes: {len(evidence)}")
    print(f"  Cause-symptom links: {len(csl)}")
    print(f"  Evidence-cause links: {len(ecl)}")
    hypotheses = [
        "db_connection_pool_exhaustion",
        "dns_resolution_failure",
        "certificate_expiry",
        "memory_leak_api",
        "kafka_partition_rebalance",
    ]
    print(f"  Active hypotheses: {len(hypotheses)}")
    print()
    return hypotheses


def section_2_superposition(hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 2: Superposition = Weighted Probability Distribution")
    print("=" * 70)
    print()
    print("  What it actually does: creates a numpy array of weights,")
    print("  normalizes so total = 1. Uniform prior means equal probability.")
    print()

    n = len(hypotheses)
    amplitudes = np.ones(n) / np.sqrt(n)
    probs = amplitudes ** 2

    print(f"  Uniform superposition of {n} hypotheses (amplitudes = 1/sqrt({n})):")
    for h, amp, p in zip(hypotheses, amplitudes, probs):
        print(f"    {h:40s} amp={amp:.4f}  prob={p:.4f}")
    print(f"\n  Total probability: {probs.sum():.4f}")
    print(f"  Shannon entropy: {shannon_entropy(probs):.4f} bits")
    print()


def section_3_collapse(hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 3: Collapse = np.random.choice with Weights")
    print("=" * 70)
    print()
    print("  What it actually does: multiplies uniform prior by context weights,")
    print("  normalizes, then samples. This is just np.random.choice(p=probs).")
    print()

    evidence_weights = {
        "certificate_expiry": 3.5,
        "dns_resolution_failure": 1.8,
        "db_connection_pool_exhaustion": 1.5,
        "memory_leak_api": 1.0,
        "kafka_partition_rebalance": 0.8,
    }

    print("  Evidence context weights (from SSL alert, cert logs, etc.):")
    for label, w in sorted(evidence_weights.items(), key=lambda x: -x[1]):
        print(f"    {label:40s} weight={w:.1f}")

    context_arr = np.array([evidence_weights[h] for h in hypotheses])
    posterior = context_arr / context_arr.sum()

    print("\n  Posterior distribution (uniform prior x context, normalized):")
    for h, p in zip(hypotheses, posterior):
        print(f"    {h:40s} {p:.1%}")

    print("\n  Running weighted sampling 1000 times...")
    n_trials = 1000
    rng = np.random.default_rng(42)
    samples = rng.choice(hypotheses, size=n_trials, p=posterior)

    counts: dict[str, int] = {}
    for s in samples:
        counts[s] = counts.get(s, 0) + 1

    print(f"\n  Sampling frequency over {n_trials} trials:")
    for label in sorted(counts, key=counts.get, reverse=True):
        bar = "#" * (counts[label] // 10)
        print(f"    {label:40s} {counts[label]:4d} ({counts[label]/n_trials:.1%}) {bar}")

    print("\n  This IS weighted random sampling. No quantum mechanics involved.")
    print()


def section_4_correlation() -> None:
    print("=" * 70)
    print("SECTION 4: Correlation = Correlation Matrix Lookup")
    print("=" * 70)
    print()
    print("  What it actually does: stores a dict of pairwise correlations")
    print("  between hypothesis groups. When one is observed, look up the")
    print("  correlated values. This is a lookup table, not physics.")
    print()

    group_a = ["certificate_expiry", "dns_resolution_failure"]
    group_b = ["memory_leak_api", "db_connection_pool_exhaustion"]

    correlations = {
        ("certificate_expiry", "memory_leak_api"): 0.2,
        ("certificate_expiry", "db_connection_pool_exhaustion"): -0.1,
        ("dns_resolution_failure", "memory_leak_api"): 0.15,
        ("dns_resolution_failure", "db_connection_pool_exhaustion"): 0.6,
    }

    print(f"  Group A: {group_a}")
    print(f"  Group B: {group_b}")
    print(f"\n  Correlations (positive = co-occur, negative = mutually exclusive):")
    for (a, b), corr in correlations.items():
        print(f"    {a:25s} <-> {b:30s}: {corr:+.2f}")

    print(f"\n  Correlated prediction (observe certificate_expiry):")
    observed = "certificate_expiry"
    for b_node in group_b:
        corr = correlations.get((observed, b_node), 0.0)
        prediction = "co-occurring" if corr > 0 else ("anti-correlated" if corr < 0 else "neutral")
        print(f"    {b_node}: correlation={corr:+.2f} ({prediction})")
    print()


def section_5_interference() -> None:
    print("=" * 70)
    print("SECTION 5: Interference = Amplitude Arithmetic")
    print("=" * 70)
    print()
    print("  What it actually does: adds amplitudes from multiple evidence")
    print("  sources. Same sign = constructive (reinforcing), opposite =")
    print("  destructive (contradicting). Compare |sum|^2 vs sum(|amp|^2).")
    print()

    print("  Constructive case: two sources both support the same hypothesis")
    amps_c = np.array([0.7, 0.5])
    net_c = amps_c.sum()
    coherent_sum = abs(net_c) ** 2
    incoherent_sum = np.sum(np.abs(amps_c) ** 2)
    kind_c = "CONSTRUCTIVE" if coherent_sum > incoherent_sum else "DESTRUCTIVE"
    print(f"    amplitudes: {amps_c}")
    print(f"    net amplitude: {net_c:.4f}")
    print(f"    |sum|^2 = {coherent_sum:.4f}, sum(|amp|^2) = {incoherent_sum:.4f}")
    print(f"    -> [{kind_c}] evidence reinforces the hypothesis")

    print("\n  Destructive case: one source supports, another contradicts")
    amps_d = np.array([0.7, -0.5])
    net_d = amps_d.sum()
    coherent_sum_d = abs(net_d) ** 2
    incoherent_sum_d = np.sum(np.abs(amps_d) ** 2)
    kind_d = "CONSTRUCTIVE" if coherent_sum_d > incoherent_sum_d else "DESTRUCTIVE"
    print(f"    amplitudes: {amps_d}")
    print(f"    net amplitude: {net_d:.4f}")
    print(f"    |sum|^2 = {coherent_sum_d:.4f}, sum(|amp|^2) = {incoherent_sum_d:.4f}")
    print(f"    -> [{kind_d}] evidence contradicts the hypothesis")

    print("\n  Takeaway: agreeing evidence amplifies, conflicting evidence diminishes.")
    print("  This is just arithmetic on signed floats. Nothing quantum about it.")
    print()


def section_6_entropy(hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 6: Density Matrix and Von Neumann Entropy")
    print("=" * 70)
    print()
    print("  The density matrix rho = |psi><psi| is the outer product of the")
    print("  amplitude vector. Von Neumann entropy S = -Tr(rho log2 rho).")
    print()
    print("  For pure states, rho has one nonzero eigenvalue (=1), so entropy=0.")
    print("  This is a math property: pure state is fully known. Entropy becomes")
    print("  meaningful for MIXED states, where it equals Shannon entropy.")
    print()

    rho_confident = np.zeros((3, 3), dtype=complex)
    basis_confident = [
        (np.array([1, 0, 0], dtype=complex), 0.90),
        (np.array([0, 1, 0], dtype=complex), 0.08),
        (np.array([0, 0, 1], dtype=complex), 0.02),
    ]
    for vec, weight in basis_confident:
        rho_confident += weight * np.outer(vec, vec.conj())
    entropy_confident = von_neumann_entropy(rho_confident)
    print(f"  Mixed state (one hypothesis dominates at 90%):")
    print(f"    Weights: 0.90, 0.08, 0.02")
    print(f"    Von Neumann entropy: {entropy_confident:.6f} bits (low = confident)")
    print(f"    Shannon entropy:     {shannon_entropy(np.array([0.90, 0.08, 0.02])):.6f} bits")

    rho_moderate = np.zeros((3, 3), dtype=complex)
    basis_moderate = [
        (np.array([1, 0, 0], dtype=complex), 0.6),
        (np.array([0, 1, 0], dtype=complex), 0.3),
        (np.array([0, 0, 1], dtype=complex), 0.1),
    ]
    for vec, weight in basis_moderate:
        rho_moderate += weight * np.outer(vec, vec.conj())
    entropy_moderate = von_neumann_entropy(rho_moderate)
    print(f"\n  Mixed state (moderate uncertainty):")
    print(f"    Weights: 0.60, 0.30, 0.10")
    print(f"    Von Neumann entropy: {entropy_moderate:.6f} bits")
    print(f"    Shannon entropy:     {shannon_entropy(np.array([0.6, 0.3, 0.1])):.6f} bits")

    rho_max = np.eye(4, dtype=complex) / 4
    entropy_max = von_neumann_entropy(rho_max)
    print(f"\n  Maximally uncertain (4 hypotheses, equal weight):")
    print(f"    Von Neumann entropy: {entropy_max:.6f} bits = log2(4) = {np.log2(4):.6f}")

    print("\n  Quick check: pure state entropy (should be 0)")
    amps = np.array([0.6, 0.3, 0.1], dtype=complex)
    psi = amps / np.linalg.norm(amps)
    rho_pure = np.outer(psi, psi.conj())
    entropy_pure = von_neumann_entropy(rho_pure)
    probs = np.abs(psi) ** 2
    print(f"    Von Neumann entropy: {entropy_pure:.10f} bits (effectively 0)")
    print(f"    Shannon entropy:     {shannon_entropy(probs):.6f} bits")
    print(f"    --> These differ! Pure state VNE=0, Shannon>0. They are NOT the same.")

    print()
    print("  Bottom line: Von Neumann entropy measures uncertainty of the STATE")
    print("  (pure vs mixed), not uncertainty of the probability distribution.")
    print("  For practical hypothesis uncertainty, use Shannon entropy.")
    print()


def section_7_bayesian_comparison() -> None:
    print("=" * 70)
    print("SECTION 7: Honest Comparison with Bayesian Inference")
    print("=" * 70)
    print()
    print("  The quantum formalism is mathematically equivalent to Bayesian")
    print("  hypothesis ranking for this use case:")
    print()
    print("  1. Superposition = prior distribution over hypotheses")
    print("  2. Collapse with context = sampling from posterior (context = likelihood)")
    print("  3. Correlation = structured prior over correlated hypotheses")
    print("  4. Interference = Bayes factor aggregation (agreeing/diverging evidence)")
    print("  5. Von Neumann entropy = for mixed states, equals Shannon entropy")
    print()
    print("  This reimplementation uses:")
    print("    - np.ones() / sqrt(n) for uniform superposition")
    print("    - np.random.choice(p=weights) for collapse")
    print("    - dict[tuple, float] for correlations")
    print("    - float arithmetic for interference")
    print("    - scipy.linalg.eigvalsh + log2 for von Neumann entropy")
    print()
    print("  Advantages of the quantum-style API:")
    print("    - Natural syntax for correlated hypotheses (correlation)")
    print("    - Built-in uncertainty quantification (entropy)")
    print("    - Density matrix gives a full covariance-like state descriptor")
    print()
    print("  Disadvantages:")
    print("    - Adds mathematical overhead for what is fundamentally Bayesian updating")
    print("    - No actual quantum speedup (this runs on classical hardware)")
    print("    - Von Neumann entropy is 0 for pure states, which is counterintuitive")
    print()
    print("  Bottom line: the quantum API is a convenience layer over classical")
    print("  probability. For simple prior-posterior updates, plain numpy is clearer.")
    print()


def main():
    hypotheses = section_1_build_graph()
    section_2_superposition(hypotheses)
    section_3_collapse(hypotheses)
    section_4_correlation()
    section_5_interference()
    section_6_entropy(hypotheses)
    section_7_bayesian_comparison()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Superposition = numpy array of weights (prior distribution)")
    print("  2. Collapse = np.random.choice(p=weights) (weighted sampling)")
    print("  3. Correlation = dict of pairwise correlations (lookup table)")
    print("  4. Interference = float arithmetic on signed amplitudes")
    print("  5. Entropy = scipy.linalg.eigvalsh (meaningful for mixed states)")
    print("  6. For this use case, quantum formalism ~= Bayesian inference")
    print("  7. This reimplementation: ~200 lines of numpy/scipy vs ~600 Hyper3")
    print()


if __name__ == "__main__":
    main()
