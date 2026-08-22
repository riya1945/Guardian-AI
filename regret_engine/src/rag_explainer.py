from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from regret_engine.src.schemas import DecisionRecord, EvidenceItem, GroundedExplanation


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
INSUFFICIENT_EVIDENCE = "Evidence unavailable / insufficient to provide a grounded explanation."


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    content: str


class LocalVectorStore:
    """Small local vector store for repo knowledge; avoids external keys for demo reliability."""

    def __init__(self, chunks: list[KnowledgeChunk]):
        if not chunks:
            raise ValueError("No knowledge chunks available for RAG retrieval.")
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=4096,
        )
        self.embeddings = self.vectorizer.fit_transform(
            [chunk.content for chunk in chunks]
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.08,
    ) -> list[EvidenceItem]:
        query_vector = self.vectorizer.transform([query])
        scores = (self.embeddings @ query_vector.T).toarray().reshape(-1)
        ranked = np.argsort(scores)[::-1][:top_k]

        evidence: list[EvidenceItem] = []
        for index in ranked:
            score = float(scores[index])
            if score < min_score:
                continue
            chunk = self.chunks[int(index)]
            evidence.append(
                EvidenceItem(
                    source=chunk.source,
                    title=chunk.title,
                    content=chunk.content,
                    relevance_score=round(score, 4),
                )
            )
        return evidence


def load_knowledge_chunks(
    knowledge_dir: Path = KNOWLEDGE_DIR,
    chunk_size: int = 900,
    overlap: int = 120,
) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        text = _normalize(path.read_text(encoding="utf-8"))
        title = _extract_title(text, path)
        for idx, chunk in enumerate(_chunk_text(text, chunk_size, overlap)):
            chunks.append(
                KnowledgeChunk(
                    source=f"{path.name}#chunk-{idx + 1}",
                    title=title,
                    content=chunk,
                )
            )
    return chunks


class RagExplainer:
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self.chunks = load_knowledge_chunks(knowledge_dir)
        self.vector_store = LocalVectorStore(self.chunks)

    def retrieve(
        self,
        record: DecisionRecord,
        question: str | None = None,
        top_k: int = 4,
    ) -> list[EvidenceItem]:
        query = self._build_query(record, question)
        return self.vector_store.retrieve(query=query, top_k=top_k)

    def explain(
        self,
        record: DecisionRecord,
        question: str | None = None,
        top_k: int = 4,
    ) -> GroundedExplanation:
        started = time.perf_counter()
        evidence = self.retrieve(record, question=question, top_k=top_k)
        latency_ms = (time.perf_counter() - started) * 1000

        if not evidence:
            return GroundedExplanation(
                status="insufficient_evidence",
                summary=INSUFFICIENT_EVIDENCE,
                decision=record.recommendation,
                regret_score=round(record.regret_score, 2),
                confidence=0.0,
                key_factors=[],
                supporting_evidence=[],
                counterfactual="No counterfactual explanation was generated because retrieval returned no grounded evidence.",
                alternative_action="Manual review required before using this explanation.",
                uncertainties=[INSUFFICIENT_EVIDENCE],
                explanation=INSUFFICIENT_EVIDENCE,
            )

        evidence_score = sum(item.relevance_score for item in evidence) / len(evidence)
        confidence = round(min(record.confidence, 0.55 + evidence_score), 3)
        top_titles = ", ".join(sorted({item.title for item in evidence}))
        counterfactual = (
            f"The selected price was {record.regret.actual_price:.2f} INR. "
            f"The best scored counterfactual price was {record.regret.best_price:.2f} INR, "
            f"with estimated regret of {record.regret.regret:.2f} INR."
        )
        alternative_action = (
            "Accept submitted price"
            if record.risk_level == "LOW"
            else f"Review price before release and compare against {record.regret.best_price:.2f} INR counterfactual."
        )
        summary = (
            f"{record.decision_id} is {record.risk_level.lower()} risk. "
            f"Guardian-AI recommends: {record.recommendation}."
        )
        explanation = (
            f"Explanation is grounded in retrieved Guardian-AI knowledge: {top_titles}. "
            f"Regret engine output shows {record.regret.regret:.2f} INR regret "
            f"({record.regret.regret_percentage:.2f}%). "
            f"{counterfactual} Retrieval latency was {latency_ms:.1f} ms."
        )

        return GroundedExplanation(
            status="grounded",
            summary=summary,
            decision=record.recommendation,
            regret_score=round(record.regret_score, 2),
            confidence=confidence,
            key_factors=record.factors[:4],
            supporting_evidence=evidence,
            counterfactual=counterfactual,
            alternative_action=alternative_action,
            uncertainties=record.uncertainties
            + [
                "Explanation generator is deterministic and does not infer facts outside retrieved repository knowledge.",
            ],
            explanation=explanation,
        )

    def _build_query(
        self,
        record: DecisionRecord,
        question: str | None = None,
    ) -> str:
        if question:
            question_terms = question.lower()
            domain_terms = {
                "regret",
                "risk",
                "price",
                "pricing",
                "counterfactual",
                "confidence",
                "evidence",
                "decision",
                "recommend",
                "demand",
                "revenue",
            }
            if not any(term in question_terms for term in domain_terms):
                return question

        factor_text = " ".join(factor.factor for factor in record.factors)
        return (
            f"{question or ''} regret risk pricing counterfactual evidence "
            f"{record.risk_level} {record.regret.decision_quality} "
            f"regret percentage {record.regret.regret_percentage:.2f} "
            f"best price selected price demand revenue confidence {factor_text}"
        )


def evaluate_explainer(explainer: RagExplainer) -> dict[str, float | int]:
    checks = [
        ("high regret counterfactual price review", True),
        ("confidence uncertainty evidence limitations", True),
        ("unrelated sports result", False),
    ]
    passed = 0
    scores: list[float] = []

    for query, should_match in checks:
        evidence = explainer.vector_store.retrieve(query, top_k=3)
        matched = bool(evidence)
        if matched == should_match:
            passed += 1
        if evidence:
            scores.extend(item.relevance_score for item in evidence)

    return {
        "synthetic_queries": len(checks),
        "passed": passed,
        "failure_rate": round((len(checks) - passed) / len(checks), 3),
        "average_relevance": round(float(np.mean(scores)) if scores else 0.0, 4),
        "evidence_coverage": round(passed / len(checks), 3),
    }


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return path.stem.replace("_", " ").title()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    sections = re.split(r"\n(?=##? )", text)
    chunks: list[str] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= chunk_size:
            chunks.append(section)
            continue
        start = 0
        while start < len(section):
            end = min(start + chunk_size, len(section))
            chunks.append(section[start:end].strip())
            if end == len(section):
                break
            start = max(end - overlap, start + 1)

    return chunks
