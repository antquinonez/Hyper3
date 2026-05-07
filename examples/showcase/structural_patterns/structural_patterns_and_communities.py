"""
Structural Pattern Matching and Community Detection
====================================================

Demonstrates structural pattern detection (chains, diamonds, fan-out) and
community detection on a knowledge graph modeling a technology ecosystem
with 100+ nodes covering companies, products, technologies, and people.

Run with:
    .venv/bin/python examples/showcase/structural_patterns/13_structural_patterns_and_communities.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory


COMPANIES = {
    "acme_cloud": {"type": "company", "sector": "cloud", "employees": 5000, "region": "US"},
    "nexa_ai": {"type": "company", "sector": "ai", "employees": 800, "region": "US"},
    "volt_data": {"type": "company", "sector": "data", "employees": 1200, "region": "EU"},
    "pulse_security": {"type": "company", "sector": "security", "employees": 600, "region": "US"},
    "orbit_iot": {"type": "company", "sector": "iot", "employees": 300, "region": "APAC"},
    "zenith_fintech": {"type": "company", "sector": "fintech", "employees": 2000, "region": "US"},
    "nova_biotech": {"type": "company", "sector": "biotech", "employees": 1500, "region": "EU"},
    "sigma_chips": {"type": "company", "sector": "semiconductor", "employees": 8000, "region": "US"},
    "aurora_energy": {"type": "company", "sector": "energy", "employees": 3000, "region": "EU"},
    "helix_health": {"type": "company", "sector": "healthtech", "employees": 900, "region": "US"},
    "quantum_lab": {"type": "company", "sector": "quantum", "employees": 200, "region": "US"},
    "terra_logistics": {"type": "company", "sector": "logistics", "employees": 4000, "region": "APAC"},
    "cipher_blockchain": {"type": "company", "sector": "blockchain", "employees": 400, "region": "US"},
    "neural_edge": {"type": "company", "sector": "edge_computing", "employees": 350, "region": "EU"},
    "stellar_education": {"type": "company", "sector": "edtech", "employees": 700, "region": "US"},
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

EDGES: list[tuple[str, str, str, float]] = [
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
    ("orbit_iot", "mqtt", "uses", 7.0) if False else ("orbit_iot", "zeromq", "uses", 6.0),
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


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building Technology Ecosystem Graph")
    print("=" * 70)

    all_nodes = {**COMPANIES, **PRODUCTS, **TECHNOLOGIES, **PEOPLE, **STANDARDS}
    for name, data in all_nodes.items():
        mem.add(name, data=data)

    for src, tgt, label, weight in EDGES:
        mem.link(src, tgt, label=label, weight=weight)

    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")
    print()

    print("=" * 70)
    print("SECTION 2: Chain Detection - Technology Dependency Chains")
    print("=" * 70)

    dev_chains = mem.match_chains(edge_label="develops", min_length=1, max_length=3, max_chains=20)
    print(f"  'develops' chains found: {len(dev_chains)}")
    for chain in dev_chains[:5]:
        print(f"    {' -> '.join(chain)}")
    print()

    use_chains = mem.match_chains(edge_label="uses", min_length=2, max_length=4, max_chains=10)
    print(f"  'uses' chains (length >= 2): {len(use_chains)}")
    for chain in use_chains[:5]:
        print(f"    {' -> '.join(chain)}")
    print()

    print("=" * 70)
    print("SECTION 3: Fan-Out Analysis - Technology Hubs")
    print("=" * 70)

    fan_outs = mem.match_fan_out(edge_label="uses", min_fan=3, max_results=10)
    print(f"  Companies using 3+ technologies:")
    for entry in fan_outs:
        print(f"    {entry['node']:<20} fan_out={entry['fan_out']}  targets={entry['targets']}")
    print()

    partner_fans = mem.match_fan_out(edge_label="partners_with", min_fan=2, max_results=10)
    print(f"  Companies with 2+ partnerships:")
    for entry in partner_fans:
        print(f"    {entry['node']:<20} partners={entry['targets']}")
    print()

    print("=" * 70)
    print("SECTION 4: Diamond Detection - Convergence Patterns")
    print("=" * 70)

    diamonds = mem.match_diamonds(edge_label="uses", max_matches=10)
    print(f"  Technology convergence diamonds: {len(diamonds)}")
    for d in diamonds[:5]:
        src_a = d.get("source_a", "?")
        src_b = d.get("source_b", "?")
        mid = d.get("mid", d.get("converge", "?"))
        print(f"    {src_a} + {src_b} -> {mid} (score={d['score']:.2f})")
    print()

    print("=" * 70)
    print("SECTION 5: Community Detection - Natural Clusters")
    print("=" * 70)

    result = mem.analyze.communities(method="weighted_label_propagation", seed=42)
    print(f"  Communities: {result.community_count}")
    print(f"  Modularity:  {result.modularity:.3f}")
    print(f"  Coverage:    {result.coverage:.1%}")
    print()

    type_map: dict[str, str] = {}
    for t in ("company", "product", "technology", "person", "standard"):
        for lbl in mem.query_nodes(data={"type": t}):
            type_map[lbl] = t

    for comm in result.communities[:8]:
        types: dict[str, int] = {}
        for lbl in comm.member_labels:
            t = type_map.get(lbl, "unknown")
            types[t] = types.get(t, 0) + 1
        members_preview = ", ".join(comm.member_labels[:5])
        if comm.size > 5:
            members_preview += "..."
        print(f"  Community {comm.community_id} ({comm.size} nodes, "
              f"int={comm.internal_edges}, ext={comm.external_edges})")
        print(f"    Types: {types}")
        print(f"    Members: {members_preview}")
        print()

    print("=" * 70)
    print("SECTION 6: Cross-Analysis - Communities + Patterns")
    print("=" * 70)

    largest = max(result.communities, key=lambda c: c.size)
    print(f"  Largest community ({largest.size} nodes):")
    print(f"    Members: {', '.join(largest.member_labels[:8])}...")

    hub_nodes = {lbl for lbl in largest.member_labels}
    cross_community_edges = 0
    for edge in mem.engine.graph.edges:
        src_node = mem.engine.graph.get_node(list(edge.source_ids)[0]) if edge.source_ids else None
        tgt_node = mem.engine.graph.get_node(list(edge.target_ids)[0]) if edge.target_ids else None
        if src_node and tgt_node:
            s_in = src_node.label in hub_nodes
            t_in = tgt_node.label in hub_nodes
            if s_in != t_in:
                cross_community_edges += 1
    print(f"    Cross-community connections: {cross_community_edges}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Graph: {mem.size[0]} nodes, {mem.size[1]} edges")
    print(f"  Patterns: {len(use_chains)} dependency chains, {len(fan_outs)} hubs, {len(diamonds)} diamonds")
    print(f"  Communities: {result.community_count} (modularity={result.modularity:.3f})")
    print()
    print("  Key insight: structural patterns reveal technology dependency")
    print("  chains and convergence points, while community detection finds")
    print("  natural technology clusters that cross company boundaries.")
    print()


if __name__ == "__main__":
    main()
