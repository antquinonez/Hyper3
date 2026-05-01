"""Add docstrings to methods that are missing them.

Uses AST to find exact insertion points, avoiding the pitfalls of
text-based editing (eating body lines, wrong indentation, etc.).

Usage:
    # Add docstrings to specific methods
    .venv/bin/python ai/add_docstrings.py \\
        --map "abstraction.py:AbstractionNavigator.collapse_subgraph=Collapse a set of nodes..." \\
        --map "community.py:CommunityDetector.detect_label_propagation=Detect communities..."

    # Or call from another script with the DOCSTRING_MAP dict
    .venv/bin/python -c "
        from ai.add_docstrings import apply_docstrings
        apply_docstrings({
            ('abstraction.py', 'AbstractionNavigator', 'collapse_subgraph'): 'Collapse a set of nodes.',
        })
    "

The script works by:
1. Parsing each file with AST to find the target method.
2. Using the first body statement's line number to determine where to insert.
3. Using the first body statement's indentation to match the docstring indent.
4. Inserting the docstring line immediately before the first body statement.
5. Processing inserts in reverse line-number order so offsets stay valid.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from dataclasses import dataclass

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "hyper3")


@dataclass
class DocstringEdit:
    filepath: str
    cls_name: str
    method_name: str
    docstring: str


def _find_func_node(
    tree: ast.Module, cls_name: str, method_name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == method_name and not ast.get_docstring(item):
                        return item
            break
    return None


def _parse_map_entry(entry: str) -> DocstringEdit:
    parts = entry.split("=", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid --map entry (need file.py:Class.method=text): {entry}")
    target, docstring = parts
    if ":" not in target:
        raise ValueError(f"Invalid target (need file.py:Class.method): {target}")
    fname, class_method = target.split(":", 1)
    if "." not in class_method:
        raise ValueError(f"Invalid class.method in target: {class_method}")
    cls_name, method_name = class_method.split(".", 1)
    return DocstringEdit(
        filepath=os.path.join(SRC_DIR, fname),
        cls_name=cls_name,
        method_name=method_name,
        docstring=docstring.strip(),
    )


def apply_docstrings(
    docstring_map: dict[tuple[str, str, str], str],
    src_dir: str | None = None,
    *,
    dry_run: bool = False,
) -> int:
    """Apply docstrings from a (file, class, method) -> docstring mapping.

    Returns the number of docstrings inserted.
    """
    base = src_dir or SRC_DIR
    file_edits: dict[str, list[tuple[int, int, str]]] = {}

    for (fname, cls_name, method_name), docstring in docstring_map.items():
        filepath = os.path.join(base, fname)
        if filepath not in file_edits:
            file_edits[filepath] = []

        with open(filepath) as f:
            source = f.read()

        tree = ast.parse(source)
        func_node = _find_func_node(tree, cls_name, method_name)
        if func_node is None:
            print(f"  SKIP {fname}:{cls_name}.{method_name} (already has docstring or not found)")
            continue

        lines = source.split("\n")
        first_stmt_line = func_node.body[0].lineno - 1
        first_stmt_indent = len(lines[first_stmt_line]) - len(lines[first_stmt_line].lstrip())
        file_edits[filepath].append((first_stmt_line, first_stmt_indent, docstring))

    total = 0
    for filepath, edits in file_edits.items():
        if not edits:
            continue

        with open(filepath) as f:
            lines = f.read().split("\n")

        edits.sort(key=lambda x: x[0], reverse=True)

        for insert_before, indent_spaces, docstring in edits:
            indent = " " * indent_spaces
            doc_line = f'{indent}"""{docstring}"""'
            lines.insert(insert_before, doc_line)
            total += 1

        if not dry_run:
            with open(filepath, "w") as f:
                f.write("\n".join(lines))

        print(f"  Updated {filepath} ({len(edits)} docstrings)")

    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Add docstrings to methods missing them")
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        metavar="file.py:Class.method=Docstring text",
        help="One docstring entry; repeat for multiple",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing files",
    )
    args = parser.parse_args()

    if not args.map:
        parser.error("At least one --map entry is required")

    docstring_map: dict[tuple[str, str, str], str] = {}
    for entry in args.map:
        edit = _parse_map_entry(entry)
        fname = os.path.basename(edit.filepath)
        docstring_map[(fname, edit.cls_name, edit.method_name)] = edit.docstring

    total = apply_docstrings(docstring_map, dry_run=args.dry_run)
    print(f"\n{total} docstring(s) {'would be ' if args.dry_run else ''}inserted.")


if __name__ == "__main__":
    main()
