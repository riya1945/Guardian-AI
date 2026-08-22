# Pricing Review Playbook

This playbook is synthetic operational guidance for the Guardian-AI demo.

## High Regret Review

High regret decisions need manual review before approval. Reviewers should compare the submitted price against the best counterfactual price, check whether predicted demand drops sharply, and validate business constraints before changing a price.

## Counterfactual Action

When the best counterfactual price differs from the submitted price, Guardian-AI should explain the direction of the change and the expected revenue gap. The dashboard should surface the selected price, best price, selected predicted demand, best predicted demand, selected predicted revenue, and best predicted revenue.

## Evidence Requirements

Pricing explanations must cite retrieved policy or incident snippets. If retrieval returns no relevant evidence, the explanation should refuse with this exact fallback: Evidence unavailable / insufficient to provide a grounded explanation.
