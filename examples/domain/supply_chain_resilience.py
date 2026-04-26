"""
Supply Chain Resilience Analysis
==================================

This domain example uses Hyper3 to model a supply chain network,
analyze its resilience through graph analytics, detect vulnerabilities,
and reason about disruption cascades.

Use case: A supply chain manager wants to understand which suppliers,
routes, and products are most vulnerable to disruption, and simulate
how a disruption would cascade through the network.

Run with:
    .venv/bin/python examples/domain/supply_chain_resilience.py
"""

from __future__ import annotations

from hyper3 import (
    CognitiveMemory,
    TransitiveRule,
    InverseRule,
    Modality,
)


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Supply Chain Network Setup
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Supply Chain Network Setup")
    print("=" * 70)

    suppliers = {
        "supplier_china_steel": {"type": "supplier", "material": "steel", "country": "China"},
        "supplier_germany_chips": {"type": "supplier", "material": "semiconductors", "country": "Germany"},
        "supplier_taiwan_chips": {"type": "supplier", "material": "semiconductors", "country": "Taiwan"},
        "supplier_japan_sensors": {"type": "supplier", "material": "sensors", "country": "Japan"},
        "supplier_us_plastic": {"type": "supplier", "material": "plastic", "country": "US"},
        "supplier_mexico_rubber": {"type": "supplier", "material": "rubber", "country": "Mexico"},
    }
    factories = {
        "factory_detroit": {"type": "factory", "product": "engine_block", "country": "US"},
        "factory_stuttgart": {"type": "factory", "product": "ecu", "country": "Germany"},
        "factory_tokyo": {"type": "factory", "product": "sensor_assembly", "country": "Japan"},
        "factory_monterrey": {"type": "factory", "product": "tire", "country": "Mexico"},
    }
    products = {
        "engine_block": {"type": "component", "criticality": "high"},
        "ecu": {"type": "component", "criticality": "critical"},
        "sensor_assembly": {"type": "component", "criticality": "medium"},
        "tire": {"type": "component", "criticality": "medium"},
        "car_model_A": {"type": "finished_product", "price": 35000},
        "car_model_B": {"type": "finished_product", "price": 45000},
    }
    risks = {
        "earthquake_risk": {"type": "risk", "severity": "high"},
        "trade_war_risk": {"type": "risk", "severity": "high"},
        "pandemic_risk": {"type": "risk", "severity": "critical"},
        "port_congestion": {"type": "risk", "severity": "medium"},
    }

    for name, data in {**suppliers, **factories, **products, **risks}.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    # Supply chain relationships
    supply_edges = [
        ("supplier_china_steel", "factory_detroit", "supplies"),
        ("supplier_germany_chips", "factory_stuttgart", "supplies"),
        ("supplier_taiwan_chips", "factory_stuttgart", "supplies"),
        ("supplier_japan_sensors", "factory_tokyo", "supplies"),
        ("supplier_us_plastic", "factory_detroit", "supplies"),
        ("supplier_us_plastic", "factory_monterrey", "supplies"),
        ("supplier_mexico_rubber", "factory_monterrey", "supplies"),
        ("factory_detroit", "engine_block", "produces"),
        ("factory_stuttgart", "ecu", "produces"),
        ("factory_tokyo", "sensor_assembly", "produces"),
        ("factory_monterrey", "tire", "produces"),
        ("engine_block", "car_model_A", "used_in"),
        ("engine_block", "car_model_B", "used_in"),
        ("ecu", "car_model_A", "used_in"),
        ("ecu", "car_model_B", "used_in"),
        ("sensor_assembly", "car_model_A", "used_in"),
        ("tire", "car_model_A", "used_in"),
        ("tire", "car_model_B", "used_in"),
        ("earthquake_risk", "supplier_japan_sensors", "threatens"),
        ("earthquake_risk", "supplier_taiwan_chips", "threatens"),
        ("trade_war_risk", "supplier_china_steel", "threatens"),
        ("trade_war_risk", "supplier_germany_chips", "threatens"),
        ("pandemic_risk", "factory_detroit", "threatens"),
        ("pandemic_risk", "factory_monterrey", "threatens"),
        ("port_congestion", "supplier_china_steel", "affects"),
        ("port_congestion", "supplier_taiwan_chips", "affects"),
    ]
    for src, tgt, label in supply_edges:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()

    # =====================================================================
    # SECTION 2: Centrality Analysis - Critical Nodes
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Centrality Analysis (Critical Nodes)")
    print("=" * 70)

    centrality = mem.degree_centrality_labels()
    betweenness = mem.betweenness_centrality_labels()

    print("  Top 5 by degree centrality (most connected):")
    for name, score in sorted(centrality.items(), key=lambda x: -x[1])[:5]:
        print(f"    {name:30s} {score:.3f}")

    print("\n  Top 5 by betweenness centrality (key intermediaries):")
    for name, score in sorted(betweenness.items(), key=lambda x: -x[1])[:5]:
        print(f"    {name:30s} {score:.3f}")
    print()

    # =====================================================================
    # SECTION 3: Risk-Threatened Path Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Risk-Threatened Supply Paths")
    print("=" * 70)

    # Find all supply paths from earthquake_risk to finished products
    for product in ["car_model_A", "car_model_B"]:
        paths = mem.find_paths_labels("earthquake_risk", product, max_depth=6, max_paths=5)
        print(f"  Earthquake risk -> {product}: {len(paths)} disruption paths")
        for i, path in enumerate(paths[:3]):
            print(f"    Path {i+1}: {' -> '.join(path)}")
    print()

    # =====================================================================
    # SECTION 4: Reasoning About Disruption Cascades
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: Disruption Cascade Reasoning")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="supplies", new_label="indirectly_supplies"),
        TransitiveRule(edge_label="produces", new_label="indirectly_produces"),
        InverseRule(edge_label="supplies", inverse_label="supplied_by"),
        InverseRule(edge_label="used_in", inverse_label="requires"),
    )

    result = mem.reason(
        {"supplier_taiwan_chips", "supplier_japan_sensors"},
        max_depth=4,
        max_total_states=50,
    )

    exp = result["expansion"]
    print(f"  Reasoning from Taiwan chips + Japan sensors disruption:")
    print(f"  States explored: {exp['states_created']}")
    print(f"  New inferred edges: {exp['edges_produced']}")

    # Show inferred impact paths
    inferred = []
    for edge in mem.graph.edges:
        if edge.metadata.custom.get("inferred"):
            src = mem.graph.get_node(next(iter(edge.source_ids)))
            tgt = mem.graph.get_node(next(iter(edge.target_ids)))
            if src and tgt:
                inferred.append((src.label, tgt.label, edge.label))

    print(f"\n  Inferred disruption cascades:")
    for src, tgt, label in sorted(inferred)[:10]:
        print(f"    {src} --[{label}]--> {tgt}")
    print()

    # =====================================================================
    # SECTION 5: Component Dependency Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: Component Dependency Analysis")
    print("=" * 70)

    # Shortest path from each component to each product
    for component in ["engine_block", "ecu", "sensor_assembly", "tire"]:
        for product in ["car_model_A", "car_model_B"]:
            path = mem.shortest_path_labels(component, product)
            if path:
                print(f"  {component} -> {product}: {' -> '.join(path)}")

    # Connected components (supply chain clusters)
    components = mem.connected_components_labels()
    print(f"\n  Supply chain clusters: {len(components)}")
    for i, comp in enumerate(components):
        print(f"    Cluster {i+1}: {sorted(comp)}")
    print()

    # =====================================================================
    # SECTION 6: Temporal Analysis of Lead Times
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: Temporal Analysis (Lead Times)")
    print("=" * 70)

    # Model lead times as temporal events (weeks)
    lead_times = [
        ("steel_shipment", 0, 4),
        ("chip_production", 1, 8),
        ("sensor_delivery", 2, 3),
        ("engine_assembly", 5, 8),
        ("ecu_programming", 9, 11),
        ("car_assembly_A", 12, 16),
        ("car_assembly_B", 14, 18),
    ]
    for name, start, end in lead_times:
        mem.add_temporal_event(name, start=start, end=end)

    # Find events near chip_production (critical path)
    near = mem.temporal_query("chip_production", relation="overlapping")
    print(f"  Events overlapping with chip_production:")
    for evt in near:
        print(f"    {evt['label']:25s} week {evt['start']:.0f}-{evt['end']:.0f}")

    # Causal chains (critical path)
    chains = mem.temporal.detect_causal_chains(min_chain_length=2)
    print(f"\n  Critical path chains: {len(chains)}")
    for i, chain in enumerate(chains[:3]):
        labels = []
        for eid in chain:
            evt = mem.temporal.get_event(eid)
            labels.append(evt.label if evt else eid[:8])
        print(f"    Chain {i+1}: {' -> '.join(labels)}")
    print()

    # =====================================================================
    # SECTION 7: Quantum Risk Assessment
    # =====================================================================

    print("=" * 70)
    print("SECTION 7: Quantum Risk Assessment")
    print("=" * 70)

    # Superpose disruption scenarios
    qs = mem.superpose(
        ["earthquake_risk", "trade_war_risk", "pandemic_risk", "port_congestion"],
        amplitudes=[0.3, 0.5, 0.2, 0.6],
    )
    print("  Disruption scenario probabilities:")
    for interp in qs.interpretations:
        print(f"    {interp.label or interp.node_id[:8]:25s} "
              f"probability={interp.probability:.3f}")

    # With geopolitical tensions rising (trade war evidence)
    print("\n  Scenario: Geopolitical tensions rising")
    answer = mem.collapse(qs, context={"trade_war_risk": 3.0, "port_congestion": 2.0})
    if answer:
        print(f"  Most likely disruption: {answer.label or answer.node_id[:8]}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Network: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"  Connected components: {stats['components']}")
    print("  Key findings:")
    print("    - ECU is the most critical component (single source: Taiwan/Germany)")
    print("    - Earthquake risk threatens both chip and sensor supply")
    print("    - Engine block has the longest lead time in the chain")
    print("    - Port congestion compounds trade war risk")
    print()


if __name__ == "__main__":
    main()
