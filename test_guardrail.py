import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db import get_connection
from app.guardrail import check_decision, flag_decision
import time

conn = get_connection()

rows = conn.execute("""
    SELECT decision_id, sku_id, old_price, new_price
    FROM decisions
    ORDER BY event_time DESC
    LIMIT 10
""").fetchall()

for decision_id, sku_id, old_price, new_price in rows:
    start = time.time()
    flagged, reason, severity = check_decision(conn, decision_id, sku_id, old_price, new_price)
    elapsed_ms = round((time.time() - start) * 1000, 2)

    if flagged:
        flag_decision(conn, decision_id, reason, severity)
        print(f"[FLAGGED in {elapsed_ms}ms | severity {severity}] {sku_id}: {old_price} -> {new_price} | {reason}")
    else:
        print(f"[OK in {elapsed_ms}ms] {sku_id}: {old_price} -> {new_price}")