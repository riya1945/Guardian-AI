from __future__ import annotations

from collections import Counter
from typing import Protocol

from regret_engine.src.rag_explainer import RagExplainer
from regret_engine.src.regret_service import RegretService, load_demo_decisions
from regret_engine.src.schemas import AnalyticsSummary, Decision, DecisionRecord


class DecisionRepository(Protocol):
    backend_name: str

    def save(self, record: DecisionRecord) -> None:
        ...

    def list_records(
        self,
        limit: int = 100,
        risk_level: str | None = None,
    ) -> list[DecisionRecord]:
        ...

    def get(self, decision_id: str) -> DecisionRecord | None:
        ...

    def count(self) -> int:
        ...


class DecisionStore:
    """Decision feed backed by Exasol when configured, memory otherwise."""

    def __init__(
        self,
        regret_service: RegretService,
        explainer: RagExplainer,
        repository: DecisionRepository,
        demo_limit: int = 40,
    ):
        self.regret_service = regret_service
        self.explainer = explainer
        self.repository = repository
        if self.repository.count() < demo_limit:
            self._load_demo_records(demo_limit)

    @property
    def backend_name(self) -> str:
        return self.repository.backend_name

    @property
    def record_count(self) -> int:
        return self.repository.count()

    def _load_demo_records(self, limit: int) -> None:
        for decision in load_demo_decisions(limit=limit):
            self.upsert(decision, explain=True, use_llm=False)

    def upsert(
        self,
        decision: Decision,
        explain: bool = True,
        use_llm: bool = True,
    ) -> DecisionRecord:
        record = self.regret_service.build_record(decision)
        if explain:
            record.explanation = self.explainer.explain(record, use_llm=use_llm)
        self.repository.save(record)
        return record

    def list_records(
        self,
        limit: int = 100,
        risk_level: str | None = None,
    ) -> list[DecisionRecord]:
        return self.repository.list_records(limit=limit, risk_level=risk_level)

    def get(self, decision_id: str) -> DecisionRecord | None:
        return self.repository.get(decision_id)

    def ensure_explanation(
        self,
        decision_id: str,
        question: str | None = None,
        top_k: int = 4,
    ) -> DecisionRecord | None:
        record = self.get(decision_id)
        if not record:
            return None
        record.explanation = self.explainer.explain(
            record,
            question=question,
            top_k=top_k,
        )
        self.repository.save(record)
        return record

    def analytics(self) -> AnalyticsSummary:
        records = self.repository.list_records(limit=10000)
        if not records:
            return AnalyticsSummary(
                total_decisions=0,
                average_regret=0.0,
                average_confidence=0.0,
                high_risk_decisions=0,
                explanation_coverage=0.0,
                retrieved_evidence_sources=0,
                risk_breakdown={"LOW": 0, "MEDIUM": 0, "HIGH": 0},
                regret_over_time=[],
                factor_breakdown=[],
            )

        risk_counts = Counter(record.risk_level for record in records)
        explained = [
            record
            for record in records
            if record.explanation and record.explanation.status == "grounded"
        ]
        evidence_sources = {
            item.source
            for record in records
            if record.explanation
            for item in record.explanation.supporting_evidence
        }
        factor_totals: Counter[str] = Counter()
        for record in records:
            for factor in record.factors:
                factor_totals[factor.factor] += factor.magnitude

        return AnalyticsSummary(
            total_decisions=len(records),
            average_regret=round(
                sum(record.regret_score for record in records) / len(records),
                2,
            ),
            average_confidence=round(
                sum(record.confidence for record in records) / len(records),
                3,
            ),
            high_risk_decisions=risk_counts.get("HIGH", 0),
            explanation_coverage=round(len(explained) / len(records), 3),
            retrieved_evidence_sources=len(evidence_sources),
            risk_breakdown={
                "LOW": risk_counts.get("LOW", 0),
                "MEDIUM": risk_counts.get("MEDIUM", 0),
                "HIGH": risk_counts.get("HIGH", 0),
            },
            regret_over_time=[
                {
                    "timestamp": record.timestamp,
                    "regret": round(record.regret_score, 2),
                    "confidence": record.confidence,
                }
                for record in sorted(records, key=lambda item: item.timestamp)
            ],
            factor_breakdown=[
                {"factor": factor, "magnitude": round(magnitude, 3)}
                for factor, magnitude in factor_totals.most_common()
            ],
        )
