"""
Network Attack Surface Analysis
================================

Build a realistic 120+ node enterprise network topology and analyze it for
security risks using graph analytics: degree centrality (exposure),
betweenness centrality (chokepoints), connected components (segmentation
violations), cycle detection (circular trust), and composite risk scoring.

Run with:
    .venv/bin/python examples/showcase/core/network_analytics/06_graph_analytics.py
"""

from __future__ import annotations

from collections import defaultdict

from hyper3 import HypergraphMemory, Modality, TransitiveRule, top_k


def build_hosts(mem: HypergraphMemory) -> list[str]:
    specs = [
        ("web-01", {"os": "linux", "zone": "dmz", "criticality": 9, "patch_level": 0.8}),
        ("web-02", {"os": "linux", "zone": "dmz", "criticality": 9, "patch_level": 0.7}),
        ("web-03", {"os": "linux", "zone": "dmz", "criticality": 8, "patch_level": 0.9}),
        ("web-04", {"os": "windows", "zone": "dmz", "criticality": 7, "patch_level": 0.5}),
        ("app-01", {"os": "linux", "zone": "internal", "criticality": 8, "patch_level": 0.85}),
        ("app-02", {"os": "linux", "zone": "internal", "criticality": 8, "patch_level": 0.9}),
        ("app-03", {"os": "linux", "zone": "internal", "criticality": 7, "patch_level": 0.75}),
        ("app-04", {"os": "windows", "zone": "internal", "criticality": 7, "patch_level": 0.6}),
        ("db-primary", {"os": "linux", "zone": "restricted", "criticality": 10, "patch_level": 0.95}),
        ("db-replica", {"os": "linux", "zone": "restricted", "criticality": 9, "patch_level": 0.95}),
        ("db-analytics", {"os": "linux", "zone": "restricted", "criticality": 8, "patch_level": 0.85}),
        ("ws-finance-01", {"os": "windows", "zone": "internal", "criticality": 6, "patch_level": 0.4}),
        ("ws-finance-02", {"os": "windows", "zone": "internal", "criticality": 6, "patch_level": 0.5}),
        ("ws-finance-03", {"os": "windows", "zone": "internal", "criticality": 5, "patch_level": 0.3}),
        ("ws-engineering-01", {"os": "linux", "zone": "internal", "criticality": 5, "patch_level": 0.7}),
        ("ws-engineering-02", {"os": "linux", "zone": "internal", "criticality": 5, "patch_level": 0.8}),
        ("ws-engineering-03", {"os": "macos", "zone": "internal", "criticality": 4, "patch_level": 0.75}),
        ("ws-hr-01", {"os": "windows", "zone": "internal", "criticality": 6, "patch_level": 0.45}),
        ("ws-hr-02", {"os": "windows", "zone": "internal", "criticality": 5, "patch_level": 0.5}),
        ("ws-exec-01", {"os": "macos", "zone": "restricted", "criticality": 8, "patch_level": 0.9}),
        ("ws-exec-02", {"os": "macos", "zone": "restricted", "criticality": 7, "patch_level": 0.85}),
        ("admin-bastion", {"os": "linux", "zone": "restricted", "criticality": 10, "patch_level": 0.98}),
        ("admin-jump-01", {"os": "linux", "zone": "internal", "criticality": 9, "patch_level": 0.92}),
        ("mail-server", {"os": "linux", "zone": "dmz", "criticality": 7, "patch_level": 0.7}),
        ("dns-server", {"os": "linux", "zone": "dmz", "criticality": 8, "patch_level": 0.85}),
        ("vpn-gateway", {"os": "linux", "zone": "dmz", "criticality": 9, "patch_level": 0.9}),
        ("load-balancer", {"os": "linux", "zone": "dmz", "criticality": 8, "patch_level": 0.95}),
        ("proxy-server", {"os": "linux", "zone": "dmz", "criticality": 7, "patch_level": 0.8}),
        ("ci-runner-01", {"os": "linux", "zone": "internal", "criticality": 6, "patch_level": 0.6}),
        ("ci-runner-02", {"os": "linux", "zone": "internal", "criticality": 6, "patch_level": 0.65}),
        ("monitoring-01", {"os": "linux", "zone": "internal", "criticality": 7, "patch_level": 0.9}),
        ("log-collector", {"os": "linux", "zone": "internal", "criticality": 7, "patch_level": 0.88}),
        ("backup-server", {"os": "linux", "zone": "restricted", "criticality": 9, "patch_level": 0.93}),
        ("dc-01", {"os": "windows", "zone": "restricted", "criticality": 10, "patch_level": 0.95}),
        ("dc-02", {"os": "windows", "zone": "restricted", "criticality": 10, "patch_level": 0.94}),
        ("nas-01", {"os": "linux", "zone": "internal", "criticality": 7, "patch_level": 0.7}),
        ("nas-02", {"os": "linux", "zone": "restricted", "criticality": 8, "patch_level": 0.8}),
        ("print-server", {"os": "windows", "zone": "internal", "criticality": 3, "patch_level": 0.3}),
        ("iot-gateway", {"os": "linux", "zone": "dmz", "criticality": 5, "patch_level": 0.4}),
        ("dev-server", {"os": "linux", "zone": "internal", "criticality": 5, "patch_level": 0.5}),
        ("staging-server", {"os": "linux", "zone": "internal", "criticality": 6, "patch_level": 0.55}),
        ("k8s-master-01", {"os": "linux", "zone": "internal", "criticality": 8, "patch_level": 0.9}),
        ("k8s-worker-01", {"os": "linux", "zone": "internal", "criticality": 7, "patch_level": 0.85}),
        ("k8s-worker-02", {"os": "linux", "zone": "internal", "criticality": 7, "patch_level": 0.82}),
        ("api-gateway", {"os": "linux", "zone": "dmz", "criticality": 8, "patch_level": 0.75}),
    ]
    for label, data in specs:
        data["kind"] = "host"
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    return [s[0] for s in specs]


def build_segments(mem: HypergraphMemory) -> list[str]:
    specs = [
        ("seg-dmz-1", {"zone": "dmz", "cidr": "10.0.1.0/24"}),
        ("seg-dmz-2", {"zone": "dmz", "cidr": "10.0.2.0/24"}),
        ("seg-internal-1", {"zone": "internal", "cidr": "10.1.0.0/16"}),
        ("seg-internal-2", {"zone": "internal", "cidr": "10.2.0.0/16"}),
        ("seg-restricted-1", {"zone": "restricted", "cidr": "10.99.0.0/24"}),
        ("seg-restricted-2", {"zone": "restricted", "cidr": "10.99.1.0/24"}),
        ("seg-vpn-pool", {"zone": "dmz", "cidr": "10.0.3.0/24"}),
        ("seg-wireless", {"zone": "internal", "cidr": "10.3.0.0/16"}),
        ("seg-iot", {"zone": "dmz", "cidr": "10.0.4.0/24"}),
        ("seg-management", {"zone": "restricted", "cidr": "10.99.2.0/24"}),
        ("seg-backup", {"zone": "restricted", "cidr": "10.99.3.0/24"}),
        ("seg-ci", {"zone": "internal", "cidr": "10.4.0.0/24"}),
        ("seg-k8s-pod", {"zone": "internal", "cidr": "10.5.0.0/16"}),
        ("seg-storage", {"zone": "internal", "cidr": "10.6.0.0/24"}),
        ("seg-exec-office", {"zone": "restricted", "cidr": "10.99.4.0/24"}),
        ("seg-print", {"zone": "internal", "cidr": "10.7.0.0/24"}),
        ("seg-dev", {"zone": "internal", "cidr": "10.8.0.0/24"}),
        ("seg-guest", {"zone": "dmz", "cidr": "10.0.5.0/24"}),
        ("seg-voip", {"zone": "internal", "cidr": "10.9.0.0/24"}),
        ("seg-monitoring", {"zone": "internal", "cidr": "10.10.0.0/24"}),
        ("seg-honeypot", {"zone": "dmz", "cidr": "10.0.6.0/24"}),
        ("seg-cloud-edge", {"zone": "dmz", "cidr": "10.0.7.0/24"}),
    ]
    for label, data in specs:
        data["kind"] = "segment"
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    return [s[0] for s in specs]


def build_controls(mem: HypergraphMemory) -> list[str]:
    specs = [
        ("fw-perimeter", {"type": "firewall", "coverage": 0.9}),
        ("fw-internal", {"type": "firewall", "coverage": 0.7}),
        ("fw-restricted", {"type": "firewall", "coverage": 0.95}),
        ("ids-dmz", {"type": "ids", "coverage": 0.85}),
        ("ids-internal", {"type": "ids", "coverage": 0.6}),
        ("ips-dmz", {"type": "ips", "coverage": 0.8}),
        ("waf-external", {"type": "waf", "coverage": 0.75}),
        ("siem-main", {"type": "siem", "coverage": 0.7}),
        ("dlp-endpoint", {"type": "dlp", "coverage": 0.5}),
        ("dlp-network", {"type": "dlp", "coverage": 0.6}),
        ("av-endpoint", {"type": "antivirus", "coverage": 0.65}),
        ("edr-fleet", {"type": "edr", "coverage": 0.55}),
        ("ntp-logging", {"type": "monitoring", "coverage": 0.9}),
        ("tls-terminator", {"type": "encryption", "coverage": 0.8}),
        ("nac-8021x", {"type": "nac", "coverage": 0.6}),
        ("vault-secrets", {"type": "secrets_mgr", "coverage": 0.85}),
    ]
    for label, data in specs:
        data["kind"] = "control"
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    return [s[0] for s in specs]


def build_services(mem: HypergraphMemory) -> list[str]:
    specs = [
        ("svc-ssh", {"port": 22, "protocol": "tcp", "encrypted": True}),
        ("svc-http", {"port": 80, "protocol": "tcp", "encrypted": False}),
        ("svc-https", {"port": 443, "protocol": "tcp", "encrypted": True}),
        ("svc-rdp", {"port": 3389, "protocol": "tcp", "encrypted": True}),
        ("svc-smb", {"port": 445, "protocol": "tcp", "encrypted": False}),
        ("svc-ldap", {"port": 389, "protocol": "tcp", "encrypted": False}),
        ("svc-ldaps", {"port": 636, "protocol": "tcp", "encrypted": True}),
        ("svc-mysql", {"port": 3306, "protocol": "tcp", "encrypted": False}),
        ("svc-postgres", {"port": 5432, "protocol": "tcp", "encrypted": False}),
        ("svc-redis", {"port": 6379, "protocol": "tcp", "encrypted": False}),
        ("svc-dns", {"port": 53, "protocol": "udp", "encrypted": False}),
        ("svc-smtp", {"port": 25, "protocol": "tcp", "encrypted": False}),
        ("svc-ftp", {"port": 21, "protocol": "tcp", "encrypted": False}),
        ("svc-kerberos", {"port": 88, "protocol": "tcp", "encrypted": True}),
        ("svc-winrm", {"port": 5985, "protocol": "tcp", "encrypted": False}),
        ("svc-k8s-api", {"port": 6443, "protocol": "tcp", "encrypted": True}),
        ("svc-prometheus", {"port": 9090, "protocol": "tcp", "encrypted": False}),
        ("svc-mqtt", {"port": 1883, "protocol": "tcp", "encrypted": False}),
    ]
    for label, data in specs:
        data["kind"] = "service"
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    return [s[0] for s in specs]


def build_vulnerabilities(mem: HypergraphMemory) -> list[str]:
    specs = [
        ("cve-2024-0001", {"cvss": 9.8, "exploit_available": True}),
        ("cve-2024-0002", {"cvss": 8.5, "exploit_available": True}),
        ("cve-2024-0003", {"cvss": 7.2, "exploit_available": False}),
        ("cve-2024-0004", {"cvss": 6.5, "exploit_available": True}),
        ("cve-2024-0005", {"cvss": 5.3, "exploit_available": False}),
        ("cve-2024-0006", {"cvss": 9.1, "exploit_available": True}),
        ("cve-2024-0007", {"cvss": 4.3, "exploit_available": False}),
        ("cve-2024-0008", {"cvss": 8.8, "exploit_available": True}),
        ("cve-2024-0009", {"cvss": 7.5, "exploit_available": True}),
        ("cve-2024-0010", {"cvss": 6.1, "exploit_available": False}),
        ("cve-2024-0011", {"cvss": 9.4, "exploit_available": True}),
        ("cve-2024-0012", {"cvss": 3.7, "exploit_available": False}),
        ("cve-2024-0013", {"cvss": 8.1, "exploit_available": True}),
        ("cve-2024-0014", {"cvss": 7.8, "exploit_available": False}),
        ("cve-2024-0015", {"cvss": 5.9, "exploit_available": True}),
        ("cve-2024-0016", {"cvss": 9.0, "exploit_available": True}),
    ]
    for label, data in specs:
        data["kind"] = "vulnerability"
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    return [s[0] for s in specs]


def build_users(mem: HypergraphMemory) -> list[str]:
    specs = [
        ("admin-root", {"privilege_level": 10, "department": "ops"}),
        ("admin-network", {"privilege_level": 9, "department": "network"}),
        ("admin-security", {"privilege_level": 9, "department": "security"}),
        ("dev-lead", {"privilege_level": 6, "department": "engineering"}),
        ("dev-senior", {"privilege_level": 5, "department": "engineering"}),
        ("dba-lead", {"privilege_level": 8, "department": "database"}),
        ("analyst-soc", {"privilege_level": 4, "department": "security"}),
        ("user-finance", {"privilege_level": 3, "department": "finance"}),
        ("user-hr", {"privilege_level": 3, "department": "hr"}),
        ("user-exec", {"privilege_level": 7, "department": "executive"}),
        ("contractor-dev", {"privilege_level": 2, "department": "engineering"}),
        ("service-account", {"privilege_level": 8, "department": "automation"}),
    ]
    for label, data in specs:
        data["kind"] = "user"
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    return [s[0] for s in specs]


def build_edges(mem: HypergraphMemory) -> int:
    edges = 0

    host_seg = {
        "web-01": "seg-dmz-1", "web-02": "seg-dmz-1", "web-03": "seg-dmz-1",
        "web-04": "seg-dmz-2", "app-01": "seg-internal-1", "app-02": "seg-internal-1",
        "app-03": "seg-internal-2", "app-04": "seg-internal-2",
        "db-primary": "seg-restricted-1", "db-replica": "seg-restricted-1",
        "db-analytics": "seg-restricted-2",
        "ws-finance-01": "seg-internal-1", "ws-finance-02": "seg-internal-1",
        "ws-finance-03": "seg-internal-2",
        "ws-engineering-01": "seg-internal-2", "ws-engineering-02": "seg-internal-2",
        "ws-engineering-03": "seg-internal-2",
        "ws-hr-01": "seg-internal-1", "ws-hr-02": "seg-internal-1",
        "ws-exec-01": "seg-exec-office", "ws-exec-02": "seg-exec-office",
        "admin-bastion": "seg-management", "admin-jump-01": "seg-internal-1",
        "mail-server": "seg-dmz-2", "dns-server": "seg-dmz-2",
        "vpn-gateway": "seg-vpn-pool", "load-balancer": "seg-dmz-1",
        "proxy-server": "seg-dmz-2", "ci-runner-01": "seg-ci",
        "ci-runner-02": "seg-ci", "monitoring-01": "seg-monitoring",
        "log-collector": "seg-monitoring", "backup-server": "seg-backup",
        "dc-01": "seg-restricted-1", "dc-02": "seg-restricted-1",
        "nas-01": "seg-storage", "nas-02": "seg-backup",
        "print-server": "seg-print", "iot-gateway": "seg-iot",
        "dev-server": "seg-dev", "staging-server": "seg-dev",
        "k8s-master-01": "seg-k8s-pod", "k8s-worker-01": "seg-k8s-pod",
        "k8s-worker-02": "seg-k8s-pod", "api-gateway": "seg-cloud-edge",
    }
    for host, seg in host_seg.items():
        mem.link(host, seg, label="connects_to")
        edges += 1

    host_services = {
        "web-01": ["svc-http", "svc-https"],
        "web-02": ["svc-http", "svc-https"],
        "web-03": ["svc-https"],
        "web-04": ["svc-http", "svc-https"],
        "app-01": ["svc-ssh", "svc-postgres"],
        "app-02": ["svc-ssh", "svc-redis"],
        "app-03": ["svc-ssh", "svc-mysql"],
        "app-04": ["svc-winrm", "svc-rdp"],
        "db-primary": ["svc-postgres", "svc-ssh"],
        "db-replica": ["svc-postgres", "svc-ssh"],
        "db-analytics": ["svc-postgres", "svc-ssh", "svc-redis"],
        "ws-finance-01": ["svc-rdp", "svc-smb"],
        "ws-finance-02": ["svc-rdp", "svc-smb"],
        "ws-finance-03": ["svc-rdp", "svc-smb"],
        "ws-engineering-01": ["svc-ssh", "svc-https"],
        "ws-engineering-02": ["svc-ssh"],
        "ws-engineering-03": ["svc-ssh"],
        "ws-hr-01": ["svc-rdp", "svc-smb"],
        "ws-hr-02": ["svc-rdp", "svc-smb"],
        "ws-exec-01": ["svc-ssh", "svc-https"],
        "ws-exec-02": ["svc-ssh", "svc-https"],
        "admin-bastion": ["svc-ssh"],
        "admin-jump-01": ["svc-ssh", "svc-winrm", "svc-rdp"],
        "mail-server": ["svc-smtp", "svc-https"],
        "dns-server": ["svc-dns"],
        "vpn-gateway": ["svc-https"],
        "load-balancer": ["svc-http", "svc-https"],
        "proxy-server": ["svc-http", "svc-https"],
        "ci-runner-01": ["svc-ssh", "svc-https"],
        "ci-runner-02": ["svc-ssh", "svc-https"],
        "monitoring-01": ["svc-prometheus", "svc-https"],
        "log-collector": ["svc-ssh", "svc-https"],
        "backup-server": ["svc-ssh"],
        "dc-01": ["svc-ldap", "svc-ldaps", "svc-kerberos", "svc-smb"],
        "dc-02": ["svc-ldap", "svc-ldaps", "svc-kerberos", "svc-smb"],
        "nas-01": ["svc-smb", "svc-ftp"],
        "nas-02": ["svc-smb"],
        "print-server": ["svc-smb"],
        "iot-gateway": ["svc-http", "svc-mqtt"],
        "dev-server": ["svc-ssh", "svc-http"],
        "staging-server": ["svc-ssh", "svc-https"],
        "k8s-master-01": ["svc-k8s-api", "svc-ssh"],
        "k8s-worker-01": ["svc-ssh", "svc-k8s-api"],
        "k8s-worker-02": ["svc-ssh", "svc-k8s-api"],
        "api-gateway": ["svc-https", "svc-http"],
    }
    for host, svcs in host_services.items():
        for svc in svcs:
            mem.link(host, svc, label="runs")
            edges += 1

    exposure = {
        "web-01": ["svc-http", "svc-https"],
        "web-02": ["svc-http", "svc-https"],
        "web-03": ["svc-https"],
        "web-04": ["svc-http", "svc-https"],
        "mail-server": ["svc-smtp"],
        "dns-server": ["svc-dns"],
        "vpn-gateway": ["svc-https"],
        "load-balancer": ["svc-http", "svc-https"],
        "proxy-server": ["svc-http", "svc-https"],
        "api-gateway": ["svc-https", "svc-http"],
        "iot-gateway": ["svc-http"],
        "admin-jump-01": ["svc-rdp"],
        "ws-finance-01": ["svc-rdp"],
        "nas-01": ["svc-ftp"],
        "staging-server": ["svc-https"],
        "monitoring-01": ["svc-prometheus"],
        "dev-server": ["svc-http"],
    }
    for host, svcs in exposure.items():
        for svc in svcs:
            mem.link(host, svc, label="exposed_on")
            edges += 1

    vuln_map = {
        "web-01": ["cve-2024-0001", "cve-2024-0004"],
        "web-02": ["cve-2024-0002", "cve-2024-0006"],
        "web-03": ["cve-2024-0003"],
        "web-04": ["cve-2024-0001", "cve-2024-0008", "cve-2024-0009"],
        "app-01": ["cve-2024-0004"],
        "app-03": ["cve-2024-0005"],
        "app-04": ["cve-2024-0008", "cve-2024-0013"],
        "db-primary": ["cve-2024-0006"],
        "db-replica": ["cve-2024-0006"],
        "db-analytics": ["cve-2024-0010"],
        "ws-finance-01": ["cve-2024-0001", "cve-2024-0009", "cve-2024-0011"],
        "ws-finance-02": ["cve-2024-0004", "cve-2024-0009"],
        "ws-finance-03": ["cve-2024-0001", "cve-2024-0013", "cve-2024-0015"],
        "ws-engineering-01": ["cve-2024-0005"],
        "ws-hr-01": ["cve-2024-0009", "cve-2024-0010"],
        "ws-hr-02": ["cve-2024-0004"],
        "dc-01": ["cve-2024-0016"],
        "dc-02": ["cve-2024-0003"],
        "nas-01": ["cve-2024-0007", "cve-2024-0014"],
        "print-server": ["cve-2024-0012", "cve-2024-0007"],
        "iot-gateway": ["cve-2024-0001", "cve-2024-0002", "cve-2024-0011"],
        "vpn-gateway": ["cve-2024-0003"],
        "admin-jump-01": ["cve-2024-0013"],
        "ci-runner-01": ["cve-2024-0005", "cve-2024-0015"],
        "k8s-worker-01": ["cve-2024-0008"],
        "k8s-worker-02": ["cve-2024-0005"],
        "api-gateway": ["cve-2024-0002", "cve-2024-0011"],
        "staging-server": ["cve-2024-0004", "cve-2024-0010"],
        "dev-server": ["cve-2024-0009"],
        "proxy-server": ["cve-2024-0006"],
        "backup-server": ["cve-2024-0003"],
    }
    for host, vulns in vuln_map.items():
        for vuln in vulns:
            mem.link(host, vuln, label="vulnerable_to")
            edges += 1

    protections = {
        "web-01": ["waf-external", "fw-perimeter", "ips-dmz"],
        "web-02": ["waf-external", "fw-perimeter", "ips-dmz"],
        "web-03": ["waf-external", "fw-perimeter"],
        "web-04": ["fw-perimeter", "ids-dmz"],
        "app-01": ["fw-internal", "ids-internal"],
        "app-02": ["fw-internal"],
        "app-03": ["fw-internal"],
        "app-04": ["fw-internal", "edr-fleet"],
        "db-primary": ["fw-restricted", "fw-internal"],
        "db-replica": ["fw-restricted", "fw-internal"],
        "db-analytics": ["fw-restricted"],
        "dc-01": ["fw-restricted", "fw-internal"],
        "dc-02": ["fw-restricted", "fw-internal"],
        "admin-bastion": ["fw-restricted"],
        "backup-server": ["fw-restricted"],
        "nas-02": ["fw-restricted"],
        "ws-exec-01": ["fw-internal", "edr-fleet"],
        "ws-exec-02": ["fw-internal", "edr-fleet"],
        "mail-server": ["fw-perimeter", "ids-dmz"],
        "dns-server": ["fw-perimeter"],
        "vpn-gateway": ["fw-perimeter"],
        "load-balancer": ["fw-perimeter", "tls-terminator"],
        "proxy-server": ["fw-perimeter"],
        "api-gateway": ["fw-perimeter", "waf-external"],
        "iot-gateway": ["fw-perimeter", "ids-dmz"],
        "monitoring-01": ["fw-internal"],
        "log-collector": ["fw-internal", "siem-main"],
        "ci-runner-01": ["fw-internal"],
        "ci-runner-02": ["fw-internal"],
        "k8s-master-01": ["fw-internal"],
        "k8s-worker-01": ["fw-internal"],
        "k8s-worker-02": ["fw-internal"],
    }
    for host, ctrls in protections.items():
        for ctrl in ctrls:
            mem.link(host, ctrl, label="protected_by")
            edges += 1

    trust = [
        ("dc-01", "dc-02", "trusts"),
        ("dc-02", "dc-01", "trusts"),
        ("admin-bastion", "dc-01", "trusts"),
        ("admin-bastion", "dc-02", "trusts"),
        ("admin-jump-01", "admin-bastion", "trusts"),
        ("ws-finance-01", "dc-01", "trusts"),
        ("ws-finance-02", "dc-01", "trusts"),
        ("ws-finance-03", "dc-01", "trusts"),
        ("ws-hr-01", "dc-01", "trusts"),
        ("ws-hr-02", "dc-01", "trusts"),
        ("ws-exec-01", "dc-01", "trusts"),
        ("ws-exec-02", "dc-01", "trusts"),
        ("ws-engineering-01", "dc-01", "trusts"),
        ("ws-engineering-02", "dc-01", "trusts"),
        ("ws-engineering-03", "dc-01", "trusts"),
        ("app-04", "dc-01", "trusts"),
        ("app-04", "dc-02", "trusts"),
        ("print-server", "dc-01", "trusts"),
        ("ci-runner-01", "dev-server", "trusts"),
        ("ci-runner-02", "dev-server", "trusts"),
        ("dev-server", "staging-server", "trusts"),
        ("staging-server", "app-01", "trusts"),
        ("k8s-master-01", "k8s-worker-01", "trusts"),
        ("k8s-master-01", "k8s-worker-02", "trusts"),
        ("k8s-worker-01", "k8s-worker-02", "trusts"),
        ("k8s-worker-02", "k8s-worker-01", "trusts"),
        ("app-01", "db-primary", "trusts"),
        ("app-01", "db-replica", "trusts"),
        ("app-02", "db-replica", "trusts"),
        ("app-02", "db-analytics", "trusts"),
        ("app-03", "db-primary", "trusts"),
        ("db-analytics", "db-primary", "trusts"),
        ("nas-01", "backup-server", "trusts"),
        ("monitoring-01", "log-collector", "trusts"),
    ]
    for src, tgt, lbl in trust:
        mem.link(src, tgt, label=lbl)
        edges += 1

    access = [
        ("admin-root", "admin-bastion"),
        ("admin-root", "admin-jump-01"),
        ("admin-root", "dc-01"),
        ("admin-root", "dc-02"),
        ("admin-root", "db-primary"),
        ("admin-network", "fw-perimeter"),
        ("admin-network", "fw-internal"),
        ("admin-network", "fw-restricted"),
        ("admin-network", "vpn-gateway"),
        ("admin-security", "siem-main"),
        ("admin-security", "ids-dmz"),
        ("admin-security", "ids-internal"),
        ("admin-security", "edr-fleet"),
        ("admin-security", "admin-bastion"),
        ("dev-lead", "k8s-master-01"),
        ("dev-lead", "dev-server"),
        ("dev-lead", "staging-server"),
        ("dev-senior", "dev-server"),
        ("dev-senior", "ci-runner-01"),
        ("dba-lead", "db-primary"),
        ("dba-lead", "db-replica"),
        ("dba-lead", "db-analytics"),
        ("analyst-soc", "siem-main"),
        ("analyst-soc", "monitoring-01"),
        ("analyst-soc", "log-collector"),
        ("user-finance", "ws-finance-01"),
        ("user-finance", "ws-finance-02"),
        ("user-finance", "app-04"),
        ("user-hr", "ws-hr-01"),
        ("user-hr", "ws-hr-02"),
        ("user-exec", "ws-exec-01"),
        ("user-exec", "ws-exec-02"),
        ("user-exec", "admin-jump-01"),
        ("contractor-dev", "dev-server"),
        ("contractor-dev", "ci-runner-01"),
        ("service-account", "backup-server"),
        ("service-account", "log-collector"),
        ("service-account", "monitoring-01"),
        ("service-account", "ci-runner-02"),
        ("service-account", "nas-01"),
    ]
    for user, host in access:
        mem.link(user, host, label="has_access")
        edges += 1

    routes = [
        ("seg-dmz-1", "seg-internal-1"),
        ("seg-dmz-2", "seg-internal-1"),
        ("seg-dmz-1", "seg-dmz-2"),
        ("seg-dmz-2", "seg-dmz-1"),
        ("seg-internal-1", "seg-restricted-1"),
        ("seg-internal-2", "seg-restricted-1"),
        ("seg-internal-1", "seg-internal-2"),
        ("seg-internal-2", "seg-internal-1"),
        ("seg-vpn-pool", "seg-internal-1"),
        ("seg-vpn-pool", "seg-internal-2"),
        ("seg-iot", "seg-dmz-2"),
        ("seg-internal-1", "seg-ci"),
        ("seg-internal-1", "seg-k8s-pod"),
        ("seg-internal-1", "seg-storage"),
        ("seg-internal-1", "seg-print"),
        ("seg-internal-2", "seg-dev"),
        ("seg-internal-1", "seg-monitoring"),
        ("seg-restricted-1", "seg-backup"),
        ("seg-restricted-1", "seg-management"),
        ("seg-restricted-1", "seg-restricted-2"),
        ("seg-restricted-2", "seg-restricted-1"),
        ("seg-restricted-1", "seg-exec-office"),
        ("seg-dmz-1", "seg-cloud-edge"),
        ("seg-internal-1", "seg-voip"),
        ("seg-internal-2", "seg-voip"),
        ("seg-guest", "seg-dmz-2"),
        ("seg-dmz-2", "seg-honeypot"),
    ]
    for src, tgt in routes:
        mem.link(src, tgt, label="routes_to")
        edges += 1

    return edges


def compute_risk_scores(
    mem: HypergraphMemory,
    degree: dict[str, float],
    betweenness: dict[str, float],
) -> dict[str, float]:
    host_labels = set(mem.query_nodes(data={"kind": "host"}))
    vuln_edges = mem.pattern_match(edge_label="vulnerable_to")
    vuln_count: dict[str, int] = defaultdict(int)
    for edge in vuln_edges:
        for lbl in edge.source_labels:
            if lbl in host_labels:
                vuln_count[lbl] += 1

    exploit_vuln_set = set(mem.query_nodes(data={"kind": "vulnerability", "exploit_available": True}))
    exploit_edges = []
    for edge in vuln_edges:
        for lbl in edge.target_labels:
            if lbl in exploit_vuln_set:
                exploit_edges.append(edge)

    scores: dict[str, float] = {}
    for label in host_labels:
        vc = vuln_count.get(label, 0)
        dc = degree.get(label, 0.0)
        bc = betweenness.get(label, 0.0)
        node = mem.engine.graph.get_node_by_label(label)
        crit = node.data.get("criticality", 1) if node else 1
        patch = node.data.get("patch_level", 0.5) if node else 0.5
        scores[label] = vc * 10 + dc * 50 + bc * 80 + crit * 3 + (1.0 - patch) * 15

    return scores


def find_cross_zone_violations(mem: HypergraphMemory) -> list[tuple[str, str, str, str, str]]:
    violations: list[tuple[str, str, str, str, str]] = []
    route_edges = mem.pattern_match(edge_label="routes_to")
    seg_zones: dict[str, str] = {}
    for lbl in mem.query_nodes(data={"kind": "segment"}):
        node = mem.engine.graph.get_node_by_label(lbl)
        if node:
            seg_zones[lbl] = node.data.get("zone", "unknown")

    zone_rank = {"dmz": 0, "internal": 1, "restricted": 2}
    for edge in route_edges:
        src_label = edge.source_labels[0] if edge.source_labels else ""
        tgt_label = edge.target_labels[0] if edge.target_labels else ""

        sz = seg_zones.get(src_label, "")
        tz = seg_zones.get(tgt_label, "")
        if sz and tz and sz != tz:
            sr = zone_rank.get(sz, -1)
            tr = zone_rank.get(tz, -1)
            if tr - sr >= 2:
                violations.append((src_label, sz, tgt_label, tz, "routes_to"))

    trust_edges = mem.pattern_match(edge_label="trusts")
    for edge in trust_edges:
        src_label = edge.source_labels[0] if edge.source_labels else ""
        tgt_label = edge.target_labels[0] if edge.target_labels else ""

        if src_label and tgt_label:
            src_node = mem.engine.graph.get_node_by_label(src_label)
            tgt_node = mem.engine.graph.get_node_by_label(tgt_label)
            if src_node and tgt_node:
                sz = src_node.data.get("zone", "")
                tz = tgt_node.data.get("zone", "")
                if sz and tz and sz != tz:
                    sr = zone_rank.get(sz, -1)
                    tr = zone_rank.get(tz, -1)
                    if tr > sr:
                        violations.append((src_label, sz, tgt_label, tz, "trusts"))

    return violations


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Building Enterprise Network Topology
    # =====================================================================
    print("=" * 70)
    print("SECTION 1: Building Enterprise Network Topology")
    print("=" * 70)

    hosts = build_hosts(mem)
    segments = build_segments(mem)
    controls = build_controls(mem)
    services = build_services(mem)
    vulns = build_vulnerabilities(mem)
    users = build_users(mem)
    edge_count = build_edges(mem)

    print(f"  Hosts:             {len(hosts)}")
    print(f"  Network segments:  {len(segments)}")
    print(f"  Security controls: {len(controls)}")
    print(f"  Services:          {len(services)}")
    print(f"  Vulnerabilities:   {len(vulns)}")
    print(f"  Users/roles:       {len(users)}")
    print(f"  Total nodes:       {mem.size[0]}")
    print(f"  Total edges:       {mem.size[1]}")
    print()

    # =====================================================================
    # SECTION 2: Degree Centrality - Most Exposed Assets
    # =====================================================================
    print("=" * 70)
    print("SECTION 2: Degree Centrality - Most Exposed Assets")
    print("=" * 70)

    degree = mem.analyze.centrality("degree")
    host_degree = {
        lbl: score for lbl, score in degree.items()
        if lbl in set(hosts)
    }
    top_exposed = top_k(host_degree, k=10)
    print(f"  {'Host':25s} {'Degree':>8s}  {'Zone':12s}  Crit Patch")
    print(f"  {'-' * 25} {'-' * 8}  {'-' * 12}  ---- -----")
    for label, score in top_exposed:
        node = mem.engine.graph.get_node_by_label(label)
        zone = node.data.get("zone", "?") if node else "?"
        crit = node.data.get("criticality", 0) if node else 0
        patch = node.data.get("patch_level", 0) if node else 0
        print(f"  {label:25s} {score:8.4f}  {zone:12s}  {crit:4d} {patch:.2f}")
    print()

    # =====================================================================
    # SECTION 3: Betweenness Centrality - Critical Chokepoints
    # =====================================================================
    print("=" * 70)
    print("SECTION 3: Betweenness Centrality - Critical Chokepoints")
    print("=" * 70)

    betweenness = mem.analyze.centrality("betweenness")
    top_choke = top_k(betweenness, k=10)
    print(f"  {'Node':25s} {'Betweenness':>12s}  {'Kind':10s}")
    print(f"  {'-' * 25} {'-' * 12}  {'-' * 10}")
    for label, score in top_choke:
        node = mem.engine.graph.get_node_by_label(label)
        kind = node.data.get("kind", "?") if node else "?"
        print(f"  {label:25s} {score:12.4f}  {kind:10s}")
    print()

    print("  Top 5 critical chokepoints (assets whose compromise reaches many systems):")
    host_bw = {lbl: s for lbl, s in betweenness.items() if lbl in set(hosts)}
    top5_choke = top_k(host_bw, k=5)
    for i, (label, score) in enumerate(top5_choke, 1):
        node = mem.engine.graph.get_node_by_label(label)
        zone = node.data.get("zone", "?") if node else "?"
        crit = node.data.get("criticality", 0) if node else 0
        print(f"    {i}. {label:25s} betweenness={score:.4f}  zone={zone}  criticality={crit}")
    print()

    # =====================================================================
    # SECTION 4: Connected Components - Segmentation Verification
    # =====================================================================
    print("=" * 70)
    print("SECTION 4: Connected Components - Segmentation Verification")
    print("=" * 70)

    components = mem.connected_components()
    print(f"  Total connected components: {len(components)}")
    for i, comp in enumerate(components):
        zones: dict[str, int] = defaultdict(int)
        for lbl in comp:
            node = mem.engine.graph.get_node_by_label(lbl)
            if node:
                zones[node.data.get("zone", "unknown")] += 1
        zones_str = ", ".join(f"{z}:{c}" for z, c in sorted(zones.items()))
        print(f"    Component {i + 1}: {len(comp)} nodes  [{zones_str}]")
    print()

    if len(components) == 1:
        print("  WARNING: Entire network is a single connected component.")
        print("  DMZ, internal, and restricted zones are NOT isolated.")
    else:
        print("  Network has multiple isolated segments.")
    print()

    # =====================================================================
    # SECTION 5: Cycle Detection - Circular Trust Relationships
    # =====================================================================
    print("=" * 70)
    print("SECTION 5: Cycle Detection - Circular Trust Relationships")
    print("=" * 70)

    cycles = mem.detect_cycles(max_cycles=15)
    print(f"  Detected {len(cycles)} cycles\n")

    trust_cycles = []
    for cycle in cycles:
        has_trust = False
        cycle_set = set(cycle)
        for i in range(len(cycle)):
            src = cycle[i]
            tgt = cycle[(i + 1) % len(cycle)]
            src_node = mem.engine.graph.get_node_by_label(src)
            tgt_node = mem.engine.graph.get_node_by_label(tgt)
            if src_node and tgt_node:
                for edge in mem.engine.graph.outgoing_edges(src_node.id):
                    if tgt_node.id in edge.target_ids and edge.label == "trusts":
                        has_trust = True
                        break
            if has_trust:
                break
        if has_trust:
            trust_cycles.append(cycle)

    if trust_cycles:
        print(f"  Trust cycles (privilege escalation paths): {len(trust_cycles)}")
        for i, cycle in enumerate(trust_cycles[:10], 1):
            display = cycle[:8]
            suffix = " ..." if len(cycle) > 8 else ""
            print(f"    {i}. {' -> '.join(display)}{suffix} -> {cycle[0]}")
    else:
        print("  No pure trust cycles detected.")
    print()

    # =====================================================================
    # SECTION 6: Cross-Zone Violations - Segmentation Policy Breaches
    # =====================================================================
    print("=" * 70)
    print("SECTION 6: Cross-Zone Violations - Segmentation Policy Breaches")
    print("=" * 70)

    violations = find_cross_zone_violations(mem)
    print(f"  Found {len(violations)} cross-zone violations\n")

    trust_violations = [v for v in violations if v[4] == "trusts"]
    route_violations = [v for v in violations if v[4] == "routes_to"]

    if trust_violations:
        print(f"  Trust violations ({len(trust_violations)}):")
        for src, sz, tgt, tz, kind in trust_violations[:10]:
            print(f"    {src} [{sz}] -> {tgt} [{tz}]  ({kind})")
        print()

    if route_violations:
        print(f"  Routing violations ({len(route_violations)}):")
        for src, sz, tgt, tz, kind in route_violations[:10]:
            print(f"    {src} [{sz}] -> {tgt} [{tz}]  ({kind})")
        print()

    # =====================================================================
    # SECTION 7: Degree Distribution
    # =====================================================================
    print("=" * 70)
    print("SECTION 7: Degree Distribution")
    print("=" * 70)

    dist = mem.degree_distribution()
    print(f"  {'Degree':>6s}  {'Nodes':>6s}  Distribution")
    print(f"  {'-' * 6}  {'-' * 6}  {'-' * 40}")
    max_count = max(dist.values()) if dist else 1
    for d in sorted(dist.keys()):
        count = dist[d]
        bar = "#" * int(count / max_count * 40)
        print(f"  {d:6d}  {count:6d}  {bar}")

    total_nodes = sum(dist.values())
    avg_deg = sum(d * c for d, c in dist.items()) / total_nodes if total_nodes else 0
    print(f"\n  Average degree: {avg_deg:.1f}")
    print()

    # =====================================================================
    # SECTION 8: Composite Risk Scoring
    # =====================================================================
    print("=" * 70)
    print("SECTION 8: Composite Risk Scoring - Critical Risk Hosts")
    print("=" * 70)

    risk_scores = compute_risk_scores(mem, degree, betweenness)
    top_risk = top_k(risk_scores, k=15)

    host_set = set(mem.query_nodes(data={"kind": "host"}))
    vuln_edges = mem.pattern_match(edge_label="vulnerable_to")
    vuln_count: dict[str, int] = defaultdict(int)
    for edge in vuln_edges:
        for lbl in edge.source_labels:
            if lbl in host_set:
                vuln_count[lbl] += 1

    print(f"  {'Host':25s} {'Risk':>7s}  {'Vulns':>5s}  {'Deg':>6s}  {'Btw':>7s}  Zone")
    print(f"  {'-' * 25} {'-' * 7}  {'-' * 5}  {'-' * 6}  {'-' * 7}  {'-' * 12}")
    for label, risk in top_risk:
        node = mem.engine.graph.get_node_by_label(label)
        zone = node.data.get("zone", "?") if node else "?"
        vc = vuln_count.get(label, 0)
        dc = degree.get(label, 0)
        bc = betweenness.get(label, 0)
        print(f"  {label:25s} {risk:7.1f}  {vc:5d}  {dc:6.4f}  {bc:7.4f}  {zone}")
    print()

    # =====================================================================
    # SECTION 9: Attack Path Highlights
    # =====================================================================
    print("=" * 70)
    print("SECTION 9: Attack Path Highlights")
    print("=" * 70)

    print("  Highest-risk DMZ hosts (attacker entry points):")
    dmz_hosts = mem.query_nodes(data={"kind": "host", "zone": "dmz"})
    dmz_with_vulns = []
    for h in dmz_hosts:
        if vuln_count.get(h, 0) > 0:
            dmz_with_vulns.append((h, risk_scores.get(h, 0)))
    dmz_with_vulns.sort(key=lambda x: -x[1])
    for label, risk in dmz_with_vulns[:5]:
        vc = vuln_count.get(label, 0)
        print(f"    {label:25s}  risk={risk:.1f}  vulns={vc}")
    print()

    print("  Lateral movement paths (trust chains to restricted zone):")
    lateral_targets = [
        ("staging-server", "db-primary", "CI/CD staging to production database"),
        ("admin-jump-01", "admin-bastion", "Jump host to bastion (restricted)"),
        ("admin-jump-01", "dc-01", "Jump host to domain controller"),
        ("dev-server", "db-primary", "Dev server to production database"),
        ("ws-exec-01", "dc-01", "Exec workstation to domain controller"),
    ]
    for src, tgt, desc in lateral_targets:
        path = mem.shortest_path(src, tgt)
        if path:
            zones_in_path = []
            for p in path:
                n = mem.engine.graph.get_node_by_label(p)
                if n:
                    zones_in_path.append(n.data.get("zone", "?"))
            print(f"    {desc}:")
            print(f"      {' -> '.join(path)}")
            print(f"      Zone traversal: {' -> '.join(zones_in_path)}")
    print()

    # =====================================================================
    # SECTION 10: Trust Chain Inference
    # =====================================================================
    print("=" * 70)
    print("SECTION 10: Trust Chain Inference")
    print("=" * 70)

    mem.add_rules(TransitiveRule(edge_label="trusts", new_label="trusts_indirectly"))
    print("  Added TransitiveRule: trusts -> trusts_indirectly\n")

    reason_result = mem.reason(
        seeds={"admin-jump-01", "dev-server", "dc-01", "vpn-gateway"},
        max_depth=4,
    )
    print(f"  Reasoning expansion:")
    print(f"    States created: {reason_result.states_created}")
    if reason_result.expansion:
        print(f"    Edges produced: {reason_result.expansion.edges_produced}")
    print()

    indirect_edges = mem.analyze.edges(label="trusts_indirectly")
    print(f"  Inferred indirect trust edges ({len(indirect_edges)}):")
    for edge in indirect_edges:
        src = ", ".join(edge.source_labels)
        tgt = ", ".join(edge.target_labels)
        print(f"    {src} -> {tgt}  (weight={edge.weight:.2f})")
    print()

    restricted_hosts = set(mem.query_nodes(data={"kind": "host", "zone": "restricted"}))
    reachable_restricted = set()
    for edge in indirect_edges:
        for lbl in edge.target_labels:
            if lbl in restricted_hosts:
                reachable_restricted.add(lbl)
        for lbl in edge.source_labels:
            if lbl in restricted_hosts:
                reachable_restricted.add(lbl)
    print(f"  Restricted-zone hosts reachable via indirect trust ({len(reachable_restricted)}):")
    for h in sorted(reachable_restricted):
        print(f"    {h}")
    print()

    # =====================================================================
    # SECTION 11: Network Segment Detection
    # =====================================================================
    print("=" * 70)
    print("SECTION 11: Network Segment Detection")
    print("=" * 70)

    comm_result = mem.analyze.communities(seed=42)
    print(f"  Communities detected: {comm_result.community_count}")
    print(f"  Modularity:            {comm_result.modularity:.4f}")
    print(f"  Coverage:              {comm_result.coverage:.4f}")
    print()

    host_zone = {}
    for lbl in mem.query_nodes(data={"kind": "host"}):
        node = mem.engine.graph.get_node_by_label(lbl)
        if node:
            host_zone[lbl] = node.data.get("zone", "unknown")

    zone_mixing = []
    for comm in comm_result.communities:
        zones_in_comm: dict[str, list[str]] = defaultdict(list)
        for member in comm.member_labels:
            zone = host_zone.get(member, "non-host")
            zones_in_comm[zone].append(member)

        is_mixing = len(zones_in_comm) > 1 and any(
            z != "non-host" for z in zones_in_comm
        )

        print(f"  Community {comm.community_id} ({comm.size} members):")
        for zone, members in sorted(zones_in_comm.items()):
            sample = members[:5]
            suffix = f" +{len(members) - 5} more" if len(members) > 5 else ""
            print(f"    {zone:12s}: {', '.join(sample)}{suffix}")

        if is_mixing:
            host_zones = {z: ms for z, ms in zones_in_comm.items() if z != "non-host"}
            zone_mixing.append((comm.community_id, dict(host_zones)))
    print()

    if zone_mixing:
        print(f"  Zone-mixing communities ({len(zone_mixing)}):")
        for cid, zones in zone_mixing:
            zone_summary = ", ".join(f"{z}({len(ms)})" for z, ms in sorted(zones.items()))
            print(f"    Community {cid}: {zone_summary}")
    else:
        print("  No zone-mixing communities detected.")
    print()

    # =====================================================================
    # SECTION 12: Structural Anomaly Detection
    # =====================================================================
    print("=" * 70)
    print("SECTION 12: Structural Anomaly Detection")
    print("=" * 70)

    anomaly_targets = [
        "dc-01", "admin-bastion", "db-primary",
        "admin-jump-01", "web-04", "iot-gateway",
    ]
    print(f"  {'Host':20s} {'Status':14s} {'Score':>7s}  Insights")
    print(f"  {'-' * 20} {'-' * 14} {'-' * 7}  {'-' * 45}")
    for concept in anomaly_targets:
        result = mem.analyze.anomalies(concept)
        insights_preview = result.structural_insights[:2]
        insights_str = "; ".join(insights_preview) if insights_preview else "(none)"
        if len(insights_str) > 60:
            insights_str = insights_str[:57] + "..."
        print(
            f"  {concept:20s} {result.anomaly_status:14s} {result.boundary_score:7.3f}  {insights_str}"
        )
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Network: {mem.size[0]} nodes, {mem.size[1]} edges")
    print(f"  Connected components: {len(components)}")
    print(f"  Total cycles detected: {len(cycles)}")
    print(f"  Cross-zone violations: {len(violations)}")
    top_host = top_exposed[0] if top_exposed else ("N/A", 0)
    top_chokepoint = top5_choke[0] if top5_choke else ("N/A", 0)
    top_critical = top_risk[0] if top_risk else ("N/A", 0)
    print(f"  Most exposed host:     {top_host[0]:25s} (degree={top_host[1]:.4f})")
    print(f"  Top chokepoint:        {top_chokepoint[0]:25s} (betweenness={top_chokepoint[1]:.4f})")
    print(f"  Highest risk host:     {top_critical[0]:25s} (risk={top_critical[1]:.1f})")
    print(f"  Segmentation:          {'ISOLATED' if len(components) > 1 else 'NOT ISOLATED'}")
    print()


if __name__ == "__main__":
    main()
