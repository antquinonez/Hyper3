"""
Building a Knowledge Graph from Security Incident Reports
==========================================================

Demonstrates extracting structured knowledge from unstructured security
incident text using Hyper3's RegexExtractor, then building and querying
a knowledge graph. Honest about what regex-based extraction catches versus
what it misses in domain-specific text, and shows the pluggable LLMProvider
interface for upgrading to a real NER pipeline.

Run with:
    .venv/bin/python examples/showcase/retrieval/text_enrichment/text_enrichment.py
"""

from __future__ import annotations

import re
from collections import Counter

from hyper3 import HypergraphMemory, LLMProvider

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


class SecurityNERProvider(LLMProvider):
    """Mock security-focused NER provider.

    Demonstrates the LLMProvider interface. In production, replace
    complete() with calls to a real NER service or fine-tuned model
    (e.g., spaCy custom NER, HuggingFace token classifier, OpenAI).
    """

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

    def complete(self, prompt: str) -> str:
        lines = ['{"entities": [']
        entities: list[str] = []
        for indicator, entries in self.INDICATOR_MAP.items():
            if indicator in prompt:
                for label, etype in entries:
                    entities.append(f'  {{"label": "{label}", "type": "{etype}"}}')
        lines.append(",\n".join(entities))
        lines.append('], "relations": []}')
        return "\n".join(lines)


def main():
    mem = HypergraphMemory(evolve_interval=0)

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
    results = mem.ingest_batch(REPORTS, extract=True, deduplicate=True)
    total_entities = sum(len(r.entities) for r in results)
    total_relations = sum(len(r.relations) for r in results)
    print(f"  Processed {len(REPORTS)} reports")
    print(f"  Extracted {total_entities} entity mentions ({total_relations} relations)")
    print(f"  Graph: {mem.size[0]} unique nodes, {mem.size[1]} edges")
    print()

    print("  Sample extracted relations:")
    shown = 0
    for r in results:
        for rel in r.relations:
            if shown >= 8:
                break
            print(f"    {rel.source_label} --[{rel.relation_label}]--> {rel.target_label}")
            shown += 1
        if shown >= 8:
            break
    print()

    print("=" * 70)
    print("SECTION 3: What RegexExtractor Caught vs Missed")
    print("=" * 70)

    regex_entity_labels: set[str] = set()
    for r in results:
        for e in r.entities:
            regex_entity_labels.add(e.label)

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
                mem.ensure(value, data={"type": category, "source": "manual_regex"})

        ip_addrs = indicators.get("ip_address", [])
        cves = indicators.get("cve_id", [])
        domains = indicators.get("domain", [])
        techniques = indicators.get("mitre_technique", [])
        hashes = indicators.get("sha256_hash", [])

        for ip in ip_addrs:
            for domain in domains:
                mem.link(ip, domain, label="communicated_with")
            for cve in cves:
                mem.link(ip, cve, label="exploited_via")

        for technique in techniques:
            for cve in cves:
                mem.link(technique, cve, label="maps_to")

        for h in hashes:
            for fp in indicators.get("file_path_windows", []) + indicators.get("file_path_unix", []):
                mem.link(h, fp, label="found_at")

    print(f"  Graph after manual enrichment: {mem.size[0]} nodes, {mem.size[1]} edges")
    print()

    print("=" * 70)
    print("SECTION 5: Querying the Security Knowledge Graph")
    print("=" * 70)

    target_nodes = ["CVE-2024-3094", "10.0.1.50", "T1059.001"]
    for concept in target_nodes:
        recalled = mem.recall(concept, max_depth=2)
        if recalled:
            labels = [n.label for n in recalled[:8]]
            print(f"  recall('{concept}', max_depth=2) -> {len(recalled)} nodes")
            print(f"    Neighbors: {labels}")
        else:
            print(f"  recall('{concept}') -> not found (node not in graph)")
    print()

    causes_edges = mem.pattern_match(edge_label="causes")
    print(f"  'causes' relationships ({len(causes_edges)}):")
    for match in causes_edges[:5]:
        src_labels = match.source_labels
        tgt_labels = match.target_labels
        if src_labels and tgt_labels:
            print(f"    {src_labels[0]} causes {tgt_labels[0]}")
    print()

    exploited_edges = mem.pattern_match(edge_label="exploited_via")
    print(f"  'exploited_via' relationships ({len(exploited_edges)}):")
    for match in exploited_edges[:5]:
        src_labels = match.source_labels
        tgt_labels = match.target_labels
        if src_labels and tgt_labels:
            print(f"    {src_labels[0]} exploited_via {tgt_labels[0]}")
    print()

    print("=" * 70)
    print("SECTION 6: Pluggable LLMProvider for Richer Extraction")
    print("=" * 70)

    mem_llm = HypergraphMemory(evolve_interval=0)
    mem_llm.set_llm_provider(SecurityNERProvider())

    sample_reports = REPORTS[:3]
    llm_results = mem_llm.ingest_batch(sample_reports, extract=True, deduplicate=True)
    print(f"  Custom provider extracted from {len(sample_reports)} reports:")
    for i, r in enumerate(llm_results):
        entities = [(e.label, e.entity_type) for e in r.entities]
        print(f"    Report {i+1}: {entities}")
    print()
    print("  The LLMProvider.complete() interface lets you plug in any NER")
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
    print("    Implement LLMProvider with a real NER model for security text.")
    print("    Combine both: regex for general patterns + custom for IOCs.")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Final graph: {stats.nodes} nodes, {stats.edges} edges")
    print(f"  Connected components: {stats.components}")
    print(f"  Has cycles: {stats.cycles}")
    print(f"  Incident reports processed: {len(REPORTS)}")
    print(f"  Entity types discovered: {len(indicator_values)} categories")
    print()


if __name__ == "__main__":
    main()
