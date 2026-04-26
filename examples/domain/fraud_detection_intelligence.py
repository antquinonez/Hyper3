"""
Fraud Detection Intelligence
=============================

Demonstrates lazy multiway expansion, traversal prefetching,
and partial proof generation in a financial fraud detection scenario.

Use case: A bank's fraud detection system explores multiple transaction
interpretations lazily, prefetches likely investigation paths, and
generates partial proofs for suspicious activity reports.

Run with:
    .venv/bin/python examples/domain/fraud_detection_intelligence.py
"""

from __future__ import annotations

from hyper3 import (
    CognitiveMemory,
    Hyperedge,
    Modality,
    PartialProof,
    TransfiniteReasoner,
    TransitiveRule,
)
from hyper3.multiway import MultiwayEngine


def main():
    mem = CognitiveMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Financial Transaction Network Setup")
    print("=" * 70)

    persons = {
        "alice_suspect": {"role": "primary_suspect", "risk_score": 0.92, "flagged": True},
        "bob_associate": {"role": "associate", "risk_score": 0.71, "flagged": True},
        "charlie_runner": {"role": "runner", "risk_score": 0.65, "flagged": False},
        "diana_victim": {"role": "victim", "risk_score": 0.10, "flagged": False},
        "eve_mule": {"role": "money_mule", "risk_score": 0.80, "flagged": True},
    }
    entities = {
        "shell_corp": {"type": "business", "jurisdiction": "Cayman_Islands", "suspicious": True},
        "front_company": {"type": "business", "jurisdiction": "Panama", "suspicious": True},
        "crypto_exchange": {"type": "exchange", "kyc_level": "minimal", "suspicious": True},
        "legit_merchant": {"type": "merchant", "kyc_level": "full", "suspicious": False},
        "offshore_bank": {"type": "bank", "jurisdiction": "Switzerland", "suspicious": True},
    }
    txns = {
        "tx_001": {"amount": 49500, "currency": "USD", "just_under_ctr": True},
        "tx_002": {"amount": 49900, "currency": "USD", "just_under_ctr": True},
        "tx_003": {"amount": 49800, "currency": "USD", "just_under_ctr": True},
        "tx_004": {"amount": 150000, "currency": "USD", "sudden_large": True},
        "tx_005": {"amount": 250000, "currency": "USD", "international": True},
    }

    all_data = {**persons, **entities, **txns}
    for name, data in all_data.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    transfer_edges = [
        ("alice_suspect", "bob_associate", "transfers"),
        ("bob_associate", "charlie_runner", "transfers"),
        ("charlie_runner", "eve_mule", "transfers"),
        ("eve_mule", "crypto_exchange", "transfers"),
        ("crypto_exchange", "offshore_bank", "transfers"),
        ("alice_suspect", "shell_corp", "transfers"),
        ("shell_corp", "front_company", "transfers"),
        ("front_company", "offshore_bank", "transfers"),
        ("offshore_bank", "alice_suspect", "transfers"),
        ("diana_victim", "alice_suspect", "transfers"),
        ("alice_suspect", "legit_merchant", "transfers"),
    ]
    purchase_edges = [
        ("alice_suspect", "tx_001", "originates"),
        ("alice_suspect", "tx_002", "originates"),
        ("alice_suspect", "tx_003", "originates"),
        ("alice_suspect", "tx_004", "originates"),
        ("alice_suspect", "tx_005", "originates"),
        ("tx_001", "bob_associate", "pays"),
        ("tx_002", "charlie_runner", "pays"),
        ("tx_003", "eve_mule", "pays"),
        ("tx_004", "shell_corp", "pays"),
        ("tx_005", "offshore_bank", "pays"),
    ]
    ownership_edges = [
        ("alice_suspect", "shell_corp", "controls"),
        ("bob_associate", "front_company", "controls"),
        ("shell_corp", "front_company", "owns"),
    ]
    suspicion_edges = [
        ("tx_001", "tx_002", "similar_amount"),
        ("tx_002", "tx_003", "similar_amount"),
        ("alice_suspect", "diana_victim", "defrauds"),
    ]

    all_edges = transfer_edges + purchase_edges + ownership_edges + suspicion_edges
    for src, tgt, label in all_edges:
        mem.relate(src, tgt, label=label)

    graph = mem.graph
    print(f"  Nodes: {graph.node_count}")
    print(f"  Edges: {graph.edge_count}")
    flagged = [n for n, d in persons.items() if d.get("flagged")]
    suspicious = [n for n, d in entities.items() if d.get("suspicious")]
    structuring = [n for n, d in txns.items() if d.get("just_under_ctr")]
    print(f"  Flagged persons: {flagged}")
    print(f"  Suspicious entities: {suspicious}")
    print(f"  Structuring transactions (just under CTR): {structuring}")
    print()

    print("=" * 70)
    print("SECTION 2: Lazy Multiway Expansion of Transaction Paths")
    print("=" * 70)

    rule = TransitiveRule(edge_label="transfers")
    seed_labels = {
        "alice_suspect", "bob_associate", "charlie_runner",
        "eve_mule", "shell_corp", "front_company", "offshore_bank",
        "crypto_exchange",
    }
    seed_ids = set()
    for lbl in seed_labels:
        node = graph.get_node_by_label(lbl)
        if node:
            seed_ids.add(node.id)

    engine = MultiwayEngine(graph)
    print("  Expanding multiway state space lazily (generator-based)...")
    print()

    total_states = 0
    max_depth_seen = 0
    for state_id, depth, n_new in engine.expand_lazy(
        seed_ids, [rule], max_depth=3, max_total_states=50,
    ):
        total_states += 1
        max_depth_seen = max(max_depth_seen, depth)
        state = engine.multiway.get_state(state_id)
        rule_name = state.rule_applied or "root"
        active_count = len(state.active_node_ids) if state else 0
        print(f"    State #{total_states:3d} | depth={depth} | "
              f"rule={rule_name:20s} | new={n_new} | active={active_count}")

    print()
    print(f"  Total states explored: {total_states}")
    print(f"  Max depth reached: {max_depth_seen}")
    print(f"  Leaf states (terminal paths): {len(engine.multiway.get_leaves())}")

    convergent = engine.find_convergent_states()
    if convergent:
        print(f"\n  Convergent paths detected: {len(convergent)}")
        for sid_a, sid_b, score in convergent[:3]:
            sa = engine.multiway.get_state(sid_a)
            sb = engine.multiway.get_state(sid_b)
            if sa and sb:
                labels_a = {graph.get_node(nid).label for nid in sa.active_node_ids
                            if graph.get_node(nid)}
                labels_b = {graph.get_node(nid).label for nid in sb.active_node_ids
                            if graph.get_node(nid)}
                print(f"    Convergence score={score:.2f}: {labels_a} <-> {labels_b}")
    print()

    print("=" * 70)
    print("SECTION 3: Traversal-Based Prefetching for Investigation")
    print("=" * 70)

    mem.enable_prefetch(True)
    print(f"  Prefetch enabled: {mem.cache.prefetch_enabled}")

    investigation_path = [
        "alice_suspect", "bob_associate", "charlie_runner",
        "eve_mule", "crypto_exchange", "offshore_bank",
        "alice_suspect", "shell_corp", "front_company",
        "offshore_bank", "alice_suspect",
    ]
    for concept in investigation_path:
        mem.record_access(concept)

    predicted_labels = mem.predict_next_access("alice_suspect", top_k=3)
    print(f"\n  After investigating circular path, predicted next from 'alice_suspect':")
    print(f"    {predicted_labels}")

    preloaded = mem.prefetch_neighbors("alice_suspect")
    print(f"\n  Prefetched {preloaded} neighbor entries for 'alice_suspect'")
    print(f"  Cache size after prefetch: {mem.cache.size}")

    for concept in ["bob_associate", "shell_corp", "tx_001"]:
        plabels = mem.predict_next_access(concept, top_k=3)
        print(f"\n    Predicted next from '{concept}': {plabels}")
    print()

    print("=" * 70)
    print("SECTION 4: Partial Proof Generation for SAR Filing")
    print("=" * 70)

    tr = TransfiniteReasoner(graph)

    concepts_to_assess = [
        ("alice_suspect", {"self_reference": 0.8, "universal_quantification": 0.3}),
        ("shell_corp", {"self_reference": 0.9, "undecidable": 0.7}),
        ("offshore_bank", {"universal_quantification": 0.7, "diagonalization": 0.4}),
        ("tx_001", {}),
        ("diana_victim", {}),
    ]

    print("  Decidability Assessment of Suspicious Entities:")
    print()
    for concept, ctx in concepts_to_assess:
        indicator = tr.assess_decidability(concept, ctx)
        node = graph.get_node_by_label(concept)
        degree = len(graph.edges_for(node.id)) if node else 0
        status = ("decidable" if indicator.is_decidable
                  else "boundary" if indicator.is_boundary
                  else "undecidable")
        print(f"    {concept}:")
        print(f"      Boundary score: {indicator.boundary_score:.3f}  "
              f"status={status}  degree={degree}")

    print()
    print("  Reasoning at Level for Key Suspects:")
    print()

    for concept, ctx in [
        ("shell_corp", {"self_reference": 0.95, "universal_quantification": 0.9,
                        "undecidable": 0.9, "diagonalization": 0.9}),
        ("alice_suspect", {"self_reference": 0.7, "universal_quantification": 0.5}),
        ("tx_001", {}),
    ]:
        result = tr.reason_at_level(concept, ctx)
        print(f"    '{concept}' -> status={result.decidability_status}, "
              f"level={result.reasoning_level}, "
              f"boundary={result.boundary_score:.3f}")
        if result.boundary_warnings:
            for w in result.boundary_warnings:
                print(f"      WARNING: {w}")
        boundary_results = [
            r for r in result.partial_results
            if isinstance(r, dict) and r.get("status") == "boundary_proximity"
        ]
        if boundary_results:
            br = boundary_results[0]
            if br.get("structural_conclusions"):
                print(f"      Structural conclusions: {br['structural_conclusions']}")
            if br.get("assumption_dependent"):
                print(f"      Assumption-dependent: {br['assumption_dependent']}")
        print()

    print("  Partial Proof for Suspicious Activity Report:")
    print()

    alice_node = graph.get_node_by_label("alice_suspect")
    if alice_node:
        alice_neighbors = [graph.get_node(nid).label for nid in graph.neighbors(alice_node.id)
                           if graph.get_node(nid)]
        tx_nodes = [l for l in alice_neighbors if l.startswith("tx_")]
        entity_nodes = [l for l in alice_neighbors if l in entities]

        total_branches = len(tx_nodes) + len(entity_nodes) + len(transfer_edges)
        explored = min(total_branches, len(tx_nodes) + 4)
        coverage = explored / total_branches if total_branches > 0 else 0.0

        sar_proof = PartialProof(
            concept="Suspicious Activity Report: alice_suspect",
            expanded_nodes=[alice_node.id] + [
                graph.get_node_by_label(t).id
                for t in tx_nodes if graph.get_node_by_label(t)
            ],
            total_branches_estimated=total_branches,
            branches_explored=explored,
            coverage=coverage,
            bounds={
                "lower_bound": "Structured deposits (3x ~$49.9k) confirmed",
                "upper_bound": "Full money laundering circuit unconfirmed - offshore records pending",
                "confidence_interval": (0.72, 0.94),
            },
        )

        print(f"    Concept: {sar_proof.concept}")
        print(f"    Coverage: {sar_proof.coverage_pct:.1f}% "
              f"({sar_proof.branches_explored}/{sar_proof.total_branches_estimated} branches)")
        print(f"    Lower bound: {sar_proof.bounds['lower_bound']}")
        print(f"    Upper bound: {sar_proof.bounds['upper_bound']}")
        print(f"    Confidence interval: {sar_proof.bounds['confidence_interval']}")

    offshore_node = graph.get_node_by_label("offshore_bank")
    if alice_node and offshore_node:
        circuit_proof = PartialProof(
            concept="Circular Flow: offshore_bank -> alice_suspect -> ... -> offshore_bank",
            expanded_nodes=[offshore_node.id, alice_node.id],
            total_branches_estimated=8,
            branches_explored=5,
            coverage=5 / 8,
            bounds={
                "lower_bound": "Circular transfer path detected structurally",
                "upper_bound": "Intent and beneficial ownership require external evidence",
                "confidence_interval": (0.55, 0.85),
            },
        )

        print()
        print(f"    Concept: {circuit_proof.concept}")
        print(f"    Coverage: {circuit_proof.coverage_pct:.1f}% "
              f"({circuit_proof.branches_explored}/{circuit_proof.total_branches_estimated} branches)")
        print(f"    Lower bound: {circuit_proof.bounds['lower_bound']}")
        print(f"    Upper bound: {circuit_proof.bounds['upper_bound']}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Graph: {graph.node_count} nodes, {graph.edge_count} edges")
    print(f"  Multiway states explored: {total_states}")
    print(f"  Convergent paths found: {len(convergent)}")
    print(f"  Cache size: {mem.cache.size} entries")
    if alice_node:
        print(f"  SAR partial proof coverage: {sar_proof.coverage_pct:.1f}%")
    print()

    print("  The lazy expansion revealed multiple money laundering paths through")
    print("  the network without exhaustively materializing all states upfront.")
    print("  The traversal prefetcher learned the investigation pattern and can")
    print("  predict likely next targets. Partial proofs quantify the evidence")
    print("  gap between what is structurally confirmed and what remains uncertain.")


if __name__ == "__main__":
    main()
