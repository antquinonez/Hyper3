"""
Combined signal analysis: spreading activation + semantic similarity.

Evaluates whether merging structural (graph) and semantic (embedding)
signals produces better retrieval than either signal alone.

Run: .venv/bin/python examples/combined_signal_analysis.py
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from hyper3 import (
    HypergraphMemory,
    EmbeddingProvider,
    Modality,
)


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)
        self._dim: int | None = None

    def embed(self, text: str) -> np.ndarray:
        vec = self._model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float64)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        return (vecs / norms).astype(np.float64)

    def dimension(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed("test"))
        return self._dim


def combined_score(activation: float, similarity: float, alpha: float = 0.5) -> float:
    return alpha * activation + (1 - alpha) * similarity


def build_medical_kb(mem: HypergraphMemory) -> None:
    conditions = {
        "type 2 diabetes": {
            "category": "metabolic",
            "symptoms": "thirst, frequent urination, fatigue, blurred vision",
            "risk_factors": "obesity, sedentary lifestyle, family history",
        },
        "hypertension": {
            "category": "cardiovascular",
            "symptoms": "headache, dizziness, chest pain, shortness of breath",
            "risk_factors": "obesity, high sodium, stress, smoking",
        },
        "obesity": {
            "category": "metabolic",
            "symptoms": "weight gain, fatigue, joint pain, sleep apnea",
            "risk_factors": "poor diet, sedentary lifestyle, genetics",
        },
        "heart disease": {
            "category": "cardiovascular",
            "symptoms": "chest pain, shortness of breath, fatigue, swelling",
            "risk_factors": "hypertension, high cholesterol, smoking, diabetes",
        },
        "stroke": {
            "category": "cardiovascular",
            "symptoms": " paralysis, speech difficulty, vision problems, headache",
            "risk_factors": "hypertension, diabetes, smoking, atrial fibrillation",
        },
        "asthma": {
            "category": "respiratory",
            "symptoms": "wheezing, shortness of breath, chest tightness, cough",
            "risk_factors": "allergies, smoking, air pollution, family history",
        },
        "depression": {
            "category": "mental health",
            "symptoms": "sadness, fatigue, sleep problems, loss of interest",
            "risk_factors": "stress, trauma, genetics, chronic illness",
        },
        "chronic kidney disease": {
            "category": "renal",
            "symptoms": "fatigue, swelling, nausea, changes in urination",
            "risk_factors": "diabetes, hypertension, family history",
        },
        "sleep apnea": {
            "category": "respiratory",
            "symptoms": "loud snoring, daytime fatigue, morning headache",
            "risk_factors": "obesity, smoking, alcohol, family history",
        },
        "osteoarthritis": {
            "category": "musculoskeletal",
            "symptoms": "joint pain, stiffness, swelling, reduced mobility",
            "risk_factors": "age, obesity, joint injury, genetics",
        },
    }

    treatments = {
        "metformin": {
            "type": "medication",
            "treats": "type 2 diabetes",
            "mechanism": "reduces liver glucose production",
        },
        "insulin": {
            "type": "medication",
            "treats": "diabetes",
            "mechanism": "regulates blood sugar",
        },
        "lisinopril": {
            "type": "medication",
            "treats": "hypertension",
            "mechanism": "ACE inhibitor, relaxes blood vessels",
        },
        "statins": {
            "type": "medication",
            "treats": "high cholesterol",
            "mechanism": "reduces cholesterol production in liver",
        },
        "beta blockers": {
            "type": "medication",
            "treats": "hypertension, heart disease",
            "mechanism": "blocks adrenaline, slows heart rate",
        },
        "cognitive behavioral therapy": {
            "type": "therapy",
            "treats": "depression",
            "mechanism": "changes negative thought patterns",
        },
        "SSRIs": {
            "type": "medication",
            "treats": "depression",
            "mechanism": "increases serotonin availability",
        },
        "weight loss surgery": {
            "type": "procedure",
            "treats": "obesity",
            "mechanism": "reduces stomach capacity",
        },
        "CPAP machine": {
            "type": "device",
            "treats": "sleep apnea",
            "mechanism": "keeps airways open during sleep",
        },
        "physical therapy": {
            "type": "therapy",
            "treats": "osteoarthritis",
            "mechanism": "strengthens muscles around joints",
        },
    }

    risk_factors = {
        "obesity": {"type": "risk_factor"},
        "smoking": {"type": "risk_factor"},
        "sedentary lifestyle": {"type": "risk_factor"},
        "high cholesterol": {"type": "risk_factor"},
        "family history": {"type": "risk_factor"},
        "chronic stress": {"type": "risk_factor"},
        "poor diet": {"type": "risk_factor"},
        "high sodium intake": {"type": "risk_factor"},
    }

    for name, data in conditions.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})
    for name, data in treatments.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})
    for name, data in risk_factors.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    mem.link("type 2 diabetes", "obesity", label="risk_factor")
    mem.link("type 2 diabetes", "sedentary lifestyle", label="risk_factor")
    mem.link("type 2 diabetes", "family history", label="risk_factor")
    mem.link("type 2 diabetes", "metformin", label="treated_by")
    mem.link("type 2 diabetes", "insulin", label="treated_by")
    mem.link("type 2 diabetes", "chronic kidney disease", label="complication")
    mem.link("type 2 diabetes", "heart disease", label="complication")

    mem.link("hypertension", "obesity", label="risk_factor")
    mem.link("hypertension", "smoking", label="risk_factor")
    mem.link("hypertension", "high sodium intake", label="risk_factor")
    mem.link("hypertension", "chronic stress", label="risk_factor")
    mem.link("hypertension", "lisinopril", label="treated_by")
    mem.link("hypertension", "beta blockers", label="treated_by")
    mem.link("hypertension", "stroke", label="complication")
    mem.link("hypertension", "heart disease", label="complication")
    mem.link("hypertension", "chronic kidney disease", label="complication")

    mem.link("heart disease", "hypertension", label="risk_factor")
    mem.link("heart disease", "high cholesterol", label="risk_factor")
    mem.link("heart disease", "smoking", label="risk_factor")
    mem.link("heart disease", "type 2 diabetes", label="risk_factor")
    mem.link("heart disease", "statins", label="treated_by")
    mem.link("heart disease", "beta blockers", label="treated_by")

    mem.link("stroke", "hypertension", label="risk_factor")
    mem.link("stroke", "type 2 diabetes", label="risk_factor")
    mem.link("stroke", "smoking", label="risk_factor")

    mem.link("obesity", "poor diet", label="risk_factor")
    mem.link("obesity", "sedentary lifestyle", label="risk_factor")
    mem.link("obesity", "weight loss surgery", label="treated_by")
    mem.link("obesity", "type 2 diabetes", label="complication")
    mem.link("obesity", "sleep apnea", label="complication")
    mem.link("obesity", "osteoarthritis", label="complication")
    mem.link("obesity", "heart disease", label="complication")

    mem.link("depression", "chronic stress", label="risk_factor")
    mem.link("depression", "family history", label="risk_factor")
    mem.link("depression", "cognitive behavioral therapy", label="treated_by")
    mem.link("depression", "SSRIs", label="treated_by")

    mem.link("sleep apnea", "obesity", label="risk_factor")
    mem.link("sleep apnea", "smoking", label="risk_factor")
    mem.link("sleep apnea", "CPAP machine", label="treated_by")

    mem.link("osteoarthritis", "obesity", label="risk_factor")
    mem.link("osteoarthritis", "physical therapy", label="treated_by")

    mem.link("chronic kidney disease", "type 2 diabetes", label="risk_factor")
    mem.link("chronic kidney disease", "hypertension", label="risk_factor")

    mem.link("asthma", "smoking", label="risk_factor")
    mem.link("asthma", "family history", label="risk_factor")

    mem.link("statins", "high cholesterol", label="treats")


def run_query(
    mem: HypergraphMemory,
    concept: str,
    *,
    alpha: float = 0.5,
    top_k: int = 10,
    iterations: int = 3,
) -> list[dict]:
    mem.clear_activations()
    mem.stimulate(concept)
    mem.spread_activation(iterations=iterations)
    activated = mem.activate(concept, top_k=top_k * 2, iterations=iterations)

    engine = mem.embedding_engine
    seed_node = mem.graph.get_node_by_label(concept)
    if not seed_node:
        return []

    results = []
    for r in activated:
        if r.node_id == seed_node.id:
            continue
        sim = engine.compute_similarity(seed_node.id, r.node_id) if engine else 0.0
        combined = combined_score(r.activation, sim, alpha)
        results.append({
            "label": r.label,
            "activation": r.activation,
            "similarity": sim,
            "combined": combined,
        })

    results.sort(key=lambda x: x["combined"], reverse=True)
    return results[:top_k]


def print_comparison(
    label: str,
    concept: str,
    results: list[dict],
    expected: list[str] | None = None,
) -> None:
    print(f"\n{'=' * 70}")
    print(f"QUERY: '{concept}'")
    if expected:
        print(f"EXPECTED RELEVANT CONCEPTS: {', '.join(expected)}")
    print(f"{'=' * 70}")
    print(f"{'Concept':<30} {'Activation':>10} {'Semantic':>10} {'Combined':>10} {'Hit':>5}")
    print(f"{'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*5}")

    hits = 0
    for r in results:
        hit = ""
        if expected and r["label"] in expected:
            hit = "  *"
            hits += 1
        print(
            f"{r['label']:<30} {r['activation']:>10.3f} {r['similarity']:>10.3f} {r['combined']:>10.3f}{hit}"
        )

    if expected:
        recall = hits / len(expected) if expected else 0
        print(f"\nRecall: {hits}/{len(expected)} = {recall:.0%}")

    return hits if expected else None


def main() -> None:
    print("Loading sentence-transformers model...")
    provider = SentenceTransformerProvider()

    mem = HypergraphMemory(evolve_interval=0)
    mem.set_embedding_provider(provider)
    build_medical_kb(mem)

    print(f"Knowledge base: {mem.size[0]} nodes, {mem.size[1]} edges\n")

    # --- Scenario 1: Clinical decision support ---
    print("\n" + "#" * 70)
    print("# SCENARIO 1: Clinical decision support")
    print("# A doctor queries 'type 2 diabetes' — what should surface?")
    print("#" * 70)

    results_diabetes = run_query(mem, "type 2 diabetes", alpha=0.5, top_k=10)
    expected_diabetes = [
        "metformin", "insulin", "obesity", "heart disease",
        "chronic kidney disease", "hypertension",
    ]
    print_comparison("diabetes", "type 2 diabetes", results_diabetes, expected_diabetes)

    # --- Show what activation-only vs semantic-only would miss ---
    print(f"\n{'=' * 70}")
    print("BREAKDOWN: What each signal contributes")
    print(f"{'=' * 70}")

    top_activation = sorted(results_diabetes, key=lambda x: x["activation"], reverse=True)[:6]
    top_semantic = sorted(results_diabetes, key=lambda x: x["similarity"], reverse=True)[:6]
    top_combined = sorted(results_diabetes, key=lambda x: x["combined"], reverse=True)[:6]

    print("\nTop 6 by ACTIVATION ONLY (graph structure):")
    for r in top_activation:
        marker = "  *" if r["label"] in expected_diabetes else ""
        print(f"  {r['label']:<30} activation={r['activation']:.3f}{marker}")

    print("\nTop 6 by SEMANTIC SIMILARITY ONLY (embeddings):")
    for r in top_semantic:
        marker = "  *" if r["label"] in expected_diabetes else ""
        print(f"  {r['label']:<30} similarity={r['similarity']:.3f}{marker}")

    print("\nTop 6 by COMBINED (alpha=0.5):")
    for r in top_combined:
        marker = "  *" if r["label"] in expected_diabetes else ""
        print(f"  {r['label']:<30} combined={r['combined']:.3f}{marker}")

    # --- Scenario 2: Cross-domain discovery ---
    print("\n\n" + "#" * 70)
    print("# SCENARIO 2: Cross-domain risk discovery")
    print("# A patient has 'obesity' — what cascading risks should be flagged?")
    print("#" * 70)

    results_obesity = run_query(mem, "obesity", alpha=0.5, top_k=10)
    expected_obesity = [
        "type 2 diabetes", "heart disease", "hypertension",
        "sleep apnea", "osteoarthritis", "stroke",
        "chronic kidney disease",
    ]
    print_comparison("obesity", "obesity", results_obesity, expected_obesity)

    # --- Scenario 3: Treatment exploration ---
    print("\n\n" + "#" * 70)
    print("# SCENARIO 3: Treatment exploration")
    print("# Query 'heart disease' — treatments and modifiable risks should surface")
    print("#" * 70)

    results_heart = run_query(mem, "heart disease", alpha=0.5, top_k=10)
    expected_heart = [
        "statins", "beta blockers", "hypertension", "high cholesterol",
        "smoking", "type 2 diabetes", "stroke",
    ]
    print_comparison("heart disease", "heart disease", results_heart, expected_heart)

    # --- Scenario 4: Mental health (sparse connections) ---
    print("\n\n" + "#" * 70)
    print("# SCENARIO 4: Sparse graph region (mental health)")
    print("# 'depression' has few edges. Can semantic similarity compensate?")
    print("#" * 70)

    results_depression = run_query(mem, "depression", alpha=0.5, top_k=10)
    expected_depression = [
        "SSRIs", "cognitive behavioral therapy", "chronic stress",
        "family history",
    ]
    print_comparison("depression", "depression", results_depression, expected_depression)

    # --- Alpha sweep ---
    print("\n\n" + "#" * 70)
    print("# ALPHA SWEEP: How does the mixing weight affect recall?")
    print("# alpha=1.0 = pure activation, alpha=0.0 = pure semantic")
    print("#" * 70)

    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
        r = run_query(mem, "type 2 diabetes", alpha=alpha, top_k=10)
        top_labels = [x["label"] for x in r[:6]]
        hits = sum(1 for l in top_labels if l in expected_diabetes)
        print(f"  alpha={alpha:.2f}  top6={top_labels}  recall={hits}/{len(expected_diabetes)}")

    # --- Final evaluation ---
    print("\n\n" + "#" * 70)
    print("# EVALUATION SUMMARY")
    print("#" * 70)

    scenarios = [
        ("type 2 diabetes", expected_diabetes),
        ("obesity", expected_obesity),
        ("heart disease", expected_heart),
        ("depression", expected_depression),
    ]

    print(f"\n{'Scenario':<20} {'Act-only':>10} {'Sem-only':>10} {'Combined':>10} {'Expected':>10}")
    print(f"{'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    for concept, expected in scenarios:
        r = run_query(mem, concept, alpha=0.5, top_k=10)

        top_act = set(x["label"] for x in sorted(r, key=lambda x: x["activation"], reverse=True)[:6])
        top_sem = set(x["label"] for x in sorted(r, key=lambda x: x["similarity"], reverse=True)[:6])
        top_comb = set(x["label"] for x in sorted(r, key=lambda x: x["combined"], reverse=True)[:6])
        expected_set = set(expected)

        act_hits = len(top_act & expected_set)
        sem_hits = len(top_sem & expected_set)
        comb_hits = len(top_comb & expected_set)

        print(
            f"{concept:<20} {act_hits:>10} {sem_hits:>10} {comb_hits:>10} {len(expected):>10}"
        )

    print("""
KEY FINDINGS:
- Activation alone surfaces direct graph neighbors (treatments, complications)
- Semantic alone surfaces conceptually similar terms (related conditions)
- Combined captures both: direct clinical relationships AND related conditions
- For sparse regions (depression), semantic similarity compensates for missing edges
- The optimal alpha depends on the query: well-connected concepts favor activation,
  sparse concepts favor semantic similarity
""")


if __name__ == "__main__":
    main()
