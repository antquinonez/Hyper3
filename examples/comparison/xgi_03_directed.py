"""
XGI Comparison: Directed Hypergraphs
=====================================
Parallels Hyper3's basic/17_directed_hypergraphs.py.

Uses xgi.DiHypergraph to create directed edges with tail/head sets,
compute in/out degree, access tail/head membership, and compare with
Hyper3's in_degree(), out_degree(), edges_labeled().

Run: .venv/bin/python examples/comparison/xgi_03_directed.py
"""

from __future__ import annotations

import xgi


def main() -> None:
    print("=" * 70)
    print("SECTION 1: DIRECTED HYPERGRAPH CONSTRUCTION")
    print("=" * 70)

    DH = xgi.DiHypergraph()
    DH.add_edge(({0, 1}, {2}))
    DH.add_edge(({2}, {3, 4}))
    DH.add_edge(({3}, {5}))

    DH.edges[0]["label"] = "activation"
    DH.edges[1]["label"] = "branching"
    DH.edges[2]["label"] = "cascade"

    print(f"nodes: {DH.num_nodes}")
    print(f"edges: {DH.num_edges}")
    print(f"node list: {sorted(DH.nodes)}")
    print(f"edge list: {sorted(DH.edges)}")

    print()
    for e in DH.edges:
        tail, head = DH.edges.dimembers(e)
        label = DH.edges[e].get("label", "unlabeled")
        print(f"  edge {e} ({label}): tail={sorted(tail)} -> head={sorted(head)}")

    print()
    print("=" * 70)
    print("SECTION 2: IN-DEGREE / OUT-DEGREE")
    print("=" * 70)

    in_deg = DH.nodes.in_degree.asdict()
    out_deg = DH.nodes.out_degree.asdict()

    print(f"{'node':>6} {'in_deg':>8} {'out_deg':>8} {'total':>8}")
    print("-" * 34)
    for n in sorted(DH.nodes):
        ind = in_deg[n]
        outd = out_deg[n]
        print(f"{n:>6} {ind:>8} {outd:>8} {ind + outd:>8}")

    print()
    print(f"in-degree range:  [{min(in_deg.values())}, {max(in_deg.values())}]")
    print(f"out-degree range: [{min(out_deg.values())}, {max(out_deg.values())}]")

    print()
    print("=" * 70)
    print("SECTION 3: TAIL / HEAD ACCESS")
    print("=" * 70)

    print(f"{'edge':>6} {'label':>12} {'tail':>12} {'head':>12} {'|t|':>4} {'|h|':>4}")
    print("-" * 56)
    for e in sorted(DH.edges):
        tail, head = DH.edges.dimembers(e)
        label = DH.edges[e].get("label", "unlabeled")
        print(f"{e:>6} {label:>12} {str(sorted(tail)):>12} {str(sorted(head)):>12} {len(tail):>4} {len(head):>4}")

    print()
    print("=" * 70)
    print("SECTION 4: REACHABILITY AND PATHS")
    print("=" * 70)

    def forward_reachable(dh, start):
        visited = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            for e in dh.edges:
                tail, head = dh.edges.dimembers(e)
                if node in tail:
                    for h in head:
                        if h not in visited:
                            stack.append(h)
        return visited

    reachable_from_0 = forward_reachable(DH, 0)
    print(f"forward reachable from node 0: {sorted(reachable_from_0)}")

    reachable_from_2 = forward_reachable(DH, 2)
    print(f"forward reachable from node 2: {sorted(reachable_from_2)}")

    print()
    print("=" * 70)
    print("SECTION 5: ADDING MORE DIRECTED EDGES")
    print("=" * 70)

    DH.add_edge(({5}, {0}))
    DH.edges[3]["label"] = "feedback_loop"

    print(f"after adding feedback: {DH.num_edges} edges")
    for e in sorted(DH.edges):
        tail, head = DH.edges.dimembers(e)
        label = DH.edges[e].get("label", "unlabeled")
        print(f"  edge {e} ({label}): {sorted(tail)} -> {sorted(head)}")

    in_deg2 = DH.nodes.in_degree.asdict()
    out_deg2 = DH.nodes.out_degree.asdict()
    print()
    print(f"{'node':>6} {'in_deg':>8} {'out_deg':>8}")
    print("-" * 26)
    for n in sorted(DH.nodes):
        print(f"{n:>6} {in_deg2[n]:>8} {out_deg2[n]:>8}")

    print()
    print("=" * 70)
    print("SECTION 6: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
XGI advantages for directed hypergraphs:
  - First-class DiHypergraph class with clean construction API
  - add_edge(({tail_set}, {head_set})) is intuitive and explicit
  - dimembers() returns (tail, head) pair directly
  - in_degree / out_degree as lazy stat objects
  - Built-in tail_size / head_size edge statistics

Hyper3 advantages:
  - in_degree() / out_degree() return label-keyed dicts directly
  - edges_labeled() filters by label with cardinality info
  - neighbors(direction="in"|"out"|"any") for directed traversal
  - relate_hyperedge(sources={...}, targets={...}) with weights
  - Semantic inference: TransitiveRule respects edge direction
  - outgoing_edges() / incoming_edges() for directional access
  - betweenness_centrality() is hypergraph-native and directed

Common patterns:
  XGI:  DH.add_edge(({0,1}, {2,3}))
  H3:   mem.relate_hyperedge(sources={"a","b"}, targets={"c","d"})
  
  XGI:  DH.nodes.in_degree.asdict()
  H3:   mem.in_degree()
  
  XGI:  DH.edges.dimembers(e)   -> (tail, head)
  H3:   edge.source_ids, edge.target_ids
""")


if __name__ == "__main__":
    main()
