# Pricing Incident Register - 2026

**Register ID:** IR-2026
**Maintained by:** Pricing Governance Council
**Classification basis:** `guardrail_rules.md` GRS-2026-02 v2.3
**Currency:** INR

Regret impact is reported as realised revenue loss against the best guardrail-feasible price over the exposure window, computed as `units_exposed × average per-unit revenue gap`.

---

## INC-2026-001 - Accessory floor breach during Republic Day window

- **Incident ID:** INC-2026-001
- **Date:** 2026-01-21
- **Impacted SKU / category:** SKU-1003 (tempered glass screen protector), CAT-MOB
- **Region / channel:** South zone, app channel
- **What happened:** The engine proposed ₹209 against an active floor of ₹239, a 12.55% breach. The proposal followed a competitor observation at ₹219 and a strong demand trend of +0.14. The price went live for 11 hours before the daily guardrail sweep caught it.
- **Guardrail flag:** GR-001 at HIGH. GR-003 recorded as a contributing signal at z = -3.76.
- **Regret impact:** ₹1,65,780 (1,842 units × ₹90 average per-unit revenue gap)
- **Root cause:** The Republic Day event manifest under PP-007 relaxes the movement band ceiling but does not relax the floor. The event configuration applied the band relaxation to the floor test as well, so the floor check evaluated against a relaxed value rather than the hard floor.
- **Remediation:** Event manifest schema changed so that floor values are immutable and cannot be referenced by a band relaxation key. Regression test added asserting that no event configuration can lower a floor. Sweep frequency for event-window SKUs raised from daily to hourly.
- **Reviewer decision:** Rejected and rolled back under ESC-004. Classified as a configuration defect, not reviewer error. No conduct finding.

---

## INC-2026-002 - Mixer grinder ceiling breach after cost-pass-through error

- **Incident ID:** INC-2026-002
- **Date:** 2026-02-07
- **Impacted SKU / category:** SKU-2001 (750W mixer grinder), CAT-SHK
- **Region / channel:** North zone, web channel
- **What happened:** A supplier cost update was applied as a price update. The live price moved from ₹3,199 to ₹4,499 in a single step - a 40.64% movement, well into Band D - against a ceiling of ₹4,249. Demand trend was already negative at -0.13 and the demand score was 0.25.
- **Guardrail flag:** GR-002 at HIGH (5.88% above ceiling). GR-003 contributing at z = 6.25.
- **Regret impact:** ₹1,89,720 (612 units × ₹310 average per-unit revenue gap)
- **Root cause:** The cost ingestion job and the price update job shared a common staging table. A schema change renamed the target column, and the cost job silently wrote into the price column. No Band D approval was sought because the movement was never surfaced as a movement - it entered as a data write, not as a decision.
- **Remediation:** Cost and price writes separated onto distinct tables with distinct service credentials. Every price mutation now must originate from a decision record with a decision ID; direct writes are rejected at the database layer. Band D movements now trigger a synchronous block pending ESC-002 approval.
- **Reviewer decision:** Rejected and rolled back within 90 minutes of detection. Escalated to finance under ESC-002 for margin restatement. Root cause assigned to platform engineering.

---

## INC-2026-003 - Air conditioner undercut on a mis-matched competitor listing

- **Incident ID:** INC-2026-003
- **Date:** 2026-03-04
- **Impacted SKU / category:** SKU-6002 (1.5 ton 3-star inverter air conditioner), CAT-CEL
- **Region / channel:** West zone, app and web channels
- **What happened:** The engine matched against a competitor listing at ₹34,999 that was in fact a 1 ton unit with a shorter compressor warranty. Believing itself to be materially above market, the engine drove the price down across three sub-threshold steps to ₹28,499, a 13.64% net move.
- **Guardrail flag:** GR-005 at HIGH (deviation -18.57%). The three individual steps each sat inside Band A and were not individually flagged.
- **Regret impact:** ₹2,10,900 (74 units × ₹2,850 average per-unit revenue gap)
- **Root cause:** Two failures compounded. First, the SKU matcher compared model family and star rating but not tonnage or warranty term, violating the exact-match requirement in PP-004. Second, the rolling 7-day net movement limit in PP-002 was defined in policy but was not implemented as an executable check, so the threshold-gaming pattern prohibited by PP-008 item 9 occurred without intent and without detection.
- **Remediation:** Matcher extended to require tonnage, pack size, warranty term and seller tier equality. Rolling 7-day net movement limit implemented as a blocking pre-check. Any negative deviation beyond 15% now forces a match-verification step before a price response is permitted.
- **Reviewer decision:** Rolled back to ₹32,999 under ESC-004. Category manager approval recorded under ESC-003 for the corrective move. Matching defect assigned to the price intelligence team.

---

## INC-2026-004 - Staple grocery markdown into thin cover

- **Incident ID:** INC-2026-004
- **Date:** 2026-04-14
- **Impacted SKU / category:** SKU-5002 (premium basmati rice 5kg), CAT-GRO
- **Region / channel:** East zone, quick-commerce channel
- **What happened:** Price was cut from ₹799 to ₹749, a 6.26% reduction, while regional inventory stood at 320 units against a 7-day run rate of 700 units - 3.2 days of cover. The SKU stocked out 31 hours later and remained unavailable in the region for four days.
- **Guardrail flag:** GR-006 at HIGH (days_cover 3.2 with a 6.26% cut).
- **Regret impact:** ₹1,43,220 (3,410 units × ₹42 average per-unit revenue gap, measured across the discount window and the subsequent unavailability window)
- **Root cause:** The inventory field passed to the guardrail engine carried the national position, not the East zone position, contrary to the regional evaluation requirement in PP-005 and BC-004. Nationally the SKU held 21 days of cover, so the rule evaluated as a pass.
- **Remediation:** Inventory input contract changed to require a region key alongside the unit count. Decisions submitted without a region key are now rejected at the contract boundary rather than defaulting to national. Regional cover dashboards added to the reviewer console.
- **Reviewer decision:** Rejected retrospectively. Price restored to ₹799 on replenishment. Stockout recorded against the BC-003 constraint. No conduct finding; classified as a data-scope defect.

---

## INC-2026-005 - Serum price spike on a stale demand signal

- **Incident ID:** INC-2026-005
- **Date:** 2026-02-23
- **Impacted SKU / category:** SKU-4001 (vitamin C face serum 30ml), CAT-BPC
- **Region / channel:** All zones, app channel
- **What happened:** Price moved from ₹599 to ₹759 in one step, a 26.71% increase, against a historical average of ₹549. The move stayed just under the ₹779 ceiling and so did not trip GR-002, but the z-score reached 4.78.
- **Guardrail flag:** GR-003 at HIGH (z = 4.78).
- **Regret impact:** ₹3,32,320 (268 units × ₹1,240 average per-unit revenue gap, aggregated across the affected serum sub-catalogue rather than the single SKU)
- **Root cause:** A single influencer-driven weekend spike was ingested as a sustained demand shift. PP-006 requires weekend spikes to be treated as transient, but the demand feature pipeline computed the 7-day rolling window with weekend days double-counted following a timezone conversion bug, inflating the apparent trend.
- **Remediation:** Timezone handling standardised to IST across the demand feature pipeline with an assertion that each calendar day contributes exactly once to the rolling window. Transient-spike suppression implemented as an explicit filter rather than an assumed property of the window. Ceiling-adjacent moves - those landing within 5% of the ceiling - now require the same evidence bundle as a ceiling breach.
- **Reviewer decision:** Rejected. Price restored to ₹599. Escalated to the category manager under ESC-003 given the size of the aggregated impact. Pipeline defect assigned to the demand modelling team.

---

## INC-2026-006 - Apparel price raised into a collapsing trend

- **Incident ID:** INC-2026-006
- **Date:** 2026-08-07
- **Impacted SKU / category:** SKU-3001 (men's cotton casual shirt), CAT-APR
- **Region / channel:** All zones, web channel
- **What happened:** Price moved from ₹849 to ₹949, an 11.78% increase, while the demand trend stood at -0.38 and the demand score had fallen to 0.02. Both values were available in the decision record at the time of proposal.
- **Guardrail flag:** GR-004 at HIGH (demand_trend -0.38 with an 11.78% upward move).
- **Regret impact:** ₹1,85,380 (1,196 units × ₹155 average per-unit revenue gap)
- **Root cause:** The proposal was generated by a margin-recovery routine that optimised contribution margin per unit in isolation, without reading the demand trend feature at all. The routine was operating on the correct objective from PP-001 item 3 but had no access to item 4, so it could not evaluate the revenue consequence of the volume it was destroying.
- **Remediation:** Margin-recovery routine now required to consume the same feature vector as the primary engine. GR-004 promoted from a post-hoc analytical flag to a blocking pre-check at HIGH severity. Demand score below 0.20 now hard-blocks any upward movement per PP-006.
- **Reviewer decision:** Rejected. Price restored to ₹849. Classified as a model-scope defect. The reviewer who had approved the initial proposal was found to have followed SOP correctly on the evidence presented; the evidence bundle itself was incomplete under GR-008, which is now the tracked finding.

---

## INC-2026-007 - Soundbar ceiling breach during a monsoon promotion

- **Incident ID:** INC-2026-007
- **Date:** 2026-06-30
- **Impacted SKU / category:** SKU-6003 (Bluetooth soundbar), CAT-CEL
- **Region / channel:** South and West zones, app channel
- **What happened:** Price moved from ₹8,999 to ₹9,799 against a ceiling of ₹9,199 - a 6.52% breach - after a promotional bundle was withdrawn and the bundle discount was removed from the effective price without the list price being reset.
- **Guardrail flag:** GR-002 at HIGH (6.52% above ceiling). GR-003 contributing at z = 6.35.
- **Regret impact:** ₹2,85,600 (51 units × ₹5,600 average per-unit revenue gap)
- **Root cause:** PP-002 requires movement bands to be measured on the pre-discount list price. The promotional system stored the bundle price as the list price for the duration of the promotion. On withdrawal, the system restored the pre-bundle list price and separately re-applied a scheduled uplift, compounding two movements into one.
- **Remediation:** Promotional systems prohibited from mutating list price; bundle discounts now carry as a separate effective-price layer. Promotion withdrawal now emits an explicit decision record that is evaluated by the full rule set rather than being treated as a restoration.
- **Reviewer decision:** Rejected and rolled back to ₹8,999 under ESC-004. Customer harm review conducted under ESC-005; 51 affected orders were issued price-difference refunds. Recorded as a brand-risk event.

---

## INC-2026-008 - Cooking oil undercut below floor on a competitor error

- **Incident ID:** INC-2026-008
- **Date:** 2026-07-05
- **Impacted SKU / category:** SKU-5001 (cold-pressed groundnut oil 5L), CAT-GRO
- **Region / channel:** North and West zones, all channels
- **What happened:** A competitor listed the product at ₹1,099, which was itself below our landed cost position. The engine proposed ₹929 against a floor of ₹999 - a 7.0% breach - in an attempt to undercut, producing a competitor deviation of -15.47%.
- **Guardrail flag:** GR-001 at HIGH and GR-005 at HIGH, firing together. GR-003 contributing at z = -3.20.
- **Regret impact:** ₹85,120 (2,240 units × ₹38 average per-unit revenue gap)
- **Root cause:** The competitor price was genuine but was a limited-quantity loss-leader listing. PP-004 states that a competitor price below our hard floor is not actionable and must be routed to the category manager for a sourcing or assortment response. That routing existed as policy but the engine had no branch implementing it, so the only available response was a price response.
- **Remediation:** Non-actionable competitor branch implemented. Where a matched competitor price sits below our floor, the engine now emits a sourcing-escalation record under ESC-003 and holds price. Loss-leader detection added on quantity-limited listings.
- **Reviewer decision:** Rejected before going live - the combined GR-001 and GR-005 flags produced a HIGH severity block. Recorded as a near-miss with regret measured on the holding period rather than on live exposure. Sourcing escalation raised to the category manager, who renegotiated landed cost the following month.
