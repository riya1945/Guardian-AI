# Dynamic Pricing Policy - Marketplace Retail

**Policy ID:** PP-2026-04
**Version:** 4.2
**Effective from:** 2026-01-01
**Owner:** Pricing Governance Council
**Review cycle:** Quarterly
**Applies to:** All first-party and marketplace-managed listings across app, web and quick-commerce channels
**Currency:** INR (all amounts in this policy are Indian Rupees unless stated otherwise)

---

## PP-001 - Pricing Objective

The pricing engine optimises for **maximum realised revenue in INR, net of regret**, subject to every guardrail defined in `guardrail_rules.md` and every constraint defined in `business_constraints.md`.

Objective hierarchy, in strict priority order:

1. **Compliance.** No price may violate a hard floor, hard ceiling, or statutory display requirement. Compliance is never traded against revenue.
2. **Customer trust.** No price movement may create a pattern that a reasonable customer would experience as manipulation.
3. **Margin protection.** Category margin targets in BC-002 are protected before volume is pursued.
4. **Revenue maximisation.** Within the remaining feasible price band, the engine selects the price with the highest predicted revenue.
5. **Volume and share.** Pursued only where 1–4 are already satisfied.

Regret is the measured gap in INR between realised revenue at the selected price and predicted revenue at the best guardrail-feasible price. The engine is evaluated on regret, not on raw revenue, because raw revenue rewards guardrail breaches that are later rolled back.

---

## PP-002 - Approved Price Movement Bands

A price movement is the change between the currently live price and the proposed price for the same SKU on the same channel.

| Band | Movement vs live price | Approval path |
|---|---|---|
| Band A - Auto | Up to ±4.0% | Engine may apply without human review |
| Band B - Reviewed | Above ±4.0% and up to ±12.0% | Requires reviewer approval per SOP-002 |
| Band C - Escalated | Above ±12.0% and up to ±25.0% | Requires category manager approval per ESC-003 |
| Band D - Restricted | Above ±25.0% | Requires finance and category manager joint approval per ESC-002 |

Additional movement limits:

- No SKU may move more than **three times in a rolling 24-hour window** on the same channel.
- No SKU may accumulate more than **±18.0% net movement in a rolling 7-day window** without a Band C approval, even if every individual step sat inside Band A.
- A movement that crosses a psychological price point downward and then reverses upward within 72 hours is treated as Band C regardless of magnitude.
- Movement bands are measured on the pre-discount list price, not on the post-coupon effective price.

---

## PP-003 - INR Margin Rules

- Every SKU carries a **landed cost** maintained by the merchandising finance team. Landed cost includes purchase price, inbound freight, storage accrual and expected return provision. Landed cost values are held in the finance master and are not published to the pricing corpus.
- The **hard floor** for a SKU is derived as `landed_cost / (1 - minimum_margin_pct)` and is refreshed on the first business day of every month.
- Minimum margin percentages by category are defined in BC-002. The engine may never propose a price below the derived hard floor, irrespective of competitor position or demand signal.
- Where a promotional co-funding agreement exists, the co-funded amount may be added back before the floor test is applied, but only when the funding reference is attached to the decision record. Unreferenced co-funding claims are rejected under SOP-003.
- Contribution margin in INR, not margin percentage, is the reporting unit for incident regret. A 2% margin loss on a ₹32,999 air conditioner is materially different from 2% on a ₹299 accessory, and the review record must reflect the absolute INR impact.
- Negative contribution margin is prohibited under all circumstances, including clearance and end-of-life liquidation. Liquidation below floor requires a separate write-down approval outside the pricing engine.

---

## PP-004 - Competitor Price Treatment

- Competitor prices are ingested from the price intelligence feed and are considered **valid for 24 hours**. A competitor observation older than 24 hours must be treated as unavailable, not as unchanged.
- Matching is permitted only on an **exact SKU match**: same manufacturer part number, same pack size, same warranty term, same seller tier. Near-match undercutting is prohibited under PP-008.
- The engine may respond to a competitor price only within the feasible band already established by the floor, ceiling and margin rules. A competitor price below our hard floor is **not actionable** and must be routed to the category manager under ESC-003 for an assortment or sourcing response rather than a price response.
- Deviation from the matched competitor price beyond the thresholds in GR-005 requires documented justification. Acceptable justifications are: verified delivery speed advantage, verified warranty or service differential, verified bundle content differential, or an active co-funded promotion.
- Where the competitor price field is null, the competitor check is recorded as **unavailable**. The decision cannot be auto-approved and is capped at MEDIUM severity per GR-007.
- Competitor observations from unverified scraping sources may inform analysis but may not be cited as the sole evidence for a price movement.

---

## PP-005 - Inventory-Sensitive Pricing Rules

- Inventory cover is expressed in days: `inventory_units / (rolling_7d_units / 7)`.
- **Below 7 days cover:** downward price movement is prohibited without reviewer approval. Cutting price into thin cover converts available margin into an accelerated stockout.
- **Below 4 days cover:** any downward movement of 3.0% or more is a HIGH severity breach under GR-006 and must be rejected or escalated.
- **Below 25 units absolute:** the SKU is flagged regardless of cover ratio, because low absolute counts make the cover ratio unstable.
- **Above 60 days cover:** downward movement inside Band A is encouraged to release working capital, provided the floor and margin tests pass.
- Inventory is evaluated at the **fulfilment-region level**, not nationally. A SKU with healthy national cover may still be constrained in a single region under BC-004.
- Where the inventory field is null, the inventory check is recorded as unavailable and the decision is capped at MEDIUM severity per GR-007.

---

## PP-006 - Demand-Sensitive Pricing Rules

- Demand trend is measured as `(rolling_7d_units - rolling_30d_units) / rolling_30d_units`, where the 30-day figure is expressed as a weekly-equivalent mean so that both terms are comparable.
- Demand momentum is measured as `(rolling_7d_units - previous_units) / previous_units`.
- **Rising demand (trend ≥ +0.20):** downward price movement of 4.0% or more is presumed to be leaving revenue on the table and is flagged under GR-004. Discounting into demand strength must be justified by an inventory clearance objective or a documented promotional commitment.
- **Falling demand (trend ≤ -0.15):** upward price movement of 4.0% or more is presumed to accelerate the decline and is flagged under GR-004.
- **Severe demand deterioration (trend ≤ -0.35)** combined with an upward movement of 8.0% or more is a HIGH severity breach.
- The demand score is a bounded 0–1 composite derived from trend and momentum. A demand score below 0.20 must not be used to justify an upward price movement.
- Weekend and festival-eve demand spikes are treated as transient. A price increase justified solely by a single weekend spike is rejected under SOP-003.

---

## PP-007 - Seasonal Exceptions

Recognised seasonal windows and the exceptions they carry:

- **Republic Day sale window (15–26 January):** Band B ceiling relaxed to ±15.0% for participating SKUs listed in the event manifest. Floors are not relaxed.
- **Summer peak (March–May):** cooling and hydration categories may operate at the upper half of their approved band without a GR-003 spike escalation, provided the movement stays inside Band B and a seasonal manifest reference is attached.
- **Monsoon clearance (June–September):** apparel and footwear may run extended markdowns inside Band C with category manager approval. The hard floor still applies.
- **Independence Day / Freedom sale window (8–17 August):** same relaxation as the Republic Day window.
- **Festive period (October–November):** the highest-traffic window. Movement bands are unchanged, but the audit sampling rate doubles under PP-009 and every HIGH severity flag is auto-escalated under ESC-001.

Seasonal exceptions never relax: the hard floor, the negative-margin prohibition, the stockout constraints in BC-003, or the prohibited behaviours in PP-008.

---

## PP-008 - Prohibited Pricing Behaviour

The following are prohibited without exception:

1. **Below-floor pricing** of any kind, including matching a competitor who is selling below our landed cost.
2. **Negative contribution margin** pricing.
3. **Reference price inflation** - raising the struck-through list price purely to manufacture a larger apparent discount.
4. **Surge pricing on essentials** - no upward movement beyond Band A on staple grocery, sanitation or basic medical supply SKUs during a declared weather, transport or civic disruption event.
5. **Personalised price discrimination** - differentiating price by an individual customer's browsing history, device type, or inferred willingness to pay. Regional and channel differentials permitted under BC-004 and BC-006 are pricing by market, not by person, and remain allowed.
6. **Near-match undercutting** - pricing against a competitor listing that differs in pack size, warranty or bundle content.
7. **Coordinated signalling** - any pricing action designed to communicate intent to a competitor.
8. **Silent rollback** - reversing a price without recording the reversal in the audit trail.
9. **Threshold gaming** - decomposing a single intended movement into multiple sub-threshold steps to stay inside Band A.
10. **Flag suppression** - disabling, muting or re-scoping a guardrail rule to allow a specific decision to pass.

Items 1, 2, 4, 5 and 10 are treated as conduct breaches, not pricing errors, and are routed under ESC-005.

---

## PP-009 - Audit Requirements

- **Retention.** Every decision record, guardrail evaluation, reviewer action and rollback is retained for 24 months in immutable storage.
- **Traceability.** Every reviewer decision must cite at least one rule identifier from `guardrail_rules.md` and at least one constraint identifier from `business_constraints.md`. A decision citing no source is void and is reopened.
- **Evidence completeness.** The evidence bundle defined in GR-008 must be attached before a decision is closed. Decisions closed without a complete bundle are reopened at the weekly audit.
- **Sampling.** A minimum 5% random sample of LOW severity auto-approvals is reviewed weekly. Sampling rises to 10% during the festive period defined in PP-007.
- **Full review.** 100% of HIGH severity decisions and 100% of rollbacks are reviewed, regardless of outcome.
- **Reconciliation.** Realised revenue is reconciled against predicted revenue monthly. A SKU whose realised-versus-predicted gap exceeds 15% for two consecutive months is removed from auto-pricing until the demand model is refitted.
- **Unsupported claims.** Where a question about a decision cannot be answered from the retained corpus, the reviewer records the gap rather than inferring an answer. Inferred answers are an audit finding.

---

## PP-010 - Change Control

- Any change to a floor, ceiling, movement band or guardrail threshold requires a version increment to this policy and a corresponding entry in the guardrail rule set.
- Threshold changes take effect at the start of the next pricing cycle, never mid-cycle, so that a single decision is never evaluated against two rule versions.
- Emergency threshold changes are permitted only under ESC-004 and expire automatically after 72 hours unless ratified by the Pricing Governance Council.
- Deprecated rule identifiers are retired, never reused, so that historical decisions remain interpretable.
