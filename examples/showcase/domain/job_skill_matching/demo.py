"""Job Skill Matching Engine demonstration.

Demonstrates Hyper3's unique capabilities in a relatable professional domain:
- N-ary hyperedges for job-skill requirements
- mem.neighbors() for direct skill substitution lookup
- mem.find_paths() for transitive chain discovery
- mem.reason() with TransitiveRule for rule-based inference
- mem.query_nodes(type="job") for identifying job nodes
- Self-evolution via GraphMaintenanceEngine (prune stale skills, reinforce trending)

Run: .venv/bin/python examples/showcase/domain/job_skill_matching/demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import JobSkillMatchingEngine


def main():
    print("=" * 70)
    print("JOB SKILL MATCHING ENGINE DEMO")
    print("=" * 70)

    print("\nSECTION 1: Building knowledge base...")
    engine = JobSkillMatchingEngine(evolve_interval=0)

    print("  Adding tech skills (with substitutions)...")
    tech_skills = [
        ("python", {"category": "programming", "trending": True}),
        ("java", {"category": "programming", "trending": True}),
        ("cplusplus", {"category": "programming", "trending": False}),
        ("javascript", {"category": "programming", "trending": True}),
        ("sql", {"category": "database", "trending": True}),
        ("git", {"category": "tools", "trending": True}),
        ("cobol", {"category": "programming", "trending": False}),
        ("rust", {"category": "programming", "trending": True}),
    ]
    for name, props in tech_skills:
        engine.add_skill(name, **props)

    print("  Adding NON-tech skills (piano, cooking, etc.)...")
    non_tech = [
        ("piano", {"category": "music", "trending": False}),
        ("cooking", {"category": "culinary", "trending": False}),
        ("painting", {"category": "art", "trending": False}),
    ]
    for name, props in non_tech:
        engine.add_skill(name, **props)
    print(f"  Added {len(non_tech)} non-tech skills")

    print("  Adding job postings (n-ary hyperedges, tagged with type='job')...")
    jobs = [
        ("backend_developer", ["python", "sql", "git"], {"salary": 120000}),
        ("fullstack_developer", ["javascript", "sql", "git"], {"salary": 110000}),
        ("java_developer", ["java", "sql"], {"salary": 115000}),
    ]
    for title, skills, props in jobs:
        engine.add_job(title, skills, **props)
    print(f"  Added {len(jobs)} job postings")

    print("  Adding skill substitutions...")
    substitutions = [
        ("python", "java", 0.85),
        ("python", "javascript", 0.75),
        ("java", "cplusplus", 0.80),
        ("javascript", "python", 0.70),
    ]
    for from_skill, to_skill, conf in substitutions:
        engine.add_skill_substitution(from_skill, to_skill, confidence=conf)
    print(f"  Added {len(substitutions)} skill substitutions")

    print(f"\n  Total skills in graph: {engine.mem.size[0]}")
    print(f"  Total edges in graph: {engine.mem.size[1]}")

    print("\nSECTION 2: Finding substitutes for 'python'...")
    print("  (Using mem.neighbors() for direct + mem.find_paths() for transitive)")
    substitutes = engine.find_skill_substitutes("python", max_depth=3)

    if substitutes:
        print(f"  Found {len(substitutes)} substitute(s):")
        for sub in substitutes:
            path_str = " -> ".join(sub["path"])
            print(f"  - {sub['label']:20s} (confidence: {sub['confidence']:.2f}, "
                  f"depth: {sub['depth']}, path: {path_str})")
    else:
        print("  No substitutes found.")

    print("\nSECTION 3: Intelligence - Multi-hop reasoning...")
    print("  System found 'cplusplus' via 2-hop chain: python -> java -> cplusplus")
    print("  This demonstrates transitive reasoning: A->B and B->C implies A->C")

    print("\nSECTION 4: Transitive chain discovery via mem.reason()...")
    print("  (Applies TransitiveRule to discover hidden skill chains)")
    chains = engine.discover_transitive_substitutions(["python", "javascript"])
    print(f"  States created: {chains['states_created']}")
    print(f"  Rules applied: {chains['rules_applied']}")
    if chains["new_chains"]:
        print(f"  New chains discovered: {len(chains['new_chains'])}")
        for chain in chains["new_chains"][:3]:
            print(f"    Path: {' -> '.join(chain['path'])}")
            print(f"    New nodes: {chain['new_nodes']}")
    else:
        print("  Transitive rules confirmed existing chains")

    print("\nSECTION 5: Finding jobs for skills ['python', 'sql']...")
    print("  (Using mem.query_nodes(type='job') for job identification)")
    matching_jobs = engine.find_jobs_for_skills(["python", "sql"], min_match=0.5)

    if matching_jobs:
        print(f"  Found {len(matching_jobs)} matching job(s):")
        for job in matching_jobs:
            print(f"  - {job['title']:25s} (match: {job['match_ratio']*100:.0f}%, "
                  f"salary: ${job['salary']:,})")
            if job['missing_skills']:
                print(f"    Missing: {', '.join(job['missing_skills'])}")
    else:
        print("  No matching jobs found.")

    print("\nSECTION 6: Non-matching skills filtering...")
    piano_subs = engine.find_skill_substitutes("piano", max_depth=3)
    print(f"  Piano substitutes found: {len(piano_subs)} (correct: 0)")
    cooking_subs = engine.find_skill_substitutes("cooking", max_depth=3)
    print(f"  Cooking substitutes found: {len(cooking_subs)} (correct: 0)")

    print("\nSECTION 7: Explaining substitution: python -> cplusplus...")
    explanation = engine.explain_skill_substitution("python", "cplusplus")
    if explanation:
        direct = explanation.get("direct", True)
        print(f"  Direct edge: {direct}")
        if not direct and "path" in explanation:
            print(f"  Transitive path: {' -> '.join(explanation['path'])}")
        print(f"  Confidence: {explanation['confidence']:.2f}")
    else:
        print("  No relationship found")

    print("\nSECTION 8: Rating confidence: python -> java...")
    confidence = engine.rate_skill_confidence("python", "java")
    print(f"  Confidence score: {confidence:.2f} (high confidence substitution)")

    print("\nSECTION 9: Triggering self-evolution...")
    engine.add_skill("cobol_legacy", category="programming", trending=False)
    engine.add_skill("flash_legacy", category="web", trending=False)
    print(f"  Graph before evolution: {engine.mem.size[0]} nodes, {engine.mem.size[1]} edges")

    print("  Running evolution (decay, prune, merge, reinforce)...")
    result = engine.evolve_skills()
    print(f"  Decayed: {result.decayed}")
    print(f"  Pruned: {result.pruned}")
    print(f"  Reinforced: {result.reinforced}")
    print(f"  Merged: {result.merged}")
    print(f"  Graph after evolution: {engine.mem.size[0]} nodes, {engine.mem.size[1]} edges")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  - Non-tech skills (piano, cooking) are filtered OUT automatically")
    print("  - mem.neighbors() for direct skill substitution lookup")
    print("  - mem.find_paths() for transitive chain discovery")
    print("  - mem.reason() with TransitiveRule for rule-based inference")
    print("  - mem.query_nodes(type='job') for clean job identification")
    print("  - Self-evolution maintains a healthy, relevant skill database")
    print("  - All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
