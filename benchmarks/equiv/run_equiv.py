"""
Runner for the Hyper3 equivalence test battery.

Discovers and runs all equiv_*.py scripts, prints a summary table.

Usage:
    .venv/bin/python benchmarks/equiv/run_equiv.py              # run all
    .venv/bin/python benchmarks/equiv/run_equiv.py 01 03 06     # run specific suites
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SUITES = sorted(HERE.glob("equiv_*.py"))

SYMBOLS = {"PASS": "+", "FAIL": "X", "GAP": "?", "SKIP": "-"}


def main() -> None:
    selected = sys.argv[1:] if len(sys.argv) > 1 else []
    total_passed = 0
    total_failed = 0
    total_gaps = 0
    total_skipped = 0
    any_failure = False

    print("Hyper3 Equivalence Test Battery")
    print("=" * 70)

    for path in SUITES:
        suite_num = path.stem.replace("equiv_", "")
        if selected and suite_num not in selected:
            continue

        mod_name = f"benchmarks.equiv.{path.stem}"
        try:
            mod = importlib.import_module(mod_name)
        except Exception as exc:
            print(f"\n  {path.stem}: IMPORT ERROR -- {exc}")
            any_failure = True
            continue

        try:
            result = mod.run()
        except Exception as exc:
            print(f"\n  {path.stem}: RUNTIME ERROR -- {exc}")
            any_failure = True
            continue

        s = result.summary
        symbols = "".join(SYMBOLS.get(r.status, "?") for r in s.results)
        line = f"  {path.stem:<30s} {symbols}"
        print(f"{line}")
        for r in s.results:
            if r.status == "FAIL":
                sym = SYMBOLS[r.status]
                print(f"    [{sym}] {r.name}  -- {r.detail}")

        total_passed += s.passed
        total_failed += s.failed
        total_gaps += s.gaps
        total_skipped += s.skipped
        if s.failed > 0:
            any_failure = True

    print()
    print(f"  TOTALS: {total_passed} pass / {total_failed} fail / {total_gaps} gap / {total_skipped} skip")

    if any_failure:
        print("\n  STATUS: FAILURES DETECTED")
        sys.exit(1)
    else:
        print("\n  STATUS: ALL EQUIVALENCE TESTS PASSED (gaps are expected)")
        sys.exit(0)


if __name__ == "__main__":
    main()
