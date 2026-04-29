"""
IMDB Movie Recommendation Graph Pipeline
import os
os.environ.setdefault("PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW", "ignore")
=========================================

A Prefect 2.x pipeline that downloads public IMDB datasets, builds a Hyper3
knowledge graph of movies/people/genres, and runs recommendation analysis
using spreading activation, retrieval, community detection, and centrality.

Data sources (public, no API key required):
    - https://datasets.imdbws.com/title.basics.tsv.gz
    - https://datasets.imdbws.com/title.ratings.tsv.gz
    - https://datasets.imdbws.com/title.principals.tsv.gz

Run with:
    .venv/bin/python examples/projects/movie_recommendations/pipeline.py
"""

from __future__ import annotations
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import gzip
import tempfile
from pathlib import Path

import pandas as pd
from prefect import flow, task
from hyper3 import HypergraphMemory, TransitiveRule, top_k


IMDB_DATASETS = {
    "basics": "https://datasets.imdbws.com/title.basics.tsv.gz",
    "ratings": "https://datasets.imdbws.com/title.ratings.tsv.gz",
    "principals": "https://datasets.imdbws.com/title.principals.tsv.gz",
}

DATA_DIR = Path(tempfile.gettempdir()) / "hyper3_imdb"


@task(retries=2, retry_delay_seconds=30)
def download_dataset(name: str, url: str) -> Path:
    logger = logging.getLogger(__name__)
    out_path = DATA_DIR / f"{name}.tsv"
    gz_path = DATA_DIR / f"{name}.tsv.gz"
    if out_path.exists():
        logger.info("Using cached %s", out_path)
        return out_path
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s from %s", name, url)
    import urllib.request
    urllib.request.urlretrieve(url, str(gz_path))
    logger.info("Decompressing %s", gz_path)
    with gzip.open(gz_path, "rb") as f_in, open(out_path, "wb") as f_out:
        f_out.write(f_in.read())
    gz_path.unlink()
    logger.info("Saved %s (%d bytes)", out_path, out_path.stat().st_size)
    return out_path


@task
def load_basics(path: Path) -> pd.DataFrame:
    logger = logging.getLogger(__name__)
    logger.info("Loading basics from %s", path)
    df = pd.read_csv(path, sep="\t", na_values="\\N", dtype=str, low_memory=False)
    movies = df[df["titleType"] == "movie"].copy()
    movies["startYear"] = pd.to_numeric(movies["startYear"], errors="coerce")
    movies["runtimeMinutes"] = pd.to_numeric(movies["runtimeMinutes"], errors="coerce")
    logger.info("Filtered to %d movies", len(movies))
    return movies[["tconst", "primaryTitle", "startYear", "genres", "runtimeMinutes"]]


@task
def load_ratings(path: Path) -> pd.DataFrame:
    logger = logging.getLogger(__name__)
    logger.info("Loading ratings from %s", path)
    df = pd.read_csv(path, sep="\t", na_values="\\N")
    df["averageRating"] = pd.to_numeric(df["averageRating"], errors="coerce")
    df["numVotes"] = pd.to_numeric(df["numVotes"], errors="coerce")
    logger.info("Loaded %d ratings", len(df))
    return df


@task
def load_principals(path: Path) -> pd.DataFrame:
    logger = logging.getLogger(__name__)
    logger.info("Loading principals from %s", path)
    df = pd.read_csv(path, sep="\t", na_values="\\N", dtype=str, low_memory=False)
    df = df[df["category"].isin(["actor", "actress", "director"])]
    df["category"] = df["category"].replace({"actress": "actor"})
    logger.info("Filtered to %d principal entries", len(df))
    return df[["tconst", "nconst", "category"]]


@task
def select_top_movies(
    basics: pd.DataFrame,
    ratings: pd.DataFrame,
    principals: pd.DataFrame,
    min_votes: int = 5000,
    top_n: int = 200,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger = logging.getLogger(__name__)
    merged = basics.merge(ratings, on="tconst", how="inner")
    qualified = merged[merged["numVotes"] >= min_votes].copy()
    qualified = qualified.sort_values("numVotes", ascending=False).head(top_n)
    tconst_set = set(qualified["tconst"])
    filtered_principals = principals[principals["tconst"].isin(tconst_set)]
    logger.info(
        "Selected %d movies with >=%d votes, %d principal entries",
        len(qualified), min_votes, len(filtered_principals),
    )
    return qualified.reset_index(drop=True), filtered_principals.reset_index(drop=True)


@task
def build_knowledge_graph(
    movies: pd.DataFrame,
    principals: pd.DataFrame,
) -> HypergraphMemory:
    logger = logging.getLogger(__name__)
    mem = HypergraphMemory(evolve_interval=0)

    person_names: dict[str, str] = {}
    for _, row in principals.iterrows():
        pid = row["nconst"]
        if pid not in person_names:
            person_names[pid] = pid

    for _, row in movies.iterrows():
        title = row["primaryTitle"]
        year = row["startYear"]
        genres_str = row["genres"]
        genres = []
        if pd.notna(genres_str):
            genres = [g.strip() for g in str(genres_str).split(",") if g.strip()]

        mem.store(title, data={
            "type": "movie",
            "imdb_id": row["tconst"],
            "year": int(year) if pd.notna(year) else None,
            "genres": genres,
            "rating": float(row["averageRating"]) if pd.notna(row["averageRating"]) else None,
            "votes": int(row["numVotes"]) if pd.notna(row["numVotes"]) else None,
            "runtime": int(row["runtimeMinutes"]) if pd.notna(row["runtimeMinutes"]) else None,
        })

        for genre in genres:
            mem.ensure(genre, data={"type": "genre"})
            if mem.has_node(title) and mem.has_node(genre):
                rating = row["averageRating"]
                w = float(rating) / 10.0 if pd.notna(rating) else 1.0
                mem.relate(title, genre, label="has_genre", weight=w)

    movie_titles = set(movies["primaryTitle"])
    for _, row in principals.iterrows():
        pid = row["nconst"]
        category = row["category"]
        tconst = row["tconst"]
        movie_rows = movies[movies["tconst"] == tconst]
        if movie_rows.empty:
            continue
        movie_title = movie_rows.iloc[0]["primaryTitle"]
        person_label = f"person_{pid}"

        mem.ensure(person_label, data={"type": "person", "category": category})

        edge_label = "acted_in" if category == "actor" else "directed"
        if mem.has_node(person_label) and mem.has_node(movie_title):
            mem.relate(person_label, movie_title, label=edge_label)

    rating_bins = [(0, 5.0), (5.0, 6.5), (6.5, 7.5), (7.5, 8.5), (8.5, 10.1)]
    bin_labels = ["low_rated", "below_avg", "above_avg", "well_rated", "top_rated"]
    bin_members: dict[str, list[str]] = {bl: [] for bl in bin_labels}

    for _, row in movies.iterrows():
        rating = row["averageRating"]
        if pd.isna(rating):
            continue
        title = row["primaryTitle"]
        for (lo, hi), bl in zip(rating_bins, bin_labels):
            if lo <= rating < hi:
                bin_members[bl].append(title)
                break

    for bl, titles in bin_members.items():
        for i in range(len(titles)):
            for j in range(i + 1, min(i + 5, len(titles))):
                if mem.has_node(titles[i]) and mem.has_node(titles[j]):
                    mem.relate(titles[i], titles[j], label="similar_rating", bidirectional=True)

    logger.info(
        "Built graph: %d nodes, %d edges",
        mem.graph.node_count, mem.graph.edge_count,
    )
    return mem


@task
def analyze_genre_chains(mem: HypergraphMemory) -> list[dict]:
    logger = logging.getLogger(__name__)
    logger.info("Running TransitiveRule on has_genre edges")
    mem.add_rules(TransitiveRule(edge_label="has_genre", new_label="has_genre"))
    result = mem.reason(
        seed_concepts=set(),
        max_depth=2,
        exhaustive=True,
    )
    inferred = result.expansion.edges_produced if result.expansion else 0
    logger.info("Genre chain reasoning: %d new edges", inferred)
    matches = mem.pattern_match(edge_label="has_genre")
    movie_set = set(mem.query_nodes(type="movie"))
    genre_set = set(mem.query_nodes(type="genre"))
    genre_associations = []
    for m in matches:
        if len(m.source_labels) > 0 and len(m.target_labels) > 0:
            src = m.source_labels[0]
            tgt = m.target_labels[0]
            if src in movie_set and tgt in genre_set:
                genre_associations.append({"movie": src, "genre": tgt})
    logger.info("Found %d movie-genre associations", len(genre_associations))
    return genre_associations[:20]


@task
def analyze_actor_genre_associations(mem: HypergraphMemory) -> list[dict]:
    logger = logging.getLogger(__name__)
    acted_edges = mem.pattern_match(edge_label="acted_in")
    genre_edges = mem.pattern_match(edge_label="has_genre")
    actor_movies: dict[str, list[str]] = {}
    for e in acted_edges:
        if e.source_labels and e.target_labels:
            actor = e.source_labels[0]
            movie = e.target_labels[0]
            actor_movies.setdefault(actor, []).append(movie)
    movie_genres: dict[str, list[str]] = {}
    for e in genre_edges:
        if e.source_labels and e.target_labels:
            movie = e.source_labels[0]
            genre = e.target_labels[0]
            movie_genres.setdefault(movie, []).append(genre)
    actor_genre_freq: dict[str, dict[str, int]] = {}
    for actor, movies in actor_movies.items():
        genre_counts: dict[str, int] = {}
        for movie in movies:
            for genre in movie_genres.get(movie, []):
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        actor_genre_freq[actor] = genre_counts
    results = []
    for actor, genres in sorted(
        actor_genre_freq.items(), key=lambda x: sum(x[1].values()), reverse=True
    ):
        total = sum(genres.values())
        top_genre = max(genres, key=lambda g: genres[g])
        results.append({
            "person": actor,
            "total_roles": total,
            "top_genre": top_genre,
            "genre_count": top_genre,
            "genre_diversity": len(genres),
        })
    logger.info("Profiled %d actors by genre", len(results))
    return results[:15]


@task
def analyze_spreading_activation(mem: HypergraphMemory, movies_df: pd.DataFrame) -> list[dict]:
    logger = logging.getLogger(__name__)
    seed_movie = movies_df.iloc[0]["primaryTitle"]
    logger.info("Running spreading activation from '%s'", seed_movie)
    activated = mem.activate(seed_movie, energy=1.0, top_k=15, iterations=4)
    movie_labels = set(mem.query_nodes(type="movie"))
    genre_labels = set(mem.query_nodes(type="genre"))
    results = []
    for ar in activated:
        node_type = "movie" if ar.label in movie_labels else ("genre" if ar.label in genre_labels else "person")
        results.append({
            "label": ar.label,
            "type": node_type,
            "activation": round(ar.activation, 4),
            "depth": ar.depth,
        })
    logger.info("Activated %d nodes from '%s'", len(results), seed_movie)
    return results


@task
def analyze_retrieval(mem: HypergraphMemory, movies_df: pd.DataFrame) -> list[dict]:
    logger = logging.getLogger(__name__)
    seed_movie = movies_df.iloc[0]["primaryTitle"]
    logger.info("Running retrieval for '%s'", seed_movie)
    results = mem.retrieve(seed_movie, top_k=15, iterations=4)
    movie_labels = set(mem.query_nodes(type="movie"))
    genre_labels = set(mem.query_nodes(type="genre"))
    output = []
    for r in results:
        node_type = "movie" if r.label in movie_labels else ("genre" if r.label in genre_labels else "person")
        output.append({
            "label": r.label,
            "type": node_type,
            "rrf_score": round(r.rrf_score, 4),
            "activation": round(r.activation, 4),
            "similarity": round(r.similarity, 4),
        })
    logger.info("Retrieved %d results for '%s'", len(output), seed_movie)
    return output


@task
def analyze_communities(mem: HypergraphMemory) -> dict:
    logger = logging.getLogger(__name__)
    logger.info("Running community detection")
    result = mem.detect_communities(seed=42)
    communities_info = []
    movie_set = set(mem.query_nodes(type="movie"))
    for c in sorted(result.communities, key=lambda x: x.size, reverse=True)[:10]:
        movie_labels = [lbl for lbl in c.member_labels if lbl in movie_set]
        communities_info.append({
            "id": c.community_id,
            "size": c.size,
            "movies": movie_labels[:5],
            "internal_edges": c.internal_edges,
            "external_edges": c.external_edges,
        })
    logger.info(
        "Found %d communities, modularity=%.3f",
        result.community_count, result.modularity,
    )
    return {
        "community_count": result.community_count,
        "modularity": round(result.modularity, 4),
        "coverage": round(result.coverage, 4),
        "largest_community_size": result.largest_community_size,
        "top_communities": communities_info,
    }


@task
def analyze_centrality(mem: HypergraphMemory) -> list[dict]:
    logger = logging.getLogger(__name__)
    logger.info("Computing betweenness centrality")
    bc = mem.betweenness_centrality(top_k=20)
    movie_labels = set(mem.query_nodes(type="movie"))
    genre_labels = set(mem.query_nodes(type="genre"))
    results = []
    for label, score in bc.items():
        node_type = "movie" if label in movie_labels else ("genre" if label in genre_labels else "person")
        results.append({
            "label": label,
            "type": node_type,
            "betweenness": round(score, 6),
        })
    logger.info("Top connector: %s", results[0]["label"] if results else "none")
    return results


@task
def print_results(
    movies_df: pd.DataFrame,
    genre_associations: list[dict],
    actor_profiles: list[dict],
    activation_results: list[dict],
    retrieval_results: list[dict],
    community_info: dict,
    centrality_results: list[dict],
) -> None:
    seed_movie = movies_df.iloc[0]["primaryTitle"]

    print("\n" + "=" * 70)
    print("IMDB MOVIE RECOMMENDATION GRAPH - RESULTS")
    print("=" * 70)

    print(f"\nGraph: {movies_df.shape[0]} movies loaded")
    print(f"Top movie by votes: {seed_movie}")
    print(f"  Rating: {movies_df.iloc[0]['averageRating']}")
    print(f"  Votes: {movies_df.iloc[0]['numVotes']}")
    print(f"  Genres: {movies_df.iloc[0]['genres']}")

    print("\n" + "-" * 70)
    print("GENRE CHAINS (TransitiveRule)")
    print("-" * 70)
    for assoc in genre_associations[:10]:
        print(f"  {assoc['movie']:40s} -> {assoc['genre']}")

    print("\n" + "-" * 70)
    print("ACTOR-GENRE PROFILES")
    print("-" * 70)
    for p in actor_profiles[:10]:
        print(f"  {p['person']:25s} | {p['total_roles']:2d} roles | top: {p['top_genre']} | diversity: {p['genre_diversity']}")

    print("\n" + "-" * 70)
    print(f"SPREADING ACTIVATION FROM '{seed_movie}'")
    print("-" * 70)
    for r in activation_results[:15]:
        print(f"  {r['label']:40s} | type={r['type']:10s} | act={r['activation']:.4f} | depth={r['depth']}")

    print("\n" + "-" * 70)
    print(f"RETRIEVAL RESULTS FOR '{seed_movie}'")
    print("-" * 70)
    for r in retrieval_results[:15]:
        print(f"  {r['label']:40s} | type={r['type']:10s} | rrf={r['rrf_score']:.4f} | act={r['activation']:.4f} | sim={r['similarity']:.4f}")

    print("\n" + "-" * 70)
    print("COMMUNITY DETECTION")
    print("-" * 70)
    print(f"  Communities: {community_info['community_count']}")
    print(f"  Modularity:  {community_info['modularity']:.4f}")
    print(f"  Coverage:    {community_info['coverage']:.4f}")
    print(f"  Largest:     {community_info['largest_community_size']} nodes")
    for c in community_info["top_communities"][:5]:
        movies_str = ", ".join(c["movies"][:3])
        print(f"  Community {c['id']:3d} | size={c['size']:3d} | int={c['internal_edges']} ext={c['external_edges']} | {movies_str}")

    print("\n" + "-" * 70)
    print("BETWEENNESS CENTRALITY (TOP CONNECTOR NODES)")
    print("-" * 70)
    for r in centrality_results[:10]:
        print(f"  {r['label']:40s} | type={r['type']:10s} | bc={r['betweenness']:.6f}")

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


@flow(name="IMDB Movie Recommendation Graph")
def imdb_movie_recommendation_pipeline(
    min_votes: int = 5000,
    top_n: int = 200,
) -> HypergraphMemory:
    basics_path = download_dataset("basics", IMDB_DATASETS["basics"])
    ratings_path = download_dataset("ratings", IMDB_DATASETS["ratings"])
    principals_path = download_dataset("principals", IMDB_DATASETS["principals"])

    basics_df = load_basics(basics_path)
    ratings_df = load_ratings(ratings_path)
    principals_df = load_principals(principals_path)

    movies_df, filtered_principals = select_top_movies(
        basics_df, ratings_df, principals_df,
        min_votes=min_votes, top_n=top_n,
    )

    mem = build_knowledge_graph(movies_df, filtered_principals)

    genre_associations = analyze_genre_chains(mem)
    actor_profiles = analyze_actor_genre_associations(mem)
    activation_results = analyze_spreading_activation(mem, movies_df)
    retrieval_results = analyze_retrieval(mem, movies_df)
    community_info = analyze_communities(mem)
    centrality_results = analyze_centrality(mem)

    print_results(
        movies_df, genre_associations, actor_profiles,
        activation_results, retrieval_results,
        community_info, centrality_results,
    )

    return mem


def main(min_votes: int = 5000, top_n: int = 200) -> None:
    basics_path = download_dataset.fn("basics", IMDB_DATASETS["basics"])
    ratings_path = download_dataset.fn("ratings", IMDB_DATASETS["ratings"])
    principals_path = download_dataset.fn("principals", IMDB_DATASETS["principals"])
    basics_df = load_basics.fn(basics_path)
    ratings_df = load_ratings.fn(ratings_path)
    principals_df = load_principals.fn(principals_path)
    movies_df, filtered_principals = select_top_movies.fn(
        basics_df, ratings_df, principals_df,
        min_votes=min_votes, top_n=top_n,
    )
    mem = build_knowledge_graph.fn(movies_df, filtered_principals)
    genre_associations = analyze_genre_chains.fn(mem)
    actor_profiles = analyze_actor_genre_associations.fn(mem)
    activation_results = analyze_spreading_activation.fn(mem, movies_df)
    retrieval_results = analyze_retrieval.fn(mem, movies_df)
    community_info = analyze_communities.fn(mem)
    centrality_results = analyze_centrality.fn(mem)
    print_results(
        movies_df, genre_associations, actor_profiles,
        activation_results, retrieval_results,
        community_info, centrality_results,
    )


if __name__ == "__main__":
    main()
