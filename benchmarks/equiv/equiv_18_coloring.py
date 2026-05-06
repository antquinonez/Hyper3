"""
Graph Coloring
===============
Greedy coloring, chromatic number, and related graph coloring algorithms.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("coloring")

    t.gap("greedy_coloring", "nx.greedy_color(G) -- assign colors so no adjacent nodes share a color")
    t.gap("chromatic_number", "Exact or approximate chromatic number (smallest colors needed)")
    t.gap("equitable_coloring", "nx.equitable_color(G, num_colors) -- balanced color class sizes")
    t.gap("strategy_coloring", "nx.coloring.greedy_color(G, strategy=...) -- largest_first, smallest_last, etc.")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
