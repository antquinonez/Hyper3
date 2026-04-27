"""
NetworkX-only equivalent of Hyper3's medical_diagnosis.py
==========================================================
Implements backward chaining, belief revision with negation map,
uncertainty/confidence propagation, and structural pattern matching
using pure NetworkX.
"""

from __future__ import annotations

import networkx as nx
from collections import defaultdict


DISEASES = {
    "pneumonia": {"category": "disease"},
    "bronchitis": {"category": "disease"},
    "asthma_exacerbation": {"category": "disease"},
    "pulmonary_embolism": {"category": "disease"},
    "lung_cancer": {"category": "disease"},
    "copd_exacerbation": {"category": "disease"},
    "pleural_effusion": {"category": "disease"},
    "myocardial_infarction": {"category": "disease"},
    "influenza": {"category": "disease"},
    "covid19": {"category": "disease"},
    "tuberculosis": {"category": "disease"},
    "pneumothorax": {"category": "disease"},
    "heart_failure": {"category": "disease"},
    "anemia": {"category": "disease"},
}

SYMPTOMS = {
    "cough": {"category": "symptom"}, "productive_cough": {"category": "symptom"},
    "dry_cough": {"category": "symptom"}, "dyspnea": {"category": "symptom"},
    "pleuritic_chest_pain": {"category": "symptom"}, "fever": {"category": "symptom"},
    "high_fever": {"category": "symptom"}, "night_sweats": {"category": "symptom"},
    "hemoptysis": {"category": "symptom"}, "weight_loss": {"category": "symptom"},
    "fatigue": {"category": "symptom"}, "tachycardia": {"category": "symptom"},
    "hypotension": {"category": "symptom"}, "cyanosis": {"category": "symptom"},
    "confusion": {"category": "symptom"}, "leg_swelling": {"category": "symptom"},
    "sudden_onset_dyspnea": {"category": "symptom"}, "orthopnea": {"category": "symptom"},
    "wheezing": {"category": "symptom"}, "myalgia": {"category": "symptom"},
}

LAB_FINDINGS = {
    "elevated_wbc": {"category": "lab"}, "elevated_crp": {"category": "lab"},
    "elevated_procalcitonin": {"category": "lab"}, "elevated_d_dimer": {"category": "lab"},
    "positive_blood_culture": {"category": "lab"}, "hypoxemia": {"category": "lab"},
    "anemia_labs": {"category": "lab"}, "elevated_troponin": {"category": "lab"},
    "elevated_bnp": {"category": "lab"},
}

IMAGING = {
    "chest_infiltrate": {"category": "imaging"}, "pleural_effusion_ct": {"category": "imaging"},
    "pulmonary_embolism_ct": {"category": "imaging"}, "cardiomegaly_xray": {"category": "imaging"},
    "pneumothorax_xray": {"category": "imaging"}, "lung_mass_ct": {"category": "imaging"},
}

RISK_FACTORS = {
    "smoking": {"category": "risk_factor"}, "immunosuppression": {"category": "risk_factor"},
    "recent_surgery": {"category": "risk_factor"}, "prolonged_immobility": {"category": "risk_factor"},
    "copd_history": {"category": "risk_factor"}, "age_over_65": {"category": "risk_factor"},
    "asbestos_exposure": {"category": "risk_factor"}, "obesity": {"category": "risk_factor"},
    "htn": {"category": "risk_factor"}, "diabetes": {"category": "risk_factor"},
}

MEDICATIONS = {
    "amoxicillin": {"category": "medication"}, "azithromycin": {"category": "medication"},
    "levofloxacin": {"category": "medication"}, "ceftriaxone": {"category": "medication"},
    "oseltamivir": {"category": "medication"}, "albuterol": {"category": "medication"},
    "prednisone": {"category": "medication"}, "heparin": {"category": "medication"},
    "warfarin": {"category": "medication"}, "doxorubicin": {"category": "medication"},
    "morphine": {"category": "medication"}, "furosemide": {"category": "medication"},
    "metoprolol": {"category": "medication"},
}

CAUSES = [
    ("pneumonia", "productive_cough"), ("pneumonia", "fever"), ("pneumonia", "dyspnea"),
    ("pneumonia", "tachycardia"), ("pneumonia", "pleuritic_chest_pain"), ("pneumonia", "hypoxemia"),
    ("pneumonia", "elevated_wbc"), ("pneumonia", "elevated_crp"), ("pneumonia", "elevated_procalcitonin"),
    ("pneumonia", "chest_infiltrate"), ("pneumonia", "cyanosis"), ("pneumonia", "confusion"),
    ("bronchitis", "cough"), ("bronchitis", "productive_cough"), ("bronchitis", "dyspnea"),
    ("bronchitis", "wheezing"), ("bronchitis", "fever"), ("bronchitis", "fatigue"),
    ("asthma_exacerbation", "wheezing"), ("asthma_exacerbation", "dyspnea"),
    ("asthma_exacerbation", "cough"), ("asthma_exacerbation", "tachycardia"),
    ("asthma_exacerbation", "hypoxemia"),
    ("pulmonary_embolism", "sudden_onset_dyspnea"), ("pulmonary_embolism", "pleuritic_chest_pain"),
    ("pulmonary_embolism", "tachycardia"), ("pulmonary_embolism", "hypoxemia"),
    ("pulmonary_embolism", "elevated_d_dimer"), ("pulmonary_embolism", "pulmonary_embolism_ct"),
    ("lung_cancer", "cough"), ("lung_cancer", "dyspnea"), ("lung_cancer", "weight_loss"),
    ("lung_cancer", "hemoptysis"), ("lung_cancer", "chest_infiltrate"),
    ("lung_cancer", "lung_mass_ct"), ("lung_cancer", "fatigue"),
    ("copd_exacerbation", "dyspnea"), ("copd_exacerbation", "productive_cough"),
    ("copd_exacerbation", "wheezing"), ("copd_exacerbation", "cyanosis"),
    ("copd_exacerbation", "tachycardia"),
    ("pleural_effusion", "dyspnea"), ("pleural_effusion", "pleuritic_chest_pain"),
    ("pleural_effusion", "pleural_effusion_ct"),
    ("myocardial_infarction", "substernal_chest_pain"), ("myocardial_infarction", "dyspnea"),
    ("myocardial_infarction", "tachycardia"), ("myocardial_infarction", "hypotension"),
    ("myocardial_infarction", "elevated_troponin"),
    ("influenza", "fever"), ("influenza", "high_fever"), ("influenza", "myalgia"),
    ("influenza", "fatigue"), ("influenza", "cough"),
    ("covid19", "fever"), ("covid19", "cough"), ("covid19", "dyspnea"),
    ("covid19", "hypoxemia"), ("covid19", "loss_of_taste") if False else ("covid19", "fatigue"),
    ("tuberculosis", "night_sweats"), ("tuberculosis", "weight_loss"),
    ("tuberculosis", "cough"), ("tuberculosis", "hemoptysis"), ("tuberculosis", "fever"),
    ("pneumothorax", "sudden_onset_dyspnea"), ("pneumothorax", "pleuritic_chest_pain"),
    ("pneumothorax", "pneumothorax_xray"),
    ("heart_failure", "orthopnea"), ("heart_failure", "leg_swelling"),
    ("heart_failure", "dyspnea"), ("heart_failure", "tachycardia"),
    ("heart_failure", "elevated_bnp"), ("heart_failure", "cardiomegaly_xray"),
    ("anemia", "fatigue"), ("anemia", "dyspnea"), ("anemia", "tachycardia"),
    ("anemia", "anemia_labs"),
]

RISK_EDGES = [
    ("smoking", "copd_exacerbation"), ("smoking", "lung_cancer"),
    ("immunosuppression", "pneumonia"), ("recent_surgery", "pulmonary_embolism"),
    ("prolonged_immobility", "pulmonary_embolism"), ("copd_history", "copd_exacerbation"),
    ("age_over_65", "pneumonia"), ("asbestos_exposure", "lung_cancer"),
    ("obesity", "heart_failure"), ("htn", "myocardial_infarction"),
    ("diabetes", "pneumonia"), ("smoking", "pneumonia"),
    ("age_over_65", "myocardial_infarction"), ("htn", "heart_failure"),
    ("obesity", "pneumonia"), ("diabetes", "heart_failure"),
    ("smoking", "bronchitis"), ("copd_history", "bronchitis"),
    ("recent_surgery", "pneumonia"), ("immunosuppression", "tuberculosis"),
    ("diabetes", "tuberculosis"),
]

TREATS = [
    ("amoxicillin", "pneumonia"), ("azithromycin", "bronchitis"),
    ("azithromycin", "pneumonia"), ("levofloxacin", "pneumonia"),
    ("ceftriaxone", "pneumonia"), ("oseltamivir", "influenza"),
    ("albuterol", "asthma_exacerbation"), ("prednisone", "asthma_exacerbation"),
    ("heparin", "pulmonary_embolism"), ("warfarin", "pulmonary_embolism"),
    ("doxorubicin", "lung_cancer"), ("morphine", "pleuritic_chest_pain"),
    ("furosemide", "heart_failure"), ("metoprolol", "myocardial_infarction"),
    ("metoprolol", "heart_failure"), ("ceftriaxone", "tuberculosis"),
]

CONFLICTS = [
    ("warfarin", "doxorubicin", "conflicts_with"),
    ("heparin", "warfarin", "overlapping_mechanism"),
]


def backward_chain(G: nx.DiGraph, target: str, known: set[str], label: str = "causes") -> dict:
    premises_needed: set[str] = set()
    premises_satisfied: set[str] = set()
    proof_depth = 0

    stack = [target]
    visited: set[str] = set()

    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        predecessors = [(u, v, d) for u, v, d in G.in_edges(current, data=True) if d.get("label") == label]
        if predecessors:
            proof_depth += 1
            for u, _, _ in predecessors:
                premises_needed.add(u)
                if u in known or G.nodes[u].get("category") in ("symptom", "lab", "imaging"):
                    premises_satisfied.add(u)
                else:
                    stack.append(u)
        elif current in known:
            premises_satisfied.add(current)

    total = max(len(premises_needed), 1)
    confidence = len(premises_satisfied) / total
    return {
        "achievable": len(premises_satisfied) > 0,
        "confidence": confidence,
        "satisfied": len(premises_satisfied),
        "total_needed": len(premises_needed),
        "depth": proof_depth,
    }


def detect_contradictions(G: nx.DiGraph, negation_map: dict[str, str]) -> list[dict]:
    edge_by_pair: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for u, v, d in G.edges(data=True):
        label = d.get("label", "")
        edge_by_pair[(u, v)].append((u, v, label))

    contradictions: list[dict] = []
    for (u, v), edges in edge_by_pair.items():
        labels = [e[2] for e in edges]
        for i, la in enumerate(labels):
            for lb in labels[i + 1:]:
                if la == lb:
                    continue
                if negation_map.get(la) == lb or negation_map.get(lb) == la:
                    contradictions.append({"source": u, "target": v, "label_a": la, "label_b": lb})
    return contradictions


def propagate_confidence(G: nx.DiGraph) -> dict[str, float]:
    confidence: dict[str, float] = {}
    categories = {n: d.get("category", "") for n, d in G.nodes(data=True)}

    for node in G.nodes():
        cat = categories[node]
        if cat in ("symptom", "lab", "imaging", "risk_factor"):
            confidence[node] = 1.0
        elif cat == "disease":
            causes_in = [(u, d) for u, v, d in G.in_edges(node, data=True) if d.get("label") == "causes"]
            if not causes_in:
                confidence[node] = 0.5
            else:
                max_conf = 0.0
                for u, d in causes_in:
                    c = confidence.get(u, 0.5)
                    if d.get("confidence"):
                        c *= d["confidence"]
                    max_conf = max(max_conf, c * 0.9)
                confidence[node] = max_conf
        else:
            confidence[node] = 0.7

    return confidence


def find_diamonds(G: nx.DiGraph, edge_label: str | None = None) -> list[dict]:
    incoming: dict[str, list[str]] = defaultdict(list)
    for u, v, d in G.edges(data=True):
        if edge_label is None or d.get("label") == edge_label:
            incoming[v].append(u)

    diamonds: list[dict] = []
    seen: set[frozenset[str]] = set()
    for target, sources in incoming.items():
        if len(sources) < 2:
            continue
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                pair = frozenset([sources[i], sources[j]])
                if pair in seen:
                    continue
                seen.add(pair)
                diamonds.append({"source_a": sources[i], "source_b": sources[j], "converge": target})
    return diamonds[:10]


def find_fan_out(G: nx.DiGraph, edge_label: str, min_fan: int = 3) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    for node in G.nodes():
        count = sum(1 for _, _, d in G.out_edges(node, data=True) if d.get("label") == edge_label)
        if count >= min_fan:
            result.append((node, count))
    result.sort(key=lambda x: -x[1])
    return result


def main() -> None:
    G = nx.DiGraph()

    all_entities = {**DISEASES, **SYMPTOMS, **LAB_FINDINGS, **IMAGING, **RISK_FACTORS, **MEDICATIONS}
    for name, data in all_entities.items():
        G.add_node(name, **data)

    for src, tgt in CAUSES:
        G.add_edge(src, tgt, label="causes", weight=1.0)
    for src, tgt in RISK_EDGES:
        G.add_edge(src, tgt, label="increases_risk", weight=1.0)
    for src, tgt in TREATS:
        G.add_edge(src, tgt, label="treats", weight=1.0)
    for src, tgt, label in CONFLICTS:
        G.add_edge(src, tgt, label=label, weight=1.0)

    print("=" * 70)
    print("NetworkX: Medical Diagnosis")
    print("=" * 70)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print()

    print("SECTION 2: Backward Chaining")
    patient_findings = {"fever", "cough", "productive_cough", "dyspnea", "pleuritic_chest_pain", "tachycardia"}
    ddx = ["pneumonia", "pulmonary_embolism", "bronchitis", "pleural_effusion", "copd_exacerbation"]
    print(f"  Patient findings: {', '.join(sorted(patient_findings))}")
    print()

    for dx in ddx:
        r = backward_chain(G, dx, patient_findings, label="causes")
        print(f"    {dx:<28} conf={r['confidence']:.2f}  premises={r['satisfied']}/{r['total_needed']}")
    print()

    print("SECTION 3: Belief Revision")
    negation_map = {"supports": "opposes", "causes": "prevents", "treats": "worsens"}
    contradictions = detect_contradictions(G, negation_map)
    print(f"  Contradictions found: {len(contradictions)}")
    for c in contradictions:
        print(f"    {c['source']} -> {c['target']}: {c['label_a']} vs {c['label_b']}")
    print()

    print("SECTION 4: Uncertainty Propagation")
    confidence = propagate_confidence(G)
    high_conf = sum(1 for v in confidence.values() if v > 0.8)
    low_conf = sum(1 for v in confidence.values() if v < 0.3)
    avg_conf = sum(confidence.values()) / max(len(confidence), 1)
    print(f"  Average confidence: {avg_conf:.3f}")
    print(f"  High confidence (>0.8): {high_conf}")
    print(f"  Low confidence (<0.3): {low_conf}")
    print()

    print("SECTION 5: Structural Patterns")
    diamonds = find_diamonds(G, edge_label="causes")
    print(f"  Convergent symptom patterns (diamonds): {len(diamonds)}")
    for d in diamonds[:5]:
        print(f"    {d['source_a']} + {d['source_b']} -> {d['converge']}")

    fan_outs = find_fan_out(G, "causes", min_fan=5)
    print(f"  Diseases with most symptoms (fan-out >= 5):")
    for node, count in fan_outs:
        print(f"    {node:<28} fan_out={count}")
    print()

    print("SECTION 6: Treatment Pathway Discovery")
    treatments = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("label") == "treats"]
    print(f"  Treatment edges: {len(treatments)}")
    for u, v, _ in treatments[:8]:
        print(f"    {u} -> {v}")
    print()


if __name__ == "__main__":
    main()
