"""
XGI Comparison: Generative Models
==================================
Parallels Hyper3's intermediate/27_generative_models.py.

Uses XGI 0.10.1 to create random hypergraphs via Erdos-Renyi,
uniform, Chung-Lu, and stochastic block model generators.
Contrasts XGI's API with Hyper3's generator functions.

Run: .venv/bin/python examples/comparison/xgi_09_generative.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Random Hypergraph (Erdos-Renyi)")
    print("=" * 70)

    import xgi

    H = xgi.random_hypergraph(15, ps=[0.3, 0.1], seed=42)
    print(f"nodes: {H.num_nodes}, edges: {H.num_edges}")

    degree_dict = H.nodes.degree.asdict()
    degree_hist = {}
    for d in degree_dict.values():
        degree_hist[d] = degree_hist.get(d, 0) + 1
    print(f"degree distribution: {dict(sorted(degree_hist.items()))}")

    size_dict = H.edges.size.asdict()
    unique_sizes = sorted(set(size_dict.values()))
    print(f"unique edge sizes: {unique_sizes}")
    print(f"is connected: {xgi.is_connected(H)}")

    print()
    print("=" * 70)
    print("SECTION 2: Uniform Hypergraph (k-uniform)")
    print("=" * 70)

    H2 = xgi.uniform_erdos_renyi_hypergraph(n=10, m=3, p=0.3, seed=42)
    print(f"nodes: {H2.num_nodes}, edges: {H2.num_edges}")

    size_dict2 = H2.edges.size.asdict()
    print(f"unique edge sizes: {sorted(set(size_dict2.values()))}")

    for e in sorted(H2.edges):
        members = H2.edges.members(e)
        print(f"  edge {e}: size={len(members)}, members={sorted(members)}")

    print()
    print("=" * 70)
    print("SECTION 3: Stochastic Block Model")
    print("=" * 70)

    import numpy as np

    p_tensor = np.array([
        [0.6, 0.03],
        [0.03, 0.6],
    ])
    H3 = xgi.uniform_HSBM(n=20, m=2, p=p_tensor, sizes=[10, 10], seed=42)
    print(f"nodes: {H3.num_nodes}, edges: {H3.num_edges}")

    components = list(xgi.connected_components(H3))
    print(f"connected components: {len(components)}")
    for i, comp in enumerate(components):
        print(f"  component {i}: {sorted(comp)}")

    print()
    print("=" * 70)
    print("SECTION 4: Chung-Lu Configuration Model")
    print("=" * 70)

    H4 = xgi.chung_lu_hypergraph(k1={0: 3, 1: 3, 2: 3, 3: 2, 4: 2}, k2={2: 2, 3: 2}, seed=42)
    print(f"nodes: {H4.num_nodes}, edges: {H4.num_edges}")

    size_dict4 = H4.edges.size.asdict()
    print(f"unique edge sizes: {sorted(set(size_dict4.values()))}")

    print()
    print("=" * 70)
    print("SECTION 5: Complete and Star Hypergraphs")
    print("=" * 70)

    H5 = xgi.complete_hypergraph(5, order=1)
    print(f"complete(5): nodes={H5.num_nodes}, edges={H5.num_edges}")

    print()
    print("=" * 70)
    print("SECTION 6: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
Hyper3 equivalents:
  random_hypergraph(n, ps)       <-> xgi.random_hypergraph(n, ps)
  random_uniform_hypergraph(n,m,k) <-> xgi.uniform_erdos_renyi_hypergraph(n,m,k)
  random_sbm(n, k, sizes, p_in, p_out) <-> xgi.uniform_HSBM(n, k, sizes, p, q)
  random_chung_lu(n, k1, k2)     <-> xgi.chung_lu_hypergraph(k1, k2)
  complete_hypergraph(n)         <-> xgi.complete_hypergraph(n)
  star_hypergraph(n)             <-> (no XGI equivalent)

XGI advantages:
  - More generator variants: flag complexes, simplicial complexes
  - DCSBM hypergraph for degree-corrected block models
  - Hypergraph configuration model with exact degree sequence

Hyper3 advantages:
  - star_hypergraph() built in
  - ring_lattice() for structured generation
  - Generators return Hypergraph with labeled, weighted edges
  - All generators accept prefix parameter for node labels
  - Can immediately use full analytics pipeline on generated graphs
""")


if __name__ == "__main__":
    main()
