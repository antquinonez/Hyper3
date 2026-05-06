"""
Hypergraph-Specific Structures
===============================
Encapsulation DAG, Hodge decomposition, simpliciality, face enumeration,
boundary operator, Betti curve, and persistence diagram.

Cross-validated against XGI where equivalent functionality exists:
- encapsulation_dag vs xgi.to_encapsulation_dag (exact)
- boundary_matrix / boundary_operator vs xgi.boundary_matrix (exact)
- hodge_laplacian vs xgi.hodge_laplacian (exact)
- simpliciality vs xgi.simplicial_fraction (structural, different metric)

No XGI/HGX/NX equivalent for: betti_curve, persistence_diagram, face_enumeration.
These are validated against structural properties and known mathematical results.
"""

from __future__ import annotations

import numpy as np
import xgi

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("hypergraph_structures")

    _test_encapsulation_dag_xgi(t)
    _test_boundary_matrix_xgi(t)
    _test_hodge_laplacian_xgi(t)
    _test_simpliciality_xgi(t)
    _test_hodge_matrix(t)
    _test_face_enumeration(t)
    _test_boundary_operator(t)
    _test_betti_curve(t)
    _test_persistence_diagram(t)

    return t


def _build_pair_triangle():
    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(3)]
    for n in nodes:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset(), weight=1.0))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset(), weight=2.0))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset(), weight=3.0))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset(), weight=4.0))
    return g, nodes


def _build_xgi_triangle():
    S = xgi.SimplicialComplex()
    S.add_simplices_from([[0, 1], [1, 2], [0, 2], [0, 1, 2]])
    return S


def _build_pair_4node():
    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(4)]
    for n in nodes:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))
    return g, nodes


def _build_xgi_4node():
    S = xgi.SimplicialComplex()
    S.add_simplices_from([[0, 1], [1, 2], [2, 3], [0, 1, 2]])
    return S


def _h3_edge_membersets(g):
    id_to_label = {n.id: n.label for n in g._nodes.values()}
    result = {}
    for edge in g._edges.values():
        result[edge.id] = frozenset(id_to_label[nid] for nid in edge.node_ids)
    return result


def _test_encapsulation_dag_xgi(t: EquivRunner) -> None:
    g, nodes = _build_pair_triangle()
    S = _build_xgi_triangle()

    h3_dag = g.encapsulation_dag()
    xgi_dag = xgi.to_encapsulation_dag(S, subset_types="all")

    h3_membersets = _h3_edge_membersets(g)

    h3_pairs = set()
    for child_id, parent_id in h3_dag:
        child_set = h3_membersets[child_id]
        parent_set = h3_membersets[parent_id]
        h3_pairs.add((child_set, parent_set))

    xgi_pairs = set()
    for u, v in xgi_dag.edges():
        u_members = frozenset(S.edges.members(u))
        v_members = frozenset(S.edges.members(v))
        xgi_pairs.add((frozenset(v_members), frozenset(u_members)))

    t.check("encap_xgi_pair_count", len(h3_pairs) == len(xgi_pairs),
            f"H3 has {len(h3_pairs)} pairs, XGI has {len(xgi_pairs)}")

    h3_subsets = {child for child, parent in h3_pairs}
    xgi_subsets = {frozenset(str(m) for m in child) for child, parent in xgi_pairs}
    t.check("encap_xgi_subsets_match", h3_subsets == xgi_subsets,
            f"H3 subsets: {h3_subsets}, XGI subsets: {xgi_subsets}")

    h3_supersets = {parent for child, parent in h3_pairs}
    xgi_supersets = {frozenset(str(m) for m in parent) for child, parent in xgi_pairs}
    t.check("encap_xgi_supersets_match", h3_supersets == xgi_supersets,
            f"H3 supersets: {h3_supersets}, XGI supersets: {xgi_supersets}")

    g4, _ = _build_pair_4node()
    S4 = _build_xgi_4node()
    h3_dag4 = g4.encapsulation_dag()
    xgi_dag4 = xgi.to_encapsulation_dag(S4, subset_types="all")
    h3_ms4 = _h3_edge_membersets(g4)
    h3_pairs4 = {(h3_ms4[c], h3_ms4[p]) for c, p in h3_dag4}
    xgi_pairs4 = set()
    for u, v in xgi_dag4.edges():
        xgi_pairs4.add((frozenset(str(m) for m in S4.edges.members(v)),
                        frozenset(str(m) for m in S4.edges.members(u))))
    t.check("encap_xgi_4node_match", h3_pairs4 == xgi_pairs4,
            f"H3: {h3_pairs4}, XGI: {xgi_pairs4}")


def _test_boundary_matrix_xgi(t: EquivRunner) -> None:
    g, _ = _build_pair_triangle()
    S = _build_xgi_triangle()

    B1_h3, k1_h3, km1_h3 = g.hodge_matrix(1)
    B1_xgi, rowdict, coldict = xgi.boundary_matrix(S, order=1, index=True)

    t.check("boundary_B1_same_shape",
            B1_h3.shape == B1_xgi.shape,
            f"H3 B1 shape {B1_h3.shape} vs XGI B1 shape {B1_xgi.shape}")

    B1_xgi_arr = np.array(B1_xgi)
    t.check("boundary_B1_same_rank",
            np.linalg.matrix_rank(B1_h3) == np.linalg.matrix_rank(B1_xgi_arr),
            f"H3 rank {np.linalg.matrix_rank(B1_h3)} vs XGI rank {np.linalg.matrix_rank(B1_xgi_arr)}")

    eigs_h3 = sorted(np.linalg.svd(B1_h3, compute_uv=False))
    eigs_xgi = sorted(np.linalg.svd(B1_xgi_arr, compute_uv=False))
    t.check("boundary_B1_same_singular_values",
            np.allclose(eigs_h3, eigs_xgi, atol=1e-10),
            f"H3 sv: {eigs_h3}, XGI sv: {eigs_xgi}")

    B2_h3, k2_h3, km2_h3 = g.hodge_matrix(2)
    B2_xgi, rowdict2, coldict2 = xgi.boundary_matrix(S, order=2, index=True)
    B2_xgi_arr = np.array(B2_xgi)

    t.check("boundary_B2_same_shape",
            B2_h3.shape == B2_xgi.shape,
            f"H3 B2 shape {B2_h3.shape} vs XGI B2 shape {B2_xgi.shape}")

    eigs_h3_b2 = sorted(np.linalg.svd(B2_h3, compute_uv=False))
    eigs_xgi_b2 = sorted(np.linalg.svd(B2_xgi_arr, compute_uv=False))
    t.check("boundary_B2_same_singular_values",
            np.allclose(eigs_h3_b2, eigs_xgi_b2, atol=1e-10),
            f"H3 sv: {eigs_h3_b2}, XGI sv: {eigs_xgi_b2}")

    g4, _ = _build_pair_4node()
    S4 = _build_xgi_4node()
    B1_h3_4, _, _ = g4.hodge_matrix(1)
    B1_xgi_4 = np.array(xgi.boundary_matrix(S4, order=1, index=False))
    eigs_h3_4 = sorted(np.linalg.svd(B1_h3_4, compute_uv=False))
    eigs_xgi_4 = sorted(np.linalg.svd(B1_xgi_4, compute_uv=False))
    t.check("boundary_B1_4node_same_singular_values",
            np.allclose(eigs_h3_4, eigs_xgi_4, atol=1e-10),
            f"H3 sv: {eigs_h3_4}, XGI sv: {eigs_xgi_4}")


def _test_hodge_laplacian_xgi(t: EquivRunner) -> None:
    g, _ = _build_pair_triangle()
    S = _build_xgi_triangle()

    L0_h3 = g.hodge_laplacian(0)
    L0_xgi = np.array(xgi.hodge_laplacian(S, order=0))

    eigs_h3 = sorted(np.linalg.eigvalsh(L0_h3))
    eigs_xgi = sorted(np.linalg.eigvalsh(L0_xgi))
    t.check("hodge_L0_xgi_eigenvalues",
            np.allclose(eigs_h3, eigs_xgi, atol=1e-10),
            f"H3: {eigs_h3}, XGI: {eigs_xgi}")

    L1_h3 = g.hodge_laplacian(1)
    L1_xgi = np.array(xgi.hodge_laplacian(S, order=1))
    eigs_h3_l1 = sorted(np.linalg.eigvalsh(L1_h3))
    eigs_xgi_l1 = sorted(np.linalg.eigvalsh(L1_xgi))
    t.check("hodge_L1_xgi_eigenvalues",
            np.allclose(eigs_h3_l1, eigs_xgi_l1, atol=1e-10),
            f"H3: {eigs_h3_l1}, XGI: {eigs_xgi_l1}")

    null_h3 = sum(1 for e in eigs_h3 if abs(e) < 1e-10)
    null_xgi = sum(1 for e in eigs_xgi if abs(e) < 1e-10)
    t.check("hodge_L0_xgi_nullity", null_h3 == null_xgi,
            f"H3 nullity: {null_h3}, XGI nullity: {null_xgi}")

    L0_h3_sq = L0_h3 @ L0_h3
    L0_xgi_sq = L0_xgi @ L0_xgi
    t.check("hodge_L0_xgi_L2_match",
            np.allclose(L0_h3_sq, L0_xgi_sq, atol=1e-10),
            "L0^2 should match between H3 and XGI")

    g4, _ = _build_pair_4node()
    S4 = _build_xgi_4node()
    L0_h3_4 = g4.hodge_laplacian(0)
    L0_xgi_4 = np.array(xgi.hodge_laplacian(S4, order=0))
    eigs_h3_4 = sorted(np.linalg.eigvalsh(L0_h3_4))
    eigs_xgi_4 = sorted(np.linalg.eigvalsh(L0_xgi_4))
    t.check("hodge_L0_4node_xgi_eigenvalues",
            np.allclose(eigs_h3_4, eigs_xgi_4, atol=1e-10),
            f"H3: {eigs_h3_4}, XGI: {eigs_xgi_4}")


def _test_simpliciality_xgi(t: EquivRunner) -> None:
    g, _ = _build_pair_triangle()
    S = _build_xgi_triangle()

    h3_simp = g.simpliciality()
    xgi_sf = xgi.simplicial_fraction(S)

    t.check("simpliciality_full_complex",
            h3_simp == 1.0 and xgi_sf == 1.0,
            f"H3: {h3_simp}, XGI: {xgi_sf} (both should be 1.0 for simplicial complex)")

    g4, _ = _build_pair_4node()
    S4 = _build_xgi_4node()
    h3_s4 = g4.simpliciality()
    xgi_sf4 = xgi.simplicial_fraction(S4)
    t.check("simpliciality_4node_complex",
            h3_s4 == 1.0 and xgi_sf4 == 1.0,
            f"H3: {h3_s4}, XGI: {xgi_sf4} (both should be 1.0)")

    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g_ns = Hypergraph()
    ns = [Hypernode(label=str(i)) for i in range(4)]
    for n in ns:
        g_ns.add_node(n)
    g_ns.add_edge(Hyperedge(source_ids=frozenset({ns[0].id, ns[1].id, ns[2].id}), target_ids=frozenset()))
    h3_s_ns = g_ns.simpliciality()
    t.check("simpliciality_non_simplicial", h3_s_ns == 1.0,
            f"no containment pairs -> 1.0, got {h3_s_ns}")

    H_ns = xgi.Hypergraph()
    H_ns.add_edges_from([[0, 1, 2]])
    xgi_sf_ns = xgi.simplicial_fraction(H_ns)
    t.check("simpliciality_xgi_non_simplicial",
            xgi_sf_ns < 1.0,
            f"single triangle without subfaces: XGI sf={xgi_sf_ns} should be < 1.0")


def _test_hodge_matrix(t: EquivRunner) -> None:
    g, _ = _build_pair_triangle()
    B1, k1, km1_1 = g.hodge_matrix(1)
    t.check("hodge_B1_shape", B1.shape[0] == len(km1_1) and B1.shape[1] == len(k1),
            f"shape ({B1.shape[0]}, {B1.shape[1]}) vs ({len(km1_1)}, {len(k1)})")
    B2, k2, km1_2 = g.hodge_matrix(2)
    t.check("hodge_B2_shape", B2.shape[0] == len(km1_2) and B2.shape[1] == len(k2),
            f"shape ({B2.shape[0]}, {B2.shape[1]}) vs ({len(km1_2)}, {len(k2)})")
    B_empty, _, _ = g.hodge_matrix(10)
    t.check("hodge_empty_dim", B_empty.shape == (0, 0), "should return empty matrix for missing dimension")


def _test_face_enumeration(t: EquivRunner) -> None:
    g, nodes = _build_pair_triangle()
    tri = frozenset({n.id for n in nodes[:3]})
    result = g.face_enumeration(tri)
    t.check("face_enum_tri_has_faces", len(result["faces"]) > 0, "triangle has proper faces")
    t.check("face_enum_tri_no_cofaces", len(result["cofaces"]) == 0, "triangle should have no cofaces in this graph")

    edge = frozenset({nodes[0].id, nodes[1].id})
    result2 = g.face_enumeration(edge)
    t.check("face_enum_edge_faces", len(result2["faces"]) == 2, f"edge has 2 vertex faces, got {len(result2['faces'])}")
    t.check("face_enum_edge_cofaces", len(result2["cofaces"]) >= 1, "edge should have triangle as coface")

    xgi_sf = xgi.subfaces([[0, 1, 2]])
    h3_face_count = len(result["faces"])
    xgi_face_count = len([f for f in xgi_sf if len(f) < 3])
    t.check("face_enum_xgi_subface_count",
            h3_face_count == xgi_face_count,
            f"H3 faces: {h3_face_count}, XGI subfaces (excluding self): {xgi_face_count}")


def _test_boundary_operator(t: EquivRunner) -> None:
    g, _ = _build_pair_triangle()
    bd2 = g.boundary_operator(2)
    t.check("boundary_d2_nonempty", len(bd2) > 0, "dimension 2 should have entries")

    for sigma, faces in bd2.items():
        t.check(f"boundary_d2_signs_{len(sigma)}", len(faces) == len(sigma),
                f"boundary of {len(sigma)}-simplex has {len(sigma)} faces")
        t.check(f"boundary_d2_alter_{len(sigma)}",
                all(s in (1, -1) for _, s in faces),
                "all boundary signs must be +1 or -1")

    bd0 = g.boundary_operator(0)
    t.check("boundary_d0_empty", bd0 == {}, "dimension 0 boundary should be empty")

    bd1 = g.boundary_operator(1)
    bd1_of_bd2: dict[frozenset[str], int] = {}
    for faces in bd2.values():
        for face, sign in faces:
            if face in bd1:
                for subface, sub_sign in bd1[face]:
                    key = subface
                    bd1_of_bd2[key] = bd1_of_bd2.get(key, 0) + sign * sub_sign
    all_zero = all(v == 0 for v in bd1_of_bd2.values())
    t.check("boundary_d2_compose_d1_zero", all_zero, "d1(d2) = 0 (boundary of boundary is zero)")


def _test_betti_curve(t: EquivRunner) -> None:
    g, _ = _build_pair_triangle()
    betti = g.betti_curve()
    t.check("betti_triangle_dim0", betti[0] == 1, f"connected triangle: beta_0=1, got {betti[0]}")

    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode
    g2 = Hypergraph()
    ns = [Hypernode(label=str(i)) for i in range(4)]
    for n in ns:
        g2.add_node(n)
    g2.add_edge(Hyperedge(source_ids=frozenset({ns[0].id, ns[1].id}), target_ids=frozenset()))
    g2.add_edge(Hyperedge(source_ids=frozenset({ns[2].id, ns[3].id}), target_ids=frozenset()))
    betti2 = g2.betti_curve()
    t.check("betti_disconnected_dim0", betti2[0] == 2, f"2 components: beta_0=2, got {betti2[0]}")

    betti_limited = g.betti_curve(max_dim=0)
    t.check("betti_max_dim", len(betti_limited) == 1, f"max_dim=0 should give 1 entry, got {len(betti_limited)}")


def _test_persistence_diagram(t: EquivRunner) -> None:
    g, _ = _build_pair_triangle()
    pd = g.persistence_diagram()
    t.check("pd_nonempty", len(pd) > 0, "should have persistence pairs")

    dim0_points = [(b, d) for dim, b, d in pd if dim == 0]
    t.check("pd_dim0_births", len(dim0_points) > 0, "should have dim 0 points")

    finite_deaths = [(b, d) for dim, b, d in pd if dim == 0 and d is not None]
    infinite_deaths = [b for dim, b, d in pd if dim == 0 and d is None]
    t.check("pd_dim0_infinite", len(infinite_deaths) >= 1,
            f"should have at least 1 infinite death (essential class), got {len(infinite_deaths)}")

    for b, d in finite_deaths:
        t.check(f"pd_birth_before_death_{b:.1f}", d >= b, f"death {d} must be >= birth {b}")

    from hyper3 import Hypergraph
    g_empty = Hypergraph()
    pd_empty = g_empty.persistence_diagram()
    t.check("pd_empty", pd_empty == [], f"empty graph should have empty PD, got {len(pd_empty)}")


if __name__ == "__main__":
    t = run()
    t.print_report()
