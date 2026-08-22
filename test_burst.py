import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import time
from app.db import get_connection
from app.guardrail import check_decision, flag_decision
from scripts.bot_simulator import make_decision

conn = get_connection()

TEST_SKU = "SKU-0005"

print(f"Firing 5 rapid decisions for {TEST_SKU} to trigger burst detection...\n")

for i in range(5):
    decision_id, sku_id, old_price, new_price, flagged, reason, severity, elapsed_ms = make_decision(TEST_SKU)
    if flagged:
        print(f"[FLAGGED in {elapsed_ms}ms | severity {severity}] {sku_id}: {old_price} -> {new_price} | {reason}")
    else:
        print(f"[OK in {elapsed_ms}ms] {sku_id}: {old_price} -> {new_price}")
    time.sleep(1)  # small gap, still well within the 10-minute burst window