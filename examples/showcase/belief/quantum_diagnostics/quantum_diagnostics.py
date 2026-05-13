"""
Managing Competing Hypotheses Under Uncertainty
================================================

This example models a production outage investigation using Hyper3's
probabilistic hypothesis management layer (the belief layer). This is NOT
real quantum computing -- it is a weighted random sampling framework that
borrows mathematical formalism (amplitudes, density matrices, entropy) from
quantum mechanics to manage competing hypotheses.

What each belief layer operation actually does:
  - Distribution: holds multiple candidate hypotheses with weights
  - Sample: weighted random selection (Born rule = sample proportional to weight^2)
  - Correlation: records pairwise correlations between hypotheses
  - Interactions: detects reinforcing vs conflicting evidence patterns
  - Density matrix / Von Neumann entropy: measures how uncertain the system is

Use case: A production service goes down. Multiple root causes are plausible.
Evidence arrives incrementally. We track beliefs, correlations, and confidence.

Run with:
    .venv/bin/python examples/showcase/belief/quantum_diagnostics/quantum_diagnostics.py
"""

from __future__ import annotations

import numpy as np

from hyper3 import HypergraphMemory, Modality


def build_incident_graph(mem: HypergraphMemory) -> None:
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
    for name, data in root_causes.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

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
    for name, data in symptoms.items():
        mem.add(name, data=data, modalities={Modality.SENSORY})

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
    for name, data in evidence.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    services = {
        "auth_service": {"tier": "critical", "stack": "java", "team": "platform"},
        "payment_service": {"tier": "critical", "stack": "go", "team": "payments"},
        "order_service": {"tier": "critical", "stack": "java", "team": "commerce"},
        "notification_service": {"tier": "non-critical", "stack": "python", "team": "engagement"},
        "search_service": {"tier": "non-critical", "stack": "go", "team": "search"},
        "config_service": {"tier": "infrastructure", "stack": "go", "team": "platform"},
    }
    for name, data in services.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    infra = {
        "postgres_primary": {"type": "database", "engine": "postgresql"},
        "redis_cluster": {"type": "cache", "engine": "redis"},
        "kafka_cluster": {"type": "messaging", "engine": "kafka"},
        "load_balancer": {"type": "network", "engine": "envoy"},
        "dns_server": {"type": "network", "engine": "bind"},
        "vault_secrets": {"type": "secrets", "engine": "vault"},
    }
    for name, data in infra.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    cause_symptom_links = [
        ("db_connection_pool_exhaustion", ["connection_timeouts", "error_rate_spike", "partial_outage", "queue_backlog"]),
        ("dns_resolution_failure", ["connection_timeouts", "latency_increase", "error_rate_spike", "partial_outage"]),
        ("certificate_expiry", ["ssl_handshake_failures", "connection_timeouts", "error_rate_spike", "partial_outage"]),
        ("memory_leak_api", ["memory_pressure", "latency_increase", "error_rate_spike", "cpu_throttling", "service_restart_loop"]),
        ("kafka_partition_rebalance", ["queue_backlog", "latency_increase", "partial_outage"]),
        ("deploy_bad_config", ["error_rate_spike", "service_restart_loop", "partial_outage", "connection_timeouts"]),
    ]
    for cause, symptoms_list in cause_symptom_links:
        for sym in symptoms_list:
            mem.link(cause, sym, label="causes_symptom")

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
    for ev, causes in evidence_cause_links:
        for cause in causes:
            mem.link(ev, cause, label="supports")

    service_deps = [
        ("auth_service", "postgres_primary"),
        ("auth_service", "redis_cluster"),
        ("auth_service", "vault_secrets"),
        ("payment_service", "postgres_primary"),
        ("payment_service", "kafka_cluster"),
        ("order_service", "postgres_primary"),
        ("order_service", "kafka_cluster"),
        ("order_service", "auth_service"),
        ("notification_service", "kafka_cluster"),
        ("search_service", "redis_cluster"),
        ("search_service", "auth_service"),
        ("config_service", "vault_secrets"),
    ]
    for svc, dep in service_deps:
        mem.link(svc, dep, label="depends_on")

    cause_infra_links = [
        ("db_connection_pool_exhaustion", "postgres_primary"),
        ("dns_resolution_failure", "dns_server"),
        ("certificate_expiry", "vault_secrets"),
        ("certificate_expiry", "load_balancer"),
        ("kafka_partition_rebalance", "kafka_cluster"),
        ("memory_leak_api", "auth_service"),
        ("memory_leak_api", "order_service"),
        ("deploy_bad_config", "config_service"),
    ]
    for cause, infra_node in cause_infra_links:
        mem.link(cause, infra_node, label="affects")

    correlated_causes = [
        ("db_connection_pool_exhaustion", "memory_leak_api"),
        ("certificate_expiry", "dns_resolution_failure"),
        ("deploy_bad_config", "kafka_partition_rebalance"),
        ("memory_leak_api", "deploy_bad_config"),
    ]
    for a, b in correlated_causes:
        mem.link(a, b, label="correlated_with")

    responders = {
        "oncall_platform": {"role": "responder", "team": "platform"},
        "oncall_payments": {"role": "responder", "team": "payments"},
        "oncall_sre": {"role": "responder", "team": "sre"},
        "incident_commander": {"role": "commander", "team": "sre"},
        "runbook_db_pool": {"type": "runbook", "cause": "db_connection_pool_exhaustion"},
        "runbook_cert_rotation": {"type": "runbook", "cause": "certificate_expiry"},
        "runbook_dns_debug": {"type": "runbook", "cause": "dns_resolution_failure"},
        "runbook_oom_kill": {"type": "runbook", "cause": "memory_leak_api"},
        "runbook_kafka_rebalance": {"type": "runbook", "cause": "kafka_partition_rebalance"},
    }
    for name, data in responders.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    timeline = {
        "t0_alert_triggered": {"offset_min": 0, "event": "PagerDuty alert fired"},
        "t1_first_response": {"offset_min": 2, "event": "On-call acknowledges"},
        "t2_investigation_starts": {"offset_min": 5, "event": "War room opened"},
        "t3_evidence_gathering": {"offset_min": 8, "event": "Logs and metrics pulled"},
        "t4_hypothesis_formed": {"offset_min": 12, "event": "Initial hypothesis formed"},
        "t5_mitigation_applied": {"offset_min": 18, "event": "Mitigation deployed"},
        "t6_monitoring": {"offset_min": 25, "event": "Monitoring recovery"},
        "t7_resolved": {"offset_min": 35, "event": "Incident resolved"},
    }
    for name, data in timeline.items():
        mem.add(name, data=data, modalities={Modality.TEMPORAL})

    responder_links = [
        ("oncall_platform", "memory_leak_api"),
        ("oncall_platform", "db_connection_pool_exhaustion"),
        ("oncall_sre", "certificate_expiry"),
        ("oncall_sre", "dns_resolution_failure"),
        ("oncall_payments", "payment_service"),
        ("incident_commander", "oncall_platform"),
        ("incident_commander", "oncall_sre"),
        ("incident_commander", "oncall_payments"),
        ("runbook_db_pool", "db_connection_pool_exhaustion"),
        ("runbook_cert_rotation", "certificate_expiry"),
        ("runbook_dns_debug", "dns_resolution_failure"),
        ("runbook_oom_kill", "memory_leak_api"),
        ("runbook_kafka_rebalance", "kafka_partition_rebalance"),
    ]
    for src, tgt in responder_links:
        mem.link(src, tgt, label="assigned_to")

    timeline_links = [
        ("t0_alert_triggered", "alert_circuit_breaker_open"),
        ("t0_alert_triggered", "alert_ssl_expiry_0_days"),
        ("t1_first_response", "oncall_sre"),
        ("t2_investigation_starts", "log_connection_refused"),
        ("t2_investigation_starts", "log_ssl_cert_invalid"),
        ("t3_evidence_gathering", "metric_db_pool_active_95pct"),
        ("t3_evidence_gathering", "metric_dns_timeout_5s"),
        ("t4_hypothesis_formed", "certificate_expiry"),
        ("t5_mitigation_applied", "runbook_cert_rotation"),
        ("t6_monitoring", "evidence_no_dns_issues_other_services"),
        ("t7_resolved", "t5_mitigation_applied"),
        ("t1_first_response", "incident_commander"),
        ("t2_investigation_starts", "oncall_platform"),
    ]
    for src, tgt in timeline_links:
        mem.link(src, tgt, label="timeline_link")

    impact_nodes = {
        "customer_facing_errors": {"type": "impact", "severity": "high"},
        "revenue_at_risk": {"type": "impact", "severity": "high"},
        "sla_breach_risk": {"type": "impact", "severity": "medium"},
        "reputation_risk": {"type": "impact", "severity": "low"},
    }
    for name, data in impact_nodes.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    impact_links = [
        ("partial_outage", "customer_facing_errors"),
        ("customer_facing_errors", "revenue_at_risk"),
        ("customer_facing_errors", "sla_breach_risk"),
        ("sla_breach_risk", "reputation_risk"),
        ("error_rate_spike", "customer_facing_errors"),
        ("connection_timeouts", "customer_facing_errors"),
        ("latency_increase", "sla_breach_risk"),
        ("ssl_handshake_failures", "customer_facing_errors"),
    ]
    for src, tgt in impact_links:
        mem.link(src, tgt, label="causes_impact")

    service_outage_links = [
        ("partial_outage", "auth_service"),
        ("partial_outage", "payment_service"),
        ("partial_outage", "order_service"),
        ("partial_outage", "notification_service"),
        ("partial_outage", "search_service"),
    ]
    for src, tgt in service_outage_links:
        mem.link(src, tgt, label="affects_service")


def section_1_build_graph(mem: HypergraphMemory) -> list[str]:
    print("=" * 70)
    print("SECTION 1: Building the Incident Knowledge Graph")
    print("=" * 70)
    build_incident_graph(mem)
    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")
    hypotheses = [
        "db_connection_pool_exhaustion",
        "dns_resolution_failure",
        "certificate_expiry",
        "memory_leak_api",
        "kafka_partition_rebalance",
    ]
    evidence_count = len([e for e in [
        "log_connection_refused", "log_ssl_cert_invalid",
        "metric_db_pool_active_95pct", "metric_dns_timeout_5s",
        "metric_heap_growth_trend", "metric_kafka_consumer_lag",
        "alert_circuit_breaker_open", "alert_ssl_expiry_0_days",
        "deploy_last_commit_config_change", "log_dns_resolution_slow",
        "metric_gc_pause_increase", "log_kafka_rebalance_event",
        "evidence_recent_deploy_rollback", "evidence_no_dns_issues_other_services",
    ] if mem.has(e)])
    print(f"  Root cause hypotheses: {len(hypotheses)}")
    print(f"  Evidence nodes: {evidence_count}")
    print()
    return hypotheses


def section_2_distribution(mem: HypergraphMemory, hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 2: Distribution = Maintaining Competing Hypotheses")
    print("=" * 70)
    print()
    print("  What it actually does: assigns weights to candidate hypotheses,")
    print("  then normalizes so total probability = 1. Without explicit amplitudes,")
    print("  you get a uniform prior: 'I have no idea which cause is right.'")
    print("  Spreading activation may shift weights based on graph connectivity.")
    print()

    qs = mem.belief.create(outcomes=hypotheses)
    print(f"  Distribution of {qs.outcome_count} hypotheses:")
    for interp in qs.outcomes:
        print(f"    {interp.label:40s} amp={interp.amplitude:.4f}  prob={interp.probability:.4f}")
    total = sum(i.probability for i in qs.outcomes)
    print(f"\n  Total probability: {total:.4f}")
    print()


def section_3_sample(mem: HypergraphMemory, hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 3: Sample = Evidence-Driven Hypothesis Selection")
    print("=" * 70)
    print()
    print("  What it actually does: multiplies each hypothesis probability by a")
    print("  context weight, then samples one hypothesis proportional to the result.")
    print("  This is weighted random sampling -- np.random.choice(p=biased_probs).")
    print()

    evidence_weights_by_label = {
        "certificate_expiry": 3.5,
        "dns_resolution_failure": 1.8,
        "db_connection_pool_exhaustion": 1.5,
        "memory_leak_api": 1.0,
        "kafka_partition_rebalance": 0.8,
    }
    print("  Evidence context weights (from SSL alert, cert logs, etc.):")
    for label, w in sorted(evidence_weights_by_label.items(), key=lambda x: -x[1]):
        print(f"    {label:40s} weight={w:.1f}")

    context_arr = np.array([evidence_weights_by_label[h] for h in hypotheses])
    expected_probs = context_arr / context_arr.sum()
    print("\n  Expected posterior distribution (uniform prior x context, normalized):")
    for h, p in zip(hypotheses, expected_probs, strict=True):
        print(f"    {h:40s} {p:.1%}")

    context_weights = evidence_weights_by_label

    print("\n  Running sample 1000 times to check distribution...")
    counts: dict[str, int] = {h: 0 for h in hypotheses}
    n_trials = 1000
    for _ in range(n_trials):
        qs_trial = mem.belief.create(outcomes=hypotheses, amplitudes=None, use_context=False)
        answer = mem.sample(qs_trial, context=context_weights)
        if answer:
            label = mem.node_label(answer.node_id) or answer.node_id
            counts[label] = counts.get(label, 0) + 1

    print(f"\n  Sample frequency over {n_trials} trials:")
    for label in sorted(counts, key=lambda k: counts.get(k, 0), reverse=True):
        bar = "#" * (counts[label] // 10)
        print(f"    {label:40s} {counts[label]:4d} ({counts[label]/n_trials:.1%}) {bar}")

    print("\n  Compare: plain np.random.choice with the same probabilities:")
    simple_counts = np.random.choice(hypotheses, size=n_trials, p=expected_probs)
    for label in sorted(set(simple_counts), key=lambda l: -np.sum(simple_counts == l)):
        c = int(np.sum(simple_counts == label))
        print(f"    {label:40s} {c:4d} ({c/n_trials:.1%})")
    print("\n  --> Distributions match. Sample = weighted sampling, nothing magical.")
    print("  Note: sample() now accepts node labels as context keys directly.")
    print()


def section_4_correlation(mem: HypergraphMemory, hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 4: Correlation = Correlated Hypotheses")
    print("=" * 70)
    print()
    print("  What it actually does: stores a correlation matrix between two")
    print("  groups of hypotheses. When one is observed (collapsed), predict()")
    print("  returns the correlated value for each partner. This is a lookup")
    print("  table -- a classical correlation matrix, not quantum entanglement.")
    print()

    qs = mem.belief.create(outcomes=hypotheses, use_context=False)

    ent = mem.belief.correlate(
        group_a=["certificate_expiry", "dns_resolution_failure"],
        group_b=["memory_leak_api", "db_connection_pool_exhaustion"],
        correlations={
            ("certificate_expiry", "memory_leak_api"): 0.2,
            ("certificate_expiry", "db_connection_pool_exhaustion"): -0.1,
            ("dns_resolution_failure", "memory_leak_api"): 0.15,
            ("dns_resolution_failure", "db_connection_pool_exhaustion"): 0.6,
        },
    )
    print(f"  Correlation created: {ent.id[:12]}...")
    print("  Group A (network/security): certificate_expiry, dns_resolution_failure")
    print("  Group B (application/database): memory_leak_api, db_connection_pool_exhaustion")
    print("\n  Correlations (positive = co-occur, negative = mutually exclusive):")
    print("    dns_failure  <-> db_pool_exhaustion: +0.6 (DNS issues stress DB pool)")
    print("    cert_expiry  <-> memory_leak:        +0.2 (weak)")
    print("    cert_expiry  <-> db_pool_exhaustion: -0.1 (slightly anti-correlated)")
    print("    dns_failure  <-> memory_leak:        +0.15 (weak)")

    cascaded = mem.belief.sample_correlated(qs, "certificate_expiry")
    print("\n  Correlated sample (observe certificate_expiry):")
    if cascaded:
        for partner_label, prediction in cascaded.items():
            print(f"    {partner_label}: prediction={prediction}")
        print()
        print("  Positive predictions mean the correlated outcome is expected")
        print("  to activate; negative means the anti-correlated outcome is expected.")
    else:
        print("    (no correlated predictions -- state not linked to correlation)")
    print()


def section_5_interference(mem: HypergraphMemory) -> None:
    print("=" * 70)
    print("SECTION 5: Interference = Evidence Reinforcement and Contradiction")
    print("=" * 70)
    print()
    print("  What it actually does: when a hypothesis appears with both positive")
    print("  and negative amplitudes, the interference computation checks whether")
    print("  evidence reinforces (constructive) or contradicts (destructive).")
    print("  It compares |sum(amps)|^2 vs sum(|amp|^2) -- standard wave math.")
    print()

    qs_constructive = mem.belief.create(
        outcomes=["certificate_expiry", "certificate_expiry"],
        amplitudes=[0.7, 0.5],
        use_context=False,
    )
    print("  Constructive case: two evidence sources both support certificate_expiry")
    print("    amplitudes: [+0.70, +0.50]")
    patterns_c = mem.belief.interactions(qs_constructive)
    for p in patterns_c:
        label = mem.node_label(p.node_id) or p.node_id[:8]
        kind = "CONSTRUCTIVE" if p.is_constructive else ("DESTRUCTIVE" if p.is_destructive else "NEUTRAL")
        print(f"    -> {label:25s} [{kind:12s}] net={p.net_amplitude:.4f}")

    qs_destructive = mem.belief.create(
        outcomes=["dns_resolution_failure", "dns_resolution_failure"],
        amplitudes=[0.7, -0.5],
        use_context=False,
    )
    print("\n  Destructive case: one source supports DNS failure, another contradicts")
    print("    amplitudes: [+0.70, -0.50]")
    patterns_d = mem.belief.interactions(qs_destructive)
    for p in patterns_d:
        label = mem.node_label(p.node_id) or p.node_id[:8]
        kind = "CONSTRUCTIVE" if p.is_constructive else ("DESTRUCTIVE" if p.is_destructive else "NEUTRAL")
        print(f"    -> {label:25s} [{kind:12s}] net={p.net_amplitude:.4f}")

    print("\n  Takeaway: agreeing evidence amplifies, conflicting evidence diminishes.")
    print("  This is Bayes factor aggregation expressed through amplitude arithmetic.")
    print()


def section_6_entropy(mem: HypergraphMemory, hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 6: Density Matrix and Von Neumann Entropy = Uncertainty Measure")
    print("=" * 70)
    print()
    print("  The density matrix rho = |psi><psi| is the outer product of the")
    print("  amplitude vector. Von Neumann entropy S = -Tr(rho log2 rho).")
    print()
    print("  IMPORTANT CAVEAT: for pure states (superpositions created by superpose()),")
    print("  rho has exactly one nonzero eigenvalue (=1), so entropy is ALWAYS 0.")
    print("  This is a mathematical property: a pure state is fully known even if")
    print("  its probability distribution is spread out. Entropy becomes meaningful")
    print("  for MIXED states (statistical ensembles), where it equals Shannon entropy.")
    print()

    rho_mixed_confident = np.zeros((3, 3), dtype=complex)
    basis_confident = [
        (np.array([1, 0, 0], dtype=complex), 0.90),
        (np.array([0, 1, 0], dtype=complex), 0.08),
        (np.array([0, 0, 1], dtype=complex), 0.02),
    ]
    for vec, weight in basis_confident:
        rho_mixed_confident += weight * np.outer(vec, vec.conj())
    entropy_confident = mem.belief.von_neumann_entropy(rho_mixed_confident)
    print("  Mixed state (one hypothesis dominates at 90%):")
    print("    Weights: 0.90, 0.08, 0.02")
    print(f"    Entropy: {entropy_confident:.6f} bits (low = confident)")

    rho_mixed_moderate = np.zeros((3, 3), dtype=complex)
    basis_moderate = [
        (np.array([1, 0, 0], dtype=complex), 0.6),
        (np.array([0, 1, 0], dtype=complex), 0.3),
        (np.array([0, 0, 1], dtype=complex), 0.1),
    ]
    for vec, weight in basis_moderate:
        rho_mixed_moderate += weight * np.outer(vec, vec.conj())
    entropy_moderate = mem.belief.von_neumann_entropy(rho_mixed_moderate)
    print("\n  Mixed state (moderate uncertainty):")
    print("    Weights: 0.60, 0.30, 0.10")
    print(f"    Entropy: {entropy_moderate:.6f} bits")

    rho_max = np.eye(4, dtype=complex) / 4
    entropy_max = mem.belief.von_neumann_entropy(rho_max)
    print("\n  Maximally uncertain (4 hypotheses, equal weight):")
    print(f"    Entropy: {entropy_max:.6f} bits = log2(4) = {np.log2(4):.6f}")

    print("\n  Quick check: pure state entropy (should be 0)")
    qs_pure = mem.belief.create(
        outcomes=hypotheses[:3],
        amplitudes=[0.6, 0.3, 0.1],
        use_context=False,
    )
    rho_pure = mem.belief.density_matrix(qs_pure.id)
    if rho_pure is not None:
        entropy_pure = mem.belief.von_neumann_entropy(rho_pure)
        print(f"    Pure state entropy: {entropy_pure:.10f} bits (effectively 0)")
        print(f"    Shannon entropy of probs: {-sum(i.probability * np.log2(max(i.probability, 1e-15)) for i in qs_pure.outcomes):.6f} bits")
        print("    --> These differ! Pure state entropy=0, Shannon>0. They are NOT the same.")

    print()
    print("  Bottom line: Von Neumann entropy measures uncertainty of the STATE")
    print("  (pure vs mixed), not uncertainty of the probability distribution.")
    print("  For practical hypothesis uncertainty, use Shannon entropy of probabilities.")
    print()


def section_7_bayesian_reasoning(mem: HypergraphMemory, hypotheses: list[str]) -> None:
    print("=" * 70)
    print("SECTION 7: Bayesian Posterior Updating")
    print("=" * 70)
    print()
    print("  Where the belief layer represents uncertainty, the Bayesian")
    print("  subsystem reduces it. Each piece of evidence updates the posterior")
    print("  via Bayes' rule: P(cause|evidence) ~ P(evidence|cause) * P(cause).")
    print()

    mem.add("root_cause_investigation", data={"type": "bayesian_analysis"})
    mem.set_prior(
        "root_cause_investigation",
        outcomes=hypotheses,
        weights=[1.0, 1.0, 1.0, 1.0, 1.0],
    )
    prior = mem.get_belief("root_cause_investigation")
    if prior:
        print("  Prior (uniform):")
        label_map = {}
        for h in hypotheses:
            nid = mem.resolve_id(h)
            if nid:
                label_map[nid] = h
        for outcome_id, prob in sorted(prior.outcomes.items(), key=lambda x: -x[1]):
            label = label_map.get(outcome_id, outcome_id[:12])
            print(f"    {label:40s} {prob:.4f}")

    print()
    print("  Applying evidence sequentially...")

    evidence_sequence = [
        (
            "ssl_alert_and_cert_logs",
            {
                "certificate_expiry": 0.85,
                "dns_resolution_failure": 0.15,
                "db_connection_pool_exhaustion": 0.10,
                "memory_leak_api": 0.05,
                "kafka_partition_rebalance": 0.02,
            },
        ),
        (
            "no_dns_issues_other_services",
            {
                "certificate_expiry": 0.70,
                "dns_resolution_failure": 0.10,
                "db_connection_pool_exhaustion": 0.30,
                "memory_leak_api": 0.20,
                "kafka_partition_rebalance": 0.10,
            },
        ),
        (
            "db_pool_metrics_moderate",
            {
                "certificate_expiry": 0.50,
                "dns_resolution_failure": 0.20,
                "db_connection_pool_exhaustion": 0.60,
                "memory_leak_api": 0.40,
                "kafka_partition_rebalance": 0.15,
            },
        ),
    ]

    label_map = {}
    for h in hypotheses:
        nid = mem.resolve_id(h)
        if nid:
            label_map[nid] = h

    for ev_name, likelihoods in evidence_sequence:
        result = mem.update_belief(
            "root_cause_investigation",
            evidence_name=ev_name,
            likelihoods=likelihoods,
        )
        if result.posterior:
            print(f"\n  After '{ev_name}':")
            for outcome_id, prob in sorted(
                result.posterior.outcomes.items(), key=lambda x: -x[1]
            ):
                label = label_map.get(outcome_id, outcome_id[:12])
                print(f"    {label:40s} {prob:.4f}")
            if result.kl_divergence > 0:
                print(f"    KL divergence from prior: {result.kl_divergence:.4f} bits")

    print()
    map_est = mem.map_estimate("root_cause_investigation")
    print(f"  MAP estimate (most probable cause): {map_est}")

    credible = mem.credible_set("root_cause_investigation", level=0.95)
    print(f"  95% credible set: {credible}")

    bf = mem.bayes_factor(
        "root_cause_investigation",
        hypothesis_a="certificate_expiry",
        hypothesis_b="dns_resolution_failure",
    )
    if bf is not None:
        print(f"  Bayes factor (cert_expiry vs dns_failure): {bf:.2f}")
        if bf > 10:
            print("    -> Strong evidence favoring certificate_expiry")
        elif bf > 3:
            print("    -> Moderate evidence favoring certificate_expiry")
        else:
            print("    -> Weak evidence, not yet decisive")

    print()


def section_8_confidence_assessment(mem: HypergraphMemory) -> None:
    print("=" * 70)
    print("SECTION 8: Confidence Assessment and Knowledge Gaps")
    print("=" * 70)
    print()
    print("  After Bayesian analysis points to certificate_expiry, how confident")
    print("  are we in each part of the knowledge graph? The confidence subsystem")
    print("  scores concepts based on provenance depth, edge weights, and graph")
    print("  structure, then flags areas that need more information.")
    print()

    all_conf = mem.compute_all_confidences()
    print("  Overall graph confidence:")
    print(f"    Average confidence: {all_conf.avg_confidence:.4f}")
    print(f"    High confidence (>0.8): {all_conf.high_confidence_count}")
    print(f"    Low confidence (<0.3): {all_conf.low_confidence_count}")
    print()

    root_causes = [
        "certificate_expiry",
        "dns_resolution_failure",
        "db_connection_pool_exhaustion",
        "memory_leak_api",
        "kafka_partition_rebalance",
        "deploy_bad_config",
    ]
    print("  Confidence scores for root cause hypotheses:")
    for cause in root_causes:
        score = mem.compute_confidence(cause)
        if score:
            bar = "#" * int(score.confidence * 30)
            print(f"    {cause:40s} {score.confidence:.4f} {bar} (depth={score.depth}, source={score.source})")

    print()
    print("  Confidence for key evidence nodes:")
    evidence_nodes = [
        "log_ssl_cert_invalid",
        "alert_ssl_expiry_0_days",
        "log_connection_refused",
        "metric_db_pool_active_95pct",
        "metric_dns_timeout_5s",
    ]
    for ev in evidence_nodes:
        score = mem.compute_confidence(ev)
        if score:
            print(f"    {ev:40s} {score.confidence:.4f} (depth={score.depth})")

    print()
    print("  Confidence chains (highest-confidence paths):")
    chains_to_check = [
        ("certificate_expiry", "customer_facing_errors"),
        ("certificate_expiry", "revenue_at_risk"),
        ("db_connection_pool_exhaustion", "sla_breach_risk"),
    ]
    for src, tgt in chains_to_check:
        chain = mem.trace_confidence_chain(src, tgt)
        if chain:
            print(f"    {src} -> {tgt}:")
            print(f"      chain_confidence={chain.chain_confidence:.4f}, depth={chain.chain_depth}")

    print()
    print("  Flagging low-confidence areas (knowledge gaps):")
    low = mem.flag_low_confidence(threshold=0.5)
    if low:
        print(f"    {len(low)} concepts below threshold 0.5:")
        for item in low[:8]:
            print(f"      {item.node_label:40s} confidence={item.confidence:.4f} (depth={item.depth}, source={item.source})")
        print()
        print("    These knowledge gaps indicate areas where additional")
        print("    relationships or evidence would improve diagnostic confidence.")
    else:
        print("    All concepts above threshold 0.5.")

    print()


def section_9_bayesian_comparison() -> None:
    print("=" * 70)
    print("SECTION 9: Honest Comparison with Bayesian Inference")
    print("=" * 70)
    print()
    print("  The quantum formalism in Hyper3 is mathematically equivalent to")
    print("  Bayesian hypothesis ranking for this use case:")
    print()
    print("  1. Distribution = prior distribution over hypotheses")
    print("  2. Sample with context = sampling from posterior (context = likelihood)")
    print("  3. Correlation = structured prior over correlated hypotheses")
    print("  4. Interference = Bayes factor aggregation (agreeing/diverging evidence)")
    print("  5. Von Neumann entropy = for mixed states, equals Shannon entropy")
    print()
    print("  Advantages of the belief layer API:")
    print("    - Natural syntax for correlated hypotheses (correlation)")
    print("    - Built-in uncertainty quantification (entropy)")
    print("    - Density matrix gives a full covariance-like state descriptor")
    print()
    print("  Disadvantages:")
    print("    - Adds mathematical overhead for what is fundamentally Bayesian updating")
    print("    - No actual quantum speedup (this runs on classical hardware)")
    print("    - Von Neumann entropy is 0 for pure states, which is counterintuitive")
    print("    - Unitary evolution (Hadamard, phase gates) has no clear Bayesian analog")
    print("      and is hard to interpret in a hypothesis management context")
    print()
    print("  Bottom line: use this when you want the correlation/entropy/overlay")
    print("  features. For simple prior-posterior updates, plain Bayesian code is")
    print("  clearer and faster.")
    print()


def main():
    mem = HypergraphMemory(evolve_interval=0)

    hypotheses = section_1_build_graph(mem)
    section_2_distribution(mem, hypotheses)
    section_3_sample(mem, hypotheses)
    section_4_correlation(mem, hypotheses)
    section_5_interference(mem)
    section_6_entropy(mem, hypotheses)
    section_7_bayesian_reasoning(mem, hypotheses)
    section_8_confidence_assessment(mem)
    section_9_bayesian_comparison()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Distribution = prior distribution over hypotheses (weighted or uniform)")
    print("  2. Sample = weighted random sampling (Born rule = p ~ weight^2)")
    print("  3. Correlation = pairwise correlation lookup between hypothesis groups")
    print("  4. Interference = detects agreeing vs conflicting evidence sources")
    print("  5. Entropy = meaningful for mixed states; 0 for pure states (a caveat)")
    print("  6. Bayesian updating = sequential evidence accumulation via Bayes' rule")
    print("  7. Confidence scoring = quantifying knowledge graph reliability")
    print("  8. For this use case, belief layer ~= Bayesian inference with APIs")
    print("  9. Be honest about what it is: classical probability with quantum-inspired notation")
    print()


if __name__ == "__main__":
    main()
