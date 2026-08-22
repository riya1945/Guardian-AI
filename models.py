from pydantic import BaseModel
from typing import Optional

class Decision(BaseModel):
    decision_id: str
    sku_id: str
    event_time: str
    old_price: Optional[float]
    new_price: Optional[float]
    reason_code: str
    flagged: bool
    flag_reason: Optional[str]
    confidence: Optional[float]
    severity: Optional[float]

class DecisionsResponse(BaseModel):
    decisions: list[Decision]