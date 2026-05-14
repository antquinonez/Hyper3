"""
Demo: self-discovering rules + persistence across sessions.

This demo shows how Hyper3 can:
  1. Examine its own graph structure to discover repeating patterns
  2. Automatically generate inference rules from those patterns
  3. Reason with those discovered rules to infer new knowledge
  4. Save the full system state to disk and restore it in a new session
  5. Continue building and reasoning in the restored session

The key insight: the system doesn't need to be told "if A causes B and B
causes C, then A causes C." It discovers this pattern by observing that
the "causes" label forms chains in the graph, and generates a TransitiveRule.

Run with: .venv/bin/python demos/demo_discovery.py
"""

import tempfile, os
from hyper3 import HypergraphMemory, Modality, Serializer

# ═══════════════════════════════════════════════════════════════════════
# SESSION 1: Build a knowledge graph, discover rules, reason, and save.
# ═══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("SESSION 1: Build knowledge, discover rules, persist")
print("=" * 70)

mem = HypergraphMemory(evolve_interval=0)

# Build a simple causal chain about an engine system.
# The repeating "causes" label creates the pattern that the discovery
# engine will detect: A-causes->B-causes->C is a transitive chain.
for label in ["ignition", "fuel_flow", "combustion", "heat", "engine_rotation", "electricity", "spark"]:
    mem.add(label, modalities={Modality.CONCEPTUAL})

mem.link("spark", "ignition", label="causes")
mem.link("ignition", "combustion", label="causes")
mem.link("combustion", "heat", label="causes")
mem.link("fuel_flow", "combustion", label="enables")
mem.link("combustion", "engine_rotation", label="causes")
mem.link("heat", "electricity", label="generates")

print(f"\n  Stored: {mem.size[0]} nodes, {mem.size[1]} edges")

# ── Rule Discovery ──────────────────────────────────────────────────
#
# auto_discover_and_apply() scans the graph for three pattern types:
#
#   1. Transitive patterns: edge labels that form chains (A-X->B-X->C).
#      The "causes" label appears in chains like spark->ignition->combustion->heat,
#      so the engine generates a TransitiveRule for "causes".
#
#   2. Inverse patterns: for each label X, the engine checks if there's
#      a complementary reverse label. If not, it suggests an InverseRule
#      that would create B-caused_by->A from A-causes->B.
#
#   3. Hub patterns: nodes with unusually high out-degree. These become
#      HubInferenceRules that propagate properties from hubs to their targets.
#
result = mem.auto_discover_and_apply()
print(f"\n  Rule discovery:")
print(f"    Total patterns:  {result['total_patterns']}")
print(f"    New rules added: {result['new_rules_added']}")
for dr in mem.discovery.get_discovered_rules():
    rule_info = f"rule={dr.rule.name}" if dr.rule else "no auto-rule"
    print(f"    [{dr.pattern_type}] {dr.pattern}  {rule_info}")

# ── Reasoning with discovered rules ─────────────────────────────────
#
# reason() applies all registered rules (both manually added and
# auto-discovered) to the graph via multiway expansion.
# Each rule finds matching patterns and produces new (inferred) edges.
print(f"\n  Reasoning with discovered rules...")
reason_result = mem.reason({"spark", "ignition", "combustion", "heat", "engine_rotation", "electricity", "fuel_flow"}, max_depth=3, max_total_states=20)
exp = reason_result["expansion"]
print(f"    States: {exp['states_created']}, Rules applied: {exp['rules_applied']}, Edges produced: {exp['edges_produced']}")

# ── Inferred knowledge ──────────────────────────────────────────────
#
# Edges marked with metadata.custom["inferred"] = True are new knowledge
# produced by the reasoning engine. The "rule" metadata field records
# which rule generated each edge.
print(f"\n  Inferred edges:")
for edge in mem.engine.graph.edges:
    if edge.metadata.custom.get("inferred"):
        src = [mem.engine.graph.get_node(n) for n in edge.source_ids]
        tgt = [mem.engine.graph.get_node(n) for n in edge.target_ids]
        print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")

# ── Persistence ─────────────────────────────────────────────────────
#
# save() serializes the complete system state to JSON:
#   - All nodes (labels, data, metadata, weights)
#   - All edges (source/target IDs, labels, weights)
#   - Event log entries
#   - Inferred edges (they become part of the graph)
#   - Discovered rules (they persist across sessions)
#
# Note: constructor parameters (evolve_interval, merge_threshold) are NOT
# saved. The loading instance must specify its own.
tmpdir = tempfile.mkdtemp()
save_path = os.path.join(tmpdir, "session.json")
mem.save(save_path)
print(f"\n  Saved to {save_path}")
print(f"  Final: {mem.size[0]} nodes, {mem.size[1]} edges")

# ═══════════════════════════════════════════════════════════════════════
# SESSION 2: Load the saved state and continue building.
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SESSION 2: Load persisted state, continue building")
print("=" * 70)

# Create a fresh instance and restore the saved state.
# The loaded graph includes all original nodes, edges, AND the inferred
# edges from session 1's reasoning.
mem2 = HypergraphMemory(evolve_interval=0)
mem2.load(save_path)
print(f"\n  Loaded: {mem2.size[0]} nodes, {mem2.size[1]} edges")
print(f"  Event log entries: {mem2.log.size}")

# Add new knowledge that extends the existing graph.
# These new edges create additional transitive chains that the
# discovered rules can exploit.
mem2.add("battery")
mem2.add("starter_motor")
mem2.link("battery", "electricity", label="supplies")
mem2.link("electricity", "starter_motor", label="powers")
mem2.link("starter_motor", "engine_rotation", label="causes")

print(f"  After additions: {mem2.size[0]} nodes, {mem2.size[1]} edges")

# Discover new patterns in the expanded graph.
# The new "causes" edge from starter_motor creates additional transitive
# chains that weren't present in session 1.
result2 = mem2.auto_discover_and_apply()
print(f"\n  New rule discovery: {result2.new_rules_added} new rules")

# Reason again with ALL rules (both session 1's rules and newly discovered ones).
# The multiway engine explores more branches because the graph is richer.
reason2 = mem2.reason({"battery", "starter_motor", "spark", "fuel_flow"}, max_depth=3, max_total_states=15)
exp2 = reason2.expansion
if exp2:
    print(f"  Reasoning: {exp2.rules_applied} rules applied, {exp2.edges_produced} edges produced")

# Show edges that are new in session 2 -- either produced by newly discovered
# rules or inferred from the expanded graph structure.
print(f"\n  New inferred edges in session 2:")
count = 0
for edge in mem2.engine.graph.edges:
    if edge.metadata.custom.get("inferred") and edge.metadata.custom.get("rule", "").startswith("discovered"):
        src = [mem2.engine.graph.get_node(n) for n in edge.source_ids]
        tgt = [mem2.engine.graph.get_node(n) for n in edge.target_ids]
        print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")
        count += 1
    elif edge.metadata.custom.get("inferred") and edge.id not in [e.id for e in mem.engine.graph.edges]:
        src = [mem2.engine.graph.get_node(n) for n in edge.source_ids]
        tgt = [mem2.engine.graph.get_node(n) for n in edge.target_ids]
        print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")
        count += 1
if count == 0:
    # Fallback: show all inferred edges if none matched the specific filters above.
    for edge in mem2.engine.graph.edges:
        if edge.metadata.custom.get("inferred"):
            src = [mem2.engine.graph.get_node(n) for n in edge.source_ids]
            tgt = [mem2.engine.graph.get_node(n) for n in edge.target_ids]
            print(f"    {[n.label for n in src if n]} --[{edge.label}]--> {[n.label for n in tgt if n]}")

print(f"\n  Session 2 final stats:")
stats = mem2.stats()
for k, v in stats.items():
    print(f"    {k}: {v}")

# Cleanup temporary files.
os.remove(save_path)
os.rmdir(tmpdir)
