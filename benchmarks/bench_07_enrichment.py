"""
Bench 7: Text Enrichment (Entity/Relation Extraction)
======================================================

Compares Hyper3's RegexExtractor against a minimal regex baseline
for entity and relation extraction from text.

Systems compared:
  1. Hyper3 RegexExtractor - 115+ patterns, coreference, noun phrases, lists
  2. Simple regex baseline  - basic "X is Y" / "X verb Y" patterns

Metrics: Entity extraction precision/recall/F1, relation extraction F1

Ground truth: manually annotated entities and relations from test passages.

Run:
    .venv/bin/python benchmarks/bench_07_enrichment.py
"""

from __future__ import annotations

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyper3 import RegexExtractor
from shared import Timer, print_header, print_comparison_table


TEST_PASSAGES = [
    {
        "text": (
            "Python is a programming language created by Guido van Rossum. "
            "Python supports object-oriented programming and functional programming. "
            "Django is a web framework written in Python. "
            "NumPy is a library for numerical computing in Python. "
            "TensorFlow is a machine learning framework developed by Google. "
            "PyTorch is another machine learning framework developed by Meta. "
            "Python was first released in 1991. "
            "Flask is a lightweight web framework for Python. "
            "Pandas is a data analysis library built on NumPy. "
            "Scikit-learn is a machine learning library that uses NumPy."
        ),
        "entities": {
            "Python", "Guido van Rossum", "Django", "NumPy", "TensorFlow",
            "Google", "PyTorch", "Meta", "Flask", "Pandas", "Scikit-learn",
        },
        "relations": {
            ("Python", "created by", "Guido van Rossum"),
            ("Python", "supports", "object-oriented programming"),
            ("Python", "supports", "functional programming"),
            ("Django", "is a", "web framework"),
            ("Django", "written in", "Python"),
            ("NumPy", "is a", "library"),
            ("TensorFlow", "is a", "machine learning framework"),
            ("TensorFlow", "developed by", "Google"),
            ("PyTorch", "is a", "machine learning framework"),
            ("PyTorch", "developed by", "Meta"),
            ("Flask", "is a", "web framework"),
            ("Pandas", "is a", "data analysis library"),
            ("Pandas", "built on", "NumPy"),
            ("Scikit-learn", "is a", "machine learning library"),
            ("Scikit-learn", "uses", "NumPy"),
        },
    },
    {
        "text": (
            "Paris is the capital of France. "
            "London is the capital of the United Kingdom. "
            "Berlin is the capital of Germany. "
            "The Eiffel Tower is located in Paris. "
            "The Louvre is a museum in Paris. "
            "France borders Germany and Belgium. "
            "Germany borders Austria and Switzerland. "
            "The Rhine flows through Germany and France. "
            "France is a member of the European Union. "
            "Germany is the largest economy in the European Union."
        ),
        "entities": {
            "Paris", "France", "London", "United Kingdom", "Berlin", "Germany",
            "Eiffel Tower", "Louvre", "Belgium", "Austria", "Switzerland",
            "Rhine", "European Union",
        },
        "relations": {
            ("Paris", "is the capital of", "France"),
            ("London", "is the capital of", "United Kingdom"),
            ("Berlin", "is the capital of", "Germany"),
            ("Eiffel Tower", "is located in", "Paris"),
            ("Louvre", "is a", "museum"),
            ("Louvre", "in", "Paris"),
            ("France", "borders", "Germany"),
            ("France", "borders", "Belgium"),
            ("Germany", "borders", "Austria"),
            ("Germany", "borders", "Switzerland"),
            ("France", "is a member of", "European Union"),
            ("Germany", "is the", "largest economy"),
        },
    },
]


class SimpleRegexBaseline:
    SIMPLE_ENTITY_RE = re.compile(
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    )
    SIMPLE_RELATION_RE = re.compile(
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        r'\s+(is\s+(?:a|an|the)\s+\w+)'
        r'\s+(?:of\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    )
    SIMPLE_VERB_RE = re.compile(
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        r'\s+(borders|developed\s+by|created\s+by|written\s+in|built\s+on|uses|supports|flows\s+through)'
        r'\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    )

    def extract(self, text: str) -> tuple[set[str], set[tuple[str, str, str]]]:
        entities = set(self.SIMPLE_ENTITY_RE.findall(text))
        relations: set[tuple[str, str, str]] = set()
        for m in self.SIMPLE_RELATION_RE.finditer(text):
            relations.add((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
        for m in self.SIMPLE_VERB_RE.finditer(text):
            relations.add((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
        return entities, relations


def entity_f1(predicted: set[str], ground_truth: set[str]) -> tuple[float, float, float]:
    if not ground_truth:
        return 0.0, 0.0, 0.0
    matched = predicted & ground_truth
    precision = len(matched) / len(predicted) if predicted else 0.0
    recall = len(matched) / len(ground_truth)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def relation_f1(
    predicted: set[tuple[str, str, str]],
    ground_truth: set[tuple[str, str, str]],
) -> tuple[float, float, float]:
    if not ground_truth:
        return 0.0, 0.0, 0.0
    matched = predicted & ground_truth
    precision = len(matched) / len(predicted) if predicted else 0.0
    recall = len(matched) / len(ground_truth)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def normalize_entity(e: str) -> str:
    return e.strip().lower()


def normalize_entities(entities: set[str]) -> set[str]:
    return {normalize_entity(e) for e in entities}


def normalize_relations(relations: set[tuple[str, str, str]]) -> set[tuple[str, str, str]]:
    return {(normalize_entity(s), rel.strip().lower(), normalize_entity(t)) for s, rel, t in relations}


def main() -> None:
    print_header("Bench 7: Text Enrichment")

    extractor = RegexExtractor()
    baseline = SimpleRegexBaseline()

    h3_results: dict[str, list[float]] = {"e_p": [], "e_r": [], "e_f1": [], "r_p": [], "r_r": [], "r_f1": []}
    bl_results: dict[str, list[float]] = {"e_p": [], "e_r": [], "e_f1": [], "r_p": [], "r_r": [], "r_f1": []}
    h3_time = 0.0
    bl_time = 0.0

    for i, passage in enumerate(TEST_PASSAGES):
        print_header(f"Passage {i+1}: {len(passage['text'])} chars")
        text = passage["text"]
        gt_entities = normalize_entities(passage["entities"])
        gt_relations = normalize_relations(passage["relations"])

        # Hyper3
        with Timer() as t:
            result = extractor.extract(text)
        h3_time += t.elapsed

        h3_entities = normalize_entities({e.label for e in result.entities})
        h3_relations = normalize_relations({
            (r.source_label, r.relation_label, r.target_label) for r in result.relations
        })

        ep, er, ef1 = entity_f1(h3_entities, gt_entities)
        rp, rr, rf1 = relation_f1(h3_relations, gt_relations)

        h3_results["e_p"].append(ep)
        h3_results["e_r"].append(er)
        h3_results["e_f1"].append(ef1)
        h3_results["r_p"].append(rp)
        h3_results["r_r"].append(rr)
        h3_results["r_f1"].append(rf1)

        print(f"  Hyper3 RegexExtractor ({t.elapsed*1000:.1f}ms):")
        print(f"    Entities found: {len(h3_entities)}  (ground truth: {len(gt_entities)})")
        print(f"    P={ep:.2f}  R={er:.2f}  F1={ef1:.2f}")
        print(f"    Relations found: {len(h3_relations)}  (ground truth: {len(gt_relations)})")
        print(f"    P={rp:.2f}  R={rr:.2f}  F1={rf1:.2f}")

        # Simple baseline
        with Timer() as t:
            bl_entities_raw, bl_relations_raw = baseline.extract(text)
        bl_time += t.elapsed

        bl_entities = normalize_entities(bl_entities_raw)
        bl_relations = normalize_relations(bl_relations_raw)

        bep, ber, bef1 = entity_f1(bl_entities, gt_entities)
        brp, brr, brf1 = relation_f1(bl_relations, gt_relations)

        bl_results["e_p"].append(bep)
        bl_results["e_r"].append(ber)
        bl_results["e_f1"].append(bef1)
        bl_results["r_p"].append(brp)
        bl_results["r_r"].append(brr)
        bl_results["r_f1"].append(brf1)

        print(f"  Simple Regex ({t.elapsed*1000:.1f}ms):")
        print(f"    Entities found: {len(bl_entities)}  (ground truth: {len(gt_entities)})")
        print(f"    P={bep:.2f}  R={ber:.2f}  F1={bef1:.2f}")
        print(f"    Relations found: {len(bl_relations)}  (ground truth: {len(gt_relations)})")
        print(f"    P={brp:.2f}  R={brr:.2f}  F1={brf1:.2f}")

        # Show unique H3 finds
        h3_only = h3_entities - bl_entities
        bl_only = bl_entities - h3_entities
        if h3_only:
            print(f"    Entities only H3 found: {h3_only}")
        if bl_only:
            print(f"    Entities only baseline found: {bl_only}")

    # --- Summary ---
    print_header("Summary (averaged)")
    headers = ["System", "Ent P", "Ent R", "Ent F1", "Rel P", "Rel R", "Rel F1", "Time"]
    rows = []

    def avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    rows.append([
        "H3 RegexExtractor",
        f"{avg(h3_results['e_p']):.2f}",
        f"{avg(h3_results['e_r']):.2f}",
        f"{avg(h3_results['e_f1']):.2f}",
        f"{avg(h3_results['r_p']):.2f}",
        f"{avg(h3_results['r_r']):.2f}",
        f"{avg(h3_results['r_f1']):.2f}",
        f"{h3_time*1000:.1f}ms",
    ])
    rows.append([
        "Simple regex",
        f"{avg(bl_results['e_p']):.2f}",
        f"{avg(bl_results['e_r']):.2f}",
        f"{avg(bl_results['e_f1']):.2f}",
        f"{avg(bl_results['r_p']):.2f}",
        f"{avg(bl_results['r_r']):.2f}",
        f"{avg(bl_results['r_f1']):.2f}",
        f"{bl_time*1000:.1f}ms",
    ])
    print_comparison_table(headers, rows)

    print()


if __name__ == "__main__":
    main()
