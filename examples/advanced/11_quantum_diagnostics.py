"""
Quantum Cognitive Diagnostics
===============================

This example demonstrates Hyper3's quantum cognitive layer in depth:
  - Superposition: Holding multiple hypotheses simultaneously
  - Entanglement: Correlated hypotheses (if A is true, B is likely true)
  - Collapse: Reducing to a single hypothesis with evidence
  - Interference: Constructive and destructive evidence combination
  - Measurement bases: Different perspectives for measurement

Use case: Medical diagnosis with competing hypotheses. A doctor
considers multiple diseases, incorporates correlated symptoms,
and updates beliefs as test results arrive.

Run with:
    .venv/bin/python examples/advanced/11_quantum_diagnostics.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, Modality


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Building a Diagnostic Knowledge Base
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Building Diagnostic Knowledge Base")
    print("=" * 70)

    diagnoses = {
        "pneumonia": {"type": "diagnosis", "urgency": "high", "icd10": "J18.9"},
        "bronchitis": {"type": "diagnosis", "urgency": "medium", "icd10": "J20.9"},
        "asthma_attack": {"type": "diagnosis", "urgency": "high", "icd10": "J45.901"},
        "pulmonary_embolism": {"type": "diagnosis", "urgency": "critical", "icd10": "I26.99"},
        "lung_cancer": {"type": "diagnosis", "urgency": "high", "icd10": "C34.90"},
        "copd_exacerbation": {"type": "diagnosis", "urgency": "high", "icd10": "J44.1"},
    }
    for name, data in diagnoses.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    symptoms = {
        "cough": {"type": "symptom"},
        "fever": {"type": "symptom"},
        "chest_pain": {"type": "symptom"},
        "shortness_of_breath": {"type": "symptom"},
        "wheezing": {"type": "symptom"},
        "hemoptysis": {"type": "symptom"},  # coughing up blood
        "fatigue": {"type": "symptom"},
        "weight_loss": {"type": "symptom"},
    }
    for name, data in symptoms.items():
        mem.store(name, data=data, modalities={Modality.SENSORY})

    tests = {
        "chest_xray": {"type": "test", "modality": "imaging"},
        "ct_scan": {"type": "test", "modality": "imaging"},
        "blood_culture": {"type": "test", "modality": "lab"},
        "d_dimer": {"type": "test", "modality": "lab"},
        "spirometry": {"type": "test", "modality": "pulmonary"},
        "sputum_culture": {"type": "test", "modality": "lab"},
    }
    for name, data in tests.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    # Diagnosis-symptom relationships
    for dx, syms in [
        ("pneumonia", ["cough", "fever", "shortness_of_breath", "fatigue", "chest_pain"]),
        ("bronchitis", ["cough", "wheezing", "fatigue"]),
        ("asthma_attack", ["wheezing", "shortness_of_breath", "chest_pain", "cough"]),
        ("pulmonary_embolism", ["chest_pain", "shortness_of_breath", "hemoptysis", "cough"]),
        ("lung_cancer", ["cough", "hemoptysis", "weight_loss", "fatigue", "chest_pain"]),
        ("copd_exacerbation", ["cough", "wheezing", "shortness_of_breath", "fatigue"]),
    ]:
        for sym in syms:
            mem.relate(dx, sym, label="causes")

    # Test-diagnosis relationships
    for test, dxs in [
        ("chest_xray", ["pneumonia", "lung_cancer"]),
        ("ct_scan", ["pulmonary_embolism", "lung_cancer"]),
        ("blood_culture", ["pneumonia"]),
        ("d_dimer", ["pulmonary_embolism"]),
        ("spirometry", ["asthma_attack", "copd_exacerbation"]),
        ("sputum_culture", ["pneumonia", "bronchitis"]),
    ]:
        for dx in dxs:
            mem.relate(test, dx, label="diagnoses")

    print(f"  {mem.graph.node_count} concepts, {mem.graph.edge_count} relationships")
    print()

    # =====================================================================
    # SECTION 2: Superposition - Multiple Diagnoses Alive
    # =====================================================================
    # Patient presents with: cough, chest pain, shortness of breath.
    # Multiple diagnoses could explain these symptoms.

    print("=" * 70)
    print("SECTION 2: Superposition of Diagnostic Hypotheses")
    print("=" * 70)

    qs = mem.superpose(
        ["pneumonia", "bronchitis", "pulmonary_embolism", "lung_cancer"],
        amplitudes=[0.6, 0.4, 0.3, 0.2],
    )
    print(f"  Patient presents with: cough, chest pain, shortness of breath")
    print(f"\n  Superposition of {qs.superposition_count} diagnoses:")
    for interp in qs.interpretations:
        print(f"    {interp.label or interp.node_id[:8]:25s} "
              f"amp={interp.amplitude:.2f}  prob={interp.probability:.3f}")

    # Probability must sum to 1 (Born rule: |amplitude|^2)
    total_prob = sum(i.probability for i in qs.interpretations)
    print(f"\n  Total probability: {total_prob:.3f} (normalized by Born rule)")
    print()

    # =====================================================================
    # SECTION 3: Entanglement - Correlated Diagnoses
    # =====================================================================
    # If the patient has pneumonia, bronchitis is more likely too
    # (co-infection). If pulmonary_embolism, pneumonia is less likely.

    print("=" * 70)
    print("SECTION 3: Entanglement - Diagnostic Correlations")
    print("=" * 70)

    ent = mem.entangle(
        ["pneumonia", "pulmonary_embolism"],
        ["bronchitis", "lung_cancer"],
        {
            ("pneumonia", "bronchitis"): 0.7,
            ("pneumonia", "lung_cancer"): 0.2,
            ("pulmonary_embolism", "bronchitis"): 0.1,
            ("pulmonary_embolism", "lung_cancer"): 0.4,
        },
    )
    print(f"  Created entanglement: {ent.id[:12]}...")
    print(f"  Correlations:")
    print(f"    pneumonia <-> bronchitis: +0.7 (co-infection likely)")
    print(f"    pneumonia <-> lung_cancer: +0.2 (possible underlying)")
    print(f"    pulmonary_embolism <-> bronchitis: +0.1 (unlikely)")
    print(f"    pulmonary_embolism <-> lung_cancer: +0.4 (cancer risk factor)")
    print()

    # =====================================================================
    # SECTION 4: Evidence-Based Collapse
    # =====================================================================
    # As test results arrive, we update our beliefs. collapse()
    # with context weights hypotheses by new evidence.

    print("=" * 70)
    print("SECTION 4: Evidence-Based Collapse")
    print("=" * 70)

    # Round 1: Chest X-ray shows consolidation (supports pneumonia)
    print("  Evidence: Chest X-ray shows consolidation (supports pneumonia)")
    answer1 = mem.collapse(qs, context={"pneumonia": 2.5, "lung_cancer": 1.5})
    if answer1:
        print(f"  Most likely: {answer1.label or answer1.node_id[:8]} "
              f"(amplitude={answer1.amplitude:.3f})")
    print()

    # =====================================================================
    # SECTION 5: Interference Patterns
    # =====================================================================
    # Interference shows how positive and negative evidence combine.

    print("=" * 70)
    print("SECTION 5: Evidence Interference Patterns")
    print("=" * 70)

    qs2 = mem.superpose(
        ["pneumonia", "bronchitis", "asthma_attack", "pulmonary_embolism",
         "copd_exacerbation", "lung_cancer"],
        amplitudes=[0.7, -0.3, 0.4, -0.5, 0.2, 0.1],
    )

    patterns = mem.compute_interference(qs2)
    print("  Interference analysis:")
    for p in patterns:
        node = mem.graph.get_node(p.node_id)
        label = node.label if node else p.node_id[:8]
        kind = "CONSTRUCTIVE" if p.is_constructive else "DESTRUCTIVE" if p.is_destructive else "NEUTRAL"
        print(f"    {label:25s} [{kind:12s}] "
              f"constructive={p.constructive:+.3f}  "
              f"destructive={p.destructive:+.3f}  "
              f"net={p.net_amplitude:+.3f}")
    print()

    # =====================================================================
    # SECTION 6: Entangled Collapse
    # =====================================================================
    # Collapse one hypothesis and see how it affects correlated hypotheses.

    print("=" * 70)
    print("SECTION 6: Entangled Collapse (Cascade)")
    print("=" * 70)

    # Create a new superposition with entanglement
    qs3 = mem.superpose(
        ["pneumonia", "bronchitis", "pulmonary_embolism", "lung_cancer"],
        amplitudes=[0.6, 0.5, 0.3, 0.2],
    )

    ent2 = mem.entangle(
        ["pneumonia"],
        ["bronchitis", "lung_cancer"],
        {
            ("pneumonia", "bronchitis"): 0.8,
            ("pneumonia", "lung_cancer"): 0.3,
        },
    )

    # Observe pneumonia (confirm it) and see cascade
    cascaded = mem.collapse_entangled(qs3, "pneumonia")
    print(f"  Observed: pneumonia (confirmed)")
    print(f"  Entangled collapse results:")
    for observed_label, state in cascaded.items():
        print(f"    {observed_label}: {state}")
    print()

    # =====================================================================
    # SECTION 7: Detection of Collapse Triggers
    # =====================================================================
    # detect_collapse_triggers() finds conditions that would force
    # the system to collapse (e.g., a test result that rules out
    # all but one hypothesis).

    print("=" * 70)
    print("SECTION 7: Collapse Trigger Detection")
    print("=" * 70)

    qs4 = mem.superpose(
        ["pneumonia", "asthma_attack", "copd_exacerbation"],
        amplitudes=[0.5, 0.4, 0.3],
    )
    triggers = mem.detect_collapse_triggers(qs4)
    if triggers:
        print(f"  Detected {len(triggers)} collapse triggers:")
        for trigger in triggers:
            print(f"    {trigger.trigger_type}: {trigger.description}")
    else:
        print("  No collapse triggers detected (system is stable)")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Superposition holds multiple diagnoses simultaneously")
    print("  2. Entanglement encodes diagnostic correlations")
    print("  3. Collapse resolves hypotheses with evidence")
    print("  4. Interference shows constructive/destructive evidence patterns")
    print("  5. Entangled collapse cascades through correlated diagnoses")
    print("  6. Collapse triggers detect forced resolution conditions")
    print()


if __name__ == "__main__":
    main()
