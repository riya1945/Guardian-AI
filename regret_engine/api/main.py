from __future__ import annotations

from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from regret_engine.src.config import load_settings
from regret_engine.src.decision_store import DecisionStore
from regret_engine.src.integration import (
    GuardrailDecisionInput,
    decision_from_guardrail,
    guardrail_contract,
)
from regret_engine.src.persistence import build_decision_repository
from regret_engine.src.rag_explainer import RagExplainer, evaluate_explainer
from regret_engine.src.regret_service import RegretService
from regret_engine.src.schemas import AnalyticsSummary, Decision, DecisionRecord, ExplainRequest


BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

settings = load_settings()
regret_service = RegretService()
rag_explainer = RagExplainer(settings=settings)
decision_repository = build_decision_repository(settings)
decision_store = DecisionStore(regret_service, rag_explainer, decision_repository)

app = FastAPI(
    title="Guardian-AI Regret Engine + RAG Explain Layer",
    description=(
        "Off-policy pricing regret scoring, grounded explanations, "
        "and local decision-intelligence dashboard."
    ),
    version="2.0.0",
)

app.mount(
    "/dashboard/assets",
    StaticFiles(directory=DASHBOARD_DIR),
    name="dashboard-assets",
)


@app.get("/health")
def health() -> dict[str, object]:
    return _health_payload()


def _health_payload(record_count: int | None = None) -> dict[str, object]:
    return {
        "status": "healthy",
        "service": "Guardian-AI",
        "model_loaded": True,
        "model_source": regret_service.model_source,
        "storage_backend": decision_store.backend_name,
        "vector_backend": rag_explainer.vector_backend,
        "embedding_provider": rag_explainer.embedding_provider.provider_name,
        "llm_provider": rag_explainer.llm_provider,
        "llm_chain": rag_explainer.llm_chain_names,
        "rag_chunks": len(rag_explainer.chunks),
        "decision_records": record_count
        if record_count is not None
        else decision_store.record_count,
    }


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/", include_in_schema=False)
def root_dashboard() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.post("/calculate-regret")
def calculate_regret_endpoint(decision: Decision) -> dict[str, object]:
    try:
        return regret_service.legacy_result(decision)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/decision", response_model=DecisionRecord)
def create_decision(decision: Decision) -> DecisionRecord:
    try:
        return decision_store.upsert(decision, explain=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/integrations/guardrail-decision", response_model=DecisionRecord)
def create_from_guardrail_decision(payload: GuardrailDecisionInput) -> DecisionRecord:
    try:
        return decision_store.upsert(decision_from_guardrail(payload), explain=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/integrations/contracts")
def integration_contracts() -> dict[str, object]:
    return guardrail_contract()


@app.get("/decisions", response_model=list[DecisionRecord])
def list_decisions(
    limit: int = Query(default=100, ge=1, le=500),
    risk_level: str | None = Query(default=None),
) -> list[DecisionRecord]:
    if risk_level and risk_level.upper() not in {"LOW", "MEDIUM", "HIGH"}:
        raise HTTPException(status_code=400, detail="risk_level must be LOW, MEDIUM, or HIGH")
    return decision_store.list_records(limit=limit, risk_level=risk_level)


@app.get("/decisions/{decision_id}", response_model=DecisionRecord)
def get_decision(decision_id: str) -> DecisionRecord:
    record = decision_store.get(decision_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return record


@app.post("/explain/{decision_id}", response_model=DecisionRecord)
def explain_decision(
    decision_id: str,
    request: ExplainRequest | None = None,
) -> DecisionRecord:
    request = request or ExplainRequest()
    if request.decision is not None:
        decision_store.upsert(request.decision, explain=False)
        decision_id = request.decision.decision_id

    record = decision_store.ensure_explanation(
        decision_id,
        question=request.question,
        top_k=request.top_k,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return record


@app.get("/decisions/{decision_id}/evidence")
def get_decision_evidence(decision_id: str) -> dict[str, object]:
    record = decision_store.ensure_explanation(decision_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return {
        "decision_id": decision_id,
        "evidence": record.explanation.supporting_evidence if record.explanation else [],
    }


@app.get("/analytics")
def analytics() -> dict[str, object]:
    summary = decision_store.analytics()
    if hasattr(summary, "model_dump"):
        return summary.model_dump()
    return summary.dict()


@app.get("/dashboard/metrics")
def dashboard_metrics() -> dict[str, object]:
    summary = decision_store.analytics()
    payload = summary.model_dump() if hasattr(summary, "model_dump") else summary.dict()
    payload["backend"] = {
        "storage_backend": decision_store.backend_name,
        "vector_backend": rag_explainer.vector_backend,
        "embedding_provider": rag_explainer.embedding_provider.provider_name,
        "llm_provider": rag_explainer.llm_provider,
        "model_source": regret_service.model_source,
    }
    return payload


@app.get("/dashboard/feed")
def dashboard_feed(
    limit: int = Query(default=100, ge=1, le=500),
    risk_level: str | None = Query(default=None),
) -> dict[str, object]:
    if risk_level and risk_level.upper() not in {"LOW", "MEDIUM", "HIGH"}:
        raise HTTPException(status_code=400, detail="risk_level must be LOW, MEDIUM, or HIGH")

    records = decision_store.list_records(limit=500)
    filtered_records = [
        record for record in records if not risk_level or record.risk_level == risk_level.upper()
    ][:limit]
    summary = _analytics_from_records(records)
    analytics_payload = (
        summary.model_dump() if hasattr(summary, "model_dump") else summary.dict()
    )
    return {
        "health": _health_payload(record_count=len(records)),
        "analytics": analytics_payload,
        "decisions": filtered_records,
    }


@app.get("/dashboard/interventions")
def dashboard_interventions(
    limit: int = Query(default=60, ge=1, le=500),
) -> dict[str, object]:
    records = [
        record
        for record in decision_store.list_records(limit=500)
        if record.risk_level in {"MEDIUM", "HIGH"}
    ]
    records.sort(key=lambda record: record.regret_score, reverse=True)
    return {
        "count": len(records[:limit]),
        "items": [_dashboard_record(record) for record in records[:limit]],
    }


@app.get("/dashboard/leaderboard")
def dashboard_leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    records = decision_store.list_records(limit=500)
    records.sort(key=lambda record: record.regret_score, reverse=True)
    return {
        "count": len(records[:limit]),
        "items": [_dashboard_record(record) for record in records[:limit]],
    }


@app.get("/dashboard/model")
def dashboard_model() -> dict[str, object]:
    return {
        "model_loaded": True,
        "model_source": regret_service.model_source,
        "storage_backend": decision_store.backend_name,
        "vector_backend": rag_explainer.vector_backend,
        "embedding_provider": rag_explainer.embedding_provider.provider_name,
        "llm_provider": rag_explainer.llm_provider,
        "llm_chain": rag_explainer.llm_chain_names,
        "rag_chunks": len(rag_explainer.chunks),
        "decision_records": decision_store.record_count,
    }


@app.get("/dashboard/ab")
def dashboard_ab() -> dict[str, object]:
    records = decision_store.list_records(limit=500)
    cohorts = []
    for risk_level in ("LOW", "MEDIUM", "HIGH"):
        cohort = [record for record in records if record.risk_level == risk_level]
        if not cohort:
            continue
        cohorts.append(
            {
                "cohort": risk_level,
                "count": len(cohort),
                "average_regret": round(
                    sum(record.regret_score for record in cohort) / len(cohort),
                    2,
                ),
                "average_confidence": round(
                    sum(record.confidence for record in cohort) / len(cohort),
                    3,
                ),
            }
        )
    return {
        "status": "derived_from_decision_cohorts",
        "cohorts": cohorts,
    }


@app.get("/dashboard/settings")
def dashboard_settings() -> dict[str, object]:
    return {
        "storage_backend": settings.storage_backend,
        "vector_backend": settings.vector_backend,
        "embedding_provider": settings.embedding_provider,
        "embedding_dim": settings.embedding_dim,
        "exasol_configured": bool(
            settings.exasol_dsn
            and settings.exasol_user
            and settings.exasol_password
        ),
        "exasol_schema": settings.exasol_schema,
        "exasol_encryption": settings.exasol_encryption,
        "exasol_compression": settings.exasol_compression,
        "exasol_certificate_validation": settings.exasol_certificate_validation,
        "llm_chain": list(settings.llm_chain),
        "groq_configured": bool(settings.groq_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
        "groq_model": settings.groq_model,
        "gemini_chat_model": settings.gemini_chat_model,
        "gemini_embedding_model": settings.gemini_embedding_model,
    }


@app.get("/rag/evaluation")
def rag_evaluation() -> dict[str, float | int | str]:
    return evaluate_explainer(rag_explainer)


def _dashboard_record(record: DecisionRecord) -> dict[str, object]:
    return {
        "decision_id": record.decision_id,
        "timestamp": record.timestamp,
        "sku": record.sku,
        "price": record.price,
        "risk_level": record.risk_level,
        "recommendation": record.recommendation,
        "regret_score": record.regret_score,
        "regret_percentage": record.regret_percentage,
        "confidence": record.confidence,
        "best_price": record.regret.best_price,
        "decision_quality": record.regret.decision_quality,
        "evidence_count": len(record.explanation.supporting_evidence)
        if record.explanation
        else 0,
    }


def _analytics_from_records(records: list[DecisionRecord]) -> AnalyticsSummary:
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
