"""
A walk through hyper3 with a real scenario: diagnosing a car that won't start.
Each section shows what the system is doing and why it matters.

Run with: .venv/bin/python demos/demo_walkthrough.py
"""

from hyper3 import CognitiveMemory, TransitiveRule, InverseRule, Modality

print("""
╔══════════════════════════════════════════════════════════════════════╗
║  HYPER3 WALKTHROUGH                                                 ║
║  Scenario: A mechanic's diagnostic assistant                       ║
╚══════════════════════════════════════════════════════════════════════╝
""")

mem = CognitiveMemory(evolve_interval=0)

# ─── STEP 1: Store domain knowledge ──────────────────────────────────
print("━" * 72)
print("STEP 1: Storing domain knowledge")
print("━" * 72)
print("""
We tell the system about car components and what they do.
This is just a knowledge graph — concepts + relationships.
""")

components = {
    "battery":            {"type": "electrical",  "voltage": 12},
    "starter_motor":      {"type": "electrical",  "draw_amps": 150},
    "alternator":         {"type": "electrical",  "output_amps": 100},
    "spark_plug":         {"type": "ignition",    "gap_mm": 0.8},
    "fuel_pump":          {"type": "fuel",        "pressure_psi": 40},
    "fuel_injector":      {"type": "fuel",        "spray_pattern": "cone"},
    "air_filter":         {"type": "air",         "flow_rating": "standard"},
    "ignition_coil":      {"type": "ignition",    "output_v": 30000},
    "combustion_chamber": {"type": "mechanical"},
    "crankshaft":         {"type": "mechanical"},
    "timing_belt":        {"type": "mechanical"},
    "engine_computer":    {"type": "electronic",  "protocol": "OBD2"},
    "fuel_tank":          {"type": "fuel"},
    "gasoline":           {"type": "fuel"},
}

for name, data in components.items():
    mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

causal_chain = [
    ("battery",            "starter_motor",      "powers"),
    ("starter_motor",      "crankshaft",         "turns"),
    ("battery",            "ignition_coil",      "powers"),
    ("ignition_coil",      "spark_plug",         "fires"),
    ("fuel_tank",          "fuel_pump",          "feeds"),
    ("fuel_pump",          "fuel_injector",      "pressurizes"),
    ("fuel_injector",      "combustion_chamber", "injects"),
    ("spark_plug",         "combustion_chamber", "ignites"),
    ("combustion_chamber", "crankshaft",         "drives"),
    ("crankshaft",         "alternator",         "spins"),
    ("alternator",         "battery",            "charges"),
    ("air_filter",         "combustion_chamber", "supplies_air"),
    ("gasoline",           "fuel_tank",          "fills"),
    ("engine_computer",    "fuel_injector",      "controls"),
    ("engine_computer",    "spark_plug",         "controls"),
    ("timing_belt",        "crankshaft",         "synchronizes"),
]

for src, tgt, label in causal_chain:
    mem.relate(src, tgt, label=label)

extra_chains = [
    ("ignition_coil", "engine_computer", "powers"),
    ("engine_computer", "fuel_injector", "powers"),
    ("fuel_tank", "gasoline", "feeds"),
    ("gasoline", "fuel_pump", "feeds"),
]
for src, tgt, label in extra_chains:
    mem.relate(src, tgt, label=label)

print(f"Stored {mem.graph.node_count} components, {mem.graph.edge_count} causal relationships")
print()

# ─── STEP 2: Rule discovery ──────────────────────────────────────────
print("━" * 72)
print("STEP 2: Self-discovering rules from the graph")
print("━" * 72)
print("""
The system looks at the graph structure and finds patterns.
It doesn't need to be told "if A powers B and B turns C, then A affects C"
— it discovers this from the chain of "powers" and "turns" edges.
""")

result = mem.auto_discover_and_apply()
print(f"Patterns found: {result['total_patterns']}")
print(f"Rules auto-generated: {result['new_rules_added']}")

for dr in mem.discovery.get_discovered_rules():
    print(f"  → [{dr.pattern_type}] {dr.pattern}")
    if dr.rule:
        print(f"    Generated rule: {dr.rule.name}")
print()

# ─── STEP 3: Multiway reasoning ──────────────────────────────────────
print("━" * 72)
print("STEP 3: Reasoning — the mechanic says 'car won't start'")
print("━" * 72)
print("""
Given a symptom, the system reasons through ALL possible causal paths
simultaneously (multiway expansion). It doesn't just follow one chain —
it branches and explores every possibility at once.

Seed: {battery, fuel_tank, spark_plug} — the three main systems needed.
""")

mem.add_rules(
    TransitiveRule(edge_label="powers"),
    TransitiveRule(edge_label="turns"),
    TransitiveRule(edge_label="fires"),
    TransitiveRule(edge_label="pressurizes"),
    TransitiveRule(edge_label="injects"),
    TransitiveRule(edge_label="ignites"),
    TransitiveRule(edge_label="drives"),
    TransitiveRule(edge_label="feeds"),
)

reason = mem.reason(
    {"battery", "fuel_tank", "spark_plug"},
    max_depth=3,
    max_total_states=25,
)

exp = reason["expansion"]
print(f"States explored: {exp['states_created']}")
print(f"Rules applied: {exp['rules_applied']}")
print(f"Inferred edges (new knowledge): {exp['edges_produced']}")
print()

print("Inferred causal chains the system discovered:")
for edge in mem.graph.edges:
    if edge.metadata.custom.get("inferred"):
        src_labels = []
        tgt_labels = []
        for sid in edge.source_ids:
            n = mem.graph.get_node(sid)
            if n:
                src_labels.append(n.label)
        for tid in edge.target_ids:
            n = mem.graph.get_node(tid)
            if n:
                tgt_labels.append(n.label)
        rule = edge.metadata.custom.get("rule", "unknown")
        print(f"  {src_labels} ──[{edge.label}]──▶ {tgt_labels}  (via {rule})")
print()

# ─── STEP 4: Quantum superposition for diagnosis ─────────────────────
print("━" * 72)
print("STEP 4: Quantum diagnosis — keeping multiple hypotheses alive")
print("━" * 72)
print("""
The mechanic has 3 candidate failure points: battery, fuel_pump, spark_plug.
Instead of guessing, we hold ALL THREE as a quantum superposition.
Each has an amplitude (confidence weight).
""")

qs = mem.superpose(
    ["battery", "fuel_pump", "spark_plug"],
    amplitudes=[0.6, 0.3, 0.25],  # battery is most suspected
)
print(f"Superposition: {qs.superposition_count} hypotheses held simultaneously")
print(f"  |battery⟩   amplitude=0.6  probability={0.6**2:.2f}")
print(f"  |fuel_pump⟩ amplitude=0.3  probability={0.3**2:.2f}")
print(f"  |spark_plug⟩ amplitude=0.25 probability={0.25**2:.2f}")
print()

# Correlation: if battery is dead, starter_motor and ignition_coil are also dead
print("Correlation: battery failure constrains other components")
ent = mem.correlate(
    ["battery"],
    ["starter_motor", "ignition_coil"],
    {("battery", "starter_motor"): 0.95, ("battery", "ignition_coil"): 0.9},
)
print(f"  battery ⟷ starter_motor (correlation=0.95)")
print(f"  battery ⟷ ignition_coil (correlation=0.90)")
print()

# Now we get new evidence: "headlights are dim" → battery confirmed weak
print("New evidence arrives: 'headlights are dim' → battery is weak")
answer = mem.collapse(qs, context={"battery": 3.0})
collapsed_node = mem.graph.get_node(answer.node_id)
collapsed_label = collapsed_node.label if collapsed_node else answer.node_id
print(f"Collapsed to: {collapsed_label} (amplitude={answer.amplitude:.3f})")
print()

# ─── STEP 5: Interference patterns ───────────────────────────────────
print("━" * 72)
print("STEP 5: Evidence interference")
print("━" * 72)
print("""
Multiple evidence sources can interfere:
- Constructive: weak signals combine into a strong conclusion
- Destructive: conflicting evidence cancels out
""")

qs2 = mem.superpose(
    ["battery", "fuel_pump", "spark_plug", "alternator", "timing_belt"],
    amplitudes=[0.7, -0.3, 0.4, -0.5, 0.2],
)
patterns = mem.compute_interference(qs2)
print("Interference analysis:")
for p in patterns:
    kind = "CONSTRUCTIVE ▲" if p.is_constructive else "DESTRUCTIVE ▼" if p.is_destructive else "neutral"
    node = mem.graph.get_node(p.node_id)
    label = node.label if node else p.node_id
    print(f"  {label:20s} [{kind}]  constructive={p.constructive:+.3f}  destructive={p.destructive:+.3f}  net={p.net_amplitude:+.3f}")
print()
print("Positive amplitudes (battery, spark_plug, timing_belt) interfere constructively")
print("Negative amplitudes (fuel_pump, alternator) interfere destructively")
print()

# ─── STEP 6: Transfinite reasoning ───────────────────────────────────
print("━" * 72)
print("STEP 6: Boundary detection — when is a question answerable?")
print("━" * 72)
print("""
Some diagnostic questions are straightforward (low risk).
Others approach boundary or anomalous territory — like "is this car's design fundamentally flawed?"
The system detects this and adapts its reasoning strategy.
""")

questions = [
    ("is the battery dead?",                       "low_risk"),
    ("what is the root cause of failure?",         "low_risk"),
    ("is the car's electrical system self-aware?", "boundary"),
]

for question, expected in questions:
    result = mem.detect_structural_anomalies(question)
    print(f"  Q: {question}")
    print(f"    Status: {result.decidability_status}  |  Level: {result.reasoning_level}  |  Score: {result.boundary_score:.3f}")
    if result.boundary_warnings:
        for w in result.boundary_warnings:
            print(f"    ⚠ {w}")
    if result.alternative_formulations:
        print(f"    Alternatives: {result.alternative_formulations[:2]}")
    print()

# ─── STEP 7: Multi-frame analysis ────────────────────────────────
print("━" * 72)
print("STEP 7: Multi-frame analysis — same problem, different lenses")
print("━" * 72)
print("""
The same diagnostic question can be analyzed in different computational frames.
Each frame reveals different aspects of the problem.
""")

concept = "combustion_chamber"
analyses = mem.multi_frame_analysis(concept)
print(f"Analyzing '{concept}' across all frames:")
for frame_name, analysis in analyses.items():
    print(f"  [{frame_name:13s}] complexity={analysis.complexity:.3f}  approach={analysis.solution_approach:25s}")
    if analysis.strengths:
        print(f"    strengths: {', '.join(analysis.strengths[:3])}")

optimal_name, optimal = mem.select_optimal_frame(concept)
print(f"\nOptimal frame: {optimal_name} (complexity={optimal.complexity:.3f})")
print()

# ─── STEP 8: Rulial space ────────────────────────────────────────────
print("━" * 72)
print("STEP 8: Rulial space — the system maps its own computational position")
print("━" * 72)
print("""
The system tracks where it stands in the space of all possible computations.
It measures how dense its knowledge is, how diverse its rules are,
and generates 'transcendental insights' — meta-knowledge about its own patterns.
""")

rulial = mem.rulial
pos = rulial.update_position()
print(f"Graph activity density: {pos.graph_activity_density:.3f}")
print(f"  (how richly interconnected the knowledge graph is)")
print(f"Structural complexity: {pos.structural_complexity:.3f}")
print(f"  (how complex the causal structure has become)")
print(f"Rules explored: {len(rulial.explored_rules)}")
print()

patterns = rulial.find_meta_patterns()
print("Meta-patterns discovered about its own knowledge:")
for p in patterns:
    print(f"  [{p.pattern_type}] {p.description}")
print()

insights = rulial.generate_high_level_insights()
print("High-level insights (meta-knowledge):")
for ins in insights:
    print(f"  ({ins.confidence:.0%}) {ins.principle}")
print()

# ─── STEP 9: Meta-cognitive introspection ────────────────────────────
print("━" * 72)
print("STEP 9: The system analyzes its own health")
print("━" * 72)
print("""
The system monitors its own cognitive fitness:
- Is the knowledge graph healthy?
- Are there anti-patterns (sparse areas, dead weight)?
- Should the architecture be restructured?
""")

introspection = mem.introspect()
cs = introspection["cognitive_state"]
gh = introspection["graph_health"]
dh = introspection["discovery_health"]

print(f"Architectural fitness: {cs.fitness:.1%}")
print(f"Reasoning mode: {cs.mode}")
print(f"Graph health: {gh.nodes} nodes, {gh.edges} edges, avg_degree={gh.avg_degree:.2f}")
print(f"Discovery: {dh.patterns} patterns, {dh.active_rules} active rules")

if "recommendations" in introspection:
    print("Recommendations:")
    for rec in introspection["recommendations"]:
        print(f"  → {rec}")

triggers = mem.check_metamorphosis()
if triggers:
    print("Metamorphosis triggers:")
    for t in triggers:
        print(f"  [{t.trigger_type}] {t.description}")
else:
    print("System is healthy — no restructuring needed")
print()

# ─── STEP 10: Persistence ────────────────────────────────────────────
print("━" * 72)
print("STEP 10: Save knowledge for next session")
print("━" * 72)
import tempfile, os
tmpdir = tempfile.mkdtemp()
path = os.path.join(tmpdir, "mechanic_knowledge.json")
mem.save(path)
print(f"Saved {mem.graph.node_count} nodes, {mem.graph.edge_count} edges, {mem.log.size} events")
print(f"File: {path}")

mem2 = CognitiveMemory(evolve_interval=0)
mem2.load(path)
print(f"Loaded into fresh memory: {mem2.graph.node_count} nodes, {mem2.graph.edge_count} edges")
print(f"Event log preserved: {mem2.log.size} events")

os.remove(path)
os.rmdir(tmpdir)

# ─── SUMMARY ──────────────────────────────────────────────────────────
print()
print("━" * 72)
print("SUMMARY: What just happened")
print("━" * 72)
print("""
1. KNOWLEDGE STORAGE    → We stored car components and causal relationships
2. RULE DISCOVERY       → The system found transitive patterns automatically
3. MULTIWAY REASONING   → It explored ALL causal paths simultaneously
4. QUANTUM DIAGNOSIS    → It held multiple failure hypotheses in superposition
5. CORRELATION         → Battery failure constrained related components
6. INTERFERENCE         → Evidence combined (constructive) or cancelled (destructive)
7. BOUNDARY DETECTION   → It knew which questions were answerable vs anomalous
8. MULTI-FRAME ANALYSIS → It analyzed the same problem from 4 different perspectives
9. RULIAL MAPPING       → It tracked its own position in computational space
10. META-COGNITION      → It evaluated its own health and recommended improvements
11. PERSISTENCE         → It saved everything for the next diagnostic session
""")
