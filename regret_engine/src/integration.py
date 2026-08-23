from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from regret_engine.src.schemas import Decision


class GuardrailDecisionInput(BaseModel):
    """Adapter for Divija's DecisionGuard output shape."""

    decision_id: str
    sku_id: str
    event_time: str
    old_price: float | None = None
    new_price: float
    reason_code: str | None = None
    flagged: bool = False
    flag_reason: str | None = None
    confidence: float | None = None
    severity: float | None = None
    demand_signal: float | None = None
    competitor_price: float | None = None
    inventory_level: float | None = None
    previous_units: float | None = None
    rolling_7d_units: float | None = None
    rolling_30d_units: float | None = None
    demand_trend: float | None = None
    demand_momentum: float | None = None
    historical_avg_price: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def decision_from_guardrail(payload: GuardrailDecisionInput) -> Decision:
    occurred_at = _parse_timestamp(payload.event_time)
    previous_price = float(payload.old_price or payload.new_price)
    previous_units = float(payload.previous_units or 40.0)
    rolling_7d_units = float(payload.rolling_7d_units or previous_units)
    rolling_30d_units = float(payload.rolling_30d_units or rolling_7d_units)
    demand_signal = float(payload.demand_signal or 1.0)

    return Decision(
        decision_id=payload.decision_id,
        timestamp=occurred_at.isoformat(),
        sku=payload.sku_id,
        price=float(payload.new_price),
        previous_units=previous_units,
        previous_price=previous_price,
        rolling_7d_units=rolling_7d_units,
        rolling_30d_units=rolling_30d_units,
        demand_trend=float(payload.demand_trend or demand_signal),
        demand_momentum=float(payload.demand_momentum or 0.0),
        day_of_week=occurred_at.weekday(),
        month=occurred_at.month,
        year=occurred_at.year,
        is_weekend=1 if occurred_at.weekday() >= 5 else 0,
        historical_avg_price=float(payload.historical_avg_price or previous_price),
        demand_score=payload.demand_signal,
        competitor_price=payload.competitor_price,
        inventory=payload.inventory_level,
    )


def guardrail_contract() -> dict[str, object]:
    return {
        "person_a_input": {
            "decision_id": "uuid-or-trace-id",
            "sku_id": "SKU-0001",
            "event_time": "2026-08-23 15:30:00",
            "old_price": 499.0,
            "new_price": 699.0,
            "reason_code": "ANOMALY_INJECTED_SPIKE",
            "flagged": True,
            "flag_reason": "Price exceeds competitor ceiling",
            "confidence": 0.91,
            "severity": 0.8,
            "demand_signal": 0.82,
            "competitor_price": 510.0,
            "inventory_level": 120,
        },
        "ranbir_output": "DecisionRecord with regret, factors, assumptions, uncertainties, and grounded explanation.",
        "endpoint": "POST /integrations/guardrail-decision",
    }


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
