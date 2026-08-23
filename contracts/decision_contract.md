# Decision Data Contracts

**Contract set ID:** DCS-2026-01
**Version:** 1.4
**Binds to:** PP-2026-04 v4.2, GRS-2026-02 v2.3, BCS-2026-03 v3.4
**Currency:** INR throughout. All monetary fields are rupee values, never paise, never a normalised unit.
**Timezone:** All timestamps are ISO-8601 with an explicit `+05:30` offset. Naive timestamps are rejected at the boundary.

Contracts are versioned with the rule set. A decision is always evaluated against the contract version in force when it was submitted, per the mid-cycle prohibition in PP-010.

---

## 1. Decision Input

The raw record submitted to the guardrail engine. This is the only accepted entry point for a price mutation; direct writes to the price store are rejected at the database layer following the remediation in INC-2026-002.

```json
{
  "decision_id": "string",
  "timestamp": "ISO-8601 string",
  "sku": "string",
  "price": "number",
  "previous_units": "number",
  "previous_price": "number",
  "rolling_7d_units": "number",
  "rolling_30d_units": "number",
  "demand_trend": "number",
  "demand_momentum": "number",
  "day_of_week": "integer 0-6",
  "month": "integer 1-12",
  "year": "integer",
  "is_weekend": "integer 0 or 1",
  "historical_avg_price": "number",
  "demand_score": "number|null",
  "competitor_price": "number|null",
  "inventory": "number|null",
  "season": "string|null"
}
```

### Field semantics

| Field | Semantics |
|---|---|
| `decision_id` | Unique, immutable. Format `dec_NNNN`. Reused identifiers are rejected; retired identifiers are never recycled, per PP-010 |
| `timestamp` | Moment of proposal, not of application. Starts the SLA clock under SOP-005 |
| `sku` | Must exist in the BC-007 registry. Absence is a hard block, never a category fallback |
| `price` | Proposed price. Tested against the SKU floor and ceiling from BC-007 by GR-001 and GR-002 |
| `previous_units` | Units sold in the previous pricing period. Denominator for `demand_momentum` |
| `previous_price` | Currently live price. Denominator for `price_move` in GR-004 and GR-006 |
| `rolling_7d_units` | Trailing 7-day unit sales |
| `rolling_30d_units` | Trailing 30-day unit sales expressed as a **weekly-equivalent mean**, so that it is directly comparable to `rolling_7d_units` |
| `demand_trend` | `(rolling_7d_units - rolling_30d_units) / rolling_30d_units`, per PP-006. Input to GR-004 |
| `demand_momentum` | `(rolling_7d_units - previous_units) / previous_units`, per PP-006 |
| `day_of_week` | Monday = 0 through Sunday = 6 |
| `is_weekend` | 1 where `day_of_week` is 5 or 6, else 0. Must agree with `day_of_week` |
| `historical_avg_price` | 90-day volume-weighted mean from BC-007. The `hist` term in GR-003; `sigma = 0.08 × hist` |
| `demand_score` | Bounded 0–1 composite, `clamp(0.5 + 1.5 × demand_trend + 0.5 × demand_momentum, 0.02, 0.99)`. Values below 0.20 hard-block upward movement under PP-006 |
| `competitor_price` | Matched competitor observation, valid 24 hours. Null means unavailable, not unchanged - see below |
| `inventory` | Units at **fulfilment-region** level, never national, per BC-004 and the INC-2026-004 remediation |
| `season` | One of `winter`, `summer`, `monsoon`, `festive`, mapped from `month` per PP-007 |

### Validation rules

1. `decision_id` unique; `sku` present in BC-007; `price`, `previous_price` and `historical_avg_price` all strictly positive.
2. `month`, `year` and `day_of_week` must agree with `timestamp`; `is_weekend` must agree with `day_of_week`.
3. `demand_trend` and `demand_momentum` are recomputed at the boundary from the unit fields. A submitted value disagreeing beyond rounding is rejected as a defect, not silently corrected - this is the boundary equivalent of the reviewer recomputation in SOP-001 step 3.
4. A region key must accompany every submission. Records without one are rejected at the boundary rather than defaulting to national inventory.
5. **Null handling.** `demand_score`, `competitor_price`, `inventory` and `season` are nullable. A null is a declared absence, never a zero and never a carried-forward value. The dependent rule returns `UNAVAILABLE`, and GR-007 step 3 caps the decision at MEDIUM severity so that it cannot be auto-approved.

---

## 2. Regret Output

Produced for every decision, flagged or not. Regret is measured against the best price in the **guardrail-feasible set** `[floor, ceiling]` from BC-007 - never against an unconstrained optimum, because an unconstrained optimum is not an action the reviewer could have taken.

```json
{
  "decision_id": "string",
  "sku": "string",
  "actual_price": "number",
  "best_price": "number",
  "actual_predicted_demand": "number",
  "best_predicted_demand": "number",
  "actual_predicted_revenue": "number",
  "best_predicted_revenue": "number",
  "regret": "number",
  "regret_percentage": "number",
  "decision_quality": "GOOD|QUESTIONABLE|HIGH_REGRET",
  "currency": "INR",
  "alternatives": [
    {
      "price": "number",
      "predicted_demand": "number",
      "predicted_revenue": "number",
      "is_selected": "boolean",
      "is_best": "boolean"
    }
  ]
}
```

### Computation

```
predicted_demand(p) = max(0, rolling_7d_units × (1 + beta × (hist - p) / hist))
predicted_revenue(p) = p × predicted_demand(p)
best_price            = argmax over p in [floor, ceiling] of predicted_revenue(p)
regret                = max(0, best_predicted_revenue - actual_predicted_revenue)
regret_percentage     = 100 × regret / best_predicted_revenue
```

`beta` is the category demand response coefficient: CAT-MOB 1.4, CAT-SHK 1.1, CAT-APR 1.5, CAT-BPC 1.2, CAT-GRO 0.9, CAT-CEL 0.7.

### Quality bands

| Band | `regret_percentage` |
|---|---|
| `GOOD` | Below 3.0 |
| `QUESTIONABLE` | 3.0 to 10.0 inclusive |
| `HIGH_REGRET` | Above 10.0 |

### Contract constraints

- `regret` is never negative. A price outside the band cannot earn credit for revenue the reviewer was not permitted to pursue.
- `alternatives` must contain exactly one entry with `is_selected` true and exactly one with `is_best` true. Both may be the same entry when the selected price is optimal.
- Every price in `alternatives` must lie inside `[floor, ceiling]`, except the selected entry, which carries the actual proposed price even where that price breaches a band.
- `currency` is always the literal `"INR"`.
- **Scope limitation.** Regret prices realised revenue only. It does not price stockout cost, lost future margin, substitution loss, search-ranking penalty, or brand and trust exposure. Per BC-003 and the GR-006 notes, a low regret figure is not evidence that a decision was acceptable. `decision_quality` and guardrail severity are independent measures and must always be read together.

---

## 3. Explanation Output

The grounded narrative returned to reviewers and to the dashboard. Every claim must be traceable to a retrieved corpus source.

```json
{
  "status": "grounded|insufficient_evidence",
  "summary": "string",
  "decision": "string",
  "regret_score": "number",
  "confidence": "number",
  "key_factors": [
    {
      "factor": "string",
      "impact": "positive|negative|neutral",
      "magnitude": "number",
      "evidence": "string"
    }
  ],
  "supporting_evidence": [
    {
      "source": "string",
      "title": "string",
      "content": "string",
      "relevance_score": "number"
    }
  ],
  "counterfactual": "string",
  "alternative_action": "string",
  "uncertainties": ["string"],
  "explanation": "string"
}
```

### Field semantics

| Field | Semantics |
|---|---|
| `status` | `grounded` when every claim is supported by a retrieved source. `insufficient_evidence` when it is not |
| `regret_score` | Regret as a fraction of best feasible revenue, 0 to 1. Equals `regret_percentage / 100` |
| `confidence` | 0 to 1. Reflects retrieval quality and input completeness, not the strength of the recommendation |
| `key_factors[].evidence` | A source identifier such as `GR-001`, `BC-003`, `PP-004`, `SOP-003`, `ESC-002`, `INC-2026-004` or `DEC-007`. Free-text evidence is invalid |
| `supporting_evidence[].source` | The document identifier the passage was retrieved from |
| `counterfactual` | What the outcome would have been at `best_price` |
| `alternative_action` | The compliant action recommended instead, or an explicit statement that none was identified, per SOP-006 item 7 |
| `uncertainties` | What could not be determined from the retrieved corpus. May not be empty on a HIGH severity decision, per SOP-006 item 6 |

### Grounding rules

1. Every claim in `explanation` and in `key_factors` must trace to an entry in `supporting_evidence`. Untraceable claims void the explanation under PP-009.
2. Where the corpus does not support an answer, `status` is `insufficient_evidence`, `supporting_evidence` is an empty array, and the returned text is exactly:

   `This information is not found in the uploaded documents`

3. An `insufficient_evidence` response must not be padded with general knowledge, plausible inference, or a partial answer assembled from unrelated sources. Recording the gap is the required behaviour under PP-009 and SOP-006.
4. `confidence` below 0.40 on a `grounded` status routes the decision to escalation under SOP-004 on the uncertainty ground, rather than being returned as a low-confidence answer.
5. Reducing `confidence` is never a substitute for setting `status` to `insufficient_evidence`.

---

## 4. Dashboard Feed Item

The composite object rendered in the reviewer console and the audit feed.

```json
{
  "decision_id": "string",
  "timestamp": "ISO-8601 string",
  "sku": "string",
  "price": "number",
  "recommendation": "string",
  "regret_score": "number",
  "regret_percentage": "number",
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": "number",
  "input": "Decision input object",
  "regret": "Regret output object",
  "factors": ["DecisionFactor objects"],
  "assumptions": ["string"],
  "uncertainties": ["string"],
  "explanation": "Explanation output object|null"
}
```

### Field semantics

| Field | Semantics |
|---|---|
| `recommendation` | The disposition surfaced to the reviewer: approve, reject, or escalate, per SOP-002, SOP-003 and SOP-004. Advisory - it never applies a price |
| `risk_level` | The GR-007 aggregate severity. Governs queue ordering and SLA under SOP-005 |
| `regret_score` | Fraction, 0 to 1. `regret_percentage` is the same quantity expressed per hundred; both are carried so that consumers do not rescale and drift apart |
| `factors` | The `key_factors` array from the explanation object, each carrying its own evidence identifier |
| `assumptions` | One entry for every `UNAVAILABLE` check, stating the field, the substituted assumption, and the last known value with its age, per SOP-006 item 5 |
| `uncertainties` | Mirrors the explanation object. Non-empty on every HIGH item |
| `explanation` | Null while generation is pending. A null explanation blocks approval but does not pause the SLA clock |

### Feed constraints

- `risk_level` must equal the GR-007 aggregation over the flags recorded against the decision. A feed item whose displayed risk disagrees with the recorded rule set is a defect and blocks closure under SOP-007.
- `regret_score` and `regret_percentage` must agree: `regret_percentage = 100 × regret_score`.
- Queue ordering is severity first, then SLA expiry - never arrival order, per SOP-001 step 1.
- A HIGH item is never rendered with an approve recommendation. HIGH is outside reviewer authority in every case under SOP-004 and routes through ESC-001.
- Feed items are immutable once closed. Corrections are issued as new decision records, never as edits, so that the audit trail required by PP-009 remains reconstructible.
