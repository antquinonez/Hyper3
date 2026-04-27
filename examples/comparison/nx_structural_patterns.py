"""
NetworkX-only equivalent of Hyper3's 13_structural_patterns_and_communities.py
===============================================================================
Implements chain detection, diamond detection, fan-out analysis, and
community detection using pure NetworkX.
"""

from __future__ import annotations

import networkx as nx
from collections import defaultdict

COMPANIES = {
    "acme_cloud": {"type": "company", "sector": "cloud"},
    "nexa_ai": {"type": "company", "sector": "ai"},
    "volt_data": {"type": "company", "sector": "data"},
    "pulse_security": {"type": "company", "sector": "security"},
    "orbit_iot": {"type": "company", "sector": "iot"},
    "zenith_fintech": {"type": "company", "sector": "fintech"},
    "nova_biotech": {"type": "company", "sector": "biotech"},
    "sigma_chips": {"type": "company", "sector": "semiconductor"},
    "aurora_energy": {"type": "company", "sector": "energy"},
    "helix_health": {"type": "company", "sector": "healthtech"},
    "quantum_lab": {"type": "company", "sector": "quantum"},
    "terra_logistics": {"type": "company", "sector": "logistics"},
    "cipher_blockchain": {"type": "company", "sector": "blockchain"},
    "neural_edge": {"type": "company", "sector": "edge_computing"},
    "stellar_education": {"type": "company", "sector": "edtech"},
}

PRODUCTS = {
    "cloud_platform_x": {"type": "product", "category": "paas"},
    "ai_assistant_pro": {"type": "product", "category": "ai_tool"},
    "data_lake_fusion": {"type": "product", "category": "data_platform"},
    "secure_vault": {"type": "product", "category": "security_tool"},
    "iot_gateway_hub": {"type": "product", "category": "iot_platform"},
    "payflow_api": {"type": "product", "category": "payment"},
    "genome_analyzer": {"type": "product", "category": "biotech_tool"},
    "neural_chip_v3": {"type": "product", "category": "hardware"},
    "smart_grid_os": {"type": "product", "category": "energy_platform"},
    "health_monitor_360": {"type": "product", "category": "health_app"},
    "quantum_sim": {"type": "product", "category": "simulation"},
    "route_optimizer": {"type": "product", "category": "logistics_tool"},
    "chain_custody": {"type": "product", "category": "blockchain_tool"},
    "edge_runtime": {"type": "product", "category": "edge_platform"},
    "learn_space": {"type": "product", "category": "lms"},
}

TECHNOLOGIES = {
    "kubernetes": {"type": "technology", "layer": "orchestration"},
    "tensorflow": {"type": "technology", "layer": "ml_framework"},
    "pytorch": {"type": "technology", "layer": "ml_framework"},
    "apache_spark": {"type": "technology", "layer": "data_processing"},
    "rust_lang": {"type": "technology", "layer": "language"},
    "golang": {"type": "technology", "layer": "language"},
    "python": {"type": "technology", "layer": "language"},
    "postgresql": {"type": "technology", "layer": "database"},
    "redis": {"type": "technology", "layer": "cache"},
    "kafka": {"type": "technology", "layer": "messaging"},
    "graphql": {"type": "technology", "layer": "api"},
    "grpc": {"type": "technology", "layer": "rpc"},
    "docker": {"type": "technology", "layer": "containerization"},
    "terraform": {"type": "technology", "layer": "infrastructure"},
    "react": {"type": "technology", "layer": "frontend"},
    "webassembly": {"type": "technology", "layer": "runtime"},
    "zeromq": {"type": "technology", "layer": "messaging"},
    "openssl": {"type": "technology", "layer": "crypto"},
    "protobuf": {"type": "technology", "layer": "serialization"},
    "arrow_format": {"type": "technology", "layer": "data_format"},
}

PEOPLE = {
    "alice_chen": {"type": "person", "role": "cto", "company": "acme_cloud"},
    "bob_kumar": {"type": "person", "role": "ml_lead", "company": "nexa_ai"},
    "carla_santos": {"type": "person", "role": "data_eng", "company": "volt_data"},
    "dave_okonkwo": {"type": "person", "role": "security_arch", "company": "pulse_security"},
    "eve_tanaka": {"type": "person", "role": "iot_eng", "company": "orbit_iot"},
    "frank_mueller": {"type": "person", "role": "fintech_lead", "company": "zenith_fintech"},
    "grace_dubois": {"type": "person", "role": "bioinformatician", "company": "nova_biotech"},
    "henry_park": {"type": "person", "role": "chip_designer", "company": "sigma_chips"},
    "iris_johansson": {"type": "person", "role": "energy_analyst", "company": "aurora_energy"},
    "jake_rivera": {"type": "person", "role": "health_dev", "company": "helix_health"},
    "kate_zhao": {"type": "person", "role": "quantum_researcher", "company": "quantum_lab"},
    "leo_singh": {"type": "person", "role": "logistics_eng", "company": "terra_logistics"},
    "maya_brown": {"type": "person", "role": "blockchain_dev", "company": "cipher_blockchain"},
    "nick_weber": {"type": "person", "role": "edge_specialist", "company": "neural_edge"},
    "olivia_patel": {"type": "person", "role": "edtech_dev", "company": "stellar_education"},
    "paul_nguyen": {"type": "person", "role": "devops", "company": "acme_cloud"},
    "quinn_foster": {"type": "person", "role": "ml_eng", "company": "nexa_ai"},
    "rita_kim": {"type": "person", "role": "backend_eng", "company": "zenith_fintech"},
    "sam_cohen": {"type": "person", "role": "security_eng", "company": "pulse_security"},
    "tina_rossi": {"type": "person", "role": "frontend_eng", "company": "stellar_education"},
}

STANDARDS = {
    "iso_27001": {"type": "standard", "domain": "security"},
    "pci_dss": {"type": "standard", "domain": "payment"},
    "hipaa": {"type": "standard", "domain": "health"},
    "gdpr": {"type": "standard", "domain": "privacy"},
    "soc2": {"type": "standard", "domain": "compliance"},
    "fedramp": {"type": "standard", "domain": "cloud_security"},
}

EDGES = [
    ("acme_cloud", "cloud_platform_x", "develops", 9.0),
    ("acme_cloud", "kubernetes", "uses", 8.0),
    ("acme_cloud", "docker", "uses", 7.0),
    ("acme_cloud", "terraform", "uses", 6.0),
    ("acme_cloud", "golang", "uses", 5.0),
    ("acme_cloud", "postgresql", "uses", 5.0),
    ("acme_cloud", "redis", "uses", 4.0),
    ("nexa_ai", "ai_assistant_pro", "develops", 9.0),
    ("nexa_ai", "tensorflow", "uses", 8.0),
    ("nexa_ai", "pytorch", "uses", 7.0),
    ("nexa_ai", "python", "uses", 6.0),
    ("nexa_ai", "kubernetes", "uses", 5.0),
    ("volt_data", "data_lake_fusion", "develops", 9.0),
    ("volt_data", "apache_spark", "uses", 8.0),
    ("volt_data", "kafka", "uses", 7.0),
    ("volt_data", "arrow_format", "uses", 5.0),
    ("volt_data", "python", "uses", 4.0),
    ("pulse_security", "secure_vault", "develops", 9.0),
    ("pulse_security", "openssl", "uses", 7.0),
    ("pulse_security", "rust_lang", "uses", 6.0),
    ("pulse_security", "grpc", "uses", 4.0),
    ("orbit_iot", "iot_gateway_hub", "develops", 9.0),
    ("orbit_iot", "zeromq", "uses", 6.0),
    ("orbit_iot", "golang", "uses", 5.0),
    ("orbit_iot", "docker", "uses", 4.0),
    ("zenith_fintech", "payflow_api", "develops", 9.0),
    ("zenith_fintech", "kubernetes", "uses", 7.0),
    ("zenith_fintech", "postgresql", "uses", 6.0),
    ("zenith_fintech", "grpc", "uses", 5.0),
    ("zenith_fintech", "kafka", "uses", 5.0),
    ("zenith_fintech", "redis", "uses", 4.0),
    ("nova_biotech", "genome_analyzer", "develops", 9.0),
    ("nova_biotech", "python", "uses", 7.0),
    ("nova_biotech", "tensorflow", "uses", 6.0),
    ("nova_biotech", "apache_spark", "uses", 5.0),
    ("sigma_chips", "neural_chip_v3", "develops", 9.0),
    ("sigma_chips", "rust_lang", "uses", 7.0),
    ("sigma_chips", "pytorch", "uses", 6.0),
    ("sigma_chips", "protobuf", "uses", 4.0),
    ("aurora_energy", "smart_grid_os", "develops", 9.0),
    ("aurora_energy", "kafka", "uses", 6.0),
    ("aurora_energy", "kubernetes", "uses", 5.0),
    ("aurora_energy", "python", "uses", 4.0),
    ("helix_health", "health_monitor_360", "develops", 9.0),
    ("helix_health", "tensorflow", "uses", 6.0),
    ("helix_health", "graphql", "uses", 5.0),
    ("helix_health", "react", "uses", 4.0),
    ("quantum_lab", "quantum_sim", "develops", 9.0),
    ("quantum_lab", "pytorch", "uses", 5.0),
    ("quantum_lab", "python", "uses", 4.0),
    ("terra_logistics", "route_optimizer", "develops", 9.0),
    ("terra_logistics", "golang", "uses", 7.0),
    ("terra_logistics", "kafka", "uses", 5.0),
    ("terra_logistics", "docker", "uses", 4.0),
    ("cipher_blockchain", "chain_custody", "develops", 9.0),
    ("cipher_blockchain", "rust_lang", "uses", 7.0),
    ("cipher_blockchain", "golang", "uses", 5.0),
    ("neural_edge", "edge_runtime", "develops", 9.0),
    ("neural_edge", "webassembly", "uses", 7.0),
    ("neural_edge", "rust_lang", "uses", 6.0),
    ("neural_edge", "docker", "uses", 4.0),
    ("stellar_education", "learn_space", "develops", 9.0),
    ("stellar_education", "react", "uses", 7.0),
    ("stellar_education", "graphql", "uses", 5.0),
    ("stellar_education", "python", "uses", 4.0),
    ("acme_cloud", "nexa_ai", "partners_with", 6.0),
    ("acme_cloud", "pulse_security", "partners_with", 5.0),
    ("nexa_ai", "sigma_chips", "partners_with", 7.0),
    ("nexa_ai", "nova_biotech", "partners_with", 4.0),
    ("zenith_fintech", "pulse_security", "partners_with", 6.0),
    ("zenith_fintech", "cipher_blockchain", "partners_with", 3.0),
    ("aurora_energy", "orbit_iot", "partners_with", 5.0),
    ("helix_health", "nova_biotech", "partners_with", 7.0),
    ("neural_edge", "orbit_iot", "partners_with", 4.0),
    ("stellar_education", "nexa_ai", "partners_with", 3.0),
    ("acme_cloud", "soc2", "certified_for", 8.0),
    ("acme_cloud", "fedramp", "certified_for", 7.0),
    ("zenith_fintech", "pci_dss", "certified_for", 9.0),
    ("helix_health", "hipaa", "certified_for", 9.0),
    ("pulse_security", "iso_27001", "certified_for", 8.0),
    ("nova_biotech", "hipaa", "certified_for", 6.0),
    ("zenith_fintech", "gdpr", "certified_for", 7.0),
    ("acme_cloud", "gdpr", "certified_for", 6.0),
    ("alice_chen", "acme_cloud", "works_at", 5.0),
    ("bob_kumar", "nexa_ai", "works_at", 5.0),
    ("carla_santos", "volt_data", "works_at", 5.0),
    ("dave_okonkwo", "pulse_security", "works_at", 5.0),
    ("eve_tanaka", "orbit_iot", "works_at", 5.0),
    ("frank_mueller", "zenith_fintech", "works_at", 5.0),
    ("grace_dubois", "nova_biotech", "works_at", 5.0),
    ("henry_park", "sigma_chips", "works_at", 5.0),
    ("iris_johansson", "aurora_energy", "works_at", 5.0),
    ("jake_rivera", "helix_health", "works_at", 5.0),
    ("kate_zhao", "quantum_lab", "works_at", 5.0),
    ("leo_singh", "terra_logistics", "works_at", 5.0),
    ("maya_brown", "cipher_blockchain", "works_at", 5.0),
    ("nick_weber", "neural_edge", "works_at", 5.0),
    ("olivia_patel", "stellar_education", "works_at", 5.0),
    ("paul_nguyen", "acme_cloud", "works_at", 5.0),
    ("quinn_foster", "nexa_ai", "works_at", 5.0),
    ("rita_kim", "zenith_fintech", "works_at", 5.0),
    ("sam_cohen", "pulse_security", "works_at", 5.0),
    ("tina_rossi", "stellar_education", "works_at", 5.0),
    ("alice_chen", "bob_kumar", "mentors", 3.0),
    ("alice_chen", "paul_nguyen", "mentors", 3.0),
    ("bob_kumar", "quinn_foster", "mentors", 3.0),
    ("dave_okonkwo", "sam_cohen", "mentors", 3.0),
    ("grace_dubois", "jake_rivera", "mentors", 3.0),
    ("henry_park", "kate_zhao", "mentors", 3.0),
]


def find_chains(G: nx.DiGraph, edge_label: str, min_length: int = 2, max_length: int = 5, max_chains: int = 50) -> list[list[str]]:
    chains: list[list[str]] = []
    for node in G.nodes():
        stack: list[tuple[str, list[str]]] = [(node, [node])]
        while stack and len(chains) < max_chains:
            current, path = stack.pop()
            if len(path) - 1 >= min_length:
                chains.append(path[:])
            if len(path) - 1 < max_length:
                for _, tgt, data in G.out_edges(current, data=True):
                    if data.get("label") == edge_label:
                        stack.append((tgt, path + [tgt]))
    return chains


def find_fan_out(G: nx.DiGraph, edge_label: str | None = None, min_fan: int = 3) -> list[tuple[str, list[str]]]:
    results: list[tuple[str, list[str]]] = []
    for node in G.nodes():
        targets: list[str] = []
        for _, tgt, data in G.out_edges(node, data=True):
            if edge_label is None or data.get("label") == edge_label:
                targets.append(tgt)
        if len(targets) >= min_fan:
            results.append((node, targets))
    results.sort(key=lambda x: -len(x[1]))
    return results


def find_diamonds(G: nx.DiGraph, edge_label: str | None = None, max_matches: int = 50) -> list[dict]:
    incoming: dict[str, list[str]] = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if edge_label is None or data.get("label") == edge_label:
            incoming[v].append(u)

    diamonds: list[dict] = []
    for target, sources in incoming.items():
        if len(sources) < 2:
            continue
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                if len(diamonds) >= max_matches:
                    return diamonds
                sa, sb = sources[i], sources[j]
                shared = set(G.successors(sa)) & set(G.successors(sb))
                if edge_label:
                    shared = {
                        t for t in shared
                        if any(d.get("label") == edge_label for _, _, d in G.out_edges(sa, data=True) if _ == sa and __ == t for _, __, d in [])
                    }
                score = 1.0 / (1.0 + abs(G.out_degree(sa) - G.out_degree(sb)))
                diamonds.append({"source_a": sa, "source_b": sb, "converge": target, "score": round(score, 2)})
    diamonds.sort(key=lambda x: -x["score"])
    return diamonds[:max_matches]


def detect_communities(G: nx.Graph, seed: int = 42) -> tuple[list[set[str]], float]:
    import random
    random.seed(seed)
    communities = list(nx.community.label_propagation_communities(G))
    if not communities:
        return [], 0.0
    mod = nx.community.modularity(G, communities)
    return communities, mod


def main() -> None:
    G = nx.DiGraph()

    all_nodes = {**COMPANIES, **PRODUCTS, **TECHNOLOGIES, **PEOPLE, **STANDARDS}
    for name, data in all_nodes.items():
        G.add_node(name, **data)

    for src, tgt, label, weight in EDGES:
        G.add_edge(src, tgt, label=label, weight=weight)

    print("=" * 70)
    print("NetworkX: Structural Patterns & Communities")
    print("=" * 70)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print()

    print("SECTION 2: Chain Detection")
    use_chains = find_chains(G, "uses", min_length=2, max_length=4, max_chains=10)
    print(f"  'uses' chains (length >= 2): {len(use_chains)}")
    for chain in use_chains[:5]:
        print(f"    {' -> '.join(chain)}")
    print()

    print("SECTION 3: Fan-Out Analysis")
    fan_outs = find_fan_out(G, "uses", min_fan=3)
    print(f"  Companies using 3+ technologies:")
    for node, targets in fan_outs[:10]:
        print(f"    {node:<20} fan_out={len(targets)}  targets={targets}")
    print()

    print("SECTION 4: Diamond Detection")
    diamonds = find_diamonds(G, "uses", max_matches=10)
    print(f"  Technology convergence diamonds: {len(diamonds)}")
    for d in diamonds[:5]:
        print(f"    {d['source_a']} + {d['source_b']} -> {d['converge']} (score={d['score']})")
    print()

    print("SECTION 5: Community Detection")
    U = G.to_undirected()
    communities, modularity = detect_communities(U, seed=42)
    print(f"  Communities: {len(communities)}")
    print(f"  Modularity:  {modularity:.3f}")
    for comm in communities[:6]:
        types: dict[str, int] = {}
        for lbl in comm:
            nd = G.nodes[lbl]
            t = nd.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        print(f"    {len(comm)} nodes: {types} — {', '.join(list(comm)[:5])}...")
    print()


if __name__ == "__main__":
    main()
