"""
Demo: Full hyper3 cognitive architecture with all subsystems.

Branchial Space | Rulial Space | Transfinite Reasoning
Computational Relativity | Meta-Cognitive Introspection
Quantum Entanglement | Interference | Measurement Bases

Run with: .venv/bin/python demos/demo_full.py
"""

from hyper3 import (
    CognitiveMemory,
    Modality,
    TransitiveRule,
    InverseRule,
)

print("=" * 72)
print("  HYPER3 FULL ARCHITECTURE DEMO")
print("=" * 72)

mem = CognitiveMemory(evolve_interval=0)

# --- 1. Build Knowledge Graph ---
print("\n[1] Building knowledge graph...")

concepts = {
    "spark": "electric_arc",
    "ignition": "combustion_start",
    "fuel_flow": "hydrocarbon_delivery",
    "combustion": "exothermic_reaction",
    "heat": "thermal_energy",
    "engine_rotation": "mechanical_work",
    "electricity": "electromagnetic_energy",
    "battery": "chemical_energy_storage",
    "starter_motor": "electric_motor",
    "coolant": "thermal_regulation",
    "thermostat": "temperature_control",
    "radiator": "heat_dissipation",
}

for name, data in concepts.items():
    mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

relations = [
    ("spark", "ignition", "causes"),
    ("ignition", "combustion", "causes"),
    ("combustion", "heat", "causes"),
    ("combustion", "engine_rotation", "causes"),
    ("fuel_flow", "combustion", "enables"),
    ("heat", "electricity", "generates"),
    ("battery", "electricity", "supplies"),
    ("electricity", "starter_motor", "powers"),
    ("starter_motor", "engine_rotation", "causes"),
    ("heat", "coolant", "transfers_to"),
    ("coolant", "thermostat", "regulated_by"),
    ("thermostat", "radiator", "activates"),
    ("radiator", "heat", "dissipates"),
]

for src, tgt, label in relations:
    mem.relate(src, tgt, label=label)

print(f"   {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")

# --- 2. Rule Discovery + Reasoning ---
print("\n[2] Discovering rules and reasoning...")

result = mem.auto_discover_and_apply()
print(f"   Patterns discovered: {result.total_patterns}")
print(f"   New rules added: {result.new_rules_added}")

mem.add_rules(TransitiveRule(edge_label="causes"), InverseRule(edge_label="causes", inverse_label="caused_by"))

reason_result = mem.reason(
    {"spark", "fuel_flow", "battery", "heat"},
    max_depth=3,
    max_total_states=30,
)
exp = reason_result.expansion
if exp:
    print(f"   Reasoning: {exp.rules_applied} rules applied, {exp.edges_produced} edges produced")
print(f"   Multiway states: {reason_result.multiway_leaves}")

# --- 3. Branchial Space ---
print("\n[3] Branchial space analysis...")

if mem.branchial:
    report = mem.branchial.analyze()
    print(f"   States mapped: {report.states_mapped}")
    print(f"   Simultaneity groups: {report.simultaneity_groups}")
    entanglements = mem.branchial.detect_entanglements()
    print(f"   Branchial entanglements: {len(entanglements)}")
    for ent in entanglements[:3]:
        print(f"     correlation={ent.correlation:.2f}, shared={len(ent.shared_concept_ids)}")

# --- 4. Rulial Space ---
print("\n[4] Rulial space exploration...")

rulial = mem.rulial
rulial.record_rule_application("transitive")
rulial.record_rule_application("inverse")
pos = rulial.update_position()
print(f"   Computational density: {pos.computational_density:.3f}")
print(f"   Causal graph complexity: {pos.causal_graph_complexity:.3f}")

patterns = rulial.find_meta_patterns()
print(f"   Meta-patterns found: {len(patterns)}")
for p in patterns[:3]:
    print(f"     [{p.pattern_type}] {p.description}")

insights = rulial.generate_transcendental_insights()
print(f"   Transcendental insights: {len(insights)}")
for ins in insights[:3]:
    print(f"     ({ins.confidence:.2f}) {ins.principle}")

# --- 5. Quantum Enhanced ---
print("\n[5] Quantum cognitive effects...")

qs = mem.superpose(["spark", "battery", "fuel_flow"], amplitudes=[0.6, 0.5, 0.4])
print(f"   Superposition: {qs.superposition_count} interpretations")

triggers = mem.detect_collapse_triggers(qs)
print(f"   Collapse triggers: {[t.trigger_type for t in triggers]}")

interference = mem.compute_interference(qs)
print(f"   Interference patterns: {len(interference)}")
for ip in interference:
    kind = "constructive" if ip.is_constructive else "destructive" if ip.is_destructive else "neutral"
    print(f"     [{kind}] net={ip.net_amplitude:.3f}")

result_basis = mem.collapse_with_basis(qs, "pragmatic")
print(f"   Collapse (pragmatic basis): {result_basis.node_id if result_basis else 'none'}")

# Entanglement
ent = mem.entangle(
    ["spark", "battery"],
    ["electricity", "starter_motor"],
    {("spark", "electricity"): 0.9, ("battery", "starter_motor"): 0.85},
)
print(f"   Entanglement created: strength={ent.strength:.2f}")

qs2 = mem.superpose(["spark", "battery"])
preds = mem.collapse_entangled(qs2, "spark")
print(f"   Entangled predictions from 'spark': {preds}")

# --- 6. Structural Anomaly Detection ---
print("\n[6] Structural anomaly detection...")

test_concepts = [
    "spark",
    "self-referential engine analysis",
    "all engines are universal",
]

for concept in test_concepts:
    result = mem.detect_structural_anomalies(concept)
    print(f"   '{concept}':")
    print(f"     status={result.decidability_status}, score={result.boundary_score:.3f}, level={result.reasoning_level}")
    if result.boundary_warnings:
        for w in result.boundary_warnings:
            print(f"     WARNING: {w}")

boundary_map = mem.map_boundaries(test_concepts)
decidable = sum(1 for r in boundary_map if r.status == "decidable")
print(f"   Boundary map: {decidable}/{len(boundary_map)} decidable")

# --- 7. Multi-Perspective Analysis ---
print("\n[7] Multi-perspective analysis...")

optimal_name, optimal_analysis = mem.select_optimal_frame("combustion")
print(f"   Optimal frame for 'combustion': {optimal_name}")
print(f"     complexity={optimal_analysis.complexity:.3f}, approach={optimal_analysis.solution_approach}")

multi = mem.multi_frame_analysis("combustion")
for frame_name, analysis in multi.items():
    print(f"   [{frame_name}] complexity={analysis.complexity:.3f}, approach={analysis.solution_approach}")

# --- 8. Meta-Cognitive Introspection ---
print("\n[8] Meta-cognitive introspection...")

introspection = mem.introspect()
cs = introspection.cognitive_state
print(f"   Architectural fitness: {cs.fitness:.3f}")
print(f"   Reasoning mode: {cs.mode}")
print(f"   Meta-computational level: {cs.meta_level}")
print(f"   Transcendental yield: {cs.transcendental_yield}")

gh = introspection.graph_health
print(f"   Graph: {gh.nodes} nodes, {gh.edges} edges, avg_degree={gh.avg_degree:.3f}")

if introspection.recommendations:
    print(f"   Recommendations:")
    for rec in introspection.recommendations:
        print(f"     - {rec}")

triggers = mem.check_metamorphosis()
if triggers:
    print(f"   Metamorphosis triggers: {len(triggers)}")
    for t in triggers:
        print(f"     [{t.trigger_type}] urgency={t.urgency:.2f}: {t.description}")
    plan = mem.propose_metamorphosis(triggers)
    if plan:
        print(f"   Metamorphosis plan: {plan.actions}")
else:
    print("   No metamorphosis triggers - system healthy")

# --- Summary ---
print("\n" + "=" * 72)
print("  FINAL STATS")
print("=" * 72)

stats = mem.stats()
print(f"  Nodes: {stats.nodes}")
print(f"  Edges: {stats.edges}")
print(f"  Log size: {stats.log_size}")
print(f"  Cache size: {stats.cache_size}")
print(f"  Operations: {stats.operations}")
print(f"  Multiway states: {stats.multiway_states}")
print(f"  Quantum active: {stats.quantum_active}")
print(f"  Components: {stats.components}")
print(f"  Active rules: {stats.active_rules}")
