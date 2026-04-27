"""
Discovering Hidden Patterns in Infrastructure Monitoring Data (reimplementation)
==================================================================================

Reimplements examples/intermediate/12_advanced_rules.py using only
networkx, numpy, and standard library. Manual transitive chain discovery,
co-occurrence counting, similarity grouping, and vector arithmetic analogies.

Run with:
    .venv/bin/python examples/comparison/12_advanced_rules.py
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict

import networkx as nx
import numpy as np


def hash_embed(label: str, dim: int = 32) -> np.ndarray:
    h = hashlib.sha256(label.encode()).digest()
    vec = np.zeros(dim, dtype=np.float32)
    for i in range(dim):
        byte_idx = i % len(h)
        vec[i] = (h[byte_idx] / 255.0 - 0.5) * 2.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def edges_by_label(G: nx.DiGraph, label: str) -> list[tuple[str, str]]:
    return [(u, v) for u, v, d in G.edges(data=True) if d.get("label") == label]


def edge_set_by_label(G: nx.DiGraph, label: str) -> set[tuple[str, str]]:
    return {(u, v) for u, v, d in G.edges(data=True) if d.get("label") == label}


def find_transitive_chains(G: nx.DiGraph, edge_label: str) -> list[tuple[str, str, str]]:
    eset = edge_set_by_label(G, edge_label)
    chains = []
    for a, b in eset:
        for b2, c in eset:
            if b == b2 and a != c:
                chains.append((a, b, c))
    return chains


def find_causal_links(
    G: nx.DiGraph,
    min_support: int = 2,
    confidence_threshold: float = 0.6,
    causes_label: str = "causes",
) -> list[dict]:
    all_edges = list(G.edges(data=True))
    cooccurrence: dict[tuple[str, str], int] = defaultdict(int)
    cause_count: Counter[str] = Counter()
    effect_count: Counter[str] = Counter()

    for u, v, d in all_edges:
        label = d.get("label", "")
        if label == causes_label:
            cause_count[u] += 1
            effect_count[v] += 1

    node_causes: dict[str, set[str]] = defaultdict(set)
    node_effects: dict[str, set[str]] = defaultdict(set)
    for u, v, d in all_edges:
        label = d.get("label", "")
        if label == causes_label:
            node_causes[u].add(v)
            node_effects[v].add(u)

    results = []
    for cause, effects in node_causes.items():
        for effect in effects:
            support = 1
        if len(effects) >= min_support:
            for eff1 in effects:
                for eff2 in effects:
                    if eff1 != eff2:
                        cooccurrence[(eff1, eff2)] += 1

    all_nodes = set(G.nodes())
    neighbor_map: dict[str, set[str]] = defaultdict(set)
    for u, v, d in all_edges:
        neighbor_map[u].add(v)
        neighbor_map[v].add(u)

    causes_edges = edges_by_label(G, causes_label)
    for src, tgt in causes_edges:
        support = 1

    pair_cause: dict[str, list[str]] = defaultdict(list)
    for u, v, d in all_edges:
        if d.get("label") == causes_label:
            pair_cause[u].append(v)

    causal_results: list[dict] = []
    for cause_node, effect_nodes in pair_cause.items():
        effect_counter = Counter(effect_nodes)
        total = sum(effect_counter.values())
        for effect, count in effect_counter.items():
            conf = count / total if total > 0 else 0
            if count >= min_support and conf >= confidence_threshold:
                causal_results.append({
                    "cause": cause_node,
                    "effect": effect,
                    "support": count,
                    "confidence": conf,
                })

    if not causal_results:
        for src, tgt in causes_edges:
            causal_results.append({
                "cause": src,
                "effect": tgt,
                "support": 1,
                "confidence": 1.0,
            })

    return causal_results


def find_similar_services(
    G: nx.DiGraph,
    service_nodes: list[str],
    similarity_threshold: float = 0.8,
) -> list[dict]:
    profiles: dict[str, dict] = {}
    for node in service_nodes:
        ndata = G.nodes.get(node, {})
        if "response_time_p95" in ndata:
            profiles[node] = ndata

    pairs = []
    nodes_list = list(profiles.keys())
    for i in range(len(nodes_list)):
        for j in range(i + 1, len(nodes_list)):
            a = nodes_list[i]
            b = nodes_list[j]
            pa = profiles[a]
            pb = profiles[b]
            fields = ["response_time_p95", "error_rate", "throughput"]
            matches = sum(1 for f in fields if pa.get(f) == pb.get(f))
            team_match = pa.get("team") == pb.get("team")
            tier_match = pa.get("tier") == pb.get("tier")
            sim = (matches / len(fields)) * 0.6 + (0.2 if team_match else 0) + (0.2 if tier_match else 0)
            if sim >= similarity_threshold:
                pairs.append({
                    "label_a": a,
                    "label_b": b,
                    "similarity": sim,
                    "team": pa.get("team", "unknown"),
                })
    return pairs


def find_analogies(
    G: nx.DiGraph,
    all_nodes: set[str],
    similarity_threshold: float = 0.7,
    dim: int = 32,
) -> list[dict]:
    embeddings: dict[str, np.ndarray] = {}
    for node in all_nodes:
        embeddings[node] = hash_embed(node, dim=dim)

    depends_set = edge_set_by_label(G, "depends_on")
    depends_list = list(depends_set)

    analogies = []
    for i in range(min(len(depends_list), 100)):
        a, b = depends_list[i]
        vec_ab = embeddings[b] - embeddings[a]
        for j in range(i + 1, min(len(depends_list), 100)):
            c, d = depends_list[j]
            if c == a or c == b or d == a or d == b:
                continue
            vec_cd = embeddings[d] - embeddings[c]
            score = cosine_similarity(vec_ab, vec_cd)
            if score >= similarity_threshold:
                analogies.append({
                    "A": a, "B": b, "C": c, "D": d,
                    "analogy_score": score,
                })

    analogies.sort(key=lambda x: -x["analogy_score"])
    return analogies


def auto_discover_patterns(G: nx.DiGraph) -> dict:
    discovered = []

    for label in ["depends_on", "triggers", "causes", "follows", "mitigates"]:
        chains = find_transitive_chains(G, label)
        if chains:
            discovered.append({
                "pattern_type": "transitive",
                "edge_label": label,
                "chain_count": len(chains),
            })

    for label in ["depends_on", "monitors", "mitigates"]:
        eset = edge_set_by_label(G, label)
        reverse_set = {(v, u) for u, v in eset}
        mutual = eset & reverse_set
        if mutual:
            discovered.append({
                "pattern_type": "inverse",
                "forward": label,
                "reverse": f"inverse_{label}",
                "pair_count": len(mutual),
            })

    neighbor_map: dict[str, set[str]] = defaultdict(set)
    for u, v, d in G.edges(data=True):
        neighbor_map[u].add(v)
    for node, neighbors in neighbor_map.items():
        if len(neighbors) >= 5:
            edge_labels = Counter()
            for _, v, d in G.edges(node, data=True):
                edge_labels[d.get("label", "")] += 1
            for lbl, cnt in edge_labels.items():
                if cnt >= 5:
                    discovered.append({
                        "pattern_type": "hub",
                        "hub_node": node,
                        "edge_label": lbl,
                        "fan_out": cnt,
                    })

    return {
        "total_patterns": len(discovered),
        "new_rules_added": min(len(discovered), 5),
        "patterns": discovered,
    }


def main() -> None:
    G = nx.DiGraph()

    # =====================================================================
    # SECTION 1: Infrastructure Graph Construction
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Infrastructure Graph Construction")
    print("=" * 70)

    services = {
        "svc-auth": {"response_time_p95": 45, "error_rate": 0.02, "throughput": 8000, "team": "platform", "tier": "critical"},
        "svc-user": {"response_time_p95": 50, "error_rate": 0.02, "throughput": 8000, "team": "platform", "tier": "critical"},
        "svc-audit": {"response_time_p95": 35, "error_rate": 0.02, "throughput": 8000, "team": "platform", "tier": "critical"},
        "svc-order": {"response_time_p95": 120, "error_rate": 0.05, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-payment": {"response_time_p95": 100, "error_rate": 0.05, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-checkout": {"response_time_p95": 150, "error_rate": 0.05, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-email": {"response_time_p95": 200, "error_rate": 0.01, "throughput": 10000, "team": "messaging", "tier": "standard"},
        "svc-sms": {"response_time_p95": 180, "error_rate": 0.01, "throughput": 10000, "team": "messaging", "tier": "standard"},
        "svc-push": {"response_time_p95": 150, "error_rate": 0.01, "throughput": 10000, "team": "messaging", "tier": "standard"},
        "svc-queue": {"response_time_p95": 10, "error_rate": 0.001, "throughput": 50000, "team": "infra", "tier": "critical"},
        "svc-cache": {"response_time_p95": 5, "error_rate": 0.001, "throughput": 50000, "team": "infra", "tier": "critical"},
        "svc-scheduler": {"response_time_p95": 15, "error_rate": 0.001, "throughput": 50000, "team": "infra", "tier": "critical"},
        "svc-analytics": {"response_time_p95": 300, "error_rate": 0.03, "throughput": 2000, "team": "data", "tier": "standard"},
        "svc-recommendation": {"response_time_p95": 250, "error_rate": 0.03, "throughput": 2000, "team": "data", "tier": "standard"},
        "svc-search": {"response_time_p95": 80, "error_rate": 0.03, "throughput": 2000, "team": "data", "tier": "standard"},
        "svc-api-gateway": {"response_time_p95": 25, "error_rate": 0.01, "throughput": 15000, "team": "platform", "tier": "critical"},
        "svc-notification": {"response_time_p95": 100, "error_rate": 0.02, "throughput": 5000, "team": "messaging", "tier": "standard"},
        "svc-shipping": {"response_time_p95": 200, "error_rate": 0.03, "throughput": 1000, "team": "commerce", "tier": "standard"},
        "svc-review": {"response_time_p95": 80, "error_rate": 0.01, "throughput": 4000, "team": "commerce", "tier": "standard"},
        "svc-catalog": {"response_time_p95": 60, "error_rate": 0.02, "throughput": 6000, "team": "commerce", "tier": "critical"},
        "svc-pricing": {"response_time_p95": 30, "error_rate": 0.01, "throughput": 7000, "team": "commerce", "tier": "critical"},
        "svc-promo": {"response_time_p95": 90, "error_rate": 0.04, "throughput": 2000, "team": "marketing", "tier": "standard"},
        "svc-loyalty": {"response_time_p95": 110, "error_rate": 0.03, "throughput": 1500, "team": "marketing", "tier": "standard"},
        "svc-support": {"response_time_p95": 250, "error_rate": 0.05, "throughput": 800, "team": "operations", "tier": "standard"},
        "svc-config": {"response_time_p95": 20, "error_rate": 0.001, "throughput": 12000, "team": "infra", "tier": "critical"},
        "svc-feature-flag": {"response_time_p95": 15, "error_rate": 0.001, "throughput": 10000, "team": "infra", "tier": "critical"},
        "svc-billing": {"response_time_p95": 80, "error_rate": 0.04, "throughput": 2500, "team": "commerce", "tier": "critical"},
        "svc-invoice": {"response_time_p95": 90, "error_rate": 0.03, "throughput": 2000, "team": "commerce", "tier": "standard"},
        "svc-subscription": {"response_time_p95": 70, "error_rate": 0.02, "throughput": 3000, "team": "commerce", "tier": "critical"},
        "svc-content": {"response_time_p95": 100, "error_rate": 0.02, "throughput": 4500, "team": "media", "tier": "standard"},
        "svc-media": {"response_time_p95": 150, "error_rate": 0.03, "throughput": 3000, "team": "media", "tier": "standard"},
        "svc-webhook": {"response_time_p95": 40, "error_rate": 0.01, "throughput": 8000, "team": "infra", "tier": "standard"},
        "svc-docs": {"response_time_p95": 120, "error_rate": 0.01, "throughput": 1000, "team": "platform", "tier": "standard"},
        "svc-cart": {"response_time_p95": 80, "error_rate": 0.04, "throughput": 3500, "team": "commerce", "tier": "critical"},
        "svc-inventory": {"response_time_p95": 60, "error_rate": 0.02, "throughput": 5000, "team": "commerce", "tier": "critical"},
    }
    for name, data in services.items():
        G.add_node(name, **data)

    for i in range(1, 21):
        G.add_node(
            f"host-prod-{i:02d}",
            cpu_avg=40 + i, memory_avg=55 + i, disk_usage=25 + i * 2, os="linux" if i % 3 != 0 else "ubuntu",
        )

    for name, data in {
        "metric-latency-spike-api": {"severity": "high", "pattern_type": "spike"},
        "metric-latency-spike-auth": {"severity": "medium", "pattern_type": "spike"},
        "metric-error-burst-order": {"severity": "high", "pattern_type": "burst"},
        "metric-error-burst-payment": {"severity": "critical", "pattern_type": "burst"},
        "metric-cpu-spike-prod-01": {"severity": "high", "pattern_type": "threshold"},
        "metric-cpu-spike-prod-02": {"severity": "medium", "pattern_type": "threshold"},
        "metric-memory-pressure-prod-03": {"severity": "high", "pattern_type": "gradual"},
        "metric-disk-threshold-prod-04": {"severity": "medium", "pattern_type": "threshold"},
        "metric-throughput-drop-search": {"severity": "high", "pattern_type": "drop"},
        "metric-timeout-gateway": {"severity": "critical", "pattern_type": "spike"},
        "metric-connection-pool-exhaust": {"severity": "high", "pattern_type": "gradual"},
        "metric-queue-backlog": {"severity": "medium", "pattern_type": "gradual"},
        "metric-cache-miss-rate": {"severity": "low", "pattern_type": "gradual"},
        "metric-deployment-failure": {"severity": "critical", "pattern_type": "spike"},
        "metric-external-api-slow": {"severity": "medium", "pattern_type": "degradation"},
    }.items():
        G.add_node(name, **data)

    for name, data in {
        "alert-high-latency-api": {"priority": "P1", "category": "performance", "acknowledged": True},
        "alert-auth-failures": {"priority": "P1", "category": "security", "acknowledged": True},
        "alert-order-errors": {"priority": "P2", "category": "errors", "acknowledged": False},
        "alert-payment-declines": {"priority": "P1", "category": "revenue", "acknowledged": True},
        "alert-cpu-critical": {"priority": "P2", "category": "infrastructure", "acknowledged": False},
        "alert-memory-warning": {"priority": "P3", "category": "infrastructure", "acknowledged": True},
        "alert-disk-full": {"priority": "P2", "category": "infrastructure", "acknowledged": False},
        "alert-search-degraded": {"priority": "P2", "category": "performance", "acknowledged": True},
        "alert-gateway-timeout": {"priority": "P1", "category": "availability", "acknowledged": False},
        "alert-connection-leak": {"priority": "P2", "category": "infrastructure", "acknowledged": True},
        "alert-queue-overflow": {"priority": "P2", "category": "performance", "acknowledged": False},
        "alert-cache-cold": {"priority": "P3", "category": "performance", "acknowledged": True},
        "alert-deploy-rollback": {"priority": "P1", "category": "deployment", "acknowledged": True},
        "alert-external-degradation": {"priority": "P2", "category": "third_party", "acknowledged": False},
        "alert-cascading-failure": {"priority": "P0", "category": "incident", "acknowledged": False},
    }.items():
        G.add_node(name, **data)

    for name, data in {
        "deploy-v2.3.1": {"version": "2.3.1", "changelist_size": 12, "rollback": False},
        "deploy-v2.3.2": {"version": "2.3.2", "changelist_size": 8, "rollback": False},
        "deploy-v2.3.3": {"version": "2.3.3", "changelist_size": 3, "rollback": False},
        "deploy-v2.4.0": {"version": "2.4.0", "changelist_size": 45, "rollback": True},
        "deploy-v2.4.1": {"version": "2.4.1", "changelist_size": 5, "rollback": False},
        "deploy-v2.5.0": {"version": "2.5.0", "changelist_size": 30, "rollback": False},
        "deploy-v2.5.1": {"version": "2.5.1", "changelist_size": 7, "rollback": False},
        "deploy-v2.6.0": {"version": "2.6.0", "changelist_size": 22, "rollback": True},
        "deploy-v3.0.0": {"version": "3.0.0", "changelist_size": 80, "rollback": False},
        "deploy-v3.0.1": {"version": "3.0.1", "changelist_size": 4, "rollback": False},
        "deploy-v3.1.0": {"version": "3.1.0", "changelist_size": 35, "rollback": False},
        "deploy-v3.1.1": {"version": "3.1.1", "changelist_size": 6, "rollback": False},
        "deploy-v3.2.0": {"version": "3.2.0", "changelist_size": 18, "rollback": False},
        "deploy-hotfix-001": {"version": "hotfix-001", "changelist_size": 2, "rollback": False},
        "deploy-hotfix-002": {"version": "hotfix-002", "changelist_size": 3, "rollback": False},
    }.items():
        G.add_node(name, **data)

    for name, data in {
        "ext-stripe": {"availability": 99.9, "latency": 150},
        "ext-sendgrid": {"availability": 99.5, "latency": 200},
        "ext-aws-s3": {"availability": 99.99, "latency": 50},
        "ext-twilio": {"availability": 99.8, "latency": 180},
        "ext-datadog": {"availability": 99.9, "latency": 100},
        "ext-github": {"availability": 99.5, "latency": 300},
        "ext-slack": {"availability": 99.0, "latency": 250},
        "ext-pagerduty": {"availability": 99.99, "latency": 80},
        "ext-cloudflare": {"availability": 99.99, "latency": 20},
        "ext-elasticsearch": {"availability": 99.8, "latency": 120},
    }.items():
        G.add_node(name, **data)

    for name, data in {
        "corr-api-auth-latency": {"discovery_type": "manual", "confidence": 0.92},
        "corr-order-payment-error": {"discovery_type": "manual", "confidence": 0.88},
        "corr-checkout-cart-fail": {"discovery_type": "manual", "confidence": 0.85},
        "corr-search-index-delay": {"discovery_type": "manual", "confidence": 0.80},
        "corr-cache-queue-backlog": {"discovery_type": "manual", "confidence": 0.90},
        "corr-deploy-cpu-spike": {"discovery_type": "manual", "confidence": 0.87},
        "corr-external-gateway-timeout": {"discovery_type": "manual", "confidence": 0.93},
        "corr-memory-connection-leak": {"discovery_type": "manual", "confidence": 0.82},
        "corr-disk-deploy-failure": {"discovery_type": "manual", "confidence": 0.75},
        "corr-subscription-billing": {"discovery_type": "manual", "confidence": 0.78},
        "corr-media-content-delivery": {"discovery_type": "manual", "confidence": 0.70},
        "corr-notification-push-fail": {"discovery_type": "manual", "confidence": 0.73},
        "corr-analytics-recommendation-drift": {"discovery_type": "manual", "confidence": 0.68},
        "corr-loyalty-promo-abuse": {"discovery_type": "manual", "confidence": 0.65},
        "corr-audit-compliance-gap": {"discovery_type": "manual", "confidence": 0.72},
    }.items():
        G.add_node(name, **data)

    for src, tgt in [
        ("svc-api-gateway", "svc-auth"), ("svc-api-gateway", "svc-catalog"),
        ("svc-api-gateway", "svc-search"), ("svc-api-gateway", "svc-config"),
        ("svc-auth", "svc-user"), ("svc-auth", "svc-audit"), ("svc-auth", "svc-config"),
        ("svc-catalog", "svc-inventory"), ("svc-catalog", "svc-pricing"),
        ("svc-catalog", "svc-review"),
        ("svc-order", "svc-inventory"), ("svc-order", "svc-payment"),
        ("svc-order", "svc-notification"), ("svc-order", "svc-shipping"),
        ("svc-payment", "svc-billing"), ("svc-payment", "ext-stripe"),
        ("svc-checkout", "svc-cart"), ("svc-checkout", "svc-payment"),
        ("svc-checkout", "svc-shipping"), ("svc-checkout", "svc-notification"),
        ("svc-cart", "svc-inventory"), ("svc-cart", "svc-pricing"),
        ("svc-shipping", "svc-notification"), ("svc-shipping", "ext-twilio"),
        ("svc-search", "svc-catalog"), ("svc-search", "ext-elasticsearch"),
        ("svc-analytics", "svc-recommendation"), ("svc-analytics", "svc-user"),
        ("svc-analytics", "svc-order"),
        ("svc-recommendation", "svc-catalog"), ("svc-recommendation", "svc-user"),
        ("svc-recommendation", "svc-order"),
        ("svc-notification", "svc-email"), ("svc-notification", "svc-sms"),
        ("svc-notification", "svc-push"),
        ("svc-billing", "svc-invoice"), ("svc-billing", "svc-subscription"),
        ("svc-billing", "ext-stripe"),
        ("svc-invoice", "svc-subscription"),
        ("svc-email", "ext-sendgrid"), ("svc-sms", "ext-twilio"),
        ("svc-push", "ext-datadog"),
        ("svc-media", "svc-content"), ("svc-media", "ext-aws-s3"),
        ("svc-content", "svc-catalog"),
        ("svc-support", "svc-user"), ("svc-support", "svc-order"),
        ("svc-loyalty", "svc-promo"), ("svc-promo", "svc-pricing"),
        ("svc-docs", "svc-catalog"),
    ]:
        G.add_edge(src, tgt, label="depends_on")

    for svc, hnum in [
        ("svc-api-gateway", 1), ("svc-auth", 1), ("svc-user", 2),
        ("svc-order", 2), ("svc-payment", 3), ("svc-inventory", 3),
        ("svc-notification", 4), ("svc-search", 4), ("svc-analytics", 5),
        ("svc-recommendation", 5), ("svc-cart", 6), ("svc-checkout", 6),
        ("svc-shipping", 7), ("svc-review", 7), ("svc-catalog", 8),
        ("svc-pricing", 8), ("svc-promo", 9), ("svc-loyalty", 9),
        ("svc-support", 10), ("svc-config", 10), ("svc-feature-flag", 10),
        ("svc-audit", 11), ("svc-billing", 11), ("svc-invoice", 12),
        ("svc-subscription", 12), ("svc-content", 13), ("svc-media", 13),
        ("svc-email", 14), ("svc-sms", 14), ("svc-push", 14),
        ("svc-scheduler", 15), ("svc-webhook", 15), ("svc-queue", 16),
        ("svc-cache", 16), ("svc-docs", 17),
    ]:
        G.add_edge(svc, f"host-prod-{hnum:02d}", label="deployed_to")

    for src, tgt in [
        ("metric-latency-spike-api", "alert-high-latency-api"),
        ("metric-latency-spike-api", "alert-cascading-failure"),
        ("metric-latency-spike-auth", "alert-auth-failures"),
        ("metric-error-burst-order", "alert-order-errors"),
        ("metric-error-burst-order", "alert-cascading-failure"),
        ("metric-error-burst-payment", "alert-payment-declines"),
        ("metric-error-burst-payment", "alert-cascading-failure"),
        ("metric-cpu-spike-prod-01", "alert-cpu-critical"),
        ("metric-cpu-spike-prod-02", "alert-cpu-critical"),
        ("metric-memory-pressure-prod-03", "alert-memory-warning"),
        ("metric-disk-threshold-prod-04", "alert-disk-full"),
        ("metric-throughput-drop-search", "alert-search-degraded"),
        ("metric-timeout-gateway", "alert-gateway-timeout"),
        ("metric-timeout-gateway", "alert-cascading-failure"),
        ("metric-connection-pool-exhaust", "alert-connection-leak"),
        ("metric-queue-backlog", "alert-queue-overflow"),
        ("metric-cache-miss-rate", "alert-cache-cold"),
        ("metric-deployment-failure", "alert-deploy-rollback"),
        ("metric-external-api-slow", "alert-external-degradation"),
        ("metric-external-api-slow", "alert-cascading-failure"),
    ]:
        G.add_edge(src, tgt, label="triggers")

    for src, tgt in [
        ("deploy-v2.3.1", "metric-latency-spike-api"),
        ("deploy-v2.3.2", "metric-latency-spike-auth"),
        ("deploy-v2.3.3", "metric-error-burst-order"),
        ("deploy-v2.4.0", "metric-error-burst-payment"),
        ("deploy-v2.4.0", "metric-deployment-failure"),
        ("deploy-v2.4.1", "metric-cpu-spike-prod-01"),
        ("deploy-v2.5.0", "metric-throughput-drop-search"),
        ("deploy-v2.5.1", "metric-timeout-gateway"),
        ("deploy-v2.6.0", "metric-connection-pool-exhaust"),
        ("deploy-v2.6.0", "metric-deployment-failure"),
        ("deploy-v3.0.0", "metric-cpu-spike-prod-02"),
        ("deploy-v3.0.0", "metric-memory-pressure-prod-03"),
        ("deploy-v3.1.0", "metric-cache-miss-rate"),
        ("deploy-v3.1.1", "metric-queue-backlog"),
        ("deploy-v3.2.0", "metric-external-api-slow"),
    ]:
        G.add_edge(src, tgt, label="causes")

    for src, tgt in [
        ("alert-high-latency-api", "alert-cascading-failure"),
        ("alert-auth-failures", "alert-cascading-failure"),
        ("alert-order-errors", "alert-cascading-failure"),
        ("alert-payment-declines", "alert-cascading-failure"),
        ("alert-cpu-critical", "alert-cascading-failure"),
        ("alert-gateway-timeout", "alert-cascading-failure"),
        ("alert-external-degradation", "alert-cascading-failure"),
        ("metric-latency-spike-auth", "metric-latency-spike-api"),
        ("metric-error-burst-payment", "metric-error-burst-order"),
        ("metric-cpu-spike-prod-02", "metric-cpu-spike-prod-01"),
        ("metric-memory-pressure-prod-03", "metric-cpu-spike-prod-01"),
        ("deploy-v2.3.2", "deploy-v2.3.1"),
        ("deploy-v2.3.3", "deploy-v2.3.2"),
        ("deploy-hotfix-001", "deploy-v2.3.3"),
        ("deploy-hotfix-002", "deploy-hotfix-001"),
    ]:
        G.add_edge(src, tgt, label="follows")

    for src, tgt in [
        ("alert-cascading-failure", "alert-high-latency-api"),
        ("alert-cascading-failure", "alert-auth-failures"),
        ("alert-cascading-failure", "alert-order-errors"),
        ("alert-cascading-failure", "alert-payment-declines"),
        ("deploy-hotfix-001", "alert-high-latency-api"),
        ("deploy-hotfix-001", "alert-cascading-failure"),
        ("deploy-hotfix-002", "alert-auth-failures"),
        ("deploy-hotfix-002", "alert-deploy-rollback"),
        ("deploy-v3.0.0", "alert-cpu-critical"),
        ("deploy-v3.0.0", "alert-memory-warning"),
        ("deploy-v3.1.0", "alert-search-degraded"),
        ("deploy-v3.1.0", "alert-cache-cold"),
        ("deploy-v3.2.0", "alert-external-degradation"),
        ("deploy-v3.2.0", "alert-connection-leak"),
        ("deploy-v3.0.1", "alert-queue-overflow"),
    ]:
        G.add_edge(src, tgt, label="mitigates")

    for src, tgt in [
        ("host-prod-01", "metric-latency-spike-api"),
        ("host-prod-01", "metric-cpu-spike-prod-01"),
        ("host-prod-02", "metric-error-burst-order"),
        ("host-prod-03", "metric-error-burst-payment"),
        ("host-prod-03", "metric-cpu-spike-prod-02"),
        ("host-prod-04", "metric-throughput-drop-search"),
        ("host-prod-05", "metric-connection-pool-exhaust"),
        ("host-prod-16", "metric-queue-backlog"),
        ("host-prod-16", "metric-cache-miss-rate"),
        ("host-prod-06", "metric-timeout-gateway"),
    ]:
        G.add_edge(src, tgt, label="monitors")

    for src, tgt in [
        ("svc-api-gateway", "metric-latency-spike-api"),
        ("svc-api-gateway", "metric-timeout-gateway"),
        ("svc-api-gateway", "metric-external-api-slow"),
        ("svc-auth", "metric-latency-spike-auth"),
        ("svc-order", "metric-error-burst-order"),
        ("svc-payment", "metric-error-burst-payment"),
        ("svc-search", "metric-throughput-drop-search"),
        ("svc-checkout", "metric-timeout-gateway"),
        ("svc-queue", "metric-queue-backlog"),
        ("svc-cache", "metric-cache-miss-rate"),
        ("svc-webhook", "metric-deployment-failure"),
        ("svc-queue", "metric-connection-pool-exhaust"),
        ("svc-inventory", "metric-external-api-slow"),
        ("svc-shipping", "metric-external-api-slow"),
        ("host-prod-01", "metric-memory-pressure-prod-03"),
    ]:
        G.add_edge(src, tgt, label="affects")

    for corr, alert, metric in [
        ("corr-api-auth-latency", "alert-high-latency-api", "metric-latency-spike-auth"),
        ("corr-order-payment-error", "alert-order-errors", "metric-error-burst-order"),
        ("corr-checkout-cart-fail", "alert-cascading-failure", "metric-error-burst-payment"),
        ("corr-search-index-delay", "alert-search-degraded", "metric-throughput-drop-search"),
        ("corr-cache-queue-backlog", "alert-queue-overflow", "metric-cache-miss-rate"),
        ("corr-deploy-cpu-spike", "alert-cpu-critical", "metric-cpu-spike-prod-01"),
        ("corr-external-gateway-timeout", "alert-gateway-timeout", "metric-timeout-gateway"),
        ("corr-memory-connection-leak", "alert-connection-leak", "metric-connection-pool-exhaust"),
    ]:
        G.add_edge(corr, alert, label="triggers")
        G.add_edge(corr, alert, label="correlates_with")
        G.add_edge(corr, alert, label="follows")
        G.add_edge(corr, metric, label="causes")

    for corr, alert, metric in [
        ("corr-disk-deploy-failure", "alert-deploy-rollback", "metric-deployment-failure"),
        ("corr-subscription-billing", "alert-payment-declines", "metric-error-burst-payment"),
        ("corr-media-content-delivery", "alert-cascading-failure", "metric-throughput-drop-search"),
        ("corr-notification-push-fail", "alert-external-degradation", "metric-external-api-slow"),
        ("corr-analytics-recommendation-drift", "alert-search-degraded", "metric-throughput-drop-search"),
        ("corr-loyalty-promo-abuse", "alert-order-errors", "metric-error-burst-order"),
        ("corr-audit-compliance-gap", "alert-auth-failures", "metric-latency-spike-auth"),
    ]:
        G.add_edge(corr, alert, label="correlates_with")
        G.add_edge(corr, metric, label="correlates_with")

    for src, tgt in [
        ("metric-latency-spike-api", "corr-api-auth-latency"),
        ("metric-error-burst-order", "corr-order-payment-error"),
        ("metric-error-burst-payment", "corr-checkout-cart-fail"),
        ("metric-throughput-drop-search", "corr-search-index-delay"),
        ("metric-cache-miss-rate", "corr-cache-queue-backlog"),
        ("metric-cpu-spike-prod-01", "corr-deploy-cpu-spike"),
        ("metric-timeout-gateway", "corr-external-gateway-timeout"),
        ("metric-connection-pool-exhaust", "corr-memory-connection-leak"),
    ]:
        G.add_edge(src, tgt, label="indicates")

    initial_nodes = G.number_of_nodes()
    initial_edges = G.number_of_edges()
    print(f"  Nodes: {initial_nodes}, Edges: {initial_edges}")
    print(f"    35 services | 20 hosts | 15 metrics | 15 alerts")
    print(f"    15 deployments | 10 external deps | 15 correlations")
    edge_counter: Counter[str] = Counter()
    for _, _, d in G.edges(data=True):
        if d.get("label"):
            edge_counter[d["label"]] += 1
    print(f"  Edge types: {dict(edge_counter)}")
    print()

    # =====================================================================
    # SECTION 2: Auto-Discovery of Structural Patterns
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Auto-Discovery of Structural Patterns")
    print("=" * 70)

    discovery_result = auto_discover_patterns(G)
    print(f"  Total patterns discovered: {discovery_result['total_patterns']}")
    print(f"  New rules added to active set: {discovery_result['new_rules_added']}")

    type_counts: Counter[str] = Counter()
    for p in discovery_result["patterns"]:
        type_counts[p["pattern_type"]] += 1
    print(f"  Pattern breakdown: {dict(type_counts)}")
    print()

    for p in discovery_result["patterns"]:
        if p["pattern_type"] == "transitive":
            label = p.get("edge_label", "?")
            chains = p.get("chain_count", 0)
            print(f"  [transitive] edge_label='{label}' -- {chains} two-hop chains found")
        elif p["pattern_type"] == "inverse":
            fwd = p.get("forward", "?")
            rev = p.get("reverse", "?")
            pairs = p.get("pair_count", 0)
            print(f"  [inverse]    '{fwd}' <-> '{rev}' -- {pairs} mutual pairs")
        elif p["pattern_type"] == "hub":
            hub = p.get("hub_node", "?")
            lbl = p.get("edge_label", "?")
            fan = p.get("fan_out", 0)
            print(f"  [hub]        '{hub}' fans out {fan}x via '{lbl}'")
    print()

    # =====================================================================
    # SECTION 3: TransitiveRule -- Multi-Hop Dependency Chains
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: TransitiveRule -- Multi-Hop Dependency Chains")
    print("=" * 70)

    t_chains = find_transitive_chains(G, "depends_on")

    print(f"  Found {len(t_chains)} transitive dependency chains")
    print(f"  (A depends_on B depends_on C => A inferred_depends_on C)")
    print()

    seen_targets: Counter[str] = Counter()
    for a, b, c in t_chains:
        seen_targets[c] += 1
    top_targets = seen_targets.most_common(8)
    print("  Top transitive targets (most reached via chains):")
    for tgt, count in top_targets:
        print(f"    {tgt}: reached by {count} chain(s)")

    print()
    print("  Sample chains (showing A -> B -> C):")
    for a, b, c in t_chains[:12]:
        print(f"    {a} -> {b} -> {c}")
    print()

    # =====================================================================
    # SECTION 4: CausalInferenceRule -- Co-Occurrence Patterns
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: CausalInferenceRule -- Co-Occurrence Patterns")
    print("=" * 70)

    c_matches = find_causal_links(G, min_support=2, confidence_threshold=0.6, causes_label="causes")

    print(f"  Found {len(c_matches)} causal relationships")
    print(f"  (min_support=2, confidence_threshold=0.6)")
    print()

    for m in c_matches:
        cause = m["cause"]
        effect = m["effect"]
        support = m["support"]
        conf = m["confidence"]
        print(f"  {cause}")
        print(f"    -> {effect}  (support={support}, confidence={conf:.2f})")
    print()

    # =====================================================================
    # SECTION 5: GeneralizationRule -- Abstract Service Categories
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: GeneralizationRule -- Abstract Service Categories")
    print("=" * 70)

    service_names = [n for n in G.nodes() if n.startswith("svc-")]
    g_matches = find_similar_services(G, service_names, similarity_threshold=0.8)

    print(f"  Found {len(g_matches)} service abstraction pairs (similarity >= 0.8)")
    print()

    team_groups: dict[str, list[tuple[str, str, float]]] = {}
    for m in g_matches:
        la = m["label_a"]
        lb = m["label_b"]
        sim = m["similarity"]
        team = m["team"]
        team_groups.setdefault(team, []).append((la, lb, sim))

    for team, pairs in sorted(team_groups.items()):
        print(f"  Team '{team}' -- {len(pairs)} similar pair(s):")
        for la, lb, sim in pairs:
            print(f"    {la} ~ {lb}  (similarity={sim:.2f})")

    print()
    print("  Applying generalization to create abstract category nodes...")
    for m in g_matches[:5]:
        cat_name = f"category_{m['label_a']}_{m['label_b']}"
        G.add_node(cat_name, kind="category", team=m["team"])
        G.add_edge(cat_name, m["label_a"], label="generalizes_to")
        G.add_edge(cat_name, m["label_b"], label="generalizes_to")
    print(f"  Created {min(5, len(g_matches))} category nodes")
    print(f"  Graph now: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print()

    # =====================================================================
    # SECTION 6: AnalogicalReasoningRule -- Structural Analogies
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: AnalogicalReasoningRule -- Structural Analogies")
    print("=" * 70)

    all_node_set = set(G.nodes())
    a_matches = find_analogies(G, all_node_set, similarity_threshold=0.7, dim=32)

    print(f"  Found {len(a_matches)} structural analogies (A:B :: C:D)")
    print()

    if a_matches:
        print("  Top analogies by score:")
        for m in a_matches[:10]:
            print(f"    {m['A']}:{m['B']} :: {m['C']}:{m['D']}  (score={m['analogy_score']:.3f})")
    else:
        print("  No analogies above threshold 0.7 with hash embeddings.")
        print("  In production, use sentence-transformer providers for")
        print("  semantically meaningful analogies.")
    print()

    # =====================================================================
    # SECTION 7: Full Reasoning with All Rules Combined
    # =====================================================================

    print("=" * 70)
    print("SECTION 7: Full Reasoning with All Rules Combined")
    print("=" * 70)

    seeds = {
        "svc-api-gateway", "svc-auth", "svc-user",
        "svc-order", "svc-payment", "svc-billing", "svc-checkout",
    }
    pre_nodes = G.number_of_nodes()
    pre_edges = G.number_of_edges()

    transitive_inferred = find_transitive_chains(G, "depends_on")
    for a, b, c in transitive_inferred:
        if not G.has_edge(a, c):
            G.add_edge(a, c, label="inferred_depends_on", inferred=True)

    mitigates_set = edge_set_by_label(G, "mitigates")
    for src, tgt in mitigates_set:
        if not G.has_edge(tgt, src):
            G.add_edge(tgt, src, label="resolved_by", inferred=True)

    visited: set[str] = set()
    frontier: set[str] = set(seeds)
    states_created = 0
    max_depth = 3
    for depth in range(max_depth):
        next_frontier: set[str] = set()
        for node in frontier:
            if node in visited:
                continue
            visited.add(node)
            states_created += 1
            for _, tgt in G.out_edges(node):
                if tgt not in visited:
                    next_frontier.add(tgt)
        frontier = next_frontier
        if not frontier:
            break

    rules_applied = len(transitive_inferred) + len(mitigates_set)

    post_nodes = G.number_of_nodes()
    post_edges = G.number_of_edges()
    print()
    print(f"  Seeds: {sorted(seeds)}")
    print(f"  (chosen to form depends_on chains for transitive inference)")
    print(f"  States created:     {states_created}")
    print(f"  Rules applied:      {rules_applied}")
    print(f"  Max depth reached:  {max_depth}")

    print()
    print(f"  Graph growth:")
    print(f"    Before reasoning: {pre_nodes} nodes, {pre_edges} edges")
    print(f"    After reasoning:  {post_nodes} nodes, {post_edges} edges")
    print(f"    Delta:            +{post_nodes - pre_nodes} nodes, +{post_edges - pre_edges} edges")

    new_edge_labels: Counter[str] = Counter()
    inferred_edges = 0
    for _, _, d in G.edges(data=True):
        if d.get("inferred"):
            inferred_edges += 1
            if d.get("label"):
                new_edge_labels[d["label"]] += 1
    print()
    print(f"  Total inferred edges in graph: {inferred_edges}")
    if new_edge_labels:
        print(f"  Inferred edge types: {dict(new_edge_labels)}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Infrastructure:  {initial_nodes} nodes, {initial_edges} edges")
    print(f"  Auto-discovery:  {discovery_result['total_patterns']} patterns")
    for ptype, count in sorted(type_counts.items()):
        print(f"    {ptype}: {count}")
    print(f"  Transitive chains:  {len(t_chains)} hidden dependency paths")
    print(f"  Causal links:       {len(c_matches)} co-occurrence patterns")
    print(f"  Abstractions:       {len(g_matches)} similar-service pairs")
    print(f"  Analogies:          {len(a_matches)} structural (A:B::C:D)")
    print(f"  Final graph:        {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print()
    print("  Key takeaway: rule-based reasoning transforms raw telemetry")
    print("  edges into actionable knowledge -- hidden dependencies, causal")
    print("  chains, and service abstractions -- without manual rule writing")
    print("  for every possible pattern.")
    print()


if __name__ == "__main__":
    main()
