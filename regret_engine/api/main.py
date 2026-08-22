from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from regret_engine.src.config import load_settings
from regret_engine.src.decision_store import DecisionStore
from regret_engine.src.persistence import build_decision_repository
from regret_engine.src.rag_explainer import RagExplainer, evaluate_explainer
from regret_engine.src.regret_service import RegretService
from regret_engine.src.schemas import Decision, DecisionRecord, ExplainRequest


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
        "decision_records": decision_store.record_count,
    }


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "index.html")


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


@app.get("/rag/evaluation")
def rag_evaluation() -> dict[str, float | int | str]:
    return evaluate_explainer(rag_explainer)
