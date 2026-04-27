"""
Medical Diagnosis Knowledge Graph with Backward Chaining and Belief Revision
============================================================================

Builds a clinical knowledge graph with 120+ nodes covering diseases, symptoms,
risk factors, lab findings, and medications. Demonstrates:

  1. Backward chaining from suspected diagnoses to required evidence
  2. Belief revision when contradictory clinical findings emerge
  3. Uncertainty propagation through inference chains
  4. Structural pattern matching for clinical pathways

Run with:
    .venv/bin/python examples/domain/medical_diagnosis.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, TransitiveRule, InverseRule


DISEASES = {
    "pneumonia": {"category": "disease", "severity": "high", "prevalence": 0.02},
    "bronchitis": {"category": "disease", "severity": "medium", "prevalence": 0.05},
    "asthma_exacerbation": {"category": "disease", "severity": "high", "prevalence": 0.03},
    "pulmonary_embolism": {"category": "disease", "severity": "critical", "prevalence": 0.001},
    "lung_cancer": {"category": "disease", "severity": "critical", "prevalence": 0.0005},
    "tuberculosis": {"category": "disease", "severity": "high", "prevalence": 0.003},
    "copd_exacerbation": {"category": "disease", "severity": "high", "prevalence": 0.01},
    "heart_failure": {"category": "disease", "severity": "critical", "prevalence": 0.02},
    "myocardial_infarction": {"category": "disease", "severity": "critical", "prevalence": 0.005},
    "aortic_dissection": {"category": "disease", "severity": "critical", "prevalence": 0.0003},
    "pneumothorax": {"category": "disease", "severity": "high", "prevalence": 0.001},
    "pleural_effusion": {"category": "disease", "severity": "medium", "prevalence": 0.004},
    "covid19": {"category": "disease", "severity": "variable", "prevalence": 0.08},
    "influenza": {"category": "disease", "severity": "medium", "prevalence": 0.10},
    "sepsis": {"category": "disease", "severity": "critical", "prevalence": 0.002},
}

SYMPTOMS = {
    "cough": {"category": "symptom", "specificity": "low"},
    "productive_cough": {"category": "symptom", "specificity": "medium"},
    "dry_cough": {"category": "symptom", "specificity": "medium"},
    "dyspnea": {"category": "symptom", "specificity": "low"},
    "pleuritic_chest_pain": {"category": "symptom", "specificity": "medium"},
    "substernal_chest_pain": {"category": "symptom", "specificity": "medium"},
    "fever": {"category": "symptom", "specificity": "low"},
    "high_fever": {"category": "symptom", "specificity": "medium"},
    "night_sweats": {"category": "symptom", "specificity": "medium"},
    "hemoptysis": {"category": "symptom", "specificity": "high"},
    "weight_loss": {"category": "symptom", "specificity": "low"},
    "fatigue": {"category": "symptom", "specificity": "low"},
    "tachycardia": {"category": "symptom", "specificity": "low"},
    "hypotension": {"category": "symptom", "specificity": "medium"},
    "cyanosis": {"category": "symptom", "specificity": "medium"},
    "confusion": {"category": "symptom", "specificity": "low"},
    "leg_swelling": {"category": "symptom", "specificity": "medium"},
    "sudden_onset_dyspnea": {"category": "symptom", "specificity": "high"},
    "orthopnea": {"category": "symptom", "specificity": "medium"},
    "wheezing": {"category": "symptom", "specificity": "medium"},
    "myalgia": {"category": "symptom", "specificity": "low"},
}

LAB_FINDINGS = {
    "elevated_wbc": {"category": "lab", "normal_range": "4-11k/uL", "specificity": "low"},
    "elevated_crp": {"category": "lab", "normal_range": "<10 mg/L", "specificity": "low"},
    "elevated_procalcitonin": {"category": "lab", "normal_range": "<0.5 ng/mL", "specificity": "high"},
    "elevated_d_dimer": {"category": "lab", "normal_range": "<500 ng/mL", "specificity": "low"},
    "positive_blood_culture": {"category": "lab", "specificity": "high"},
    "hypoxemia": {"category": "lab", "normal_range": "PaO2 > 80", "specificity": "medium"},
    "elevated_troponin": {"category": "lab", "normal_range": "<14 ng/L", "specificity": "high"},
    "elevated_bnp": {"category": "lab", "normal_range": "<100 pg/mL", "specificity": "medium"},
    "elevated_ldh": {"category": "lab", "normal_range": "140-280 U/L", "specificity": "low"},
    "anemia": {"category": "lab", "normal_range": "Hgb > 12", "specificity": "low"},
    "positive_pcr_covid": {"category": "lab", "specificity": "very_high"},
    "positive_ppd": {"category": "lab", "specificity": "medium"},
    "elevated_esr": {"category": "lab", "normal_range": "<20 mm/hr", "specificity": "low"},
    "coagulopathy": {"category": "lab", "specificity": "medium"},
    "lactic_acidosis": {"category": "lab", "specificity": "medium"},
}

IMAGING = {
    "chest_infiltrate_xray": {"category": "imaging", "specificity": "medium"},
    "chest_opacity_ct": {"category": "imaging", "specificity": "high"},
    "pleural_effusion_xray": {"category": "imaging", "specificity": "high"},
    "pulmonary_embolism_ct": {"category": "imaging", "specificity": "very_high"},
    "pneumothorax_xray": {"category": "imaging", "specificity": "very_high"},
    "cardiomegaly_xray": {"category": "imaging", "specificity": "high"},
    "ground_glass_opacities_ct": {"category": "imaging", "specificity": "medium"},
    "lung_mass_ct": {"category": "imaging", "specificity": "high"},
    "pulmonary_edema_ct": {"category": "imaging", "specificity": "high"},
    "aortic_dissection_ct": {"category": "imaging", "specificity": "very_high"},
    "normal_chest_xray": {"category": "imaging", "specificity": "medium"},
}

RISK_FACTORS = {
    "age_over_65": {"category": "risk_factor", "strength": "moderate"},
    "smoking_history": {"category": "risk_factor", "strength": "strong"},
    "current_smoker": {"category": "risk_factor", "strength": "strong"},
    "immunosuppression": {"category": "risk_factor", "strength": "strong"},
    "recent_surgery": {"category": "risk_factor", "strength": "moderate"},
    "prolonged_immobility": {"category": "risk_factor", "strength": "strong"},
    "copd_history": {"category": "risk_factor", "strength": "strong"},
    "heart_disease_history": {"category": "risk_factor", "strength": "strong"},
    "diabetes": {"category": "risk_factor", "strength": "moderate"},
    "malignancy_history": {"category": "risk_factor", "strength": "moderate"},
    "recent_travel_endemic_tb": {"category": "risk_factor", "strength": "strong"},
    "obesity": {"category": "risk_factor", "strength": "moderate"},
    "hypertension": {"category": "risk_factor", "strength": "moderate"},
    "asbestos_exposure": {"category": "risk_factor", "strength": "strong"},
    "vaccination_status": {"category": "risk_factor", "strength": "moderate"},
}

MEDICATIONS = {
    "amoxicillin": {"category": "medication", "class": "antibiotic", "route": "oral"},
    "azithromycin": {"category": "medication", "class": "antibiotic", "route": "oral/IV"},
    "levofloxacin": {"category": "medication", "class": "antibiotic", "route": "oral/IV"},
    "ceftriaxone": {"category": "medication", "class": "antibiotic", "route": "IV"},
    "oseltamivir": {"category": "medication", "class": "antiviral", "route": "oral"},
    "albuterol": {"category": "medication", "class": "bronchodilator", "route": "inhaled"},
    "prednisone": {"category": "medication", "class": "corticosteroid", "route": "oral"},
    "heparin": {"category": "medication", "class": "anticoagulant", "route": "IV"},
    "warfarin": {"category": "medication", "class": "anticoagulant", "route": "oral"},
    "furosemide": {"category": "medication", "class": "diuretic", "route": "oral/IV"},
    "isoniazid": {"category": "medication", "class": "antitubercular", "route": "oral"},
    "rifampin": {"category": "medication", "class": "antitubercular", "route": "oral"},
    "morphine": {"category": "medication", "class": "analgesic", "route": "IV"},
    "oxygen_therapy": {"category": "medication", "class": "supportive", "route": "inhaled"},
    "metoprolol": {"category": "medication", "class": "beta_blocker", "route": "oral"},
}

CAUSES_EDGES = [
    ("pneumonia", "cough"), ("pneumonia", "productive_cough"), ("pneumonia", "fever"),
    ("pneumonia", "dyspnea"), ("pneumonia", "pleuritic_chest_pain"), ("pneumonia", "tachycardia"),
    ("pneumonia", "elevated_wbc"), ("pneumonia", "elevated_crp"), ("pneumonia", "hypoxemia"),
    ("pneumonia", "elevated_procalcitonin"), ("pneumonia", "chest_infiltrate_xray"),
    ("pneumonia", "chest_opacity_ct"), ("pneumonia", "elevated_ldh"),
    ("bronchitis", "cough"), ("bronchitis", "productive_cough"), ("bronchitis", "fever"),
    ("bronchitis", "dyspnea"), ("bronchitis", "wheezing"), ("bronchitis", "fatigue"),
    ("asthma_exacerbation", "dyspnea"), ("asthma_exacerbation", "wheezing"),
    ("asthma_exacerbation", "dry_cough"), ("asthma_exacerbation", "tachycardia"),
    ("asthma_exacerbation", "hypoxemia"),
    ("pulmonary_embolism", "sudden_onset_dyspnea"), ("pulmonary_embolism", "pleuritic_chest_pain"),
    ("pulmonary_embolism", "tachycardia"), ("pulmonary_embolism", "hypoxemia"),
    ("pulmonary_embolism", "elevated_d_dimer"), ("pulmonary_embolism", "hemoptysis"),
    ("pulmonary_embolism", "pulmonary_embolism_ct"),
    ("lung_cancer", "cough"), ("lung_cancer", "hemoptysis"), ("lung_cancer", "weight_loss"),
    ("lung_cancer", "dyspnea"), ("lung_cancer", "chest_opacity_ct"),
    ("lung_cancer", "lung_mass_ct"), ("lung_cancer", "fatigue"),
    ("tuberculosis", "cough"), ("tuberculosis", "night_sweats"), ("tuberculosis", "fever"),
    ("tuberculosis", "weight_loss"), ("tuberculosis", "hemoptysis"),
    ("tuberculosis", "positive_ppd"), ("tuberculosis", "chest_infiltrate_xray"),
    ("copd_exacerbation", "dyspnea"), ("copd_exacerbation", "productive_cough"),
    ("copd_exacerbation", "wheezing"), ("copd_exacerbation", "cyanosis"),
    ("heart_failure", "dyspnea"), ("heart_failure", "orthopnea"), ("heart_failure", "leg_swelling"),
    ("heart_failure", "fatigue"), ("heart_failure", "tachycardia"),
    ("heart_failure", "elevated_bnp"), ("heart_failure", "cardiomegaly_xray"),
    ("heart_failure", "pulmonary_edema_ct"),
    ("myocardial_infarction", "substernal_chest_pain"), ("myocardial_infarction", "dyspnea"),
    ("myocardial_infarction", "tachycardia"), ("myocardial_infarction", "hypotension"),
    ("myocardial_infarction", "elevated_troponin"), ("myocardial_infarction", "coagulopathy"),
    ("aortic_dissection", "substernal_chest_pain"), ("aortic_dissection", "hypotension"),
    ("aortic_dissection", "tachycardia"), ("aortic_dissection", "confusion"),
    ("aortic_dissection", "aortic_dissection_ct"),
    ("pneumothorax", "sudden_onset_dyspnea"), ("pneumothorax", "pleuritic_chest_pain"),
    ("pneumothorax", "tachycardia"), ("pneumothorax", "hypoxemia"),
    ("pneumothorax", "pneumothorax_xray"),
    ("pleural_effusion", "dyspnea"), ("pleural_effusion", "pleuritic_chest_pain"),
    ("pleural_effusion", "cough"), ("pleural_effusion", "pleural_effusion_xray"),
    ("covid19", "fever"), ("covid19", "dry_cough"), ("covid19", "dyspnea"),
    ("covid19", "fatigue"), ("covid19", "confusion"), ("covid19", "hypoxemia"),
    ("covid19", "positive_pcr_covid"), ("covid19", "ground_glass_opacities_ct"),
    ("covid19", "elevated_crp"), ("covid19", "coagulopathy"),
    ("influenza", "fever"), ("influenza", "high_fever"), ("influenza", "dry_cough"),
    ("influenza", "fatigue"), ("influenza", "myalgia"),
    ("sepsis", "fever"), ("sepsis", "high_fever"), ("sepsis", "tachycardia"),
    ("sepsis", "hypotension"), ("sepsis", "confusion"), ("sepsis", "lactic_acidosis"),
    ("sepsis", "elevated_procalcitonin"), ("sepsis", "positive_blood_culture"),
]

RISK_FACTOR_EDGES = [
    ("age_over_65", "pneumonia"), ("smoking_history", "copd_exacerbation"),
    ("current_smoker", "lung_cancer"), ("immunosuppression", "pneumonia"),
    ("recent_surgery", "pulmonary_embolism"), ("prolonged_immobility", "pulmonary_embolism"),
    ("copd_history", "copd_exacerbation"), ("heart_disease_history", "heart_failure"),
    ("diabetes", "pneumonia"), ("malignancy_history", "sepsis"),
    ("recent_travel_endemic_tb", "tuberculosis"), ("obesity", "heart_failure"),
    ("hypertension", "myocardial_infarction"), ("asbestos_exposure", "lung_cancer"),
    ("age_over_65", "pneumothorax"), ("immunosuppression", "tuberculosis"),
    ("smoking_history", "lung_cancer"), ("copd_history", "pneumonia"),
    ("heart_disease_history", "myocardial_infarction"),
    ("obesity", "pulmonary_embolism"), ("diabetes", "sepsis"),
]

TREATS_EDGES = [
    ("amoxicillin", "pneumonia"), ("azithromycin", "pneumonia"),
    ("levofloxacin", "pneumonia"), ("ceftriaxone", "pneumonia"),
    ("azithromycin", "bronchitis"), ("oseltamivir", "influenza"),
    ("albuterol", "asthma_exacerbation"), ("prednisone", "asthma_exacerbation"),
    ("heparin", "pulmonary_embolism"), ("warfarin", "pulmonary_embolism"),
    ("furosemide", "heart_failure"), ("isoniazid", "tuberculosis"),
    ("rifampin", "tuberculosis"), ("morphine", "myocardial_infarction"),
    ("oxygen_therapy", "pneumonia"), ("metoprolol", "myocardial_infarction"),
]

CONFLICTS = [
    ("warfarin", "heparin", "conflicts_with"),
    ("morphine", "confusion", "worsens"),
]


def main() -> None:
    mem = CognitiveMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building Clinical Knowledge Graph")
    print("=" * 70)

    all_entities = {**DISEASES, **SYMPTOMS, **LAB_FINDINGS, **IMAGING, **RISK_FACTORS, **MEDICATIONS}
    for name, data in all_entities.items():
        mem.store(name, data=data)

    for src, tgt in CAUSES_EDGES:
        mem.relate(src, tgt, label="causes")
    for src, tgt in RISK_FACTOR_EDGES:
        mem.relate(src, tgt, label="increases_risk")
    for src, tgt in TREATS_EDGES:
        mem.relate(src, tgt, label="treats")
    for src, tgt, label in CONFLICTS:
        mem.relate(src, tgt, label=label)

    print(f"  Nodes: {mem.graph.node_count}")
    print(f"  Edges: {mem.graph.edge_count}")
    print(f"    causes:          {len(CAUSES_EDGES)}")
    print(f"    increases_risk:  {len(RISK_FACTOR_EDGES)}")
    print(f"    treats:          {len(TREATS_EDGES)}")
    print(f"    conflicts:       {len(CONFLICTS)}")
    print()

    print("=" * 70)
    print("SECTION 2: Backward Chaining - Proving a Diagnosis")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
        InverseRule(edge_label="causes", inverse_label="caused_by"),
    )
    mem.reason(
        seed_concepts=set(DISEASES.keys()) | set(SYMPTOMS.keys()),
        max_depth=3, max_total_states=80,
    )

    patient_findings = {"fever", "cough", "productive_cough", "dyspnea", "pleuritic_chest_pain", "tachycardia"}

    print(f"  Patient presents with: {', '.join(sorted(patient_findings))}")
    print()

    ddx = ["pneumonia", "pulmonary_embolism", "bronchitis", "pleural_effusion", "copd_exacerbation"]
    print(f"  Differential diagnosis workup ({len(ddx)} candidates):")
    print()

    scores: list[tuple[str, float, int, int]] = []
    for dx in ddx:
        result = mem.prove(dx, known_facts=patient_findings)
        scores.append((dx, result.confidence, result.satisfied_premises, result.total_premises_needed))
        status = "PROVEN" if result.achievable else "possible"
        print(f"    {dx:<28} conf={result.confidence:.2f}  "
              f"premises={result.satisfied_premises}/{result.total_premises_needed}  [{status}]")
        if result.missing_premises:
            print(f"      Missing evidence: {', '.join(result.missing_premises[:5])}")
    print()

    scores.sort(key=lambda x: x[1], reverse=True)
    print(f"  Ranked differential: {' > '.join(s[0] for s in scores)}")
    print()

    print("=" * 70)
    print("SECTION 3: Belief Revision - Contradictory Findings")
    print("=" * 70)

    mem.store("patient_ct_result", data={"finding": "chest_infiltrate_xray"})
    mem.relate("patient_ct_result", "pneumonia", label="supports")
    mem.store("negative_blood_culture", data={"finding": "no_bacteremia"})
    mem.relate("negative_blood_culture", "pneumonia", label="opposes")

    contradictions = mem.detect_contradictions()
    print(f"  Clinical contradictions detected: {len(contradictions)}")
    for c in contradictions[:5]:
        print(f"    {c['source']} -> {c['target']}: "
              f"{c['edge_a_label']} vs {c['edge_b_label']} (severity={c['severity']:.2f})")
    print()

    revision = mem.revise_beliefs(strategy="higher_weight")
    print(f"  Belief revision complete: {revision.contradictions_detected} contradictions, "
          f"{revision.edges_removed_count} edges removed")
    print()

    print("=" * 70)
    print("SECTION 4: Uncertainty Propagation")
    print("=" * 70)

    confidence_result = mem.compute_all_confidences()
    print(f"  Average confidence across graph: {confidence_result.avg_confidence:.3f}")
    print(f"  High confidence nodes (>0.8):    {confidence_result.high_confidence_count}")
    print(f"  Low confidence nodes (<0.3):     {confidence_result.low_confidence_count}")
    print()

    low_conf = mem.flag_low_confidence(threshold=0.5)
    print(f"  Nodes below confidence 0.5 ({len(low_conf)}):")
    for entry in low_conf[:8]:
        print(f"    {entry['node_label']:<30} conf={entry['confidence']:.3f}  depth={entry['depth']}")
    print()

    for dx in ["pneumonia", "pulmonary_embolism", "lung_cancer"]:
        conf = mem.compute_confidence(dx)
        if conf:
            print(f"  {dx:<28} confidence={conf['confidence']:.3f}  source={conf['source']}")
    print()

    print("=" * 70)
    print("SECTION 5: Structural Pattern Matching - Clinical Pathways")
    print("=" * 70)

    chains = mem.match_chains(edge_label="causes", min_length=3, max_length=6, max_chains=10)
    print(f"  Disease-to-symptom chains (length 3+): {len(chains)}")
    for chain in chains[:5]:
        print(f"    {' -> '.join(chain[:6])}")
    print()

    diamonds = mem.match_diamonds(edge_label="causes", max_matches=10)
    print(f"  Convergent symptom patterns (diamonds): {len(diamonds)}")
    for d in diamonds[:5]:
        print(f"    {d.get('source_a', '?')} + {d.get('source_b', '?')} -> {d.get('converge', '?')}  "
              f"score={d['score']:.3f}")
    print()

    fans = mem.match_fan_out(edge_label="causes", min_fan=5, max_results=5)
    print(f"  Diseases with most symptoms (fan-out >= 5):")
    for f in fans:
        print(f"    {f['node']:<28} fan_out={f['fan_out']}  "
              f"symptoms: {', '.join(f['targets'][:4])}...")
    print()

    print("=" * 70)
    print("SECTION 6: Treatment Pathway Discovery")
    print("=" * 70)

    treat_chains = mem.match_chains(edge_label="treats", min_length=1, max_length=2, max_chains=20)
    print(f"  Treatment edges found: {len(treat_chains)}")
    for chain in treat_chains[:8]:
        print(f"    {chain[0]} --[treats]--> {chain[1]}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Graph: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"  Top differential: {scores[0][0]} (confidence={scores[0][1]:.2f})")
    print(f"  Contradictions resolved: {revision.edges_removed_count}")
    print(f"  Low-confidence nodes flagged: {len(low_conf)}")
    print()
    print("  Key insight: backward chaining identifies missing evidence")
    print("  needed to confirm or rule out diagnoses, while belief revision")
    print("  automatically resolves contradictory clinical findings.")
    print()


if __name__ == "__main__":
    main()
