"""
Multi-Perspective Risk Assessment
==================================

Analyzes an enterprise infrastructure graph from four operational
perspectives (dependency, risk propagation, compliance, operational
impact) using Hyper3's multi-frame reasoning. Finds cross-perspective
invariants (assets to protect first) and disagreement regions (areas
needing further analysis).

Run with:
    .venv/bin/python examples/advanced/09_iterative_frame_reasoning.py
"""

from __future__ import annotations

from collections import defaultdict

from hyper3 import (
    HypergraphMemory,
    RobustReachabilityDetector,
    Modality,
    TransitiveRule,
    InverseRule,
)


def build_infrastructure(mem: HypergraphMemory) -> set[str]:
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
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

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
        mem.relate(src, tgt, label=label)

    return set(all_entities.keys())


def _traverse(
    mem: HypergraphMemory,
    seed_labels: set[str],
    *,
    max_depth: int = 4,
    edge_filter: set[str] | None = None,
    node_filter=None,
    weight_threshold: float = 0.0,
) -> set[str]:
    seed_ids = set()
    for label in seed_labels:
        node = mem.graph.get_node_by_label(label)
        if node:
            seed_ids.add(node.id)

    reachable: set[str] = set()
    frontier = list(seed_ids)
    visited = set(seed_ids)

    for _ in range(max_depth):
        next_frontier = []
        for nid in frontier:
            for edge in mem.graph.incident_edges(nid):
                if edge.weight < weight_threshold:
                    continue
                if edge_filter and edge.label not in edge_filter:
                    continue
                for tgt in edge.target_ids:
                    if node_filter and not node_filter(mem, tgt):
                        reachable.add(tgt)
                        continue
                    if tgt not in visited:
                        visited.add(tgt)
                        next_frontier.append(tgt)
                    reachable.add(tgt)
        frontier = next_frontier

    return reachable


def _is_sensitive_node(mem: HypergraphMemory, nid: str) -> bool:
    node = mem.graph.get_node(nid)
    if not node or not isinstance(node.data, dict):
        return True
    classification = node.data.get("data_classification", "internal")
    return classification in ("confidential", "restricted")


def analyze_perspective(
    mem: HypergraphMemory,
    seed_labels: set[str],
    frame_name: str,
    perspective_label: str,
) -> dict:
    print(f"\n  --- {perspective_label} ({frame_name} frame) ---")

    result = mem.reason_with_frame(seed_labels, frame_name=frame_name)
    expansion = result.get("expansion", {})
    frame_config = result.get("frame_config", {})
    print(f"    Expansion: {expansion.get('edges_produced', 0)} edges, "
          f"{expansion.get('states_created', 0)} states, "
          f"{expansion.get('rules_applied', 0)} rule applications")
    print(f"    Algorithm: {frame_config.get('algorithm', 'N/A')}, "
          f"info_loss: {frame_config.get('information_loss', 0):.3f}")

    if frame_name == "classical":
        reachable = _traverse(mem, seed_labels, max_depth=4)
    elif frame_name == "hypergraph":
        reachable = _traverse(
            mem, seed_labels, max_depth=5,
            edge_filter={"depends_on", "routes_to", "indirect_depends_on",
                         "indirect_routes_to", "accesses", "stores"},
        )
    elif frame_name == "probabilistic":
        reachable = _traverse(
            mem, seed_labels, max_depth=3,
            edge_filter={"accesses", "stores", "processes", "depends_on",
                         "contains", "protects"},
            node_filter=_is_sensitive_node,
        )
    elif frame_name == "quantum":
        reachable = _traverse(
            mem, seed_labels, max_depth=6,
            edge_filter={"depends_on", "routes_to", "indirect_depends_on",
                         "indirect_routes_to"},
        )
    else:
        reachable = _traverse(mem, seed_labels, max_depth=4)

    centrality = mem.degree_centrality()

    reachability_scores: dict[str, float] = {}
    for nid in reachable:
        node = mem.graph.get_node(nid)
        if node and node.label in centrality:
            data = node.data if isinstance(node.data, dict) else {}
            crit = data.get("criticality", 5)
            reachability_scores[node.label] = centrality[node.label] * crit

    sorted_assets = sorted(reachability_scores.items(), key=lambda x: x[1], reverse=True)

    reachable_labels = set()
    for nid in reachable:
        node = mem.graph.get_node(nid)
        if node:
            reachable_labels.add(node.label)

    print(f"    Reachable nodes: {len(reachable_labels)}")
    print(f"    Top critical assets from this perspective:")
    for label, score in sorted_assets[:6]:
        node = mem.graph.get_node_by_label(label)
        dtype = node.data.get("type", "?") if isinstance(node.data, dict) else "?"
        print(f"      {label:25s}  score={score:.3f}  type={dtype}")

    return {
        "reachable_labels": reachable_labels,
        "sorted_assets": sorted_assets,
        "expansion": expansion,
        "frame_config": frame_config,
    }


def find_invariants_and_disagreements(
    mem: HypergraphMemory,
    seed_labels: set[str],
    perspective_results: dict[str, dict],
) -> None:
    print("\n  --- Cross-Perspective Invariants ---")

    seed_ids = set()
    for label in seed_labels:
        node = mem.graph.get_node_by_label(label)
        if node:
            seed_ids.add(node.id)

    detector = RobustReachabilityDetector(mem.perspective)
    inv = detector.find_invariants(list(seed_ids), mem.graph)

    inv_labels = set()
    for nid in inv.invariant_nodes:
        node = mem.graph.get_node(nid)
        if node:
            inv_labels.add(node.label)

    print(f"    Invariant nodes (reachable from ALL built-in frames): {len(inv_labels)}")
    print(f"    Invariant confidence: {inv.confidence:.3f}")
    if inv.frame_unique:
        print(f"    Per-frame unique nodes:")
        for fname, unique_ids in inv.frame_unique.items():
            unique_labels = set()
            for uid in unique_ids:
                n = mem.graph.get_node(uid)
                if n:
                    unique_labels.add(n.label)
            print(f"      {fname:15s}: {len(unique_labels)} unique")
            for ul in sorted(unique_labels)[:4]:
                print(f"        - {ul}")

    invariant_assets = []
    for label in inv_labels:
        node = mem.graph.get_node_by_label(label)
        if node and isinstance(node.data, dict):
            crit = node.data.get("criticality", 0)
            dtype = node.data.get("type", "?")
            invariant_assets.append((label, crit, dtype))

    invariant_assets.sort(key=lambda x: x[1], reverse=True)

    print(f"\n    Top invariant assets (protect these first):")
    for label, crit, dtype in invariant_assets[:10]:
        print(f"      {label:25s}  criticality={crit}  type={dtype}")

    print("\n  --- Disagreement Regions (Perspective Analysis) ---")
    all_reachable: dict[str, set[str]] = {}
    for pname, res in perspective_results.items():
        all_reachable[pname] = res["reachable_labels"]

    if not all_reachable:
        return

    union_all = set.union(*all_reachable.values())
    intersection_all = set.intersection(*all_reachable.values()) if len(all_reachable) > 1 else union_all
    disagreeing = union_all - intersection_all

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
        node = mem.graph.get_node_by_label(label)
        dtype = node.data.get("type", "?") if node and isinstance(node.data, dict) else "?"
        print(f"      {label:25s}  type={dtype}  "
              f"seen_by={agreeing}  missed_by={disagreeing_frames}")


def generate_recommendations(
    mem: HypergraphMemory,
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
        node = mem.graph.get_node_by_label(label)
        data = node.data if node and isinstance(node.data, dict) else {}
        print(f"      - Prioritize hardening: {label} "
              f"(criticality={data.get('criticality', '?')}, "
              f"exposure={data.get('exposure', '?')})")

    secondary = (mostly_critical - universal_critical)
    if secondary:
        print(f"\n    Critical in 2 perspectives ({len(secondary)} assets):")
        for label in sorted(secondary):
            node = mem.graph.get_node_by_label(label)
            data = node.data if node and isinstance(node.data, dict) else {}
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
    for label in mem.query_nodes(type="service"):
        node = mem.graph.get_node_by_label(label)
        if not node or not isinstance(node.data, dict):
            continue
        crit = node.data.get("criticality", 0)
        exposure = node.data.get("exposure", "internal")
        if crit >= 9:
            dep_count = len(mem.neighbors(label, edge_label="depends_on", direction="in"))
            high_crit.append((label, crit, exposure, dep_count))

    if high_crit:
        high_crit.sort(key=lambda x: x[3], reverse=True)
        print(f"\n    High-criticality dependency hubs (single points of failure):")
        for label, crit, exposure, dep_count in high_crit:
            print(f"      - {label}: criticality={crit}, "
                  f"exposure={exposure}, depended_on_by={dep_count}")


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Infrastructure Graph Construction
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Infrastructure Graph Construction")
    print("=" * 70)

    all_labels = build_infrastructure(mem)
    print(f"  Nodes: {mem.graph.node_count}")
    print(f"  Edges: {mem.graph.edge_count}")

    mem.add_rules(
        TransitiveRule(edge_label="depends_on", new_label="indirect_depends_on"),
        TransitiveRule(edge_label="routes_to", new_label="indirect_routes_to"),
        TransitiveRule(edge_label="accesses", new_label="indirect_accesses"),
        InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
        InverseRule(edge_label="contains", inverse_label="contained_in"),
    )

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
            mem, seeds, frame, label,
        )

    # =====================================================================
    # SECTION 3: Cross-Perspective Invariants and Disagreements
    # =====================================================================

    print()
    print("=" * 70)
    print("SECTION 3: Cross-Perspective Invariants & Disagreements")
    print("=" * 70)

    find_invariants_and_disagreements(mem, seeds, perspective_results)

    # =====================================================================
    # SECTION 4: Actionable Recommendations
    # =====================================================================

    print()
    print("=" * 70)
    print("SECTION 4: Actionable Recommendations")
    print("=" * 70)

    generate_recommendations(mem, perspective_results)

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Infrastructure: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    total_new = sum(
        r["expansion"].get("edges_produced", 0)
        for r in perspective_results.values()
    )
    print(f"  Inferred edges across all perspectives: {total_new}")
    print("  Analysis performed from 4 operational perspectives:")
    print("    1. Classical (dependency traversal)")
    print("    2. Hypergraph (structural multi-hop risk)")
    print("    3. Probabilistic (compliance-weighted data flow)")
    print("    4. Quantum (operational impact breadth)")
    print("  Cross-perspective invariants identify highest-priority assets.")
    print("  Disagreement regions flag areas needing deeper investigation.")
    print()


if __name__ == "__main__":
    main()
