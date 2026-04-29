"""
Software Dependency Security Scanner (NetworkX Implementation)
==============================================================

Same pipeline as the Hyper3 Prefect flow, implemented with NetworkX:

1. Fetches reviewed security advisories from the GitHub Advisory Database API.
2. Enriches each vulnerable package with metadata from PyPI.
3. Builds a directed NetworkX graph connecting advisories, packages, and
   their transitive dependencies.
4. Analyses vulnerability chains, blast radii, chokepoints, advisory
   patterns, and ecosystem clusters using NetworkX primitives.

Run:
    .venv/bin/python examples/comparison/dependency_scanner/networkx_analysis.py
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import requests


GITHUB_ADV_ENDPOINT = "https://api.github.com/advisories"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
PYPI_ENDPOINT = "https://pypi.org/pypi/{package}/json"


@dataclass
class AdvisoryRecord:
    ghsa_id: str
    cve_id: str | None
    summary: str
    severity: str
    packages: list[dict[str, Any]] = field(default_factory=list)
    patched_versions: list[str] = field(default_factory=list)


@dataclass
class PackageRecord:
    name: str
    version: str
    requires_dist: list[str] = field(default_factory=list)
    ecosystem: str = "pypi"


def fetch_advisories(per_page: int = 50) -> list[dict[str, Any]]:
    print(f"[fetch] GET {GITHUB_ADV_ENDPOINT}?type=reviewed&per_page={per_page}")
    url = f"{GITHUB_ADV_ENDPOINT}?type=reviewed&per_page={per_page}"

    resp = requests.get(url, headers=GITHUB_HEADERS, timeout=30)
    if resp.status_code == 403:
        print("[fetch] Rate limited — sleeping 60s")
        time.sleep(60)
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    print(f"[fetch] Received {len(data)} advisories")
    return data


def fetch_pypi_metadata(package_name: str) -> PackageRecord | None:
    url = PYPI_ENDPOINT.format(package=package_name)
    print(f"[fetch] GET {url}")

    try:
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
        if resp.status_code == 404:
            print(f"[fetch] {package_name} not found on PyPI")
            return None
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[fetch] PyPI request failed for {package_name}: {exc}")
        return None

    body = resp.json()
    info = body.get("info", {})
    version = info.get("version", "unknown")
    requires_dist = info.get("requires_dist") or []
    time.sleep(0.25)
    return PackageRecord(name=package_name, version=version, requires_dist=requires_dist)


def parse_advisories(raw: list[dict[str, Any]]) -> list[AdvisoryRecord]:
    records: list[AdvisoryRecord] = []

    for item in raw:
        ghsa_id = item.get("ghsa_id", "")
        cve_id = item.get("cve_id")
        summary = item.get("summary", "")
        severity = item.get("severity", "UNKNOWN")
        vulns = item.get("vulnerabilities") or []
        packages = []
        patched: list[str] = []

        for vuln in vulns:
            pkg = vuln.get("package", {})
            packages.append({
                "name": pkg.get("name", ""),
                "ecosystem": pkg.get("ecosystem", ""),
            })
            first_patched = vuln.get("first_patched_version", {})
            if first_patched and isinstance(first_patched, dict) and first_patched.get("identifier"):
                patched.append(first_patched["identifier"])
            elif first_patched and isinstance(first_patched, str):
                patched.append(first_patched)

        if ghsa_id and packages:
            records.append(AdvisoryRecord(
                ghsa_id=ghsa_id,
                cve_id=cve_id,
                summary=summary,
                severity=severity,
                packages=packages,
                patched_versions=patched,
            ))

    print(f"[parse] {len(records)} actionable advisories")
    return records


def parse_requires_dist(requires_dist: list[str]) -> list[tuple[str, list[str]]]:
    deps: list[tuple[str, list[str]]] = []
    for spec in requires_dist:
        base = spec.split(";")[0].split(">")[0].split("<")[0].split("=")[0].split("!")[0].split("~")[0]
        base = base.strip()
        if not base:
            continue

        extras: list[str] = []
        if "[" in base:
            idx = base.index("[")
            extras_str = base[idx + 1 : base.index("]")]
            extras = [e.strip() for e in extras_str.split(",")]
            base = base[:idx]

        deps.append((base.strip(), extras))
    return deps


def build_graph(
    advisories: list[AdvisoryRecord],
    pypi_packages: dict[str, PackageRecord],
) -> tuple[nx.DiGraph, dict[str, dict[str, Any]]]:
    G = nx.DiGraph()
    node_data: dict[str, dict[str, Any]] = {}

    for adv in advisories:
        adv_label = adv.ghsa_id
        G.add_node(adv_label)
        node_data[adv_label] = {
            "type": "advisory",
            "cve_id": adv.cve_id,
            "severity": adv.severity,
            "summary": adv.summary[:200],
            "patched_versions": adv.patched_versions,
        }

        if adv.cve_id:
            G.add_node(adv.cve_id)
            node_data[adv.cve_id] = {"type": "cve"}
            G.add_edge(adv.cve_id, adv_label, label="identified_as")

        for pkg_info in adv.packages:
            pkg_name = pkg_info["name"]
            ecosystem = pkg_info.get("ecosystem", "unknown")

            if pkg_name in pypi_packages:
                pypi = pypi_packages[pkg_name]
                G.add_node(pkg_name)
                node_data[pkg_name] = {
                    "type": "package",
                    "version": pypi.version,
                    "ecosystem": ecosystem,
                }
                G.add_edge(adv_label, pkg_name, label="affects")

                for patched in adv.patched_versions:
                    fixed_label = f"{pkg_name}=={patched}"
                    G.add_node(fixed_label)
                    node_data[fixed_label] = {
                        "type": "fixed_version",
                        "package": pkg_name,
                        "version": patched,
                    }
                    G.add_edge(adv_label, fixed_label, label="fixes")

                deps = parse_requires_dist(pypi.requires_dist)
                for dep_name, extras in deps:
                    dep_label = dep_name.lower().replace("-", "_")
                    G.add_node(dep_label)
                    node_data[dep_label] = {
                        "type": "dependency",
                        "extras": extras,
                        "ecosystem": "pypi",
                    }
                    G.add_edge(pkg_name, dep_label, label="depends_on")
            else:
                G.add_node(pkg_name)
                node_data[pkg_name] = {
                    "type": "package",
                    "ecosystem": ecosystem,
                    "version": "unknown",
                }
                G.add_edge(adv_label, pkg_name, label="affects")

    print(f"[build] Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G, node_data


def analyze_transitive_dependencies(
    G: nx.DiGraph,
    node_data: dict[str, dict[str, Any]],
) -> list[tuple[str, str, str]]:
    inferred: list[tuple[str, str, str]] = []

    dep_edges = {(u, v) for u, v, d in G.edges(data=True) if d.get("label") == "depends_on"}
    for (a, b) in list(dep_edges):
        for (c, d) in list(dep_edges):
            if b == c and a != d:
                if not G.has_edge(a, d):
                    inferred.append((a, d, "depends_on_transitive"))

    for src, tgt, label in inferred:
        G.add_edge(src, tgt, label=label)

    print(f"[transitive] {len(inferred)} transitive dependency edges inferred")
    return inferred


def analyze_blast_radius(
    G: nx.DiGraph,
    node_data: dict[str, dict[str, Any]],
    advisories: list[AdvisoryRecord],
) -> dict[str, list[str]]:
    critical = [a for a in advisories if a.severity in ("HIGH", "CRITICAL")]
    if not critical:
        critical = advisories[:3]

    blast_radii: dict[str, list[str]] = {}
    for adv in critical[:5]:
        adv_label = adv.ghsa_id
        if adv_label not in G:
            continue

        visited = set()
        queue = [adv_label]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for neighbor in list(G.successors(node)) + list(G.predecessors(node)):
                if neighbor not in visited:
                    queue.append(neighbor)

        reachable = [n for n in visited if n != adv_label]
        blast_radii[adv_label] = reachable[:20]

    print(f"[blast] Computed blast radius for {len(blast_radii)} advisories")
    return blast_radii


def analyze_chokepoints(G: nx.DiGraph) -> dict[str, float]:
    centrality = nx.betweenness_centrality(G, normalized=True)
    filtered = {k: v for k, v in centrality.items() if v > 0}
    sorted_c = sorted(filtered.items(), key=lambda x: -x[1])[:15]
    if sorted_c:
        print(f"[chokepoint] Top: {sorted_c[0][0]} ({sorted_c[0][1]:.4f})")
    else:
        print("[chokepoint] Top: N/A (0)")
    return dict(sorted_c)


def analyze_advisory_patterns(
    G: nx.DiGraph,
    node_data: dict[str, dict[str, Any]],
) -> dict[str, int]:
    package_advisory_count: dict[str, int] = {}

    for node in G.nodes():
        if node_data.get(node, {}).get("type") != "package":
            continue
        count = 0
        for src, _, d in G.in_edges(node, data=True):
            if d.get("label") == "affects" and node_data.get(src, {}).get("type") == "advisory":
                count += 1
        if count > 0:
            package_advisory_count[node] = count

    sorted_pkgs = sorted(package_advisory_count.items(), key=lambda x: -x[1])[:10]
    print(f"[patterns] Most-advised: {sorted_pkgs[0][0] if sorted_pkgs else 'N/A'} ({sorted_pkgs[0][1] if sorted_pkgs else 0})")
    return dict(sorted_pkgs)


def analyze_ecosystem_communities(
    G: nx.DiGraph,
    node_data: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    undirected = G.to_undirected()
    communities_gen = nx.community.label_propagation_communities(undirected)
    communities: list[dict[str, Any]] = []

    for comm in communities_gen:
        members = list(comm)
        if len(members) < 2:
            continue
        ecosystems: dict[str, int] = {}
        types: dict[str, int] = {}
        for node in members:
            nd = node_data.get(node, {})
            eco = nd.get("ecosystem", "unknown")
            ecosystems[eco] = ecosystems.get(eco, 0) + 1
            t = nd.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        communities.append({
            "size": len(members),
            "ecosystems": ecosystems,
            "types": types,
            "members": members[:10],
        })

    communities.sort(key=lambda c: -c["size"])
    print(f"[communities] Detected {len(communities)} communities")
    return communities


def print_results(
    advisories: list[AdvisoryRecord],
    blast_radii: dict[str, list[str]],
    chokepoints: dict[str, float],
    pkg_advisory_counts: dict[str, int],
    communities: list[dict[str, Any]],
    inferences: list[tuple[str, str, str]],
    G: nx.DiGraph,
) -> None:
    print("\n" + "=" * 70)
    print("DEPENDENCY SECURITY SCANNER — RESULTS (NetworkX)")
    print("=" * 70)

    print(f"\n{'─' * 70}")
    print(f"  Advisories processed: {len(advisories)}")
    severities: dict[str, int] = {}
    for a in advisories:
        severities[a.severity] = severities.get(a.severity, 0) + 1
    for sev in ["CRITICAL", "HIGH", "MODERATE", "LOW"]:
        if sev in severities:
            print(f"    {sev}: {severities[sev]}")

    print(f"\n{'─' * 70}")
    print("  BLAST RADIUS (critical advisories)")
    print(f"{'─' * 70}")
    for adv_id, reachable in blast_radii.items():
        print(f"  {adv_id}:")
        if reachable:
            print(f"    Reaches {len(reachable)} packages: {', '.join(reachable[:8])}")
        else:
            print("    No reachable packages")

    print(f"\n{'─' * 70}")
    print("  DEPENDENCY CHOKEPOINTS (betweenness centrality)")
    print(f"{'─' * 70}")
    for pkg, score in chokepoints.items():
        print(f"    {pkg:<40s} {score:.4f}")

    print(f"\n{'─' * 70}")
    print("  PACKAGES WITH MOST ADVISORIES")
    print(f"{'─' * 70}")
    for pkg, count in pkg_advisory_counts.items():
        print(f"    {pkg:<40s} {count} advisories")

    print(f"\n{'─' * 70}")
    print("  ECOSYSTEM COMMUNITIES (vulnerability clusters)")
    print(f"{'─' * 70}")
    for i, comm in enumerate(communities[:6]):
        ecos = ", ".join(f"{k}={v}" for k, v in sorted(comm["ecosystems"].items()))
        types = ", ".join(f"{k}={v}" for k, v in sorted(comm["types"].items()))
        print(f"  Community {i + 1} (size={comm['size']}):")
        print(f"    Ecosystems: {ecos or 'mixed'}")
        print(f"    Node types: {types}")
        print(f"    Members: {', '.join(str(m) for m in comm['members'][:8])}")

    print(f"\n{'─' * 70}")
    print("  TRANSITIVE INFERENCES")
    print(f"{'─' * 70}")
    print(f"    Total inferred edges: {len(inferences)}")
    for src, tgt, label in inferences[:10]:
        print(f"    {src} --[{label}]--> {tgt}")

    print(f"\n{'─' * 70}")
    print("  COMPARISON WITH HYPER3 APPROACH")
    print(f"{'─' * 70}")
    print("  NetworkX approach:")
    print("    - Manual BFS for blast radius vs Hyper3 spreading activation")
    print("    - Manual transitive closure vs Hyper3 TransitiveRule engine")
    print("    - label_propagation_communities() vs Hyper3 CommunityDetector")
    print("    - betweenness_centrality() on undirected projection vs")
    print("      Hyper3 centrality() with inverted-weight semantics")
    print("    - No semantic edge labels; all metadata stored in node_data dict")
    print("    - No built-in evolution, provenance, or overlay capabilities")
    print("    - Simpler setup but less expressive relationship modeling")
    print()
    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"{'=' * 70}\n")


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Fetch GitHub Advisories")
    print("=" * 70)
    raw = fetch_advisories(per_page=50)

    print(f"\n{'=' * 70}")
    print("SECTION 2: Parse Advisories")
    print(f"{'=' * 70}")
    advisories = parse_advisories(raw)

    print(f"\n{'=' * 70}")
    print("SECTION 3: Fetch PyPI Metadata")
    print(f"{'=' * 70}")
    unique_packages: set[str] = set()
    for adv in advisories:
        for pkg in adv.packages:
            if pkg.get("ecosystem", "").lower() in ("pip", "pypi"):
                unique_packages.add(pkg["name"])

    pypi_packages: dict[str, PackageRecord] = {}
    for pkg_name in sorted(unique_packages)[:30]:
        result = fetch_pypi_metadata(pkg_name)
        if result is not None:
            pypi_packages[pkg_name] = result

    print(f"\n{'=' * 70}")
    print("SECTION 4: Build NetworkX Graph")
    print(f"{'=' * 70}")
    G, node_data = build_graph(advisories, pypi_packages)

    print(f"\n{'=' * 70}")
    print("SECTION 5: Transitive Dependency Analysis")
    print(f"{'=' * 70}")
    inferences = analyze_transitive_dependencies(G, node_data)

    print(f"\n{'=' * 70}")
    print("SECTION 6: Blast Radius (BFS from critical advisories)")
    print(f"{'=' * 70}")
    blast_radii = analyze_blast_radius(G, node_data, advisories)

    print(f"\n{'=' * 70}")
    print("SECTION 7: Chokepoint Detection (betweenness centrality)")
    print(f"{'=' * 70}")
    chokepoints = analyze_chokepoints(G)

    print(f"\n{'=' * 70}")
    print("SECTION 8: Advisory Pattern Analysis")
    print(f"{'=' * 70}")
    pkg_patterns = analyze_advisory_patterns(G, node_data)

    print(f"\n{'=' * 70}")
    print("SECTION 9: Ecosystem Community Detection")
    print(f"{'=' * 70}")
    communities = analyze_ecosystem_communities(G, node_data)

    print_results(
        advisories=advisories,
        blast_radii=blast_radii,
        chokepoints=chokepoints,
        pkg_advisory_counts=pkg_patterns,
        communities=communities,
        inferences=inferences,
        G=G,
    )


if __name__ == "__main__":
    main()
