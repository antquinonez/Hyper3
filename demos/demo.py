"""
Demonstration of hyper3's self-evolving hypergraph cognitive kernel.

This script walks through the core lifecycle of a HypergraphMemory instance:
  1. Building a knowledge graph from concepts and relationships
  2. Observer slices: viewing the same graph from different perspectives
  3. Equivalence merging: the graph deduplicates similar nodes automatically
  4. Weight decay: unused knowledge fades over time
  5. Reinforcement: frequently accessed knowledge grows stronger
  6. Dimensional traversal: filtering by modality (conceptual, abstract, etc.)
  7. Final system state

Key idea: The hypergraph is not a static data structure. It continuously
evolves -- decaying unused edges, merging equivalent nodes, and reinforcing
frequently accessed paths. This is the "self-evolving" part of Hyper3.

Run with: .venv/bin/python demos/demo.py
"""

from hyper3 import HypergraphMemory, Modality, AbstractionLayer

# Create a memory instance with auto-evolution DISABLED (evolve_interval=0).
# This keeps behavior deterministic for the demo. In production you'd set
# evolve_interval=10 or 50 to let the graph evolve automatically every N
# operations.
mem = HypergraphMemory(evolve_interval=0)

# --- 1. BUILD A KNOWLEDGE GRAPH -----------------------------------------
#
# Concepts are stored as nodes (Hypernodes) with optional metadata:
#   - modalities: semantic categories (CONCEPTUAL, ABSTRACT, CAUSAL, etc.)
#   - tags: arbitrary key-value pairs for filtering
#   - data: structured payload (any Python dict)
#
# Relationships are stored as directed edges (Hyperedges) with a semantic
# label like "requires", "enables", "implements". Edges can be bidirectional.
#
print("=" * 60)
print("1. BUILDING A KNOWLEDGE GRAPH")
print("=" * 60)

# Store concepts about patent law and hypergraph technology.
# Each mem.add() creates a node. The label is the human-readable identifier.
mem.add("patent law", modalities={Modality.CONCEPTUAL}, tags={"domain": "legal"})
mem.add("novelty", modalities={Modality.CONCEPTUAL}, tags={"domain": "legal"})
mem.add("non-obviousness", modalities={Modality.CONCEPTUAL}, tags={"domain": "legal"})
mem.add("hypergraph", modalities={Modality.CONCEPTUAL, Modality.ABSTRACT}, tags={"domain": "cs"})
mem.add("computational architecture", modalities={Modality.CONCEPTUAL}, tags={"domain": "cs"})
mem.add("dynamic instantiation", modalities={Modality.CONCEPTUAL}, tags={"domain": "cs"})
mem.add("token independence", modalities={Modality.CONCEPTUAL}, tags={"domain": "cs"})

# Link concepts with directed, labeled edges.
# "hypergraph" <-> "computational architecture" is bidirectional.
mem.link("patent law", "novelty", label="requires")
mem.link("patent law", "non-obviousness", label="requires")
mem.link("hypergraph", "computational architecture", label="enables", bidirectional=True)
mem.link("hypergraph", "dynamic instantiation", label="implements")
mem.link("hypergraph", "token independence", label="achieves")
mem.link("patent law", "hypergraph", label="applies to", bidirectional=True)

print(f"  Nodes: {mem.size[0]}, Edges: {mem.size[1]}")

# Print the adjacency structure: for each node, show its neighbors.
# This uses the raw graph API (mem.engine.graph) to traverse all nodes.
for node in mem.engine.graph.nodes:
    neighbor_nodes = [mem.engine.graph.get_node(nid) for nid in mem.engine.graph.neighbors(node.id)]
    neighbor_labels = [n.label for n in neighbor_nodes if n]
    print(f"  [{node.label}] -> {neighbor_labels}")
print()

# --- 2. OBSERVER SLICES: SAME GRAPH, DIFFERENT PERSPECTIVES -------------
#
# An "observer slice" is a filtered view of the graph, constrained by depth
# and size. It answers the question: "from this starting point, what can I
# see within N hops?" Different observers (users, tasks, subsystems) may
# need different views of the same underlying graph.
#
# recall() performs a traversal from a seed concept, returning reachable
# nodes within the specified depth and count limits.
#
print("=" * 60)
print("2. OBSERVER SLICES: SAME GRAPH, DIFFERENT PERSPECTIVES")
print("=" * 60)

print("\n  Narrow slice (depth=1, max=3) from 'patent law':")
# Depth=1 means one expansion step from the seed. Max_nodes=3 caps the result.
narrow = mem.recall("patent law", max_depth=1, max_nodes=3)
for n in narrow:
    print(f"    {n.label} (weight={n.weight:.2f})")

print("\n  Broad slice (depth=4, max=50) from 'patent law':")
# A deeper, wider traversal reveals the full connected component.
broad = mem.recall("patent law", max_depth=4, max_nodes=50)
for n in broad:
    print(f"    {n.label} (weight={n.weight:.2f})")
print()

# --- 3. EQUIVALENCE MERGING: THE GRAPH DEDUPLICATES ITSELF --------------
#
# Hyper3's GraphMaintenanceEngine can detect and merge equivalent nodes.
# Two nodes with matching data and overlapping neighborhoods are candidates
# for merging. When they merge, one absorbs the other's edges and records
# the absorbed label as an alias.
#
# Here we manually inject two duplicate nodes that have the same data as
# "novelty" to demonstrate the merging behavior.
#
print("=" * 60)
print("3. EQUIVALENCE MERGING: THE GRAPH DEDUPLICATES ITSELF")
print("=" * 60)

# Bypass the normal API to inject nodes with identical data payloads.
# Both "inventive step" and "inventive step criterion" share the same
# data string as "novelty", making them merge candidates.
from hyper3 import Hypernode
dup1 = Hypernode(label="inventive step", data="requirement for patentability",
                  metadata=mem.engine.graph.get_node(
                      [n for n in mem.engine.graph.nodes if n.label == "novelty"][0].id
                  ).metadata)
dup2 = Hypernode(label="inventive step criterion", data="requirement for patentability",
                  metadata=dup1.metadata)
mem.engine.graph.add_node(dup1)
mem.engine.graph.add_node(dup2)
mem.link("patent law", "inventive step", label="requires")
mem.link("patent law", "inventive step criterion", label="requires")

print(f"\n  Before merge: {mem.size[0]} nodes")
for n in mem.engine.graph.nodes:
    if "novelty" in n.label.lower():
        aliases = n.metadata.custom.get("aliases", [])
        print(f"    '{n.label}' aliases={aliases}")

# evolve() runs the full maintenance cycle: decay -> prune -> merge -> reinforce.
# The EquivalenceEngine identifies similar nodes and merges them.
report = mem.evolve()
print(f"\n  Evolve report: merged={report['merged']}, pruned={report['pruned']}")
print(f"  After merge: {mem.size[0]} nodes")
for n in mem.engine.graph.nodes:
    if "novelty" in n.label.lower():
        aliases = n.metadata.custom.get("aliases", [])
        print(f"    '{n.label}' aliases={aliases}")
print()

# --- 4. WEIGHT DECAY AND PRUNING: FORGET WHAT'S UNUSED ------------------
#
# Nodes have a weight that represents their importance. The maintenance
# engine decays weights on inactive nodes (those not recently accessed).
# When weight drops below a threshold, the node is pruned (removed).
#
# This models "forgetting" -- knowledge that isn't used gradually fades.
#
print("=" * 60)
print("4. WEIGHT DECAY: WHAT'S UNUSED FADES")
print("=" * 60)

mem.add("ephemeral concept A", tags={"temporary": True})
mem.add("ephemeral concept B", tags={"temporary": True})

# Find the freshly-added node to track its weight.
node_a = None
for n in mem.engine.graph.nodes:
    if n.label == "ephemeral concept A":
        node_a = n
        break

print(f"\n  '{node_a.label}' initial weight: {node_a.weight:.4f}")

# Simulate 20 decay cycles: multiply weight by 0.7 each time.
# After 20 cycles: 1.0 * 0.7^20 ≈ 0.0008, well below any reasonable threshold.
for _ in range(20):
    n = mem.engine.graph.get_node(node_a.id)
    if n:
        n.weight *= 0.7

node_a = mem.engine.graph.get_node(node_a.id)
if node_a:
    print(f"  After 20 decay cycles: {node_a.weight:.6f}")
else:
    print(f"  Already pruned during auto-evolve")

# evolve() will prune the decayed node if its weight is below the threshold.
report = mem.evolve()
print(f"  Evolve report: pruned={report['pruned']}")
survived = mem.engine.graph.get_node(node_a.id) if node_a else None
print(f"  'ephemeral concept A' survived? {survived is not None}")

# Concept B was never decayed, so it should still be healthy.
ephemeral_b = None
for n in mem.engine.graph.nodes:
    if n.label == "ephemeral concept B":
        ephemeral_b = n
if ephemeral_b:
    print(f"  'ephemeral concept B' weight: {ephemeral_b.weight:.4f} (untouched, still healthy)")
print()

# --- 5. REINFORCEMENT: WHAT'S USED GROWS STRONGER -----------------------
#
# The flip side of decay: every time a concept is stored or recalled, its
# weight increases. Frequently-used paths through the graph get reinforced,
# making them easier to find in future traversals.
#
print("=" * 60)
print("5. REINFORCEMENT: WHAT'S USED GROWS STRONGER")
print("=" * 60)

hl = None
for n in mem.engine.graph.nodes:
    if n.label == "hypergraph":
        hl = n
        break

print(f"\n  'hypergraph' initial weight: {hl.weight:.2f}")

# Each add() + get() cycle reinforces the node (increases its weight).
for _ in range(5):
    mem.add("hypergraph")
    mem.get("hypergraph")
print(f"  After 5 store+recall cycles: {hl.weight:.2f}")

# Explicit reinforcement with a custom boost factor.
# This is what the maintenance engine does internally for frequently-used paths.
mem._evolution.reinforce(hl.id, boost=3.0)
print(f"  After explicit reinforce(boost=3.0): {hl.weight:.2f}")
print()

# --- 6. DIMENSIONAL TRAVERSAL: EXPLORE BY MODALITY ---------------------
#
# The graph supports dimensional filtering: you can traverse only the
# subgraph that matches a particular modality. This is useful when an
# observer only cares about one aspect of the knowledge (e.g., only
# abstract concepts, or only causal relationships).
#
# query() with a modality filter returns nodes reachable from the seed
# that carry the specified modality tag.
#
print("=" * 60)
print("6. DIMENSIONAL TRAVERSAL: EXPLORE BY MODALITY")
print("=" * 60)

conceptual = mem.query("patent law", modality=Modality.CONCEPTUAL)
print(f"\n  Traversing CONCEPTUAL dimension from 'patent law':")
for n in conceptual:
    print(f"    {n.label} (modalities={[m.value for m in n.metadata.modality_tags]})")

# "hypergraph" is tagged with both CONCEPTUAL and ABSTRACT, so it appears
# in both dimensional traversals.
print(f"\n  Traversing ABSTRACT dimension from 'hypergraph':")
abstract = mem.query("hypergraph", modality=Modality.ABSTRACT)
for n in abstract:
    print(f"    {n.label} (modalities={[m.value for m in n.metadata.modality_tags]})")
print()

# --- 7. FULL STATS -------------------------------------------------------
print("=" * 60)
print("7. FINAL SYSTEM STATE")
print("=" * 60)
print()
for k, v in mem.stats().items():
    print(f"  {k}: {v}")
