"""Phase C: Migrate test files to new API. Safe mechanical replacements only."""
from __future__ import annotations

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"

SAFE_REPLACEMENTS = [
    (".store(", ".add(", "store->add"),
    (".relate(", ".link(", "relate->link"),
    (".has_node(", ".has(", "has_node->has"),
    (".graph.node_count", ".size[0]", "graph.node_count->size[0]"),
    (".graph.edge_count", ".size[1]", "graph.edge_count->size[1]"),
]


def migrate_file(path: Path) -> list[str]:
    text = path.read_text()
    original = text
    changes: list[str] = []

    for old, new, label in SAFE_REPLACEMENTS:
        count = text.count(old)
        if count > 0:
            text = text.replace(old, new)
            changes.append(f"  {label}: {count}x")

    if text != original:
        path.write_text(text)
        return changes
    return []


def main() -> None:
    py_files = sorted(TESTS_DIR.rglob("*.py"))
    print(f"Scanning {len(py_files)} test files")
    print()

    files_changed = 0
    for path in py_files:
        changes = migrate_file(path)
        if changes:
            files_changed += 1
            rel = path.relative_to(TESTS_DIR.parent)
            print(f"{rel}:")
            for c in changes:
                print(c)

    print(f"\nDone: {files_changed} files changed")


if __name__ == "__main__":
    main()
