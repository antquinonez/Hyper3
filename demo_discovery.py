"""
Demo: self-discovering rules + persistence across sessions.

Run with: .venv/bin/python demo_discovery.py
"""

import tempfile, os
from hyper3 import CognitiveMemory, Modality, Serializer

print("=" * 70)
print("SESSION 1: Build knowledge, discover rules, persist")
print("=" * 70)

mem = CognitiveMemory(evolve_interval=0)

for label in ["ignition", "fuel_flow", "combustion", "heat", "engine_rotation", "electricity", "spark"]:
    mem.store(label, modalities={Modality.CONCEPTUAL})

mem.relate("spark", "ignition", label="causes")
mem.relate("ignition", "combustion", label="causes")
mem.relate("combustion", "heat", label="causes")
mem.relate("fuel_flow", "combustion", label="enables")
mem.relate("combustion", "engine_rotation", label="causes")
mem.relate("heat", "electricity", label="generates")

print(f"\n  Stored: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")

# Auto-discover rules from the graph structure
result = mem.auto_discover_and_apply()
print(f"\n  Rule discovery:")
print(f"    Total patterns:  {result['total_patterns']}")
print(f"    New rules added: {result['new_rules_added']}")
for dr in mem.discovery.get_discovered_rules():
    rule_info = f"rule={dr.rule.name}" if dr.rule else "no auto-rule"
    print(f"    [{dr.pattern_type}] {dr.pattern}  {rule_info}")

# Reason with discovered rules
print(f"\n  Reasoning with discovered rules...")
reason_result = mem.reason({"spark", "ignition", "combustion", "heat", "engine_rotation", "electricity", "fuel_flow"}, max_depth=3, max_total_states=20)
exp = reason_result["expansion"]
print(f"    States: {exp['states_created']}, Rules applied: {exp['rules_applied']}, Edges produced: {exp['edges_produced']}")

# Show inferred knowledge
print(f"\n  Inferred edges:")
for edge in mem.graph.edges:
    if edge.metadata.custom.get("inferred"):
        src = [mem.graph.get_node(n) for n in edge.source_ids]
        tgt = [mem.graph.get_node(n) for n in edge.target_ids]
        print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")

# Save
tmpdir = tempfile.mkdtemp()
save_path = os.path.join(tmpdir, "session.json")
mem.save(save_path)
print(f"\n  Saved to {save_path}")
print(f"  Final: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")

# --- SESSION 2 ---
print("\n" + "=" * 70)
print("SESSION 2: Load persisted state, continue building")
print("=" * 70)

mem2 = CognitiveMemory(evolve_interval=0)
mem2.load(save_path)
print(f"\n  Loaded: {mem2.graph.node_count} nodes, {mem2.graph.edge_count} edges")
print(f"  Event log entries: {mem2.log.size}")

# Add new knowledge on top
mem2.store("battery")
mem2.store("starter_motor")
mem2.relate("battery", "electricity", label="supplies")
mem2.relate("electricity", "starter_motor", label="powers")
mem2.relate("starter_motor", "engine_rotation", label="causes")

print(f"  After additions: {mem2.graph.node_count} nodes, {mem2.graph.edge_count} edges")

# Discover new patterns with the expanded graph
result2 = mem2.auto_discover_and_apply()
print(f"\n  New rule discovery: {result2['new_rules_added']} new rules")

# Reason again with all rules (old + newly discovered)
reason2 = mem2.reason({"battery", "starter_motor", "spark", "fuel_flow"}, max_depth=3, max_total_states=15)
exp2 = reason2["expansion"]
print(f"  Reasoning: {exp2['rules_applied']} rules applied, {exp2['edges_produced']} edges produced")

print(f"\n  New inferred edges in session 2:")
count = 0
for edge in mem2.graph.edges:
    if edge.metadata.custom.get("inferred") and edge.metadata.custom.get("rule", "").startswith("discovered"):
        src = [mem2.graph.get_node(n) for n in edge.source_ids]
        tgt = [mem2.graph.get_node(n) for n in edge.target_ids]
        print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")
        count += 1
    elif edge.metadata.custom.get("inferred") and edge.id not in [e.id for e in mem.graph.edges]:
        src = [mem2.graph.get_node(n) for n in edge.source_ids]
        tgt = [mem2.graph.get_node(n) for n in edge.target_ids]
        print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")
        count += 1
if count == 0:
    for edge in mem2.graph.edges:
        if edge.metadata.custom.get("inferred"):
            src = [mem2.graph.get_node(n) for n in edge.source_ids]
            tgt = [mem2.graph.get_node(n) for n in edge.target_ids]
            print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")

print(f"\n  Session 2 final stats:")
stats = mem2.stats()
for k, v in stats.items():
    print(f"    {k}: {v}")

# Cleanup
os.remove(save_path)
os.rmdir(tmpdir)
