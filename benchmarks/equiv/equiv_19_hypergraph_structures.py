"""
Hypergraph-Specific Structures
================================
Encapsulation DAG, Hodge decomposition, simpliciality, face enumeration,
and other structures unique to hypergraphs / simplicial complexes.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("hypergraph_structures")

    t.gap("encapsulation_dag", "xgi.encapsulation_dag(H) -- DAG of edge containment relationships")
    t.gap("hodge_matrix", "xgi.hodge_matrix(SC) -- boundary / coboundary operators for simplicial complex")
    t.gap("hodge_laplacian", "xgi.hodge_laplacian(SC, order) -- combinatorial Laplacian per dimension")
    t.gap("simpliciality", "xgi.simplicial_edgewise(H) / simplicial_fraction(H) -- measure of how simplicial a hypergraph is")
    t.gap("face_enumeration", "Enumerate all faces/cofaces of a simplicial complex")
    t.gap("boundary_operator", "Compute boundary operator d_k for simplicial complex")
    t.gap("betticurve", "Betti curve (Betti numbers as function of threshold) for persistent homology")
    t.gap("persistence_diagram", "Persistence diagram from filtered hypergraph / clique complex")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
