"""
Graph Versioning, Diffing, and Rollback
=========================================
Demonstrates version control for knowledge graphs using GraphDiffer. Shows how
to capture versions, compute diffs between them, maintain a version history,
and roll back to a previous state when mistakes are made.

Run: .venv/bin/python examples/showcase/workflow/graph_versioning/graph_versioning.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD INITIAL GRAPH AND CAPTURE BASELINE")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    topics = ["machine_learning", "neural_networks", "nlp", "computer_vision"]
    authors = ["alice_chen", "bob_smith", "carol_wu"]
    papers = ["paper_transformer", "paper_cnn", "paper_gan"]
    institutions = ["mit", "stanford"]

    for t in topics:
        mem.add(t, data={"type": "topic"})
    for a in authors:
        mem.add(a, data={"type": "author"})
    for p in papers:
        mem.add(p, data={"type": "paper"})
    for i in institutions:
        mem.add(i, data={"type": "institution"})

    mem.link("alice_chen", "mit", label="affiliated_with", weight=1.0)
    mem.link("bob_smith", "stanford", label="affiliated_with", weight=1.0)
    mem.link("carol_wu", "mit", label="affiliated_with", weight=1.0)
    mem.link("alice_chen", "paper_transformer", label="writes", weight=1.0)
    mem.link("bob_smith", "paper_cnn", label="writes", weight=1.0)
    mem.link("carol_wu", "paper_gan", label="writes", weight=1.0)
    mem.link("paper_transformer", "nlp", label="cites", weight=2.0)
    mem.link("paper_cnn", "computer_vision", label="cites", weight=2.0)
    mem.link("paper_gan", "computer_vision", label="cites", weight=1.5)

    v0 = mem.capture_version()
    print(f"v0 captured: version_id={v0['version_id']}, nodes={v0['node_count']}, edges={v0['edge_count']}")

    print("\n" + "=" * 70)
    print("SECTION 2: FIRST EDIT SESSION - ADD COLLABORATIONS")
    print("=" * 70)

    mem.link("alice_chen", "carol_wu", label="collaborates_with", weight=2.0)
    mem.link("bob_smith", "carol_wu", label="collaborates_with", weight=1.5)
    mem.add("paper_diffusion", data={"type": "paper"})
    mem.link("alice_chen", "paper_diffusion", label="writes", weight=1.0)
    mem.link("carol_wu", "paper_diffusion", label="writes", weight=1.0)
    mem.link("paper_diffusion", "machine_learning", label="cites", weight=2.5)

    v1 = mem.capture_version()
    print(f"v1 captured: version_id={v1['version_id']}, nodes={v1['node_count']}, edges={v1['edge_count']}")

    delta = mem.diff_from_version(v0["version_id"])
    if delta:
        print("\ndelta v0 -> v1:")
        print(f"  total changes: {delta.total_changes}")
        print(f"  nodes added: {len(delta.nodes_added)}")
        print(f"  edges added: {len(delta.edges_added)}")
        for nd in delta.nodes_added:
            print(f"    +node: {nd.node_label}")
        for ed in delta.edges_added:
            print(f"    +edge: {ed.source_label} -[{ed.new_label}]-> {ed.target_label}")

    print("\n" + "=" * 70)
    print("SECTION 3: SECOND EDIT SESSION - CROSS-DOMAIN LINKS")
    print("=" * 70)

    mem.link("nlp", "computer_vision", label="cross_domain", weight=1.0)
    mem.link("machine_learning", "nlp", label="subfield_of", weight=1.0)

    v2 = mem.capture_version()
    print(f"v2 captured: version_id={v2['version_id']}, nodes={v2['node_count']}, edges={v2['edge_count']}")

    delta_v1_v2 = mem.diff_between_versions(v1["version_id"], v2["version_id"])
    if delta_v1_v2:
        print("\ndelta v1 -> v2:")
        print(f"  total changes: {delta_v1_v2.total_changes}")
        print(f"  edges added: {len(delta_v1_v2.edges_added)}")
        for ed in delta_v1_v2.edges_added:
            print(f"    +edge: {ed.source_label} -[{ed.new_label}]-> {ed.target_label}")

    print("\n" + "=" * 70)
    print("SECTION 4: VERSION HISTORY")
    print("=" * 70)

    history = mem.version_history()
    print(f"total versions: {history.total_versions}")
    print(f"current version: {history.current_version}")
    for v in history.versions:
        print(f"  v{v.version_id}: nodes={v.node_count}, edges={v.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 5: ERRONEOUS EDIT AND ROLLBACK")
    print("=" * 70)

    mem.add("bad_node_1", data={"type": "error"})
    mem.add("bad_node_2", data={"type": "error"})
    mem.link("bad_node_1", "alice_chen", label="spurious", weight=0.1)
    mem.link("bad_node_2", "paper_cnn", label="spurious", weight=0.1)
    mem.link("nlp", "bad_node_1", label="spurious", weight=0.1)

    print(f"before rollback: nodes={mem.size[0]}, edges={mem.size[1]}")

    rollback_delta = mem.diff_from_version(v2["version_id"])
    if rollback_delta:
        print(f"changes to undo: {rollback_delta.total_changes}")
        for nd in rollback_delta.nodes_added:
            print(f"  will remove node: {nd.node_label}")
        for ed in rollback_delta.edges_added:
            print(f"  will remove edge: {ed.source_label} -[{ed.new_label}]-> {ed.target_label}")

    mem.capture_version()

    print(f"\nperforming rollback to v{v2['version_id']}...")

    if mem.differ:
        mem.differ.rollback_to_version(v2["version_id"])

    print(f"after rollback: nodes={mem.size[0]}, edges={mem.size[1]}")

    has_bad = mem.has("bad_node_1") or mem.has("bad_node_2")
    print(f"bad nodes removed: {not has_bad}")

    print("\n" + "=" * 70)
    print("SECTION 6: DIFF FROM ARBITRARY SNAPSHOT")
    print("=" * 70)

    snapshot = {
        "nodes": {"fake_id": {"label": "external_node", "data": None, "weight": 1.0, "access_count": 0}},
        "edges": {},
        "node_count": 1,
        "edge_count": 0,
    }

    if mem.differ:
        snap_delta = mem.differ.diff_from_snapshot(snapshot)
        print("diff from external snapshot:")
        print(f"  current nodes: {snap_delta.node_count_after}")
        print(f"  snapshot nodes: {snap_delta.node_count_before}")
        print(f"  nodes added: {len(snap_delta.nodes_added)}")
        print(f"  edges added: {len(snap_delta.edges_added)}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
