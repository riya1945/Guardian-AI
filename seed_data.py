import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import random
import uuid
from datetime import datetime, timedelta
from app.db import get_connection

conn = get_connection()

NUM_SKUS = 20
DAYS_OF_HISTORY = 90
SKU_IDS = [f"SKU-{i:04d}" for i in range(1, NUM_SKUS + 1)]

sku_base_price = {sku: round(random.uniform(200, 2000), 2) for sku in SKU_IDS}
sku_cost = {sku: round(sku_base_price[sku] * random.uniform(0.5, 0.7), 2) for sku in SKU_IDS}

market_rows = []
decision_rows = []
outcome_rows = []

start_date = datetime.now() - timedelta(days=DAYS_OF_HISTORY)

def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

for sku in SKU_IDS:
    base_price = sku_base_price[sku]
    cost = sku_cost[sku]
    current_price = base_price

    for day in range(DAYS_OF_HISTORY):
        event_time = start_date + timedelta(days=day, hours=random.randint(0, 23))

        demand_signal = round(random.uniform(0.3, 1.0), 2)
        competitor_price = round(base_price * random.uniform(0.9, 1.1), 2)
        inventory_level = random.randint(10, 500)

        market_rows.append((sku, fmt(event_time), demand_signal, competitor_price, inventory_level, cost))

        old_price = current_price
        price_change_pct = random.uniform(-0.03, 0.03)
        new_price = round(old_price * (1 + price_change_pct), 2)
        current_price = new_price

        decision_id = str(uuid.uuid4())
        decision_rows.append((
            decision_id, sku, fmt(event_time), old_price, new_price,
            "ROUTINE_ADJUSTMENT", False, None, round(random.uniform(0.7, 0.99), 4), 0.0
        ))

        units_sold = max(0, int(random.gauss(50 * demand_signal, 10)))
        revenue = round(units_sold * new_price, 2)
        margin = round(units_sold * (new_price - cost), 2)
        outcome_rows.append((decision_id, units_sold, revenue, margin, "1_DAY"))

conn.execute("DELETE FROM market_context")
conn.execute("DELETE FROM outcomes")
conn.execute("DELETE FROM decisions")

conn.ext.insert_multi("market_context", market_rows)
conn.ext.insert_multi("decisions", decision_rows)
conn.ext.insert_multi("outcomes", outcome_rows)

print(f"Inserted {len(market_rows)} market_context rows")
print(f"Inserted {len(decision_rows)} decision rows")
print(f"Inserted {len(outcome_rows)} outcome rows")

sample = conn.execute("SELECT * FROM decisions LIMIT 5").fetchall()
print("Sample decisions:", sample)