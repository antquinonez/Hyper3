"""
Knowledge Graph Basics
======================

This example demonstrates the foundational operations of Hyper3:
storing concepts, creating relationships, querying the graph,
and using the recall/retrieve API.

Use case: Building a medical symptoms knowledge base.

A doctor wants to encode symptom-disease relationships so that
given a symptom, the system can recall related conditions and
treatments through graph traversal.

Run with:
    .venv/bin/python examples/basic/01_knowledge_basics.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, Modality


def main():
    # Initialize the cognitive memory. evolve_interval=0 disables
    # automatic evolution cycles, keeping behavior deterministic
    # for this example.
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Storing Concepts
    # =====================================================================
    # Concepts are stored with optional metadata (data dict), modality
    # tags (which perception channel this concept belongs to), and
    # abstraction layer (detail vs summary).

    print("=" * 70)
    print("SECTION 1: Storing Concepts")
    print("=" * 70)

    # Store diseases
    mem.store("influenza", data={"icd10": "J11.1", "category": "viral"},
              modalities={Modality.CONCEPTUAL})
    mem.store("pneumonia", data={"icd10": "J18.9", "category": "bacterial"},
              modalities={Modality.CONCEPTUAL})
    mem.store("migraine", data={"icd10": "G43.9", "category": "neurological"},
              modalities={Modality.CONCEPTUAL})
    mem.store("hypertension", data={"icd10": "I10", "category": "cardiovascular"},
              modalities={Modality.CONCEPTUAL})

    # Store symptoms
    mem.store("fever", data={"type": "symptom", "severity_scale": "mild-severe"},
              modalities={Modality.SENSORY})
    mem.store("cough", data={"type": "symptom", "character": "dry_or_productive"},
              modalities={Modality.SENSORY})
    mem.store("headache", data={"type": "symptom", "location": "generalized"},
              modalities={Modality.SENSORY})
    mem.store("fatigue", data={"type": "symptom", "duration": "acute_or_chronic"},
              modalities={Modality.SENSORY})
    mem.store("chest_pain", data={"type": "symptom", "urgency": "high"},
              modalities={Modality.SENSORY})

    # Store treatments
    mem.store("oseltamivir", data={"type": "antiviral", "brand": "Tamiflu"})
    mem.store("antibiotics", data={"type": "antibacterial", "spectrum": "broad"})
    mem.store("triptans", data={"type": "migraine_specific", "route": "oral"})
    mem.store("lisinopril", data={"type": "ace_inhibitor", "dose_mg": 10})

    print(f"  Stored {mem.graph.node_count} concepts")
    print()

    # =====================================================================
    # SECTION 2: Creating Relationships
    # =====================================================================
    # relate() connects two concepts with a labeled edge. The label
    # describes the relationship type and is used by rule engines
    # for pattern matching.

    print("=" * 70)
    print("SECTION 2: Creating Relationships")
    print("=" * 70)

    # Disease -> Symptom (causes)
    mem.relate("influenza", "fever", label="causes")
    mem.relate("influenza", "cough", label="causes")
    mem.relate("influenza", "headache", label="causes")
    mem.relate("influenza", "fatigue", label="causes")
    mem.relate("pneumonia", "fever", label="causes")
    mem.relate("pneumonia", "cough", label="causes")
    mem.relate("pneumonia", "chest_pain", label="causes")
    mem.relate("migraine", "headache", label="causes")
    mem.relate("hypertension", "headache", label="causes")
    mem.relate("hypertension", "chest_pain", label="causes")
    mem.relate("hypertension", "fatigue", label="causes")

    # Disease -> Treatment (treated_by)
    mem.relate("influenza", "oseltamivir", label="treated_by")
    mem.relate("pneumonia", "antibiotics", label="treated_by")
    mem.relate("migraine", "triptans", label="treated_by")
    mem.relate("hypertension", "lisinopril", label="treated_by")

    # Symptom similarity
    mem.relate("fever", "fatigue", label="co_occurs_with", bidirectional=True)
    mem.relate("headache", "fatigue", label="co_occurs_with", bidirectional=True)

    print(f"  Created {mem.graph.edge_count} relationships")
    print()

    # =====================================================================
    # SECTION 3: Basic Recall
    # =====================================================================
    # recall() finds a concept and its neighborhood up to a given depth.
    # It returns a list of Hypernodes that are connected to the seed.

    print("=" * 70)
    print("SECTION 3: Basic Recall")
    print("=" * 70)

    # Recall everything connected to "influenza" within 2 hops
    related = mem.recall("influenza", max_depth=2)
    print(f"  Recalled {len(related)} concepts related to influenza:")
    for node in related:
        node_type = node.data.get("type", node.data.get("category", "unknown")) if isinstance(node.data, dict) else "concept"
        print(f"    {node.label:20s} [{node_type}]")
    print()

    # =====================================================================
    # SECTION 4: Traversal Strategies
    # =====================================================================
    # query() supports different traversal strategies: bfs (breadth-first)
    # and dfs (depth-first). You can also filter by modality.

    print("=" * 70)
    print("SECTION 4: Traversal Strategies")
    print("=" * 70)

    # BFS traversal from "fever" (explores neighbors level by level)
    bfs_results = mem.query("fever", strategy="bfs", max_depth=2)
    bfs_labels = [n.label for n in bfs_results]
    print(f"  BFS from 'fever': {bfs_labels}")

    # DFS traversal from "fever" (follows paths deeply before backtracking)
    dfs_results = mem.query("fever", strategy="dfs", max_depth=2)
    dfs_labels = [n.label for n in dfs_results]
    print(f"  DFS from 'fever': {dfs_labels}")

    # Modality-filtered query: only sensory concepts
    sensory = mem.query("fever", modality=Modality.SENSORY, max_depth=3)
    sensory_labels = [n.label for n in sensory]
    print(f"  Sensory modality from 'fever': {sensory_labels}")
    print()

    # =====================================================================
    # SECTION 5: Pattern Matching
    # =====================================================================
    # pattern_match() finds edges by label, source, or target.
    # Useful for finding all edges of a specific type.

    print("=" * 70)
    print("SECTION 5: Pattern Matching")
    print("=" * 70)

    # Find all "causes" relationships
    causes = mem.pattern_match(edge_label="causes")
    print(f"  Found {len(causes)} 'causes' relationships:")
    for match in causes:
        src_labels = [mem.graph.get_node(sid).label for sid in match["source_ids"] if mem.graph.get_node(sid)]
        tgt_labels = [mem.graph.get_node(tid).label for tid in match["target_ids"] if mem.graph.get_node(tid)]
        print(f"    {src_labels[0]} --[causes]--> {tgt_labels[0]}")

    # Find all edges pointing to "headache"
    headache_causes = mem.pattern_match(target_label="headache", edge_label="causes")
    print(f"\n  Diseases that cause headache: {len(headache_causes)}")
    for match in headache_causes:
        src_labels = [mem.graph.get_node(sid).label for sid in match["source_ids"] if mem.graph.get_node(sid)]
        print(f"    {src_labels[0]}")
    print()

    # =====================================================================
    # SECTION 6: Subgraph Extraction
    # =====================================================================
    # subgraph() extracts the induced subgraph for a set of concepts.

    print("=" * 70)
    print("SECTION 6: Subgraph Extraction")
    print("=" * 70)

    respiratory = mem.subgraph({"influenza", "pneumonia", "fever", "cough",
                                 "oseltamivir", "antibiotics"})
    print(f"  Respiratory subgraph: {respiratory['nodes']} nodes, {respiratory['edges']} edges")
    print()

    # =====================================================================
    # SECTION 7: Event Log
    # =====================================================================
    # Every operation is logged. The event log is an append-only record
    # of all mutations to the cognitive memory.

    print("=" * 70)
    print("SECTION 7: Event Log")
    print("=" * 70)

    print(f"  Total events logged: {mem.log.size}")
    # Show the most recent events
    recent = mem.log.query()[-5:]
    print("  Last 5 events:")
    for event in recent:
        print(f"    {event.get('event_type', 'unknown')}: {event}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Nodes: {stats['nodes']}")
    print(f"  Edges: {stats['edges']}")
    print(f"  Events: {stats['log_size']}")
    print(f"  Connected components: {stats['components']}")
    print(f"  Has cycles: {stats['cycles']}")
    print()


if __name__ == "__main__":
    main()
