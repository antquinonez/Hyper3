"""
Demo: Full hyper3 architecture with all subsystems.

This demo exercises every major subsystem in a single run:
  1. Knowledge graph construction (nodes + labeled directed edges)
  2. Rule discovery + multiway reasoning (transitive + inverse rules)
  3. State clustering (mapping multiway states into coordinate space)
  4. Rule analytics (tracking rule effectiveness and meta-patterns)
  5. Belief distributions (superposition, interference, sampling, correlation)
  6. Structural anomaly detection (boundary analysis)
  7. Multi-perspective analysis (classical/quantum/hypergraph/probabilistic frames)
  8. Meta-cognitive introspection (health, metamorphosis triggers)

The domain is an engine system: spark, ignition, fuel, cooling, and their
causal relationships.

Run with: .venv/bin/python demos/demo_full.py
"""

from hyper3 import (
    HypergraphMemory,
    Modality,
    TransitiveRule,
    InverseRule,
)

print("=" * 72)
print("  HYPER3 FULL ARCHITECTURE DEMO")
print("=" * 72)

mem = HypergraphMemory(evolve_interval=0)

# --- 1. Build Knowledge Graph ---
#
# Store engine components as nodes and their causal relationships as edges.
# Each node carries a data payload (technical description) and a modality
# tag (CONCEPTUAL means abstract knowledge, not a physical measurement).
#
# The edge labels ("causes", "enables", "powers") encode the relationship
# semantics. Rules use these labels to decide which edges to match.
#
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
    mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

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
    mem.link(src, tgt, label=label)

print(f"   {mem.size[0]} nodes, {mem.size[1]} edges")

# --- 2. Rule Discovery + Reasoning ---
#
# auto_discover_and_apply() scans the graph for structural patterns:
#   - Transitive chains (A-causes->B-causes->C) suggest a TransitiveRule
#   - Inverse pairs (A-causes->B suggests B-caused_by->A) suggest an InverseRule
#   - Hub nodes (many outgoing edges) suggest a HubInferenceRule
#
# Then we manually add TransitiveRule and InverseRule for "causes" and
# run reason() to perform multiway expansion.
#
print("\n[2] Discovering rules and reasoning...")

# Step 2a: Auto-discover patterns from the graph topology.
result = mem.auto_discover_and_apply()
print(f"   Patterns discovered: {result.total_patterns}")
print(f"   New rules added: {result.new_rules_added}")

# Step 2b: Manually register two core rules.
# TransitiveRule: if A-causes->B and B-causes->C, infer A-causes->C
# InverseRule: if A-causes->B, infer B-caused_by->A
mem.add_rules(TransitiveRule(edge_label="causes"), InverseRule(edge_label="causes", inverse_label="caused_by"))

# Step 2c: Run multiway expansion.
# reason() applies all registered rules to the graph, branching into
# multiple simultaneous states (the "multiway" approach). Each state
# represents a different set of rule applications.
reason_result = mem.reason(
    {"spark", "fuel_flow", "battery", "heat"},
    max_depth=3,
    max_total_states=30,
)
exp = reason_result.expansion
if exp:
    print(f"   Reasoning: {exp.rules_applied} rules applied, {exp.edges_produced} edges produced")
# multiway_leaves is the number of terminal states (no further rules can apply).
print(f"   Multiway states: {reason_result.multiway_leaves}")

# --- 3. State Clustering ---
#
# After multiway expansion, each leaf state represents a possible "world"
# of inferred knowledge. State clustering maps these states into a coordinate
# space based on which nodes are active, then groups similar states together.
#
# This enables "lateral reasoning": insights from one branch can transfer
# to nearby branches, even if they were derived independently.
#
print("\n[3] State clustering analysis...")

if mem.state_clustering:
    # analyze() performs the full clustering pipeline: coordinate assignment,
    # distance calculation, and group detection.
    report = mem.state_clustering.analyze()
    print(f"   States mapped: {report.states_mapped}")
    # Simultaneity groups: sets of states that share most of their active nodes.
    print(f"   Simultaneity groups: {report.simultaneity_groups}")

    # detect_correlations() finds pairs of states with high node overlap.
    correlations = mem.state_clustering.detect_correlations()
    print(f"   State correlations: {len(correlations)}")
    for corr in correlations[:3]:
        print(f"     correlation={corr.correlation:.2f}, shared={len(corr.shared_concept_ids)}")

# --- 4. Rule Analytics ---
#
# RuleAnalytics tracks which rules fire, how often, and what they produce.
# From this data it computes:
#   - graph_activity_density: how richly connected the graph is
#   - structural_complexity: composite of spectral entropy and motif diversity
#   - meta-patterns: recurring patterns in rule application
#   - high-level insights: abstract principles derived from the data
#
print("\n[4] Rule analytics exploration...")

rule_analytics = mem.rule_analytics
# Manually record some rule applications for demonstration.
# In normal usage, these are recorded automatically during reason().
rule_analytics.record_rule_application("transitive")
rule_analytics.record_rule_application("inverse")

pos = rule_analytics.update_position()
print(f"   Graph activity density: {pos.graph_activity_density:.3f}")
print(f"   Structural complexity: {pos.structural_complexity:.3f}")

patterns = rule_analytics.find_meta_patterns()
print(f"   Meta-patterns found: {len(patterns)}")
for p in patterns[:3]:
    print(f"     [{p.pattern_type}] {p.description}")

insights = rule_analytics.generate_high_level_insights()
print(f"   High-level insights: {len(insights)}")
for ins in insights[:3]:
    print(f"     ({ins.confidence:.2f}) {ins.principle}")

# --- 5. Quantum Enhanced ---
#
# Belief distributions hold multiple interpretations simultaneously,
# each with a complex-valued amplitude. The Born rule (probability = |amplitude|^2)
# governs sampling. Amplitudes can interfere constructively (same sign)
# or destructively (opposite sign), just like wave superposition.
#
# This is NOT quantum computing -- it's a probabilistic framework inspired
# by quantum formalism, applied to knowledge representation.
#
print("\n[5] Quantum cognitive effects...")

# Create a superposition of three interpretations (spark, battery, fuel_flow).
# Each gets an amplitude; probability of selection = |amplitude|^2.
qs = mem.belief.create(["spark", "battery", "fuel_flow"], amplitudes=[0.6, 0.5, 0.4])
print(f"   Superposition: {qs.outcome_count} interpretations")

# triggers() lists the conditions that would cause the superposition to
# collapse to a single outcome (context bias, threshold, external evidence).
triggers = mem.belief.triggers(qs)
print(f"   Collapse triggers: {[t.trigger_type for t in triggers]}")

# interactions() computes the interference pattern: for each outcome,
# how much constructive vs destructive interference it experiences.
interference = mem.belief.interactions(qs)
print(f"   Interference patterns: {len(interference)}")
for ip in interference:
    kind = "constructive" if ip.is_constructive else "destructive" if ip.is_destructive else "neutral"
    print(f"     [{kind}] net={ip.net_amplitude:.3f}")

# sample_with_profile() collapses the superposition using a named sampling
# profile ("pragmatic" favors the highest-probability outcome).
result_basis = mem.sample_with_profile(qs, "pragmatic")
print(f"   Collapse (pragmatic basis): {result_basis.node_id if result_basis else 'none'}")

# correlate() creates a ConceptCorrelation between two sets of outcomes.
# When one set is sampled, correlated outcomes in the other set shift in
# probability. Here: spark correlates with electricity (0.9), battery with
# starter_motor (0.85).
ent = mem.belief.correlate(
    ["spark", "battery"],
    ["electricity", "starter_motor"],
    {("spark", "electricity"): 0.9, ("battery", "starter_motor"): 0.85},
)
print(f"   Correlation created: strength={ent.strength:.2f}")

# sample_correlated() samples the second set given a sample from the first.
qs2 = mem.belief.create(["spark", "battery"])
preds = mem.belief.sample_correlated(qs2, "spark")
print(f"   Correlated predictions from 'spark': {preds}")

# --- 6. Structural Anomaly Detection ---
#
# The StructuralAnomalyDetector classifies concepts on a spectrum:
#   - low_risk: well-connected concepts with clear relationships
#   - boundary: concepts approaching unusual structural territory
#   - anomalous: concepts with cycles, contradictions, or extreme centrality
#
# Concepts NOT in the graph are analyzed by their novelty (how different
# they are from existing graph structure).
#
print("\n[6] Structural anomaly detection...")

test_concepts = [
    "spark",                             # exists in graph, well-connected
    "self-referential engine analysis",  # not in graph, unusual phrasing
    "all engines are universal",         # not in graph, universal quantifier
]

for concept in test_concepts:
    result = mem.analyze.anomalies(concept)
    print(f"   '{concept}':")
    print(f"     status={result.anomaly_status}, score={result.boundary_score:.3f}, level={result.reasoning_level}")
    if result.boundary_warnings:
        for w in result.boundary_warnings:
            print(f"     WARNING: {w}")

# map_boundaries() batch-classifies multiple concepts and reports how many
# are "decidable" (low_risk or boundary with sufficient evidence).
boundary_map = mem.map_boundaries(test_concepts)
decidable = sum(1 for r in boundary_map if r.status == "decidable")
print(f"   Boundary map: {decidable}/{len(boundary_map)} decidable")

# --- 7. Multi-Perspective Analysis ---
#
# The MultiPerspectiveAnalyzer evaluates a concept through four computational
# frames, each with its own complexity metric and solution approach:
#   - classical: standard graph metrics
#   - probabilistic: uncertainty-based assessment
#   - hypergraph: structural complexity from n-ary edges
#   - distributional: similarity/embedding-based assessment
#
# select_optimal_frame() uses Thompson sampling to pick the best frame
# based on learned effectiveness.
#
print("\n[7] Multi-perspective analysis...")

optimal_name, optimal_analysis = mem.select_optimal_frame("combustion")
print(f"   Optimal frame for 'combustion': {optimal_name}")
print(f"     complexity={optimal_analysis.complexity:.3f}, approach={optimal_analysis.solution_approach}")

multi = mem.multi_frame_analysis("combustion")
for frame_name, analysis in multi.items():
    print(f"   [{frame_name}] complexity={analysis.complexity:.3f}, approach={analysis.solution_approach}")

# --- 8. Meta-Cognitive Introspection ---
#
# The system monitors its own architectural fitness and structural health.
# introspect() returns a HealthReport with:
#   - system_health: fitness score, reasoning mode, meta-level
#   - graph_health: node/edge counts, average degree
#   - discovery_health: pattern/rule counts
#   - recommendations: actionable improvements
#
# check_metamorphosis() detects triggers for structural restructuring.
#
print("\n[8] Meta-cognitive introspection...")

introspection = mem.introspect()
cs = introspection.system_health
print(f"   Architectural fitness: {cs.fitness:.3f}")
print(f"   Reasoning mode: {cs.mode}")
print(f"   Meta-computational level: {cs.meta_level}")
print(f"   Rule analytics insight count: {cs.rule_analytics_insight_count}")

gh = introspection.graph_health
print(f"   Graph: {gh.nodes} nodes, {gh.edges} edges, avg_degree={gh.avg_degree:.3f}")

if introspection.recommendations:
    print(f"   Recommendations:")
    for rec in introspection.recommendations:
        print(f"     - {rec}")

# Metamorphosis triggers indicate conditions where the system should
# restructure itself (e.g., too many pruned nodes, stale rules).
triggers = mem.check_metamorphosis()
if triggers:
    print(f"   Metamorphosis triggers: {len(triggers)}")
    for t in triggers:
        print(f"     [{t.trigger_type}] urgency={t.urgency:.2f}: {t.description}")
    # propose_tuning() generates a concrete action plan from the triggers.
    plan = mem.propose_tuning(triggers)
    if plan:
        print(f"   Metamorphosis plan: {plan.actions}")
else:
    print("   No metamorphosis triggers - system healthy")

# --- Summary ---
print("\n" + "=" * 72)
print("  FINAL STATS")
print("=" * 72)

# stats() returns a MemoryStats dataclass with key system metrics.
stats = mem.stats()
print(f"  Nodes: {stats.nodes}")
print(f"  Edges: {stats.edges}")
print(f"  Log size: {stats.log_size}")
print(f"  Cache size: {stats.cache_size}")
print(f"  Operations: {stats.operations}")
print(f"  Multiway states: {stats.multiway_states}")
print(f"  Quantum active: {stats.belief_active}")
print(f"  Components: {stats.components}")
print(f"  Active rules: {stats.active_rules}")
