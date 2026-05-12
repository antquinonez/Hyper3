"""
Bayesian Medical Diagnosis Pipeline
====================================

First example demonstrating the Bayesian subsystem end-to-end. Models
an emergency department chest pain evaluation where diagnoses are refined
as test results arrive, culminating in a proved diagnosis.

Also demonstrates belief distributions for ambiguous symptom interpretation
and confidence assessment for identifying knowledge gaps.

Run with:
    .venv/bin/python examples/showcase/belief/bayesian_medical_diagnosis/bayesian_medical_diagnosis.py
"""

from __future__ import annotations


def main() -> None:
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building the Medical Knowledge Graph")
    print("=" * 70)

    symptoms = {
        "chest_pain": {"type": "symptom", "presentation": "common"},
        "shortness_of_breath": {"type": "symptom", "presentation": "common"},
        "diaphoresis": {"type": "symptom", "presentation": "moderate"},
        "nausea": {"type": "symptom", "presentation": "common"},
        "radiating_pain": {"type": "symptom", "presentation": "specific"},
    }
    for name, data in symptoms.items():
        mem.add(name, data=data)

    diagnoses = {
        "mi": {"type": "diagnosis", "full_name": "myocardial_infarction", "urgency": "critical"},
        "pe": {"type": "diagnosis", "full_name": "pulmonary_embolism", "urgency": "critical"},
        "gerd": {"type": "diagnosis", "full_name": "gastroesophageal_reflux", "urgency": "low"},
        "costochondritis": {"type": "diagnosis", "full_name": "costochondritis", "urgency": "low"},
        "anxiety": {"type": "diagnosis", "full_name": "anxiety_attack", "urgency": "low"},
        "aortic_dissection": {"type": "diagnosis", "full_name": "aortic_dissection", "urgency": "critical"},
    }
    for name, data in diagnoses.items():
        mem.add(name, data=data)

    tests = {
        "ecg_st_elevation": {"type": "test_result", "modality": "ecg"},
        "troponin_elevated": {"type": "test_result", "modality": "lab"},
        "d_dimer_elevated": {"type": "test_result", "modality": "lab"},
        "chest_xray_normal": {"type": "test_result", "modality": "imaging"},
        "ct_angio_positive": {"type": "test_result", "modality": "imaging"},
    }
    for name, data in tests.items():
        mem.add(name, data=data)

    risk_factors = {
        "hypertension": {"type": "risk_factor", "prevalence": "high"},
        "smoking_history": {"type": "risk_factor", "prevalence": "moderate"},
        "age_over_50": {"type": "risk_factor", "prevalence": "moderate"},
        "family_history": {"type": "risk_factor", "prevalence": "moderate"},
        "recent_surgery": {"type": "risk_factor", "prevalence": "low"},
        "obesity": {"type": "risk_factor", "prevalence": "high"},
    }
    for name, data in risk_factors.items():
        mem.add(name, data=data)

    cause_symptom_edges = [
        ("mi", "chest_pain", 0.95),
        ("mi", "shortness_of_breath", 0.75),
        ("mi", "diaphoresis", 0.80),
        ("mi", "nausea", 0.50),
        ("mi", "radiating_pain", 0.70),
        ("pe", "chest_pain", 0.65),
        ("pe", "shortness_of_breath", 0.90),
        ("pe", "diaphoresis", 0.40),
        ("gerd", "chest_pain", 0.85),
        ("gerd", "nausea", 0.60),
        ("costochondritis", "chest_pain", 0.90),
        ("costochondritis", "radiating_pain", 0.30),
        ("anxiety", "chest_pain", 0.70),
        ("anxiety", "shortness_of_breath", 0.80),
        ("anxiety", "diaphoresis", 0.60),
        ("anxiety", "nausea", 0.40),
        ("aortic_dissection", "chest_pain", 0.95),
        ("aortic_dissection", "shortness_of_breath", 0.50),
        ("aortic_dissection", "radiating_pain", 0.80),
    ]
    for cause, symptom, weight in cause_symptom_edges:
        mem.link(cause, symptom, label="causes_symptom", weight=weight)

    test_diagnosis_edges = [
        ("ecg_st_elevation", "mi", 0.90),
        ("troponin_elevated", "mi", 0.95),
        ("d_dimer_elevated", "pe", 0.85),
        ("ct_angio_positive", "pe", 0.95),
        ("chest_xray_normal", "gerd", 0.40),
        ("chest_xray_normal", "costochondritis", 0.50),
    ]
    for test, diagnosis, weight in test_diagnosis_edges:
        mem.link(test, diagnosis, label="supports", weight=weight)

    risk_edges = [
        ("hypertension", "mi", 0.7),
        ("smoking_history", "mi", 0.8),
        ("age_over_50", "mi", 0.6),
        ("family_history", "mi", 0.5),
        ("recent_surgery", "pe", 0.7),
        ("obesity", "mi", 0.5),
        ("obesity", "gerd", 0.6),
    ]
    for risk, diagnosis, weight in risk_edges:
        mem.link(risk, diagnosis, label="risk_factor_for", weight=weight)

    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")
    print(f"  Diagnoses: {len(diagnoses)}")
    print(f"  Symptoms: {len(symptoms)}")
    print(f"  Tests: {len(tests)}")
    print(f"  Risk factors: {len(risk_factors)}")
    print()

    print("=" * 70)
    print("SECTION 2: Initial Differential Diagnosis (Prior)")
    print("=" * 70)

    dx_outcomes = ["mi", "pe", "gerd", "costochondritis", "anxiety", "aortic_dissection"]
    dx_weights = [0.30, 0.10, 0.25, 0.15, 0.15, 0.05]

    mem.add("differential_diagnosis", data={"type": "bayesian_analysis"})
    mem.set_prior("differential_diagnosis", outcomes=dx_outcomes, weights=dx_weights)

    prior = mem.get_belief("differential_diagnosis")
    print("\n  Prior distribution (based on prevalence):")
    label_map = {}
    for h in dx_outcomes:
        nid = mem.resolve_id(h)
        if nid:
            label_map[nid] = h
    if prior:
        for outcome_id, prob in sorted(prior.outcomes.items(), key=lambda x: -x[1]):
            label = label_map.get(outcome_id, outcome_id[:12])
            print(f"    {label:25s} {prob:.4f}  {'#' * int(prob * 40)}")
    print()

    print("=" * 70)
    print("SECTION 3: Evidence Accumulation (Sequential Bayesian Updates)")
    print("=" * 70)

    evidence_sequence = [
        (
            "patient_presents_with_chest_pain_and_radiating_pain",
            {"mi": 0.80, "pe": 0.40, "gerd": 0.50, "costochondritis": 0.30, "anxiety": 0.40, "aortic_dissection": 0.60},
        ),
        (
            "ecg_shows_st_elevation",
            {"mi": 0.90, "pe": 0.10, "gerd": 0.05, "costochondritis": 0.05, "anxiety": 0.05, "aortic_dissection": 0.30},
        ),
        (
            "troponin_markedly_elevated",
            {"mi": 0.95, "pe": 0.25, "gerd": 0.02, "costochondritis": 0.01, "anxiety": 0.02, "aortic_dissection": 0.20},
        ),
        (
            "d_dimer_normal",
            {"mi": 0.60, "pe": 0.10, "gerd": 0.70, "costochondritis": 0.70, "anxiety": 0.70, "aortic_dissection": 0.40},
        ),
    ]

    for ev_name, likelihoods in evidence_sequence:
        result = mem.update_belief(
            "differential_diagnosis",
            evidence_name=ev_name,
            likelihoods=likelihoods,
        )
        if result.posterior:
            print(f"\n  After '{ev_name}':")
            for outcome_id, prob in sorted(
                result.posterior.outcomes.items(), key=lambda x: -x[1]
            ):
                label = label_map.get(outcome_id, outcome_id[:12])
                print(f"    {label:25s} {prob:.4f}")
            if result.kl_divergence > 0:
                print(f"    KL divergence: {result.kl_divergence:.4f} bits")
    print()

    print("=" * 70)
    print("SECTION 4: Diagnosis Confirmation")
    print("=" * 70)

    map_est = mem.map_estimate("differential_diagnosis")
    print(f"  MAP estimate (most probable diagnosis): {map_est}")

    credible = mem.credible_set("differential_diagnosis", level=0.95)
    print(f"  95% credible set: {credible}")

    bf = mem.bayes_factor(
        "differential_diagnosis",
        hypothesis_a="mi",
        hypothesis_b="pe",
    )
    if bf is not None:
        print(f"  Bayes factor (MI vs PE): {bf:.2f}")
        if bf > 100:
            print("    -> Decisive evidence for MI over PE")
        elif bf > 10:
            print("    -> Strong evidence for MI over PE")
        else:
            print("    -> Moderate evidence for MI over PE")
    print()

    print("=" * 70)
    print("SECTION 5: Ambiguous Symptom Interpretation")
    print("=" * 70)
    print()
    print("  Chest pain is ambiguous: it could be cardiac or GI in origin.")
    print("  Belief distributions model this ambiguity with context-dependent")
    print("  sampling to determine the most likely interpretation.")
    print()

    pain_outcomes = ["cardiac_chest_pain", "gi_chest_pain", "musculoskeletal_chest_pain"]
    for outcome in pain_outcomes:
        mem.add(outcome, data={"type": "pain_interpretation"})

    qs_pain = mem.belief.create(
        outcomes=["cardiac_chest_pain", "gi_chest_pain", "musculoskeletal_chest_pain"],
        amplitudes=[0.65, 0.25, 0.10],
        use_context=False,
    )
    print("  Chest pain interpretation distribution:")
    for o in qs_pain.outcomes:
        node = mem.engine.graph.get_node(o.node_id)
        lbl = node.label if node else o.node_id[:12]
        print(f"    {lbl:30s} amp={o.amplitude:.4f}  prob={o.probability:.4f}")

    cardiac_context = {"cardiac_chest_pain": 3.0, "gi_chest_pain": 0.5, "musculoskeletal_chest_pain": 0.3}
    answer = mem.sample(qs_pain, context=cardiac_context)
    if answer:
        node = mem.engine.graph.get_node(answer.node_id)
        lbl = node.label if node else answer.node_id[:12]
        print(f"\n  Given cardiac risk factors, sampled: {lbl}")
    print()

    print("=" * 70)
    print("SECTION 6: Knowledge Gap Identification")
    print("=" * 70)

    all_conf = mem.compute_all_confidences()
    print("\n  Overall confidence statistics:")
    print(f"    Average confidence: {all_conf.avg_confidence:.4f}")
    print(f"    High confidence (>0.8): {all_conf.high_confidence_count}")
    print(f"    Low confidence (<0.3): {all_conf.low_confidence_count}")

    print("\n  Per-diagnosis confidence:")
    for dx in dx_outcomes:
        score = mem.compute_confidence(dx)
        if score:
            bar_len = min(int(score.confidence * 20), 30)
            print(f"    {dx:25s} {score.confidence:.4f} {'#' * bar_len}")

    low = mem.flag_low_confidence(threshold=0.5)
    if low:
        print(f"\n  Low-confidence concepts ({len(low)}):")
        for item in low[:5]:
            print(f"    {item.node_label:25s} confidence={item.confidence:.4f} (depth={item.depth})")
        print("\n  These represent knowledge gaps where additional test relationships")
        print("  or risk factor connections would improve diagnostic confidence.")
    else:
        print("\n  No low-confidence concepts found.")

    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Prior distribution established from prevalence data")
    print("  2. Sequential Bayesian updates converge to MI diagnosis")
    print("  3. MAP estimate and Bayes factor confirm MI")
    print("  4. Belief distributions handle ambiguous symptom interpretation")
    print("  5. Confidence assessment identifies knowledge gaps")
    print(f"  6. Graph: {mem.size[0]} nodes, {mem.size[1]} edges")
    print()


if __name__ == "__main__":
    main()
