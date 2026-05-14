#!/usr/bin/env python3
"""Generate Sphinx .rst source files from the PUBLIC_MODULES list.

Reuses the same module list as generate_api_docs.py so that the AI-consumable
docs (docs/api/) and the Sphinx docs (docs/sphinx/) stay in sync.

Run with: .venv/bin/python scripts/generate_sphinx_docs.py
"""
import importlib
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "docs" / "sphinx" / "source"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))  # noqa: E402

from generate_api_docs import PUBLIC_MODULES  # noqa: E402


def _grouped_modules() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for mod in PUBLIC_MODULES:
        short = mod.removeprefix("hyper3.")
        prefix = short.split("_")[0]
        if prefix in ("kernel", "memory"):
            prefix = short.rsplit("_", 1)[0] if "_" in short else short
        groups.setdefault(prefix, []).append(short)
    return groups


def generate_api_index() -> None:
    lines = [
        "API Reference\n",
        "=============\n",
        "\n",
        ".. toctree::\n",
        "   :maxdepth: 2\n",
        "   :caption: Modules\n",
        "   :glob:\n",
        "\n",
        "   api/*\n",
    ]
    (SOURCE_DIR / "api.rst").write_text("".join(lines))


def generate_module_rst(module_name: str) -> None:
    short = module_name.removeprefix("hyper3.")

    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return

    all_names = getattr(mod, "__all__", None)

    classes = []
    functions = []
    for name in sorted(dir(mod)):
        if name.startswith("_"):
            continue
        if all_names and name not in all_names:
            continue
        obj = getattr(mod, name, None)
        if obj is None:
            continue
        defining = getattr(obj, "__module__", "")
        if defining and defining != module_name and not defining.startswith(
            "hyper3." + module_name.removeprefix("hyper3.") + "."
        ):
            continue
        if inspect.isclass(obj):
            classes.append(name)
        elif inspect.isfunction(obj):
            functions.append(name)

    title = short
    lines = [
        f"{title}\n",
        f"{'=' * len(title)}\n",
        "\n",
    ]

    if mod.__doc__:
        doc = inspect.cleandoc(mod.__doc__)
        lines.append(f"{doc}\n\n")

    lines.append(f".. automodule:: {module_name}\n")
    lines.append("   :members:\n")
    lines.append("   :undoc-members:\n")
    lines.append("   :show-inheritance:\n")
    lines.append("\n")

    if classes:
        lines.append("Classes\n")
        lines.append("-------\n\n")
        for cls_name in classes:
            lines.append(f".. autoclass:: {module_name}.{cls_name}\n")
            lines.append("   :members:\n")
            lines.append("   :undoc-members:\n")
            lines.append("   :show-inheritance:\n")
            lines.append("   :inherited-members:\n")
            lines.append("\n")

    if functions:
        lines.append("Functions\n")
        lines.append("---------\n\n")
        for func_name in functions:
            lines.append(f".. autofunction:: {module_name}.{func_name}\n")
            lines.append("\n")

    api_dir = SOURCE_DIR / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / f"{short}.rst").write_text("".join(lines))


def generate() -> None:
    api_dir = SOURCE_DIR / "api"
    api_dir.mkdir(parents=True, exist_ok=True)

    for rst in api_dir.glob("*.rst"):
        rst.unlink()

    for module_name in PUBLIC_MODULES:
        print(f"  Generating {module_name}...", file=sys.stderr)
        generate_module_rst(module_name)

    generate_api_index()

    count = len(list(api_dir.glob("*.rst")))
    print(f"\nGenerated docs/sphinx/source/api/: {count} .rst files")


if __name__ == "__main__":
    generate()
