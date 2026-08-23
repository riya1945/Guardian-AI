# Pricing Guardrail Rule Set

**Rule set ID:** GRS-2026-02
**Version:** 2.3
**Binds to policy:** PP-2026-04 v4.2
**Evaluation order:** GR-001 → GR-002 → GR-003 → GR-004 → GR-005 → GR-006 → GR-007
**Currency:** INR

Shared symbols used across all rules:

```
price          = proposed price (INR)
prev_price     = currently live price (INR)
floor          = SKU hard floor from BC-007 (INR)
ceiling        = SKU hard ceiling from BC-007 (INR)
hist           = historical_avg_price for the SKU (INR)
sigma          = 0.08 * hist          # 30-day price dispersion proxy
r7             = rolling_7d_units
r30            = rolling_30d_units    # weekly-equivalent mean over trailing 30 days
comp           = competitor_price (INR, nullable)
inv            = inventory units (nullable)
price_move     = (price - prev_price) / prev_price
demand_trend   = (r7 - r30) / r30
days_cover     = inv / (r7 / 7)
```

---

## GR-001 - Floor Breach

**Intent:** Prevent any price below the margin-derived hard floor. Implements PP-003.

```
condition:  price < floor
breach_pct: (floor - price) / floor
severity:
  MEDIUM  if 0 < breach_pct <= 0.02
  HIGH    if breach_pct > 0.02
blocking:   true          # never auto-approved at any severity
```

**Notes**

- The floor is a hard boundary, not a soft target. There is no promotional, seasonal or competitive exception.
- A floor breach caused by an approved co-funded promotion must carry the funding reference; the funded amount is added back before the test is applied, per PP-003.
- Where a floor breach and a competitor deviation fire together, the pricing response is blocked and the case is routed to the category manager under ESC-003.

---

## GR-002 - Ceiling Breach

**Intent:** Prevent prices above the approved band ceiling. Implements PP-002 and BC-001.

```
condition:  price > ceiling
exceed_pct: (price - ceiling) / ceiling
severity:
  MEDIUM  if 0 < exceed_pct <= 0.02
  HIGH    if exceed_pct > 0.02
blocking:   true
```

**Notes**

- Ceiling breaches carry brand and trust risk as well as revenue risk. A ceiling breach on a staple or essential SKU during a declared disruption event is a conduct breach under PP-008 item 4 and routes to ESC-005, not to a normal reviewer queue.
- A MEDIUM ceiling breach is not a minor event. Ceiling breaches sit above the revenue-maximising price by construction, so they typically carry the highest regret in the portfolio even when the breach percentage is small.

---

## GR-003 - Z-Score Spike

**Intent:** Detect abnormal single-step movement relative to the SKU's own price history. Operationalises the movement bands in PP-002.

```
z:          (price - hist) / sigma          # sigma = 0.08 * hist
condition:  abs(z) >= 2.5
severity:
  MEDIUM  if 2.5 <= abs(z) < 3.5
  HIGH    if abs(z) >= 3.5
blocking:   true at HIGH, reviewable at MEDIUM
```

**Suppression rule**

When GR-001 or GR-002 has already fired on the same decision, GR-003 is recorded as a **contributing signal** rather than as an independent flag. This prevents a single large movement from being counted twice in the severity aggregation of GR-007. The contributing signal is still written to the evidence bundle and still appears in the reviewer's explanation.

**Notes**

- `sigma` is a fixed proportional proxy rather than a fitted standard deviation, so the rule remains evaluable for SKUs with sparse price history.
- A high positive z with a demand score below 0.20 is the classic pattern behind INC-2026-002 and INC-2026-006.

---

## GR-004 - Rolling Drift

**Intent:** Detect price movement that runs against the demand signal. Implements PP-006.

```
condition:
  (price_move >= 0.04  AND demand_trend <= -0.15)     # raising into falling demand
  OR
  (price_move <= -0.04 AND demand_trend >= 0.20)      # discounting into rising demand
severity:
  MEDIUM  by default
  HIGH    if abs(demand_trend) >= 0.35 AND abs(price_move) >= 0.08
blocking:   true at HIGH, reviewable at MEDIUM
```

**Notes**

- The downward arm of this rule is a revenue-protection rule, not a compliance rule: discounting into rising demand is legal but is the single largest recurring source of regret in the portfolio.
- The upward arm is a demand-protection rule: raising price into a collapsing trend converts a slow decline into a stall.
- Transient weekend spikes are excluded from the demand trend input, per PP-006.

---

## GR-005 - Competitor Deviation

**Intent:** Keep prices within a defensible distance of the matched competitor listing. Implements PP-004.

```
precondition: comp is not null AND observation age <= 24 hours
deviation:    (price - comp) / comp
condition:    abs(deviation) > 0.07
severity:
  MEDIUM  if 0.07 < abs(deviation) <= 0.15
  HIGH    if abs(deviation) > 0.15
blocking:   true at HIGH, reviewable at MEDIUM
```

**Unavailable handling**

If `comp` is null, or the observation is older than 24 hours, the rule returns **UNAVAILABLE**. An unavailable check is not a pass. Per GR-007 the decision is capped at MEDIUM severity and may not be auto-approved.

**Notes**

- Positive deviation (we are more expensive) carries conversion risk. Negative deviation (we are cheaper) carries margin risk and may indicate a mis-matched SKU pairing.
- A negative deviation beyond 15% should first be checked for a matching error under PP-004 before it is treated as a genuine competitive gap.

---

## GR-006 - Low Inventory

**Intent:** Prevent price actions that accelerate stockout. Implements PP-005 and BC-003.

```
precondition: inv is not null
days_cover:   inv / (r7 / 7)

condition_high:    days_cover < 4  AND price_move <= -0.03
condition_medium:  days_cover < 7  AND price_move < 0
condition_absolute: inv <= 25                       # evaluated regardless of price direction

severity:
  HIGH    if condition_high
  MEDIUM  if condition_medium or condition_absolute
blocking:   true at HIGH, reviewable at MEDIUM
```

**Unavailable handling**

If `inv` is null the rule returns **UNAVAILABLE** and GR-007 caps the decision at MEDIUM.

**Notes**

- Evaluation is at fulfilment-region level per PP-005. National cover may mask a regional constraint under BC-004.
- Revenue regret systematically **understates** the harm from this rule, because the regret model prices realised revenue only and does not price the lost future margin, the substitution loss, or the search-ranking penalty that follows a stockout. A GR-006 HIGH decision with low measured regret is still a bad decision.

---

## GR-007 - Severity Mapping and Aggregation

**Intent:** Convert the set of fired rules into a single decision-level risk level.

```
rank:  LOW = 0, MEDIUM = 1, HIGH = 2

step 1  severity = max(severity of all fired flags), default LOW
step 2  if severity == MEDIUM and count(MEDIUM flags) >= 2:  severity = HIGH
step 3  if any check returned UNAVAILABLE and severity < MEDIUM:  severity = MEDIUM
step 4  contributing signals (suppressed GR-003) do not participate in steps 1-2
```

### Severity definitions

| Level | Meaning | Default disposition |
|---|---|---|
| **LOW** | No rule fired and every check was evaluable. Price sits inside the approved band, movement is inside Band A or justified inside Band B, and no demand, competitor or inventory signal is adverse. | Auto-approve, subject to the 5% audit sample in PP-009 |
| **MEDIUM** | Exactly one rule fired at MEDIUM, or a required input was unavailable. The decision is defensible but not self-evident. | Reviewer approval required within the SOP-005 SLA |
| **HIGH** | Any rule fired at HIGH, or two or more rules fired at MEDIUM. The decision carries material revenue, margin, stockout or trust exposure. | Reject or escalate under ESC-001. Never auto-approved |

### Aggregation notes

- Step 2 exists because independent MEDIUM signals are rarely independent in practice. A small floor breach that is also a large competitive undercut is a sourcing problem, not two small pricing problems.
- Step 3 exists because a missing input is an unmeasured risk, not an absent one.
- Severity is a property of the decision, not of the SKU. A SKU may produce LOW decisions daily and one HIGH decision in a single cycle.

---

## GR-008 - Required Evidence by Flag

Every flagged decision must carry a complete evidence bundle before it can be closed. Bundles are validated at the weekly audit under PP-009.

### Common evidence - required for every flag

- Full decision input record, including all nullable fields with their null state preserved.
- Rule identifier, computed statistic, threshold applied, and rule set version.
- Timestamp of evaluation in IST with offset.
- Reviewer identity role and disposition.
- Citation of at least one policy or constraint identifier.

### Flag-specific evidence

| Flag | Additional required evidence |
|---|---|
| **GR-001** Floor breach | Current landed cost reference ID, active floor value and its effective date, minimum margin percentage applied from BC-002, co-funding reference if the breach is claimed to be funded |
| **GR-002** Ceiling breach | Active ceiling value and effective date, category band from BC-001, seasonal manifest reference if a PP-007 window is claimed, essential-SKU classification check per PP-008 item 4 |
| **GR-003** Z-score spike | `hist`, computed sigma, computed z, prior 30-day price series reference, movement band classification from PP-002 |
| **GR-004** Rolling drift | `r7`, `r30`, computed demand_trend, computed price_move, demand score, and either the clearance objective reference or the promotional commitment reference being relied on |
| **GR-005** Competitor deviation | Competitor observation ID, observation timestamp, SKU match attributes verified (part number, pack size, warranty term, seller tier), computed deviation, and the differential justification claimed under PP-004 |
| **GR-006** Low inventory | Region-level inventory snapshot, computed days_cover, open replenishment PO reference and expected receipt date, regional constraint check from BC-004 |
| **Unavailable check** | Field name, reason for unavailability, last known value with its age, and the assumption the reviewer applied in its place |

### Bundle completeness

A bundle missing any required element is **incomplete**. Incomplete bundles cannot support an approval. A reviewer facing an incomplete bundle must reject under SOP-003 or escalate under SOP-004 - never approve on the assumption that the missing element would have passed.
