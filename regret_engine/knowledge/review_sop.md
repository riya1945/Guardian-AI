# Pricing Review - Standard Operating Procedure

**SOP set ID:** SOPS-2026-01
**Version:** 3.1
**Binds to:** PP-2026-04 v4.2, GRS-2026-02 v2.3
**Audience:** Pricing reviewers, category managers, audit
**Currency:** INR

---

## SOP-001 - Reviewer Workflow

Every flagged decision moves through the same seven steps. Steps may not be skipped or reordered.

1. **Intake.** Pull the decision from the queue in severity order - HIGH first, then MEDIUM, each ordered by SLA expiry under SOP-005. Never work the queue in arrival order.
2. **Bundle check.** Verify the evidence bundle against GR-008 before reading the proposal. An incomplete bundle ends the review at step 2 and routes to SOP-003 or SOP-004. Do not proceed to evaluate a proposal you cannot evidence.
3. **Recompute.** Independently recompute every fired statistic - breach percentage, z, demand trend, price move, deviation, days cover - from the raw input record. Do not accept the engine's computed value as the reviewed value. Recomputation catches the class of defect behind INC-2026-004 and INC-2026-005.
4. **Constraint test.** Check the proposal against `business_constraints.md` for the SKU's category, region and channel. A decision that clears the guardrails can still fail a constraint.
5. **Disposition.** Approve under SOP-002, reject under SOP-003, or escalate under SOP-004. There is no fourth option and no deferral.
6. **Notes.** Record the note set required by SOP-006. A disposition without notes is void and reopens at audit.
7. **Close.** Confirm the audit checklist in SOP-007 is complete, then close. Closure timestamps the SLA.

**Reviewer independence.** A reviewer may not review a decision they proposed, configured or requested. Where the queue offers no independent reviewer, the decision escalates under SOP-004 rather than waiting.

---

## SOP-002 - When to Approve

Approve only when **all** of the following hold:

- The evidence bundle is complete under GR-008.
- Every fired statistic has been independently recomputed and matches the engine value within rounding.
- No rule fired at HIGH.
- No two rules fired at MEDIUM. Two MEDIUM flags aggregate to HIGH under GR-007 and are outside approval authority.
- The proposal sits inside the SKU's approved band from BC-007 and inside the movement band from PP-002 appropriate to the reviewer's authority.
- Every category, regional, promotional and channel constraint in `business_constraints.md` is satisfied.
- Where a single MEDIUM flag fired, a documented justification exists that is traceable to a corpus source - a seasonal manifest reference under PP-007, a verified differential under PP-004, a clearance objective under PP-005, or a promotional commitment under BC-005.
- No check returned UNAVAILABLE, **or** the reviewer has recorded the substituting assumption and that assumption is conservative - it must not be more favourable to the proposal than the last known value.

**Approval authority by band**

| Movement band (PP-002) | Approval authority |
|---|---|
| Band A, up to ±4.0% | Engine auto-approval; reviewer sampling only |
| Band B, ±4.0% to ±12.0% | Pricing reviewer |
| Band C, ±12.0% to ±25.0% | Category manager under ESC-003 |
| Band D, beyond ±25.0% | Finance and category manager jointly under ESC-002 |

A reviewer who approves outside their band authority creates a void approval. The decision is reopened and the approval is recorded as an audit finding.

---

## SOP-003 - When to Reject

Reject when **any** of the following hold:

- The evidence bundle is incomplete under GR-008 and the missing element cannot be obtained inside the SLA.
- GR-001 fired at any severity and no valid co-funding reference is attached. Floor breaches have no exception path.
- GR-002 fired and no seasonal manifest reference under PP-007 applies, or the SKU is classified essential under PP-008 item 4.
- Recomputation disagrees with the engine's computed statistic beyond rounding. Reject and raise a defect; do not reconcile the difference yourself.
- The justification offered is not traceable to a corpus source. An unsupported justification is treated as absent.
- The proposal relies on a competitor observation older than 24 hours, or on a match that fails the exact-match attributes in PP-004.
- The proposal is justified solely by a single weekend or festival-eve demand spike, per PP-006.
- The proposal is one step in a sequence that would breach the rolling 7-day net movement limit in PP-002, even where each step sits inside Band A.
- The proposal falls under any prohibited behaviour in PP-008.

**Rejection is a complete disposition.** A rejected decision does not require an alternative price. Where the reviewer can identify a compliant alternative, it is recorded as a recommendation, not as a substitute approval.

---

## SOP-004 - When to Escalate

Escalate rather than dispose when **any** of the following hold:

- Any rule fired at HIGH. HIGH severity is outside reviewer authority in every case and routes under ESC-001.
- Two or more rules fired at MEDIUM, aggregating to HIGH under GR-007.
- The proposed movement exceeds the reviewer's band authority under SOP-002.
- A matched competitor price sits below our hard floor. This is a sourcing question, not a pricing question, and routes to the category manager under ESC-003 per PP-004.
- The decision would breach a stockout constraint under BC-003 or a regional constraint under BC-004.
- Customer harm or brand risk is plausible - refund exposure, essential-goods pricing during a disruption, or a pattern a customer would read as manipulation. Routes to ESC-005.
- No independent reviewer is available under SOP-001.
- The reviewer is uncertain. Uncertainty is a valid and sufficient escalation reason and must be recorded as such. Escalating on uncertainty is never a performance finding; approving on uncertainty always is.

---

## SOP-005 - SLA by Severity

SLAs run from the moment the decision enters the queue, on a 24×7 clock. Business hours do not pause the clock.

| Severity | Acknowledge | Disposition | Escalation response | Breach handling |
|---|---|---|---|---|
| **HIGH** | 15 minutes | 2 hours | 1 hour from escalation | Price is held, not applied, while the SLA runs. On breach, the proposal auto-rejects and the queue owner is paged. |
| **MEDIUM** | 2 hours | 8 hours | 4 hours from escalation | Price is held. On breach, the proposal auto-rejects and rolls into the next cycle. |
| **LOW** | Not applicable | Sampled weekly under PP-009 | Not applicable | Sample findings feed the weekly audit; no per-decision SLA. |

**Held, not applied.** A flagged price never goes live while its SLA runs. The failure to hold is what converted INC-2026-001 from a caught defect into an eleven-hour live exposure.

**Festive period.** During the October–November window in PP-007, HIGH disposition tightens to 1 hour and MEDIUM to 4 hours.

---

## SOP-006 - Required Notes

Every disposition carries a note set. Notes are structured, not free prose, and each field is mandatory.

1. **Rules cited.** Every rule identifier that fired, plus every contributing signal, with the recomputed statistic for each.
2. **Sources cited.** At least one identifier from `pricing_policy.md` or `business_constraints.md`. A disposition citing no source is void under PP-009.
3. **Recomputation result.** Stated as agree or disagree against the engine value, with the reviewer's own computed figures.
4. **Justification.** The specific claim being relied on, and the corpus source that supports it. Where no source supports it, state that plainly - the absence is itself the finding.
5. **Assumptions.** Every assumption substituted for an unavailable input, with the last known value and its age.
6. **Uncertainties.** What the reviewer could not determine from the available evidence. This field may not be left empty on a HIGH severity decision; if nothing is uncertain on a HIGH decision, the reviewer has not looked hard enough.
7. **Counterfactual.** The compliant alternative price and its predicted revenue, or an explicit statement that none was identified.
8. **INR impact.** Estimated regret in absolute rupees, not percentage alone, per PP-003.

**Prohibited note content.** Do not record inferred facts as observed facts. Do not record a justification the corpus does not support. Where a question cannot be answered from the retained corpus, record the gap.

---

## SOP-007 - Audit Checklist

Run before closing any decision. Every item is a yes-or-no check; any "no" blocks closure.

- [ ] Evidence bundle complete against GR-008 for every fired flag
- [ ] Every fired statistic independently recomputed and agreement recorded
- [ ] Severity aggregation verified against GR-007, including the two-MEDIUM rule and the unavailable-input cap
- [ ] Contributing signals from suppressed GR-003 recorded in the bundle
- [ ] Disposition sits inside the reviewer's band authority under SOP-002
- [ ] At least one policy or constraint identifier cited
- [ ] All eight note fields from SOP-006 populated
- [ ] Uncertainties field non-empty on HIGH severity decisions
- [ ] Assumptions recorded for every UNAVAILABLE check, with last known value and age
- [ ] INR regret impact stated in absolute rupees
- [ ] Reviewer independence confirmed under SOP-001
- [ ] SLA timestamps captured for acknowledge and disposition
- [ ] Escalation reference attached where SOP-004 applied
- [ ] Rollback reference attached where a live price was reversed
- [ ] Related incident register entry linked where the decision matches a known pattern

---

## SOP-008 - Reopening and Appeal

- **Audit reopening.** Any decision found non-compliant at the weekly audit under PP-009 is reopened. Reopening does not reverse a live price by itself; reversal requires ESC-004.
- **Proposer appeal.** The proposing team may appeal a rejection once, within 48 hours, by supplying the missing evidence. An appeal without new evidence is closed without review.
- **Standing.** A rejection stands while an appeal is open. There is no provisional approval.
- **Pattern escalation.** Three rejections on the same SKU within a rolling 30-day window remove that SKU from auto-pricing until the category manager reinstates it under ESC-003.
- **No retrospective approval.** A decision that went live without approval is recorded as an exposure event and reviewed on its outcome. It is never approved after the fact, because retrospective approval destroys the audit signal that PP-009 depends on.
