"""
Validation Engine and Frame Transformations
=============================================
Demonstrates comparing simple vs enhanced reasoning strategies using
ValidationEngine, and shows how frame transformations (classical, quantum,
hypergraph, probabilistic) affect reasoning parameters and information loss.

Run: .venv/bin/python examples/showcase/validation_engine/validation_engine.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD BIOMEDICAL KNOWLEDGE GRAPH")
    print("=" * 70)

    from hyper3 import HypergraphMemory, TransitiveRule

    mem = HypergraphMemory(evolve_interval=0, rules=[
        TransitiveRule(edge_label="regulates", new_label="indirect_regulation"),
    ])

    genes = ["gene_brca1", "gene_tp53", "gene_egfr", "gene_kras"]
    proteins = ["protein_p53", "protein_egfr", "protein_kras"]
    diseases = ["breast_cancer", "lung_cancer", "pancreatic_cancer"]
    drugs = ["drug_cisplatin", "drug_erlotinib", "drug_olaparib"]
    pathways = ["pathway_apoptosis", "pathway_cell_cycle"]
    evidence = ["evidence_clinical", "evidence_preclinical"]

    for g in genes:
        mem.add(g, data={"type": "gene"})
    for p in proteins:
        mem.add(p, data={"type": "protein"})
    for d in diseases:
        mem.add(d, data={"type": "disease"})
    for dr in drugs:
        mem.add(dr, data={"type": "drug"})
    for pw in pathways:
        mem.add(pw, data={"type": "pathway"})
    for ev in evidence:
        mem.add(ev, data={"type": "evidence"})

    mem.link("gene_brca1", "gene_tp53", label="regulates", weight=3.0)
    mem.link("gene_tp53", "protein_p53", label="regulates", weight=3.0)
    mem.link("protein_p53", "pathway_apoptosis", label="activates", weight=2.5)
    mem.link("pathway_apoptosis", "breast_cancer", label="associated_with", weight=3.0)
    mem.link("gene_egfr", "protein_egfr", label="regulates", weight=3.0)
    mem.link("protein_egfr", "pathway_cell_cycle", label="activates", weight=2.0)
    mem.link("pathway_cell_cycle", "lung_cancer", label="associated_with", weight=3.0)
    mem.link("gene_kras", "protein_kras", label="regulates", weight=2.5)
    mem.link("protein_kras", "pancreatic_cancer", label="associated_with", weight=3.0)
    mem.link("drug_cisplatin", "protein_p53", label="inhibits", weight=2.0)
    mem.link("drug_erlotinib", "protein_egfr", label="inhibits", weight=2.5)
    mem.link("drug_olaparib", "gene_brca1", label="targets", weight=3.0)
    mem.link("evidence_clinical", "drug_cisplatin", label="evidence_for", weight=3.0)
    mem.link("evidence_preclinical", "drug_olaparib", label="evidence_for", weight=2.0)
    mem.link("breast_cancer", "lung_cancer", label="associated_with", weight=1.0)

    desc = mem.analyze.describe()
    print(f"nodes: {desc.node_count}, edges: {desc.edge_count}")
    print(f"edge labels: {sorted(desc.edge_labels)}")

    print("\n" + "=" * 70)
    print("SECTION 2: FRAME TRANSFORMATIONS")
    print("=" * 70)

    from hyper3 import FrameTransformer

    ft = FrameTransformer()
    frames = ["classical", "quantum", "hypergraph", "probabilistic"]

    print("\ninformation loss matrix:")
    header = f"{'from\\to':>15s}"
    for f in frames:
        header += f"  {f[:10]:>10s}"
    print(header)

    for src in frames:
        row = f"{src:>15s}"
        for tgt in frames:
            loss = ft.information_loss(src, tgt, parameters={"branching_factor": 4, "amplitudes": [0.5, 0.3, 0.2]})
            row += f"  {loss:>10.4f}"
        print(row)

    for src in frames[:2]:
        for tgt in frames[1:3]:
            if src != tgt:
                tc = ft.transform(src, tgt, parameters={"branching_factor": 4})
                print(f"\n{src} -> {tgt}:")
                print(f"  algorithm: {tc.algorithm}")
                print(f"  information_loss: {tc.information_loss:.4f}")
                print(f"  preserved: {tc.preserved_properties}")

    print("\n" + "=" * 70)
    print("SECTION 3: SIMPLE VS ENHANCED REASONING COMPARISON")
    print("=" * 70)

    from hyper3 import ValidationEngine

    ve = ValidationEngine(mem)

    simple_rules = [TransitiveRule(edge_label="regulates", new_label="indirect_regulation")]

    report = ve.run_comparison(
        seed_concepts={"gene_brca1", "gene_tp53"},
        rules=simple_rules,
    )

    print("\nsimple reasoning:")
    print(f"  nodes produced: {len(report.simple_results.nodes_produced)}")
    print(f"  edges produced: {len(report.simple_results.edges_produced)}")
    print(f"  avg confidence: {report.simple_results.avg_confidence:.4f}")
    print(f"  coverage: {report.simple_results.coverage:.4f}")
    print(f"  time: {report.simple_results.time_ms:.2f} ms")

    print("\nenhanced reasoning:")
    print(f"  nodes produced: {len(report.enhanced_results.nodes_produced)}")
    print(f"  edges produced: {len(report.enhanced_results.edges_produced)}")
    print(f"  avg confidence: {report.enhanced_results.avg_confidence:.4f}")
    print(f"  coverage: {report.enhanced_results.coverage:.4f}")
    print(f"  time: {report.enhanced_results.time_ms:.2f} ms")

    print("\n" + "=" * 70)
    print("SECTION 4: AGREEMENT METRICS ANALYSIS")
    print("=" * 70)

    a = report.agreement
    print(f"\nnode jaccard: {a.node_jaccard:.4f}")
    print(f"edge jaccard: {a.edge_jaccard:.4f}")
    print(f"consistency: {a.consistency:.4f}")
    print(f"precision: {a.precision:.4f}")
    print(f"recall: {a.recall:.4f}")
    print(f"f1: {a.f1:.4f}")
    print(f"\nrecommendation: {report.recommendation}")
    print(f"enhanced overhead: {report.enhanced_overhead_ms:.2f} ms")

    print(f"\nnovel findings: {len(report.novel_findings)}")
    for finding in report.novel_findings[:5]:
        print(f"  {finding['type']}: {finding.get('label', finding.get('id', '')[:8])}")

    print(f"\ncontradictions: {len(report.contradictions)}")
    for c in report.contradictions[:3]:
        print(f"  {c['type']}: {c}")

    print("\n" + "=" * 70)
    print("SECTION 5: MULTI-CASE VALIDATION SUITE")
    print("=" * 70)

    test_cases = [
        {"gene_brca1"},
        {"drug_cisplatin"},
        {"pathway_apoptosis"},
    ]

    reports = ve.run_validation_suite(test_cases)
    print(f"validation suite: {len(reports)} cases")
    for i, r in enumerate(reports):
        seeds = test_cases[i]
        print(f"\ncase {i + 1} ({seeds}):")
        print(f"  simple edges: {len(r.simple_results.edges_produced)}")
        print(f"  enhanced edges: {len(r.enhanced_results.edges_produced)}")
        print(f"  f1: {r.agreement.f1:.4f}")
        print(f"  recommendation: {r.recommendation}")

    reliable = ve.is_enhanced_reliable()
    print(f"\nenhanced reliable: {reliable}")

    print("\n" + "=" * 70)
    print("SECTION 6: CROSS-FRAME COMPARISON")
    print("=" * 70)

    identity_loss = ft.information_loss("classical", "classical")
    print(f"identity transform loss: {identity_loss:.4f}")

    c2q = ft.transform("classical", "quantum", parameters={"branching_factor": 4})
    c2p = ft.transform("classical", "probabilistic", parameters={"weights": [3.0, 2.0, 1.0]})
    c2h = ft.transform("classical", "hypergraph", parameters={"max_arity": 3})

    print(f"\nclassical -> quantum: algo={c2q.algorithm}, loss={c2q.information_loss:.4f}")
    print(f"classical -> probabilistic: algo={c2p.algorithm}, loss={c2p.information_loss:.4f}")
    print(f"classical -> hypergraph: algo={c2h.algorithm}, loss={c2h.information_loss:.4f}")

    print("\nparameters preserved:")
    print(f"  quantum: {c2q.preserved_properties}")
    print(f"  probabilistic: {c2p.preserved_properties}")
    print(f"  hypergraph: {c2h.preserved_properties}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
