---
description: Regenerate API reference documentation
agent: build
---

Regenerate the API reference documentation.

1. Run `scripts/generate_api_docs.py` using the project venv Python (`.venv/bin/python`).
2. Report the output (number of modules, file size).
3. Do not commit the generated files.

If the script fails, investigate and fix the issue. Common causes:
- Import errors: check that `src/hyper3` is importable from the `src/` directory
- Missing modules: check that the module name in `PUBLIC_MODULES` list matches an actual file
