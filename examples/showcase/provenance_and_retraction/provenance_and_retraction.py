"""
Provenance, Explanation, and Retraction
=========================================

This example demonstrates Hyper3's provenance tracking system.
Every inferred edge records its derivation: which rule produced it,
which input edges it used, and at what depth. This enables:
  - explain(): Show why an inference was made
  - retract_inference(): Remove an inference and all dependent inferences
  - Cascading retraction: Removing a premise removes all conclusions

Use case: A research knowledge graph where claims are backed by
evidence chains. When a source paper is retracted, all derived
conclusions are automatically removed.

Run with:
    .venv/bin/python examples/showcase/provenance_and_retraction/05_provenance_and_retraction.py
"""

from __future__ import annotations

from hyper3 import (
    HypergraphMemory,
    TransitiveRule,
    InverseRule,
    Modality,
)


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Building a Research Knowledge Graph
    # =====================================================================
    # We model scientific findings: studies, proteins, drugs, and
    # their relationships.

    print("=" * 70)
    print("SECTION 1: Building Research Knowledge Graph")
    print("=" * 70)

    entities = {
        "study_alpha": {"type": "clinical_trial", "year": 2023, "n_patients": 500},
        "study_beta": {"type": "observational", "year": 2022, "n_patients": 1200},
        "study_gamma": {"type": "meta_analysis", "year": 2024, "n_studies": 15},
        "protein_BRCA1": {"type": "protein", "function": "dna_repair"},
        "protein_TP53": {"type": "protein", "function": "tumor_suppressor"},
        "protein_RAD51": {"type": "protein", "function": "recombination"},
        "drug_olaparib": {"type": "drug", "class": "PARP_inhibitor"},
        "drug_cisplatin": {"type": "drug", "class": "platinum_agent"},
        "breast_cancer": {"type": "disease", "icd10": "C50"},
        "ovarian_cancer": {"type": "disease", "icd10": "C56"},
        "dna_damage": {"type": "mechanism"},
        "apoptosis": {"type": "mechanism"},
    }
    for name, data in entities.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    # Evidence-backed relationships
    relations = [
        ("study_alpha", "drug_olaparib", "investigated"),
        ("study_alpha", "breast_cancer", "investigated"),
        ("study_beta", "protein_BRCA1", "found_association"),
        ("study_beta", "breast_cancer", "found_association"),
        ("study_gamma", "drug_olaparib", "confirms_efficacy"),
        ("protein_BRCA1", "dna_damage", "repairs"),
        ("protein_BRCA1", "protein_RAD51", "interacts_with"),
        ("protein_TP53", "apoptosis", "promotes"),
        ("dna_damage", "apoptosis", "triggers"),
        ("drug_olaparib", "dna_damage", "increases"),
        ("drug_cisplatin", "dna_damage", "causes"),
        ("dna_damage", "breast_cancer", "associated_with"),
        ("dna_damage", "ovarian_cancer", "associated_with"),
    ]
    for src, tgt, label in relations:
        mem.link(src, tgt, label=label)

    print(f"  {mem.size[0]} entities, {mem.size[1]} relationships")
    print()

    # =====================================================================
    # SECTION 2: Reasoning with Provenance Tracking
    # =====================================================================
    # When reason() is called, it tracks which rule produced each
    # inferred edge and what inputs it used.

    print("=" * 70)
    print("SECTION 2: Reasoning with Provenance")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="associated_with", new_label="indirectly_associated"),
        TransitiveRule(edge_label="investigated", new_label="indirectly_investigated"),
        InverseRule(edge_label="investigated", inverse_label="was_investigated_by"),
    )

    result = mem.reason(
        {"study_alpha", "drug_olaparib", "dna_damage"},
        max_depth=3,
        max_total_states=40,
    )

    exp = result.expansion
    print(f"  States explored: {exp.states_created}")
    print(f"  Rules applied: {exp.rules_applied}")
    print(f"  Edges inferred: {exp.edges_produced}")
    print(f"  Provenance records: {mem.provenance.record_count}")
    print()

    # =====================================================================
    # SECTION 3: Explaining Inferences
    # =====================================================================
    # explain() traces back through the provenance chain to show
    # WHY an edge exists.

    print("=" * 70)
    print("SECTION 3: Explaining Inferences")
    print("=" * 70)

    # Find inferred edges and explain them
    inferred_edges = []
    for le in mem.engine.graph.labeled_edges:
        if not le["source_labels"] or not le["target_labels"]:
            continue
        raw = mem.engine.graph.get_edge(le["id"])
        if raw and raw.metadata.custom.get("inferred"):
            inferred_edges.append((raw, le["source_labels"][0], le["target_labels"][0]))

    print(f"  {len(inferred_edges)} inferred edges. Explaining each:")
    for edge, src_label, tgt_label in inferred_edges[:6]:
        explanation = mem.provenance.explain(edge.id, graph=mem.engine.graph)
        if explanation:
            print(f"\n  {src_label} --[{edge.label}]--> {tgt_label}")
            print(f"    Rule: {explanation.rule_name}")
            print(f"    Depth: {explanation.depth}")
            print(f"    Explanation:")
            print(f"    {explanation.render(indent=2)}")
    print()

    # =====================================================================
    # SECTION 4: High-Level Explain API
    # =====================================================================
    # The HypergraphMemory.explain() method provides a convenient
    # way to explain the relationship between two concepts.

    print("=" * 70)
    print("SECTION 4: High-Level Explain API")
    print("=" * 70)

    # Explain relationship between two concepts
    explanation = mem.explain("drug_olaparib", "breast_cancer")
    if explanation:
        print(f"  Why is drug_olaparib connected to breast_cancer?")
        print(f"  {explanation.render(indent=2)}")
    else:
        print("  No inferred relationship found")

    explanation2 = mem.explain("dna_damage", "ovarian_cancer")
    if explanation2:
        print(f"\n  Why is dna_damage connected to ovarian_cancer?")
        print(f"  {explanation2.render(indent=2)}")
    print()

    # =====================================================================
    # SECTION 5: Cascading Retraction
    # =====================================================================
    # When we retract an inference, all inferences that depended on it
    # are also removed. This maintains knowledge graph consistency.

    print("=" * 70)
    print("SECTION 5: Cascading Retraction")
    print("=" * 70)

    print(f"  Graph before retraction: {mem.size[1]} edges")
    print(f"  Provenance records: {mem.provenance.record_count}")

    # Retract a specific inference
    # (Note: the exact retractable edges depend on what was inferred)
    retracted = []
    for edge, src_label, tgt_label in inferred_edges[:1]:
        retracted_ids = mem.retract_inference(src_label, tgt_label, edge_label=edge.label)
        retracted.extend(retracted_ids)
        print(f"\n  Retracted: {src_label} --[{edge.label}]--> {tgt_label}")
        print(f"  Cascading removals: {len(retracted_ids)}")
        for rid in retracted_ids:
            e = mem.engine.graph.get_edge(rid)
            if e:
                pass  # edge already removed
            print(f"    Removed edge {rid[:12]}...")

    print(f"\n  Graph after retraction: {mem.size[1]} edges")
    print(f"  Provenance records: {mem.provenance.record_count}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Built a research knowledge graph with clinical evidence")
    print("  2. Ran reasoning that produced inferred edges")
    print("  3. Traced provenance chains to explain WHY inferences hold")
    print("  4. Used high-level explain() API for convenience")
    print("  5. Demonstrated cascading retraction for knowledge maintenance")
    print()


if __name__ == "__main__":
    main()
