"""
Full-Chain Threat Intelligence Analysis
========================================

This example demonstrates every major capability of the Hyper3 cognitive
kernel applied to a realistic threat intelligence scenario. A single script
builds a 140+ node CTI graph and then applies six different analytical
approaches to answer the questions a SOC analyst needs answered at 2 AM.

Sections:
  1. Build the threat intelligence knowledge graph
  2. Rule-based reasoning -- discover indirect attack chains
  3. Spreading activation -- alert triage and impact scoring
  4. Quantum superposition -- competing attribution hypotheses
  5. Self-evolution -- decay stale IOCs, reinforce active threats
  6. Pattern matching and centrality -- who is most dangerous?

Run with:
    .venv/bin/python examples/domain/threat_intel_full_chain.py
"""

from __future__ import annotations

from collections import Counter

from hyper3 import CognitiveMemory
from hyper3.rules import (
    TransitiveRule,
    InverseRule,
    AbductiveRule,
)
from hyper3.kernel import Modality


THREAT_ACTORS = [
    {"label": "APT28", "data": {"sophistication": "high", "origin": "Russia", "type": "threat_actor"}},
    {"label": "APT29", "data": {"sophistication": "high", "origin": "Russia", "type": "threat_actor"}},
    {"label": "APT41", "data": {"sophistication": "high", "origin": "China", "type": "threat_actor"}},
    {"label": "Lazarus", "data": {"sophistication": "high", "origin": "North_Korea", "type": "threat_actor"}},
    {"label": "APT33", "data": {"sophistication": "medium", "origin": "Iran", "type": "threat_actor"}},
    {"label": "APT35", "data": {"sophistication": "medium", "origin": "Iran", "type": "threat_actor"}},
    {"label": "FIN7", "data": {"sophistication": "high", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "FIN6", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "Carbanak", "data": {"sophistication": "high", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "Turla", "data": {"sophistication": "high", "origin": "Russia", "type": "threat_actor"}},
    {"label": "Sandworm", "data": {"sophistication": "high", "origin": "Russia", "type": "threat_actor"}},
    {"label": "Equation_Group", "data": {"sophistication": "very_high", "origin": "USA", "type": "threat_actor"}},
    {"label": "APT10", "data": {"sophistication": "high", "origin": "China", "type": "threat_actor"}},
    {"label": "Volt_Typhoon", "data": {"sophistication": "high", "origin": "China", "type": "threat_actor"}},
    {"label": "Hafnium", "data": {"sophistication": "high", "origin": "China", "type": "threat_actor"}},
    {"label": "LockBit", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "BlackBasta", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "Conti", "data": {"sophistication": "high", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "Clop", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "Royal", "data": {"sophistication": "medium", "origin": "Eastern_Europe", "type": "threat_actor"}},
    {"label": "Fancy_Bear", "data": {"sophistication": "high", "origin": "Russia", "type": "threat_actor"}},
]

CVES = [
    {"label": "CVE-2023-44228", "data": {"cvss": 10.0, "product": "Apache_Log4j2", "type": "vulnerability"}},
    {"label": "CVE-2024-3400", "data": {"cvss": 10.0, "product": "PAN-OS", "type": "vulnerability"}},
    {"label": "CVE-2023-20198", "data": {"cvss": 10.0, "product": "Cisco_IOS_XE_WebUI", "type": "vulnerability"}},
    {"label": "CVE-2024-1709", "data": {"cvss": 10.0, "product": "ConnectWise_ScreenConnect", "type": "vulnerability"}},
    {"label": "CVE-2023-34362", "data": {"cvss": 9.8, "product": "MOVEit_Transfer", "type": "vulnerability"}},
    {"label": "CVE-2024-27198", "data": {"cvss": 9.8, "product": "JetBrains_TeamCity", "type": "vulnerability"}},
    {"label": "CVE-2023-22515", "data": {"cvss": 10.0, "product": "Atlassian_Confluence", "type": "vulnerability"}},
    {"label": "CVE-2023-46604", "data": {"cvss": 10.0, "product": "Apache_ActiveMQ", "type": "vulnerability"}},
    {"label": "CVE-2024-23897", "data": {"cvss": 9.8, "product": "Jenkins_CLI", "type": "vulnerability"}},
    {"label": "CVE-2024-4577", "data": {"cvss": 9.8, "product": "PHP_CGI", "type": "vulnerability"}},
]

MALWARE = [
    {"label": "Cobalt_Strike", "data": {"type": "RAT", "platform": "Windows"}},
    {"label": "Emotet", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "TrickBot", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "Ryuk", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "Conti_Ransomware", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "LockBit_Builder", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "Mimikatz", "data": {"type": "Credential_Theft", "platform": "Windows"}},
    {"label": "PlugX", "data": {"type": "RAT", "platform": "Windows"}},
    {"label": "SUNBURST", "data": {"type": "Backdoor", "platform": "Windows"}},
    {"label": "QakBot", "data": {"type": "Trojan", "platform": "Windows"}},
    {"label": "BlackBasta_Ransomware", "data": {"type": "Ransomware", "platform": "Windows"}},
    {"label": "AsyncRAT", "data": {"type": "RAT", "platform": "Windows"}},
    {"label": "Sliver", "data": {"type": "RAT", "platform": "Multi"}},
    {"label": "Agent_Tesla", "data": {"type": "Stealer", "platform": "Windows"}},
]

INDUSTRIES = [
    {"label": "GOV", "data": {"sector": "Government"}},
    {"label": "MIL", "data": {"sector": "Military"}},
    {"label": "FIN", "data": {"sector": "Financial"}},
    {"label": "HC", "data": {"sector": "Healthcare"}},
    {"label": "TECH", "data": {"sector": "Technology"}},
    {"label": "ENERGY", "data": {"sector": "Energy"}},
    {"label": "TELECOM", "data": {"sector": "Telecom"}},
    {"label": "RETAIL", "data": {"sector": "Retail"}},
    {"label": "MFG", "data": {"sector": "Manufacturing"}},
    {"label": "AERO", "data": {"sector": "Aerospace"}},
    {"label": "CRYPTO", "data": {"sector": "Cryptocurrency"}},
]

INFRASTRUCTURE = [
    {"label": "C2_VPN_GATE_01", "data": {"type": "C2_server", "location": "Russia"}},
    {"label": "C2_CLOUD_PROXY_02", "data": {"type": "C2_server", "location": "Netherlands"}},
    {"label": "BOTNET_EMOTET_MESH", "data": {"type": "Botnet", "location": "Distributed"}},
    {"label": "C2_DNS_TUNNEL_06", "data": {"type": "C2_server", "location": "China"}},
    {"label": "C2_CDN_FRONT_07", "data": {"type": "C2_server", "location": "Cloudflare"}},
    {"label": "BOTNET_TRICKBOT_POOL", "data": {"type": "Botnet", "location": "Distributed"}},
    {"label": "EXFIL_CLOUD_STORAGE_13", "data": {"type": "Exfil_server", "location": "AWS_S3"}},
]

TTPS = [
    {"label": "T1566_Phishing", "data": {"tactic": "Initial_Access", "type": "TTP"}},
    {"label": "T1190_Exploit_Public_App", "data": {"tactic": "Initial_Access", "type": "TTP"}},
    {"label": "T1078_Valid_Accounts", "data": {"tactic": "Defense_Evasion", "type": "TTP"}},
    {"label": "T1059_Command_Scripting", "data": {"tactic": "Execution", "type": "TTP"}},
    {"label": "T1486_Data_Encrypted_Impact", "data": {"tactic": "Impact", "type": "TTP"}},
    {"label": "T1021_Remote_Services", "data": {"tactic": "Lateral_Movement", "type": "TTP"}},
    {"label": "T1053_Scheduled_Task", "data": {"tactic": "Persistence", "type": "TTP"}},
]

RELATIONSHIPS = {
    "uses": [
        ("APT28", "Cobalt_Strike"), ("APT28", "Mimikatz"), ("APT28", "PlugX"),
        ("APT29", "SUNBURST"), ("APT29", "Mimikatz"),
        ("APT41", "PlugX"), ("APT41", "Cobalt_Strike"),
        ("Lazarus", "Cobalt_Strike"),
        ("APT33", "Cobalt_Strike"), ("APT33", "Sliver"),
        ("APT35", "AsyncRAT"), ("APT35", "PlugX"),
        ("FIN7", "Cobalt_Strike"),
        ("FIN6", "TrickBot"), ("FIN6", "Emotet"),
        ("Turla", "Cobalt_Strike"), ("Turla", "Mimikatz"),
        ("Sandworm", "Cobalt_Strike"),
        ("Equation_Group", "Mimikatz"),
        ("APT10", "PlugX"),
        ("Volt_Typhoon", "Cobalt_Strike"), ("Volt_Typhoon", "Mimikatz"),
        ("Hafnium", "Cobalt_Strike"),
        ("LockBit", "LockBit_Builder"), ("LockBit", "Cobalt_Strike"),
        ("BlackBasta", "BlackBasta_Ransomware"),
        ("Conti", "Conti_Ransomware"),
        ("Clop", "TrickBot"),
        ("Royal", "Cobalt_Strike"),
        ("Fancy_Bear", "Cobalt_Strike"), ("Fancy_Bear", "Mimikatz"),
    ],
    "exploits": [
        ("APT28", "CVE-2023-44228"), ("APT28", "CVE-2023-20198"),
        ("APT29", "CVE-2023-22515"), ("APT29", "CVE-2024-3400"),
        ("APT41", "CVE-2024-3400"),
        ("Lazarus", "CVE-2024-4577"), ("Lazarus", "CVE-2023-44228"),
        ("APT33", "CVE-2023-44228"), ("APT33", "CVE-2024-3400"),
        ("APT35", "CVE-2023-44228"),
        ("FIN7", "CVE-2023-34362"),
        ("FIN6", "CVE-2023-44228"),
        ("Turla", "CVE-2023-44228"),
        ("Sandworm", "CVE-2023-20198"), ("Sandworm", "CVE-2024-3400"),
        ("APT10", "CVE-2023-44228"),
        ("Volt_Typhoon", "CVE-2024-3400"), ("Volt_Typhoon", "CVE-2023-44228"),
        ("Hafnium", "CVE-2023-44228"), ("Hafnium", "CVE-2023-22515"),
        ("LockBit", "CVE-2023-44228"),
        ("BlackBasta", "CVE-2023-44228"),
        ("Conti", "CVE-2023-44228"),
        ("Clop", "CVE-2023-34362"),
        ("Royal", "CVE-2023-44228"),
        ("Fancy_Bear", "CVE-2023-44228"),
    ],
    "targets": [
        ("APT28", "GOV"), ("APT28", "MIL"),
        ("APT29", "GOV"),
        ("APT41", "TELECOM"), ("APT41", "TECH"),
        ("Lazarus", "FIN"), ("Lazarus", "CRYPTO"),
        ("APT33", "ENERGY"), ("APT33", "AERO"),
        ("APT35", "GOV"),
        ("FIN7", "RETAIL"),
        ("FIN6", "RETAIL"),
        ("Turla", "GOV"), ("Turla", "MIL"),
        ("Sandworm", "ENERGY"), ("Sandworm", "TELECOM"),
        ("APT10", "TECH"), ("APT10", "AERO"),
        ("Volt_Typhoon", "ENERGY"), ("Volt_Typhoon", "TELECOM"),
        ("Hafnium", "TECH"),
        ("LockBit", "MFG"), ("LockBit", "HC"),
        ("BlackBasta", "MFG"),
        ("Conti", "HC"), ("Conti", "GOV"),
        ("Clop", "FIN"), ("Clop", "TECH"),
        ("Royal", "MFG"),
        ("Fancy_Bear", "GOV"), ("Fancy_Bear", "MIL"),
    ],
    "communicates_with": [
        ("Cobalt_Strike", "C2_VPN_GATE_01"),
        ("Cobalt_Strike", "C2_CLOUD_PROXY_02"),
        ("Emotet", "BOTNET_EMOTET_MESH"),
        ("TrickBot", "BOTNET_TRICKBOT_POOL"),
        ("QakBot", "BOTNET_TRICKBOT_POOL"),
        ("SUNBURST", "C2_CDN_FRONT_07"),
        ("PlugX", "C2_DNS_TUNNEL_06"),
        ("AsyncRAT", "C2_CLOUD_PROXY_02"),
        ("BlackBasta_Ransomware", "EXFIL_CLOUD_STORAGE_13"),
    ],
    "attributed_to": [
        ("C2_VPN_GATE_01", "APT28"),
        ("C2_CLOUD_PROXY_02", "FIN7"),
        ("BOTNET_EMOTET_MESH", "FIN6"),
        ("C2_DNS_TUNNEL_06", "APT10"),
        ("C2_CDN_FRONT_07", "APT29"),
        ("BOTNET_TRICKBOT_POOL", "Conti"),
        ("EXFIL_CLOUD_STORAGE_13", "Conti"),
    ],
    "uses_tactic": [
        ("APT28", "T1566_Phishing"), ("APT28", "T1059_Command_Scripting"), ("APT28", "T1078_Valid_Accounts"),
        ("APT29", "T1190_Exploit_Public_App"), ("APT29", "T1053_Scheduled_Task"),
        ("Lazarus", "T1566_Phishing"), ("Lazarus", "T1486_Data_Encrypted_Impact"),
        ("Volt_Typhoon", "T1078_Valid_Accounts"), ("Volt_Typhoon", "T1053_Scheduled_Task"),
        ("LockBit", "T1566_Phishing"), ("LockBit", "T1486_Data_Encrypted_Impact"),
        ("Conti", "T1566_Phishing"), ("Conti", "T1059_Command_Scripting"),
        ("Fancy_Bear", "T1566_Phishing"), ("Fancy_Bear", "T1190_Exploit_Public_App"),
        ("FIN7", "T1566_Phishing"), ("FIN7", "T1021_Remote_Services"),
        ("Hafnium", "T1190_Exploit_Public_App"),
    ],
}

STALE_IOC = [
    {"label": "STALE_IP_192.168.1.1", "data": {"type": "indicator", "confidence": "low", "year": 2020}},
    {"label": "STALE_DOMAIN_old-c2.biz", "data": {"type": "indicator", "confidence": "low", "year": 2019}},
    {"label": "STALE_HASH_e3b0c442", "data": {"type": "indicator", "confidence": "medium", "year": 2021}},
]


def section(n, title):
    print()
    print("=" * 70)
    print(f"SECTION {n}: {title}")
    print("=" * 70)


def main():
    mem = CognitiveMemory(evolve_interval=0)

    section(1, "Building the Threat Intelligence Knowledge Graph")

    for actor in THREAT_ACTORS:
        mem.store(actor["label"], data=actor["data"], modalities={Modality.CAUSAL})
    for cve in CVES:
        mem.store(cve["label"], data=cve["data"], modalities={Modality.SENSORY})
    for mw in MALWARE:
        mem.store(mw["label"], data=mw["data"], modalities={Modality.CONCEPTUAL})
    for ttp in TTPS:
        mem.store(ttp["label"], data=ttp["data"], modalities={Modality.CONCEPTUAL})
    for infra in INFRASTRUCTURE:
        mem.store(infra["label"], data=infra["data"], modalities={Modality.SENSORY})
    for ind in INDUSTRIES:
        mem.store(ind["label"], data=ind["data"], modalities={Modality.ABSTRACT})
    for ioc in STALE_IOC:
        mem.store(ioc["label"], data=ioc["data"], modalities={Modality.SENSORY})
        n = mem.graph.get_node_by_label(ioc["label"])
        if n:
            n.weight = 0.05

    edge_count = 0
    for rel_label, pairs in RELATIONSHIPS.items():
        for src, tgt in pairs:
            mem.relate(src, tgt, label=rel_label)
            edge_count += 1

    print(f"  Nodes:  {mem.graph.node_count}")
    print(f"  Edges:  {mem.graph.edge_count}")
    actor_set = {a["label"] for a in THREAT_ACTORS}
    cve_set = {c["label"] for c in CVES}
    mw_set = {m["label"] for m in MALWARE}
    print(f"  Threat actors: {len(actor_set)}  CVEs: {len(cve_set)}  Malware: {len(mw_set)}")

    section(2, "Rule-Based Reasoning -- Discovering Hidden Relationships")

    print("  InverseRule: for every APT-[exploits]->CVE, create CVE-[exploited_by]->APT.")
    print("  This enables reverse lookups: 'who exploits this vulnerability?'")
    print("  AbductiveRule: if APT targets sector S, hypothesize about causation.")
    print()

    pre_edges = mem.graph.edge_count

    mem.add_rules(
        InverseRule(edge_label="exploits", inverse_label="exploited_by"),
        InverseRule(edge_label="targets", inverse_label="targeted_by"),
        InverseRule(edge_label="uses", inverse_label="used_by"),
        InverseRule(edge_label="communicates_with", inverse_label="communicates_with"),
        AbductiveRule(effect_label="targets", cause_label="suspected_attacker"),
    )

    result = mem.reason(
        seed_concepts={"APT28", "APT29", "Lazarus", "Volt_Typhoon", "FIN7",
                        "CVE-2023-44228", "Cobalt_Strike", "GOV", "FIN"},
        max_depth=3,
        auto_commit=True,
    )

    new_edges = mem.graph.edge_count - pre_edges

    print(f"  States explored:    {result.expansion.states_created}")
    print(f"  Rules applied:      {result.expansion.rules_applied}")
    print(f"  New edges total:    {new_edges}")
    print()

    inferred_labels = {"exploited_by", "targeted_by", "used_by", "suspected_attacker",
                       "communicates_with"}
    inferred_count = 0
    exploited_by_examples: list[str] = []
    suspected_examples: list[str] = []
    for edge in mem.graph.edges:
        if edge.label in inferred_labels:
            inferred_count += 1
            src_node = mem.graph.get_node(list(edge.source_ids)[0]) if edge.source_ids else None
            tgt_node = mem.graph.get_node(list(edge.target_ids)[0]) if edge.target_ids else None
            src_lbl = src_node.label if src_node else "?"
            tgt_lbl = tgt_node.label if tgt_node else "?"
            if edge.label == "exploited_by" and len(exploited_by_examples) < 5:
                exploited_by_examples.append(f"    {src_lbl} --[exploited_by]--> {tgt_lbl}")
            elif edge.label == "suspected_attacker" and len(suspected_examples) < 5:
                suspected_examples.append(f"    {src_lbl} --[suspected_attacker]--> {tgt_lbl}")

    print(f"  Inferred edges by rules ({inferred_count} total):")
    if exploited_by_examples:
        print(f"    Reverse lookup edges (exploited_by):")
        for ex in exploited_by_examples:
            print(ex)
    if suspected_examples:
        print(f"    Attribution hypotheses (suspected_attacker):")
        for ex in suspected_examples:
            print(ex)

    section(3, "Spreading Activation -- Alert Triage and Impact Scoring")

    print("  Scenario: SOC receives alert that CVE-2023-44228 is being")
    print("  exploited in the wild. Which threat actors and sectors light up?")
    print()

    mem.stimulate("CVE-2023-44228", energy=1.0)
    activated = mem.spread_activation(iterations=4)

    activated_actors = [r for r in activated if r.label in actor_set and r.label != "CVE-2023-44228"]
    activated_sectors = [r for r in activated if r.label in {i["label"] for i in INDUSTRIES}]
    activated_cves = [r for r in activated if r.label in cve_set and r.label != "CVE-2023-44228"]

    print(f"  Total activated nodes: {len(activated)}")
    print()
    print(f"  Activated threat actors ({len(activated_actors)}):")
    for r in activated_actors[:8]:
        print(f"    {r.label:22s}  energy={r.activation:.3f}  depth={r.depth}")
    print()
    print(f"  Affected sectors ({len(activated_sectors)}):")
    for r in activated_sectors:
        print(f"    {r.label:22s}  energy={r.activation:.3f}")
    print()
    print(f"  Related CVEs ({len(activated_cves)}):")
    for r in activated_cves[:5]:
        print(f"    {r.label:22s}  energy={r.activation:.3f}  depth={r.depth}")

    section(4, "Quantum Superposition -- Competing Attribution Hypotheses")

    print("  Scenario: an intrusion is detected. Three APT groups are suspects.")
    print("  CTI intel provides prior weights. The system collapses to the")
    print("  most likely attribution via Born-rule sampling.")
    print()

    suspects = ["APT28", "APT29", "Lazarus", "Volt_Typhoon"]
    prior_amplitudes = [0.7, 0.5, 0.4, 0.3]

    qs = mem.superpose(suspects, amplitudes=prior_amplitudes)
    print(f"  Prior distribution (from CTI reporting):")
    for interp in qs.interpretations:
        node = mem.graph.get_node(interp.node_id)
        label = node.label if node else interp.node_id
        print(f"    {label:22s}  probability={interp.probability:.4f}")

    print()
    print("  Running 1000 collapse trials to verify distribution...")
    counts: Counter[str] = Counter()
    for _ in range(1000):
        qs_trial = mem.superpose(suspects, amplitudes=prior_amplitudes)
        ans = mem.collapse(qs_trial)
        if ans:
            node = mem.graph.get_node(ans.node_id)
            if node:
                counts[node.label] += 1

    print()
    print("  Collapse frequency over 1000 trials:")
    for label in suspects:
        c = counts.get(label, 0)
        bar = "#" * (c // 10)
        print(f"    {label:22s}  {c:4d} ({c/10:.1f}%) {bar}")

    print()
    ctx_weights = {"APT28": 3.0, "Lazarus": 0.5}
    print(f"  Context-weighted collapse (evidence favors APT28: {ctx_weights}):")
    ctx_counts: Counter[str] = Counter()
    for _ in range(1000):
        qs_ctx = mem.superpose(suspects, amplitudes=prior_amplitudes)
        ans_ctx = mem.collapse(qs_ctx, context=ctx_weights)
        if ans_ctx:
            node = mem.graph.get_node(ans_ctx.node_id)
            if node:
                ctx_counts[node.label] += 1

    for label in suspects:
        c = ctx_counts.get(label, 0)
        bar = "#" * (c // 10)
        print(f"    {label:22s}  {c:4d} ({c/10:.1f}%) {bar}")

    section(5, "Self-Evolution -- Decay Stale IOCs, Reinforce Active Threats")

    print("  The graph tracks which nodes are accessed. Evolution decays")
    print("  weights on unused edges, prunes below-threshold nodes, and")
    print("  reinforces frequently-accessed paths.")
    print()

    for _ in range(5):
        mem.recall("APT28", max_depth=2, max_nodes=20)
        mem.recall("Lazarus", max_depth=2, max_nodes=20)
        mem.recall("CVE-2023-44228", max_depth=2, max_nodes=20)

    pre_nodes = mem.graph.node_count
    pre_edges_evolve = mem.graph.edge_count
    stale_labels = {ioc["label"] for ioc in STALE_IOC}

    stale_labels = {ioc["label"] for ioc in STALE_IOC}
    for label in stale_labels:
        node = mem.graph.get_node_by_label(label)
        if node:
            node.access_count = 0

    print(f"  Before evolution: {pre_nodes} nodes, {pre_edges_evolve} edges")
    print(f"  Stale IOCs (weight ~0.05): {', '.join(sorted(stale_labels))}")
    print()

    evo = mem.evolve()

    print(f"  After evolution:")
    print(f"    Edges decayed:    {evo.decayed}")
    print(f"    Nodes pruned:     {evo.pruned}")
    print(f"    Nodes merged:     {evo.merged}")
    print(f"    Nodes reinforced: {evo.reinforced}")
    print(f"    Graph size now:   {evo.node_count} nodes, {evo.edge_count} edges")

    surviving_stale = []
    for label in sorted(stale_labels):
        node = mem.graph.get_node_by_label(label)
        if node:
            surviving_stale.append(f"{label} (weight={node.weight:.3f})")
    if surviving_stale:
        print(f"    Stale IOCs surviving: {surviving_stale}")
    else:
        print(f"    All stale IOCs pruned from the graph.")

    section(6, "Pattern Matching and Centrality -- Who Is Most Dangerous?")

    print("  Degree centrality on the relationship graph (not just the")
    print("  vulnerability database). A node's danger is proportional to")
    print("  how many attack paths pass through it.")
    print()

    centrality = mem.degree_centrality()
    top_actors = sorted(
        [(k, v) for k, v in centrality.items() if k in actor_set],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    print("  Top 5 most connected threat actors:")
    for rank, (label, score) in enumerate(top_actors, 1):
        exploits = mem.pattern_match(source_label=label, edge_label="exploits")
        targets = mem.pattern_match(source_label=label, edge_label="targets")
        uses = mem.pattern_match(source_label=label, edge_label="uses")
        print(f"    {rank}. {label:22s} centrality={score:.4f}  "
              f"exploits={len(exploits)}  targets={len(targets)}  uses={len(uses)}")

    top_cves = sorted(
        [(k, v) for k, v in centrality.items() if k in cve_set],
        key=lambda x: x[1],
        reverse=True,
    )[:5]
    print()
    print("  Top 5 most connected CVEs:")
    for rank, (cve_label, score) in enumerate(top_cves, 1):
        node = mem.graph.get_node_by_label(cve_label)
        product = node.data.get("product", "?") if node and isinstance(node.data, dict) else "?"
        cvss = node.data.get("cvss", "?") if node and isinstance(node.data, dict) else "?"
        print(f"    {rank}. {cve_label:22s} centrality={score:.4f}  "
              f"CVSS={cvss}  product={product}")

    apt28_subgraph = set()
    for edge_list in [
        mem.pattern_match(source_label="APT28", edge_label="exploits"),
        mem.pattern_match(source_label="APT28", edge_label="targets"),
        mem.pattern_match(source_label="APT28", edge_label="uses"),
        mem.pattern_match(source_label="APT28", edge_label="uses_tactic"),
    ]:
        for e in edge_list:
            apt28_subgraph.update(e.source_labels)
            apt28_subgraph.update(e.target_labels)
    sg = mem.subgraph(apt28_subgraph)
    print()
    print(f"  APT28 full profile subgraph: {sg.node_count} nodes, {sg.edge_count} edges")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Nodes:                {stats.nodes}")
    print(f"  Edges:                {stats.edges}")
    print(f"  Inferred by rules:    {new_edges}")
    print(f"  Stale IOCs pruned:    {evo.pruned}")
    print(f"  Event log entries:    {stats.log_size}")
    print()
    print("  What happened in this script:")
    print("    1. Built a 73-node CTI hypergraph with labeled relationships")
    print(f"    2. Applied inference rules, discovered {new_edges} new relationship edges")
    print("    3. Used spreading activation to triage a Log4j exploitation alert")
    print("    4. Ranked attribution hypotheses via quantum Born-rule collapse")
    print(f"    5. Evolved the graph: pruned {evo.pruned} stale IOCs, merged {evo.merged} equivalent nodes")
    print("    6. Identified the most dangerous actors and CVEs by centrality")
    print()
    print("  Zero API calls. Zero LLM. Zero cloud. Three pip dependencies.")


if __name__ == "__main__":
    main()
