---
description: Regenerate all documentation (API reference + Sphinx HTML)
agent: build
---

Regenerate both the AI-consumable API reference and the Sphinx HTML documentation.

1. Run `scripts/generate_api_docs.py` using the project venv Python (`.venv/bin/python`).
2. Run `scripts/generate_sphinx_docs.py` using the project venv Python (`.venv/bin/python`).
3. Build the Sphinx HTML: `.venv/bin/sphinx-build -b html docs/sphinx/source docs/sphinx/build/html`
4. Report the output (number of modules, file sizes, build status).
5. Do not commit the generated files.

Both scripts share the same `PUBLIC_MODULES` list (defined in `generate_api_docs.py`).
When adding a new module, add it to `PUBLIC_MODULES` in `scripts/generate_api_docs.py`
and both doc sets will pick it up on the next regeneration.

If a script fails, investigate and fix the issue. Common causes:
- Import errors: check that `src/hyper3` is importable from the `src/` directory
- Missing modules: check that the module name in `PUBLIC_MODULES` list matches an actual file
- Sphinx warnings: check for duplicate object descriptions or missing imports
