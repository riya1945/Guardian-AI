from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
ExplanationStatus = Literal["grounded", "insufficient_evidence"]


class Decision(BaseModel):
    decision_id: str
    timestamp: str
    sku: str
    price: float
    previous_units: float
    previous_price: float
    rolling_7d_units: float
    rolling_30d_units: float
    demand_trend: float
    demand_momentum: float
    day_of_week: int
    month: int
    year: int
    is_weekend: int
    historical_avg_price: float
    demand_score: float | None = None
    competitor_price: float | None = None
    inventory: float | None = None
    season: str | None = None


class PriceAlternative(BaseModel):
    price: float
    predicted_demand: float
    predicted_revenue: float
    is_selected: bool = False
    is_best: bool = False


class RegretResult(BaseModel):
    decision_id: str
    sku: str
    actual_price: float
    best_price: float
    actual_predicted_demand: float
    best_predicted_demand: float
    actual_predicted_revenue: float
    best_predicted_revenue: float
    regret: float
    regret_percentage: float
    decision_quality: Literal["GOOD", "QUESTIONABLE", "HIGH_REGRET"]
    currency: Literal["INR"] = "INR"
    alternatives: list[PriceAlternative] = Field(default_factory=list)


class DecisionFactor(BaseModel):
    factor: str
    impact: Literal["positive", "negative", "neutral"]
    magnitude: float
    evidence: str


class EvidenceItem(BaseModel):
    source: str
    title: str
    content: str
    relevance_score: float


class GroundedExplanation(BaseModel):
    status: ExplanationStatus
    summary: str
    decision: str
    regret_score: float
    confidence: float
    key_factors: list[DecisionFactor] = Field(default_factory=list)
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    counterfactual: str
    alternative_action: str
    uncertainties: list[str] = Field(default_factory=list)
    explanation: str


class DecisionRecord(BaseModel):
    decision_id: str
    timestamp: str
    sku: str
    price: float
    recommendation: str
    regret_score: float
    regret_percentage: float
    risk_level: RiskLevel
    confidence: float
    input: Decision
    regret: RegretResult
    factors: list[DecisionFactor]
    assumptions: list[str]
    uncertainties: list[str]
    explanation: GroundedExplanation | None = None


class ExplainRequest(BaseModel):
    decision: Decision | None = None
    question: str | None = None
    top_k: int = 4


class AnalyticsSummary(BaseModel):
    total_decisions: int
    average_regret: float
    average_confidence: float
    high_risk_decisions: int
    explanation_coverage: float
    retrieved_evidence_sources: int
    risk_breakdown: dict[str, int]
    regret_over_time: list[dict[str, float | str]]
    factor_breakdown: list[dict[str, float | str]]
