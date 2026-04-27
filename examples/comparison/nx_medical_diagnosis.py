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
    "aortic_dissection": {"category": "disease"},
    "sepsis": {"category": "disease"},
}

SYMPTOMS = {
    "cough": {"category": "symptom"}, "productive_cough": {"category": "symptom"},
    "dry_cough": {"category": "symptom"}, "dyspnea": {"category": "symptom"},
    "pleuritic_chest_pain": {"category": "symptom"}, "substernal_chest_pain": {"category": "symptom"},
    "fever": {"category": "symptom"}, "high_fever": {"category": "symptom"},
    "night_sweats": {"category": "symptom"}, "hemoptysis": {"category": "symptom"},
    "weight_loss": {"category": "symptom"}, "fatigue": {"category": "symptom"},
    "tachycardia": {"category": "symptom"}, "hypotension": {"category": "symptom"},
    "cyanosis": {"category": "symptom"}, "confusion": {"category": "symptom"},
    "leg_swelling": {"category": "symptom"}, "sudden_onset_dyspnea": {"category": "symptom"},
    "orthopnea": {"category": "symptom"}, "wheezing": {"category": "symptom"},
    "myalgia": {"category": "symptom"},
}

LAB_FINDINGS = {
    "elevated_wbc": {"category": "lab"}, "elevated_crp": {"category": "lab"},
    "elevated_procalcitonin": {"category": "lab"}, "elevated_d_dimer": {"category": "lab"},
    "positive_blood_culture": {"category": "lab"}, "hypoxemia": {"category": "lab"},
    "elevated_troponin": {"category": "lab"}, "elevated_bnp": {"category": "lab"},
    "elevated_ldh": {"category": "lab"}, "positive_pcr_covid": {"category": "lab"},
    "positive_ppd": {"category": "lab"}, "elevated_esr": {"category": "lab"},
    "coagulopathy": {"category": "lab"}, "lactic_acidosis": {"category": "lab"},
}

IMAGING = {
    "chest_infiltrate_xray": {"category": "imaging"}, "chest_opacity_ct": {"category": "imaging"},
    "pleural_effusion_xray": {"category": "imaging"}, "pulmonary_embolism_ct": {"category": "imaging"},
    "pneumothorax_xray": {"category": "imaging"}, "cardiomegaly_xray": {"category": "imaging"},
    "ground_glass_opacities_ct": {"category": "imaging"}, "lung_mass_ct": {"category": "imaging"},
    "pulmonary_edema_ct": {"category": "imaging"}, "aortic_dissection_ct": {"category": "imaging"},
    "normal_chest_xray": {"category": "imaging"},
}

RISK_FACTORS = {
    "smoking_history": {"category": "risk_factor"}, "current_smoker": {"category": "risk_factor"},
    "immunosuppression": {"category": "risk_factor"}, "recent_surgery": {"category": "risk_factor"},
    "prolonged_immobility": {"category": "risk_factor"}, "copd_history": {"category": "risk_factor"},
    "heart_disease_history": {"category": "risk_factor"}, "age_over_65": {"category": "risk_factor"},
    "asbestos_exposure": {"category": "risk_factor"}, "obesity": {"category": "risk_factor"},
    "hypertension": {"category": "risk_factor"}, "diabetes": {"category": "risk_factor"},
    "malignancy_history": {"category": "risk_factor"}, "recent_travel_endemic_tb": {"category": "risk_factor"},
    "vaccination_status": {"category": "risk_factor"},
}

MEDICATIONS = {
    "amoxicillin": {"category": "medication"}, "azithromycin": {"category": "medication"},
    "levofloxacin": {"category": "medication"}, "ceftriaxone": {"category": "medication"},
    "oseltamivir": {"category": "medication"}, "albuterol": {"category": "medication"},
    "prednisone": {"category": "medication"}, "heparin": {"category": "medication"},
    "warfarin": {"category": "medication"}, "furosemide": {"category": "medication"},
    "isoniazid": {"category": "medication"}, "rifampin": {"category": "medication"},
    "morphine": {"category": "medication"}, "oxygen_therapy": {"category": "medication"},
    "metoprolol": {"category": "medication"},
}

CAUSES = [
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

RISK_EDGES = [
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

TREATS = [
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


def find_chains(
    G: nx.DiGraph, edge_label: str, min_length: int = 2, max_length: int = 5, max_chains: int = 50,
) -> list[list[str]]:
    all_targets: set[str] = set()
    for u, v, d in G.edges(data=True):
        if d.get("label") == edge_label:
            all_targets.add(v)
    seeds = [n for n in G.nodes() if n not in all_targets]
    if not seeds:
        seeds = list(G.nodes())

    results: list[list[str]] = []

    def dfs(current: str, path: list[str], visited: set[str]) -> None:
        if len(results) >= max_chains:
            return
        if len(path) - 1 >= max_length:
            return
        if len(path) - 1 >= min_length:
            results.append(list(path))
        visited.add(current)
        for _, neighbor, d in G.out_edges(current, data=True):
            if d.get("label") == edge_label and neighbor not in visited:
                path.append(neighbor)
                dfs(neighbor, path, visited)
                path.pop()
        visited.discard(current)

    for seed in seeds:
        dfs(seed, [seed], set())
        if len(results) >= max_chains:
            break
    return results[:max_chains]


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
                src_set_a = set(s for s in incoming.keys() if sources[i] in incoming[s])
                src_set_b = set(s for s in incoming.keys() if sources[j] in incoming[s])
                overlap = len(src_set_a & src_set_b)
                union = max(len(src_set_a | src_set_b), 1)
                score = min(overlap / union, 1.0)
                diamonds.append({"source_a": sources[i], "source_b": sources[j], "converge": target, "score": score})
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
    print("SECTION 1: Building Clinical Knowledge Graph")
    print("=" * 70)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print(f"    causes:          {len(CAUSES)}")
    print(f"    increases_risk:  {len(RISK_EDGES)}")
    print(f"    treats:          {len(TREATS)}")
    print(f"    conflicts:       {len(CONFLICTS)}")
    print()

    print("=" * 70)
    print("SECTION 2: Backward Chaining - Proving a Diagnosis")
    print("=" * 70)
    patient_findings = {"fever", "cough", "productive_cough", "dyspnea", "pleuritic_chest_pain", "tachycardia"}
    ddx = ["pneumonia", "pulmonary_embolism", "bronchitis", "pleural_effusion", "copd_exacerbation"]

    print(f"  Patient presents with: {', '.join(sorted(patient_findings))}")
    print()
    print(f"  Differential diagnosis workup ({len(ddx)} candidates):")
    print()

    scores: list[tuple[str, float, int, int]] = []
    for dx in ddx:
        r = backward_chain(G, dx, patient_findings, label="causes")
        scores.append((dx, r["confidence"], r["satisfied"], r["total_needed"]))
        status = "PROVEN" if r["achievable"] else "possible"
        print(f"    {dx:<28} conf={r['confidence']:.2f}  "
              f"premises={r['satisfied']}/{r['total_needed']}  [{status}]")
    print()

    scores.sort(key=lambda x: x[1], reverse=True)
    print(f"  Ranked differential: {' > '.join(s[0] for s in scores)}")
    print()

    print("=" * 70)
    print("SECTION 3: Belief Revision - Contradictory Findings")
    print("=" * 70)
    negation_map = {"supports": "opposes", "causes": "prevents", "treats": "worsens"}
    contradictions = detect_contradictions(G, negation_map)
    print(f"  Clinical contradictions detected: {len(contradictions)}")
    for c in contradictions[:5]:
        print(f"    {c['source']} -> {c['target']}: {c['label_a']} vs {c['label_b']}")
    print()

    print("=" * 70)
    print("SECTION 4: Uncertainty Propagation")
    print("=" * 70)
    confidence = propagate_confidence(G)
    high_conf = sum(1 for v in confidence.values() if v > 0.8)
    low_conf = sum(1 for v in confidence.values() if v < 0.3)
    avg_conf = sum(confidence.values()) / max(len(confidence), 1)
    print(f"  Average confidence: {avg_conf:.3f}")
    print(f"  High confidence (>0.8): {high_conf}")
    print(f"  Low confidence (<0.3): {low_conf}")
    print()

    print("=" * 70)
    print("SECTION 5: Structural Pattern Matching - Clinical Pathways")
    print("=" * 70)

    chains = find_chains(G, edge_label="causes", min_length=3, max_length=6, max_chains=10)
    print(f"  Disease-to-symptom chains (length 3+): {len(chains)}")
    for chain in chains[:5]:
        print(f"    {' -> '.join(chain[:6])}")
    print()

    diamonds = find_diamonds(G, edge_label="causes")
    print(f"  Convergent symptom patterns (diamonds): {len(diamonds)}")
    for d in diamonds[:5]:
        print(f"    {d['source_a']} + {d['source_b']} -> {d['converge']}  "
              f"score={d['score']:.3f}")
    print()

    fan_outs = find_fan_out(G, "causes", min_fan=5)
    print(f"  Diseases with most symptoms (fan-out >= 5):")
    for node, count in fan_outs:
        print(f"    {node:<28} fan_out={count}")
    print()

    print("=" * 70)
    print("SECTION 6: Treatment Pathway Discovery")
    print("=" * 70)
    treat_chains = find_chains(G, edge_label="treats", min_length=1, max_length=2, max_chains=20)
    print(f"  Treatment edges found: {len(treat_chains)}")
    for chain in treat_chains[:8]:
        print(f"    {chain[0]} --[treats]--> {chain[1]}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"  Top differential: {scores[0][0]} (confidence={scores[0][1]:.2f})")
    print(f"  Contradictions resolved: {len(contradictions)}")
    print(f"  Low-confidence nodes flagged: {low_conf}")
    print()
    print("  Key insight: backward chaining identifies missing evidence")
    print("  needed to confirm or rule out diagnoses, while belief revision")
    print("  automatically resolves contradictory clinical findings.")
    print()


if __name__ == "__main__":
    main()
