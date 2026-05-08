"""
Demonstrates RRF retrieval, directional activation, and relevance feedback.

Shows how the new features fix the problems identified in the medical KB analysis:
1. RRF replaces broken score fusion with rank-based fusion
2. Directional activation respects edge semantics (complication vs treated_by)
3. Relevance feedback trains a learning-to-rank model from user input

Run: .venv/bin/python examples/feedback_demo.py
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from hyper3 import (
    HypergraphMemory,
    EmbeddingProvider,
    Modality,
    RetrievalEngine,
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


def build_medical_kb(mem: HypergraphMemory) -> None:
    conditions = {
        "type 2 diabetes": {"category": "metabolic"},
        "hypertension": {"category": "cardiovascular"},
        "obesity": {"category": "metabolic"},
        "heart disease": {"category": "cardiovascular"},
        "stroke": {"category": "cardiovascular"},
        "depression": {"category": "mental health"},
        "chronic kidney disease": {"category": "renal"},
        "sleep apnea": {"category": "respiratory"},
        "osteoarthritis": {"category": "musculoskeletal"},
        "asthma": {"category": "respiratory"},
        "metformin": {"type": "medication"},
        "insulin": {"type": "medication"},
        "lisinopril": {"type": "medication"},
        "statins": {"type": "medication"},
        "beta blockers": {"type": "medication"},
        "cognitive behavioral therapy": {"type": "therapy"},
        "SSRIs": {"type": "medication"},
        "weight loss surgery": {"type": "procedure"},
        "CPAP machine": {"type": "device"},
        "physical therapy": {"type": "therapy"},
        "smoking": {"type": "risk_factor"},
        "obesity risk": {"type": "risk_factor"},
        "sedentary lifestyle": {"type": "risk_factor"},
        "high cholesterol": {"type": "risk_factor"},
        "chronic stress": {"type": "risk_factor"},
    }

    for name, data in conditions.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    mem.link("type 2 diabetes", "obesity", label="risk_factor")
    mem.link("type 2 diabetes", "sedentary lifestyle", label="risk_factor")
    mem.link("type 2 diabetes", "metformin", label="treated_by")
    mem.link("type 2 diabetes", "insulin", label="treated_by")
    mem.link("type 2 diabetes", "chronic kidney disease", label="complication")
    mem.link("type 2 diabetes", "heart disease", label="complication")
    mem.link("type 2 diabetes", "stroke", label="complication")

    mem.link("hypertension", "obesity", label="risk_factor")
    mem.link("hypertension", "smoking", label="risk_factor")
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

    mem.link("obesity", "type 2 diabetes", label="complication")
    mem.link("obesity", "sleep apnea", label="complication")
    mem.link("obesity", "osteoarthritis", label="complication")
    mem.link("obesity", "heart disease", label="complication")
    mem.link("obesity", "sedentary lifestyle", label="risk_factor")
    mem.link("obesity", "weight loss surgery", label="treated_by")

    mem.link("depression", "chronic stress", label="risk_factor")
    mem.link("depression", "cognitive behavioral therapy", label="treated_by")
    mem.link("depression", "SSRIs", label="treated_by")

    mem.link("sleep apnea", "obesity", label="risk_factor")
    mem.link("sleep apnea", "CPAP machine", label="treated_by")

    mem.link("chronic kidney disease", "type 2 diabetes", label="risk_factor")
    mem.link("chronic kidney disease", "hypertension", label="risk_factor")

    mem.link("stroke", "hypertension", label="risk_factor")
    mem.link("stroke", "type 2 diabetes", label="risk_factor")

    mem.link("osteoarthritis", "obesity", label="risk_factor")
    mem.link("osteoarthritis", "physical therapy", label="treated_by")


def print_results(label: str, results, expected: set[str] | None = None):
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"{'=' * 70}")
    from hyper3.retrieval_engine import RetrievalResult
    if results and isinstance(results[0], RetrievalResult):
        print(f"{'Concept':<30} {'Act':>6} {'Sem':>6} {'RRF':>8} {'A#':>4} {'S#':>4}")
        print(f"{'-'*30} {'-'*6} {'-'*6} {'-'*8} {'-'*4} {'-'*4}")
        hits = 0
        for r in results:
            hit = " *" if expected and r.label in expected else ""
            if expected and r.label in expected:
                hits += 1
            print(f"{r.label:<30} {r.activation:>6.2f} {r.similarity:>6.3f} {r.rrf_score:>8.5f} {r.activation_rank:>4} {r.similarity_rank:>4}{hit}")
        if expected:
            print(f"\nRecall@{len(results)}: {hits}/{len(expected)} = {hits/len(expected):.0%}")
        return hits
    return 0


def main() -> None:
    print("Loading model...")
    provider = SentenceTransformerProvider()
    mem = HypergraphMemory(evolve_interval=0)
    mem.set_embedding_provider(provider)
    build_medical_kb(mem)
    print(f"KB: {mem.size[0]} nodes, {mem.size[1]} edges\n")

    expected_diabetes = {"metformin", "insulin", "obesity", "heart disease", "chronic kidney disease", "stroke", "hypertension"}
    expected_depression = {"SSRIs", "cognitive behavioral therapy", "chronic stress"}

    # --- Phase 1: Baseline RRF (no feedback) ---
    print("#" * 70)
    print("# PHASE 1: Baseline RRF retrieval (no feedback)")
    print("#" * 70)

    r1 = mem.search.query("type 2 diabetes", top_k=10)
    print_results("Query: 'type 2 diabetes' (RRF, no feedback)", r1, expected_diabetes)

    r2 = mem.search.query("depression", top_k=10)
    print_results("Query: 'depression' (RRF, no feedback)", r2, expected_depression)

    # --- Phase 2: Provide feedback and retrain ---
    print("\n\n" + "#" * 70)
    print("# PHASE 2: Record relevance feedback and retrain")
    print("#" * 70)

    relevant_diabetes = {"metformin", "insulin", "obesity", "heart disease", "chronic kidney disease", "stroke", "hypertension"}
    mem.record_feedback("type 2 diabetes", r1, relevant_diabetes)

    relevant_depression = {"SSRIs", "cognitive behavioral therapy", "chronic stress"}
    mem.record_feedback("depression", r2, relevant_depression)

    for _ in range(3):
        tmp_r1 = mem.search.query("type 2 diabetes", top_k=10)
        mem.record_feedback("type 2 diabetes", tmp_r1, relevant_diabetes)
        tmp_r2 = mem.search.query("depression", top_k=10)
        mem.record_feedback("depression", tmp_r2, relevant_depression)

    report = mem.train_retriever()
    print(f"\nLearnt weights: {report['weights']}")

    # --- Phase 3: LTR retrieval after feedback ---
    print("\n\n" + "#" * 70)
    print("# PHASE 3: LTR retrieval (trained on feedback)")
    print("#" * 70)

    r3 = mem.search.query("type 2 diabetes", top_k=10, use_ltr=True)
    print_results("Query: 'type 2 diabetes' (LTR, post-feedback)", r3, expected_diabetes)

    r4 = mem.search.query("depression", top_k=10, use_ltr=True)
    print_results("Query: 'depression' (LTR, post-feedback)", r4, expected_depression)

    # --- Comparison ---
    print("\n\n" + "#" * 70)
    print("# COMPARISON: Before vs After feedback")
    print("#" * 70)

    def count_hits(results, expected):
        return sum(1 for r in results if r.label in expected)

    print(f"\n{'Scenario':<25} {'RRF base':>10} {'LTR trained':>12} {'Expected':>10}")
    print(f"{'-'*25} {'-'*10} {'-'*12} {'-'*10}")

    rrf_d = count_hits(r1, expected_diabetes)
    ltr_d = count_hits(r3, expected_diabetes)
    print(f"{'type 2 diabetes':<25} {rrf_d:>10} {ltr_d:>12} {len(expected_diabetes):>10}")

    rrf_dep = count_hits(r2, expected_depression)
    ltr_dep = count_hits(r4, expected_depression)
    print(f"{'depression':<25} {rrf_dep:>10} {ltr_dep:>12} {len(expected_depression):>10}")

    print("\nDone.")


if __name__ == "__main__":
    main()
