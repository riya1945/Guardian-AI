DROP TABLE IF EXISTS outcomes;
DROP TABLE IF EXISTS decisions;
DROP TABLE IF EXISTS market_context;

CREATE TABLE market_context (
    sku_id          VARCHAR(50)     NOT NULL,
    event_time      TIMESTAMP       NOT NULL,
    demand_signal   DECIMAL(10,2),
    competitor_price DECIMAL(10,2),
    inventory_level INTEGER,
    cost_price      DECIMAL(10,2)
);

CREATE TABLE decisions (
    decision_id     VARCHAR(50)     NOT NULL,
    sku_id          VARCHAR(50)     NOT NULL,
    event_time      TIMESTAMP       NOT NULL,
    old_price       DECIMAL(10,2),
    new_price       DECIMAL(10,2),
    reason_code     VARCHAR(100),
    flagged         BOOLEAN         DEFAULT FALSE,
    flag_reason     VARCHAR(500),
    confidence      DECIMAL(5,4),
    severity        DECIMAL(5,4)
);

CREATE TABLE outcomes (
    decision_id     VARCHAR(50)     NOT NULL,
    units_sold      INTEGER,
    revenue         DECIMAL(12,2),
    margin          DECIMAL(12,2),
    time_window     VARCHAR(50)
);