"""
Demonstration of hyper3's self-evolving hypergraph cognitive kernel.

Run with: .venv/bin/python demo.py
"""

from hyper3 import HypergraphMemory, Modality, AbstractionLayer

mem = HypergraphMemory(evolve_interval=0)

# --- 1. BUILD A KNOWLEDGE GRAPH -----------------------------------------
print("=" * 60)
print("1. BUILDING A KNOWLEDGE GRAPH")
print("=" * 60)

mem.store("patent law", modalities={Modality.CONCEPTUAL}, tags={"domain": "legal"})
mem.store("novelty", modalities={Modality.CONCEPTUAL}, tags={"domain": "legal"})
mem.store("non-obviousness", modalities={Modality.CONCEPTUAL}, tags={"domain": "legal"})
mem.store("hypergraph", modalities={Modality.CONCEPTUAL, Modality.ABSTRACT}, tags={"domain": "cs"})
mem.store("computational architecture", modalities={Modality.CONCEPTUAL}, tags={"domain": "cs"})
mem.store("dynamic instantiation", modalities={Modality.CONCEPTUAL}, tags={"domain": "cs"})
mem.store("token independence", modalities={Modality.CONCEPTUAL}, tags={"domain": "cs"})

mem.relate("patent law", "novelty", label="requires")
mem.relate("patent law", "non-obviousness", label="requires")
mem.relate("hypergraph", "computational architecture", label="enables", bidirectional=True)
mem.relate("hypergraph", "dynamic instantiation", label="implements")
mem.relate("hypergraph", "token independence", label="achieves")
mem.relate("patent law", "hypergraph", label="applies to", bidirectional=True)

print(f"  Nodes: {mem.graph.node_count}, Edges: {mem.graph.edge_count}")
for node in mem.graph.nodes:
    neighbor_nodes = [mem.graph.get_node(nid) for nid in mem.graph.neighbors(node.id)]
    neighbor_labels = [n.label for n in neighbor_nodes if n]
    print(f"  [{node.label}] -> {neighbor_labels}")
print()

# --- 2. OBSERVER SLICES: SAME GRAPH, DIFFERENT PERSPECTIVES -------------
print("=" * 60)
print("2. OBSERVER SLICES: SAME GRAPH, DIFFERENT PERSPECTIVES")
print("=" * 60)

print("\n  Narrow slice (depth=1, max=3) from 'patent law':")
narrow = mem.recall("patent law", max_depth=1, max_nodes=3)
for n in narrow:
    print(f"    {n.label} (weight={n.weight:.2f})")

print("\n  Broad slice (depth=4, max=50) from 'patent law':")
broad = mem.recall("patent law", max_depth=4, max_nodes=50)
for n in broad:
    print(f"    {n.label} (weight={n.weight:.2f})")
print()

# --- 3. EQUIVALENCE MERGING: THE GRAPH DEDUPLICATES ITSELF --------------
print("=" * 60)
print("3. EQUIVALENCE MERGING: THE GRAPH DEDUPLICATES ITSELF")
print("=" * 60)

# Bypass cache to inject duplicate nodes with matching data
from hyper3 import Hypernode
dup1 = Hypernode(label="inventive step", data="requirement for patentability",
                  metadata=mem.graph.get_node(
                      [n for n in mem.graph.nodes if n.label == "novelty"][0].id
                  ).metadata)
dup2 = Hypernode(label="inventive step criterion", data="requirement for patentability",
                  metadata=dup1.metadata)
mem.graph.add_node(dup1)
mem.graph.add_node(dup2)
mem.relate("patent law", "inventive step", label="requires")
mem.relate("patent law", "inventive step criterion", label="requires")

print(f"\n  Before merge: {mem.graph.node_count} nodes")
for n in mem.graph.nodes:
    if "novelty" in n.label.lower():
        aliases = n.metadata.custom.get("aliases", [])
        print(f"    '{n.label}' aliases={aliases}")

report = mem.evolve()
print(f"\n  Evolve report: merged={report['merged']}, pruned={report['pruned']}")
print(f"  After merge: {mem.graph.node_count} nodes")
for n in mem.graph.nodes:
    if "novelty" in n.label.lower():
        aliases = n.metadata.custom.get("aliases", [])
        print(f"    '{n.label}' aliases={aliases}")
print()

# --- 4. WEIGHT DECAY AND PRUNING: FORGET WHAT'S UNUSED ------------------
print("=" * 60)
print("4. WEIGHT DECAY: WHAT'S UNUSED FADES")
print("=" * 60)

mem.store("ephemeral concept A", tags={"temporary": True})
mem.store("ephemeral concept B", tags={"temporary": True})
node_a = None
for n in mem.graph.nodes:
    if n.label == "ephemeral concept A":
        node_a = n
        break

print(f"\n  '{node_a.label}' initial weight: {node_a.weight:.4f}")

for _ in range(20):
    n = mem.graph.get_node(node_a.id)
    if n:
        n.weight *= 0.7

node_a = mem.graph.get_node(node_a.id)
if node_a:
    print(f"  After 20 decay cycles: {node_a.weight:.6f}")
else:
    print(f"  Already pruned during auto-evolve")

report = mem.evolve()
print(f"  Evolve report: pruned={report['pruned']}")
survived = mem.graph.get_node(node_a.id) if node_a else None
print(f"  'ephemeral concept A' survived? {survived is not None}")
ephemeral_b = None
for n in mem.graph.nodes:
    if n.label == "ephemeral concept B":
        ephemeral_b = n
if ephemeral_b:
    print(f"  'ephemeral concept B' weight: {ephemeral_b.weight:.4f} (untouched, still healthy)")
print()

# --- 5. REINFORCEMENT: WHAT'S USED GROWS STRONGER -----------------------
print("=" * 60)
print("5. REINFORCEMENT: WHAT'S USED GROWS STRONGER")
print("=" * 60)

hl = None
for n in mem.graph.nodes:
    if n.label == "hypergraph":
        hl = n
        break

print(f"\n  'hypergraph' initial weight: {hl.weight:.2f}")
for _ in range(5):
    mem.store("hypergraph")
    mem.recall("hypergraph")
print(f"  After 5 store+recall cycles: {hl.weight:.2f}")

mem._evolution.reinforce(hl.id, boost=3.0)
print(f"  After explicit reinforce(boost=3.0): {hl.weight:.2f}")
print()

# --- 6. DIMENSIONAL TRAVERSAL: EXPLORE BY MODALITY ---------------------
print("=" * 60)
print("6. DIMENSIONAL TRAVERSAL: EXPLORE BY MODALITY")
print("=" * 60)

conceptual = mem.query("patent law", modality=Modality.CONCEPTUAL)
print(f"\n  Traversing CONCEPTUAL dimension from 'patent law':")
for n in conceptual:
    print(f"    {n.label} (modalities={[m.value for m in n.metadata.modality_tags]})")

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
