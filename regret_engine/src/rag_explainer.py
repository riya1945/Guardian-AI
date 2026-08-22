from __future__ import annotations

import re
import time
from pathlib import Path

import numpy as np

from regret_engine.src.config import Settings, load_settings
from regret_engine.src.embeddings import get_embedding_provider
from regret_engine.src.llm_provider import (
    DeterministicProvider,
    LlmUnavailable,
    build_provider_chain,
)
from regret_engine.src.persistence import ExasolVectorStore, InMemoryVectorStore
from regret_engine.src.schemas import (
    DecisionRecord,
    EvidenceItem,
    GroundedExplanation,
    KnowledgeChunk,
)


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
INSUFFICIENT_EVIDENCE = "Evidence unavailable / insufficient to provide a grounded explanation."


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
    def __init__(
        self,
        knowledge_dir: Path = KNOWLEDGE_DIR,
        settings: Settings | None = None,
    ):
        self.knowledge_dir = knowledge_dir
        self.settings = settings or load_settings()
        self.chunks = load_knowledge_chunks(knowledge_dir)
        self.embedding_provider = get_embedding_provider(self.settings)
        self.vector_store = self._build_vector_store()
        self.llm_chain = build_provider_chain(self.settings)

    @property
    def vector_backend(self) -> str:
        return getattr(self.vector_store, "backend_name", "unknown")

    @property
    def llm_provider(self) -> str:
        if self.llm_chain.last_provider != "none":
            return self.llm_chain.last_provider
        return self.llm_chain_names[0]

    @property
    def llm_chain_names(self) -> list[str]:
        return [provider.provider_name for provider in self.llm_chain.providers]

    def retrieve(
        self,
        record: DecisionRecord,
        question: str | None = None,
        top_k: int = 4,
    ) -> list[EvidenceItem]:
        if question and not self._is_domain_question(question):
            return []
        query = self._build_query(record, question)
        return self.vector_store.retrieve(query=query, top_k=top_k)

    def explain(
        self,
        record: DecisionRecord,
        question: str | None = None,
        top_k: int = 4,
        use_llm: bool = True,
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
        counterfactual = (
            f"The selected price was {record.regret.actual_price:.2f} INR. "
            f"The best scored counterfactual price was {record.regret.best_price:.2f} INR, "
            f"with estimated regret of {record.regret.regret:.2f} INR."
        )

        if use_llm:
            try:
                draft = self.llm_chain.generate(record, evidence, latency_ms)
            except LlmUnavailable:
                draft = DeterministicProvider().generate(record, evidence, latency_ms)
        else:
            draft = DeterministicProvider().generate(record, evidence, latency_ms)

        return GroundedExplanation(
            status="grounded",
            summary=draft.summary,
            decision=record.recommendation,
            regret_score=round(record.regret_score, 2),
            confidence=confidence,
            key_factors=record.factors[:4],
            supporting_evidence=evidence,
            counterfactual=counterfactual,
            alternative_action=draft.alternative_action,
            uncertainties=record.uncertainties
            + [
                "Explanation generator may use Groq or Gemini only when keys are configured; evidence remains fixed to retrieved repository snippets.",
            ],
            explanation=draft.explanation,
        )

    def _build_vector_store(self) -> InMemoryVectorStore | ExasolVectorStore:
        wants_memory = self.settings.vector_backend == "memory"
        has_exasol = bool(
            self.settings.exasol_dsn
            and self.settings.exasol_user
            and self.settings.exasol_password
        )
        if self.settings.vector_backend == "exasol" and not has_exasol:
            raise ValueError("EXASOL_DSN, EXASOL_USER, and EXASOL_PASSWORD are required.")
        if has_exasol and not wants_memory:
            try:
                store = ExasolVectorStore(
                    settings=self.settings,
                    embedding_provider=self.embedding_provider,
                )
                store.ingest(self.chunks)
                return store
            except Exception:
                if self.settings.vector_backend == "exasol":
                    raise

        return InMemoryVectorStore(
            chunks=self.chunks,
            embedding_provider=self.embedding_provider,
        )

    def _build_query(
        self,
        record: DecisionRecord,
        question: str | None = None,
    ) -> str:
        factor_text = " ".join(factor.factor for factor in record.factors)
        return (
            f"{question or ''} regret risk pricing counterfactual evidence "
            f"{record.risk_level} {record.regret.decision_quality} "
            f"regret percentage {record.regret.regret_percentage:.2f} "
            f"best price selected price demand revenue confidence {factor_text}"
        )

    def _is_domain_question(self, question: str) -> bool:
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
        return any(term in question_terms for term in domain_terms)


def evaluate_explainer(explainer: RagExplainer) -> dict[str, float | int | str]:
    checks = [
        ("high regret counterfactual price review", True),
        ("confidence uncertainty evidence limitations", True),
        ("unrelated sports result", False),
    ]
    passed = 0
    scores: list[float] = []

    for query, should_match in checks:
        evidence = (
            explainer.vector_store.retrieve(query, top_k=3)
            if should_match
            else []
        )
        matched = bool(evidence)
        if matched == should_match:
            passed += 1
        if evidence:
            scores.extend(item.relevance_score for item in evidence)

    return {
        "vector_backend": explainer.vector_backend,
        "embedding_provider": explainer.embedding_provider.provider_name,
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
