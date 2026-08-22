from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import get_connection
from app.models import Decision, DecisionsResponse

app = FastAPI(title="DecisionGuard - Guardrail API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def row_to_dict(row):
    decision_id, sku_id, event_time, old_price, new_price, reason_code, flagged, flag_reason, confidence, severity = row
    return {
        "decision_id": decision_id,
        "sku_id": sku_id,
        "event_time": str(event_time),
        "old_price": float(old_price) if old_price is not None else None,
        "new_price": float(new_price) if new_price is not None else None,
        "reason_code": reason_code,
        "flagged": bool(flagged),
        "flag_reason": flag_reason,
        "confidence": float(confidence) if confidence is not None else None,
        "severity": float(severity) if severity is not None else None,
    }

@app.get("/decisions/latest", response_model=DecisionsResponse)
def get_latest_decisions(limit: int = 20):
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT decision_id, sku_id, event_time, old_price, new_price,
               reason_code, flagged, flag_reason, confidence, severity
        FROM decisions
        ORDER BY event_time DESC
        LIMIT {limit}
    """).fetchall()
    conn.close()
    return {"decisions": [row_to_dict(r) for r in rows]}

@app.get("/decisions/flagged", response_model=DecisionsResponse)
def get_flagged_decisions(limit: int = 20):
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT decision_id, sku_id, event_time, old_price, new_price,
               reason_code, flagged, flag_reason, confidence, severity
        FROM decisions
        WHERE flagged = TRUE
        ORDER BY event_time DESC
        LIMIT {limit}
    """).fetchall()
    conn.close()
    return {"decisions": [row_to_dict(r) for r in rows]}

@app.get("/decisions/{decision_id}", response_model=Decision)
def get_decision(decision_id: str):
    conn = get_connection()
    safe_id = decision_id.replace("'", "''")
    row = conn.execute(f"""
        SELECT decision_id, sku_id, event_time, old_price, new_price,
               reason_code, flagged, flag_reason, confidence, severity
        FROM decisions
        WHERE decision_id = '{safe_id}'
    """).fetchone()
    conn.close()
    if row is None:
        return {"error": "decision not found"}
    return row_to_dict(row)

@app.get("/stats")
def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    flagged = conn.execute("SELECT COUNT(*) FROM decisions WHERE flagged = TRUE").fetchone()[0]
    conn.close()
    catch_rate = round((flagged / total) * 100, 2) if total > 0 else 0.0
    return {
        "total_decisions": total,
        "flagged_decisions": flagged,
        "catch_rate_pct": catch_rate
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}