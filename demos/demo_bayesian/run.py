"""
Bayesian Reasoning Walkthrough
==============================

Emergency room triage: a patient presents with chest pain. The system
maintains a differential diagnosis using Bayesian prior/posterior updating.
Evidence arrives sequentially (ECG, troponin, D-dimer) and the posterior
shifts with each update.

Contrasts with demo_walkthrough.py which uses Born-rule sampling (the belief
layer). This demo uses classical Bayesian updating: prior x likelihood = posterior.

Key Hyper3 API demonstrated:
    - mem.bayes.set_prior()   — initialize categorical prior
    - mem.bayes.get()         — inspect current distribution
    - mem.bayes.update()      — apply evidence via Bayes' rule
    - mem.bayes.map()         — maximum a posteriori estimate
    - mem.bayes.factor()      — Bayes factor between hypotheses
    - mem.bayes.credible()    — credible set at given level
    - mem.bayes.reset()       — reset to uniform prior

Supporting infrastructure:
    - data.py     — conditions, symptoms, evidence likelihoods
    - storage.py  — SQLite for belief snapshot persistence

Run: .venv/bin/python demos/demo_bayesian/run.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper3 import HypergraphMemory, Modality

try:
    from .data import CONDITIONS, SYMPTOMS, EVIDENCE_SEQUENCE, CONDITION_EDGES
    from .storage import (
        open_db,
        seed_conditions,
        snapshot_beliefs,
        log_evidence,
        load_belief_history,
        load_evidence_log,
    )
except ImportError:
    from data import CONDITIONS, SYMPTOMS, EVIDENCE_SEQUENCE, CONDITION_EDGES
    from storage import (
        open_db,
        seed_conditions,
        snapshot_beliefs,
        log_evidence,
        load_belief_history,
        load_evidence_log,
    )


def _resolve_outcomes(mem: HypergraphMemory, dist) -> dict[str, float]:
    """Map outcome keys (which may be node IDs) back to human-readable labels."""
    resolved = {}
    for key, prob in dist.outcomes.items():
        node = mem.engine.graph.get_node(key)
        label = node.label if node else key
        resolved[label] = prob
    return resolved


def header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def main() -> None:
    print(
        """
    +------------------------------------------------------------------+
    |  BAYESIAN REASONING WALKTHROUGH                                  |
    |  Scenario: Emergency room differential diagnosis                 |
    +------------------------------------------------------------------+
    """
    )

    mem = HypergraphMemory(evolve_interval=0)
    db = open_db()
    seed_conditions(db)

    # ── STEP 1: Build the medical knowledge graph ────────────────────
    #
    # Conditions become nodes with severity/type data. Symptoms become
    # nodes linked to conditions via "presents_with" edges. The graph
    # provides context for the Bayesian reasoning but is not itself
    # updated by Bayes' rule -- that happens in the BayesianLayer.
    #
    header("STEP 1: Building the medical knowledge graph")

    for name, data in CONDITIONS.items():
        mem.add(name, data={"type": "condition", **data}, modalities={Modality.CONCEPTUAL})

    for name, data in SYMPTOMS.items():
        mem.add(name, data={"type": "symptom", **data})

    for src, tgt, label in CONDITION_EDGES:
        mem.link(src, tgt, label=label)

    print(f"  Stored {mem.size[0]} concepts, {mem.size[1]} relationships")
    print(f"  Conditions: {', '.join(CONDITIONS.keys())}")
    print(f"  Symptoms:   {', '.join(SYMPTOMS.keys())}")

    # ── STEP 2: Set the prior distribution ───────────────────────────
    #
    # bayes.set_prior() initializes a CategoricalDistribution over the
    # named outcomes. The weights are based on ER prevalence data:
    # GERD and costochondritis are the most common causes of chest pain,
    # but MI is the most dangerous and gets higher clinical weight.
    #
    # The prior must target an EXISTING node in the graph.
    #
    header("STEP 2: Setting the prior distribution")

    outcome_names = list(CONDITIONS.keys())
    prior_weights = [CONDITIONS[name]["prevalence"] for name in outcome_names]

    mem.add("diagnosis", data={"type": "distribution_target"})
    prior = mem.bayes.set_prior("diagnosis", outcomes=outcome_names, weights=prior_weights)

    resolved_prior = _resolve_outcomes(mem, prior)
    print("  Prior distribution (ER prevalence):")
    for name, prob in resolved_prior.items():
        bar = "#" * int(prob * 40)
        print(f"    {name:25s} {prob:.3f}  {bar}")
    print(f"\n  Entropy: {prior.entropy():.3f} bits")
    print(f"  (higher entropy = more uncertainty)")
    snapshot_beliefs(db, step=0, posterior=resolved_prior)

    # ── STEP 3: First evidence — ECG shows ST elevation ──────────────
    #
    # bayes.update() applies Bayes' rule: P(H|E) = P(E|H) * P(H) / P(E).
    # The likelihoods dict provides P(E|H) for each hypothesis.
    # ST elevation is highly specific for MI (likelihood 0.85).
    #
    header("STEP 3: Evidence arrives — ECG shows ST elevation")

    ev1 = EVIDENCE_SEQUENCE[0]
    print(f"  Evidence: {ev1['description']}")

    result1 = mem.bayes.update(
        "diagnosis", evidence=ev1["name"], likelihoods=ev1["likelihoods"]
    )

    resolved_post1 = _resolve_outcomes(mem, result1.posterior)
    print(f"\n  KL divergence from prior: {result1.kl_divergence:.4f}")
    print(f"  (how much the evidence shifted our beliefs)")
    print("\n  Posterior after ST elevation:")
    for name, prob in resolved_post1.items():
        bar = "#" * int(prob * 40)
        print(f"    {name:25s} {prob:.3f}  {bar}")

    log_evidence(db, step=1, evidence_name=ev1["name"],
                 description=ev1["description"], kl_divergence=result1.kl_divergence)
    snapshot_beliefs(db, step=1, posterior=resolved_post1)

    # ── STEP 4: MAP estimate and Bayes factor ────────────────────────
    #
    # bayes.map() returns the maximum a posteriori (MAP) estimate: the
    # single hypothesis with the highest posterior probability.
    #
    # bayes.factor() computes the Bayes factor K = P(E|H_a) / P(E|H_b).
    # K > 150 is "very strong" evidence on the Kass-Raftery scale.
    #
    header("STEP 4: MAP estimate and Bayes factor")

    map_result = mem.bayes.map("diagnosis")
    print(f"  MAP estimate: {map_result}")

    bf = mem.bayes.factor("diagnosis", hyp_a="mi", hyp_b="gerd")
    print(f"  Bayes factor MI vs GERD: {bf:.1f}")
    if bf > 150:
        print("  Interpretation: VERY STRONG evidence favoring MI")
    elif bf > 20:
        print("  Interpretation: STRONG evidence favoring MI")
    elif bf > 3:
        print("  Interpretation: MODERATE evidence favoring MI")
    else:
        print("  Interpretation: weak or inconclusive evidence")

    # ── STEP 5: Second evidence — troponin elevated ──────────────────
    #
    # Sequential updating: each call to bayes.update() modifies the
    # posterior in place. The second evidence compounds on the first.
    # Elevated troponin further confirms MI (likelihood 0.95).
    #
    header("STEP 5: Second evidence — troponin elevated")

    ev2 = EVIDENCE_SEQUENCE[1]
    print(f"  Evidence: {ev2['description']}")

    result2 = mem.bayes.update(
        "diagnosis", evidence=ev2["name"], likelihoods=ev2["likelihoods"]
    )

    resolved_post2 = _resolve_outcomes(mem, result2.posterior)
    print(f"  KL divergence: {result2.kl_divergence:.4f}")
    print("\n  Posterior after ST elevation + troponin:")
    for name, prob in resolved_post2.items():
        bar = "#" * int(prob * 40)
        print(f"    {name:25s} {prob:.3f}  {bar}")

    log_evidence(db, step=2, evidence_name=ev2["name"],
                 description=ev2["description"], kl_divergence=result2.kl_divergence)
    snapshot_beliefs(db, step=2, posterior=resolved_post2)

    # After two strong pieces of evidence, MI should dominate.
    print(f"\n  MAP estimate: {mem.bayes.map('diagnosis')}")

    # ── STEP 6: Credible set ─────────────────────────────────────────
    #
    # bayes.credible() returns the smallest set of hypotheses whose
    # cumulative probability >= level. This is the Bayesian analog of
    # a confidence interval: "which diagnoses should we still consider?"
    #
    header("STEP 6: Credible set at 95%")

    credible = mem.bayes.credible("diagnosis", level=0.95)
    print(f"  95% credible set: {credible}")
    print(f"  Size: {len(credible)} hypotheses")
    if len(credible) == 1:
        print("  One hypothesis exceeds 95% probability -- diagnosis is clear.")
    else:
        print("  Multiple hypotheses remain in the credible set.")

    # ── STEP 7: Contrasting evidence — D-dimer elevated ──────────────
    #
    # D-dimer is sensitive for PE but non-specific. This introduces
    # genuine diagnostic uncertainty where the posterior doesn't collapse
    # to a single hypothesis. This step demonstrates what happens when
    # evidence partially conflicts with the current best hypothesis.
    #
    header("STEP 7: Conflicting evidence — D-dimer elevated")

    ev3 = EVIDENCE_SEQUENCE[2]
    print(f"  Evidence: {ev3['description']}")
    print("  D-dimer is sensitive for PE but can be elevated in many conditions.")

    result3 = mem.bayes.update(
        "diagnosis", evidence=ev3["name"], likelihoods=ev3["likelihoods"]
    )

    resolved_post3 = _resolve_outcomes(mem, result3.posterior)
    print(f"  KL divergence: {result3.kl_divergence:.4f}")
    print("\n  Posterior after all three evidence updates:")
    for name, prob in resolved_post3.items():
        bar = "#" * int(prob * 40)
        print(f"    {name:25s} {prob:.3f}  {bar}")

    log_evidence(db, step=3, evidence_name=ev3["name"],
                 description=ev3["description"], kl_divergence=result3.kl_divergence)
    snapshot_beliefs(db, step=3, posterior=resolved_post3)

    print(f"\n  MAP: {mem.bayes.map('diagnosis')}")
    print(f"  MI vs PE Bayes factor: {mem.bayes.factor('diagnosis', hyp_a='mi', hyp_b='pe'):.1f}")
    credible3 = mem.bayes.credible("diagnosis", level=0.95)
    print(f"  95% credible set: {credible3}")

    # ── STEP 8: Review evidence history from SQLite ──────────────────
    #
    # The storage layer has captured every belief snapshot. We can query
    # it to see how the posterior evolved across all evidence updates.
    #
    header("STEP 8: Evidence history (from SQLite)")

    history = load_belief_history(db)
    evidence_log = load_evidence_log(db)

    print("  Evidence log:")
    for entry in evidence_log:
        print(f"    Step {entry['step']}: {entry['evidence_name']}")
        print(f"      {entry['description']}")
        print(f"      KL divergence: {entry['kl_divergence']:.4f}")

    print("\n  Belief evolution (probability by step):")
    steps = sorted(set(row["step"] for row in history))
    conditions = sorted(set(row["condition"] for row in history))
    header_row = f"    {'Condition':25s}"
    for step in steps:
        header_row += f"  Step {step:>2}"
    print(header_row)
    print(f"    {'-' * 25}  {'------  ' * len(steps)}")
    for cond in conditions:
        row = f"    {cond:25s}"
        for step in steps:
            prob = next(
                (r["probability"] for r in history if r["step"] == step and r["condition"] == cond),
                0.0,
            )
            row += f"  {prob:>6.3f}"
        print(row)

    # ── STEP 9: Reset to uniform prior ───────────────────────────────
    #
    # bayes.reset() restores the distribution to a uniform prior and
    # clears the evidence history. This simulates starting a fresh
    # diagnostic workup for a new patient.
    #
    header("STEP 9: Reset to uniform prior")

    mem.bayes.reset("diagnosis")
    reset_dist = mem.bayes.get("diagnosis")
    resolved_reset = _resolve_outcomes(mem, reset_dist)
    print("  After reset (uniform prior):")
    for name, prob in resolved_reset.items():
        print(f"    {name:25s} {prob:.3f}")
    print(f"  Entropy: {reset_dist.entropy():.3f} bits")
    print("  (maximum entropy = maximum uncertainty = uniform distribution)")

    # ── SUMMARY ──────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    print("""
    1. KNOWLEDGE GRAPH  — Stored conditions, symptoms, and relationships
    2. PRIOR            — Set Bayesian prior from ER prevalence data
    3. ST ELEVATION     — Strong evidence for MI; posterior shifts sharply
    4. MAP + FACTOR     — MAP estimate: MI. Bayes factor: very strong
    5. TROponIN         — Compounds ST elevation; MI probability increases
    6. CREDIBLE SET     — MI alone exceeds 95% credible threshold
    7. D-DIMER          — Conflicting evidence; PE probability increases
    8. HISTORY          — SQLite tracks belief evolution across updates
    9. RESET            — Uniform prior; ready for a new patient

    Key contrast with demo_walkthrough.py:
      - That demo uses Born-rule sampling (|amplitude|^2) for belief states
      - This demo uses classical Bayesian updating (prior x likelihood)
      - Both manage uncertainty but with different mathematical formalisms
    """)

    db.close()


if __name__ == "__main__":
    main()
