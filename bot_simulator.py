import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import random
import uuid
import time
import threading
from datetime import datetime
from app.db import get_connection
from app.guardrail import check_decision, flag_decision

conn = get_connection()

def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_latest_price(sku_id):
    result = conn.execute(f"""
        SELECT new_price FROM decisions
        WHERE sku_id = '{sku_id}'
        ORDER BY event_time DESC
        LIMIT 1
    """).fetchone()
    return float(result[0]) if result else 500.0

def get_latest_cost(sku_id):
    result = conn.execute(f"""
        SELECT cost_price FROM market_context
        WHERE sku_id = '{sku_id}'
        ORDER BY event_time DESC
        LIMIT 1
    """).fetchone()
    return float(result[0]) if result else 300.0

def get_latest_competitor_price(sku_id):
    result = conn.execute(f"""
        SELECT competitor_price FROM market_context
        WHERE sku_id = '{sku_id}'
        ORDER BY event_time DESC
        LIMIT 1
    """).fetchone()
    return float(result[0]) if result else 500.0

def make_decision(sku_id, anomaly_type=None):
    old_price = get_latest_price(sku_id)
    cost = get_latest_cost(sku_id)
    event_time = datetime.now()

    if anomaly_type == "crash":
        new_price = round(cost * random.uniform(0.5, 0.8), 2)
        reason_code = "ANOMALY_INJECTED_CRASH"
    elif anomaly_type == "spike":
        competitor = get_latest_competitor_price(sku_id)
        new_price = round(competitor * random.uniform(1.3, 1.6), 2)
        reason_code = "ANOMALY_INJECTED_SPIKE"
    else:
        price_change_pct = random.uniform(-0.03, 0.03)
        new_price = round(old_price * (1 + price_change_pct), 2)
        reason_code = "ROUTINE_ADJUSTMENT"

    decision_id = str(uuid.uuid4())
    row = (
        decision_id, sku_id, fmt(event_time), old_price, new_price,
        reason_code, False, None, round(random.uniform(0.7, 0.99), 4), 0.0
    )
    conn.ext.insert_multi("decisions", [row])

    start = time.time()
    flagged, reason, severity = check_decision(conn, decision_id, sku_id, old_price, new_price)
    elapsed_ms = round((time.time() - start) * 1000, 2)

    if flagged:
        flag_decision(conn, decision_id, reason, severity)

    return decision_id, sku_id, old_price, new_price, flagged, reason, severity, elapsed_ms

if __name__ == "__main__":
    SKU_IDS = [f"SKU-{i:04d}" for i in range(1, 21)]

    print("Bot simulator + guardrail running. Press Ctrl+C to stop.")
    print("Type 'a' + Enter to inject a CRASH anomaly (below-cost) on the next decision.")
    print("Type 's' + Enter to inject a SPIKE anomaly (above-competitor) on the next decision.\n")

    inject_flag = {"type": None}

    def listen_for_input():
        while True:
            cmd = input().strip().lower()
            if cmd == "a":
                inject_flag["type"] = "crash"
                print(">> Crash anomaly armed for next decision.")
            elif cmd == "s":
                inject_flag["type"] = "spike"
                print(">> Spike anomaly armed for next decision.")

    threading.Thread(target=listen_for_input, daemon=True).start()

    while True:
        sku = random.choice(SKU_IDS)
        anomaly_type = inject_flag["type"]
        if anomaly_type:
            inject_flag["type"] = None  # reset after firing

        decision_id, sku_id, old_price, new_price, flagged, reason, severity, elapsed_ms = make_decision(sku, anomaly_type=anomaly_type)

        if flagged:
            print(f"[FLAGGED in {elapsed_ms}ms | severity {severity}] {sku_id}: {old_price} -> {new_price} | {reason}")
        else:
            print(f"[OK in {elapsed_ms}ms] {sku_id}: {old_price} -> {new_price}")

        time.sleep(2)