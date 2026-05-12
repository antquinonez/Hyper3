"""
Multi-Perspective Risk Assessment (Standard Library Reimplementation)
=====================================================================

Reimplements Hyper3's multi-frame reasoning example using networkx.DiGraph,
BFS with 4 different parameter sets (frames), reachability set comparison,
zlib compression for Kolmogorov approximation, and numpy spectral gap.

Run with:
    .venv/bin/python examples/comparison/09_iterative_frame_reasoning.py
"""

from __future__ import annotations

import zlib
from collections import defaultdict

import networkx as nx
import numpy as np


def build_infrastructure(G: nx.DiGraph) -> set[str]:
    services = {
        "web_frontend": {"type": "service", "exposure": "internet", "criticality": 8, "data_classification": "public"},
        "mobile_app": {"type": "service", "exposure": "internet", "criticality": 7, "data_classification": "public"},
        "api_gateway": {"type": "service", "exposure": "dmz", "criticality": 9, "data_classification": "internal"},
        "auth_service": {"type": "service", "exposure": "internal", "criticality": 10, "data_classification": "confidential"},
        "user_service": {"type": "service", "exposure": "internal", "criticality": 8, "data_classification": "confidential"},
        "order_service": {"type": "service", "exposure": "internal", "criticality": 9, "data_classification": "confidential"},
        "payment_service": {"type": "service", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "inventory_service": {"type": "service", "exposure": "internal", "criticality": 7, "data_classification": "internal"},
        "notification_service": {"type": "service", "exposure": "internal", "criticality": 4, "data_classification": "internal"},
        "search_service": {"type": "service", "exposure": "internal", "criticality": 5, "data_classification": "internal"},
        "analytics_service": {"type": "service", "exposure": "internal", "criticality": 6, "data_classification": "confidential"},
        "reporting_service": {"type": "service", "exposure": "internal", "criticality": 5, "data_classification": "internal"},
        "cache_redis": {"type": "service", "exposure": "internal", "criticality": 7, "data_classification": "internal"},
        "queue_rabbitmq": {"type": "service", "exposure": "internal", "criticality": 8, "data_classification": "internal"},
        "cdn_edge": {"type": "service", "exposure": "internet", "criticality": 6, "data_classification": "public"},
        "load_balancer": {"type": "service", "exposure": "dmz", "criticality": 9, "data_classification": "public"},
        "dns_resolver": {"type": "service", "exposure": "dmz", "criticality": 8, "data_classification": "public"},
        "mail_relay": {"type": "service", "exposure": "dmz", "criticality": 4, "data_classification": "internal"},
        "vpn_concentrator": {"type": "service", "exposure": "dmz", "criticality": 7, "data_classification": "confidential"},
        "log_aggregator": {"type": "service", "exposure": "internal", "criticality": 6, "data_classification": "internal"},
        "config_vault": {"type": "service", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "scheduler": {"type": "service", "exposure": "internal", "criticality": 5, "data_classification": "internal"},
        "graphql_endpoint": {"type": "service", "exposure": "dmz", "criticality": 7, "data_classification": "internal"},
        "grpc_internal": {"type": "service", "exposure": "internal", "criticality": 6, "data_classification": "internal"},
        "doc_service": {"type": "service", "exposure": "internal", "criticality": 4, "data_classification": "internal"},
        "batch_processor": {"type": "service", "exposure": "internal", "criticality": 6, "data_classification": "confidential"},
        "health_check": {"type": "service", "exposure": "dmz", "criticality": 5, "data_classification": "public"},
        "rate_limiter": {"type": "service", "exposure": "dmz", "criticality": 7, "data_classification": "internal"},
        "feature_flags": {"type": "service", "exposure": "internal", "criticality": 3, "data_classification": "internal"},
        "blob_storage": {"type": "service", "exposure": "internal", "criticality": 5, "data_classification": "internal"},
    }

    data_stores = {
        "db_customers": {"type": "datastore", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "db_orders": {"type": "datastore", "exposure": "internal", "criticality": 9, "data_classification": "confidential"},
        "db_payments": {"type": "datastore", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "db_products": {"type": "datastore", "exposure": "internal", "criticality": 6, "data_classification": "internal"},
        "db_sessions": {"type": "datastore", "exposure": "internal", "criticality": 7, "data_classification": "confidential"},
        "db_analytics": {"type": "datastore", "exposure": "internal", "criticality": 5, "data_classification": "confidential"},
        "db_audit_log": {"type": "datastore", "exposure": "internal", "criticality": 8, "data_classification": "restricted"},
        "object_storage": {"type": "datastore", "exposure": "internal", "criticality": 6, "data_classification": "internal"},
        "secrets_store": {"type": "datastore", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "config_backup": {"type": "datastore", "exposure": "internal", "criticality": 7, "data_classification": "confidential"},
        "db_inventory": {"type": "datastore", "exposure": "internal", "criticality": 6, "data_classification": "internal"},
        "db_notifications": {"type": "datastore", "exposure": "internal", "criticality": 3, "data_classification": "internal"},
        "db_feature_flags": {"type": "datastore", "exposure": "internal", "criticality": 2, "data_classification": "internal"},
        "db_health_status": {"type": "datastore", "exposure": "internal", "criticality": 3, "data_classification": "internal"},
        "db_rate_limits": {"type": "datastore", "exposure": "internal", "criticality": 5, "data_classification": "internal"},
    }

    network = {
        "seg_dmz": {"type": "network", "exposure": "dmz", "criticality": 8, "data_classification": "mixed"},
        "seg_app": {"type": "network", "exposure": "internal", "criticality": 7, "data_classification": "internal"},
        "seg_data": {"type": "network", "exposure": "internal", "criticality": 9, "data_classification": "restricted"},
        "seg_mgmt": {"type": "network", "exposure": "internal", "criticality": 8, "data_classification": "confidential"},
        "seg_public": {"type": "network", "exposure": "internet", "criticality": 5, "data_classification": "public"},
    }

    security = {
        "fw_perimeter": {"type": "security", "exposure": "perimeter", "criticality": 9, "data_classification": "public"},
        "fw_internal": {"type": "security", "exposure": "internal", "criticality": 8, "data_classification": "internal"},
        "waf": {"type": "security", "exposure": "dmz", "criticality": 8, "data_classification": "public"},
        "ids_sensor": {"type": "security", "exposure": "dmz", "criticality": 7, "data_classification": "internal"},
        "siem": {"type": "security", "exposure": "internal", "criticality": 9, "data_classification": "confidential"},
        "cert_manager": {"type": "security", "exposure": "internal", "criticality": 8, "data_classification": "restricted"},
        "iam_provider": {"type": "security", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "dlp_gateway": {"type": "security", "exposure": "dmz", "criticality": 7, "data_classification": "confidential"},
        "endpoint_protect": {"type": "security", "exposure": "internal", "criticality": 6, "data_classification": "internal"},
        "vuln_scanner": {"type": "security", "exposure": "internal", "criticality": 5, "data_classification": "internal"},
        "hsm": {"type": "security", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "backup_vault": {"type": "security", "exposure": "internal", "criticality": 8, "data_classification": "restricted"},
        "token_service": {"type": "security", "exposure": "internal", "criticality": 9, "data_classification": "restricted"},
    }

    users = {
        "end_users": {"type": "user_group", "exposure": "internet", "criticality": 3, "data_classification": "public"},
        "customer_support": {"type": "user_group", "exposure": "internal", "criticality": 5, "data_classification": "confidential"},
        "engineering": {"type": "user_group", "exposure": "internal", "criticality": 6, "data_classification": "confidential"},
        "finance_team": {"type": "user_group", "exposure": "internal", "criticality": 7, "data_classification": "restricted"},
        "sysadmin": {"type": "user_group", "exposure": "internal", "criticality": 9, "data_classification": "restricted"},
        "third_party_api": {"type": "user_group", "exposure": "dmz", "criticality": 6, "data_classification": "confidential"},
        "payment_processor": {"type": "user_group", "exposure": "dmz", "criticality": 8, "data_classification": "restricted"},
        "auditor": {"type": "user_group", "exposure": "internal", "criticality": 5, "data_classification": "confidential"},
        "monitoring_agent": {"type": "user_group", "exposure": "internal", "criticality": 6, "data_classification": "internal"},
    }

    data_flows = {
        "flow_login": {"type": "dataflow", "exposure": "dmz", "criticality": 8, "data_classification": "confidential"},
        "flow_orders": {"type": "dataflow", "exposure": "internal", "criticality": 9, "data_classification": "confidential"},
        "flow_payments": {"type": "dataflow", "exposure": "internal", "criticality": 10, "data_classification": "restricted"},
        "flow_analytics": {"type": "dataflow", "exposure": "internal", "criticality": 5, "data_classification": "confidential"},
        "flow_notifications": {"type": "dataflow", "exposure": "internal", "criticality": 3, "data_classification": "internal"},
        "flow_search": {"type": "dataflow", "exposure": "internal", "criticality": 4, "data_classification": "internal"},
        "flow_audit": {"type": "dataflow", "exposure": "internal", "criticality": 7, "data_classification": "restricted"},
        "flow_reporting": {"type": "dataflow", "exposure": "internal", "criticality": 4, "data_classification": "internal"},
    }

    all_entities = {}
    for group in (services, data_stores, network, security, users, data_flows):
        all_entities.update(group)

    for name, data in all_entities.items():
        G.add_node(name, **data)

    relations = [
        ("seg_public", "cdn_edge", "contains"),
        ("seg_public", "dns_resolver", "contains"),
        ("seg_dmz", "load_balancer", "contains"),
        ("seg_dmz", "waf", "contains"),
        ("seg_dmz", "ids_sensor", "contains"),
        ("seg_dmz", "dlp_gateway", "contains"),
        ("seg_dmz", "mail_relay", "contains"),
        ("seg_dmz", "vpn_concentrator", "contains"),
        ("seg_dmz", "graphql_endpoint", "contains"),
        ("seg_app", "api_gateway", "contains"),
        ("seg_app", "auth_service", "contains"),
        ("seg_app", "user_service", "contains"),
        ("seg_app", "order_service", "contains"),
        ("seg_app", "payment_service", "contains"),
        ("seg_app", "inventory_service", "contains"),
        ("seg_app", "notification_service", "contains"),
        ("seg_app", "search_service", "contains"),
        ("seg_app", "analytics_service", "contains"),
        ("seg_app", "reporting_service", "contains"),
        ("seg_app", "cache_redis", "contains"),
        ("seg_app", "queue_rabbitmq", "contains"),
        ("seg_app", "log_aggregator", "contains"),
        ("seg_app", "config_vault", "contains"),
        ("seg_app", "scheduler", "contains"),
        ("seg_app", "grpc_internal", "contains"),
        ("seg_app", "doc_service", "contains"),
        ("seg_data", "db_customers", "contains"),
        ("seg_data", "db_orders", "contains"),
        ("seg_data", "db_payments", "contains"),
        ("seg_data", "db_products", "contains"),
        ("seg_data", "db_sessions", "contains"),
        ("seg_data", "db_analytics", "contains"),
        ("seg_data", "db_audit_log", "contains"),
        ("seg_data", "object_storage", "contains"),
        ("seg_data", "secrets_store", "contains"),
        ("seg_data", "config_backup", "contains"),
        ("seg_data", "db_inventory", "contains"),
        ("seg_data", "db_notifications", "contains"),
        ("seg_mgmt", "siem", "contains"),
        ("seg_mgmt", "vuln_scanner", "contains"),
        ("seg_mgmt", "endpoint_protect", "contains"),

        ("end_users", "cdn_edge", "accesses"),
        ("end_users", "web_frontend", "accesses"),
        ("end_users", "mobile_app", "accesses"),
        ("cdn_edge", "load_balancer", "routes_to"),
        ("web_frontend", "cdn_edge", "depends_on"),
        ("web_frontend", "api_gateway", "depends_on"),
        ("mobile_app", "api_gateway", "depends_on"),
        ("end_users", "dns_resolver", "accesses"),
        ("dns_resolver", "load_balancer", "routes_to"),
        ("load_balancer", "waf", "routes_to"),
        ("waf", "api_gateway", "routes_to"),
        ("waf", "graphql_endpoint", "routes_to"),
        ("api_gateway", "auth_service", "depends_on"),
        ("api_gateway", "user_service", "depends_on"),
        ("api_gateway", "order_service", "depends_on"),
        ("api_gateway", "search_service", "depends_on"),
        ("api_gateway", "notification_service", "depends_on"),
        ("api_gateway", "doc_service", "depends_on"),
        ("graphql_endpoint", "auth_service", "depends_on"),
        ("graphql_endpoint", "order_service", "depends_on"),
        ("graphql_endpoint", "inventory_service", "depends_on"),
        ("auth_service", "iam_provider", "depends_on"),
        ("auth_service", "db_sessions", "accesses"),
        ("auth_service", "config_vault", "depends_on"),
        ("auth_service", "cert_manager", "depends_on"),
        ("user_service", "db_customers", "stores"),
        ("user_service", "cache_redis", "depends_on"),
        ("user_service", "grpc_internal", "depends_on"),
        ("order_service", "db_orders", "stores"),
        ("order_service", "payment_service", "depends_on"),
        ("order_service", "inventory_service", "depends_on"),
        ("order_service", "queue_rabbitmq", "depends_on"),
        ("order_service", "notification_service", "depends_on"),
        ("order_service", "cache_redis", "depends_on"),
        ("order_service", "grpc_internal", "depends_on"),
        ("payment_service", "db_payments", "stores"),
        ("payment_service", "payment_processor", "depends_on"),
        ("payment_service", "config_vault", "depends_on"),
        ("payment_service", "queue_rabbitmq", "depends_on"),
        ("payment_service", "grpc_internal", "depends_on"),
        ("inventory_service", "db_inventory", "stores"),
        ("inventory_service", "db_products", "accesses"),
        ("inventory_service", "cache_redis", "depends_on"),
        ("notification_service", "mail_relay", "depends_on"),
        ("notification_service", "db_notifications", "stores"),
        ("notification_service", "queue_rabbitmq", "depends_on"),
        ("search_service", "db_products", "accesses"),
        ("search_service", "cache_redis", "depends_on"),
        ("analytics_service", "db_analytics", "accesses"),
        ("analytics_service", "queue_rabbitmq", "depends_on"),
        ("analytics_service", "scheduler", "depends_on"),
        ("reporting_service", "db_orders", "accesses"),
        ("reporting_service", "db_analytics", "accesses"),
        ("reporting_service", "object_storage", "depends_on"),
        ("doc_service", "object_storage", "accesses"),
        ("doc_service", "cache_redis", "depends_on"),
        ("scheduler", "queue_rabbitmq", "depends_on"),
        ("grpc_internal", "auth_service", "depends_on"),
        ("grpc_internal", "config_vault", "depends_on"),

        ("fw_perimeter", "seg_dmz", "protects"),
        ("fw_perimeter", "seg_public", "protects"),
        ("fw_internal", "seg_app", "protects"),
        ("fw_internal", "seg_data", "protects"),
        ("fw_internal", "seg_mgmt", "protects"),

        ("config_vault", "secrets_store", "accesses"),
        ("config_vault", "config_backup", "depends_on"),

        ("customer_support", "user_service", "accesses"),
        ("customer_support", "order_service", "accesses"),
        ("engineering", "api_gateway", "accesses"),
        ("engineering", "log_aggregator", "accesses"),
        ("finance_team", "reporting_service", "accesses"),
        ("finance_team", "payment_service", "accesses"),
        ("sysadmin", "config_vault", "accesses"),
        ("sysadmin", "siem", "accesses"),
        ("sysadmin", "vuln_scanner", "accesses"),
        ("sysadmin", "vpn_concentrator", "accesses"),
        ("auditor", "db_audit_log", "accesses"),
        ("auditor", "siem", "accesses"),
        ("third_party_api", "api_gateway", "accesses"),

        ("flow_login", "auth_service", "processes"),
        ("flow_login", "iam_provider", "processes"),
        ("flow_login", "db_sessions", "processes"),
        ("flow_orders", "order_service", "processes"),
        ("flow_orders", "inventory_service", "processes"),
        ("flow_orders", "notification_service", "processes"),
        ("flow_payments", "payment_service", "processes"),
        ("flow_payments", "payment_processor", "processes"),
        ("flow_payments", "db_payments", "processes"),
        ("flow_analytics", "analytics_service", "processes"),
        ("flow_analytics", "db_analytics", "processes"),
        ("flow_notifications", "notification_service", "processes"),
        ("flow_notifications", "mail_relay", "processes"),
        ("flow_search", "search_service", "processes"),
        ("flow_audit", "log_aggregator", "processes"),
        ("flow_audit", "siem", "processes"),
        ("flow_audit", "db_audit_log", "processes"),
        ("flow_reporting", "reporting_service", "processes"),
        ("flow_reporting", "object_storage", "processes"),

        ("log_aggregator", "siem", "routes_to"),
        ("ids_sensor", "siem", "routes_to"),
        ("endpoint_protect", "siem", "routes_to"),

        ("vpn_concentrator", "fw_perimeter", "depends_on"),
        ("vpn_concentrator", "auth_service", "depends_on"),

        ("iam_provider", "cert_manager", "depends_on"),
        ("iam_provider", "secrets_store", "accesses"),

        ("dlp_gateway", "flow_payments", "protects"),
        ("dlp_gateway", "flow_reporting", "protects"),

        ("rate_limiter", "api_gateway", "protects"),
        ("rate_limiter", "db_rate_limits", "depends_on"),
        ("health_check", "api_gateway", "depends_on"),
        ("health_check", "auth_service", "depends_on"),
        ("health_check", "db_health_status", "stores"),
        ("feature_flags", "db_feature_flags", "stores"),
        ("api_gateway", "feature_flags", "depends_on"),
        ("batch_processor", "queue_rabbitmq", "depends_on"),
        ("batch_processor", "db_orders", "accesses"),
        ("batch_processor", "db_analytics", "stores"),
        ("batch_processor", "scheduler", "depends_on"),
        ("blob_storage", "object_storage", "depends_on"),
        ("doc_service", "blob_storage", "depends_on"),

        ("payment_service", "hsm", "depends_on"),
        ("auth_service", "token_service", "depends_on"),
        ("token_service", "hsm", "depends_on"),
        ("token_service", "secrets_store", "accesses"),
        ("cert_manager", "hsm", "depends_on"),
        ("backup_vault", "secrets_store", "accesses"),
        ("backup_vault", "config_backup", "accesses"),
        ("backup_vault", "db_audit_log", "accesses"),

        ("seg_app", "batch_processor", "contains"),
        ("seg_app", "rate_limiter", "contains"),
        ("seg_app", "feature_flags", "contains"),
        ("seg_app", "blob_storage", "contains"),
        ("seg_app", "health_check", "contains"),
        ("seg_mgmt", "hsm", "contains"),
        ("seg_mgmt", "backup_vault", "contains"),
        ("seg_mgmt", "token_service", "contains"),
        ("seg_data", "db_feature_flags", "contains"),
        ("seg_data", "db_health_status", "contains"),
        ("seg_data", "db_rate_limits", "contains"),
        ("monitoring_agent", "siem", "accesses"),
        ("monitoring_agent", "log_aggregator", "accesses"),
        ("monitoring_agent", "health_check", "accesses"),
    ]

    for src, tgt, label in relations:
        G.add_edge(src, tgt, label=label)

    return set(all_entities.keys())


def add_transitive_edges(G: nx.DiGraph, edge_label: str, new_label: str) -> int:
    added = 0
    edges_of_label = [(u, v) for u, v, d in G.edges(data=True) if d.get("label") == edge_label]
    for u, v in edges_of_label:
        for w in G.successors(v):
            vd = G.edges[v, w]
            if vd.get("label") == edge_label:
                if not G.has_edge(u, w) or not any(
                    d.get("label") == new_label for d in [G.edges[u, w]]
                ):
                    G.add_edge(u, w, label=new_label)
                    added += 1
    return added


def add_inverse_edges(G: nx.DiGraph, edge_label: str, inverse_label: str) -> int:
    added = 0
    edges_of_label = [(u, v) for u, v, d in G.edges(data=True) if d.get("label") == edge_label]
    for u, v in edges_of_label:
        if not G.has_edge(v, u) or not any(
            G.edges[v, u].get("label") == inverse_label
        ):
            G.add_edge(v, u, label=inverse_label)
            added += 1
    return added


def bfs_reachable(G: nx.DiGraph, seeds: set[str], max_depth: int = 4,
                  edge_filter: set[str] | None = None,
                  node_filter=None) -> set[str]:
    reachable: set[str] = set()
    frontier = list(seeds)
    visited = set(seeds)

    for _ in range(max_depth):
        next_frontier = []
        for nid in frontier:
            for _, tgt, data in G.out_edges(nid, data=True):
                label = data.get("label", "")
                if edge_filter and label not in edge_filter:
                    continue
                if node_filter and node_filter(tgt):
                    reachable.add(tgt)
                    continue
                if tgt not in visited:
                    visited.add(tgt)
                    next_frontier.append(tgt)
                reachable.add(tgt)
        frontier = next_frontier

    return reachable


def degree_centrality(G: nx.DiGraph) -> dict[str, float]:
    deg = {}
    n = G.number_of_nodes()
    if n <= 1:
        return {n: 1.0 for n in G.nodes()}
    for node in G.nodes():
        deg[node] = (G.in_degree(node) + G.out_degree(node)) / (2 * (n - 1))
    return deg


def is_sensitive(node: str, G: nx.DiGraph) -> bool:
    data = G.nodes[node]
    classification = data.get("data_classification", "internal")
    return classification in ("confidential", "restricted")


def kolmogorov_approx(items: set[str]) -> int:
    serialized = ",".join(sorted(items)).encode()
    return len(zlib.compress(serialized, 9))


def spectral_gap(G: nx.DiGraph) -> float:
    nodes = list(G.nodes())
    n = len(nodes)
    if n < 2:
        return 0.0
    idx = {node: i for i, node in enumerate(nodes)}
    A = np.zeros((n, n))
    for u, v in G.edges():
        A[idx[u], idx[v]] = 1.0
    L = np.diag(A.sum(axis=1)) - A
    eigenvalues = np.sort(np.linalg.eigvalsh(L))
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) >= 2:
        return float(pos[1])
    elif len(pos) == 1:
        return float(pos[0])
    return 0.0


def analyze_perspective(
    G: nx.DiGraph,
    seeds: set[str],
    frame_name: str,
    perspective_label: str,
) -> dict:
    print(f"\n  --- {perspective_label} ({frame_name} frame) ---")

    centrality = degree_centrality(G)

    if frame_name == "classical":
        reachable = bfs_reachable(G, seeds, max_depth=4)
    elif frame_name == "hypergraph":
        reachable = bfs_reachable(
            G, seeds, max_depth=5,
            edge_filter={"depends_on", "routes_to", "indirect_depends_on",
                         "indirect_routes_to", "accesses", "stores"},
        )
    elif frame_name == "probabilistic":
        reachable = bfs_reachable(
            G, seeds, max_depth=3,
            edge_filter={"accesses", "stores", "processes", "depends_on",
                         "contains", "protects"},
            node_filter=lambda n: is_sensitive(n, G),
        )
    elif frame_name == "quantum":
        reachable = bfs_reachable(
            G, seeds, max_depth=6,
            edge_filter={"depends_on", "routes_to", "indirect_depends_on",
                         "indirect_routes_to"},
        )
    else:
        reachable = bfs_reachable(G, seeds, max_depth=4)

    reachability_scores: dict[str, float] = {}
    for node in reachable:
        if node in centrality:
            data = G.nodes[node]
            crit = data.get("criticality", 5)
            reachability_scores[node] = centrality[node] * crit

    sorted_assets = sorted(reachability_scores.items(), key=lambda x: x[1], reverse=True)

    print(f"    Reachable nodes: {len(reachable)}")
    print(f"    Top critical assets from this perspective:")
    for label, score in sorted_assets[:6]:
        data = G.nodes[label]
        dtype = data.get("type", "?")
        print(f"      {label:25s}  score={score:.3f}  type={dtype}")

    comp_size = kolmogorov_approx(reachable)
    print(f"    Kolmogorov approx (zlib bytes): {comp_size}")

    return {
        "reachable_labels": reachable,
        "sorted_assets": sorted_assets,
        "frame_name": frame_name,
    }


def find_invariants_and_disagreements(
    G: nx.DiGraph,
    seeds: set[str],
    perspective_results: dict[str, dict],
) -> None:
    print("\n  --- Cross-Perspective Invariants ---")

    all_reachable: dict[str, set[str]] = {}
    for pname, res in perspective_results.items():
        all_reachable[pname] = res["reachable_labels"]

    if not all_reachable:
        return

    union_all = set.union(*all_reachable.values())
    intersection_all = set.intersection(*all_reachable.values()) if len(all_reachable) > 1 else union_all
    disagreeing = union_all - intersection_all

    invariant_assets = []
    for label in intersection_all:
        data = G.nodes[label]
        crit = data.get("criticality", 0)
        dtype = data.get("type", "?")
        invariant_assets.append((label, crit, dtype))

    invariant_assets.sort(key=lambda x: x[1], reverse=True)

    print(f"    Invariant nodes (reachable from ALL frames): {len(intersection_all)}")
    print(f"    Confidence: {len(intersection_all) / len(union_all):.3f}" if union_all else "    Confidence: 0.000")

    per_frame_unique: dict[str, set[str]] = {}
    for fname, reachable in all_reachable.items():
        unique = reachable - intersection_all
        per_frame_unique[fname] = unique

    print(f"    Per-frame unique nodes:")
    for fname, unique in per_frame_unique.items():
        print(f"      {fname:15s}: {len(unique)} unique")
        for ul in sorted(unique)[:4]:
            print(f"        - {ul}")

    print(f"\n    Top invariant assets (protect these first):")
    for label, crit, dtype in invariant_assets[:10]:
        print(f"      {label:25s}  criticality={crit}  type={dtype}")

    print("\n  --- Disagreement Regions (Perspective Analysis) ---")
    disagreements: list[tuple[str, list[str], list[str]]] = []
    for label in sorted(disagreeing):
        agreeing = [p for p, nodes in all_reachable.items() if label in nodes]
        disagreeing_frames = [p for p in all_reachable if p not in agreeing]
        if disagreeing_frames:
            disagreements.append((label, agreeing, disagreeing_frames))

    print(f"    Total nodes seen by any perspective: {len(union_all)}")
    print(f"    Nodes seen by ALL perspectives: {len(intersection_all)}")
    print(f"    Nodes where perspectives disagree: {len(disagreements)}")
    for label, agreeing, disagreeing_frames in disagreements[:12]:
        data = G.nodes[label]
        dtype = data.get("type", "?")
        print(f"      {label:25s}  type={dtype}  "
              f"seen_by={agreeing}  missed_by={disagreeing_frames}")

    gap = spectral_gap(G)
    print(f"\n  Graph spectral gap (algebraic connectivity): {gap:.4f}")
    print(f"  Higher spectral gap = more connected = harder to partition")


def generate_recommendations(
    G: nx.DiGraph,
    perspective_results: dict[str, dict],
) -> None:
    print("\n  --- Recommended Action Items ---")

    all_top_assets: dict[str, int] = defaultdict(int)
    for pname, res in perspective_results.items():
        for label, _score in res["sorted_assets"][:8]:
            all_top_assets[label] += 1

    universal_critical = {l for l, c in all_top_assets.items() if c >= 3}
    mostly_critical = {l for l, c in all_top_assets.items() if c >= 2}

    print(f"    Critical in 3+ perspectives ({len(universal_critical)} assets):")
    for label in sorted(universal_critical):
        data = G.nodes[label]
        print(f"      - Prioritize hardening: {label} "
              f"(criticality={data.get('criticality', '?')}, "
              f"exposure={data.get('exposure', '?')})")

    secondary = (mostly_critical - universal_critical)
    if secondary:
        print(f"\n    Critical in 2 perspectives ({len(secondary)} assets):")
        for label in sorted(secondary):
            data = G.nodes[label]
            print(f"      - Add monitoring: {label} "
                  f"(criticality={data.get('criticality', '?')}, "
                  f"type={data.get('type', '?')})")

    single_frame_only = {l for l, c in all_top_assets.items() if c == 1}
    if single_frame_only:
        print(f"\n    Single-perspective concerns ({len(single_frame_only)} assets):")
        for label in sorted(list(single_frame_only)[:6]):
            perspectives = [p for p, res in perspective_results.items()
                            if any(l == label for l, _ in res["sorted_assets"][:8])]
            print(f"      - Investigate: {label} "
                  f"(flagged by: {', '.join(perspectives)})")

    high_crit = []
    for node in G.nodes():
        data = G.nodes[node]
        crit = data.get("criticality", 0)
        exposure = data.get("exposure", "internal")
        dtype = data.get("type", "")
        if crit >= 9 and dtype == "service":
            dep_count = sum(1 for _, tgt, d in G.in_edges(node, data=True)
                            if d.get("label") == "depends_on")
            high_crit.append((node, crit, exposure, dep_count))

    if high_crit:
        high_crit.sort(key=lambda x: x[3], reverse=True)
        print(f"\n    High-criticality dependency hubs (single points of failure):")
        for label, crit, exposure, dep_count in high_crit:
            print(f"      - {label}: criticality={crit}, "
                  f"exposure={exposure}, depended_on_by={dep_count}")


def main():
    G = nx.DiGraph()

    # =====================================================================
    # SECTION 1: Infrastructure Graph Construction
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Infrastructure Graph Construction")
    print("=" * 70)

    all_labels = build_infrastructure(G)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")

    t1 = add_transitive_edges(G, "depends_on", "indirect_depends_on")
    t2 = add_transitive_edges(G, "routes_to", "indirect_routes_to")
    t3 = add_transitive_edges(G, "accesses", "indirect_accesses")
    i1 = add_inverse_edges(G, "depends_on", "depended_on_by")
    i2 = add_inverse_edges(G, "contains", "contained_in")
    print(f"  Transitive edges added: depends_on={t1}, routes_to={t2}, accesses={t3}")
    print(f"  Inverse edges added: depends_on={i1}, contains={i2}")
    print(f"  Total edges after inference: {G.number_of_edges()}")

    # =====================================================================
    # SECTION 2: Four Analysis Perspectives
    # =====================================================================

    print()
    print("=" * 70)
    print("SECTION 2: Multi-Perspective Analysis")
    print("=" * 70)

    seeds = {"api_gateway", "auth_service", "payment_service"}

    perspectives = {
        "classical": "Standard Dependency Analysis",
        "hypergraph": "Structural Risk Propagation",
        "probabilistic": "Compliance / Data Flow Analysis",
        "quantum": "Operational Impact Analysis",
    }

    perspective_results: dict[str, dict] = {}
    for frame, label in perspectives.items():
        perspective_results[frame] = analyze_perspective(
            G, seeds, frame, label,
        )

    # =====================================================================
    # SECTION 3: Cross-Perspective Invariants and Disagreements
    # =====================================================================

    print()
    print("=" * 70)
    print("SECTION 3: Cross-Perspective Invariants & Disagreements")
    print("=" * 70)

    find_invariants_and_disagreements(G, seeds, perspective_results)

    # =====================================================================
    # SECTION 4: Actionable Recommendations
    # =====================================================================

    print()
    print("=" * 70)
    print("SECTION 4: Actionable Recommendations")
    print("=" * 70)

    generate_recommendations(G, perspective_results)

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Infrastructure: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    total_inferred = t1 + t2 + t3 + i1 + i2
    print(f"  Inferred edges (transitive + inverse): {total_inferred}")
    print("  Analysis performed from 4 operational perspectives:")
    print("    1. Classical (dependency traversal)")
    print("    2. Hypergraph (structural multi-hop risk)")
    print("    3. Probabilistic (compliance-weighted data flow)")
    print("    4. Quantum (operational impact breadth)")
    print("  Cross-perspective invariants identify highest-priority assets.")
    print("  Disagreement regions flag areas needing deeper investigation.")
    print("  Kolmogorov complexity (zlib) and spectral gap provide graph metrics.")
    print()


if __name__ == "__main__":
    main()
