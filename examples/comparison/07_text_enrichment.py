"""
Building a Knowledge Graph from Security Incident Reports (reimplementation)
=============================================================================

Reimplements examples/intermediate/07_text_enrichment.py using only
re, collections, and networkx. Same data, same outputs, no Hyper3.

Run with:
    .venv/bin/python examples/comparison/07_text_enrichment.py
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

import networkx as nx


REPORTS: list[str] = [
    (
        "On 2025-01-15 the threat actor used CVE-2024-3094 to compromise the "
        "build server at 10.0.1.50. The attacker exploited a supply chain "
        "vulnerability in the compression library."
    ),
    (
        "Malicious payload 4a2b8c3d1e5f6a7b8c9d0e1f2a3b4c5d was delivered via "
        "phishing email from attacker@c2-domain.xyz. The malware communicates "
        "with 192.168.45.100 on port 4444 using technique T1059.001."
    ),
    (
        "The Cobalt Strike beacon at C:\\Windows\\Temp\\update.exe "
        "established persistence using technique T1053.005 Scheduled Task. "
        "The beacon causes a C2 channel to the domain evil-cdn.net."
    ),
    (
        "Credential harvesting was performed by Mimikatz extracting NTLM hashes "
        "from LSASS memory. The attacker used technique T1003.001 and moved "
        "laterally to the domain controller at 10.0.1.1."
    ),
    (
        "Data exfiltration was detected as 2.3 GB of compressed archives "
        "uploaded to cloud-storage.example.net. The exfiltration leads to "
        "regulatory notification requirements."
    ),
    (
        "The ransomware payload a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6 encrypted files "
        "in C:\\Users\\ and C:\\Shares\\. Ransom note demanded payment via "
        "bitcoin to wallet bc1qexample. Technique T1486 was used."
    ),
    (
        "Reconnaissance activity from 203.0.113.50 included port scanning against "
        "the web server farm. The scanning is associated with known threat group "
        "APT-29. OSINT reveals this IP is part of a known botnet."
    ),
    (
        "The web application firewall blocked an SQL injection attempt targeting "
        "the login endpoint at https://portal.corp.example.com/login. "
        "The attack used technique T1190 exploiting CVE-2024-1234."
    ),
    (
        "A compromised service account was used to query Active Directory for "
        "all domain admin accounts. This reconnaissance is part of technique "
        "T1087.002 and was followed by lateral movement to 10.0.2.25."
    ),
    (
        "The rootkit f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2 was found in "
        "/lib/modules/6.1.0/kernel trojan. It intercepts system calls "
        "and hides processes. Technique T1014 was identified."
    ),
    (
        "DNS tunneling was used to exfiltrate data through queries to "
        "tunnel.attacker-controlled.com. Each query contains encoded data "
        "in the subdomain. This is associated with technique T1071.004."
    ),
    (
        "The vulnerable Apache Struts server at 10.0.3.100 was exploited "
        "using CVE-2024-5678. The exploitation causes remote code execution "
        "and a web shell was deployed to /var/www/html/shell.php."
    ),
    (
        "Bluetooth exploitation tool BAdChapter targeted mobile devices in "
        "the executive lounge. The tool uses CVE-2024-9012 to bypass "
        "authentication. Technique T1200 was documented."
    ),
    (
        "Anomalous VPN logins from 198.51.100.23 were traced to compromised "
        "contractor credentials. The credentials were used to access the "
        "source code repository at git.corp.example.net."
    ),
    (
        "The incident response team contained the breach by isolating "
        "10.0.1.0/24 and revoking all compromised service accounts. "
        "Forensic imaging of disk 4a2b8c3d was completed. Recovery "
        "prevents further data loss."
    ),
    (
        "Cryptocurrency mining malware 9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b "
        "was found consuming 95 percent CPU on the CI server. The malware "
        "was delivered through a malicious npm package using technique "
        "T1059.007 JavaScript execution."
    ),
]


def extract_technical_indicators(text: str) -> dict[str, list[str]]:
    patterns = {
        "ip_address": r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b',
        "cve_id": r'\bCVE-\d{4}-\d{4,7}\b',
        "mitre_technique": r'\bT\d{4}(?:\.\d{3})?\b',
        "sha256_hash": r'\b[a-f0-9]{32,64}\b',
        "file_path_windows": r'\b[A-Z]:\\(?:[^\s<>:"|?*]+\\)*[^\s<>:"|?*]+\b',
        "file_path_unix": r'\b/(?:[^\s<>:"|?*]+/)*[^\s<>:"|?*]+\b',
        "domain": r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){2,}[a-z]{2,}\b',
        "url": r'\bhttps?://[^\s<>"]+\b',
        "email": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    }
    results: dict[str, list[str]] = {}
    for category, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            results[category] = matches
    return results


RELATION_PATTERNS = [
    (r'(\w[\w\s-]+?)\s+causes\s+(\w[\w\s-]+)', "causes"),
    (r'(\w[\w\s-]+?)\s+is\s+associated\s+with\s+(\w[\w\s-]+)', "associated_with"),
    (r'(\w[\w\s-]+?)\s+leads\s+to\s+(\w[\w\s-]+)', "leads_to"),
    (r'(\w[\w\s-]+?)\s+exploited\s+(\w[\w\s-]+)', "exploited"),
]


def regex_extract_entities_and_relations(text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    np_pattern = r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    raw_entities = re.findall(np_pattern, text)
    stop_words = {
        "The", "This", "A", "An", "In", "On", "At", "To", "For", "And",
        "Or", "But", "Not", "Is", "Was", "Were", "Been", "Have", "Has",
        "It", "Its", "From", "By", "With", "As", "Of", "Each", "All",
    }
    entities = [(e, "entity") for e in raw_entities if e not in stop_words and len(e) > 1]

    relations: list[tuple[str, str, str]] = []
    for pattern, label in RELATION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            src = m.group(1).strip()
            tgt = m.group(2).strip()
            if src and tgt:
                relations.append((src, tgt, label))

    return entities, relations


def deduplicate_entities(entities: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for label, etype in entities:
        key = label.lower()
        if key not in seen:
            seen.add(key)
            result.append((label, etype))
    return result


def deduplicate_relations(relations: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[tuple[str, str, str]] = []
    for src, tgt, label in relations:
        key = (src.lower(), tgt.lower(), label)
        if key not in seen:
            seen.add(key)
            result.append((src, tgt, label))
    return result


class SecurityNERProvider:
    INDICATOR_MAP: dict[str, list[tuple[str, str]]] = {
        "CVE-2024-3094": [("CVE-2024-3094", "vulnerability")],
        "CVE-2024-1234": [("CVE-2024-1234", "vulnerability")],
        "CVE-2024-5678": [("CVE-2024-5678", "vulnerability")],
        "CVE-2024-9012": [("CVE-2024-9012", "vulnerability")],
        "T1059.001": [("T1059.001", "mitre_technique")],
        "T1053.005": [("T1053.005", "mitre_technique")],
        "T1003.001": [("T1003.001", "mitre_technique")],
        "T1486": [("T1486", "mitre_technique")],
        "T1190": [("T1190", "mitre_technique")],
        "T1087.002": [("T1087.002", "mitre_technique")],
        "T1014": [("T1014", "mitre_technique")],
        "T1071.004": [("T1071.004", "mitre_technique")],
        "T1200": [("T1200", "mitre_technique")],
        "T1059.007": [("T1059.007", "mitre_technique")],
        "Mimikatz": [("Mimikatz", "tool")],
        "Cobalt Strike": [("Cobalt Strike", "tool")],
        "BAdChapter": [("BAdChapter", "tool")],
    }

    def complete(self, prompt: str) -> list[tuple[str, str]]:
        entities: list[tuple[str, str]] = []
        for indicator, entries in self.INDICATOR_MAP.items():
            if indicator in prompt:
                entities.extend(entries)
        return entities


def neighbors(G: nx.DiGraph, node: str, max_depth: int = 2) -> list[str]:
    visited: set[str] = {node}
    frontier: set[str] = {node}
    for _ in range(max_depth):
        next_frontier: set[str] = set()
        for n in frontier:
            for succ in G.successors(n):
                if succ not in visited:
                    next_frontier.add(succ)
                    visited.add(succ)
            for pred in G.predecessors(n):
                if pred not in visited:
                    next_frontier.add(pred)
                    visited.add(pred)
        frontier = next_frontier
    return list(visited - {node})


def edges_by_label(G: nx.DiGraph, label: str) -> list[tuple[str, str]]:
    return [(u, v) for u, v, d in G.edges(data=True) if d.get("label") == label]


def main():
    G = nx.DiGraph()

    print("=" * 70)
    print("SECTION 1: Security Incident Reports")
    print("=" * 70)
    print(f"  Loaded {len(REPORTS)} synthetic incident reports")
    for i, report in enumerate(REPORTS[:3], 1):
        print(f"  Report {i}: {report[:80]}...")
    print(f"  ... and {len(REPORTS) - 3} more")
    print()

    print("=" * 70)
    print("SECTION 2: Regex Extraction (Built-in)")
    print("=" * 70)

    all_entities: list[tuple[str, str]] = []
    all_relations: list[tuple[str, str, str]] = []
    per_report_results: list[dict] = []

    for report in REPORTS:
        entities, relations = regex_extract_entities_and_relations(report)
        entities = deduplicate_entities(entities)
        relations = deduplicate_relations(relations)
        all_entities.extend(entities)
        all_relations.extend(relations)
        per_report_results.append({"entities": entities, "relations": relations})

    all_entities = deduplicate_entities(all_entities)
    all_relations = deduplicate_relations(all_relations)

    total_entities = sum(len(r["entities"]) for r in per_report_results)
    total_relations = sum(len(r["relations"]) for r in per_report_results)

    for label, etype in all_entities:
        if label not in G:
            G.add_node(label, entity_type=etype, source="regex")

    for src, tgt, label in all_relations:
        if src not in G:
            G.add_node(src, entity_type="entity", source="regex")
        if tgt not in G:
            G.add_node(tgt, entity_type="entity", source="regex")
        G.add_edge(src, tgt, label=label)

    print(f"  Processed {len(REPORTS)} reports")
    print(f"  Extracted {total_entities} entity mentions ({total_relations} relations)")
    print(f"  Graph: {G.number_of_nodes()} unique nodes, {G.number_of_edges()} edges")
    print()

    print("  Sample extracted relations:")
    shown = 0
    for r in per_report_results:
        for src, tgt, label in r["relations"]:
            if shown >= 8:
                break
            print(f"    {src} --[{label}]--> {tgt}")
            shown += 1
        if shown >= 8:
            break
    print()

    print("=" * 70)
    print("SECTION 3: What RegexExtractor Caught vs Missed")
    print("=" * 70)

    regex_entity_labels: set[str] = set()
    for r in per_report_results:
        for label, _ in r["entities"]:
            regex_entity_labels.add(label)

    indicator_totals: Counter[str] = Counter()
    indicator_values: dict[str, set[str]] = {}
    for report in REPORTS:
        indicators = extract_technical_indicators(report)
        for category, values in indicators.items():
            indicator_totals[category] += len(values)
            indicator_values.setdefault(category, set()).update(values)

    print("  Technical indicators present in reports (manual regex):")
    for category, count in indicator_totals.most_common():
        unique = len(indicator_values.get(category, set()))
        print(f"    {category:25s}: {count:3d} occurrences ({unique} unique)")
    print()

    overlap_count = 0
    missed_examples: list[tuple[str, str]] = []
    for category, values in indicator_values.items():
        for v in values:
            if v in regex_entity_labels or any(v in label for label in regex_entity_labels):
                overlap_count += 1
            else:
                if len(missed_examples) < 10:
                    missed_examples.append((category, v))

    print(f"  Technical indicators caught by RegexExtractor: ~{overlap_count}")
    print(f"  Technical indicators missed: ~{sum(len(v) for v in indicator_values.values()) - overlap_count}")
    print()
    print("  Examples of MISSED indicators (regex cannot parse these):")
    for cat, val in missed_examples:
        print(f"    [{cat}] {val}")
    print()

    print("  What RegexExtractor DOES catch from these reports:")
    print("    - Capitalized noun phrases (Cobalt Strike, Mimikatz, Active Directory)")
    print("    - General relation patterns (X causes Y, X is associated with Y)")
    print("    - Quoted terms, appositions, list structures")
    print()
    print("  What it MISSES:")
    print("    - IP addresses, CVE IDs, MITRE technique IDs")
    print("    - File paths, SHA hashes, domain names")
    print("    - Domain-specific relations (X exploited Y, X communicated with Y)")
    print()

    print("=" * 70)
    print("SECTION 4: Manual Technical Indicator Extraction")
    print("=" * 70)
    print("  Using domain-specific regex to extract indicators that the")
    print("  built-in extractor misses, then adding them to the graph.")
    print()

    for report in REPORTS:
        indicators = extract_technical_indicators(report)
        for category, values in indicators.items():
            for value in values:
                if value not in G:
                    G.add_node(value, type=category, source="manual_regex")

        ip_addrs = indicators.get("ip_address", [])
        cves = indicators.get("cve_id", [])
        domains = indicators.get("domain", [])
        techniques = indicators.get("mitre_technique", [])
        hashes = indicators.get("sha256_hash", [])

        for ip in ip_addrs:
            for domain in domains:
                G.add_edge(ip, domain, label="communicated_with")
            for cve in cves:
                G.add_edge(ip, cve, label="exploited_via")

        for technique in techniques:
            for cve in cves:
                G.add_edge(technique, cve, label="maps_to")

        for h in hashes:
            for fp in indicators.get("file_path_windows", []) + indicators.get("file_path_unix", []):
                G.add_edge(h, fp, label="found_at")

    print(f"  Graph after manual enrichment: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print()

    print("=" * 70)
    print("SECTION 5: Querying the Security Knowledge Graph")
    print("=" * 70)

    target_nodes = ["CVE-2024-3094", "10.0.1.50", "T1059.001"]
    for concept in target_nodes:
        if concept in G:
            nbrs = neighbors(G, concept, max_depth=2)
            labels = nbrs[:8]
            print(f"  recall('{concept}', max_depth=2) -> {len(nbrs)} nodes")
            print(f"    Neighbors: {labels}")
        else:
            print(f"  recall('{concept}') -> not found (node not in graph)")
    print()

    causes = edges_by_label(G, "causes")
    print(f"  'causes' relationships ({len(causes)}):")
    for src, tgt in causes[:5]:
        print(f"    {src} causes {tgt}")
    print()

    exploited = edges_by_label(G, "exploited_via")
    print(f"  'exploited_via' relationships ({len(exploited)}):")
    for src, tgt in exploited[:5]:
        print(f"    {src} exploited_via {tgt}")
    print()

    print("=" * 70)
    print("SECTION 6: Pluggable Provider for Richer Extraction")
    print("=" * 70)

    provider = SecurityNERProvider()
    sample_reports = REPORTS[:3]
    for i, report in enumerate(sample_reports):
        entities = provider.complete(report)
        print(f"    Report {i+1}: {entities}")
    print()
    print("  The provider interface lets you plug in any NER")
    print("  backend (spaCy, HuggingFace, GPT-4) for domain-specific extraction")
    print("  without changing application code.")
    print()

    print("=" * 70)
    print("SECTION 7: Honest Assessment")
    print("=" * 70)
    print()
    print("  RegexExtractor (built-in):")
    print("    + Zero dependencies, works offline")
    print("    + Good at generic English relation patterns (causes, is_a, leads_to)")
    print("    + Catches noun phrases, quoted terms, appositions")
    print("    - Cannot parse structured identifiers (IPs, CVEs, hashes)")
    print("    - Misses domain-specific verbs (exploited, exfiltrated, persisted)")
    print("    - No coreference resolution beyond basic pronouns")
    print()
    print("  Production recommendation:")
    print("    Use RegexExtractor for prototyping and general text.")
    print("    Implement provider with a real NER model for security text.")
    print("    Combine both: regex for general patterns + custom for IOCs.")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    components = list(nx.weakly_connected_components(G))
    has_cycles = False
    try:
        if list(nx.simple_cycles(G)):
            has_cycles = True
    except Exception:
        pass
    print(f"  Final graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"  Connected components: {len(components)}")
    print(f"  Has cycles: {has_cycles}")
    print(f"  Incident reports processed: {len(REPORTS)}")
    print(f"  Entity types discovered: {len(indicator_values)} categories")
    print()


if __name__ == "__main__":
    main()
