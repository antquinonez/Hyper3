"""
Movie Recommendation via Knowledge Graph Analysis
==================================================

Builds a synthetic movie knowledge graph (~100 movies, 25 directors, 40 actors,
10 studios, 12 genres) and demonstrates graph-based recommendation strategies
using spreading activation, retrieval, community detection, centrality, and
structural pattern matching.

Run with:
    .venv/bin/python examples/projects/movie_recommendations/pipeline.py
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass

from hyper3 import HypergraphMemory


@dataclass
class MovieData:
    title: str
    year: int
    rating: float
    genres: list[str]
    director: str
    actors: list[str]
    studio: str


GENRES = [
    "Action", "Comedy", "Drama", "Thriller", "Sci-Fi", "Horror",
    "Romance", "Animation", "Documentary", "Mystery", "Fantasy", "Adventure",
]

DIRECTORS = [
    "Elena Vasquez", "Marcus Chen", "Ingrid Holm", "Rafael Torres",
    "Yuki Tanaka", "Omar Khalil", "Sofia Petrov", "Liam Calloway",
    "Priya Sharma", "Henrik Strand", "Camille Dubois", "Jin-Soo Park",
    "Natasha Volkov", "Diego Ramirez", "Anika Bauer", "Tomás Faria",
    "Mei-Ling Wu", "Sebastian Roth", "Amara Okafor", "Leo Bergström",
    "Fatima Al-Rashid", "Giovanni Costa", "Hana Kimura", "André Lefèvre",
    "Rowan Walsh",
]

ACTORS = [
    "Kai Nakamura", "Zara Okonkwo", "Felix Lindqvist", "Mia Serrano",
    "Adrian Voss", "Luna Petrova", "Soren Haugen", "Ava Chen",
    "Mateo Rivera", "Isla McKinnon", "Idris Mensah", "Freya Andersen",
    "Rafael Monteiro", "Celine Moreau", "Dax Holloway", "Yuki Ishida",
    "Nadia Kowalski", "Theo Papadopoulos", "Aaliya Hassan", "Leif Erikson",
    "Valentina Ruiz", "Owen Tierney", "Sakura Hayashi", "Emeka Obi",
    "Clara Whitfield", "Joaquin Vega", "Ingrid Nyström", "Dante Moretti",
    "Sienna Ashford", "Arjun Mehta", "Elsa Magnusson", "Cruz Delgado",
    "Talia Nazari", "Finnegan O'Reilly", "Rosa Ferreira", "Kenji Mori",
    "Elise Beaumont", "Nico Alvarez", "Priya Desai", "Hugo Lagerkvist",
]

STUDIOS = [
    "Meridian Pictures", "Ironclad Films", "Lumina Studios",
    "Northlight Cinema", "Ember Entertainment", "Atlas Film Group",
    "Silverleaf Productions", "Crestline Media", "Obsidian Pictures",
    "Verdant Releasing",
]

GENRE_PAIRS = [
    ("Action", "Adventure"), ("Action", "Thriller"), ("Action", "Sci-Fi"),
    ("Comedy", "Romance"), ("Comedy", "Drama"), ("Comedy", "Adventure"),
    ("Drama", "Romance"), ("Drama", "Thriller"), ("Drama", "Mystery"),
    ("Sci-Fi", "Thriller"), ("Sci-Fi", "Action"), ("Sci-Fi", "Adventure"),
    ("Horror", "Thriller"), ("Horror", "Mystery"),
    ("Romance", "Comedy"), ("Romance", "Drama"),
    ("Animation", "Adventure"), ("Animation", "Fantasy"), ("Animation", "Comedy"),
    ("Documentary", "Drama"),
    ("Mystery", "Thriller"), ("Mystery", "Drama"),
    ("Fantasy", "Adventure"), ("Fantasy", "Action"),
    ("Adventure", "Action"), ("Adventure", "Sci-Fi"),
]

MOVIE_TITLES = [
    ("The Last Meridian", 2023, 7.8, "Action", "Adventure"),
    ("Echoes of Nowhere", 2019, 8.2, "Drama", "Mystery"),
    ("Neon Divide", 2021, 7.4, "Sci-Fi", "Thriller"),
    ("Wandering Hearts", 2020, 6.9, "Comedy", "Romance"),
    ("Beneath the Surface", 2022, 7.1, "Horror", "Thriller"),
    ("Quantum Drift", 2024, 8.0, "Sci-Fi", "Action"),
    ("The Painter's Daughter", 2018, 8.4, "Drama", "Romance"),
    ("Steel City Blues", 2017, 7.3, "Drama", "Thriller"),
    ("Midnight Lantern", 2023, 7.6, "Mystery", "Thriller"),
    ("Frozen Horizon", 2021, 6.5, "Adventure", "Sci-Fi"),
    ("The Garden of Lies", 2020, 7.9, "Drama", "Mystery"),
    ("Laughing at Gravity", 2019, 7.0, "Comedy", "Adventure"),
    ("Phantom Frequency", 2022, 7.5, "Horror", "Sci-Fi"),
    ("Inception 2", 2024, 8.6, "Sci-Fi", "Action"),
    ("Letters from Havana", 2018, 7.7, "Drama", "Romance"),
    ("The Crimson Protocol", 2023, 7.2, "Action", "Thriller"),
    ("Whispered Secrets", 2021, 6.8, "Mystery", "Drama"),
    ("Skyward Bound", 2020, 8.1, "Animation", "Adventure"),
    ("The Reckoning Hour", 2019, 7.4, "Thriller", "Drama"),
    ("Fractured Light", 2022, 7.8, "Sci-Fi", "Mystery"),
    ("Summer in Lisbon", 2023, 6.7, "Romance", "Comedy"),
    ("The Obsidian Gate", 2021, 7.9, "Fantasy", "Adventure"),
    ("Rogue Element", 2024, 7.3, "Action", "Sci-Fi"),
    ("Still Waters", 2017, 8.3, "Drama", "Thriller"),
    ("The Fox and the Storm", 2020, 8.0, "Animation", "Fantasy"),
    ("Deadlight", 2022, 6.4, "Horror", "Mystery"),
    ("Chasing the Sun", 2019, 7.1, "Adventure", "Drama"),
    ("The Berlin Conundrum", 2023, 7.7, "Thriller", "Mystery"),
    ("Love in the Algorithm", 2024, 6.6, "Comedy", "Romance"),
    ("Ember Rising", 2021, 7.5, "Fantasy", "Action"),
    ("The Cartographer", 2018, 8.1, "Adventure", "Mystery"),
    ("Glass Houses", 2020, 7.0, "Thriller", "Drama"),
    ("Parallel Worlds", 2022, 7.8, "Sci-Fi", "Romance"),
    ("The Silent Witness", 2019, 7.6, "Mystery", "Thriller"),
    ("Wildflower", 2023, 7.2, "Drama", "Romance"),
    ("Nova Strike", 2024, 7.4, "Action", "Sci-Fi"),
    ("The Depth of Blue", 2017, 7.9, "Documentary", "Drama"),
    ("Carnival of Shadows", 2021, 6.9, "Horror", "Fantasy"),
    ("Second Chances", 2020, 7.3, "Comedy", "Drama"),
    ("The Iron Veil", 2023, 7.7, "Action", "Thriller"),
    ("Starfall", 2022, 8.2, "Sci-Fi", "Adventure"),
    ("The Understudy", 2018, 7.1, "Comedy", "Drama"),
    ("Haunted Requiem", 2019, 6.3, "Horror", "Drama"),
    ("The Silver Lining", 2024, 7.5, "Comedy", "Romance"),
    ("Frostfire", 2021, 7.6, "Fantasy", "Adventure"),
    ("The Informant's Dilemma", 2020, 7.8, "Thriller", "Drama"),
    ("Beyond the Veil", 2023, 7.0, "Sci-Fi", "Mystery"),
    ("The Long Road Home", 2019, 8.0, "Drama", "Adventure"),
    ("Clockwork Dreams", 2022, 7.4, "Animation", "Sci-Fi"),
    ("Desert Rose", 2021, 7.2, "Romance", "Drama"),
    ("The Sentinel's Oath", 2024, 7.6, "Fantasy", "Action"),
    ("Broken Compass", 2018, 6.8, "Adventure", "Comedy"),
    ("Nightfall Protocol", 2023, 7.3, "Thriller", "Sci-Fi"),
    ("The Last Waltz", 2020, 7.9, "Drama", "Romance"),
    ("Rise of the Ancients", 2022, 7.1, "Fantasy", "Action"),
    ("Crossing Mhor", 2019, 7.5, "Adventure", "Drama"),
    ("Signal Lost", 2024, 7.0, "Sci-Fi", "Thriller"),
    ("The Vinyl Years", 2017, 8.1, "Comedy", "Drama"),
    ("Shadowlight", 2021, 6.7, "Horror", "Thriller"),
    ("Tidal Force", 2023, 7.8, "Action", "Adventure"),
    ("A Map of Scars", 2020, 7.4, "Documentary", "Drama"),
    ("Inferno Gate", 2022, 7.2, "Action", "Fantasy"),
    ("The Orchid Thief", 2018, 7.6, "Mystery", "Thriller"),
    ("When Stars Align", 2024, 7.3, "Romance", "Comedy"),
    ("Zero Gravity", 2021, 7.7, "Sci-Fi", "Adventure"),
    ("The Confession", 2019, 7.5, "Drama", "Thriller"),
    ("Lucky Break", 2023, 6.5, "Comedy", "Adventure"),
    ("Emerald Kingdom", 2020, 7.8, "Animation", "Fantasy"),
    ("The Desperate Hour", 2022, 7.0, "Thriller", "Action"),
    ("Voices in the Fog", 2018, 7.4, "Mystery", "Horror"),
    ("Turning Point", 2024, 7.6, "Drama", "Romance"),
    ("Circuit Breaker", 2021, 7.3, "Sci-Fi", "Action"),
    ("The Heiress", 2023, 7.1, "Drama", "Mystery"),
    ("Gone Tomorrow", 2020, 7.5, "Action", "Thriller"),
    ("The Beekeeper's Song", 2019, 7.9, "Drama", "Romance"),
    ("Spirit Walker", 2022, 7.2, "Fantasy", "Adventure"),
    ("Deadly Calculus", 2024, 7.4, "Thriller", "Mystery"),
    ("The Morning After", 2018, 6.6, "Comedy", "Romance"),
    ("Abyss", 2021, 7.0, "Horror", "Sci-Fi"),
    ("The Forgotten War", 2023, 8.0, "Documentary", "Drama"),
    ("Crown of Embers", 2020, 7.7, "Fantasy", "Action"),
    ("Under the Neon", 2019, 7.3, "Thriller", "Drama"),
    ("Starlight Express", 2024, 7.5, "Animation", "Adventure"),
    ("The Betrayal", 2022, 7.6, "Drama", "Thriller"),
    ("Misfit Patrol", 2021, 6.8, "Comedy", "Action"),
    ("Ripples", 2023, 7.8, "Drama", "Romance"),
    ("The Black Archive", 2018, 7.4, "Mystery", "Sci-Fi"),
    ("Iron Resolve", 2020, 7.1, "Action", "Drama"),
    ("Wanderlust", 2024, 7.0, "Adventure", "Comedy"),
    ("The Hollow Crown", 2019, 7.9, "Drama", "Fantasy"),
    ("Frequency Shift", 2022, 7.2, "Sci-Fi", "Thriller"),
    ("Painted Faces", 2021, 7.6, "Drama", "Mystery"),
    ("Sunstorm", 2023, 7.3, "Action", "Sci-Fi"),
    ("The Quiet Type", 2020, 7.5, "Comedy", "Drama"),
    ("Mortal Coil", 2018, 6.9, "Horror", "Action"),
    ("Driftwood", 2024, 7.7, "Romance", "Drama"),
    ("The Architect's Eye", 2021, 7.4, "Documentary", "Mystery"),
    ("Sunderland Heights", 2019, 7.1, "Drama", "Thriller"),
]


def generate_movies(seed: int = 42) -> list[MovieData]:
    rng = random.Random(seed)
    movies: list[MovieData] = []
    director_pool = list(DIRECTORS)
    actor_pool = list(ACTORS)
    studio_pool = list(STUDIOS)
    director_assignments: dict[str, list[str]] = defaultdict(list)
    for title, year, rating, g1, g2 in MOVIE_TITLES:
        director = rng.choice(director_pool)
        director_assignments[director].append(title)
        n_actors = rng.randint(3, 6)
        actors = rng.sample(actor_pool, n_actors)
        studio = rng.choice(studio_pool)
        movies.append(MovieData(
            title=title, year=year, rating=rating,
            genres=[g1, g2], director=director,
            actors=actors, studio=studio,
        ))
    while len(movies) < 100:
        idx = len(movies)
        g1, g2 = GENRE_PAIRS[idx % len(GENRE_PAIRS)]
        title = f"Untitled Project {idx + 1}"
        year = rng.randint(2015, 2024)
        rating = round(rng.gauss(7.0, 1.2), 1)
        rating = max(1.0, min(10.0, rating))
        director = rng.choice(director_pool)
        actors = rng.sample(actor_pool, rng.randint(3, 6))
        studio = rng.choice(studio_pool)
        movies.append(MovieData(
            title=title, year=year, rating=rating,
            genres=[g1, g2], director=director,
            actors=actors, studio=studio,
        ))
    return movies


def build_graph(movies: list[MovieData]) -> HypergraphMemory:
    mem = HypergraphMemory(evolve_interval=0)
    for genre in GENRES:
        mem.ensure(genre, data={"type": "genre"})
    for director in DIRECTORS:
        mem.ensure(director, data={"type": "director"})
    for actor in ACTORS:
        mem.ensure(actor, data={"type": "actor"})
    for studio in STUDIOS:
        mem.ensure(studio, data={"type": "studio"})
    for m in movies:
        mem.add(m.title, data={"type": "movie", "year": m.year, "rating": m.rating})
        for genre in m.genres:
            w = m.rating / 10.0
            mem.link(m.title, genre, label="has_genre", weight=w)
        mem.link(m.title, m.director, label="directed_by")
        for actor in m.actors:
            mem.link(actor, m.title, label="acted_in")
        mem.link(m.title, m.studio, label="produced_by")
    actor_movies: dict[str, list[str]] = defaultdict(list)
    for m in movies:
        for actor in m.actors:
            actor_movies[actor].append(m.title)
    movie_titles_set = {m.title for m in movies}
    actor_list = list(actor_movies.keys())
    for i in range(len(actor_list)):
        for j in range(i + 1, len(actor_list)):
            shared = set(actor_movies[actor_list[i]]) & set(actor_movies[actor_list[j]])
            shared_movie_list = sorted(shared)
            for k in range(len(shared_movie_list)):
                for l in range(k + 1, len(shared_movie_list)):
                    a_title = shared_movie_list[k]
                    b_title = shared_movie_list[l]
                    if a_title in movie_titles_set and b_title in movie_titles_set:
                        mem.link(a_title, b_title, label="similar_taste",
                                   weight=float(len(shared)), bidirectional=True)
    return mem


def section1_construction(mem: HypergraphMemory, movies: list[MovieData]) -> None:
    print("=" * 70)
    print("SECTION 1: KNOWLEDGE GRAPH CONSTRUCTION")
    print("=" * 70)
    print(f"\nNodes:  {mem.size[0]}")
    print(f"Edges:  {mem.size[1]}")
    genre_counts: dict[str, int] = Counter()
    for m in movies:
        for g in m.genres:
            genre_counts[g] += 1
    print(f"\nGenre distribution ({len(genre_counts)} genres):")
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
        print(f"  {genre:15s} {count:3d} movies")
    top_rated = sorted(movies, key=lambda m: -m.rating)[:5]
    print(f"\nTop-5 rated movies:")
    for m in top_rated:
        print(f"  {m.title:35s}  {m.rating:.1f}  {m.year}  [{', '.join(m.genres)}]")
    print()


def section2_genre_recommendation(mem: HypergraphMemory, movies: list[MovieData]) -> None:
    print("=" * 70)
    print("SECTION 2: GENRE-BASED RECOMMENDATION VIA ACTIVATION")
    print("=" * 70)
    seed_movie = "Inception 2"
    print(f"\nSeed movie: {seed_movie}")
    seed_data = None
    for m in movies:
        if m.title == seed_movie:
            seed_data = m
            break
    if seed_data:
        print(f"  Genres: {', '.join(seed_data.genres)}")
        print(f"  Rating: {seed_data.rating}")
    activated = mem.activate(seed_movie, energy=1.0, top_k=30, iterations=3)
    movie_labels = set(mem.query_nodes(type="movie"))
    genre_labels = set(mem.query_nodes(type="genre"))
    movie_results = [a for a in activated if a.label in movie_labels and a.label != seed_movie]
    print(f"\nTop-10 genre-similar movies (by activation):")
    for a in movie_results[:10]:
        rating = "?"
        for m in movies:
            if m.title == a.label:
                rating = f"{m.rating:.1f}"
                break
        print(f"  {a.label:35s}  activation={a.activation:.4f}  depth={a.depth}  rating={rating}")
    genre_results = [a for a in activated if a.label in genre_labels]
    print(f"\nActivated genres:")
    for a in genre_results:
        print(f"  {a.label:15s}  activation={a.activation:.4f}  depth={a.depth}")
    print()


def section3_actor_director_collabs(mem: HypergraphMemory) -> None:
    print("=" * 70)
    print("SECTION 3: STRUCTURAL PATTERN - ACTOR-DIRECTOR COLLABORATIONS")
    print("=" * 70)
    acted_edges = mem.pattern_match(edge_label="acted_in")
    directed_edges = mem.pattern_match(edge_label="directed_by")
    actor_movies: dict[str, list[str]] = defaultdict(list)
    for e in acted_edges:
        if e.source_labels and e.target_labels:
            actor_movies[e.source_labels[0]].append(e.target_labels[0])
    director_movies: dict[str, list[str]] = defaultdict(list)
    for e in directed_edges:
        if e.source_labels and e.target_labels:
            director_movies[e.target_labels[0]].append(e.source_labels[0])
    collab_count: dict[tuple[str, str], int] = Counter()
    for actor, a_movies in actor_movies.items():
        a_set = set(a_movies)
        for director, d_movies in director_movies.items():
            shared = a_set & set(d_movies)
            if len(shared) >= 2:
                collab_count[(actor, director)] = len(shared)
    top_collabs = sorted(collab_count.items(), key=lambda x: -x[1])[:10]
    print(f"\nTop recurring actor-director collaborations (shared >= 2 movies):")
    print(f"  {'Actor':25s}  {'Director':25s}  {'Shared Movies':>14s}")
    for (actor, director), count in top_collabs:
        print(f"  {actor:25s}  {director:25s}  {count:>14d}")
    print(f"\nTotal collaboration pairs: {len(collab_count)}")
    print()


def section4_communities(mem: HypergraphMemory) -> None:
    print("=" * 70)
    print("SECTION 4: COMMUNITY DETECTION FOR TASTE CLUSTERS")
    print("=" * 70)
    result = mem.analyze.communities(seed=42)
    movie_labels = set(mem.query_nodes(type="movie"))
    genre_labels = set(mem.query_nodes(type="genre"))
    actor_labels_set = set(mem.query_nodes(type="actor"))
    print(f"\nCommunities found: {result.community_count}")
    print(f"Modularity:        {result.modularity:.4f}")
    print(f"Coverage:          {result.coverage:.4f}")
    top_communities = sorted(result.communities, key=lambda c: -c.size)[:5]
    for i, c in enumerate(top_communities):
        c_movies = [lbl for lbl in c.member_labels if lbl in movie_labels]
        c_genres = [lbl for lbl in c.member_labels if lbl in genre_labels]
        c_actors = [lbl for lbl in c.member_labels if lbl in actor_labels_set]
        genre_str = ", ".join(c_genres[:5]) if c_genres else "none"
        print(f"\n  Community {c.community_id} (size={c.size}, "
              f"internal={c.internal_edges}, external={c.external_edges}):")
        print(f"    Genres:  {genre_str}")
        if c_movies:
            print(f"    Movies:  {', '.join(c_movies[:6])}")
        if c_actors:
            print(f"    Actors:  {', '.join(c_actors[:4])}")
    print()


def section5_bridge_movies(mem: HypergraphMemory, movies: list[MovieData]) -> None:
    print("=" * 70)
    print("SECTION 5: BRIDGE MOVIES (BETWEENNESS CENTRALITY)")
    print("=" * 70)
    bc = mem.analyze.centrality("betweenness", top_k=10)
    movie_labels = set(mem.query_nodes(type="movie"))
    genre_labels = set(mem.query_nodes(type="genre"))
    print(f"\nTop-10 bridge nodes (gateway recommendations):\n")
    print(f"  {'Label':35s}  {'Type':10s}  {'Betweenness':>12s}")
    for label, score in bc.items():
        ntype = "movie" if label in movie_labels else ("genre" if label in genre_labels else "other")
        print(f"  {label:35s}  {ntype:10s}  {score:12.6f}")
    bridge_movies = [lbl for lbl, _ in bc.items() if lbl in movie_labels]
    if bridge_movies:
        print(f"\nBridge movies connect disparate genres/communities:")
        for lbl in bridge_movies[:5]:
            for m in movies:
                if m.title == lbl:
                    genre_str = ", ".join(m.genres)
                    print(f"  {lbl:35s}  [{genre_str}]  rating={m.rating}")
                    break
    print()


def section6_retrieval(mem: HypergraphMemory, movies: list[MovieData]) -> None:
    print("=" * 70)
    print("SECTION 6: RETRIEVAL-BASED RECOMMENDATION")
    print("=" * 70)
    seed_movie = "The Last Meridian"
    print(f"\nSeed movie: {seed_movie}")
    seed_data = None
    for m in movies:
        if m.title == seed_movie:
            seed_data = m
            break
    if seed_data:
        print(f"  Genres: {', '.join(seed_data.genres)}")
        print(f"  Rating: {seed_data.rating}")
    mem.search.activate(seed_movie, energy=1.0)
    activation_results = mem.search.activate(seed_movie, energy=1.0)
    print(f"\nPure activation (top-10):")
    movie_labels = set(mem.query_nodes(type="movie"))
    act_movies = [a for a in activation_results if a.label in movie_labels and a.label != seed_movie]
    for a in act_movies[:10]:
        print(f"  {a.label:35s}  energy={a.energy:.4f}")
    retrieval_results = mem.search.query(seed_movie, top_k=15)
    ret_movies = [r for r in retrieval_results if r.label in movie_labels and r.label != seed_movie]
    print(f"\nRRF retrieval (top-10, activation + similarity fused):")
    print(f"  {'Label':35s}  {'RRF':>8s}  {'Act':>8s}  {'Sim':>8s}")
    for r in ret_movies[:10]:
        print(f"  {r.label:35s}  {r.rrf_score:8.4f}  {r.activation:8.4f}  {r.similarity:8.4f}")
    act_set = {a.label for a in act_movies[:10]}
    ret_set = {r.label for r in ret_movies[:10]}
    overlap = act_set & ret_set
    unique_to_retrieval = ret_set - act_set
    print(f"\nComparison (top-10 lists):")
    print(f"  Overlap:                {len(overlap)} movies")
    print(f"  Unique to retrieval:    {len(unique_to_retrieval)} movies")
    if unique_to_retrieval:
        print(f"  Movies only in retrieval:")
        for lbl in sorted(unique_to_retrieval):
            rating = "?"
            for m in movies:
                if m.title == lbl:
                    rating = f"{m.rating:.1f}"
                    break
            print(f"    {lbl:35s}  rating={rating}")
    print()


def main() -> None:
    movies = generate_movies(seed=42)
    print(f"Generated {len(movies)} movies")
    directors_used = {m.director for m in movies}
    actors_used = set()
    for m in movies:
        actors_used.update(m.actors)
    print(f"Directors: {len(directors_used)}  Actors: {len(actors_used)}  Studios: {len(STUDIOS)}")
    mem = build_graph(movies)
    section1_construction(mem, movies)
    section2_genre_recommendation(mem, movies)
    section3_actor_director_collabs(mem)
    section4_communities(mem)
    section5_bridge_movies(mem, movies)
    section6_retrieval(mem, movies)
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
