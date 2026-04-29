"""
ArXiv Research Navigator — Pandas + NetworkX Baseline
======================================================
Same data source and problem as the Hyper3 Prefect pipeline, solved with
pandas DataFrames and a NetworkX bipartite graph. Implements degree
centrality, betweenness centrality, simple category-overlap clustering,
and prolific-author detection. Ends with a brief comparison to the
Hyper3 approach.

Run with:
    .venv/bin/python examples/comparison/arxiv_navigator/pandas_analysis.py
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx
import pandas as pd


ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

ARXIV_API_URL = (
    "http://export.arxiv.org/api/query"
    "?search_query=cat:cs.AI+AND+cat:cs.LG"
    "&max_results=50"
    "&sortBy=submittedDate"
    "&sortOrder=descending"
)


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    categories: list[str]
    abstract: str
    published: str


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return (element.text or "").strip()


def fetch_papers() -> list[ArxivPaper]:
    with urllib.request.urlopen(ARXIV_API_URL, timeout=30) as resp:
        payload = resp.read()
    root = ET.fromstring(payload)
    papers: list[ArxivPaper] = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        raw_id = _text(entry.find(f"{{{ATOM_NS}}}id"))
        arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
        title = " ".join(_text(entry.find(f"{{{ATOM_NS}}}title")).split())
        authors = [
            _text(a.find(f"{{{ATOM_NS}}}name"))
            for a in entry.findall(f"{{{ATOM_NS}}}author")
        ]
        cat_elements = entry.findall(f"{{{ARXIV_NS}}}primary_category")
        categories = [c.attrib.get("term", "") for c in cat_elements]
        for sc in entry.findall(f"{{{ATOM_NS}}}category"):
            term = sc.attrib.get("term", "")
            if term not in categories:
                categories.append(term)
        abstract = " ".join(_text(entry.find(f"{{{ATOM_NS}}}summary")).split())
        published = _text(entry.find(f"{{{ATOM_NS}}}published"))[:10]
        papers.append(ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            categories=categories,
            abstract=abstract,
            published=published,
        ))
    return papers


def build_dataframes(papers: list[ArxivPaper]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paper_rows = []
    for p in papers:
        paper_rows.append({
            "arxiv_id": p.arxiv_id,
            "title": p.title,
            "abstract_snippet": p.abstract[:200],
            "year": p.published[:4],
            "published": p.published,
            "category_count": len(p.categories),
            "author_count": len(p.authors),
        })
    df_papers = pd.DataFrame(paper_rows)

    author_rows = []
    edge_rows = []
    for p in papers:
        for author in p.authors:
            author_rows.append({"author": author, "paper": p.arxiv_id})
            edge_rows.append({"source": p.arxiv_id, "target": author, "edge_type": "authored_by"})
        for cat in p.categories:
            edge_rows.append({"source": p.arxiv_id, "target": cat, "edge_type": "published_in"})

    df_authorships = pd.DataFrame(author_rows)
    df_edges = pd.DataFrame(edge_rows)
    return df_papers, df_authorships, df_edges


def build_bipartite_graph(df_edges: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    for _, row in df_edges.iterrows():
        G.add_node(row["source"], bipartite="paper")
        G.add_node(row["target"], bipartite=row["edge_type"])
        G.add_edge(row["source"], row["target"], edge_type=row["edge_type"])
    return G


def degree_centrality_analysis(G: nx.Graph, df_papers: pd.DataFrame) -> pd.DataFrame:
    dc = nx.degree_centrality(G)
    paper_ids = set(df_papers["arxiv_id"])
    paper_dc = {k: v for k, v in dc.items() if k in paper_ids}
    df_dc = pd.DataFrame([
        {"arxiv_id": k, "degree_centrality": v} for k, v in sorted(paper_dc.items(), key=lambda x: -x[1])
    ])
    return df_dc.merge(df_papers[["arxiv_id", "title"]], on="arxiv_id", how="left")


def betweenness_analysis(G: nx.Graph, df_papers: pd.DataFrame) -> pd.DataFrame:
    bc = nx.betweenness_centrality(G, normalized=True)
    paper_ids = set(df_papers["arxiv_id"])
    paper_bc = {k: v for k, v in bc.items() if k in paper_ids}
    df_bc = pd.DataFrame([
        {"arxiv_id": k, "betweenness": v} for k, v in sorted(paper_bc.items(), key=lambda x: -x[1])
    ])
    return df_bc.merge(df_papers[["arxiv_id", "title"]], on="arxiv_id", how="left")


def category_overlap_clustering(df_authorships: pd.DataFrame, df_papers: pd.DataFrame) -> list[dict]:
    paper_authors: dict[str, set[str]] = defaultdict(set)
    for _, row in df_authorships.iterrows():
        paper_authors[row["paper"]].add(row["author"])

    paper_ids = list(paper_authors.keys())
    clusters: dict[str, list[str]] = {}
    assigned: dict[str, str] = {}

    for i in range(len(paper_ids)):
        p1 = paper_ids[i]
        if p1 in assigned:
            continue
        cluster_key = p1
        clusters[cluster_key] = [p1]
        assigned[p1] = cluster_key
        for j in range(i + 1, len(paper_ids)):
            p2 = paper_ids[j]
            if p2 in assigned:
                continue
            overlap = len(paper_authors[p1] & paper_authors[p2])
            if overlap > 0:
                clusters[cluster_key].append(p2)
                assigned[p2] = cluster_key

    result = []
    title_map = dict(zip(df_papers["arxiv_id"], df_papers["title"]))
    for key, members in sorted(clusters.items(), key=lambda x: -len(x[1]))[:10]:
        result.append({
            "cluster_representative": key,
            "size": len(members),
            "papers": members[:5],
            "titles": [title_map.get(m, "")[:60] for m in members[:5]],
        })
    return result


def prolific_author_analysis(df_authorships: pd.DataFrame) -> pd.DataFrame:
    counts = df_authorships.groupby("author").size().reset_index(name="paper_count")
    return counts.sort_values("paper_count", ascending=False).head(10).reset_index(drop=True)


def print_report(
    df_papers: pd.DataFrame,
    df_centrality: pd.DataFrame,
    df_betweenness: pd.DataFrame,
    clusters: list[dict],
    df_prolific: pd.DataFrame,
) -> None:
    print("=" * 70)
    print("ArXiv Research Navigator — Pandas + NetworkX Analysis")
    print("=" * 70)

    print()
    print("SECTION 1: Dataset Overview")
    print("-" * 50)
    print(f"  Papers: {len(df_papers)}")
    print(f"  Columns: {list(df_papers.columns)}")
    print(f"  Year range: {df_papers['year'].min()} — {df_papers['year'].max()}")
    print(f"  Avg authors/paper: {df_papers['author_count'].mean():.1f}")
    print(f"  Avg categories/paper: {df_papers['category_count'].mean():.1f}")
    print()

    print("SECTION 2: Degree Centrality (Top Papers)")
    print("-" * 50)
    for _, row in df_centrality.head(10).iterrows():
        print(f"  {row['arxiv_id']:<30} dc={row['degree_centrality']:.4f}")
        print(f"    {row['title'][:80]}")
    print()

    print("SECTION 3: Betweenness Centrality (Bridge Papers)")
    print("-" * 50)
    for _, row in df_betweenness.head(10).iterrows():
        print(f"  {row['arxiv_id']:<30} bc={row['betweenness']:.6f}")
        print(f"    {row['title'][:80]}")
    print()

    print("SECTION 4: Category-Overlap Clusters")
    print("-" * 50)
    for cl in clusters:
        print(f"  Cluster around {cl['cluster_representative']}: {cl['size']} papers")
        for pid, title in zip(cl["papers"], cl["titles"]):
            print(f"    {pid:<30} {title}")
    print()

    print("SECTION 5: Prolific Authors")
    print("-" * 50)
    for _, row in df_prolific.iterrows():
        print(f"  {row['author']:<40} papers={row['paper_count']}")
    print()

    print("SECTION 6: Comparison with Hyper3")
    print("-" * 50)
    print("  Pandas+NX approach:")
    print("    + Simple, familiar API (DataFrames, networkx functions)")
    print("    + Fast for small-to-medium datasets (50 papers)")
    print("    + Easy to export tables / CSV / Excel")
    print("    - Bipartite graph requires manual bipartite tracking")
    print("    - Clustering is ad-hoc (author overlap), not graph-based")
    print("    - No structural anomaly detection, no spreading activation")
    print("    - No semantic relationships or inference rules")
    print("    - Each analysis is a separate function call, no integrated graph")
    print()
    print("  Hyper3 approach:")
    print("    + Unified knowledge graph: papers, authors, categories as nodes")
    print("    + Structural anomaly detection finds unusual cross-domain papers")
    print("    + Spreading activation discovers related work via graph topology")
    print("    + Community detection uses label propagation on the full graph")
    print("    + Pattern matching over typed edges (authored_by, shares_author)")
    print("    + Self-evolving graph with decay, prune, merge, reinforce")
    print("    + Built-in provenance tracking and temporal reasoning")
    print("    - Higher API surface, steeper learning curve")
    print("    - Overhead for small datasets where SQL/pandas suffices")
    print()


def main() -> None:
    papers = fetch_papers()
    if not papers:
        print("No papers retrieved from arXiv API.")
        return

    df_papers, df_authorships, df_edges = build_dataframes(papers)
    G = build_bipartite_graph(df_edges)

    df_centrality = degree_centrality_analysis(G, df_papers)
    df_betweenness = betweenness_analysis(G, df_papers)
    clusters = category_overlap_clustering(df_authorships, df_papers)
    df_prolific = prolific_author_analysis(df_authorships)

    print_report(df_papers, df_centrality, df_betweenness, clusters, df_prolific)


if __name__ == "__main__":
    main()
