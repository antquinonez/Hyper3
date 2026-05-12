"""
NetworkX-only equivalent of Hyper3's threat_intel_full_chain.py
================================================================
Implements all six analytical capabilities using only NetworkX and NumPy:
  1. Build the knowledge graph
  2. Rule-based inference (inverse + abductive)
  3. Spreading activation for alert triage
  4. Born-rule collapse for attribution ranking
  5. Self-evolution (decay, prune, merge)
  6. Centrality and pattern matching

Run with:
    .venv/bin/python examples/comparison/nx_threat_intel_full_chain.py
"""

from __future__ import annotations

import random
from collections import Counter

import networkx as nx
import numpy as np

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

RELATIONSHIPS: dict[str, list[tuple[str, str]]] = {
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


def section(n: int, title: str) -> None:
    print()
    print("=" * 70)
    print(f"SECTION {n}: {title}")
    print("=" * 70)


def apply_inverse_rule(G: nx.DiGraph, edge_label: str, inverse_label: str) -> int:
    added = 0
    for u, v, data in list(G.edges(data=True)):
        if data.get("label") == edge_label:
            if not G.has_edge(v, u) or G[v][u].get("label") != inverse_label:
                G.add_edge(v, u, label=inverse_label, weight=1.0, inferred=True)
                added += 1
    return added


def apply_abductive_rule(G: nx.DiGraph, effect_label: str, cause_label: str) -> int:
    added = 0
    for u, v, data in list(G.edges(data=True)):
        if data.get("label") == effect_label:
            cause_node = f"hypothesis:{u}"
            if not G.has_node(cause_node):
                G.add_node(cause_node, **{"type": "hypothesis", "source": u})
            if not G.has_edge(cause_node, v) or G[cause_node][v].get("label") != cause_label:
                G.add_edge(cause_node, v, label=cause_label, weight=1.0, inferred=True)
                added += 1
    return added


def spreading_activation(
    G: nx.DiGraph,
    seed: str,
    energy: float = 1.0,
    decay: float = 0.5,
    iterations: int = 4,
) -> list[dict]:
    activation: dict[str, float] = {seed: energy}
    depth: dict[str, int] = {seed: 0}
    frontier = [seed]

    for _ in range(iterations):
        next_frontier: list[str] = []
        for node in frontier:
            current_energy = activation[node] * decay
            d = depth[node] + 1
            for nb in list(G.successors(node)) + list(G.predecessors(node)):
                propagated = current_energy
                if nb in activation:
                    activation[nb] = max(activation[nb], propagated)
                    if nb not in depth or d < depth[nb]:
                        depth[nb] = d
                else:
                    activation[nb] = propagated
                    depth[nb] = d
                    next_frontier.append(nb)
        frontier = next_frontier

    results = []
    for node, act in activation.items():
        if node == seed:
            continue
        results.append({"label": node, "activation": act, "depth": depth.get(node, 0)})
    results.sort(key=lambda x: -x["activation"])
    return results


def born_rule_collapse(
    labels: list[str],
    amplitudes: list[float],
    n_trials: int = 1,
    context: dict[str, float] | None = None,
) -> str | None:
    amps = np.array(amplitudes, dtype=float)
    if context:
        ctx = np.ones(len(labels))
        for i, label in enumerate(labels):
            if label in context:
                ctx[i] = context[label]
        amps = amps * ctx
    probs = np.abs(amps) ** 2
    total = probs.sum()
    if total == 0:
        return None
    probs = probs / total
    indices = np.random.choice(len(labels), size=n_trials, p=probs)
    return labels[indices[0]] if n_trials == 1 else Counter(labels[i] for i in indices)


def evolve_graph(
    G: nx.DiGraph,
    decay_factor: float = 0.85,
    prune_threshold: float = 0.1,
) -> dict:
    decayed = 0
    for node in G.nodes():
        old_w = G.nodes[node].get("_weight", 1.0)
        new_w = old_w * decay_factor
        G.nodes[node]["_weight"] = new_w
        if old_w > prune_threshold >= new_w:
            decayed += 1

    to_prune = [
        n for n in G.nodes()
        if G.nodes[n].get("_weight", 1.0) <= prune_threshold
        and G.nodes[n].get("_access_count", 0) <= 0
    ]
    for n in to_prune:
        G.remove_node(n)

    node_list = list(G.nodes())
    merged = 0
    i = 0
    while i < len(node_list):
        ni = node_list[i]
        if ni not in G:
            i += 1
            continue
        j = i + 1
        while j < len(node_list):
            nj = node_list[j]
            if nj not in G:
                j += 1
                continue
            di = dict(G.nodes[ni])
            dj = dict(G.nodes[nj])
            ti = di.get("type", "")
            tj = dj.get("type", "")
            if ti and tj and ti == tj:
                si = di.get("sophistication", "")
                sj = dj.get("sophistication", "")
                if si and sj and si == sj:
                    succ_i = set(G.successors(ni))
                    succ_j = set(G.successors(nj))
                    if len(succ_i & succ_j) >= 2:
                        for _, v, data in list(G.out_edges(nj, data=True)):
                            if not G.has_edge(ni, v):
                                G.add_edge(ni, v, **data)
                        for u, _, data in list(G.in_edges(nj, data=True)):
                            if not G.has_edge(u, ni):
                                G.add_edge(u, ni, **data)
                        G.remove_node(nj)
                        merged += 1
                        node_list.remove(nj)
                        continue
            j += 1
        i += 1

    return {
        "decayed": decayed,
        "pruned": len(to_prune),
        "merged": merged,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
    }


def edges_by_label(G: nx.DiGraph, src: str, label: str) -> list[str]:
    return [v for _, v, d in G.out_edges(src, data=True) if d.get("label") == label]


def degree_centrality(G: nx.DiGraph) -> dict[str, float]:
    n = G.number_of_nodes()
    if n <= 1:
        return {node: 0.0 for node in G.nodes()}
    return {node: (G.in_degree(node) + G.out_degree(node)) / (2 * (n - 1)) for node in G.nodes()}


def main() -> None:
    G = nx.DiGraph()

    section(1, "Building the Threat Intelligence Knowledge Graph")

    for actor in THREAT_ACTORS:
        G.add_node(actor["label"], **actor["data"], _weight=1.0, _access_count=1)
    for cve in CVES:
        G.add_node(cve["label"], **cve["data"], _weight=1.0, _access_count=1)
    for mw in MALWARE:
        G.add_node(mw["label"], **mw["data"], _weight=1.0, _access_count=1)
    for ttp in TTPS:
        G.add_node(ttp["label"], **ttp["data"], _weight=1.0, _access_count=1)
    for infra in INFRASTRUCTURE:
        G.add_node(infra["label"], **infra["data"], _weight=1.0, _access_count=1)
    for ind in INDUSTRIES:
        G.add_node(ind["label"], **ind["data"], _weight=1.0, _access_count=1)
    for ioc in STALE_IOC:
        G.add_node(ioc["label"], **ioc["data"], _weight=0.05, _access_count=0)

    for rel_label, pairs in RELATIONSHIPS.items():
        for src, tgt in pairs:
            G.add_edge(src, tgt, label=rel_label, weight=1.0)

    actor_set = {a["label"] for a in THREAT_ACTORS}
    cve_set = {c["label"] for c in CVES}
    mw_set = {m["label"] for m in MALWARE}

    print(f"  Nodes:  {G.number_of_nodes()}")
    print(f"  Edges:  {G.number_of_edges()}")
    print(f"  Threat actors: {len(actor_set)}  CVEs: {len(cve_set)}  Malware: {len(mw_set)}")

    section(2, "Rule-Based Reasoning -- Discovering Hidden Relationships")

    print("  InverseRule: for every APT-[exploits]->CVE, create CVE-[exploited_by]->APT.")
    print("  AbductiveRule: if APT targets sector S, hypothesize about causation.")
    print()

    pre_edges = G.number_of_edges()

    inv_exploits = apply_inverse_rule(G, "exploits", "exploited_by")
    inv_targets = apply_inverse_rule(G, "targets", "targeted_by")
    inv_uses = apply_inverse_rule(G, "uses", "used_by")
    inv_comms = apply_inverse_rule(G, "communicates_with", "communicates_with")
    abd_targets = apply_abductive_rule(G, "targets", "suspected_attacker")

    new_edges = G.number_of_edges() - pre_edges
    print(f"  Inverse edges added:  {inv_exploits} (exploited_by) + {inv_targets} (targeted_by) + {inv_uses} (used_by) + {inv_comms} (communicates_with)")
    print(f"  Abductive hypotheses: {abd_targets}")
    print(f"  New edges total:      {new_edges}")
    print()

    exploited_by_examples = []
    suspected_examples = []
    for u, v, data in G.edges(data=True):
        if data.get("label") == "exploited_by" and len(exploited_by_examples) < 3:
            exploited_by_examples.append(f"    {u} --[exploited_by]--> {v}")
        elif data.get("label") == "suspected_attacker" and len(suspected_examples) < 5:
            suspected_examples.append(f"    {u} --[suspected_attacker]--> {v}")

    if exploited_by_examples:
        print(f"    Reverse lookup edges (exploited_by):")
        for ex in exploited_by_examples:
            print(ex)
    if suspected_examples:
        print(f"    Attribution hypotheses (suspected_attacker):")
        for ex in suspected_examples:
            print(ex)

    section(3, "Spreading Activation -- Alert Triage and Impact Scoring")

    print("  Scenario: CVE-2023-44228 is being exploited in the wild.")
    print("  Which threat actors and sectors light up?")
    print()

    activated = spreading_activation(G, "CVE-2023-44228", energy=1.0, decay=0.5, iterations=4)

    activated_actors = [r for r in activated if r["label"] in actor_set]
    activated_sectors = [r for r in activated if r["label"] in {i["label"] for i in INDUSTRIES}]
    activated_cves = [r for r in activated if r["label"] in cve_set]

    print(f"  Total activated nodes: {len(activated)}")
    print()
    print(f"  Activated threat actors ({len(activated_actors)}):")
    for r in activated_actors[:8]:
        print(f"    {r['label']:22s}  energy={r['activation']:.3f}  depth={r['depth']}")
    print()
    print(f"  Affected sectors ({len(activated_sectors)}):")
    for r in activated_sectors:
        print(f"    {r['label']:22s}  energy={r['activation']:.3f}")
    print()
    print(f"  Related CVEs ({len(activated_cves)}):")
    for r in activated_cves[:5]:
        print(f"    {r['label']:22s}  energy={r['activation']:.3f}  depth={r['depth']}")

    section(4, "Quantum Superposition -- Competing Attribution Hypotheses")

    print("  Scenario: an intrusion is detected. Four APT groups are suspects.")
    print("  Born-rule collapse from prior amplitudes.")
    print()

    suspects = ["APT28", "APT29", "Lazarus", "Volt_Typhoon"]
    prior_amplitudes = [0.7, 0.5, 0.4, 0.3]

    amps = np.array(prior_amplitudes)
    probs = np.abs(amps) ** 2
    probs = probs / probs.sum()

    print(f"  Prior distribution (from CTI reporting):")
    for label, p in zip(suspects, probs):
        print(f"    {label:22s}  probability={p:.4f}")

    print()
    print("  Running 1000 collapse trials to verify distribution...")

    np.random.seed(None)
    counts: Counter[str] = Counter()
    for _ in range(1000):
        result = born_rule_collapse(suspects, prior_amplitudes)
        if result:
            counts[result] += 1

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
        result = born_rule_collapse(suspects, prior_amplitudes, context=ctx_weights)
        if result:
            ctx_counts[result] += 1

    for label in suspects:
        c = ctx_counts.get(label, 0)
        bar = "#" * (c // 10)
        print(f"    {label:22s}  {c:4d} ({c/10:.1f}%) {bar}")

    section(5, "Self-Evolution -- Decay Stale IOCs, Reinforce Active Threats")

    print("  Evolution decays weights, prunes low-weight/low-access nodes,")
    print("  and merges structurally similar nodes.")
    print()

    stale_labels = {ioc["label"] for ioc in STALE_IOC}
    for label in stale_labels:
        if G.has_node(label):
            G.nodes[label]["_access_count"] = 0

    pre_nodes = G.number_of_nodes()
    pre_edges_evolve = G.number_of_edges()

    print(f"  Before evolution: {pre_nodes} nodes, {pre_edges_evolve} edges")
    print(f"  Stale IOCs (weight ~0.05): {', '.join(sorted(stale_labels))}")
    print()

    evo = evolve_graph(G)

    print(f"  After evolution:")
    print(f"    Edges decayed:    {evo['decayed']}")
    print(f"    Nodes pruned:     {evo['pruned']}")
    print(f"    Nodes merged:     {evo['merged']}")
    print(f"    Graph size now:   {evo['node_count']} nodes, {evo['edge_count']} edges")

    surviving_stale = []
    for label in sorted(stale_labels):
        if G.has_node(label):
            w = G.nodes[label].get("_weight", 0)
            surviving_stale.append(f"{label} (weight={w:.3f})")
    if surviving_stale:
        print(f"    Stale IOCs surviving: {surviving_stale}")
    else:
        print(f"    All stale IOCs pruned from the graph.")

    section(6, "Pattern Matching and Centrality -- Who Is Most Dangerous?")

    print("  Degree centrality on the relationship graph.")
    print()

    centrality = degree_centrality(G)
    top_actors = sorted(
        [(k, v) for k, v in centrality.items() if k in actor_set],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    print("  Top 5 most connected threat actors:")
    for rank, (label, score) in enumerate(top_actors, 1):
        exploits = edges_by_label(G, label, "exploits")
        targets = edges_by_label(G, label, "targets")
        uses = edges_by_label(G, label, "uses")
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
        nd = G.nodes[cve_label]
        product = nd.get("product", "?")
        cvss = nd.get("cvss", "?")
        print(f"    {rank}. {cve_label:22s} centrality={score:.4f}  "
              f"CVSS={cvss}  product={product}")

    apt28_neighbors = set()
    for edge_list_fn in [
        lambda: edges_by_label(G, "APT28", "exploits"),
        lambda: edges_by_label(G, "APT28", "targets"),
        lambda: edges_by_label(G, "APT28", "uses"),
        lambda: edges_by_label(G, "APT28", "uses_tactic"),
    ]:
        for nb in edge_list_fn():
            apt28_neighbors.add(nb)
    apt28_neighbors.add("APT28")
    sg = G.subgraph(apt28_neighbors & set(G.nodes()))
    print()
    print(f"  APT28 full profile subgraph: {sg.number_of_nodes()} nodes, {sg.number_of_edges()} edges")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Nodes:                {G.number_of_nodes()}")
    print(f"  Edges:                {G.number_of_edges()}")
    print(f"  Inferred by rules:    {new_edges}")
    print(f"  Stale IOCs pruned:    {evo['pruned']}")
    print()
    print("  Lines of code written for this script:")
    print("    Rule engine (inverse + abductive):  ~35 lines")
    print("    Spreading activation:               ~20 lines")
    print("    Born-rule collapse:                  ~15 lines")
    print("    Self-evolution (decay+prune+merge):  ~40 lines")
    print("    Total custom logic:                 ~110 lines")
    print()
    print("  NetworkX + NumPy only. No Hyper3 dependency.")


if __name__ == "__main__":
    main()
