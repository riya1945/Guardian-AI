# Worked Decision Examples

**Example set ID:** DES-2026-01
**Version:** 1.6
**Binds to:** PP-2026-04 v4.2, GRS-2026-02 v2.3, SOPS-2026-01 v3.1, BCS-2026-03 v3.4
**Currency:** INR

Each example maps to a decision record held in the decision store. Regret score is expressed as a fraction of the best guardrail-feasible revenue; regret is also stated in absolute INR per PP-003. Decision quality bands are: GOOD below 3% regret, QUESTIONABLE from 3% to 10%, HIGH_REGRET above 10%.

Six examples are good decisions and six are bad decisions. Note that guardrail status and regret are **independent** measures - DEC-012 is a bad decision with a low regret figure, and DEC-002 is a good decision with a large absolute regret figure. Reading either measure alone produces the wrong conclusion.

---

# Part A - Good Decisions

## DEC-001 - Routine uplift inside band, kettle

- **Decision ID:** DEC-001 (record `dec_0004`)
- **Input context:** SKU-2002, 1.5L electric kettle, CAT-SHK. 2026-01-26, winter. Live price ₹1,249. Rolling 7-day 74 units against a 30-day weekly-equivalent mean of 70, demand trend +0.06, demand score 0.60. Competitor observed at ₹1,339. Inventory 420 units, 39.7 days cover.
- **Proposed price:** ₹1,299
- **Guardrail status:** LOW. No rule fired. Price sits inside the ₹999–₹1,749 band, z = 0.50, competitor deviation -2.99%, cover well inside the healthy range.
- **Regret score:** 0.008 (₹743, 0.8%, GOOD). Best guardrail-feasible price ₹1,192.
- **Explanation:** The movement is +4.00%, which lands marginally outside Band A and therefore required pricing reviewer approval under the SOP-002 authority table even though the severity was LOW. This distinction matters: severity governs whether a rule fired, while the movement band governs who may approve. The reviewer approved because every check was evaluable, no flag fired, and the competitor position gave headroom. The residual regret reflects the engine sitting slightly above the modelled revenue optimum, which is acceptable inside a ₹743 gap on a category whose target margin is 22%.
- **Evidence source IDs:** PP-002, BC-001, BC-002, BC-007, GR-007, SOP-002

## DEC-002 - Hold-and-nudge on a television, large absolute regret accepted

- **Decision ID:** DEC-002 (record `dec_0013`)
- **Input context:** SKU-6001, 43-inch 4K smart television, CAT-CEL. 2026-03-17, summer. Live price ₹26,499. Rolling 7-day 55 units, 30-day mean 52, demand trend +0.06, demand score 0.61. Competitor observed at ₹27,499. Inventory 240 units, 30.5 days cover.
- **Proposed price:** ₹26,999
- **Guardrail status:** LOW. No rule fired. Movement +1.89% is inside Band A. z = 0.48. Competitor deviation -1.82%.
- **Regret score:** 0.021 (₹30,943, 2.1%, GOOD). Best guardrail-feasible price ₹31,570.
- **Explanation:** The absolute regret is the largest of any LOW severity decision in the set, but the percentage sits inside the GOOD band because CAT-CEL turns over high rupee values per unit. The model's suggested optimum of ₹31,570 would require a +19.1% movement, which is Band C and would need category manager approval under ESC-003, and it would breach the ±6.0% regional differential in BC-004 against zones already priced near ₹27,000. The decision was correct given the feasible set actually available to the reviewer, not the feasible set the unconstrained model assumed. This example is retained specifically because a large INR regret figure on a compliant decision is often misread as an error.
- **Evidence source IDs:** PP-002, BC-002, BC-004, BC-007, GR-007, ESC-003

## DEC-003 - Essential staple held flat through summer

- **Decision ID:** DEC-003 (record `dec_0016`)
- **Input context:** SKU-5001, cold-pressed groundnut oil 5L, CAT-GRO, classified essential staple. 2026-04-02, summer. Live price ₹1,229. Rolling 7-day 500 units, 30-day mean 480, demand trend +0.04, demand score 0.57. Competitor observed at ₹1,279. Inventory 3,100 units, 43.4 days cover.
- **Proposed price:** ₹1,249
- **Guardrail status:** LOW. No rule fired. Movement +1.63%, inside Band A. z = 0.00 - the proposal sits exactly at the 90-day historical average. Competitor deviation -2.35%.
- **Regret score:** 0.0028 (₹1,735, 0.28%, GOOD). Best guardrail-feasible price ₹1,318.
- **Explanation:** A deliberately unambitious decision on an essential staple. The engine had headroom to ₹1,318 but CAT-GRO carries an 8.0% minimum margin, the disruption-event restriction in PP-008 item 4, and the tightest customer-trust exposure in the portfolio. Holding at the historical average keeps the SKU well clear of every threshold and produces a regret figure under ₹2,000. On essentials, staying boring is the objective.
- **Evidence source IDs:** PP-008, BC-002, BC-003, BC-007, GR-007, SOP-002

## DEC-004 - Air fryer nudge with healthy cover

- **Decision ID:** DEC-004 (record `dec_0022`)
- **Input context:** SKU-2003, 4L air fryer, CAT-SHK. 2026-05-06, summer. Live price ₹4,699. Rolling 7-day 82 units, 30-day mean 80, demand trend +0.03, demand score 0.56. Competitor observed at ₹4,899. Inventory 320 units, 27.3 days cover.
- **Proposed price:** ₹4,799
- **Guardrail status:** LOW. No rule fired. Movement +2.13%, Band A. z = 0.27. Competitor deviation -2.04%. Cover inside the BC-003 healthy range.
- **Regret score:** 0.0049 (₹1,888, 0.49%, GOOD). Best guardrail-feasible price ₹4,485.
- **Explanation:** A small uplift into flat demand, taken while still sitting ₹100 below the matched competitor. Every input was evaluable, so no unavailable-input cap applied under GR-007 step 3. The modelled optimum is below the proposed price, meaning the engine gave up a small amount of predicted volume to hold the competitive gap - a trade the reviewer accepted and documented under SOP-006 item 7 rather than leaving implicit.
- **Evidence source IDs:** PP-004, BC-003, BC-007, GR-005, GR-007, SOP-006

## DEC-005 - Basmati rice uplift on deep cover

- **Decision ID:** DEC-005 (record `dec_0034`)
- **Input context:** SKU-5002, premium basmati rice 5kg, CAT-GRO, classified essential staple. 2026-07-11, monsoon. Live price ₹749. Rolling 7-day 660 units, 30-day mean 640, demand trend +0.03, demand score 0.56. Competitor observed at ₹789. Inventory 4,200 units, 44.5 days cover.
- **Proposed price:** ₹769
- **Guardrail status:** LOW. No rule fired. Movement +2.67%, Band A. z = 0.33. Competitor deviation -2.53%.
- **Regret score:** 0.0007 (₹370, 0.07%, GOOD). Best guardrail-feasible price ₹791.
- **Explanation:** The lowest regret figure in the example set. The proposal sits ₹22 below the modelled optimum and ₹20 below the matched competitor, on a SKU with 44.5 days of cover and no disruption event declared in any zone. This is the shape the engine should produce by default: a small move, a fully evaluable input record, and a regret figure small enough that the reviewer's time is better spent on the HIGH queue.
- **Evidence source IDs:** PP-006, BC-003, BC-004, BC-007, GR-007

## DEC-006 - Mixer grinder markdown correctly stopped on thin cover

- **Decision ID:** DEC-006 (record `dec_0023`)
- **Input context:** SKU-2001, 750W mixer grinder, CAT-SHK. 2026-05-11, summer. Live price ₹3,299. Rolling 7-day 210 units, 30-day mean 190, demand trend +0.11, demand score 0.69. Competitor observed at ₹3,199. Inventory 165 units against a 30-unit daily run rate - **5.5 days cover**.
- **Proposed price:** ₹3,149
- **Guardrail status:** MEDIUM. GR-006 fired at MEDIUM: cover below 7 days combined with a downward movement of -4.55%. No other rule fired, so no aggregation to HIGH under GR-007 step 2.
- **Regret score:** 0.010 (₹6,314, 1.0%, GOOD). Best guardrail-feasible price ₹2,863.
- **Explanation:** This is a good decision on process, not on proposal. The revenue model favoured the cut - the modelled optimum sits below the proposed price - but BC-003 makes thin cover binding regardless of what the revenue model prefers. The reviewer rejected the markdown under SOP-003, recorded the replenishment PO reference, and recommended revisiting after receipt. The guardrail did exactly the job it exists to do: it stopped a revenue-positive proposal that would have converted 5.5 days of cover into a stockout. The same pattern with national rather than regional inventory produced INC-2026-004.
- **Evidence source IDs:** GR-006, GR-007, BC-003, BC-007, SOP-003, INC-2026-004

---

# Part B - Bad Decisions

## DEC-007 - Groundnut oil driven below floor to chase a loss-leader

- **Decision ID:** DEC-007 (record `dec_0033`)
- **Input context:** SKU-5001, cold-pressed groundnut oil 5L, CAT-GRO, essential staple. 2026-07-05, monsoon. Live price ₹1,199. Rolling 7-day 640 units, 30-day mean 560, demand trend +0.14, demand score 0.74. Competitor observed at ₹1,099. Inventory 3,400 units, 37.2 days cover. Active floor ₹999.
- **Proposed price:** ₹929
- **Guardrail status:** HIGH. GR-001 fired at HIGH - a 7.01% breach of the ₹999 floor. GR-005 fired at HIGH - competitor deviation -15.47%. Two HIGH flags. GR-003 recorded as a contributing signal at z = -3.20, suppressed from the aggregation under the GR-003 suppression rule.
- **Regret score:** 0.0872 (₹69,924, 8.72%, QUESTIONABLE). Best guardrail-feasible price ₹1,318.
- **Explanation:** The competitor price of ₹1,099 sat below our own hard floor. PP-004 is explicit that a competitor price below the floor is not actionable and must route to the category manager for a sourcing response. The engine had no branch implementing that routing and so produced the only response available to it - a price response - which drove ₹70 below the floor. The correct disposition was rejection and a sourcing escalation under ESC-003. This decision is the pattern registered as INC-2026-008.
- **Evidence source IDs:** GR-001, GR-005, GR-003, PP-003, PP-004, BC-002, BC-007, ESC-003, INC-2026-008

## DEC-008 - Mixer grinder pushed through the ceiling on a cost write

- **Decision ID:** DEC-008 (record `dec_0006`)
- **Input context:** SKU-2001, 750W mixer grinder, CAT-SHK. 2026-02-07, winter. Live price ₹3,199. Rolling 7-day 150 units against a 30-day mean of 172, demand trend **-0.13**, demand score 0.25. Competitor observed at ₹4,299. Inventory 380 units, 17.7 days cover. Active ceiling ₹4,249.
- **Proposed price:** ₹4,499
- **Guardrail status:** HIGH. GR-002 fired at HIGH - 5.88% above ceiling. GR-003 recorded as a contributing signal at z = 6.25. Movement of +40.64% is Band D under PP-002 and required joint finance and category manager approval under ESC-002, which was never sought.
- **Regret score:** 0.3267 (₹1,47,314, 32.67%, HIGH_REGRET). Best guardrail-feasible price ₹2,863.
- **Explanation:** The worst regret percentage in the example set, and a textbook illustration of why ceiling breaches are expensive by construction: the price sat ₹1,636 above the modelled revenue optimum on a SKU whose demand was already declining at -0.13 with a demand score of 0.25. Under PP-006 a demand score below 0.20 hard-blocks upward movement; at 0.25 this proposal cleared that specific test while still being obviously wrong on every other reading. The proposal never entered as a decision at all - it arrived as a direct data write, which is why no band check ran. Registered as INC-2026-002.
- **Evidence source IDs:** GR-002, GR-003, GR-007, PP-002, PP-006, BC-001, BC-007, ESC-002, INC-2026-002

## DEC-009 - Serum spike on a double-counted weekend

- **Decision ID:** DEC-009 (record `dec_0009`)
- **Input context:** SKU-4001, vitamin C face serum 30ml, CAT-BPC. 2026-02-23, winter. Live price ₹599. Rolling 7-day 150 units, 30-day mean 140, demand trend +0.07, demand score 0.62. Competitor observed at ₹729. Inventory 600 units, 28.0 days cover. Band ₹439–₹779, historical average ₹549.
- **Proposed price:** ₹759
- **Guardrail status:** HIGH. GR-003 fired at HIGH with z = 4.78. GR-001 and GR-002 did not fire - the price stayed ₹20 inside the ceiling - so no suppression applied and GR-003 counted as an independent flag. Movement +26.71% is Band D.
- **Regret score:** 0.2583 (₹21,445, 25.83%, HIGH_REGRET). Best guardrail-feasible price ₹503.
- **Explanation:** The decision demonstrates why GR-003 exists as a separate control from GR-002. Nothing about the ₹759 price breaches a band boundary, yet it sits 4.78 standard deviations above the SKU's own price history and ₹256 above the modelled revenue optimum. The underlying demand signal was an artefact: a weekend spike double-counted through a timezone conversion, in breach of the transient-spike treatment required by PP-006. Registered as INC-2026-005, which is also the origin of the rule that ceiling-adjacent moves now require a full ceiling-breach evidence bundle.
- **Evidence source IDs:** GR-003, GR-007, PP-002, PP-006, BC-007, GR-008, INC-2026-005

## DEC-010 - Shirt price raised into a collapsing trend

- **Decision ID:** DEC-010 (record `dec_0039`)
- **Input context:** SKU-3001, men's cotton casual shirt, CAT-APR. 2026-08-07, monsoon. Live price ₹849. Rolling 7-day **300 units against a 30-day mean of 480**, demand trend -0.38, demand score 0.02. Competitor observed at ₹929. Inventory 1,900 units, 44.3 days cover.
- **Proposed price:** ₹949
- **Guardrail status:** HIGH. GR-004 fired at HIGH: an upward movement of +11.78% against a demand trend of -0.38 satisfies both the severity conditions - trend magnitude at or beyond 0.35 and movement magnitude at or beyond 8%. Price stayed inside the ₹719–₹1,279 band, so no floor or ceiling flag.
- **Regret score:** 0.0712 (₹19,989, 7.12%, QUESTIONABLE). Best guardrail-feasible price ₹749.
- **Explanation:** Every band check passed and the decision was still wrong. The demand score of 0.02 is the lowest in the decision set and sits far below the 0.20 threshold at which PP-006 hard-blocks upward movement. The proposal came from a margin-recovery routine optimising contribution margin per unit in isolation - correctly pursuing PP-001 item 3 with no visibility of item 4, so it could not price the volume it was destroying. The 8th of August also falls inside the Freedom Sale window under PP-007 and BC-005, making an upward move against collapsing demand a customer-trust exposure as well as a revenue one. Registered as INC-2026-006.
- **Evidence source IDs:** GR-004, GR-007, PP-001, PP-006, PP-007, BC-005, BC-007, INC-2026-006

## DEC-011 - Air conditioner undercut against a mis-matched listing

- **Decision ID:** DEC-011 (record `dec_0038`)
- **Input context:** SKU-6002, 1.5 ton 3-star inverter air conditioner, CAT-CEL. 2026-08-02, monsoon. Live price ₹32,999. Rolling 7-day 34 units, 30-day mean 30, demand trend +0.13, demand score 0.73. Competitor observed at ₹34,999. Inventory 95 units, 19.6 days cover. Band ₹27,199–₹48,299.
- **Proposed price:** ₹28,499
- **Guardrail status:** HIGH. GR-005 fired at HIGH - competitor deviation -18.57%, beyond the 15% threshold. The price stayed ₹1,300 above the floor, so GR-001 did not fire, and z = -2.02 sat below the GR-003 threshold. A single rule fired, and it was enough.
- **Regret score:** 0.0959 (₹1,14,432, 9.59%, QUESTIONABLE). Best guardrail-feasible price ₹41,284.
- **Explanation:** The largest absolute INR regret among the QUESTIONABLE-quality decisions, on a category with only a 5.0% minimum margin buffer. The competitor listing was a 1 ton unit with a shorter compressor warranty, failing the exact-match requirement in PP-004 on both tonnage and warranty term. PP-004 also requires any negative deviation beyond 15% to be checked for a matching error before it is treated as a genuine competitive gap; that check did not exist at the time. The move was executed as three sub-threshold steps, each inside Band A, which is the threshold-gaming pattern prohibited by PP-008 item 9 and constrained by the rolling 7-day net movement limit in PP-002. Registered as INC-2026-003.
- **Evidence source IDs:** GR-005, GR-007, PP-002, PP-004, PP-008, BC-002, BC-007, INC-2026-003

## DEC-012 - Rice markdown into 3.2 days of cover

- **Decision ID:** DEC-012 (record `dec_0018`)
- **Input context:** SKU-5002, premium basmati rice 5kg, CAT-GRO, essential staple. 2026-04-14, summer. Live price ₹799. Rolling 7-day 700 units - a 100-unit daily run rate - 30-day mean 620, demand trend +0.13, demand score 0.73. Competitor observed at ₹769. Regional inventory 320 units, **3.2 days cover**.
- **Proposed price:** ₹749
- **Guardrail status:** HIGH. GR-006 fired at HIGH: cover below 4 days combined with a downward movement of -6.26%, beyond the -3% condition. No other rule fired. Price sat comfortably inside the ₹599–₹1,049 band and z = 0.00.
- **Regret score:** 0.0028 (₹1,456, 0.28%, GOOD). Best guardrail-feasible price ₹791.
- **Explanation:** This is the most instructive example in the set because the two measures disagree completely. Guardrail status is HIGH; measured regret is ₹1,456 and the quality label reads GOOD. The regret model prices realised revenue only. It does not price the four-day regional unavailability that followed, the lost future margin, the substitution loss to a competitor, or the search-ranking penalty on the restored listing - the exclusions stated explicitly in BC-003 and repeated in the GR-006 notes. A reviewer reading the regret figure alone would have approved this. A reviewer following SOP-001 step 4 and testing against BC-003 would not. Registered as INC-2026-004, where the root cause was national rather than regional inventory being passed to the rule.
- **Evidence source IDs:** GR-006, GR-007, BC-003, BC-004, BC-007, PP-005, SOP-001, INC-2026-004
