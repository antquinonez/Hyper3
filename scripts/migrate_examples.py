"""Phase 8 migration script: safe mechanical API replacements for example files.

Run: .venv/bin/python scripts/migrate_examples.py
"""
from __future__ import annotations

import re
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

SAFE_REPLACEMENTS: list[tuple[str, str, str]] = [
    ("mem.store(", "mem.add(", "store->add"),
    ("mem.relate(", "mem.link(", "relate->link"),
    ("mem.has_node(", "mem.has(", "has_node->has"),
    ("mem.graph.node_count", "mem.size[0]", "graph.node_count->size[0]"),
    ("mem.graph.edge_count", "mem.size[1]", "graph.edge_count->size[1]"),
]

CENTRALITY_REPLACEMENTS: list[tuple[str, str, str]] = [
    ("mem.degree_centrality(", "mem.analyze.centrality(\"degree\", top_k=None, ", "degree_centrality"),
    ("mem.betweenness_centrality(", "mem.analyze.centrality(\"betweenness\", ", "betweenness_centrality"),
    ("mem.pagerank(", "mem.analyze.centrality(\"pagerank\", ", "pagerank"),
    ("mem.katz_centrality(", "mem.analyze.centrality(\"katz\", ", "katz_centrality"),
]

RETRIEVAL_REPLACEMENTS: list[tuple[str, str, str]] = [
    ("mem.detect_communities(", "mem.analyze.communities(", "detect_communities->analyze.communities"),
    ("mem.detect_structural_anomalies(", "mem.analyze.contradictions(", "detect_structural_anomalies"),
    ("mem.find_similar(", "mem.search.similar(", "find_similar->search.similar"),
]

BULK_REPLACEMENTS = SAFE_REPLACEMENTS + RETRIEVAL_REPLACEMENTS

MIGRATED_TEMPORAL = [
    ("mem.temporal_engine.", "mem.temporal.", "temporal_engine->temporal (already done)"),
]

MIGRATED_BELIEF = [
    ("mem.belief_layer.", "mem.belief.", "belief_layer->belief (namespace collision, keep engine access)"),
]


def migrate_file(path: Path, dry_run: bool = False) -> list[str]:
    text = path.read_text()
    original = text
    changes: list[str] = []

    for old, new, label in BULK_REPLACEMENTS:
        count = text.count(old)
        if count > 0:
            text = text.replace(old, new)
            changes.append(f"  {label}: {count}x")

    for old, new, label in MIGRATED_TEMPORAL:
        count = text.count(old)
        if count > 0:
            text = text.replace(old, new)
            changes.append(f"  {label}: {count}x")

    if text != original:
        if not dry_run:
            path.write_text(text)
        return changes
    return []


def main() -> None:
    py_files = sorted(EXAMPLES_DIR.rglob("*.py"))
    print(f"Scanning {len(py_files)} .py files in {EXAMPLES_DIR}")
    print()

    total_changes = 0
    files_changed = 0

    for path in py_files:
        changes = migrate_file(path, dry_run=False)
        if changes:
            files_changed += 1
            total_changes += len(changes)
            rel = path.relative_to(EXAMPLES_DIR.parent)
            print(f"{rel}:")
            for c in changes:
                print(c)

    print()
    print(f"Done: {files_changed} files changed, {total_changes} replacement groups applied")


if __name__ == "__main__":
    main()
