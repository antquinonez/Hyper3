"""
IMDB Movie Recommendation Analysis (Pandas + NetworkX)
======================================================

Same data source and problem as the Hyper3 pipeline, solved with pandas
DataFrames and NetworkX graphs. Uses collaborative filtering with pandas
merge/groupby, builds a bipartite actor-movie graph with NetworkX, and
finds recommendations via graph-based Jaccard similarity.

Compare with: examples/projects/movie_recommendations/pipeline.py

Run with:
    .venv/bin/python examples/comparison/movie_recommendations/pandas_analysis.py
"""

from __future__ import annotations

import gzip
import tempfile
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

IMDB_DATASETS = {
    "basics": "https://datasets.imdbws.com/title.basics.tsv.gz",
    "ratings": "https://datasets.imdbws.com/title.ratings.tsv.gz",
    "principals": "https://datasets.imdbws.com/title.principals.tsv.gz",
}

DATA_DIR = Path(tempfile.gettempdir()) / "hyper3_imdb_nx"


def download_and_load(name: str, url: str) -> pd.DataFrame:
    out_path = DATA_DIR / f"{name}.tsv"
    gz_path = DATA_DIR / f"{name}.tsv.gz"
    if not out_path.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        import urllib.request
        urllib.request.urlretrieve(url, str(gz_path))
        with gzip.open(gz_path, "rb") as f_in, open(out_path, "wb") as f_out:
            f_out.write(f_in.read())
        gz_path.unlink()
    df = pd.read_csv(out_path, sep="\t", na_values="\\N", low_memory=False)
    return df


def prepare_data(
    min_votes: int = 5000,
    top_n: int = 200,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    basics = download_and_load("basics", IMDB_DATASETS["basics"])
    ratings = download_and_load("ratings", IMDB_DATASETS["ratings"])
    principals = download_and_load("principals", IMDB_DATASETS["principals"])

    movies = basics[basics["titleType"] == "movie"].copy()
    movies["startYear"] = pd.to_numeric(movies["startYear"], errors="coerce")
    movies["runtimeMinutes"] = pd.to_numeric(movies["runtimeMinutes"], errors="coerce")
    movies = movies[["tconst", "primaryTitle", "startYear", "genres", "runtimeMinutes"]]

    ratings["averageRating"] = pd.to_numeric(ratings["averageRating"], errors="coerce")
    ratings["numVotes"] = pd.to_numeric(ratings["numVotes"], errors="coerce")

    merged = movies.merge(ratings, on="tconst", how="inner")
    qualified = merged[merged["numVotes"] >= min_votes].sort_values(
        "numVotes", ascending=False
    ).head(top_n).reset_index(drop=True)

    principals = principals[principals["category"].isin(["actor", "actress", "director"])]
    principals["category"] = principals["category"].replace({"actress": "actor"})
    tconst_set = set(qualified["tconst"])
    filtered_principals = principals[principals["tconst"].isin(tconst_set)].reset_index(drop=True)

    return qualified, filtered_principals


def build_bipartite_graph(
    movies: pd.DataFrame,
    principals: pd.DataFrame,
) -> nx.Graph:
    G = nx.Graph()
    for _, row in movies.iterrows():
        title = row["primaryTitle"]
        G.add_node(
            title,
            bipartite="movie",
            imdb_id=row["tconst"],
            year=row["startYear"],
            genres=row["genres"] if pd.notna(row["genres"]) else "",
            rating=row["averageRating"] if pd.notna(row["averageRating"]) else np.nan,
            votes=row["numVotes"] if pd.notna(row["numVotes"]) else 0,
        )

    for _, row in principals.iterrows():
        person = f"person_{row['nconst']}"
        tconst = row["tconst"]
        category = row["category"]
        movie_rows = movies[movies["tconst"] == tconst]
        if movie_rows.empty:
            continue
        movie_title = movie_rows.iloc[0]["primaryTitle"]
        if not G.has_node(person):
            G.add_node(person, bipartite="person", category=category)
        edge_label = "acted_in" if category == "actor" else "directed"
        G.add_edge(person, movie_title, label=edge_label)

    return G


def collaborative_filtering(
    movies: pd.DataFrame,
    principals: pd.DataFrame,
) -> pd.DataFrame:
    person_movies = principals.groupby("nconst")["tconst"].apply(set).reset_index()
    person_movies.columns = ["nconst", "movie_set"]

    title_map = dict(zip(movies["tconst"], movies["primaryTitle"]))
    rating_map = dict(zip(movies["tconst"], movies["averageRating"]))
    genre_map = {}
    for _, row in movies.iterrows():
        if pd.notna(row["genres"]):
            genre_map[row["tconst"]] = set(str(row["genres"]).split(","))

    movie_persons = principals.groupby("tconst")["nconst"].apply(set).reset_index()
    movie_persons.columns = ["tconst", "person_set"]
    movie_persons["title"] = movie_persons["tconst"].map(title_map)

    movie_ids = list(movie_persons["tconst"])
    n = len(movie_ids)
    jaccard_matrix = np.zeros((n, n))

    person_sets = [set(movie_persons.loc[movie_persons["tconst"] == mid, "person_set"].values[0]) for mid in movie_ids]

    for i in range(n):
        for j in range(i + 1, n):
            intersection = len(person_sets[i] & person_sets[j])
            union = len(person_sets[i] | person_sets[j])
            sim = intersection / union if union > 0 else 0.0
            jaccard_matrix[i][j] = sim
            jaccard_matrix[j][i] = sim

    return movie_ids, movie_persons, jaccard_matrix, title_map, rating_map


def genre_similarity(
    movies: pd.DataFrame,
) -> tuple[list[str], np.ndarray, dict]:
    movie_data = []
    genre_set = set()
    for _, row in movies.iterrows():
        if pd.notna(row["genres"]):
            genres = set(str(row["genres"]).split(","))
        else:
            genres = set()
        genre_set.update(genres)
        movie_data.append({"tconst": row["tconst"], "title": row["primaryTitle"], "genres": genres})

    genre_list = sorted(genre_set)
    genre_idx = {g: i for i, g in enumerate(genre_list)}
    n = len(movie_data)
    matrix = np.zeros((n, len(genre_list)))

    for i, md in enumerate(movie_data):
        for g in md["genres"]:
            if g in genre_idx:
                matrix[i][genre_idx[g]] = 1.0

    from scipy.spatial.distance import cosine
    genre_sim = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i].sum() > 0 and matrix[j].sum() > 0:
                sim = 1.0 - cosine(matrix[i], matrix[j])
            else:
                sim = 0.0
            genre_sim[i][j] = sim
            genre_sim[j][i] = sim

    title_map = {md["tconst"]: md["title"] for md in movie_data}
    return [md["tconst"] for md in movie_data], genre_sim, title_map


def find_communities(G: nx.Graph) -> list[set]:
    communities = list(nx.community.label_propagation_communities(G))
    communities.sort(key=len, reverse=True)
    return communities


def graph_based_recommendations(
    G: nx.Graph,
    seed_movie: str,
    top_k: int = 15,
) -> list[dict]:
    if seed_movie not in G:
        return []

    seed_persons = set(G.neighbors(seed_movie))
    scores: dict[str, float] = {}

    for person in seed_persons:
        for movie in G.neighbors(person):
            if movie == seed_movie:
                continue
            if G.nodes[movie].get("bipartite") != "movie":
                continue
            shared = len(seed_persons & set(G.neighbors(movie)))
            total = len(seed_persons | set(G.neighbors(movie)))
            jaccard = shared / total if total > 0 else 0.0
            rating = G.nodes[movie].get("rating", 0.0)
            if np.isnan(rating):
                rating = 0.0
            scores[movie] = 0.5 * jaccard + 0.5 * (rating / 10.0)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [
        {
            "title": title,
            "score": round(score, 4),
            "rating": G.nodes[title].get("rating", 0.0),
            "year": G.nodes[title].get("year", ""),
        }
        for title, score in ranked
    ]


def compute_centrality(G: nx.Graph) -> list[dict]:
    bc = nx.betweenness_centrality(G, normalized=True)
    ranked = sorted(bc.items(), key=lambda x: x[1], reverse=True)[:20]
    return [
        {
            "node": node,
            "type": G.nodes[node].get("bipartite", "unknown"),
            "betweenness": round(score, 6),
        }
        for node, score in ranked
    ]


def main():
    print("=" * 70)
    print("SECTION 1: Data Loading")
    print("=" * 70)

    movies, principals = prepare_data(min_votes=5000, top_n=200)
    print(f"Loaded {len(movies)} movies, {len(principals)} principal entries")
    print(f"Top movie: {movies.iloc[0]['primaryTitle']} ({movies.iloc[0]['startYear']:.0f})")
    print(f"  Rating: {movies.iloc[0]['averageRating']}, Votes: {movies.iloc[0]['numVotes']:.0f}")

    print("\n" + "=" * 70)
    print("SECTION 2: Bipartite Graph Construction")
    print("=" * 70)

    G = build_bipartite_graph(movies, principals)
    movie_nodes = {n for n, d in G.nodes(data=True) if d.get("bipartite") == "movie"}
    person_nodes = {n for n, d in G.nodes(data=True) if d.get("bipartite") == "person"}
    print(f"Nodes: {G.number_of_nodes()} ({len(movie_nodes)} movies, {len(person_nodes)} persons)")
    print(f"Edges: {G.number_of_edges()}")

    print("\n" + "=" * 70)
    print("SECTION 3: Collaborative Filtering (Jaccard on shared cast)")
    print("=" * 70)

    movie_ids, movie_persons, jaccard_matrix, title_map, rating_map = collaborative_filtering(movies, principals)
    seed_idx = 0
    seed_title = title_map[movie_ids[seed_idx]]
    similarities = jaccard_matrix[seed_idx]
    top_indices = np.argsort(similarities)[::-1][1:11]
    print(f"Movies most similar to '{seed_title}' by shared cast:")
    for idx in top_indices:
        mid = movie_ids[idx]
        print(f"  {title_map[mid]:45s} | jaccard={similarities[idx]:.4f} | rating={rating_map.get(mid, 'N/A')}")

    print("\n" + "=" * 70)
    print("SECTION 4: Genre-Based Similarity")
    print("=" * 70)

    genre_ids, genre_sim, genre_title_map = genre_similarity(movies)
    seed_genre_idx = 0
    seed_genre_title = genre_title_map[genre_ids[seed_genre_idx]]
    genre_scores = genre_sim[seed_genre_idx]
    top_genre_idx = np.argsort(genre_scores)[::-1][1:11]
    print(f"Movies most similar to '{seed_genre_title}' by genre overlap:")
    for idx in top_genre_idx:
        if genre_scores[idx] > 0:
            print(f"  {genre_title_map[genre_ids[idx]]:45s} | cosine_sim={genre_scores[idx]:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: Graph-Based Recommendations")
    print("=" * 70)

    seed_movie = movies.iloc[0]["primaryTitle"]
    recs = graph_based_recommendations(G, seed_movie, top_k=15)
    print(f"Recommendations for '{seed_movie}':")
    for r in recs:
        print(f"  {r['title']:45s} | score={r['score']:.4f} | rating={r['rating']} | year={r['year']}")

    print("\n" + "=" * 70)
    print("SECTION 6: Community Detection")
    print("=" * 70)

    communities = find_communities(G)
    print(f"Found {len(communities)} communities")
    for i, comm in enumerate(communities[:5]):
        comm_movies = [n for n in comm if G.nodes[n].get("bipartite") == "movie"]
        comm_persons = [n for n in comm if G.nodes[n].get("bipartite") == "person"]
        sample = comm_movies[:3] if comm_movies else list(comm)[:3]
        print(f"  Community {i}: {len(comm)} nodes ({len(comm_movies)} movies, {len(comm_persons)} persons) | e.g. {', '.join(sample)}")

    print("\n" + "=" * 70)
    print("SECTION 7: Betweenness Centrality")
    print("=" * 70)

    centrality = compute_centrality(G)
    print("Top connector nodes:")
    for c in centrality[:10]:
        print(f"  {c['node']:45s} | type={c['type']:10s} | bc={c['betweenness']:.6f}")

    print("\n" + "=" * 70)
    print("COMPARISON WITH HYPER3 APPROACH")
    print("=" * 70)
    print("""
Pandas + NetworkX approach:
  - Collaborative filtering via Jaccard similarity on shared cast/crew
  - Genre cosine similarity via one-hot encoding and scipy
  - Bipartite graph with manual neighbor traversal for recommendations
  - Community detection via label propagation (with modularity)
  - Betweenness centrality via nx.betweenness_centrality()

Hyper3 approach (see pipeline.py):
  - Knowledge graph with typed nodes (movie, person, genre) and labeled edges
  - TransitiveRule for multi-hop genre chain discovery
  - SpreadingActivation for associative recall from seed movies
  - RetrievalEngine with RRF combining activation + embedding similarity
  - CommunityDetector with label propagation and modularity scoring
  - Built-in betweenness_centrality with weight inversion
  - Provenance tracking, overlay commit/rollback, and self-evolving graph
""")


if __name__ == "__main__":
    main()
