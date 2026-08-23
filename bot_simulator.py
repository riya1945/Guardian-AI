import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import random
import uuid
import time
import threading
import requests
from datetime import datetime
from app.db import get_connection
from app.guardrail import check_decision, flag_decision

conn = get_connection()

INTEGRATION_URL = os.getenv(
    "INTEGRATION_URL",
    "https://guardian-ai-ragex.onrender.com/integrations/guardrail-decision",
)

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

def get_latest_market_context(sku_id):
    """Returns (cost_price, competitor_price, demand_signal, inventory_level) for a SKU."""
    result = conn.execute(f"""
        SELECT cost_price, competitor_price, demand_signal, inventory_level
        FROM market_context
        WHERE sku_id = '{sku_id}'
        ORDER BY event_time DESC
        LIMIT 1
    """).fetchone()
    if result:
        cost_price, competitor_price, demand_signal, inventory_level = result
        return (
            float(cost_price) if cost_price is not None else 300.0,
            float(competitor_price) if competitor_price is not None else 500.0,
            float(demand_signal) if demand_signal is not None else 0.5,
            int(inventory_level) if inventory_level is not None else 100,
        )
    return 300.0, 500.0, 0.5, 100

def push_to_integration(payload):
    """Send the flagged/unflagged decision to the shared handoff endpoint. Non-blocking failure — logs and continues."""
    try:
        response = requests.post(INTEGRATION_URL, json=payload, timeout=3)
        if response.status_code >= 400:
            print(f"  [integration warning] {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"  [integration error] Could not reach {INTEGRATION_URL}: {e}")

def make_decision(sku_id, anomaly_type=None):
    old_price = get_latest_price(sku_id)
    cost, competitor_price, demand_signal, inventory_level = get_latest_market_context(sku_id)
    event_time = datetime.now()

    if anomaly_type == "crash":
        new_price = round(cost * random.uniform(0.5, 0.8), 2)
        reason_code = "ANOMALY_INJECTED_CRASH"
    elif anomaly_type == "spike":
        new_price = round(competitor_price * random.uniform(1.3, 1.6), 2)
        reason_code = "ANOMALY_INJECTED_SPIKE"
    else:
        price_change_pct = random.uniform(-0.03, 0.03)
        new_price = round(old_price * (1 + price_change_pct), 2)
        reason_code = "ROUTINE_ADJUSTMENT"

    decision_id = str(uuid.uuid4())
    confidence = round(random.uniform(0.7, 0.99), 4)

    row = (
        decision_id, sku_id, fmt(event_time), old_price, new_price,
        reason_code, False, None, confidence, 0.0
    )
    conn.ext.insert_multi("decisions", [row])

    start = time.time()
    flagged, reason, severity = check_decision(conn, decision_id, sku_id, old_price, new_price)
    elapsed_ms = round((time.time() - start) * 1000, 2)

    if flagged:
        flag_decision(conn, decision_id, reason, severity)

    # --- Build and send the shared handoff payload ---
    payload = {
        "decision_id": decision_id,
        "sku_id": sku_id,
        "event_time": fmt(event_time),
        "old_price": old_price,
        "new_price": new_price,
        "reason_code": reason_code,
        "flagged": flagged,
        "flag_reason": reason,
        "confidence": confidence,
        "severity": severity,
        "demand_signal": demand_signal,
        "competitor_price": competitor_price,
        "inventory_level": inventory_level,
    }
    push_to_integration(payload)

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
            inject_flag["type"] = None

        decision_id, sku_id, old_price, new_price, flagged, reason, severity, elapsed_ms = make_decision(sku, anomaly_type=anomaly_type)

        if flagged:
            print(f"[FLAGGED in {elapsed_ms}ms | severity {severity}] {sku_id}: {old_price} -> {new_price} | {reason}")
        else:
            print(f"[OK in {elapsed_ms}ms] {sku_id}: {old_price} -> {new_price}")

        time.sleep(2)
