"""
Basic Graph Metrics
====================
Diameter, radius, eccentricity, periphery, assortativity, and other
fundamental distance-based and mixing measures.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("basic_metrics")

    t.gap("diameter", "nx.diameter(G) -- longest shortest path length")
    t.gap("radius", "nx.radius(G) -- minimum eccentricity")
    t.gap("eccentricity", "nx.eccentricity(G) -- per-node max shortest path length")
    t.gap("periphery", "nx.periphery(G) -- nodes with eccentricity == diameter")
    t.gap("center", "nx.center(G) -- nodes with eccentricity == radius")
    t.gap("assortativity_degree", "nx.degree_assortativity_coefficient(G) -- Pearson correlation of degrees across edges")
    t.gap("assortativity_attribute", "nx.attribute_assortativity_coefficient(G, attr) -- mixing by node attribute")
    t.gap("average_neighbor_degree", "nx.average_neighbor_degree(G) -- mean neighbor degree per node")
    t.gap("average_degree_connectivity", "nx.average_degree_connectivity(G) -- avg neighbor degree by degree bin")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
