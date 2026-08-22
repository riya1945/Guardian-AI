# Explainability Guidelines

This guide defines demo explanation behavior for Guardian-AI.

## Grounding

Grounded explanations must connect engine output to retrieved repository knowledge. Valid evidence includes policy descriptions, review playbooks, and synthetic incident notes stored in the knowledge base.

## Factors

Useful factors include price versus historical average, counterfactual revenue gap, recent demand movement, and confidence modifiers such as demand momentum or weekend effects. Factors should be shown with direction, magnitude, and a short evidence statement.

## Uncertainty

Uncertainty should be explicit when competitor price, inventory, live demand, or real market data is missing. The current repository uses synthetic training data, so explanations should avoid production claims.
