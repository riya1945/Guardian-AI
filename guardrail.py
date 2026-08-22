import statistics
from app.db import get_connection

Z_SCORE_THRESHOLD = 3.0        # flag if price change is >3 std deviations from normal
COMPETITOR_CEILING_MULT = 1.25  # flag if priced >25% above competitor
BURST_WINDOW_MINUTES = 10
BURST_MAX_CHANGES = 3


def get_recent_price_changes(conn, sku_id, limit=30):
    """Get recent % price changes for a SKU to establish 'normal' behavior."""
    rows = conn.execute(f"""
        SELECT old_price, new_price FROM decisions
        WHERE sku_id = '{sku_id}' AND reason_code = 'ROUTINE_ADJUSTMENT'
        ORDER BY event_time DESC
        LIMIT {limit}
    """).fetchall()

    pct_changes = []
    for old_price, new_price in rows:
        old_price, new_price = float(old_price), float(new_price)
        if old_price > 0:
            pct_changes.append((new_price - old_price) / old_price)
    return pct_changes


def get_latest_cost(conn, sku_id):
    result = conn.execute(f"""
        SELECT cost_price FROM market_context
        WHERE sku_id = '{sku_id}'
        ORDER BY event_time DESC
        LIMIT 1
    """).fetchone()
    return float(result[0]) if result else None


def get_latest_competitor_price(conn, sku_id):
    result = conn.execute(f"""
        SELECT competitor_price FROM market_context
        WHERE sku_id = '{sku_id}'
        ORDER BY event_time DESC
        LIMIT 1
    """).fetchone()
    return float(result[0]) if result else None


def check_burst_pattern(conn, sku_id, window_minutes=BURST_WINDOW_MINUTES, max_changes=BURST_MAX_CHANGES):
    """Flags if a SKU has had too many price changes in a short window — signals a runaway bot."""
    result = conn.execute(f"""
        SELECT COUNT(*) FROM decisions
        WHERE sku_id = '{sku_id}'
        AND event_time >= ADD_SECONDS(CURRENT_TIMESTAMP, -{window_minutes * 60})
    """).fetchone()
    count = result[0] if result else 0
    if count > max_changes:
        reason = f"{count} price changes for {sku_id} in {window_minutes} min (possible runaway bot)"
        return True, reason, 0.7
    return False, None, 0.0


def check_decision(conn, decision_id, sku_id, old_price, new_price):
    """
    Runs guardrail checks on a single decision.
    Returns (flagged: bool, flag_reason: str or None, severity: float 0-1)
    """
    old_price, new_price = float(old_price), float(new_price)

    # --- Check 1: cost floor violation ---
    cost = get_latest_cost(conn, sku_id)
    if cost is not None and new_price < cost:
        pct_below = round((cost - new_price) / cost, 3)
        reason = f"Price {new_price} is below cost {cost} (cost floor violation, {pct_below*100:.1f}% under)"
        severity = min(1.0, 0.6 + pct_below)
        return True, reason, severity

    # --- Check 2: competitor ceiling violation ---
    competitor_price = get_latest_competitor_price(conn, sku_id)
    if competitor_price is not None and new_price > competitor_price * COMPETITOR_CEILING_MULT:
        pct_above = round((new_price - competitor_price) / competitor_price, 3)
        reason = f"Price {new_price} is {pct_above*100:.1f}% above competitor price {competitor_price}"
        severity = min(1.0, 0.4 + pct_above)
        return True, reason, severity

    # --- Check 3: statistical deviation from normal behavior ---
    history = get_recent_price_changes(conn, sku_id)
    if len(history) >= 5:
        mean = statistics.mean(history)
        stdev = statistics.stdev(history)
        if stdev > 0:
            actual_change = (new_price - old_price) / old_price
            z_score = abs((actual_change - mean) / stdev)
            if z_score > Z_SCORE_THRESHOLD:
                reason = f"Price change z-score {round(z_score, 2)} exceeds threshold {Z_SCORE_THRESHOLD}"
                severity = min(1.0, z_score / 10)
                return True, reason, severity

    # --- Check 4: burst pattern (too many changes in a short window) ---
    burst_flagged, burst_reason, burst_severity = check_burst_pattern(conn, sku_id)
    if burst_flagged:
        return True, burst_reason, burst_severity

    return False, None, 0.0


def flag_decision(conn, decision_id, flag_reason, severity=0.0):
    """Update a decision row as flagged, with the reason and severity."""
    safe_reason = flag_reason.replace("'", "''")  # basic SQL escaping
    conn.execute(f"""
        UPDATE decisions
        SET flagged = TRUE, flag_reason = '{safe_reason}', severity = {severity}
        WHERE decision_id = '{decision_id}'
    """)