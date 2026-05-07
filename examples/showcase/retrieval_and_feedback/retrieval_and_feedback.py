"""
Semantic Retrieval with Relevance Feedback in a Knowledge Base
==============================================================

This example builds a 150+ node cybersecurity / IT operations knowledge
base and demonstrates multi-signal retrieval: spreading activation for
associative recall, hash-based embedding similarity, Reciprocal Rank
Fusion (RRF) to merge both signals, and a learning-to-rank model that
improves after user relevance feedback.

The HashEmbeddingProvider used here is a deterministic placeholder. In
production you would inject a real provider (e.g. sentence-transformers)
via ``mem.set_embedding_provider(my_provider)`` for meaningful semantic
similarity.

Run with:
    .venv/bin/python examples/showcase/retrieval_and_feedback/03_retrieval_and_feedback.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory, Modality


def _build_kb(mem: HypergraphMemory) -> None:
    security_threats = [
        "sql_injection", "xss", "csrf", "rce", "privilege_escalation",
        "buffer_overflow", "mitm", "phishing", "ransomware", "rootkit",
        "keylogger", "ddos", "brute_force", "zero_day", "apt",
        "supply_chain_attack", "insider_threat", "data_exfiltration",
        "credential_stuffing", "session_hijacking",
    ]
    security_vulns = [
        "cve_2021_44228", "cve_2023_44487", "cve_2022_22965",
        "misconfig_s3_bucket", "weak_tls", "default_credentials",
        "unpatched_apache", "open_redirect", "ssrf", "xxe",
    ]
    security_controls = [
        "firewall", "ids", "ips", "waf", "siem", "edr", "xdr",
        "dlp", "iam", "mfa", "vpn", "encryption_at_rest",
        "encryption_in_transit", "network_segmentation", "zero_trust",
    ]
    security_tools = [
        "nmap", "burp_suite", "metasploit", "nessus", "snort",
        "suricata", "ossec", "yara", "volatility", "wireshark",
    ]
    security_protocols = [
        "tls_1_3", "oauth2", "saml", "openid_connect", "kerberos",
        "ipsec", "ssh", "pgp",
    ]
    security_frameworks = [
        "nist_csf", "iso_27001", "cis_controls", "mitre_attack",
        "owasp_top10", "soc2", "pci_dss", "gdpr",
    ]

    infra_servers = [
        "web_server_01", "web_server_02", "app_server_01", "app_server_02",
        "db_primary", "db_replica_01", "db_replica_02",
        "mail_server", "dns_server", "ntp_server",
        "bastion_host", "proxy_server", "api_gateway_node",
    ]
    infra_network = [
        "dmz_network", "internal_network", "management_network",
        "vpn_gateway", "core_switch", "edge_router", "load_balancer",
        "cdn_edge", "dns_resolver", "dhcp_server",
    ]
    infra_databases = [
        "postgres_cluster", "redis_cache", "elasticsearch_cluster",
        "kafka_broker", "mongodb_shard", "cassandra_ring",
    ]
    infra_cloud = [
        "aws_vpc", "aws_s3_data", "aws_iam_roles", "aws_cloudtrail",
        "azure_ad", "gcp_firewall", "kubernetes_cluster",
        "docker_registry", "terraform_state", "ansible_inventory",
    ]
    infra_monitoring = [
        "prometheus_server", "grafana_dashboard", "alertmanager",
        "pagerduty_integration", "slack_webhook", "log_aggregator",
        "jaeger_tracer", "elk_stack",
    ]

    incident_alerts = [
        "alert_brute_force", "alert_malware_detected", "alert_data_leak",
        "alert_ddos_spike", "alert_unauthorized_access",
        "alert_privilege_escalation", "alert_phishing_click",
        "alert_vulnerability_scan", "alert_config_drift",
        "alert_anomalous_traffic", "malware_detected_proxy",
    ]
    incident_logs = [
        "syslog", "windows_event_log", "apache_access_log",
        "cloudtrail_log", "flow_log", "dns_query_log",
        "auth_log", "firewall_log", "app_log", "audit_log",
    ]
    incident_response = [
        "isolate_host", "block_ip", "revoke_credentials", "patch_system",
        "forensic_capture", "notify_stakeholders", "restore_backup",
        "update_firewall_rules", "rotate_keys", "escalate_to_tier2",
    ]
    incident_severity = [
        "severity_critical", "severity_high", "severity_medium",
        "severity_low", "severity_info",
    ]

    org_teams = [
        "soc_team", "incident_response_team", "devops_team",
        "security_architecture", "compliance_team", "executive_board",
    ]
    org_assets = [
        "customer_pii", "financial_records", "source_code_repo",
        "production_database", "internal_wiki", "backup_vault",
    ]
    org_policies = [
        "password_policy", "access_control_policy", "data_retention_policy",
        "incident_response_plan", "disaster_recovery_plan",
        "acceptable_use_policy",
    ]
    org_compliance = [
        "soc2_audit", "pci_assessment", "gdpr_review",
        "hipaa_compliance", "sox_controls",
    ]

    def _store_group(labels: list[str], type_name: str, category: str, kw: list[str]) -> None:
        for label in labels:
            mem.add(label, data={"type": type_name, "category": category, "keywords": kw})

    _store_group(security_threats, "threat", "security", ["attack", "exploit", "adversary"])
    _store_group(security_vulns, "vulnerability", "security", ["cve", "flaw", "weakness"])
    _store_group(security_controls, "control", "security", ["defense", "mitigation", "prevention"])
    _store_group(security_tools, "tool", "security", ["scanner", "detector", "forensics"])
    _store_group(security_protocols, "protocol", "security", ["authentication", "encryption", "standard"])
    _store_group(security_frameworks, "framework", "security", ["compliance", "governance", "standard"])
    _store_group(infra_servers, "server", "infrastructure", ["host", "compute", "service"])
    _store_group(infra_network, "network", "infrastructure", ["routing", "switching", "connectivity"])
    _store_group(infra_databases, "database", "infrastructure", ["storage", "persistence", "query"])
    _store_group(infra_cloud, "cloud_resource", "infrastructure", ["aws", "azure", "gcp", "iac"])
    _store_group(infra_monitoring, "monitoring", "infrastructure", ["observability", "metrics", "alerting"])
    _store_group(incident_alerts, "alert", "incident", ["detection", "signal", "notification"])
    _store_group(incident_logs, "log_source", "incident", ["telemetry", "evidence", "audit"])
    _store_group(incident_response, "response_action", "incident", ["remediation", "containment", "recovery"])
    _store_group(incident_severity, "severity_level", "incident", ["priority", "urgency", "classification"])
    _store_group(org_teams, "team", "organization", ["people", "responsibility", "escalation"])
    _store_group(org_assets, "asset", "organization", ["data", "crown_jewel", "protection"])
    _store_group(org_policies, "policy", "organization", ["governance", "rule", "requirement"])
    _store_group(org_compliance, "compliance", "organization", ["audit", "regulation", "attestation"])

    edges: list[tuple[str, str, str]] = []

    def _add(src: str, tgt: str, label: str, bidir: bool = False) -> None:
        edges.append((src, tgt, label))
        if bidir:
            edges.append((tgt, src, label))

    _add("sql_injection", "waf", "mitigated_by")
    _add("xss", "waf", "mitigated_by")
    _add("csrf", "waf", "mitigated_by")
    _add("rce", "edr", "mitigated_by")
    _add("rce", "ips", "mitigated_by")
    _add("privilege_escalation", "iam", "mitigated_by")
    _add("privilege_escalation", "mfa", "mitigated_by")
    _add("buffer_overflow", "edr", "mitigated_by")
    _add("mitm", "tls_1_3", "mitigated_by")
    _add("mitm", "vpn", "mitigated_by")
    _add("phishing", "mfa", "mitigated_by")
    _add("ransomware", "dlp", "mitigated_by")
    _add("ransomware", "encryption_at_rest", "mitigated_by")
    _add("rootkit", "edr", "mitigated_by")
    _add("ddos", "ips", "mitigated_by")
    _add("ddos", "cdn_edge", "mitigated_by")
    _add("brute_force", "mfa", "mitigated_by")
    _add("brute_force", "ids", "detected_by")
    _add("zero_day", "edr", "detected_by")
    _add("apt", "siem", "detected_by")
    _add("supply_chain_attack", "siem", "detected_by")
    _add("insider_threat", "dlp", "detected_by")
    _add("data_exfiltration", "dlp", "detected_by")
    _add("credential_stuffing", "mfa", "mitigated_by")
    _add("credential_stuffing", "ids", "detected_by")
    _add("session_hijacking", "tls_1_3", "mitigated_by")
    _add("keylogger", "edr", "detected_by")

    _add("sql_injection", "owasp_top10", "part_of")
    _add("xss", "owasp_top10", "part_of")
    _add("csrf", "owasp_top10", "part_of")
    _add("ssrf", "owasp_top10", "part_of")
    _add("xxe", "owasp_top10", "part_of")

    _add("cve_2021_44228", "rce", "enables")
    _add("cve_2023_44487", "ddos", "enables")
    _add("cve_2022_22965", "privilege_escalation", "enables")
    _add("misconfig_s3_bucket", "data_exfiltration", "enables")
    _add("weak_tls", "mitm", "enables")
    _add("default_credentials", "brute_force", "enables")
    _add("unpatched_apache", "rce", "enables")
    _add("open_redirect", "phishing", "enables")
    _add("ssrf", "data_exfiltration", "enables")
    _add("xxe", "data_exfiltration", "enables")

    _add("nist_csf", "cis_controls", "related_to", bidir=True)
    _add("nist_csf", "iso_27001", "related_to", bidir=True)
    _add("iso_27001", "soc2", "related_to", bidir=True)
    _add("pci_dss", "pci_assessment", "depends_on")
    _add("gdpr", "gdpr_review", "depends_on")
    _add("soc2", "soc2_audit", "depends_on")
    _add("nist_csf", "incident_response_plan", "requires")
    _add("nist_csf", "access_control_policy", "requires")
    _add("pci_dss", "encryption_at_rest", "requires")
    _add("pci_dss", "encryption_in_transit", "requires")
    _add("gdpr", "data_retention_policy", "requires")
    _add("gdpr", "dlp", "requires")
    _add("mitre_attack", "siem", "uses")
    _add("mitre_attack", "edr", "uses")
    _add("mitre_attack", "soc_team", "used_by")

    _add("nmap", "unpatched_apache", "detects")
    _add("nessus", "weak_tls", "detects")
    _add("nessus", "default_credentials", "detects")
    _add("burp_suite", "sql_injection", "detects")
    _add("burp_suite", "xss", "detects")
    _add("metasploit", "rce", "tests")
    _add("wireshark", "mitm", "detects")
    _add("yara", "ransomware", "detects")
    _add("yara", "rootkit", "detects")
    _add("volatility", "rootkit", "detects")
    _add("snort", "ddos", "detects")
    _add("snort", "brute_force", "detects")
    _add("suricata", "apt", "detects")
    _add("ossec", "privilege_escalation", "detects")

    _add("web_server_01", "dmz_network", "part_of")
    _add("web_server_02", "dmz_network", "part_of")
    _add("app_server_01", "internal_network", "part_of")
    _add("app_server_02", "internal_network", "part_of")
    _add("db_primary", "management_network", "part_of")
    _add("db_replica_01", "management_network", "part_of")
    _add("db_replica_02", "management_network", "part_of")
    _add("bastion_host", "dmz_network", "part_of")
    _add("proxy_server", "dmz_network", "part_of")
    _add("dns_server", "dmz_network", "part_of")
    _add("mail_server", "dmz_network", "part_of")

    _add("load_balancer", "web_server_01", "routes_to")
    _add("load_balancer", "web_server_02", "routes_to")
    _add("web_server_01", "app_server_01", "depends_on")
    _add("web_server_02", "app_server_02", "depends_on")
    _add("app_server_01", "db_primary", "depends_on")
    _add("app_server_02", "db_primary", "depends_on")
    _add("app_server_01", "redis_cache", "depends_on")
    _add("app_server_02", "redis_cache", "depends_on")
    _add("api_gateway_node", "app_server_01", "routes_to")
    _add("api_gateway_node", "app_server_02", "routes_to")
    _add("edge_router", "load_balancer", "routes_to")
    _add("edge_router", "cdn_edge", "routes_to")
    _add("vpn_gateway", "bastion_host", "routes_to")
    _add("bastion_host", "management_network", "enables")
    _add("core_switch", "dmz_network", "connects")
    _add("core_switch", "internal_network", "connects")
    _add("core_switch", "management_network", "connects")

    _add("postgres_cluster", "db_primary", "includes")
    _add("postgres_cluster", "db_replica_01", "includes")
    _add("postgres_cluster", "db_replica_02", "includes")
    _add("elasticsearch_cluster", "log_aggregator", "depends_on")
    _add("kafka_broker", "app_server_01", "depends_on")
    _add("kafka_broker", "app_server_02", "depends_on")
    _add("mongodb_shard", "app_server_01", "depends_on")

    _add("aws_vpc", "internal_network", "maps_to")
    _add("aws_s3_data", "backup_vault", "stores")
    _add("aws_iam_roles", "iam", "implements")
    _add("aws_cloudtrail", "cloudtrail_log", "produces")
    _add("kubernetes_cluster", "app_server_01", "hosts")
    _add("kubernetes_cluster", "app_server_02", "hosts")
    _add("docker_registry", "kubernetes_cluster", "depends_on")
    _add("terraform_state", "aws_vpc", "manages")
    _add("terraform_state", "aws_iam_roles", "manages")
    _add("ansible_inventory", "web_server_01", "manages")
    _add("ansible_inventory", "web_server_02", "manages")
    _add("azure_ad", "oauth2", "implements")
    _add("azure_ad", "mfa", "implements")
    _add("gcp_firewall", "firewall", "implements")

    _add("prometheus_server", "app_server_01", "monitors")
    _add("prometheus_server", "app_server_02", "monitors")
    _add("prometheus_server", "db_primary", "monitors")
    _add("prometheus_server", "redis_cache", "monitors")
    _add("prometheus_server", "kafka_broker", "monitors")
    _add("grafana_dashboard", "prometheus_server", "depends_on")
    _add("grafana_dashboard", "elasticsearch_cluster", "depends_on")
    _add("alertmanager", "prometheus_server", "depends_on")
    _add("alertmanager", "pagerduty_integration", "notifies")
    _add("pagerduty_integration", "slack_webhook", "notifies")
    _add("log_aggregator", "syslog", "collects")
    _add("log_aggregator", "apache_access_log", "collects")
    _add("log_aggregator", "auth_log", "collects")
    _add("log_aggregator", "cloudtrail_log", "collects")
    _add("log_aggregator", "flow_log", "collects")
    _add("elk_stack", "elasticsearch_cluster", "includes")
    _add("elk_stack", "log_aggregator", "includes")
    _add("elk_stack", "grafana_dashboard", "includes")
    _add("jaeger_tracer", "app_server_01", "monitors")
    _add("jaeger_tracer", "app_server_02", "monitors")

    _add("siem", "log_aggregator", "depends_on")
    _add("siem", "elk_stack", "depends_on")
    _add("siem", "alert_brute_force", "produces")
    _add("siem", "alert_malware_detected", "produces")
    _add("siem", "alert_data_leak", "produces")
    _add("siem", "alert_ddos_spike", "produces")
    _add("siem", "alert_unauthorized_access", "produces")
    _add("edr", "alert_malware_detected", "produces")
    _add("edr", "alert_privilege_escalation", "produces")
    _add("ids", "alert_anomalous_traffic", "produces")
    _add("ids", "alert_brute_force", "produces")
    _add("ips", "alert_ddos_spike", "produces")
    _add("waf", "alert_vulnerability_scan", "produces")
    _add("dlp", "alert_data_leak", "produces")
    _add("prometheus_server", "alert_config_drift", "produces")

    _add("alert_brute_force", "severity_high", "classified_as")
    _add("alert_malware_detected", "severity_critical", "classified_as")
    _add("alert_data_leak", "severity_critical", "classified_as")
    _add("alert_ddos_spike", "severity_high", "classified_as")
    _add("alert_unauthorized_access", "severity_critical", "classified_as")
    _add("alert_privilege_escalation", "severity_critical", "classified_as")
    _add("alert_phishing_click", "severity_medium", "classified_as")
    _add("alert_vulnerability_scan", "severity_low", "classified_as")
    _add("alert_config_drift", "severity_info", "classified_as")
    _add("alert_anomalous_traffic", "severity_medium", "classified_as")

    _add("alert_malware_detected", "isolate_host", "triggers")
    _add("alert_ddos_spike", "block_ip", "triggers")
    _add("alert_unauthorized_access", "revoke_credentials", "triggers")
    _add("alert_privilege_escalation", "revoke_credentials", "triggers")
    _add("alert_data_leak", "forensic_capture", "triggers")
    _add("alert_brute_force", "update_firewall_rules", "triggers")
    _add("alert_phishing_click", "revoke_credentials", "triggers")
    _add("alert_vulnerability_scan", "patch_system", "triggers")
    _add("alert_config_drift", "patch_system", "triggers")
    _add("alert_anomalous_traffic", "escalate_to_tier2", "triggers")

    _add("isolate_host", "edr", "executed_by")
    _add("block_ip", "firewall", "executed_by")
    _add("revoke_credentials", "iam", "executed_by")
    _add("patch_system", "ansible_inventory", "executed_by")
    _add("forensic_capture", "volatility", "executed_by")
    _add("update_firewall_rules", "firewall", "executed_by")
    _add("rotate_keys", "aws_iam_roles", "executed_by")
    _add("notify_stakeholders", "slack_webhook", "uses")
    _add("restore_backup", "aws_s3_data", "uses")
    _add("escalate_to_tier2", "soc_team", "assigned_to")

    _add("incident_response_team", "isolate_host", "responsible_for")
    _add("incident_response_team", "forensic_capture", "responsible_for")
    _add("incident_response_team", "block_ip", "responsible_for")
    _add("soc_team", "alert_brute_force", "triages")
    _add("soc_team", "alert_phishing_click", "triages")
    _add("soc_team", "alert_anomalous_traffic", "triages")
    _add("devops_team", "patch_system", "responsible_for")
    _add("devops_team", "restore_backup", "responsible_for")
    _add("compliance_team", "soc2_audit", "responsible_for")
    _add("compliance_team", "pci_assessment", "responsible_for")
    _add("compliance_team", "gdpr_review", "responsible_for")
    _add("executive_board", "disaster_recovery_plan", "approves")

    _add("customer_pii", "gdpr", "protected_by")
    _add("customer_pii", "encryption_at_rest", "protected_by")
    _add("financial_records", "pci_dss", "protected_by")
    _add("source_code_repo", "supply_chain_attack", "vulnerable_to")
    _add("production_database", "db_primary", "stored_on")
    _add("internal_wiki", "phishing", "vulnerable_to")
    _add("backup_vault", "ransomware", "vulnerable_to")
    _add("backup_vault", "encryption_at_rest", "protected_by")

    _add("severity_critical", "incident_response_plan", "activates")
    _add("severity_high", "incident_response_plan", "activates")
    _add("severity_critical", "notify_stakeholders", "triggers")
    _add("severity_critical", "escalate_to_tier2", "triggers")

    _add("password_policy", "mfa", "enforces")
    _add("password_policy", "default_credentials", "prevents")
    _add("access_control_policy", "iam", "enforces")
    _add("access_control_policy", "zero_trust", "enforces")
    _add("data_retention_policy", "data_exfiltration", "prevents")
    _add("acceptable_use_policy", "insider_threat", "prevents")
    _add("disaster_recovery_plan", "restore_backup", "defines")

    _add("oauth2", "openid_connect", "related_to", bidir=True)
    _add("saml", "openid_connect", "related_to", bidir=True)
    _add("oauth2", "api_gateway_node", "used_by")
    _add("kerberos", "bastion_host", "used_by")
    _add("ssh", "bastion_host", "used_by")
    _add("ipsec", "vpn_gateway", "used_by")
    _add("pgp", "encryption_in_transit", "enables")

    _add("network_segmentation", "dmz_network", "implements")
    _add("network_segmentation", "internal_network", "implements")
    _add("network_segmentation", "management_network", "implements")
    _add("zero_trust", "network_segmentation", "requires")
    _add("zero_trust", "mfa", "requires")
    _add("zero_trust", "iam", "requires")

    _add("brute_force", "auth_log", "logged_in")
    _add("ddos", "flow_log", "logged_in")
    _add("phishing", "apache_access_log", "logged_in")
    _add("privilege_escalation", "audit_log", "logged_in")
    _add("malware_detected_proxy", "syslog", "logged_in")
    _add("dns_server", "dns_query_log", "produces")
    _add("firewall", "firewall_log", "produces")
    _add("app_server_01", "app_log", "produces")
    _add("app_server_02", "app_log", "produces")

    for label, parent in [
        ("firewall", "network_segmentation"),
        ("ids", "ips"),
        ("edr", "xdr"),
        ("waf", "ips"),
    ]:
        _add(label, parent, "subclass_of")

    for alert, sev in [
        ("severity_critical", "severity_high"),
        ("severity_high", "severity_medium"),
        ("severity_medium", "severity_low"),
        ("severity_low", "severity_info"),
    ]:
        _add(sev, alert, "subclass_of")

    for src, tgt, label in edges:
        mem.link(src, tgt, label=label)


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Knowledge Base Construction
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Knowledge Base Construction")
    print("=" * 70)

    _build_kb(mem)
    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")

    categories: dict[str, int] = {}
    for node in mem.graph.nodes:
        cat = node.data.get("category", "unknown") if isinstance(node.data, dict) else "unknown"
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count} nodes")
    print()

    # =====================================================================
    # SECTION 2: Spreading Activation Retrieval
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Spreading Activation from 'ransomware'")
    print("=" * 70)

    activated = mem.activate("ransomware", energy=1.0, top_k=15, iterations=3)
    print(f"  {'Label':30s} {'Activation':>10s} {'Depth':>5s}")
    print(f"  {'-'*30} {'-'*10} {'-'*5}")
    for r in activated:
        print(f"  {r.label:30s} {r.activation:10.4f} {r.depth:5d}")
    print()

    # =====================================================================
    # SECTION 3: Embedding Similarity (HashEmbeddingProvider)
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Embedding Similarity from 'ransomware'")
    print("=" * 70)
    print("  (HashEmbeddingProvider is a deterministic placeholder)")

    similar = mem.search.similar("ransomware", top_k=15, threshold=-1.0)
    print(f"  {'Label':30s} {'Cosine':>8s} {'Euclid':>8s}")
    print(f"  {'-'*30} {'-'*8} {'-'*8}")
    for s in similar:
        print(f"  {s.label_b:30s} {s.similarity:8.4f} {s.embedding_distance:8.4f}")
    print()

    # =====================================================================
    # SECTION 4: Reciprocal Rank Fusion
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: RRF-Retrieved Concepts for 'ransomware'")
    print("=" * 70)

    rrf_results = mem.retrieve("ransomware", top_k=15, iterations=3)
    print(f"  {'Label':30s} {'RRF':>7s} {'Act':>7s} {'Sim':>7s} {'A#':>4s} {'S#':>4s}")
    print(f"  {'-'*30} {'-'*7} {'-'*7} {'-'*7} {'-'*4} {'-'*4}")
    for r in rrf_results:
        print(f"  {r.label:30s} {r.rrf_score:7.4f} {r.activation:7.4f} "
              f"{r.similarity:7.4f} {r.activation_rank:4d} {r.similarity_rank:4d}")
    print()

    # =====================================================================
    # SECTION 5: Relevance Feedback
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: Recording Relevance Feedback")
    print("=" * 70)

    feedback_queries: list[tuple[str, list, set]] = []

    relevant_ransomware = {
        "encryption_at_rest", "dlp", "edr", "backup_vault", "isolate_host",
        "siem", "yara", "alert_malware_detected", "severity_critical",
    }
    feedback_queries.append(("ransomware", rrf_results, relevant_ransomware))
    n1 = mem.record_feedback("ransomware", rrf_results, relevant_ransomware)
    print(f"  Query 'ransomware': {n1} judgments, {len(relevant_ransomware)} relevant")

    rrf_phishing = mem.retrieve("phishing", top_k=15, iterations=3)
    relevant_phishing = {
        "mfa", "waf", "ids", "alert_phishing_click", "severity_medium",
        "revoke_credentials", "soc_team", "open_redirect", "burp_suite",
    }
    feedback_queries.append(("phishing", rrf_phishing, relevant_phishing))
    n2 = mem.record_feedback("phishing", rrf_phishing, relevant_phishing)
    print(f"  Query 'phishing':   {n2} judgments, {len(relevant_phishing)} relevant")

    rrf_ddos = mem.retrieve("ddos", top_k=15, iterations=3)
    relevant_ddos = {
        "ips", "cdn_edge", "load_balancer", "alert_ddos_spike",
        "block_ip", "severity_high", "firewall", "suricata", "snort",
    }
    feedback_queries.append(("ddos", rrf_ddos, relevant_ddos))
    n3 = mem.record_feedback("ddos", rrf_ddos, relevant_ddos)
    print(f"  Query 'ddos':       {n3} judgments, {len(relevant_ddos)} relevant")

    rrf_zero_day = mem.retrieve("zero_day", top_k=15, iterations=3)
    relevant_zero_day = {
        "edr", "xdr", "siem", "mitre_attack", "alert_privilege_escalation",
        "severity_critical", "patch_system", "nmap", "nessus",
    }
    feedback_queries.append(("zero_day", rrf_zero_day, relevant_zero_day))
    n4 = mem.record_feedback("zero_day", rrf_zero_day, relevant_zero_day)
    print(f"  Query 'zero_day':   {n4} judgments, {len(relevant_zero_day)} relevant")
    print(f"  Total feedback records: {mem.feedback.size}")
    print()

    # =====================================================================
    # SECTION 6: Training the Learning-to-Rank Model
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: Training Learning-to-Rank Model")
    print("=" * 70)

    report = mem.train_retriever()
    print(f"  Trained: {report.get('trained', False)}")
    print(f"  Samples: {report.get('samples', 0)}")
    if "weights" in report:
        print("  Learned feature weights:")
        for feat, weight in sorted(report["weights"].items()):
            print(f"    {feat:20s} {weight:+.4f}")
    print()

    # =====================================================================
    # SECTION 7: Improved Retrieval After Training
    # =====================================================================

    print("=" * 70)
    print("SECTION 7: Retrieval Comparison (Before vs After LTR)")
    print("=" * 70)

    queries = ["ransomware", "phishing", "ddos", "zero_day"]
    for query in queries:
        before = mem.retrieve(query, top_k=15, iterations=3, use_ltr=False)
        after = mem.retrieve(query, top_k=15, iterations=3, use_ltr=True)

        before_labels = [r.label for r in before]
        after_labels = [r.label for r in after]

        before_relevant = feedback_queries[queries.index(query)][2]
        before_hits = sum(1 for l in before_labels[:5] if l in before_relevant)
        after_hits = sum(1 for l in after_labels[:5] if l in before_relevant)

        promoted = [l for l in after_labels[:5] if l not in before_labels[:5]]
        demoted = [l for l in before_labels[:5] if l not in after_labels[:5]]

        print(f"  Query: {query}")
        print(f"    Top-5 relevant hits:  RRF={before_hits}/5  LTR={after_hits}/5")
        if promoted:
            print(f"    Promoted into top-5:  {promoted}")
        if demoted:
            print(f"    Demoted from top-5:   {demoted}")
        print()

    # =====================================================================
    # SECTION 8: Signal Comparison Across Query Types
    # =====================================================================

    print("=" * 70)
    print("SECTION 8: Activation vs Embedding by Query Type")
    print("=" * 70)

    comparison_queries = [
        ("ransomware", "threat-focused"),
        ("db_primary", "infrastructure-focused"),
        ("severity_critical", "classification-focused"),
        ("soc_team", "organizational-focused"),
        ("oauth2", "protocol-focused"),
    ]

    for query, description in comparison_queries:
        act = mem.activate(query, energy=1.0, top_k=5, iterations=3)
        sim = mem.search.similar(query, top_k=5, threshold=-1.0)
        act_labels = [r.label for r in act]
        sim_labels = [s.label_b for s in sim]
        overlap = set(act_labels) & set(sim_labels)

        print(f"  {query} ({description}):")
        print(f"    Activation top-5: {act_labels}")
        print(f"    Similarity top-5: {sim_labels}")
        print(f"    Overlap: {len(overlap)}/5  {sorted(overlap) if overlap else '(none)'}")
        print()

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Graph:     {stats.nodes} nodes, {stats.edges} edges")
    print(f"  Events:    {stats.log_size}")
    print(f"  Feedback:  {mem.feedback.size} judgments across {len(queries)} queries")
    print(f"  LTR model: trained with {report.get('samples', 0)} samples")
    print(f"  Key takeaway: RRF fuses graph topology (activation) with")
    print(f"  embedding similarity. Relevance feedback teaches the system")
    print(f"  which signal matters more for each type of query.")
    print()


if __name__ == "__main__":
    main()
