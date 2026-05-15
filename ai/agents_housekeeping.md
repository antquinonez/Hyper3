# Housekeeping and Validation

Extracted from [AGENTS.md](../AGENTS.md). Read this after making substantive changes (new features, bug fixes, API changes).

## Validation Commands

Run the equivalence battery after any changes to core hypergraph algorithms,
generative models, or graph transformations:

```bash
.venv/bin/python benchmarks/equiv/run_equiv.py              # all suites
.venv/bin/python benchmarks/equiv/run_equiv.py 03 06 12     # specific suites
```

Exit code 0 = no failures (gaps are expected and non-blocking).

## Housekeeping

After making substantive changes (new features, bug fixes, API changes), perform these housekeeping tasks:

1. **Update test count** in the "Making Changes" section of `AGENTS.md`.
2. **Update coverage report**: Run `.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short` and verify 95%+ per module.
3. **Update `README.md`** -- verify the Architecture section lists all current modules, the API reference reflects current methods, and all metrics (test count, module count, coverage, pyright/ruff error count, equiv counts) are accurate. This includes the Architecture tree, the benchmark/equiv paragraph, the testing line, and any example counts.
4. **Update `examples/README.md`** if new examples were added.
5. **Update the Architecture section** of `AGENTS.md` if new modules were added.
6. **Update Key Conventions** if new conventions were introduced (e.g., weight semantics, context parameters).
7. **Update Common Pitfalls** if new pitfalls were discovered.
8. **Update the Extracted Modules or New Modules sections** if new result dataclasses were added to `results.py`.
9. **Update `src/hyper3/__init__.py`** if new public classes were added.
10. **Run full validation**: tests + pyright + ruff + examples + demos + benchmarks + equiv.
11. **Update `benchmarks/README.md`** if new benchmarks or equiv suites were added.
12. **Update project metrics** in this file (test count, coverage, pyright/ruff error count, equiv counts).
13. **Run the equivalence battery** and verify 0 FAILs: `.venv/bin/python benchmarks/equiv/run_equiv.py`.

### Full Validation Checklist

Run this sequence after substantive changes. All gates must pass:

```bash
# 1. Test suite (4129 tests, must all pass)
.venv/bin/python -m pytest tests/ -q --tb=short

# 2. Type checking (0 errors)
.venv/bin/pyright src/hyper3/

# 3. Linting (0 errors)
.venv/bin/ruff check src/hyper3/ tests/

# 4. All examples (must complete without error)
for f in examples/showcase/*/*.py examples/showcase/*/*/*.py; do [ "$(basename "$f")" = "__init__.py" ] && continue; .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK $f" || echo "FAIL $f"; done
for f in examples/projects/*/pipeline.py; do .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK $f" || echo "FAIL $f"; done

# 5. All demos (must complete without error)
for f in demos/*/*.py; do .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK $f" || echo "FAIL $f"; done

# 6. Benchmarks (must complete without error)
.venv/bin/python benchmarks/run_all.py

# 7. Equivalence battery (0 FAILs, gaps are expected)
.venv/bin/python benchmarks/equiv/run_equiv.py
```

## AI Utilities

Reusable scripts for common bulk operations live in `ai/`. Run them with `.venv/bin/python ai/<script>.py`.

### Adding docstrings (`ai/add_docstrings.py`)

Bulk-inserts docstrings into methods that are missing them. Uses AST to find exact insertion points, avoiding text-editing pitfalls (eating body lines, wrong indentation).

**CLI usage** (one method at a time):
```bash
.venv/bin/python ai/add_docstrings.py \
    --map "kernel.py:Hypergraph._betweenness_bfs=BFS helper returning (delta, stack, sigma) for Brandes betweenness." \
    --map "kernel.py:Hypergraph._build_pagerank_transition=Build the incidence-based transition structure." \
    --dry-run  # preview without writing
```

**Programmatic usage** (batch of methods):
```bash
.venv/bin/python -c "
from ai.add_docstrings import apply_docstrings
apply_docstrings({
    ('abstraction.py', 'AbstractionNavigator', 'collapse_subgraph'): 'Collapse nodes into a summary.',
    ('community.py', 'CommunityDetector', 'detect_label_propagation'): 'Detect communities via label propagation.',
})
"
```

**How it works**: For each target method, the script parses the file with AST, finds the first body statement's line number and indentation, and inserts a `"""docstring"""` line immediately before it. Inserts are applied in reverse line-number order so earlier offsets stay valid.

**When to use**: After adding new classes or methods, run this to bulk-add docstrings rather than editing each file individually. Classes that already have docstrings and `__init__` methods are intentionally skipped.

Current project metrics (update after changes):
- **Tests**: 4129
- **Test files**: 83 (one per source module + integration)
- **Coverage**: 98%
- **Pyright**: 0 errors
- **Ruff**: 0 errors
- **Examples**: 69 showcase + 5 project pipelines + 53 comparison = 127 total
- **Equiv battery**: 871 pass / 17 diverge / 0 fail / 24 gap / 1 skip (24 suites, HGX + XGI + NX)
- **Benchmarks**: 15 (10 original + 5 new: bayesian, backward_chain, community, belief_distributions, multi_frame)

## Edit Safety

### ES-1: Verify match uniqueness before editing

The `Edit` tool replaces exact string matches. When `oldString` appears multiple times in a file, the edit fails with a "found multiple matches" error. To resolve this, include more surrounding context in `oldString` to make it unique.

**Critical hazard**: In test files, common patterns like `assert g.edge_count == 2` or `rule.apply(g, match)` can appear dozens of times. If you narrow `oldString` to include the *last* occurrence of such a pattern (e.g., the last few lines of the file), the edit will replace from that match point to the end of the file — **silently deleting everything after it** if `newString` is shorter than `oldString`.

**Prevention steps** (mandatory before every edit to a file with 200+ lines):
1. **Count matches**: Use `grep -c "your oldString pattern" <file>` to verify it appears exactly once. If it appears more than once, include more surrounding lines until it is unique.
2. **Prefer appending**: When adding new test classes to the end of a file, use a multi-line `oldString` that includes the *final* `def test_` method body plus its closing assert, and a `newString` that reproduces that method body *and* appends the new class. This avoids any risk of truncation.
3. **Verify after edit**: Immediately run `wc -l <file>` or `git diff --stat` after editing to confirm the file has *grown*, not shrunk. If the line count decreased unexpectedly, run `git checkout <file>` immediately and retry.
4. **Never match on generic patterns**: Do not use `assert g.edge_count == N` or `rule.apply(g, match)` alone as `oldString` in files like `test_multiway.py` or `test_rules.py` where these patterns repeat. Always include the surrounding `def test_` method signature to make the match unique.

### ES-2: Verify test count after editing existing test files

After editing any test file that already existed (not newly created), immediately compare the test count before and after:

```bash
# Before editing
grep -cE '^\s+def test_' tests/test_X.py

# After editing — must be >= before count
grep -cE '^\s+def test_' tests/test_X.py
```

If the count decreased, a test was accidentally deleted. Run `git checkout tests/test_X.py` and retry the edit.

## API Reference Documentation

Two auto-generated documentation pipelines share the same `PUBLIC_MODULES` list (defined in `scripts/generate_api_docs.py`). Both are gitignored and regenerated on demand.

### docs/api/ — AI-consumable Markdown (docstrings only)

Per-module Markdown files produced by `inspect`/`importlib`. Lightweight, no external tools required.

**Structure**:
- `docs/api/index.md` — concise index of all modules, classes, and one-line summaries (~55KB)
- `docs/api/<module>.md` — full docstrings, args, returns per module

**When to use it**: Read `docs/api/index.md` to discover relevant classes/methods, then read the specific module file for detail. This is faster than reading source files directly and avoids loading all 97 modules into context.

**How to regenerate**:
```bash
.venv/bin/python scripts/generate_api_docs.py
```

### docs/sphinx/ — Multi-format Sphinx documentation (full API with type resolution)

Sphinx builds from the same module list, using `autodoc` + `napoleon` to render Google-style docstrings with full type resolution, inherited members, cross-references, and intersphinx links to numpy/scipy/networkx.

**How to regenerate**:
```bash
.venv/bin/pip install -e ".[docs]"
.venv/bin/python scripts/generate_sphinx_docs.py
```

This generates `.rst` stubs then builds all three output formats:

| Format | Location | Use case |
|--------|----------|----------|
| HTML | `docs/sphinx/build/html/` | Human browsing (search, navigation, source links) |
| Plaintext | `docs/sphinx/build/text/` | AI context windows — clean `.txt` files, no markup, token-efficient (~1.5MB total) |
| JSON | `docs/sphinx/build/json/` | Programmatic traversal — structured `.fjson` per page with toctree, sections, cross-refs |

**Sphinx text output vs docs/api/ Markdown**: The Sphinx text format includes everything `docs/api` has plus inherited members, resolved cross-references, napoleon-rendered parameter/return types, and intersphinx links. For AI agents that need maximum API detail in minimal tokens, prefer `docs/sphinx/build/text/`.

**Hand-written source files** (tracked in git):
- `docs/sphinx/source/conf.py` — Sphinx configuration (autodoc, napoleon, viewviewcode, intersphinx)
- `docs/sphinx/source/index.rst` — Master toctree
- `docs/sphinx/source/user_guide.rst` — User guide
- `docs/sphinx/source/examples.rst` — Examples index

**Gitignored** (regenerated): `docs/sphinx/source/api/*.rst`, `docs/sphinx/build/`

**Regenerate both pipelines at once**: Type `/update-docs` in OpenCode.

**When to regenerate**: After adding, removing, or renaming public classes, methods, or exported symbols. The docs are not auto-updated on commit. To add a new module, append it to `PUBLIC_MODULES` in `scripts/generate_api_docs.py` and both pipelines will pick it up.

**Docstring standard**: Google-style (`Args:`, `Returns:`). Core modules have 100% coverage; newer subsystems (search, sqlite, embedding) have gaps that produce signature-only entries. When adding public methods, include a docstring so the next regeneration picks it up.
