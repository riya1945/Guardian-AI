# Pricing Escalation Rules

**Escalation set ID:** ESCS-2026-01
**Version:** 2.0
**Binds to:** PP-2026-04 v4.2, GRS-2026-02 v2.3, SOPS-2026-01 v3.1
**Currency:** INR

---

## ESC-001 - HIGH Severity Escalation Matrix

Every HIGH severity decision escalates. Reviewers have no approval authority at HIGH under SOP-004. The routing depends on which rule fired.

| Triggering condition | Primary approver | Secondary approver | Response SLA | Default disposition if SLA breached |
|---|---|---|---|---|
| **GR-001** floor breach at HIGH | Category manager (ESC-003) | Finance (ESC-002) if breach > 5% of floor | 1 hour | Auto-reject, price held |
| **GR-002** ceiling breach at HIGH | Category manager (ESC-003) | Brand risk lead (ESC-005) if SKU is essential | 1 hour | Auto-reject, price held |
| **GR-003** z-score spike at HIGH | Pricing lead | Category manager (ESC-003) if movement enters Band C | 1 hour | Auto-reject, price held |
| **GR-004** rolling drift at HIGH | Category manager (ESC-003) | Demand modelling lead for feature verification | 2 hours | Auto-reject, price held |
| **GR-005** competitor deviation at HIGH | Category manager (ESC-003) | Sourcing lead where the competitor sits below our floor | 2 hours | Auto-reject, price held |
| **GR-006** low inventory at HIGH | Supply planning lead | Category manager (ESC-003) | 1 hour | Auto-reject, price held; replenishment ticket raised |
| **Two or more MEDIUM flags** aggregating to HIGH under GR-007 | Category manager (ESC-003) | Per the highest-ranked constituent rule above | 1 hour | Auto-reject, price held |
| **Any HIGH during the festive window** (PP-007) | Category manager (ESC-003) | Pricing Governance Council notified | 30 minutes | Auto-reject, price held |

**Standing rules for all HIGH escalations**

- The price is **held, not applied**, for the entire escalation window. There is no provisional go-live.
- The escalation record must carry the complete GR-008 evidence bundle. An escalation with an incomplete bundle is returned, and the return does not pause the SLA.
- Approval at escalation must cite the specific policy provision relied on. An escalation approval that cites no source is void under PP-009 exactly as a reviewer approval would be.
- Approvers may approve, reject, or approve a modified price. A modified price re-enters the rule set as a new decision and is evaluated afresh - it does not inherit the escalation's approval.

---

## ESC-002 - Finance Approval Rules

Finance approval is required - jointly with the category manager - when any of the following hold.

- **Band D movement.** Any proposed movement beyond ±25.0% of the live price, per PP-002.
- **Deep floor breach.** A GR-001 breach greater than 5% of the floor value.
- **Margin restatement.** Any decision whose remediation requires restating recognised margin, as occurred in INC-2026-002.
- **Aggregate exposure.** Any single decision, or any related set of decisions on one SKU inside a rolling 7-day window, with estimated regret above **₹2,00,000**.
- **Portfolio exposure.** Cumulative estimated regret above **₹10,00,000** across a category inside a rolling 30-day window, regardless of individual decision severity.
- **Co-funding claims.** Any floor add-back claimed under PP-003 where the co-funding reference exceeds ₹1,00,000 in value.
- **Write-down.** Any liquidation below floor. Finance approves the write-down separately; the pricing engine is never the approval path for below-cost disposal.

**Finance approval constraints**

- Finance may approve exposure. Finance may **not** approve a prohibited behaviour under PP-008 - those items have no approval path at any level.
- Finance approval expires after 72 hours if the price has not gone live.
- Finance approval is recorded against a decision ID, never against a SKU. A subsequent decision on the same SKU requires its own approval.

---

## ESC-003 - Category Manager Approval Rules

The category manager is the default approver for HIGH severity pricing decisions and the sole approver for Band C movements.

**Scope of authority**

- Band C movements: above ±12.0% and up to ±25.0%, per PP-002.
- HIGH severity flags under GR-001, GR-002, GR-004, GR-005 and the GR-007 aggregation, subject to the secondary approvers in ESC-001.
- Seasonal manifest exceptions under PP-007, including monsoon clearance markdowns inside Band C.
- Reinstatement of a SKU removed from auto-pricing under SOP-008.
- Sourcing and assortment responses where a matched competitor price sits below our hard floor, per PP-004. This is the intended path for the pattern behind INC-2026-008.

**Limits of authority**

- The category manager may **not** approve below the hard floor. No role can. The floor is a boundary of the system, not a threshold of authority.
- The category manager may not approve Band D movements alone; those require finance under ESC-002.
- The category manager may not approve a decision with an incomplete GR-008 evidence bundle.
- The category manager may not approve their own proposal, per the independence requirement in SOP-001.

**Required record**

Every category manager approval records: the decision ID, the rules that fired with recomputed statistics, the policy provision relied on, the estimated INR regret, the expected duration of the price, and the rollback trigger that would reverse it.

---

## ESC-004 - Emergency Rollback Rules

Emergency rollback reverses a live price outside the normal decision cycle.

**Who may trigger**

Any of: pricing reviewer, pricing lead, category manager, supply planning lead, brand risk lead, or the on-call platform engineer. Rollback authority is deliberately broad because the cost of a delayed rollback exceeds the cost of an unnecessary one.

**Mandatory rollback triggers**

Rollback is not discretionary where any of these are observed on a live price:

1. A live price below the hard floor, for any duration.
2. A live price above the ceiling on a SKU classified essential under PP-008 item 4.
3. Any live price resulting from a direct data write rather than a decision record, the pattern behind INC-2026-002.
4. Any live price where the underlying competitor match is found to be invalid under PP-004, the pattern behind INC-2026-003.
5. A stockout attributable to a live markdown under BC-003, the pattern behind INC-2026-004.
6. Any live price arising from a suppressed or disabled guardrail rule, prohibited under PP-008 item 10.

**Rollback target**

- Roll back to the **last known compliant price**, not to the historical average and not to a newly optimised price.
- Where the last known compliant price is itself under question, roll back to the SKU floor plus the category minimum margin, and raise a fresh decision.
- The rollback is recorded as its own decision record with its own decision ID. Silent rollback is prohibited under PP-008 item 8.

**Post-rollback obligations**

- Rollback confirmation within **30 minutes** of trigger.
- Incident register entry opened within **4 hours**, even where no customer was affected. INC-2026-008 is registered as a near-miss on exactly this basis.
- Root cause recorded within **5 business days**.
- 100% review of all rollbacks under PP-009, with no sampling exemption.

**Emergency threshold changes.** Where a rollback requires a temporary threshold change, that change is permitted under PP-010 but expires automatically after 72 hours unless the Pricing Governance Council ratifies it.

---

## ESC-005 - Customer Harm and Brand Risk Handling

This path handles decisions where the exposure is to customer trust rather than, or in addition to, revenue.

**Triggers**

- A live price above the ceiling on an essential SKU during a declared weather, transport or civic disruption event - prohibited under PP-008 item 4.
- Any evidence of personalised price discrimination under PP-008 item 5.
- Reference price inflation under PP-008 item 3.
- A price pattern a reasonable customer would experience as manipulation, including the psychological-point reversal pattern in PP-002 and the threshold-gaming pattern in PP-008 item 9.
- Any customer-facing price error where orders were placed at the erroneous price, as in INC-2026-007.
- Any external escalation - regulatory query, consumer forum complaint, or sustained public complaint volume on a single SKU.

**Handling sequence**

1. **Contain.** Trigger ESC-004 rollback immediately. Containment precedes analysis; do not wait for root cause.
2. **Quantify.** Identify every affected order, the price paid, and the compliant price. Report the exposure in absolute INR.
3. **Remedy.** Where customers paid above the compliant price, issue price-difference refunds. Refunds are not discretionary and do not require a business case. INC-2026-007 issued 51 refunds on this basis.
4. **Notify.** Brand risk lead within 1 hour. Where refunds exceed 100 orders or ₹5,00,000 in aggregate, the Pricing Governance Council is notified the same day.
5. **Record.** Open an incident register entry classified as a brand-risk event. Brand-risk events are reported separately from revenue incidents and are never netted against revenue gains.

**Conduct breaches**

Items 1, 2, 4, 5 and 10 of PP-008 are conduct breaches rather than pricing errors. These route directly to ESC-005 and to the Pricing Governance Council, bypassing the normal reviewer queue entirely. Conduct breaches have no approval path, no seasonal exception, and no SLA-expiry auto-disposition - they remain open until the Council closes them.

---

## ESC-006 - Escalation Records and Documentation

- Every escalation carries a unique escalation reference linked to the originating decision ID.
- The escalation record inherits the full GR-008 evidence bundle and adds: escalation reason under SOP-004, approver role, approver disposition, policy provision cited, and disposition timestamp.
- Escalation records are retained for 24 months alongside decision records under PP-009.
- An escalation that expires on SLA without disposition is recorded as an auto-reject, with the expiry itself as the recorded reason. Expiry is never recorded as an approval.
- Escalation volume by rule is reported monthly. A rule generating a sustained escalation volume without a corresponding rejection rate is reviewed for threshold recalibration under PP-010 - a rule that escalates everything and rejects nothing is a miscalibrated rule, not a working control.
