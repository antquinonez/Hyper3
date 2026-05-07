"""
Provenance, Explanation, and Retraction (Plain Python)
=======================================================

Reimplements examples/showcase/provenance_and_retraction/provenance_and_retraction.py using
only networkx and standard libraries. No Hyper3 imports.

Run with:
    .venv/bin/python examples/comparison/05_provenance_and_retraction.py
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import uuid

import networkx as nx


@dataclass
class ProvenanceRecord:
    edge_key: tuple[str, str, str]
    rule_name: str
    input_edges: list[tuple[str, str, str]]
    depth: int


@dataclass
class Explanation:
    edge_key: tuple[str, str, str]
    rule_name: str
    depth: int
    premises: list[Explanation] = field(default_factory=list)

    def render(self, indent: int = 0) -> str:
        prefix = " " * indent
        src, tgt, lbl = self.edge_key
        lines = [f"{prefix}{src} --[{lbl}]--> {tgt} (via {self.rule_name}, depth={self.depth})"]
        for p in self.premises:
            lines.append(p.render(indent + 2))
        return "\n".join(lines)


class ProvenanceTracker:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], ProvenanceRecord] = {}
        self.dependency_graph: dict[tuple[str, str, str], set[tuple[str, str, str]]] = defaultdict(set)

    @property
    def record_count(self) -> int:
        return len(self.records)

    def record(
        self, edge_key: tuple[str, str, str], rule_name: str,
        input_edges: list[tuple[str, str, str]], depth: int,
    ) -> None:
        rec = ProvenanceRecord(edge_key=edge_key, rule_name=rule_name, input_edges=input_edges, depth=depth)
        self.records[edge_key] = rec
        for inp in input_edges:
            self.dependency_graph[inp].add(edge_key)

    def explain(self, edge_key: tuple[str, str, str]) -> Explanation | None:
        rec = self.records.get(edge_key)
        if not rec:
            return None
        premises = []
        for inp in rec.input_edges:
            sub = self.explain(inp)
            if sub:
                premises.append(sub)
        return Explanation(
            edge_key=edge_key, rule_name=rec.rule_name,
            depth=rec.depth, premises=premises,
        )

    def retract(self, edge_key: tuple[str, str, str]) -> list[tuple[str, str, str]]:
        removed = []
        stack = [edge_key]
        while stack:
            current = stack.pop()
            if current in self.records:
                del self.records[current]
                removed.append(current)
            dependents = self.dependency_graph.pop(current, set())
            for dep in dependents:
                if dep in self.records:
                    stack.append(dep)
        return removed


def transitive_closure(
    G: nx.DiGraph, edge_label: str, new_label: str,
    provenance: ProvenanceTracker, max_depth: int = 3,
) -> int:
    edges_produced = 0

    def _run_pass(depth: int) -> int:
        current_edges = [
            (u, v) for u, v, d in G.edges(data=True)
            if d.get("label") == edge_label
        ]
        current_set = set(current_edges)
        new_edges = []
        for a, b in current_edges:
            for c, d in current_edges:
                if b == c and a != d:
                    key = (a, d, new_label)
                    if (a, d) not in current_set and not G.has_edge(a, d):
                        new_edges.append((a, d, new_label, [(a, b, edge_label), (c, d, edge_label)], depth))
        count = 0
        for src, tgt, lbl, inputs, d in new_edges:
            if not G.has_edge(src, tgt):
                G.add_edge(src, tgt, label=lbl, inferred=True)
                provenance.record((src, tgt, lbl), "TransitiveRule", inputs, d)
                count += 1
        return count

    for d in range(1, max_depth + 1):
        produced = _run_pass(d)
        edges_produced += produced
        if produced == 0:
            break
    return edges_produced


def inverse_edges(
    G: nx.DiGraph, edge_label: str, inverse_label: str,
    provenance: ProvenanceTracker,
) -> int:
    edges_produced = 0
    edges = [
        (u, v) for u, v, d in G.edges(data=True)
        if d.get("label") == edge_label
    ]
    for u, v in edges:
        if not G.has_edge(v, u):
            G.add_edge(v, u, label=inverse_label, inferred=True)
            provenance.record(
                (v, u, inverse_label), "InverseRule",
                [(u, v, edge_label)], 1,
            )
            edges_produced += 1
    return edges_produced


def explain_relationship(
    G: nx.DiGraph, provenance: ProvenanceTracker, src: str, tgt: str,
) -> Explanation | None:
    for u, v, d in G.edges(data=True):
        if u == src and v == tgt and d.get("inferred"):
            expl = provenance.explain((u, v, d["label"]))
            if expl:
                return expl
    return None


def main():
    G = nx.DiGraph()
    node_data: dict[str, dict] = {}
    provenance = ProvenanceTracker()

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
        G.add_node(name)
        node_data[name] = data

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
        G.add_edge(src, tgt, label=label)

    print(f"  {G.number_of_nodes()} entities, {G.number_of_edges()} relationships")
    print()

    print("=" * 70)
    print("SECTION 2: Reasoning with Provenance")
    print("=" * 70)

    t_count = transitive_closure(G, "associated_with", "indirectly_associated", provenance, max_depth=3)
    t_count += transitive_closure(G, "investigated", "indirectly_investigated", provenance, max_depth=3)
    inv_count = inverse_edges(G, "investigated", "was_investigated_by", provenance)

    edges_produced = t_count + inv_count
    print(f"  Edges inferred: {edges_produced}")
    print(f"  Provenance records: {provenance.record_count}")
    print()

    print("=" * 70)
    print("SECTION 3: Explaining Inferences")
    print("=" * 70)

    inferred_edges = []
    for u, v, d in G.edges(data=True):
        if d.get("inferred"):
            inferred_edges.append((u, v, d["label"]))

    print(f"  {len(inferred_edges)} inferred edges. Explaining each:")
    for u, v, lbl in inferred_edges[:6]:
        explanation = provenance.explain((u, v, lbl))
        if explanation:
            print(f"\n  {u} --[{lbl}]--> {v}")
            print(f"    Rule: {explanation.rule_name}")
            print(f"    Depth: {explanation.depth}")
            print(f"    Explanation:")
            print(f"    {explanation.render(indent=2)}")
    print()

    print("=" * 70)
    print("SECTION 4: High-Level Explain API")
    print("=" * 70)

    explanation = explain_relationship(G, provenance, "drug_olaparib", "breast_cancer")
    if explanation:
        print(f"  Why is drug_olaparib connected to breast_cancer?")
        print(f"  {explanation.render(indent=2)}")
    else:
        print("  No inferred relationship found")

    explanation2 = explain_relationship(G, provenance, "dna_damage", "ovarian_cancer")
    if explanation2:
        print(f"\n  Why is dna_damage connected to ovarian_cancer?")
        print(f"  {explanation2.render(indent=2)}")
    print()

    print("=" * 70)
    print("SECTION 5: Cascading Retraction")
    print("=" * 70)

    print(f"  Graph before retraction: {G.number_of_edges()} edges")
    print(f"  Provenance records: {provenance.record_count}")

    retracted_ids = []
    for u, v, lbl in inferred_edges[:1]:
        key = (u, v, lbl)
        removed = provenance.retract(key)
        retracted_ids.extend(removed)
        print(f"\n  Retracted: {u} --[{lbl}]--> {v}")
        print(f"  Cascading removals: {len(removed)}")
        for rk in removed:
            ru, rv, rl = rk
            print(f"    Removed edge {ru} --[{rl}]--> {rv}")
            if G.has_edge(ru, rv):
                edge_data = G.get_edge_data(ru, rv)
                if edge_data and edge_data.get("label") == rl:
                    G.remove_edge(ru, rv)

    print(f"\n  Graph after retraction: {G.number_of_edges()} edges")
    print(f"  Provenance records: {provenance.record_count}")
    print()

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
