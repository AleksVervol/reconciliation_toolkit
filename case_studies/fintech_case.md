## Hypothesis
A discrepancy between the sender's expected and actual balance after a transaction
is a potential indicator of fraud.

## Method
Based on the dbt mart model `mart_balance_discrepancies`: comparing the sender's
balance before/after each transaction against the expected value (balance before
minus transaction amount), on a 50,000-transaction sample from PaySim.

## Finding
39,105 balance discrepancies were found — but only 5 of them are flagged as
confirmed fraud (is_fraud = 1). This means a balance discrepancy alone is a very
weak signal: applied naively as a rule, it would produce a ~99.99% false positive
rate.

## Recommendation
Balance discrepancy should not be used as a standalone fraud flag. Additional
segmentation is needed (e.g. by transaction amount, transaction type, or sender
pattern) to separate systemic effects (fees, rounding, delayed balance updates)
from genuine fraudulent behavior.