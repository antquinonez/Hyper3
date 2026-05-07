"""
Laminar Comparison: Belief & Bayesian Inference (Hyper3-only)
==============================================================
No direct competitor parallel — XGI, HNX, NetworkX have no
probabilistic belief representation or Bayesian updating.

Shows Born-rule belief distributions, Bayesian prior/posterior
updating, concept correlation, and multi-outcome sampling.

Run: .venv/bin/python examples/comparison/laminar/11_belief_and_bayesian.py
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

    print("\n--- No competitor equivalent ---")
    print("Set prior and update with evidence")

    mem.set_prior("patient", outcomes=["healthy", "disease_a", "disease_b"],
                  weights=[0.7, 0.2, 0.1])

    prior = mem.get_belief("patient")
    print(f"\nprior: {prior}")

    mem.update_belief("patient", evidence_name="fever", likelihoods={"healthy": 0.1, "disease_a": 0.8, "disease_b": 0.3})
    posterior = mem.get_belief("patient")
    print(f"posterior (after fever evidence): {posterior}")

    estimate = mem.map_estimate("patient")
    print(f"MAP estimate: {estimate}")

    mem.update_belief("patient", evidence_name="lab_results", likelihoods={"healthy": 0.05, "disease_a": 0.9, "disease_b": 0.4})
    posterior2 = mem.get_belief("patient")
    print(f"posterior (after lab results): {posterior2}")
    print(f"updated MAP estimate: {mem.map_estimate('patient')}")

    bf = mem.bayes_factor("patient", hypothesis_a="disease_a", hypothesis_b="disease_b")
    print(f"Bayes factor (disease_a vs disease_b): {bf:.2f}")

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

    mem.create_distribution(
        ["financial", "river_edge", "billiards"],
        amplitudes=[0.6, 0.7, 0.3],
    )

    print("\n--- No competitor equivalent ---")
    print("Born-rule sampling: P = |amplitude|^2")

    counts = {"financial": 0, "river_edge": 0, "billiards": 0}
    n_samples = 100
    for _ in range(n_samples):
        sample = mem.sample_distribution("financial")
        if sample and sample.label in counts:
            counts[sample.label] += 1

    total = sum(counts.values())
    print(f"\nsampling distribution ({n_samples} trials):")
    for outcome, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {outcome:>12}: {count:>3} ({pct:>5.1f}%) {bar}")

    print("\n" + "=" * 70)
    print("SECTION 3: CONCEPT CORRELATION (QUANTUM-INSPIRED)")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")

    mem.add("water", data={"type": "concept"})
    mem.add("fish", data={"type": "concept"})

    mem.create_distribution(
        ["financial", "river_edge", "billiards"],
        amplitudes=[0.6, 0.7, 0.3],
    )
    mem.create_distribution(
        ["drinking", "river", "ocean"],
        amplitudes=[0.3, 0.8, 0.4],
    )

    mem.correlate(
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

    sample_result = mem.sample_distribution("financial")
    if sample_result:
        print(f"\nsampled from distribution -> {sample_result.label}")
        print("  (correlated outcome is biased by this observation)")
    else:
        print("\nno belief state available for sampling")

    print("\n" + "=" * 70)
    print("SECTION 4: CREDIBLE SET")
    print("=" * 70)

    cs = mem.credible_set("patient", level=0.9)
    print(f"\n90% credible set for patient diagnosis: {cs}")

    mem.reset_belief("patient")
    prior_after = mem.get_belief("patient")
    print(f"prior after reset: {prior_after}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
