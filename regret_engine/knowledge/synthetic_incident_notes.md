# Synthetic Incident Notes

These incident notes are synthetic examples for evaluating retrieval and explanation behavior in this repository.

## Incident A: Price Above Demand-Sensitive Range

When submitted prices drift materially above the historical average for a SKU, predicted demand can decline enough that a lower counterfactual price has higher predicted revenue. Explanations should highlight the revenue gap instead of only saying the price is high.

## Incident B: Weak Context Coverage

When competitor price or inventory is missing, confidence should be reduced or uncertainty should be stated. Missing context does not invalidate the regret score, but it limits how strongly Guardian-AI should recommend automated action.
