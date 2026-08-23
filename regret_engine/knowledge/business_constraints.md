# Business Constraints - Pricing

**Constraint set ID:** BCS-2026-03
**Version:** 3.4
**Binds to:** PP-2026-04 v4.2
**Effective from:** 2026-01-01
**Refresh cadence:** Floors and ceilings recomputed on the first business day of each month
**Currency:** INR

Constraints in this document are checked **in addition to** the guardrail rules. A decision that passes every rule in `guardrail_rules.md` can still fail a constraint here, and a constraint failure is a rejection under SOP-003.

---

## BC-001 - Category Floor and Ceiling Ranges

Category bands define the envelope within which individual SKU floors and ceilings must sit. A SKU-level value outside its category envelope is a data error and blocks pricing on that SKU until corrected.

| Category ID | Category | SKU floor range | SKU ceiling range | Max spread (ceiling ÷ floor) |
|---|---|---|---|---|
| **CAT-MOB** | Mobile accessories | ₹199 – ₹1,099 | ₹399 – ₹1,799 | 1.85 |
| **CAT-SHK** | Small home & kitchen appliances | ₹899 – ₹3,999 | ₹1,599 – ₹7,499 | 1.85 |
| **CAT-APR** | Apparel & fashion | ₹499 – ₹1,499 | ₹999 – ₹2,499 | 1.85 |
| **CAT-BPC** | Beauty & personal care | ₹299 – ₹899 | ₹599 – ₹1,499 | 1.85 |
| **CAT-GRO** | Packaged grocery & staples | ₹499 – ₹1,299 | ₹899 – ₹1,999 | 1.85 |
| **CAT-CEL** | Consumer electronics & large appliances | ₹4,999 – ₹29,999 | ₹8,999 – ₹49,999 | 1.85 |

**Rules**

- The ceiling is a hard boundary in both directions of interpretation: it is the maximum permitted price, and it is also the upper bound of the feasible set the regret engine optimises over. The best price is always chosen from within `[floor, ceiling]`.
- No category band may be widened without a version increment under PP-010.
- CAT-GRO and any SKU classified as an essential staple carry the additional disruption-event restriction in PP-008 item 4.

---

## BC-002 - Margin Targets

Minimum margin drives the derived floor under PP-003: `floor = landed_cost / (1 - minimum_margin_pct)`. Target margin drives planning, not blocking.

| Category ID | Minimum margin | Target margin | Notes |
|---|---|---|---|
| **CAT-MOB** | 18.0% | 28.0% | High attach rate; margin funded by volume |
| **CAT-SHK** | 14.0% | 22.0% | Seasonal peaks in summer and festive windows |
| **CAT-APR** | 28.0% | 42.0% | Highest markdown exposure; monsoon clearance under PP-007 |
| **CAT-BPC** | 24.0% | 38.0% | Shelf-life sensitive; ageing stock releases to clearance at 90 days |
| **CAT-GRO** | 8.0% | 14.0% | Thin margin, high frequency; essential-goods restrictions apply |
| **CAT-CEL** | 5.0% | 9.0% | Highest absolute INR exposure per unit; smallest percentage buffer |

**Rules**

- Minimum margin is a floor input, never a target to be optimised toward. A price at exactly the minimum margin is at the hard floor and is one rounding error away from a GR-001 breach.
- Contribution margin is reported in absolute INR, not percentage, per PP-003. A 3% miss on CAT-CEL exceeds a 20% miss on CAT-MOB in rupee terms.
- Negative contribution margin is prohibited under PP-008 item 2 with no approval path at any level.

---

## BC-003 - Stockout Constraints

| Constraint | Threshold | Effect |
|---|---|---|
| Critical cover | Below 4 days | No downward movement of 3.0% or more. GR-006 HIGH. |
| Thin cover | Below 7 days | No downward movement without reviewer approval. GR-006 MEDIUM. |
| Low absolute units | 25 units or fewer | Flagged regardless of cover ratio or price direction. GR-006 MEDIUM. |
| Healthy cover | 7 to 60 days | Normal pricing operation |
| Excess cover | Above 60 days | Downward movement inside Band A encouraged to release working capital |
| Replenishment in flight | Open PO with receipt inside 5 days | Cover may be evaluated against projected receipt, but only where the PO reference is attached to the decision under GR-008 |

**Rules**

- Cover is evaluated at fulfilment-region level, never nationally. Evaluating national cover on a regional decision is the defect behind INC-2026-004.
- A stockout attributable to a live markdown is a mandatory rollback trigger under ESC-004.
- Stockout cost is **not** captured by the revenue regret figure. Regret prices realised revenue only; it does not price lost future margin, substitution loss, or the search-ranking penalty that follows an out-of-stock listing. A low regret figure on a GR-006 HIGH decision is not evidence that the decision was acceptable.
- Maximum permitted regional stockout duration on a CAT-GRO essential staple is 24 hours before the incident register entry becomes mandatory.

---

## BC-004 - Regional Constraints

Regions: North, South, East, West zones.

| Constraint | Rule |
|---|---|
| Regional price differential | Maximum ±6.0% between any two zones on the same SKU and channel in the same pricing cycle |
| Regional inventory evaluation | Mandatory. Inventory, cover and GR-006 are always evaluated on the fulfilment-region position |
| Regional competitor matching | Competitor observations are zone-scoped. A North zone observation may not justify a South zone price |
| Zone-restricted categories | CAT-CEL large appliances are priced only in zones with an active installation and service network |
| Disruption events | Where a weather, transport or civic disruption is declared in a zone, upward movement in that zone is capped at Band A on all SKUs and prohibited entirely on essentials, per PP-008 item 4 |
| Cross-zone arbitrage | Where the differential approaches ±6.0%, the narrower-margin zone sets the binding constraint for both |

**Rules**

- Regional differentials are pricing by market and are permitted. They are distinct from personalised price discrimination, which is prohibited under PP-008 item 5.
- A decision record submitted without a region key is rejected at the contract boundary. It does not default to the national position.

---

## BC-005 - Promotion Constraints

| Constraint | Rule |
|---|---|
| Floor immutability | Promotions never lower a floor. A promotional price below floor requires a co-funding reference added back under PP-003, or it is a GR-001 breach |
| Co-funding evidence | The funding reference must be attached to the decision record. Unreferenced co-funding claims are rejected under SOP-003 |
| List price immutability | Promotional systems may not mutate list price. Bundle discounts carry as a separate effective-price layer, per the remediation in INC-2026-007 |
| Promotion withdrawal | Withdrawal emits its own decision record and is evaluated by the full rule set. It is not treated as a restoration |
| Reference price | Struck-through list price must reflect a price genuinely charged for at least 28 consecutive days in the preceding 90 days. Inflating it is prohibited under PP-008 item 3 |
| Stacking | Maximum two concurrent discount layers per SKU. Coupon plus bank offer is the permitted maximum |
| Event manifest | Participation in a PP-007 seasonal window requires the SKU to appear on the event manifest. The manifest relaxes movement bands only, never floors |
| Post-promotion recovery | Return to pre-promotion price must respect the movement bands in PP-002 and may not be executed as a single Band D step |

**Recognised promotional windows:** Republic Day (15–26 January), Summer Sale (April), Monsoon Clearance (June–September), Freedom Sale (8–17 August), Big Festive Days (October–November).

---

## BC-006 - Channel Constraints

Channels: app, web, quick-commerce.

| Constraint | Rule |
|---|---|
| Channel differential | Maximum ±4.0% between app and web on the same SKU in the same zone and cycle |
| Quick-commerce premium | Quick-commerce may carry up to +8.0% over the web price to fund delivery economics, and this differential is exempt from the channel differential cap above |
| Quick-commerce assortment | Restricted to CAT-GRO, CAT-BPC and CAT-MOB. CAT-CEL is excluded |
| Channel-scoped movement | Movement bands under PP-002 are measured per channel. A movement on app does not consume the web allowance |
| Cross-channel consistency | A SKU may not sit above ceiling on one channel and below floor on another in the same cycle. Both are independent breaches and aggregate to HIGH under GR-007 |
| Channel-scoped inventory | Quick-commerce draws on dark-store inventory, which is evaluated separately from marketplace warehouse inventory under BC-003 |

---

## BC-007 - SKU Band Registry

Active SKU-level floors and ceilings. These are the binding values for GR-001 and GR-002. Historical average price is the 90-day volume-weighted mean used as the `hist` input to GR-003.

| SKU | Description | Category | Floor (₹) | Ceiling (₹) | Historical avg (₹) |
|---|---|---|---|---|---|
| **SKU-1001** | True wireless earbuds | CAT-MOB | 949 | 1,699 | 1,199 |
| **SKU-1002** | 65W fast charger | CAT-MOB | 679 | 1,199 | 849 |
| **SKU-1003** | Tempered glass screen protector | CAT-MOB | 239 | 429 | 299 |
| **SKU-2001** | 750W mixer grinder | CAT-SHK | 2,399 | 4,249 | 2,999 |
| **SKU-2002** | 1.5L electric kettle | CAT-SHK | 999 | 1,749 | 1,249 |
| **SKU-2003** | 4L air fryer | CAT-SHK | 3,749 | 6,699 | 4,699 |
| **SKU-3001** | Men's cotton casual shirt | CAT-APR | 719 | 1,279 | 899 |
| **SKU-3002** | Women's kurta set | CAT-APR | 1,039 | 1,849 | 1,299 |
| **SKU-4001** | Vitamin C face serum 30ml | CAT-BPC | 439 | 779 | 549 |
| **SKU-4002** | Anti-hairfall shampoo 650ml | CAT-BPC | 479 | 849 | 599 |
| **SKU-5001** | Cold-pressed groundnut oil 5L | CAT-GRO | 999 | 1,749 | 1,249 |
| **SKU-5002** | Premium basmati rice 5kg | CAT-GRO | 599 | 1,049 | 749 |
| **SKU-6001** | 43-inch 4K smart television | CAT-CEL | 20,799 | 36,899 | 25,999 |
| **SKU-6002** | 1.5 ton 3-star inverter air conditioner | CAT-CEL | 27,199 | 48,299 | 33,999 |
| **SKU-6003** | Bluetooth soundbar | CAT-CEL | 5,199 | 9,199 | 6,499 |

**Essential staple classification:** SKU-5001 and SKU-5002 are classified as essential staples and carry the disruption-event restriction in PP-008 item 4 and the 24-hour stockout reporting threshold in BC-003.

**Registry rules**

- Landed cost is held in the finance master and is not published here. Floors are the published derivation of it under PP-003.
- A SKU absent from this registry cannot be priced by the engine. Absence is a hard block, not a default-to-category fallback.
- Retired SKU identifiers are never reused, so that historical decisions remain interpretable under PP-010.
