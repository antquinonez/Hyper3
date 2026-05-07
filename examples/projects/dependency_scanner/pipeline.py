"""
Software Dependency Security Scanner Pipeline (Prefect + Hyper3)
import os
os.environ.setdefault("PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW", "ignore")
=================================================================

A production-grade data pipeline that:

1. Fetches reviewed security advisories from the GitHub Advisory Database API.
2. Enriches each vulnerable package with metadata from PyPI.
3. Builds a Hyper3 knowledge graph connecting advisories, packages, and
   their transitive dependencies.
4. Runs rule-based inference, spreading activation, centrality analysis,
   pattern matching, and community detection to surface vulnerability
   chains, blast radii, chokepoints, and ecosystem clusters.

Requirements:
    pip install prefect requests hyper3

Run:
    .venv/bin/python examples/projects/dependency_scanner/pipeline.py
"""

from __future__ import annotations
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import time
from dataclasses import dataclass, field
from typing import Any

import requests
from prefect import flow, task

from hyper3 import HypergraphMemory, top_k
from hyper3.rules import InverseRule, TransitiveRule


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


@task(retries=3, retry_delay_seconds=5)
def fetch_advisories(per_page: int = 50) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    url = f"{GITHUB_ADV_ENDPOINT}?type=reviewed&per_page={per_page}"
    logger.info("Fetching advisories from %s", url)

    resp = requests.get(url, headers=GITHUB_HEADERS, timeout=30)
    if resp.status_code == 403:
        logger.warning("GitHub rate limit hit — sleeping 60s")
        time.sleep(60)
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    logger.info("Received %d advisories", len(data))
    return data


@task(retries=2, retry_delay_seconds=3)
def fetch_pypi_metadata(package_name: str) -> PackageRecord | None:
    logger = logging.getLogger(__name__)
    url = PYPI_ENDPOINT.format(package=package_name)
    logger.info("Fetching PyPI metadata for %s", package_name)

    try:
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
        if resp.status_code == 404:
            logger.warning("Package %s not found on PyPI", package_name)
            return None
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("PyPI request failed for %s: %s", package_name, exc)
        return None

    body = resp.json()
    info = body.get("info", {})
    version = info.get("version", "unknown")
    requires_dist = info.get("requires_dist") or []
    time.sleep(0.25)
    return PackageRecord(name=package_name, version=version, requires_dist=requires_dist)


@task
def parse_advisories(raw: list[dict[str, Any]]) -> list[AdvisoryRecord]:
    logger = logging.getLogger(__name__)
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
            first_patched = vuln.get("first_patched_version")
            if isinstance(first_patched, dict) and first_patched.get("identifier"):
                patched.append(first_patched["identifier"])

        if ghsa_id and packages:
            records.append(AdvisoryRecord(
                ghsa_id=ghsa_id,
                cve_id=cve_id,
                summary=summary,
                severity=severity,
                packages=packages,
                patched_versions=patched,
            ))

    logger.info("Parsed %d actionable advisories", len(records))
    return records


@task
def build_knowledge_graph(
    advisories: list[AdvisoryRecord],
    pypi_packages: dict[str, PackageRecord],
) -> HypergraphMemory:
    logger = logging.getLogger(__name__)
    mem = HypergraphMemory(
        evolve_interval=0,
        rules=[
            TransitiveRule(edge_label="depends_on", new_label="depends_on"),
            InverseRule(edge_label="affects", inverse_label="affected_by"),
        ],
    )

    for adv in advisories:
        adv_label = adv.ghsa_id
        mem.add(adv_label, data={
            "type": "advisory",
            "cve_id": adv.cve_id,
            "severity": adv.severity,
            "summary": adv.summary[:200],
            "patched_versions": adv.patched_versions,
        })

        if adv.cve_id:
            mem.add(adv.cve_id, data={"type": "cve"})
            mem.link(adv.cve_id, adv_label, label="identified_as")

        for pkg_info in adv.packages:
            pkg_name = pkg_info["name"]
            ecosystem = pkg_info.get("ecosystem", "unknown")

            if pkg_name in pypi_packages:
                pypi = pypi_packages[pkg_name]
                mem.add(pkg_name, data={
                    "type": "package",
                    "version": pypi.version,
                    "ecosystem": ecosystem,
                })

                mem.link(adv_label, pkg_name, label="affects", weight={"CRITICAL": 10.0, "HIGH": 7.0, "MODERATE": 4.0, "LOW": 1.0}.get(adv.severity, 1.0))

                for patched in adv.patched_versions:
                    fixed_label = f"{pkg_name}=={patched}"
                    mem.add(fixed_label, data={
                        "type": "fixed_version",
                        "package": pkg_name,
                        "version": patched,
                    })
                    mem.link(adv_label, fixed_label, label="fixes")

                deps = _parse_requires_dist(pypi.requires_dist)
                for dep_name, extras in deps:
                    dep_label = dep_name.lower().replace("-", "_")
                    mem.ensure(dep_label, data={
                        "type": "dependency",
                        "extras": extras,
                        "ecosystem": "pypi",
                    })
                    mem.link(pkg_name, dep_label, label="depends_on")
            else:
                mem.add(pkg_name, data={
                    "type": "package",
                    "ecosystem": ecosystem,
                    "version": "unknown",
                })
                mem.link(adv_label, pkg_name, label="affects", weight={"CRITICAL": 10.0, "HIGH": 7.0, "MODERATE": 4.0, "LOW": 1.0}.get(adv.severity, 1.0))

    stats = mem.stats()
    logger.info(
        "Knowledge graph: %d nodes, %d edges",
        stats.nodes,
        stats.edges,
    )
    return mem


@task
def analyze_transitive_chains(mem: HypergraphMemory) -> int:
    logger = logging.getLogger(__name__)
    result = mem.reason(
        seed_concepts=set(),
        max_depth=3,
        exhaustive=True,
    )
    edges_produced = 0
    if result.expansion:
        edges_produced = result.expansion.edges_produced
    logger.info("Reasoning produced %d new edges", edges_produced)
    return edges_produced


@task
def analyze_blast_radius(
    mem: HypergraphMemory,
    advisories: list[AdvisoryRecord],
) -> dict[str, list[str]]:
    logger = logging.getLogger(__name__)
    critical = [a for a in advisories if a.severity in ("HIGH", "CRITICAL")]
    if not critical:
        critical = advisories[:3]

    blast_radii: dict[str, list[str]] = {}
    for adv in critical[:5]:
        adv_label = adv.ghsa_id
        try:
            mem.stimulate(adv_label, energy=1.0)
            activated = mem.spread_activation(iterations=5)
            reachable = [r.label for r in activated][:20]
            blast_radii[adv_label] = reachable
            mem.clear_activations()
        except Exception:
            blast_radii[adv_label] = []

    logger.info("Computed blast radius for %d critical advisories", len(blast_radii))
    return blast_radii


@task
def analyze_chokepoints(mem: HypergraphMemory) -> dict[str, float]:
    logger = logging.getLogger(__name__)
    centrality_map = mem.betweenness_centrality(top_k=15)
    top = {k: v for k, v in centrality_map.items() if v > 0}

    logger.info("Top chokepoint: %s (%.4f)", next(iter(top)) if top else "N/A", next(iter(top.values())) if top else 0.0)
    return top


@task
def analyze_advisory_patterns(mem: HypergraphMemory) -> dict[str, int]:
    logger = logging.getLogger(__name__)
    advisory_labels = set(mem.query_nodes(type="advisory"))
    packages = mem.query_nodes(type="package")
    package_advisory_count: dict[str, int] = {}

    for pkg in packages:
        advisory_neighbors = mem.neighbors(pkg, edge_label="affects", direction="in")
        count = len([n for n in advisory_neighbors if n in advisory_labels])
        if count > 0:
            package_advisory_count[pkg] = count

    sorted_pkgs = top_k(package_advisory_count, k=10)
    logger.info("Most-advised package: %s (%d advisories)", sorted_pkgs[0][0] if sorted_pkgs else "N/A", sorted_pkgs[0][1] if sorted_pkgs else 0)
    return dict(sorted_pkgs)


@task
def analyze_ecosystem_communities(mem: HypergraphMemory) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    try:
        result = mem.analyze.communities(method="label_propagation", seed=42)
    except Exception:
        logger.warning("Community detection failed; returning empty")
        return []

    communities: list[dict[str, Any]] = []
    for comm in result.communities:
        ecosystems: dict[str, int] = {}
        types: dict[str, int] = {}
        for member_label in comm.member_labels:
            node = mem.graph.get_node_by_label(member_label)
            if node:
                eco = node.data.get("ecosystem", "unknown")
                ecosystems[eco] = ecosystems.get(eco, 0) + 1
                t = node.data.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
        communities.append({
            "size": comm.size,
            "ecosystems": ecosystems,
            "types": types,
            "members": comm.member_labels[:10],
        })

    communities.sort(key=lambda c: -c["size"])
    logger.info("Detected %d communities", len(communities))
    return communities


def _parse_requires_dist(requires_dist: list[str]) -> list[tuple[str, list[str]]]:
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


def _print_results(
    advisories: list[AdvisoryRecord],
    blast_radii: dict[str, list[str]],
    chokepoints: dict[str, float],
    pkg_advisory_counts: dict[str, int],
    communities: list[dict[str, Any]],
    edges_produced: int,
) -> None:
    print("\n" + "=" * 70)
    print("DEPENDENCY SECURITY SCANNER — RESULTS")
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
        print(f"    Members: {', '.join(comm['members'][:8])}")

    print(f"\n{'─' * 70}")
    print("  TRANSITIVE INFERENCES")
    print(f"{'─' * 70}")
    print(f"    Total inferred edges: {edges_produced}")

    print(f"\n{'=' * 70}")
    print("  SCAN COMPLETE")
    print(f"{'=' * 70}\n")


@flow(name="dependency-security-scanner")
def dependency_security_scanner(
    per_page: int = 50,
) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting dependency security scanner pipeline")

    raw_advisories = fetch_advisories(per_page=per_page)
    advisories = parse_advisories(raw_advisories)

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

    mem = build_knowledge_graph(advisories, pypi_packages)

    desc = mem.describe()
    logger.info("Graph composition: %s", desc.node_types)

    edges_produced = analyze_transitive_chains(mem)
    blast_radii = analyze_blast_radius(mem, advisories)
    chokepoints = analyze_chokepoints(mem)
    pkg_patterns = analyze_advisory_patterns(mem)
    communities = analyze_ecosystem_communities(mem)

    _print_results(
        advisories=advisories,
        blast_radii=blast_radii,
        chokepoints=chokepoints,
        pkg_advisory_counts=pkg_patterns,
        communities=communities,
        edges_produced=edges_produced,
    )


def main(per_page: int = 50) -> None:
    raw_advisories = fetch_advisories.fn(per_page=per_page)
    advisories = parse_advisories.fn(raw_advisories)
    unique_packages: set[str] = set()
    for adv in advisories:
        for pkg in adv.packages:
            if pkg.get("ecosystem", "").lower() in ("pip", "pypi"):
                unique_packages.add(pkg["name"])
    pypi_packages: dict[str, PackageRecord] = {}
    for pkg_name in sorted(unique_packages)[:30]:
        result = fetch_pypi_metadata.fn(pkg_name)
        if result is not None:
            pypi_packages[pkg_name] = result
    mem = build_knowledge_graph.fn(advisories, pypi_packages)
    desc = mem.describe()
    print(f"\n  Graph composition: {desc.node_types}")
    edges_produced = analyze_transitive_chains.fn(mem)
    blast_radii = analyze_blast_radius.fn(mem, advisories)
    chokepoints = analyze_chokepoints.fn(mem)
    pkg_patterns = analyze_advisory_patterns.fn(mem)
    communities = analyze_ecosystem_communities.fn(mem)
    _print_results(
        advisories=advisories,
        blast_radii=blast_radii,
        chokepoints=chokepoints,
        pkg_advisory_counts=pkg_patterns,
        communities=communities,
        edges_produced=edges_produced,
    )


if __name__ == "__main__":
    main()
