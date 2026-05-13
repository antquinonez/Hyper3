"""
Belief Distributions and Bayesian Updating
===========================================

Demonstrates two probabilistic reasoning mechanisms: Bayesian belief
updating (evidence revises a prior over hypotheses) and Born-rule
distributions (ambiguous concepts with complex-amplitude states).

Covers prior/posterior updating, MAP estimation, Bayes factors,
credible sets, Born-rule sampling, concept correlation, and reset.

Run: .venv/bin/python examples/showcase/belief/belief_and_bayesian/belief_and_bayesian.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BAYESIAN BELIEF UPDATING")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    mem.add("patient", data={"type": "entity"})
    mem.add("healthy", data={"type": "state"})
    mem.add("disease_a", data={"type": "state"})
    mem.add("disease_b", data={"type": "state"})

    print("\n  Setting prior and updating with evidence")

    mem.bayes.set_prior("patient", outcomes=["healthy", "disease_a", "disease_b"],
                  weights=[0.7, 0.2, 0.1])

    outcome_labels = ["healthy", "disease_a", "disease_b"]
    label_map = {}
    for label in outcome_labels:
        nid = mem.resolve_id(label)
        if nid:
            label_map[nid] = label

    prior = mem.bayes.get("patient")
    print("\nprior:")
    if prior:
        for oid, prob in sorted(prior.outcomes.items(), key=lambda x: -x[1]):
            print(f"  {label_map.get(oid, oid[:12]):25s} {prob:.4f}")

    mem.bayes.update("patient", evidence="fever", likelihoods={"healthy": 0.1, "disease_a": 0.8, "disease_b": 0.3})
    posterior = mem.bayes.get("patient")
    print("\nposterior (after fever evidence):")
    if posterior:
        for oid, prob in sorted(posterior.outcomes.items(), key=lambda x: -x[1]):
            print(f"  {label_map.get(oid, oid[:12]):25s} {prob:.4f}")

    estimate = mem.bayes.map("patient")
    print(f"\nMAP estimate: {estimate}")

    mem.bayes.update("patient", evidence="lab_results", likelihoods={"healthy": 0.05, "disease_a": 0.9, "disease_b": 0.4})
    posterior2 = mem.bayes.get("patient")
    print("\nposterior (after lab results):")
    if posterior2:
        for oid, prob in sorted(posterior2.outcomes.items(), key=lambda x: -x[1]):
            print(f"  {label_map.get(oid, oid[:12]):25s} {prob:.4f}")
    print(f"\nupdated MAP estimate: {mem.bayes.map('patient')}")

    bf = mem.bayes.factor("patient", hyp_a="disease_a", hyp_b="disease_b")
    if bf is not None:
        print(f"Bayes factor (disease_a vs disease_b): {bf:.2f}")
    else:
        print("Bayes factor (disease_a vs disease_b): N/A")

    print("\n" + "=" * 70)
    print("SECTION 2: BORN-RULE BELIEF DISTRIBUTIONS")
    print("=" * 70)

    mem.add("bank", data={"type": "ambiguous"})
    mem.add("financial", data={"type": "sense"})
    mem.add("river_edge", data={"type": "sense"})
    mem.add("billiards", data={"type": "sense"})
    mem.add("drinking", data={"type": "sense"})
    mem.add("river", data={"type": "sense"})
    mem.add("ocean", data={"type": "sense"})

    mem.belief.create(
        ["financial", "river_edge", "billiards"],
        amplitudes=[0.6, 0.7, 0.3],
    )

    print("\n  Born-rule sampling: P = |amplitude|^2")

    counts = {"financial": 0, "river_edge": 0, "billiards": 0}
    n_samples = 1000
    for _ in range(n_samples):
        sample = mem.belief.sample("financial")
        if sample and sample in counts:
            counts[sample] += 1

    total = sum(counts.values())
    print(f"\nsampling distribution ({n_samples} trials):")
    for outcome, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {outcome:>12}: {count:>4} ({pct:>5.1f}%) {bar}")

    print("\n" + "=" * 70)
    print("SECTION 3: CONCEPT CORRELATION (QUANTUM-INSPIRED)")
    print("=" * 70)

    print("\n  Linking two distributions with pairwise correlation coefficients")

    mem.add("water", data={"type": "concept"})
    mem.add("fish", data={"type": "concept"})

    print("\n  Creating fresh distributions for correlation (overwrites Section 2 state)")
    print("  Group A: bank senses (financial, river_edge, billiards)")
    print("  Group B: water senses (drinking, river, ocean)")

    mem.belief.create(
        ["financial", "river_edge", "billiards"],
        amplitudes=[0.6, 0.7, 0.3],
    )
    mem.belief.create(
        ["drinking", "river", "ocean"],
        amplitudes=[0.3, 0.8, 0.4],
    )

    mem.belief.correlate(
        ["financial", "river_edge", "billiards"],
        ["drinking", "river", "ocean"],
        correlations={
            ("financial", "drinking"): 0.1,
            ("financial", "river"): -0.5,
            ("financial", "ocean"): 0.0,
            ("river_edge", "drinking"): 0.2,
            ("river_edge", "river"): 0.9,
            ("river_edge", "ocean"): 0.3,
            ("billiards", "drinking"): 0.1,
            ("billiards", "river"): -0.3,
            ("billiards", "ocean"): 0.0,
        },
    )

    sample_result = mem.belief.sample("financial")
    if sample_result:
        print(f"\nsampled from distribution -> {sample_result}")
        print("  (correlated outcome is biased by this observation)")
    else:
        print("\nno belief state available for sampling")

    print("\n" + "=" * 70)
    print("SECTION 4: CREDIBLE SET")
    print("=" * 70)

    cs = mem.bayes.credible("patient", level=0.9)
    print(f"\n90% credible set for patient diagnosis: {cs}")

    mem.bayes.reset("patient")
    prior_after = mem.bayes.get("patient")
    print("prior after reset:")
    if prior_after:
        for oid, prob in sorted(prior_after.outcomes.items(), key=lambda x: -x[1]):
            print(f"  {label_map.get(oid, oid[:12]):25s} {prob:.4f}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
