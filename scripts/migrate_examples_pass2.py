"""Phase 8 migration pass 2: migrate reverted patterns to proper namespace API."""
from __future__ import annotations

from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

REPLACEMENTS = [
    ("mem.temporal_engine.get_event(", "mem.temporal.get_event(", "temporal.get_event"),
    ("mem.temporal_engine.detect_causal_chains(", "mem.temporal.detect_causal_chains(", "temporal.detect_causal_chains"),
    ("mem.temporal_engine.infer_constraints(", "mem.temporal.infer_constraints(", "temporal.infer_constraints"),
    ("mem.temporal_engine.check_constraint_consistency(", "mem.temporal.check_constraint_consistency(", "temporal.check_constraint_consistency"),
    ("mem.temporal_engine.add_constraint(", "mem.temporal.add_constraint(", "temporal.add_constraint"),
    ("mem.temporal_engine.events", "mem.temporal.events", "temporal.events"),
    ("mem.belief_layer.von_neumann_entropy(", "mem.belief.von_neumann_entropy(", "belief.von_neumann_entropy"),
    ("mem.belief_layer.compute_density_matrix(", "mem.belief.density_matrix(", "belief.density_matrix"),
    ("mem.find_similar(", "mem.search.similar(", "find_similar->search.similar"),
    ("mem.detect_structural_anomalies(", "mem.analyze.anomalies(", "detect_structural_anomalies->analyze.anomalies"),
]


def migrate_file(path: Path) -> list[str]:
    text = path.read_text()
    original = text
    changes: list[str] = []

    for old, new, label in REPLACEMENTS:
        count = text.count(old)
        if count > 0:
            text = text.replace(old, new)
            changes.append(f"  {label}: {count}x")

    if text != original:
        path.write_text(text)
        return changes
    return []


def main() -> None:
    py_files = sorted(EXAMPLES_DIR.rglob("*.py"))
    print(f"Scanning {len(py_files)} .py files")
    print()

    files_changed = 0
    for path in py_files:
        changes = migrate_file(path)
        if changes:
            files_changed += 1
            rel = path.relative_to(EXAMPLES_DIR.parent)
            print(f"{rel}:")
            for c in changes:
                print(c)

    print(f"\nDone: {files_changed} files changed")


if __name__ == "__main__":
    main()
