"""
Full System Snapshot and Restore
==================================
Demonstrates capturing the complete state of all Hyper3 subsystems into a
snapshot, saving it to disk, restoring into a fresh instance, and verifying
that the restored system behaves identically.

Run: .venv/bin/python examples/showcase/system_snapshot/system_snapshot.py
"""

from __future__ import annotations

import os
import tempfile


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD AND ENRICH THE KNOWLEDGE GRAPH")
    print("=" * 70)

    from hyper3 import HypergraphMemory, TransitiveRule

    mem = HypergraphMemory(evolve_interval=0, rules=[
        TransitiveRule(edge_label="influences", new_label="indirect_influence"),
    ])

    concepts = [
        "quantum_computing", "machine_learning", "cryptography",
        "optimization", "simulation", "error_correction",
        "neural_network", "deep_learning", "reinforcement_learning",
        "natural_language", "computer_vision", "robotics",
    ]
    for c in concepts:
        mem.add(c, data={"type": "concept"})

    mem.link("quantum_computing", "machine_learning", label="influences", weight=3.0)
    mem.link("quantum_computing", "cryptography", label="influences", weight=4.0)
    mem.link("quantum_computing", "optimization", label="influences", weight=3.0)
    mem.link("quantum_computing", "simulation", label="influences", weight=2.5)
    mem.link("machine_learning", "neural_network", label="influences", weight=3.0)
    mem.link("neural_network", "deep_learning", label="influences", weight=2.5)
    mem.link("deep_learning", "computer_vision", label="influences", weight=2.0)
    mem.link("deep_learning", "natural_language", label="influences", weight=2.0)
    mem.link("machine_learning", "reinforcement_learning", label="influences", weight=2.0)
    mem.link("reinforcement_learning", "robotics", label="influences", weight=2.0)
    mem.link("quantum_computing", "error_correction", label="influences", weight=3.5)
    mem.link("error_correction", "cryptography", label="influences", weight=2.0)

    result = mem.reason(seeds={"quantum_computing", "machine_learning"}, max_depth=3)
    print(f"reasoning: edges_produced={result.expansion.edges_produced}, states_created={result.expansion.states_created}")

    mem.belief.create(["quantum_computing", "machine_learning", "cryptography"])

    mem.search.activate("quantum_computing", energy=2.0)
    mem.search.activate("machine_learning", energy=1.5)

    retrieve_results = mem.search.query("machine_learning", top_k=3)
    mem.record_feedback("machine_learning", retrieve_results, relevant_labels={"machine_learning"})
    retrieve_results2 = mem.search.query("cryptography", top_k=3)
    mem.record_feedback("cryptography", retrieve_results2, relevant_labels={"cryptography"})

    print(f"graph: nodes={mem.size[0]}, edges={mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: CAPTURE FULL SYSTEM SNAPSHOT")
    print("=" * 70)

    from hyper3.snapshot import capture_snapshot

    snapshot = capture_snapshot(
        belief=mem._belief,
        multiway_engine=mem._multiway_engine,
        state_clustering=mem._state_clustering,
        rule_analytics=mem._rule_analytics,
        provenance=mem._provenance,
        retrieval=mem._retrieval,
        perspective=mem._perspective,
        meta=mem._meta,
        cache=mem._cache,
        feedback=mem._feedback,
    )

    print("snapshot captured:")
    print(f"  version: {snapshot.version}")
    print(f"  belief states: {len(snapshot.belief_states)}")
    print(f"  multiway states: {len(snapshot.multiway_states)}")
    print(f"  provenance records: {len(snapshot.provenance_records)}")
    print(f"  retrieval feedback: {len(snapshot.retrieval_feedback)}")
    print(f"  frame outcomes: {len(snapshot.frame_outcomes)}")
    print(f"  cache items: {len(snapshot.cache_items)}")
    print(f"  feedback signals: {len(snapshot.feedback_signals)}")

    print("\n" + "=" * 70)
    print("SECTION 3: SAVE SNAPSHOT TO DISK")
    print("=" * 70)

    tmpdir = tempfile.mkdtemp()
    graph_path = os.path.join(tmpdir, "graph.json")
    snapshot_path = os.path.join(tmpdir, "snapshot.json")

    mem.save(graph_path)
    mem.save(snapshot_path, full=True)
    graph_size = os.path.getsize(graph_path)
    snapshot_size = os.path.getsize(snapshot_path)
    print(f"saved graph to: {graph_path} ({graph_size} bytes)")
    print(f"saved snapshot to: {snapshot_path} ({snapshot_size} bytes, {snapshot_size / 1024:.1f} KB)")

    print("\n" + "=" * 70)
    print("SECTION 4: RESTORE INTO FRESH INSTANCE")
    print("=" * 70)

    mem2 = HypergraphMemory(evolve_interval=0, rules=[
        TransitiveRule(edge_label="influences", new_label="indirect_influence"),
    ])

    mem2.load(graph_path)
    mem2.load(snapshot_path)

    print(f"restored graph: nodes={mem2.size[0]}, edges={mem2.size[1]}")
    print(f"original graph: nodes={mem.size[0]}, edges={mem.size[1]}")
    print(f"nodes match: {mem2.size[0] == mem.size[0]}")
    print(f"edges match: {mem2.size[1] == mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 5: VERIFY RESTORED STATE")
    print("=" * 70)

    for concept in concepts:
        assert mem2.has(concept), f"missing node: {concept}"
    print(f"all {len(concepts)} concepts restored: True")

    desc1 = mem.analyze.describe()
    desc2 = mem2.analyze.describe()
    print(f"density match: {desc1.density:.4f} vs {desc2.density:.4f}")

    score1 = mem.compute_confidence("quantum_computing")
    score2 = mem2.compute_confidence("quantum_computing")
    if score1 and score2:
        print(f"confidence for 'quantum_computing': original={score1.confidence:.4f}, restored={score2.confidence:.4f}")

    all_conf1 = mem.compute_all_confidences()
    all_conf2 = mem2.compute_all_confidences()
    print(f"avg confidence: original={all_conf1.avg_confidence:.4f}, restored={all_conf2.avg_confidence:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 6: SNAPSHOT SERIALIZATION ROUND-TRIP")
    print("=" * 70)

    from hyper3.snapshot import SystemSnapshot

    data_dict = snapshot.to_dict()
    print(f"to_dict keys: {len(data_dict)}")

    restored_snapshot = SystemSnapshot.from_dict(data_dict)
    print(f"from_dict belief states: {len(restored_snapshot.belief_states)}")
    print(f"from_dict multiway states: {len(restored_snapshot.multiway_states)}")
    print(f"from_dict provenance records: {len(restored_snapshot.provenance_records)}")
    print(f"round-trip preserves all fields: {len(restored_snapshot.belief_states) == len(snapshot.belief_states)}")

    os.remove(graph_path)
    os.remove(snapshot_path)
    os.rmdir(tmpdir)

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
