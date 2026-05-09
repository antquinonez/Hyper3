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
3. **Update `examples/README.md`** if new examples were added.
4. **Update the Architecture section** if new modules were added.
5. **Update Key Conventions** if new conventions were introduced (e.g., weight semantics, context parameters).
6. **Update Common Pitfalls** if new pitfalls were discovered.
7. **Update the Extracted Modules or New Modules sections** if new result dataclasses were added to `results.py`.
8. **Update `src/hyper3/__init__.py`** if new public classes were added.
9. **Run full validation**: tests + pyright + ruff + examples + demos + benchmarks + equiv.
10. **Update `benchmarks/README.md`** if new benchmarks or equiv suites were added.
11. **Update project metrics** in this file and `README.md` (test count, coverage, example count, equiv counts).
12. **Run the equivalence battery** and verify 0 FAILs: `.venv/bin/python benchmarks/equiv/run_equiv.py`.

### Full Validation Checklist

Run this sequence after substantive changes. All gates must pass:

```bash
# 1. Test suite (3490 tests, must all pass)
.venv/bin/python -m pytest tests/ -q --tb=short

# 2. Type checking (0 errors)
.venv/bin/pyright src/hyper3/

# 3. Linting (0 errors)
.venv/bin/ruff check src/hyper3/ tests/

# 4. All examples (must complete without error)
for f in examples/showcase/*/*.py; do .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK $f" || echo "FAIL $f"; done
for f in examples/showcase/*/*.py; do .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK $f" || echo "FAIL $f"; done

# 5. All demos (must complete without error)
for f in demos/demo*.py; do .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK $f" || echo "FAIL $f"; done

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
- **Tests**: 3490
- **Test files**: 38 (one per source module + integration)
- **Coverage**: 98%
- **Pyright**: 0 errors
- **Ruff**: 0 errors
- **Examples**: 110 (47 Hyper3: 3 basic, 22 intermediate, 11 advanced, 11 domain, 5 project pipelines; 47 comparison + 8 laminar)
- **Equiv battery**: 788 pass / 0 fail / 54 gap (14 suites, HGX + XGI + NX)
