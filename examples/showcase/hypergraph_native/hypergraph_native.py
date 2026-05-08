"""Hypergraph-Native Algorithms: N-ary Edges and Structural Analysis.

Demonstrates six hypergraph-native capabilities that go beyond pairwise graphs:
  1. N-ary hyperedges — link_hyper() connects multiple sources to multiple targets
  2. Multi-resolution structure — s_persistence() reveals nested component hierarchies
  3. Spectral embedding — eigenvectors of the hypergraph Laplacian for node similarity
  4. Hyperedge similarity — Jaccard/Sorensen-Dice overlap between hyperedge node sets
  5. Gated diffusion — AND/OR/majority modes for n-ary edge activation flow
  6. Hyperedge querying — filter by cardinality and node membership

Domain: protein interaction network with multi-protein complexes.

Run:
    .venv/bin/python examples/showcase/hypergraph_native/14_hypergraph_native.py
"""

from __future__ import annotations

import math

from hyper3 import HypergraphMemory


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: N-ary Hyperedge Construction")
    print("-" * 70)

    proteins = [
        "TP53", "MDM2", "BRCA1", "BRCA2", "RAD51", "ATM", "ATR",
        "CHEK1", "CHEK2", "CDK2", "CDK4", "RB1", "E2F1", "MYC",
        "AKT1", "PIK3CA", "PTEN", "MTOR", "EGFR", "KRAS",
        "BRAF", "MAPK1", "RAF1", "APC", "CTNNB1", "VEGFA",
    ]
    for p in proteins:
        mem.add(p, data={"kind": "protein"})

    pathways = ["p53_signaling", "cell_cycle", "dna_repair", "pi3k_akt", "mapk_signaling"]
    for pw in pathways:
        mem.add(pw, data={"kind": "pathway"})

    diseases = ["breast_cancer", "lung_cancer", "colorectal_cancer", "glioblastoma"]
    for d in diseases:
        mem.add(d, data={"kind": "disease"})

    mem.link_hyper(
        sources={"TP53", "MDM2", "ATM"},
        targets={"p53_signaling"},
        label="complex_regulates",
    )
    mem.link_hyper(
        sources={"BRCA1", "BRCA2", "RAD51"},
        targets={"dna_repair"},
        label="complex_regulates",
    )
    mem.link_hyper(
        sources={"CDK2", "CDK4", "RB1", "E2F1"},
        targets={"cell_cycle"},
        label="complex_regulates",
    )
    mem.link_hyper(
        sources={"AKT1", "PIK3CA", "PTEN", "MTOR"},
        targets={"pi3k_akt"},
        label="complex_regulates",
    )
    mem.link_hyper(
        sources={"EGFR", "KRAS", "BRAF", "MAPK1", "RAF1"},
        targets={"mapk_signaling"},
        label="complex_regulates",
    )
    mem.link_hyper(
        sources={"TP53", "BRCA1", "BRCA2"},
        targets={"breast_cancer"},
        label="complex_associated_with",
    )
    mem.link_hyper(
        sources={"EGFR", "KRAS", "APC"},
        targets={"lung_cancer"},
        label="complex_associated_with",
    )
    mem.link_hyper(
        sources={"APC", "CTNNB1", "KRAS", "BRAF"},
        targets={"colorectal_cancer"},
        label="complex_associated_with",
    )
    mem.link_hyper(
        sources={"EGFR", "PTEN", "TP53"},
        targets={"glioblastoma"},
        label="complex_associated_with",
    )

    for p in ["TP53", "BRCA1", "KRAS", "EGFR", "PIK3CA"]:
        mem.link(p, "dna_repair", label="participates_in")

    pairwise_edges = mem.size[1]
    print(f"  Proteins: {len(proteins)}, Pathways: {len(pathways)}, Diseases: {len(diseases)}")
    print(f"  Total edges (including n-ary): {pairwise_edges}")

    n_ary = mem.query_hyperedges(min_source_cardinality=2)
    print(f"  N-ary hyperedges: {len(n_ary)}")

    print()
    print("=" * 70)
    print("SECTION 2: Hyperedge Querying")
    print("-" * 70)

    tp53_hyperedges = mem.query_hyperedges(containing="TP53")
    print(f"  Hyperedges containing TP53: {len(tp53_hyperedges)}")
    for he in tp53_hyperedges:
        src_labels = sorted(
            mem.engine.graph.get_node(sid).label
            for sid in he.source_ids
            if mem.engine.graph.get_node(sid)
        )
        tgt_labels = sorted(
            mem.engine.graph.get_node(tid).label
            for tid in he.target_ids
            if mem.engine.graph.get_node(tid)
        )
        print(f"    [{', '.join(src_labels)}] --[{he.label}]--> [{', '.join(tgt_labels)}]")

    multi_src = mem.query_hyperedges(min_source_cardinality=3)
    print(f"  Hyperedges with 3+ sources: {len(multi_src)}")

    print()
    print("=" * 70)
    print("SECTION 3: Multi-Resolution Structure (s-persistence)")
    print("-" * 70)

    sp_result = mem.s_persistence(max_s=3)
    for level in sp_result.levels:
        print(f"  s={level.s}: {level.num_components} components", end="")
        if level.largest_component_size > 1:
            print(f"  (largest: {level.largest_component_size} nodes)")
        else:
            print()

    print()
    print("=" * 70)
    print("SECTION 4: Spectral Embedding from Hypergraph Laplacian")
    print("-" * 70)

    emb = mem.spectral_embedding(dimensions=4)
    if emb:
        print(f"  Computed {len(emb)} embeddings in 4D")
        for label in ["TP53", "BRCA1", "KRAS", "EGFR"]:
            if label in emb:
                vec = emb[label]
                mag = math.sqrt(sum(v * v for v in vec))
                print(f"    {label}: magnitude={mag:.4f}  dim0={vec[0]:.4f}")

        tp53_vec = emb.get("TP53")
        brca1_vec = emb.get("BRCA1")
        kras_vec = emb.get("KRAS")
        if tp53_vec and brca1_vec and kras_vec:
            cos_tp53_brca1 = sum(a * b for a, b in zip(tp53_vec, brca1_vec)) / (
                math.sqrt(sum(a * a for a in tp53_vec))
                * math.sqrt(sum(b * b for b in brca1_vec))
                + 1e-12
            )
            cos_tp53_kras = sum(a * b for a, b in zip(tp53_vec, kras_vec)) / (
                math.sqrt(sum(a * a for a in tp53_vec))
                * math.sqrt(sum(b * b for b in kras_vec))
                + 1e-12
            )
            print(f"  Cosine similarity(TP53, BRCA1) = {cos_tp53_brca1:.4f}")
            print(f"  Cosine similarity(TP53, KRAS)  = {cos_tp53_kras:.4f}")
            if cos_tp53_brca1 > cos_tp53_kras:
                print("  -> TP53 is spectrally closer to BRCA1 than to KRAS (shared complex)")
    else:
        print("  (insufficient graph structure for spectral embedding)")

    print()
    print("=" * 70)
    print("SECTION 5: Hyperedge Similarity")
    print("-" * 70)

    for protein in ["TP53", "EGFR", "KRAS"]:
        sims = mem.hyperedge_similarity(protein, metric="jaccard")
        if sims:
            top_label, top_score = sims[0]
            print(f"  {protein}: top similar edge (Jaccard={top_score:.4f})")
        else:
            print(f"  {protein}: no similar hyperedges found")

    print()
    print("=" * 70)
    print("SECTION 6: Gated Diffusion (AND/OR/majority)")
    print("-" * 70)

    for mode in ["linear", "or", "majority", "and"]:
        results = mem.spread_hyperedge("TP53", mode=mode)
        active = [
            (r.label, r.activation)
            for r in results
            if r.label.startswith(("p53", "dna", "breast", "gliob", "cell"))
        ]
        active.sort(key=lambda x: -x[1])
        print(f"  mode={mode:8s}: {len(active)} pathway/disease nodes activated", end="")
        if active:
            print(f"  top: {active[0][0]}={active[0][1]:.3f}")
        else:
            print()

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    desc = mem.analyze.describe()
    print(f"  Nodes: {desc.node_count}  ({desc.node_types})")
    print(f"  Edges: {desc.edge_count}")
    print(f"  N-ary edges: {len(n_ary)}")
    print(f"  Components: {desc.components}")
    print(f"  Density: {desc.density:.4f}")


if __name__ == "__main__":
    main()
